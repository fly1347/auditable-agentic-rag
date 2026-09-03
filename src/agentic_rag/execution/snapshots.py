"""
程序作用：
为运行时与评估侧生成确定性的证据快照和提示快照，使实际可见上下文能够被稳定哈希、回放和审计。

整体结构：
1）_snapshot_id 根据规范 JSON 生成稳定快照标识；
2）_chunk_payload 统一 chunk、得分、偏移和 ACL 字段；
3）build_evidence_snapshot 与 build_prompt_snapshot 分别冻结候选证据和实际提示内容。
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from agentic_rag.types import Chunk, RetrievalResult


def _snapshot_id(prefix: str, payload: Mapping[str, Any]) -> str:
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:20]}"


def _chunk_payload(chunk: Chunk, score: float | None, rank: int, score_type: str) -> dict[str, Any]:
    metadata = dict(chunk.metadata or {})
    acl = dict(metadata.get("acl") or {}) if isinstance(metadata.get("acl"), dict) else {}
    return {
        "rank": int(rank),
        "chunk_id": str(chunk.chunk_id),
        "source_id": str(chunk.source_id),
        "offset_start": int(chunk.offset_start),
        "offset_end": int(chunk.offset_end),
        "score": float(score) if score is not None else None,
        "score_type": str(score_type),
        "text": str(chunk.text),
        "acl": {
            "visibility": acl.get("visibility"),
            "tenant_id": acl.get("tenant_id"),
            "source_id": acl.get("source_id") or str(chunk.source_id),
        },
    }


# 冻结一次检索中的候选与选中证据。
def build_evidence_snapshot(result: RetrievalResult) -> dict[str, Any]:
    selected = [
        _chunk_payload(
            chunk,
            result.scores[index - 1] if index - 1 < len(result.scores) else None,
            index,
            str(getattr(result, "score_type", "vector_similarity")),
        )
        for index, chunk in enumerate(result.chunks, start=1)
    ]
    payload: dict[str, Any] = {
        "query": str(result.query),
        "score_type": str(getattr(result, "score_type", "vector_similarity")),
        "retrieval_events": list(getattr(result, "retrieval_events", []) or []),
        "merge_trace": dict(getattr(result, "merge_trace", {}) or {}),
        "rerank_applied": bool(result.rerank_applied),
        "rerank_model": result.rerank_model,
        "evidence_selected": selected,
    }
    return {"snapshot_id": _snapshot_id("ev", payload), **payload}


def build_prompt_snapshot(
    chunks_in_prompt: Sequence[Mapping[str, Any]],
    *,
    evidence_snapshot_id: str,
    query: str = "",
    prompt_template: str = "",
    rendered_prompt: str = "",
) -> dict[str, Any]:
    visible: list[dict[str, Any]] = []
    for index, raw in enumerate(chunks_in_prompt, start=1):
        text = str(raw.get("text") or "")
        offset_start = int(raw.get("offset_start") or 0)
        source_offset_end = int(raw.get("offset_end") or offset_start + len(text))
        visible.append(
            {
                "marker": f"E{index}",
                "rank": index,
                "chunk_id": str(raw.get("chunk_id") or ""),
                "source_id": str(raw.get("source_id") or ""),
                "source_offset_start": offset_start,
                "source_offset_end": source_offset_end,
                "visible_offset_start": offset_start,
                "visible_offset_end": min(source_offset_end, offset_start + len(text)),
                "visible_char_count": len(text),
                "text": text,
                "visibility": dict(raw.get("acl") or {}).get("visibility")
                if isinstance(raw.get("acl"), Mapping)
                else None,
            }
        )
    template_hash = hashlib.sha256(str(prompt_template).encode("utf-8")).hexdigest()
    rendered_hash = hashlib.sha256(str(rendered_prompt).encode("utf-8")).hexdigest()
    payload: dict[str, Any] = {
        "evidence_snapshot_id": str(evidence_snapshot_id),
        "citation_contract": "evidence_marker_v1",
        "query": str(query),
        "prompt_template_sha256": template_hash,
        "rendered_prompt_sha256": rendered_hash,
        "rendered_prompt": str(rendered_prompt),
        "visible_evidence": visible,
    }
    return {"snapshot_id": _snapshot_id("prompt", payload), **payload}


__all__ = ["build_evidence_snapshot", "build_prompt_snapshot"]
