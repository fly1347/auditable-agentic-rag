"""
作用：
- 构建 D-full Step 9 的 EvidenceItem / EvidencePacket。
- 输入来自 retrieve_node 写入的 RetrievalResult 与 WorkflowState.retrieval_rounds。
- 当前为最小可用版本：不接 sufficiency、不接 citation_support、不接 conflict detection。

整体结构：
1. chunk_to_evidence_item：将 Chunk + score 转成 EvidenceItem。
2. build_evidence_items：从 RetrievalResult 构建 EvidenceItem 列表。
3. compress_evidence_items：按 source 去重压缩，最多保留 max_chunks_in_packet。
4. build_evidence_packet：生成 EvidencePacket 与基础诊断字段。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from agentic_rag.evidence.diagnostics import (
    detect_known_gaps,
    summarize_answer_bearing,
    summarize_scores,
    summarize_source_coverage,
)
from agentic_rag.types import Chunk, RetrievalResult
from agentic_rag.workflow.workflow_state import EvidenceItem, EvidencePacket, RetrievalRound


DEFAULT_TEXT_PREVIEW_CHARS = 300
DEFAULT_MAX_CHUNKS_IN_PACKET = 5


def _metadata_value(metadata: Dict[str, Any], keys: Sequence[str]) -> Optional[str]:
    """作用：按候选 key 从 metadata 中读取第一个非空字符串值。"""
    for key in keys:
        value = metadata.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _round_lookup(rounds: List[RetrievalRound]) -> Dict[str, RetrievalRound]:
    """作用：按 retrieval_query 建立 round 映射，便于回填检索轮次。"""
    out: Dict[str, RetrievalRound] = {}
    for item in rounds:
        query = str(item.retrieval_query or "").strip()
        if query and query not in out:
            out[query] = item
    return out


def _score_at(scores: Sequence[float], idx: int) -> Optional[float]:
    """作用：安全读取分数。"""
    if idx < 0 or idx >= len(scores):
        return None
    try:
        return float(scores[idx])
    except (TypeError, ValueError):
        return None


def chunk_to_evidence_item(
    chunk: Chunk,
    *,
    vector_score: Optional[float] = None,
    rrf_score: Optional[float] = None,
    rerank_score: Optional[float] = None,
    retrieval_round: Optional[int] = None,
    retrieval_query: Optional[str] = None,
    rank_before_rerank: Optional[int] = None,
    rank_after_rerank: Optional[int] = None,
    text_preview_chars: int = DEFAULT_TEXT_PREVIEW_CHARS,
) -> EvidenceItem:
    """作用：把一个 Chunk 转成 EvidenceItem，并尽量从 metadata 补齐来源字段。"""
    metadata = dict(getattr(chunk, "metadata", {}) or {})
    acl = dict(metadata.get("acl") or {}) if isinstance(metadata.get("acl"), dict) else {}
    text = str(getattr(chunk, "text", "") or "")

    return EvidenceItem(
        chunk_id=str(getattr(chunk, "chunk_id", "")),
        source_id=str(getattr(chunk, "source_id", "")),
        source_path=_metadata_value(
            metadata,
            ["source_path", "path", "file_path", "doc_path", "source"],
        ),
        section_path=_metadata_value(
            metadata,
            ["section_path", "heading_path", "headers", "section"],
        ),
        offset_start=int(getattr(chunk, "offset_start", 0)),
        offset_end=int(getattr(chunk, "offset_end", 0)),
        text_preview=text[: int(text_preview_chars)],
        visibility=str(acl.get("visibility")) if acl.get("visibility") not in (None, "") else None,
        vector_score=vector_score,
        rrf_score=rrf_score,
        rerank_score=rerank_score,
        retrieval_round=retrieval_round,
        retrieval_query=retrieval_query,
        rank_before_rerank=rank_before_rerank,
        rank_after_rerank=rank_after_rerank,
        in_prompt=False,
    )


def build_evidence_items(
    retrieval_result: RetrievalResult,
    retrieval_rounds: Optional[List[RetrievalRound]] = None,
    *,
    text_preview_chars: int = DEFAULT_TEXT_PREVIEW_CHARS,
) -> List[EvidenceItem]:
    """作用：从 RetrievalResult 构建 EvidenceItem 列表。"""
    rounds = list(retrieval_rounds or [])
    round_by_query = _round_lookup(rounds)
    result_query = str(getattr(retrieval_result, "query", "") or "").strip()
    matched_round = round_by_query.get(result_query)

    chunks = list(getattr(retrieval_result, "chunks", []) or [])
    result_scores = list(getattr(retrieval_result, "scores", []) or [])
    rerank_scores = list(getattr(retrieval_result, "rerank_scores", []) or [])
    score_type = str(getattr(retrieval_result, "score_type", "vector_similarity") or "vector_similarity")
    rerank_applied = bool(getattr(retrieval_result, "rerank_applied", False))

    items: List[EvidenceItem] = []
    for idx, chunk in enumerate(chunks):
        rank = idx + 1
        raw_score = _score_at(result_scores, idx)
        vector_score = raw_score if (not rerank_applied and score_type == "vector_similarity") else None
        rrf_score = raw_score if (not rerank_applied and score_type == "rrf") else None
        rerank_score = _score_at(rerank_scores, idx) if rerank_applied else None
        item = chunk_to_evidence_item(
            chunk,
            vector_score=vector_score,
            rrf_score=rrf_score,
            rerank_score=rerank_score,
            retrieval_round=getattr(matched_round, "round_id", None),
            retrieval_query=result_query or getattr(matched_round, "retrieval_query", None),
            rank_before_rerank=rank,
            rank_after_rerank=rank if rerank_scores else None,
            text_preview_chars=text_preview_chars,
        )
        items.append(item)

    return items


def _item_rank_score(item: EvidenceItem) -> Tuple[float, float]:
    """作用：给压缩排序提供稳定分数，优先 rerank_score，其次 rrf_score / vector_score。"""
    primary = item.rerank_score
    if primary is None:
        primary = item.rrf_score if item.rrf_score is not None else item.vector_score
    secondary = item.rrf_score if item.rrf_score is not None else item.vector_score
    return (
        float(primary) if primary is not None else float("-inf"),
        float(secondary) if secondary is not None else float("-inf"),
    )


def compress_evidence_items(
    items: List[EvidenceItem],
    *,
    max_chunks_in_packet: int = DEFAULT_MAX_CHUNKS_IN_PACKET,
    dedupe_by_source: bool = False,
) -> List[EvidenceItem]:
    """
    作用：
    - 默认保持 retrieve_node 的排序，只截断 max_chunks_in_packet。
    - 可选按 source_id 去重，保留每个 source 中分数最高的 chunk。
    """
    if not dedupe_by_source:
        return list(items)[: int(max_chunks_in_packet)]

    best_by_source: Dict[str, EvidenceItem] = {}
    for item in items:
        key = item.source_id or item.chunk_id
        current = best_by_source.get(key)
        if current is None or _item_rank_score(item) > _item_rank_score(current):
            best_by_source[key] = item

    compressed = list(best_by_source.values())
    compressed.sort(key=_item_rank_score, reverse=True)
    return compressed[: int(max_chunks_in_packet)]


def build_evidence_packet(
    retrieval_result: RetrievalResult,
    retrieval_rounds: Optional[List[RetrievalRound]] = None,
    *,
    route: Optional[str] = None,
    max_chunks_in_packet: int = DEFAULT_MAX_CHUNKS_IN_PACKET,
    dedupe_by_source: bool = False,
    text_preview_chars: int = DEFAULT_TEXT_PREVIEW_CHARS,
) -> EvidencePacket:
    """作用：构建 EvidencePacket，并写入 source / score / gap 诊断。"""
    raw_items = build_evidence_items(
        retrieval_result,
        retrieval_rounds=retrieval_rounds,
        text_preview_chars=text_preview_chars,
    )
    items = compress_evidence_items(
        raw_items,
        max_chunks_in_packet=max_chunks_in_packet,
        dedupe_by_source=dedupe_by_source,
    )

    compression_policy = (
        f"dedupe_by_source=true,max_chunks_in_packet={max_chunks_in_packet}"
        if dedupe_by_source
        else f"preserve_retrieval_order,max_chunks_in_packet={max_chunks_in_packet}"
    )

    return EvidencePacket(
        items=items,
        source_coverage=summarize_source_coverage(items),
        answer_bearing_summary=summarize_answer_bearing(items),
        score_summary=summarize_scores(items),
        compression_policy=compression_policy,
        known_gaps=detect_known_gaps(items, route=route),
    )
