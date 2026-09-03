"""
程序作用：
提供公开默认的 Hybrid RRF 检索器：Dense Top10 + BM25 Top10，经 RRF(k=60) 融合后返回最终 TopK。

整体结构：
1）复用当前不可变向量库中的同一批 chunk，同时构建 Dense 与 BM25 候选通道；
2）两路候选分别保留真实分数语义与 ACL 结果；
3）使用 RRF 做稳定融合，并把 retrieval events、融合贡献和参数写入审计轨迹。
"""

from __future__ import annotations

import re
import time
from typing import Any, Optional

from agentic_rag.retrieve.fusion import FusionInput, retrieval_event, rrf_fuse
from agentic_rag.retrieve.retriever import Retriever
from agentic_rag.types import Chunk, RetrievalResult


def _tokenize(text: str) -> list[str]:
    """沿用已验证的 BM25/RRF 实验分词口径。"""
    try:
        import jieba
    except ImportError as exc:  # pragma: no cover - runtime dependency guard
        raise RuntimeError("hybrid_rrf requires jieba; install project local extras") from exc

    parts = re.findall(r"[a-z][a-z0-9_.+#-]*|[\u4e00-\u9fff]+", str(text).lower())
    out: list[str] = []
    for part in parts:
        if re.fullmatch(r"[\u4e00-\u9fff]+", part):
            out.extend(token for token in jieba.lcut(part) if token.strip())
        else:
            out.append(part)
    return out


def _chunk_from_store_row(row: dict[str, Any]) -> Chunk:
    return Chunk(
        chunk_id=str(row.get("chunk_id", "")),
        source_id=str(row.get("source_id", "")),
        doc_hash=str(row.get("doc_hash", "")),
        text=str(row.get("text", "")),
        offset_start=int(row.get("offset_start", 0)),
        offset_end=int(row.get("offset_end", 0)),
        metadata=dict(row.get("metadata") or {}),
    )


def _chunk_from_dense_hit(hit: Any) -> Chunk:
    return Chunk(
        chunk_id=str(getattr(hit, "chunk_id", "")),
        source_id=str(getattr(hit, "source_id", "")),
        doc_hash=str(getattr(hit, "doc_hash", "")),
        text=str(getattr(hit, "text", "")),
        offset_start=int(getattr(hit, "offset_start", 0)),
        offset_end=int(getattr(hit, "offset_end", 0)),
        metadata=dict(getattr(hit, "metadata", {}) or {}),
    )


class HybridRRFRetriever:
    """复用当前不可变向量库，构造 Dense + BM25 + RRF 的统一检索接口。"""

    def __init__(
        self,
        dense_retriever: Retriever,
        *,
        dense_candidate_topk: int = 10,
        bm25_candidate_topk: int = 10,
        rrf_k: int = 60,
    ) -> None:
        if dense_candidate_topk < 1 or bm25_candidate_topk < 1 or rrf_k < 1:
            raise ValueError("hybrid_rrf candidate sizes and rrf_k must be positive")
        try:
            from rank_bm25 import BM25Okapi
        except ImportError as exc:  # pragma: no cover - runtime dependency guard
            raise RuntimeError("hybrid_rrf requires rank-bm25; install project local extras") from exc

        self.dense = dense_retriever
        self.dense_candidate_topk = int(dense_candidate_topk)
        self.bm25_candidate_topk = int(bm25_candidate_topk)
        self.rrf_k = int(rrf_k)

        # Reuse the exact current S2 chunks; no second corpus or index version is introduced.
        store = self.dense.store
        rows = [dict(row) for row in store.sample(store.count())]
        self._rows = rows
        self._chunks = [_chunk_from_store_row(row) for row in rows]
        self._bm25 = BM25Okapi([_tokenize(chunk.text) for chunk in self._chunks])

    def run(
        self,
        query: str,
        topk: Optional[int] = None,
        user_context: Any = None,
    ) -> RetrievalResult:
        started = time.perf_counter()
        final_topk = int(topk if topk is not None else self.dense.cfg.topk)
        dense_k = max(final_topk, self.dense_candidate_topk)
        bm25_k = max(final_topk, self.bm25_candidate_topk)

        dense_started = time.perf_counter()
        dense_out = self.dense.run(
            query=str(query),
            topk=dense_k,
            user_context=user_context,
        )
        dense_ms = (time.perf_counter() - dense_started) * 1000.0
        dense_chunks = [_chunk_from_dense_hit(hit) for hit in dense_out.hits]
        dense_scores = [float(getattr(hit, "score", 0.0)) for hit in dense_out.hits]
        dense_rr = RetrievalResult(
            query=str(query),
            chunks=dense_chunks,
            scores=dense_scores,
            topk=dense_k,
            timing_ms=float(dense_ms),
            access_policy=dict(dense_out.access_policy or {}),
            score_type="vector_similarity",
        )

        # Dense's ACL predicate scans the whole current store before TopK, so this set is
        # the same source-level visibility decision used by the production retriever.
        allowed_sources = set(dense_out.access_policy.get("allowed_source_ids") or [])

        bm_started = time.perf_counter()
        bm_scores = self._bm25.get_scores(_tokenize(str(query)))
        ranked_indices = sorted(
            range(len(self._chunks)),
            key=lambda idx: (-float(bm_scores[idx]), self._chunks[idx].chunk_id),
        )
        bm_indices = [
            idx for idx in ranked_indices
            if self._chunks[idx].source_id in allowed_sources
        ][:bm25_k]
        bm_chunks = [self._chunks[idx] for idx in bm_indices]
        bm_rank_scores = [float(bm_scores[idx]) for idx in bm_indices]
        bm_ms = (time.perf_counter() - bm_started) * 1000.0
        bm_rr = RetrievalResult(
            query=str(query),
            chunks=bm_chunks,
            scores=bm_rank_scores,
            topk=bm25_k,
            timing_ms=float(bm_ms),
            access_policy=dict(dense_out.access_policy or {}),
            score_type="bm25",
        )

        fused = rrf_fuse(
            query=str(query),
            inputs=[
                FusionInput(dense_rr, "dense_channel", 0),
                FusionInput(bm_rr, "bm25_channel", 0),
            ],
            topk=final_topk,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
            rrf_k=self.rrf_k,
        )
        object.__setattr__(
            fused,
            "retrieval_events",
            [
                retrieval_event(dense_rr, query_role="dense_channel", round_id=0, duration_ms=dense_ms),
                retrieval_event(bm_rr, query_role="bm25_channel", round_id=0, duration_ms=bm_ms),
            ],
        )
        trace = dict(fused.merge_trace or {})
        trace.update(
            {
                "strategy": "hybrid_dense_bm25_rrf",
                "dense_candidate_topk": self.dense_candidate_topk,
                "bm25_candidate_topk": self.bm25_candidate_topk,
                "final_topk": final_topk,
                "rrf_k": self.rrf_k,
                "stable_tie_breaker": "rrf_score,best_rank,first_input,chunk_id",
                "bm25_corpus_chunk_count": len(self._chunks),
            }
        )
        object.__setattr__(fused, "merge_trace", trace)
        return fused


__all__ = ["HybridRRFRetriever"]
