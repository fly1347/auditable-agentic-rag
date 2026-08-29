"""
程序作用：
按排名融合多路检索结果，并完整保留各候选的来源、轮次、原始排名和融合贡献。

整体结构：
1）FusionInput 描述一路检索结果及其查询角色、轮次；
2）candidate_item 与 retrieval_event 生成可审计的候选和事件投影；
3）rrf_fuse 使用 RRF 融合排名，返回结果与逐项贡献明细。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Sequence

from agentic_rag.types import Chunk, RetrievalResult


@dataclass(frozen=True)
class FusionInput:
    result: RetrievalResult
    query_role: str
    round_id: int


def candidate_item(
    chunk: Chunk,
    *,
    rank: int,
    score: float | None,
    score_type: str,
    selected: bool = True,
) -> dict[str, Any]:
    return {
        "rank": int(rank),
        "chunk_id": str(getattr(chunk, "chunk_id", "")),
        "source_id": str(getattr(chunk, "source_id", "")),
        "offset_start": int(getattr(chunk, "offset_start", 0)),
        "offset_end": int(getattr(chunk, "offset_end", 0)),
        "score": float(score) if score is not None else None,
        "score_type": str(score_type),
        "selected": bool(selected),
    }


def retrieval_event(
    result: RetrievalResult,
    *,
    query_role: str,
    round_id: int,
    duration_ms: float,
) -> dict[str, Any]:
    return {
        "round_id": int(round_id),
        "query_role": str(query_role),
        "query": str(result.query),
        "topk": int(result.topk),
        "duration_ms": float(duration_ms),
        "access_policy": dict(getattr(result, "access_policy", {}) or {}),
        "candidates": [
            candidate_item(
                chunk,
                rank=index,
                score=result.scores[index - 1] if index - 1 < len(result.scores) else None,
                score_type=str(getattr(result, "score_type", "vector_similarity")),
            )
            for index, chunk in enumerate(result.chunks, start=1)
        ],
    }


def rrf_fuse(
    query: str,
    inputs: Sequence[FusionInput],
    *,
    topk: int,
    elapsed_ms: float,
    rrf_k: int = 60,
) -> RetrievalResult:
    """使用排名融合多路结果，不直接比较不同检索器口径不一的原始分数。"""

    if rrf_k < 1:
        raise ValueError("rrf_k must be positive")

    by_id: dict[str, dict[str, Any]] = {}
    pre_dedupe: list[dict[str, Any]] = []
    all_events: list[dict[str, Any]] = []
    access_policies: list[dict[str, Any]] = []

    for input_index, item in enumerate(inputs):
        result = item.result
        all_events.extend(list(getattr(result, "retrieval_events", []) or []))
        policy = dict(getattr(result, "access_policy", {}) or {})
        if policy:
            access_policies.append(policy)
        for rank, chunk in enumerate(result.chunks, start=1):
            raw_score = result.scores[rank - 1] if rank - 1 < len(result.scores) else None
            contribution = 1.0 / float(rrf_k + rank)
            row = {
                **candidate_item(
                    chunk,
                    rank=rank,
                    score=raw_score,
                    score_type=str(getattr(result, "score_type", "vector_similarity")),
                ),
                "round_id": int(item.round_id),
                "query_role": str(item.query_role),
                "query": str(result.query),
                "rrf_contribution": contribution,
            }
            pre_dedupe.append(row)
            chunk_id = str(chunk.chunk_id)
            aggregate = by_id.setdefault(
                chunk_id,
                {
                    "chunk": chunk,
                    "rrf_score": 0.0,
                    "best_rank": rank,
                    "first_input": input_index,
                    "contributions": [],
                },
            )
            aggregate["rrf_score"] += contribution
            aggregate["best_rank"] = min(int(aggregate["best_rank"]), rank)
            aggregate["contributions"].append(
                {
                    "round_id": int(item.round_id),
                    "query_role": str(item.query_role),
                    "query": str(result.query),
                    "rank": rank,
                    "raw_score": float(raw_score) if raw_score is not None else None,
                    "rrf_contribution": contribution,
                }
            )

    ordered = sorted(
        by_id.items(),
        key=lambda pair: (
            -float(pair[1]["rrf_score"]),
            int(pair[1]["best_rank"]),
            int(pair[1]["first_input"]),
            pair[0],
        ),
    )
    selected = ordered[: max(0, int(topk))]
    chunks = [data["chunk"] for _, data in selected]
    scores = [float(data["rrf_score"]) for _, data in selected]
    final_order = [
        {
            "rank": rank,
            "chunk_id": chunk_id,
            "source_id": str(data["chunk"].source_id),
            "rrf_score": float(data["rrf_score"]),
            "contributions": list(data["contributions"]),
        }
        for rank, (chunk_id, data) in enumerate(selected, start=1)
    ]
    trace = {
        "strategy": "rrf",
        "rrf_k": int(rrf_k),
        "input_count": len(inputs),
        "pre_dedupe_candidates": pre_dedupe,
        "dedupe_key": "chunk_id",
        "unique_candidate_count": len(ordered),
        "final_order": final_order,
        "subquery_quota_enabled": False,
    }
    return RetrievalResult(
        query=str(query),
        chunks=chunks,
        scores=scores,
        topk=int(topk),
        timing_ms=float(elapsed_ms),
        retrieval_events=all_events,
        merge_trace=trace,
        access_policy={"enforced_before_topk": True, "queries": access_policies},
        score_type="rrf",
    )


__all__ = ["FusionInput", "candidate_item", "retrieval_event", "rrf_fuse"]
