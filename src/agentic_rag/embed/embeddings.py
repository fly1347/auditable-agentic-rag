# src/agentic_rag/embed/embeddings.py
# 程序作用：提供 Embedding 接口冻结：embed(texts)->vectors；默认使用 BAAI/bge-small-zh-v1.5；L2 normalize；批处理；Phase C 新增 query embedding 内存缓存。
# 整体结构：
# 1) EmbeddingConfig：模型名、batch_size、normalize
# 2) 模块级 query embedding cache：只缓存单条 query embedding，不缓存检索结果/生成结果/judge 结果
# 3) EmbeddingModel：加载模型并提供 embed
# 4) 辅助函数：L2 normalize、依赖探测、缓存开关与 LRU 管理

from __future__ import annotations  # 允许前置类型注解  # noqa: E402

import hashlib  # 用于构造稳定 cache key  # noqa: E402
import os  # 读取 DISABLE_EMBED_CACHE / EMBED_CACHE_MAX_SIZE  # noqa: E402
from collections import OrderedDict  # 简单 LRU 缓存  # noqa: E402
from dataclasses import dataclass  # 配置结构  # noqa: E402
from threading import Lock  # 保护模块级缓存  # noqa: E402
from typing import Dict, List, Optional  # 类型注解  # noqa: E402

import numpy as np  # 用于向量与归一化  # noqa: E402


@dataclass  # EmbeddingConfig：embedding 配置  # noqa: E402
class EmbeddingConfig:  # noqa: E402
    model_name: str = "BAAI/bge-small-zh-v1.5"  # 融合版默认模型  # noqa: E402
    batch_size: int = 32  # 默认 batch_size  # noqa: E402
    normalize: bool = True  # 是否 L2 normalize  # noqa: E402


def _l2_normalize(v: np.ndarray) -> np.ndarray:  # 对二维向量做 L2 normalize  # noqa: E402
    denom = np.linalg.norm(v, axis=1, keepdims=True) + 1e-12  # 计算范数并防止除零  # noqa: E402
    return v / denom  # 返回归一化结果  # noqa: E402


def _try_sentence_transformers():  # 探测 sentence-transformers（优先）  # noqa: E402
    try:  # noqa: E402
        from sentence_transformers import SentenceTransformer  # type: ignore  # 动态导入  # noqa: E402

        return SentenceTransformer  # 返回类  # noqa: E402
    except Exception:  # 无依赖  # noqa: E402
        return None  # 返回 None  # noqa: E402


def _env_truthy(name: str) -> bool:
    """读取布尔环境变量。"""

    raw = str(os.getenv(name, "")).strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


def _read_positive_int_from_env(name: str, default: int) -> int:
    """读取正整数环境变量，非法值回退到 default。"""

    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return int(default)
    try:
        value = int(raw)
    except ValueError:
        return int(default)
    return max(1, value)


def _embedding_cache_enabled() -> bool:
    """判断 query embedding cache 是否启用。"""

    return not _env_truthy("DISABLE_EMBED_CACHE")


def _make_query_cache_key(cfg: EmbeddingConfig, text: str) -> str:
    """构造 query embedding cache key，绑定模型名、normalize 配置与 query 文本。"""

    src = f"{cfg.model_name}|normalize={bool(cfg.normalize)}|{text}"
    return hashlib.sha256(src.encode("utf-8")).hexdigest()


_QUERY_EMBED_CACHE_MAX_SIZE = _read_positive_int_from_env("EMBED_CACHE_MAX_SIZE", 1000)
_QUERY_EMBED_CACHE: "OrderedDict[str, List[float]]" = OrderedDict()
_QUERY_EMBED_CACHE_LOCK = Lock()


def _get_cached_query_embedding(key: str) -> Optional[List[float]]:
    """从模块级 LRU 缓存读取 query embedding。"""

    with _QUERY_EMBED_CACHE_LOCK:
        value = _QUERY_EMBED_CACHE.get(str(key))
        if value is None:
            return None
        _QUERY_EMBED_CACHE.move_to_end(str(key))
        return list(value)


def _put_cached_query_embedding(key: str, vector: List[float]) -> None:
    """写入模块级 LRU 缓存。"""

    with _QUERY_EMBED_CACHE_LOCK:
        _QUERY_EMBED_CACHE[str(key)] = list(vector)
        _QUERY_EMBED_CACHE.move_to_end(str(key))
        while len(_QUERY_EMBED_CACHE) > int(_QUERY_EMBED_CACHE_MAX_SIZE):
            _QUERY_EMBED_CACHE.popitem(last=False)


class EmbeddingModel:  # EmbeddingModel：统一 embed 接口  # noqa: E402
    def __init__(self, cfg: Optional[EmbeddingConfig] = None):  # 初始化  # noqa: E402
        self.cfg = cfg or EmbeddingConfig()  # 使用默认配置  # noqa: E402
        SentenceTransformer = _try_sentence_transformers()  # 探测依赖  # noqa: E402
        if SentenceTransformer is None:  # 没装 sentence-transformers  # noqa: E402
            raise RuntimeError(  # 抛出明确错误  # noqa: E402
                "缺少依赖 sentence-transformers；请安装后再运行：pip install sentence-transformers"  # 错误信息  # noqa: E402
            )  # raise 完成  # noqa: E402
        self._model = SentenceTransformer(
            self.cfg.model_name,
            local_files_only=True,
        )  # 加载模型  # noqa: E402
        self._model.max_seq_length = 512  # 强制最大序列长度，超长自动截断，避免刷屏警告  # noqa: E402
        self.dim = int(getattr(self._model, "get_sentence_embedding_dimension")())  # 记录维度  # noqa: E402

    def content_token_counts(self, texts: List[str]) -> List[int]:
        """Count untruncated content tokens with the embedding model tokenizer."""
        tokenizer = getattr(self._model, "tokenizer", None)
        if tokenizer is None:
            raise RuntimeError("embedding model does not expose a tokenizer")
        encoded = tokenizer(
            list(texts),
            add_special_tokens=False,
            truncation=False,
            padding=False,
            verbose=False,
        )
        return [len(list(item)) for item in encoded.get("input_ids", [])]

    def content_token_offsets(self, text: str) -> List[tuple[int, int]]:
        """Return exact untruncated content-token character offsets for one text.

        Production structure-first splitting uses this same tokenizer contract as
        the final embedding hard gate, so token budgeting and embedding cannot
        silently disagree.
        """
        tokenizer = getattr(self._model, "tokenizer", None)
        if tokenizer is None:
            raise RuntimeError("embedding model does not expose a tokenizer")
        if not bool(getattr(tokenizer, "is_fast", False)):
            raise RuntimeError(
                "embedding tokenizer must be a fast tokenizer to expose exact offset_mapping"
            )
        encoded = tokenizer(
            str(text),
            add_special_tokens=False,
            truncation=False,
            padding=False,
            return_offsets_mapping=True,
            verbose=False,
        )
        offsets = list(encoded.get("offset_mapping", []) or [])
        if not offsets and text:
            # Whitespace-only text may legitimately produce no content tokens.
            token_count = self.content_token_counts([str(text)])[0]
            if token_count:
                raise RuntimeError("embedding tokenizer did not return offset_mapping")
        return [(int(start), int(end)) for start, end in offsets]

    def validate_content_token_budget(
        self,
        texts: List[str],
        *,
        max_content_tokens: int = 510,
    ) -> Dict[str, int]:
        """Fail the index build before embedding truncation can lose content."""
        counts = self.content_token_counts(texts)
        violating = [count for count in counts if count > int(max_content_tokens)]
        if violating:
            raise ValueError(
                "embedding token budget exceeded: "
                f"violations={len(violating)} max_observed={max(violating)} "
                f"limit={max_content_tokens}"
            )
        return {
            "validated_text_count": len(counts),
            "max_content_tokens": max(counts) if counts else 0,
            "content_token_limit": int(max_content_tokens),
        }

    def embed(self, texts: List[str]) -> List[List[float]]:  # 冻结接口：返回 list[list[float]]  # noqa: E402
        if not texts:  # 空输入  # noqa: E402
            return []  # 返回空  # noqa: E402

        # Phase C 只缓存单条 query embedding；批量 embedding 主要用于 ingest/index，不进入缓存。
        if len(texts) == 1 and _embedding_cache_enabled():
            text = str(texts[0])
            cache_key = _make_query_cache_key(self.cfg, text)
            cached = _get_cached_query_embedding(cache_key)
            if cached is not None:
                return [cached]

            vecs = self._embed_uncached([text])
            if vecs:
                _put_cached_query_embedding(cache_key, vecs[0])
            return vecs

        return self._embed_uncached(texts)

    def _embed_uncached(self, texts: List[str]) -> List[List[float]]:
        """执行真实 embedding 计算，不读写 query cache。"""

        bs = int(self.cfg.batch_size)  # batch_size  # noqa: E402
        out: List[List[float]] = []  # 累计输出  # noqa: E402
        for i in range(0, len(texts), bs):  # 分批  # noqa: E402
            batch = texts[i : i + bs]  # 当前批次  # noqa: E402
            vec = self._model.encode(batch, show_progress_bar=False, convert_to_numpy=True, normalize_embeddings=False)  # 保持你自己的 normalize 逻辑不变  # noqa: E402
            vec = vec.astype(np.float32)  # 统一 float32  # noqa: E402
            if self.cfg.normalize:  # 需要归一化  # noqa: E402
                vec = _l2_normalize(vec)  # L2 normalize  # noqa: E402
            out.extend(vec.tolist())  # 转回 Python list  # noqa: E402
        return out  # 返回结果  # noqa: E402
