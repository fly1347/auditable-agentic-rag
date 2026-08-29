"""
文件作用：
1）提供 legacy 全局 rerank 与 D-lite selective rerank 共用的轻量 rerank 能力；
2）输入 query 与候选 chunks，输出重排后的 chunk 列表与 rerank 分数；
3）提供 top1-top5 gap 计算与 selective 触发判断；
4）默认使用 sentence-transformers CrossEncoder 加载 BAAI/bge-reranker-base；
5）采用懒加载，避免 baseline 路径产生额外初始化开销。

整体结构：
1）RerankResult 保存重排后 chunk、分数与模型信息；
2）gap 与触发函数判断是否需要 selective rerank；
3）CrossEncoderReranker 懒加载模型并执行实际重排。

说明：
- 本模块只在 rerank 开关开启时被调用；
- 若本地缺少 sentence-transformers，可按报错信息安装后再运行；
- 若模型尚未缓存，首次运行会发生模型加载开销。
"""

from __future__ import annotations  # 启用前向引用类型标注。

from dataclasses import dataclass  # 导入 dataclass。
from typing import List, Optional, Sequence, Tuple  # 导入类型标注。

from agentic_rag.types import Chunk  # 导入稳定 Chunk 类型。


@dataclass(frozen=True)
class RerankResult:
    chunks: List[Chunk]
    scores: List[float]


def compute_top1_topk_gap(scores: Sequence[float], k: int = 5) -> Optional[float]:
    """计算 top1 与 topk 末位之间的分数差；候选不足 k 个时返回 None。"""
    score_list: List[float] = [float(x) for x in list(scores or [])]
    if len(score_list) < int(k):
        return None
    return float(score_list[0] - score_list[int(k) - 1])


def should_trigger_selective_rerank(scores: Sequence[float], threshold: float, k: int = 5) -> bool:
    """当 top1-topk gap 小于阈值时触发 selective rerank。"""
    gap: Optional[float] = compute_top1_topk_gap(scores=scores, k=int(k))
    if gap is None:
        return False
    return bool(gap < float(threshold))


class CrossEncoderReranker:
    _model_cache = {}

    def __init__(self, model_name: str = "BAAI/bge-reranker-base") -> None:
        self.model_name = str(model_name)

    @classmethod
    def _load_model(cls, model_name: str):
        if model_name in cls._model_cache:
            return cls._model_cache[model_name]
        try:
            from sentence_transformers import CrossEncoder
        except Exception as exc:
            raise RuntimeError(
                "缺少 sentence-transformers，无法启用 rerank。请先安装该依赖。"
            ) from exc
        model = CrossEncoder(
            model_name,
            local_files_only=True,
        )
        cls._model_cache[model_name] = model
        return model

    def rerank(self, query: str, chunks: Sequence[Chunk], topn: int) -> RerankResult:
        chunk_list: List[Chunk] = list(chunks or [])
        if len(chunk_list) == 0:
            return RerankResult(chunks=[], scores=[])

        model = self._load_model(self.model_name)
        sentence_pairs: List[Tuple[str, str]] = [
            (str(query), str(chunk.text)) for chunk in chunk_list
        ]
        raw_scores = model.predict(sentence_pairs)
        scored = list(zip(chunk_list, [float(score) for score in raw_scores]))
        scored.sort(key=lambda item: item[1], reverse=True)
        kept = scored[: max(0, int(topn))]
        return RerankResult(
            chunks=[item[0] for item in kept],
            scores=[item[1] for item in kept],
        )
