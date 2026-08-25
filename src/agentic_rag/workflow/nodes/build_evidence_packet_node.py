"""
作用：
- 提供 D-full Step 9 的 build_evidence_packet workflow node。
- 从 state.extra["retrieval_result"] 与 state.retrieval_rounds 构建 EvidencePacket。
- 写入 state.evidence_packet / state.extra["evidence_packet"]，并追加 BUILD_EVIDENCE_PACKET step。
- 当前不接 sufficiency / citation_support / conflict detection。

整体结构：
1. 读取 retrieve_node 产物。
2. 调用 evidence.packet.build_evidence_packet。
3. 将 EvidencePacket 写回 WorkflowState。
4. 记录 WorkflowStep。
"""

from __future__ import annotations

import time
from dataclasses import asdict, is_dataclass
from typing import Any, Dict, Optional

from agentic_rag.evidence.packet import build_evidence_packet
from agentic_rag.types import RetrievalResult
from agentic_rag.workflow.workflow_state import (
    EvidencePacket,
    WorkflowRoute,
    WorkflowState,
    WorkflowStep,
    WorkflowStepType,
)


def _route_value(state: WorkflowState) -> Optional[str]:
    """作用：安全读取当前 workflow route。"""
    if state.route is None:
        return None
    if isinstance(state.route, WorkflowRoute):
        return state.route.value
    return str(state.route)


def _packet_to_dict(packet: EvidencePacket) -> Dict[str, Any]:
    """作用：把 EvidencePacket 转成可序列化 dict，便于 debug / replay。"""
    if is_dataclass(packet):
        return asdict(packet)
    return dict(packet)  # type: ignore[arg-type]


def _empty_retrieval_result(state: WorkflowState) -> RetrievalResult:
    """作用：在 retrieval_result 缺失时生成空结果，保证 node fail-safe。"""
    return RetrievalResult(
        query=str(state.query),
        chunks=[],
        scores=[],
        topk=0,
        timing_ms=0.0,
    )


def run_build_evidence_packet_node(
    state: WorkflowState,
    *,
    max_chunks_in_packet: int = 5,
    dedupe_by_source: bool = False,
    text_preview_chars: int = 300,
) -> EvidencePacket:
    """
    作用：
    - 构建 EvidencePacket。
    - 对 REJECT / NEEDS_CLARIFICATION 或空检索结果输出空 EvidencePacket + known_gaps。
    """
    t0 = time.time()
    retrieval_result = state.extra.get("retrieval_result")
    if not isinstance(retrieval_result, RetrievalResult):
        retrieval_result = _empty_retrieval_result(state)

    route = _route_value(state)

    packet = build_evidence_packet(
        retrieval_result=retrieval_result,
        retrieval_rounds=list(state.retrieval_rounds or []),
        route=route,
        max_chunks_in_packet=int(max_chunks_in_packet),
        dedupe_by_source=bool(dedupe_by_source),
        text_preview_chars=int(text_preview_chars),
    )

    state.evidence_packet = packet
    state.extra["evidence_packet"] = _packet_to_dict(packet)

    state.steps.append(
        WorkflowStep(
            step_type=WorkflowStepType.BUILD_EVIDENCE_PACKET,
            name="build_evidence_packet",
            decision=f"built:{len(packet.items)}",
            input_summary={
                "query": state.query,
                "route": route,
                "retrieval_hit_count": len(list(retrieval_result.chunks or [])),
                "max_chunks_in_packet": int(max_chunks_in_packet),
                "dedupe_by_source": bool(dedupe_by_source),
            },
            output_summary={
                "item_count": len(packet.items),
                "distinct_source_count": packet.source_coverage.get("distinct_source_count"),
                "known_gaps": list(packet.known_gaps),
                "compression_policy": packet.compression_policy,
            },
            duration_ms=float((time.time() - t0) * 1000.0),
        )
    )

    return packet


# 兼容短命名。
build_evidence_packet_node = run_build_evidence_packet_node
