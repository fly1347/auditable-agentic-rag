"""
作用：
- 提供 D-full Step 15 的 BUILD_UNCERTAINTY workflow node。
- 从 WorkflowState / state.extra 读取 sufficiency、conflicts、citation_support、EvidencePacket。
- 调用 evidence.uncertainty.build_uncertainty_report。
- 写入 state.uncertainty 与 state.extra["uncertainty"]。
- 追加 BUILD_UNCERTAINTY step。

整体结构：
1. 兼容性读取前序节点输出。
2. 规则聚合 UncertaintyReport。
3. 写回 WorkflowState。
4. 追加 WorkflowStep。
"""

from __future__ import annotations

import time
from dataclasses import asdict, is_dataclass
from types import SimpleNamespace
from typing import Any, Dict, Optional

from agentic_rag.evidence.uncertainty import (
    build_uncertainty_report,
    uncertainty_report_to_dict,
)

try:
    from agentic_rag.workflow.workflow_state import WorkflowStep, WorkflowStepType
except Exception:  # noqa: BLE001
    WorkflowStep = None  # type: ignore[assignment]
    WorkflowStepType = None  # type: ignore[assignment]


def _get_extra(state: Any) -> Dict[str, Any]:
    """作用：安全获取 state.extra。"""
    extra = getattr(state, "extra", None)
    if isinstance(extra, dict):
        return extra
    setattr(state, "extra", {})
    return getattr(state, "extra")


def _to_dict(value: Any) -> Dict[str, Any]:
    """作用：兼容 dict / dataclass / to_dict / SimpleNamespace-like 对象。"""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "to_dict"):
        try:
            out = value.to_dict()
            return out if isinstance(out, dict) else {}
        except Exception:
            return {}
    if hasattr(value, "__dict__"):
        try:
            return dict(value.__dict__)
        except Exception:
            return {}
    return {}


def _latest_sufficiency(state: Any) -> Any:
    """作用：优先读取 state.extra['sufficiency']，否则读取最后一轮 sufficiency_round。"""
    extra = _get_extra(state)
    if extra.get("sufficiency") is not None:
        return extra.get("sufficiency")

    rounds = getattr(state, "sufficiency_rounds", None)
    if rounds:
        return rounds[-1]

    return None


def _latest_conflicts(state: Any) -> Any:
    """作用：优先读取 conflict_detection report，其次读取 conflicts list。"""
    extra = _get_extra(state)
    if extra.get("conflict_detection") is not None:
        return extra.get("conflict_detection")
    if extra.get("conflicts") is not None:
        return extra.get("conflicts")
    return getattr(state, "conflicts", None)


def _latest_citation_support(state: Any) -> Any:
    """作用：优先读取 state.extra['citation_support']，否则读取 state.citation_support。"""
    extra = _get_extra(state)
    if extra.get("citation_support") is not None:
        return extra.get("citation_support")
    return getattr(state, "citation_support", None)


def _latest_evidence_packet(state: Any) -> Any:
    """作用：优先读取 state.evidence_packet，兜底读取 state.extra['evidence_packet']。"""
    extra = _get_extra(state)
    packet = getattr(state, "evidence_packet", None)
    if packet is not None:
        return packet
    return extra.get("evidence_packet")


def _latest_refused_reason(state: Any) -> Optional[str]:
    """作用：读取拒答原因。"""
    extra = _get_extra(state)
    value = (
        extra.get("refused_reason")
        or extra.get("refusal_reason")
        or getattr(state, "refused_reason", None)
    )
    return str(value).strip() if value else None


def _append_step(
    state: Any,
    *,
    decision: str,
    input_summary: Dict[str, Any],
    output_summary: Dict[str, Any],
    duration_ms: float,
) -> None:
    """作用：按现有 WorkflowStep 结构追加 BUILD_UNCERTAINTY step。"""
    steps = getattr(state, "steps", None)
    if steps is None:
        setattr(state, "steps", [])
        steps = getattr(state, "steps")

    step_type = "BUILD_UNCERTAINTY"
    if WorkflowStepType is not None and hasattr(WorkflowStepType, "BUILD_UNCERTAINTY"):
        step_type = getattr(WorkflowStepType, "BUILD_UNCERTAINTY")

    if WorkflowStep is not None:
        try:
            steps.append(
                WorkflowStep(
                    step_type=step_type,
                    name="build_uncertainty_node",
                    decision=decision,
                    input_summary=input_summary,
                    output_summary=output_summary,
                    duration_ms=duration_ms,
                )
            )
            return
        except TypeError:
            pass

    steps.append(
        SimpleNamespace(
            step_type=step_type,
            name="build_uncertainty_node",
            decision=decision,
            input_summary=input_summary,
            output_summary=output_summary,
            duration_ms=duration_ms,
            model_call=None,
            error=None,
        )
    )


def _input_summary(
    *,
    sufficiency: Any,
    conflicts: Any,
    citation_support: Any,
    evidence_packet: Any,
    refused_reason: Optional[str],
) -> Dict[str, Any]:
    """作用：构造 step 输入摘要，避免记录大段文本。"""
    suff_row = _to_dict(sufficiency)
    suff_result = _to_dict(suff_row.get("result")) if suff_row.get("result") is not None else suff_row

    conflict_row = _to_dict(conflicts)
    if conflict_row:
        conflict_count = conflict_row.get("conflict_count", 0)
    else:
        conflict_count = len(conflicts or []) if isinstance(conflicts, list) else 0

    citation_row = _to_dict(citation_support)
    packet_row = _to_dict(evidence_packet)

    return {
        "sufficiency_verdict": suff_result.get("verdict"),
        "sufficiency_confidence": suff_result.get("confidence"),
        "conflict_count": conflict_count,
        "citation_support_label": citation_row.get("citation_support_label"),
        "unsupported_claim_count": citation_row.get("unsupported_claim_count"),
        "known_gaps_count": len(packet_row.get("known_gaps") or []),
        "refused_reason_present": bool(refused_reason),
    }


def run_build_uncertainty_node(state: Any, *, enabled: bool = True) -> Any:
    """
    运行 uncertainty 聚合节点。

    enabled=False 时写入 low + disabled，便于 workflow 统一调用。
    """
    started = time.time()
    extra = _get_extra(state)

    if not enabled:
        report = build_uncertainty_report()
        report.reasons = ["disabled"]
        report.safe_answer_boundary = None
        report.next_steps = []

        report_dict = uncertainty_report_to_dict(report)
        setattr(state, "uncertainty", report)
        extra["uncertainty"] = report_dict
        extra["uncertainty_level"] = report.level

        _append_step(
            state,
            decision="skipped_disabled",
            input_summary={"enabled": False},
            output_summary=report_dict,
            duration_ms=(time.time() - started) * 1000.0,
        )
        return report

    sufficiency = _latest_sufficiency(state)
    conflicts = _latest_conflicts(state)
    citation_support = _latest_citation_support(state)
    evidence_packet = _latest_evidence_packet(state)
    refused_reason = _latest_refused_reason(state)

    report = build_uncertainty_report(
        sufficiency=sufficiency,
        conflicts=conflicts,
        citation_support=citation_support,
        evidence_packet=evidence_packet,
        refused_reason=refused_reason,
    )
    report_dict = uncertainty_report_to_dict(report)

    setattr(state, "uncertainty", report)
    extra["uncertainty"] = report_dict
    extra["uncertainty_level"] = report.level
    extra["missing_info"] = list(report.missing_info or [])
    extra["safe_answer_boundary"] = report.safe_answer_boundary
    extra["next_steps"] = list(report.next_steps or [])

    _append_step(
        state,
        decision=str(report.level or "low"),
        input_summary=_input_summary(
            sufficiency=sufficiency,
            conflicts=conflicts,
            citation_support=citation_support,
            evidence_packet=evidence_packet,
            refused_reason=refused_reason,
        ),
        output_summary=report_dict,
        duration_ms=(time.time() - started) * 1000.0,
    )

    return report


# 兼容短命名。
build_uncertainty_node = run_build_uncertainty_node
