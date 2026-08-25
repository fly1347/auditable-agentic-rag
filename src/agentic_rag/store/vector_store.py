# src/agentic_rag/store/vector_store.py
# 程序作用：实现 Phase A 本地向量库（无额外依赖）：向量存 .npy，chunk 记录存 .jsonl；支持 upsert、count、sample、search（cosine，相当于 dot 因为向量已归一化）。
# 整体结构：
# 1) LocalVectorStore：持久化目录管理（artifacts/vector_store/）
# 2) upsert：按 chunk_id 覆盖写入（重写全量 .npy/.jsonl，Phase A 数据量可接受）
# 3) search：topk 检索（numpy 点积）
# 4) 诊断：count/sample

from __future__ import annotations  # 允许前置类型注解  # noqa: E402

import json  # jsonl 序列化  # noqa: E402
from dataclasses import dataclass  # 配置结构  # noqa: E402
from pathlib import Path  # 路径处理  # noqa: E402
from typing import Callable, Dict, List, Optional, Tuple  # 类型注解  # noqa: E402

import numpy as np  # 数值计算  # noqa: E402
from agentic_rag.policy.source_registry import validate_chunk_acl

try:  # 复用统一类型  # noqa: E402
    from agentic_rag.types import Chunk  # Chunk 类型  # noqa: E402
except Exception:  # fallback  # noqa: E402
    from dataclasses import dataclass as _dataclass  # 备用 dataclass  # noqa: E402
    from typing import Any as _Any  # 备用 Any  # noqa: E402

    @_dataclass  # 备用 Chunk  # noqa: E402
    class Chunk:  # noqa: E402
        chunk_id: str  # noqa: E402
        source_id: str  # noqa: E402
        doc_hash: str  # noqa: E402
        text: str  # noqa: E402
        offset_start: int  # noqa: E402
        offset_end: int  # noqa: E402
        metadata: Dict[str, _Any]  # noqa: E402


@dataclass  # 向量库配置  # noqa: E402
class VectorStoreConfig:  # noqa: E402
    persist_dir: str = "artifacts/vector_store"  # 默认持久化目录（不进 Git）  # noqa: E402


class LocalVectorStore:  # 本地向量库实现  # noqa: E402
    def __init__(self, cfg: Optional[VectorStoreConfig] = None):  # 初始化  # noqa: E402
        self.cfg = cfg or VectorStoreConfig()  # 应用默认配置  # noqa: E402
        self.dir = Path(self.cfg.persist_dir).expanduser().resolve()  # 规范化目录  # noqa: E402
        self.dir.mkdir(parents=True, exist_ok=True)  # 确保目录存在  # noqa: E402
        self.vec_path = self.dir / "vectors.npy"  # 向量文件  # noqa: E402
        self.meta_path = self.dir / "chunks.jsonl"  # chunk 元数据文件  # noqa: E402
        self._chunk_ids: List[str] = []  # chunk_id 列表（内存索引）  # noqa: E402
        self._chunks: List[Dict[str, object]] = []  # chunk dict 列表  # noqa: E402
        self._vectors: np.ndarray = np.zeros((0, 1), dtype=np.float32)  # 向量矩阵  # noqa: E402
        self._loaded = False  # 是否已加载  # noqa: E402

    def load(self) -> None:  # 从磁盘加载  # noqa: E402
        if self._loaded:  # 避免重复加载  # noqa: E402
            return  # 直接返回  # noqa: E402
        if self.vec_path.exists() and self.meta_path.exists():  # 文件齐全  # noqa: E402
            self._vectors = np.load(self.vec_path)  # 加载向量  # noqa: E402
            self._chunk_ids = []  # 重置  # noqa: E402
            self._chunks = []  # 重置  # noqa: E402
            with self.meta_path.open("r", encoding="utf-8") as f:  # 打开 jsonl  # noqa: E402
                for line in f:  # 遍历行  # noqa: E402
                    line = line.strip()  # 去空白  # noqa: E402
                    if not line:  # 空行  # noqa: E402
                        continue  # 跳过  # noqa: E402
                    obj = json.loads(line)  # 解析  # noqa: E402
                    self._chunk_ids.append(str(obj["chunk_id"]))  # 记录 chunk_id  # noqa: E402
                    self._chunks.append(obj)  # 记录 chunk dict  # noqa: E402
        else:  # 文件不齐  # noqa: E402
            self._vectors = np.zeros((0, 1), dtype=np.float32)  # 空库  # noqa: E402
            self._chunk_ids = []  # 空  # noqa: E402
            self._chunks = []  # 空  # noqa: E402
        self._loaded = True  # 标记已加载  # noqa: E402

    def _persist_all(self) -> None:  # 全量落盘（Phase A 可接受，简单稳定）  # noqa: E402
        np.save(self.vec_path, self._vectors.astype(np.float32))  # 保存向量  # noqa: E402
        with self.meta_path.open("w", encoding="utf-8") as f:  # 重写 jsonl  # noqa: E402
            for obj in self._chunks:  # 遍历 chunk  # noqa: E402
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")  # 写一行  # noqa: E402

    def count(self) -> int:  # 返回 chunk 总数  # noqa: E402
        self.load()  # 确保已加载  # noqa: E402
        return int(len(self._chunk_ids))  # 返回数量  # noqa: E402

    def sample(self, n: int = 3) -> List[Dict[str, object]]:  # 抽样查看  # noqa: E402
        self.load()  # 确保已加载  # noqa: E402
        return self._chunks[: max(0, int(n))]  # 返回前 n 个作为样本  # noqa: E402

    def upsert(self, chunks: List[Chunk], vectors: List[List[float]]) -> None:  # upsert：同 chunk_id 覆盖  # noqa: E402
        self.load()  # 确保加载  # noqa: E402
        if len(chunks) != len(vectors):  # 长度必须一致  # noqa: E402
            raise ValueError("chunks 与 vectors 长度不一致")  # 抛错  # noqa: E402
        if not chunks:  # 空输入  # noqa: E402
            return  # 无操作  # noqa: E402
        v = np.asarray(vectors, dtype=np.float32)  # 转为 numpy  # noqa: E402
        if self._vectors.shape[0] == 0:  # 空库初始化维度  # noqa: E402
            self._vectors = np.zeros((0, v.shape[1]), dtype=np.float32)  # 创建空矩阵  # noqa: E402
        if v.shape[1] != self._vectors.shape[1]:  # 维度必须一致  # noqa: E402
            raise ValueError(f"embedding dim 不一致：store={self._vectors.shape[1]} new={v.shape[1]}")  # 抛错  # noqa: E402
        index: Dict[str, int] = {cid: i for i, cid in enumerate(self._chunk_ids)}  # chunk_id -> row  # noqa: E402
        for chunk, vec in zip(chunks, v):  # 遍历输入  # noqa: E402
            validate_chunk_acl(chunk)  # store boundary: missing/mismatched ACL fails the build.
            cid = str(chunk.chunk_id)  # chunk_id  # noqa: E402
            obj: Dict[str, object] = {}  # chunk dict  # noqa: E402
            obj["chunk_id"] = cid  # 写入 chunk_id  # noqa: E402
            obj["source_id"] = str(chunk.source_id)  # 写入 source_id  # noqa: E402
            obj["doc_hash"] = str(chunk.doc_hash)  # 写入 doc_hash  # noqa: E402
            obj["text"] = str(chunk.text)  # 写入 text  # noqa: E402
            obj["offset_start"] = int(chunk.offset_start)  # 写入 offset_start  # noqa: E402
            obj["offset_end"] = int(chunk.offset_end)  # 写入 offset_end  # noqa: E402
            obj["metadata"] = dict(chunk.metadata or {})  # 写入 metadata  # noqa: E402
            if cid in index:  # 已存在则覆盖  # noqa: E402
                row = index[cid]  # 找到行号  # noqa: E402
                self._vectors[row, :] = vec  # 覆盖向量  # noqa: E402
                self._chunks[row] = obj  # 覆盖元数据  # noqa: E402
            else:  # 不存在则追加  # noqa: E402
                self._chunk_ids.append(cid)  # 追加 id  # noqa: E402
                self._chunks.append(obj)  # 追加 obj  # noqa: E402
                self._vectors = np.vstack([self._vectors, vec.reshape(1, -1)])  # 追加向量行  # noqa: E402
                index[cid] = len(self._chunk_ids) - 1  # 更新索引  # noqa: E402
        self._persist_all()  # 全量落盘  # noqa: E402

    def search(
        self,
        query_vector: List[float],
        topk: int = 5,
        predicate: Optional[Callable[[Dict[str, object]], bool]] = None,
    ) -> List[Tuple[Dict[str, object], float]]:  # 检索 topk  # noqa: E402
        self.load()  # 确保已加载  # noqa: E402
        if self._vectors.shape[0] == 0:  # 空库  # noqa: E402
            return []  # 返回空  # noqa: E402
        q = np.asarray(query_vector, dtype=np.float32).reshape(1, -1)  # 转为行向量  # noqa: E402
        if q.shape[1] != self._vectors.shape[1]:  # 维度检查  # noqa: E402
            raise ValueError(f"query dim 不一致：store={self._vectors.shape[1]} query={q.shape[1]}")  # 抛错  # noqa: E402
        scores = (self._vectors @ q.T).reshape(-1)  # 点积（向量归一化时等价 cosine）  # noqa: E402
        # ACL/tenant filtering happens before TopK selection.  Computing the
        # similarity matrix is still O(N), but denied rows can no longer occupy
        # the finite TopK window and starve authorized evidence.
        if predicate is None:
            eligible = np.arange(scores.shape[0], dtype=np.int64)
        else:
            eligible = np.asarray(
                [idx for idx, chunk in enumerate(self._chunks) if bool(predicate(chunk))],
                dtype=np.int64,
            )
        k = max(0, min(int(topk), int(eligible.shape[0])))  # 计算有效 k  # noqa: E402
        if k == 0:  # k=0  # noqa: E402
            return []  # 返回空  # noqa: E402
        eligible_scores = scores[eligible]
        local_idx = np.argpartition(-eligible_scores, kth=k - 1)[:k]
        local_idx = local_idx[np.argsort(-eligible_scores[local_idx])]
        idx = eligible[local_idx]
        out: List[Tuple[Dict[str, object], float]] = []  # 输出  # noqa: E402
        for i in idx.tolist():  # 遍历索引  # noqa: E402
            out.append((self._chunks[int(i)], float(scores[int(i)])))  # 追加 (chunk, score)  # noqa: E402
        return out  # 返回结果  # noqa: E402
    def query(
        self,
        query_vector: List[float],
        topk: int = 5,
        predicate: Optional[Callable[[Dict[str, object]], bool]] = None,
    ) -> List[Tuple[Dict[str, object], float]]:  # query：对外统一命名（等价 search）  # noqa: E402
        return self.search(query_vector=query_vector, topk=int(topk), predicate=predicate)
