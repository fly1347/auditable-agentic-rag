"""
D-full Step 13 citation support workflow node.

作用：
- 将 citation_support.py 的离线评估能力包装成 Workflow node；
- 从 WorkflowState 中读取 answer / citations / EvidencePacket；
- 写入 state.extra["citation_support"]；
- 追加 CHECK_CITATION_SUPPORT step；
- 默认 offline-only，不接入在线主链路。

整体结构：
1. 兼容性读取 WorkflowState 字段。
2. 调用 evaluate_citation_support。
3. 将报告写回 state.extra。
4. 尽量按现有 WorkflowStep 结构追加 step；若构造器不匹配，使用 SimpleNamespace 兜底。
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any, Dict, Optional, Sequence

from agentic_rag.evidence.citation_support import evaluate_citation_support

try:
    from agentic_rag.workflow.workflow_state import WorkflowStep, WorkflowStepType
except Exception:  # noqa: BLE001
    WorkflowStep = None  # type: ignore[assignment]
    WorkflowStepType = None  # type: ignore[assignment]


def _get_extra(state: Any) -> Dict[str, Any]:
    extra = getattr(state, "extra", None)
    if isinstance(extra, dict):
        return extra
    setattr(state, "extra", {})
    return getattr(state, "extra")


def _get_first(state: Any, keys: Sequence[str], default: Any = None) -> Any:
    extra = _get_extra(state)
    for key in keys:
        if hasattr(state, key):
            value = getattr(state, key)
            if value is not None:
                return value
        if key in extra and extra[key] is not None:
            return extra[key]
    return default


def _append_step(
    state: Any,
    *,
    decision: str,
    input_summary: Dict[str, Any],
    output_summary: Dict[str, Any],
    duration_ms: float,
    error: Optional[Dict[str, Any]] = None,
) -> None:
    steps = getattr(state, "steps", None)
    if steps is None:
        setattr(state, "steps", [])
        steps = getattr(state, "steps")

    step_type = "CHECK_CITATION_SUPPORT"
    if WorkflowStepType is not None and hasattr(WorkflowStepType, "CHECK_CITATION_SUPPORT"):
        step_type = getattr(WorkflowStepType, "CHECK_CITATION_SUPPORT")

    if WorkflowStep is not None:
        try:
            step = WorkflowStep(
                step_type=step_type,
                name="check_citation_support_node",
                decision=decision,
                input_summary=input_summary,
                output_summary=output_summary,
                duration_ms=duration_ms,
                error=error,
            )
            steps.append(step)
            return
        except TypeError:
            pass

    steps.append(
        SimpleNamespace(
            step_type=step_type,
            name="check_citation_support_node",
            decision=decision,
            input_summary=input_summary,
            output_summary=output_summary,
            duration_ms=duration_ms,
            model_call=None,
            error=error,
        )
    )


def run_check_citation_support_node(
    state: Any,
    *,
    answer: Optional[str] = None,
    citations: Optional[Sequence[Any]] = None,
    prompt_chunks: Optional[Sequence[Any]] = None,
    retrieved_chunks: Optional[Sequence[Any]] = None,
    evidence_scope: str = "actual_citations",
    enabled: bool = True,
) -> Any:
    """
    运行 citation support 检查。

    enabled=False 时只记录 skipped，便于后续 workflow/replay 统一调用。
    """
    started = time.time()
    extra = _get_extra(state)

    if not enabled:
        report = {
            "citation_support_label": "not_applicable",
            "unsupported_claim_count": 0,
            "claim_count": 0,
            "claims": [],
            "borderline_dimension": ["disabled"],
            "evidence_scope": "actual_citations",
            "evidence_count": 0,
            "notes": "citation support node disabled",
        }
        extra["citation_support"] = report
        _append_step(
            state,
            decision="skipped_disabled",
            input_summary={"enabled": False},
            output_summary=report,
            duration_ms=(time.time() - started) * 1000.0,
        )
        return report

    answer_value = answer
    if answer_value is None:
        answer_value = _get_first(
            state,
            ["answer", "final_answer", "generated_answer"],
            "",
        )

    citations_value = citations
    if citations_value is None:
        citations_value = _get_first(state, ["citations"], []) or []

    prompt_chunks_value = prompt_chunks
    if prompt_chunks_value is None:
        prompt_chunks_value = _get_first(
            state,
            ["prompt_chunks", "prompt_evidence_chunks"],
            [],
        ) or []

    retrieved_chunks_value = retrieved_chunks
    if retrieved_chunks_value is None:
        retrieved_chunks_value = _get_first(
            state,
            ["retrieved_chunks", "retrieval_results"],
            [],
        ) or []

    evidence_packet = _get_first(state, ["evidence_packet"], None)
    refused = bool(_get_first(state, ["refused"], False))
    expected_behavior = _get_first(state, ["expected_behavior"], None)

    try:
        report_obj = evaluate_citation_support(
            answer=str(answer_value or ""),
            citations=citations_value,
            prompt_chunks=prompt_chunks_value,
            retrieved_chunks=retrieved_chunks_value,
            evidence_packet=evidence_packet,
            refused=refused,
            expected_behavior=expected_behavior,
            evidence_scope="actual_citations",
        )
        report = report_obj.to_dict()
        extra["citation_support"] = report

        _append_step(
            state,
            decision="evaluated",
            input_summary={
                "answer_present": bool(answer_value),
                "citations_count": len(citations_value or []),
                "prompt_chunks_count": len(prompt_chunks_value or []),
                "retrieved_chunks_count": len(retrieved_chunks_value or []),
                "evidence_scope": "actual_citations",
            },
            output_summary={
                "citation_support_label": report.get("citation_support_label"),
                "unsupported_claim_count": report.get("unsupported_claim_count"),
                "claim_count": report.get("claim_count"),
                "borderline_dimension": report.get("borderline_dimension"),
            },
            duration_ms=(time.time() - started) * 1000.0,
        )
        return report

    except Exception as exc:  # noqa: BLE001
        report = {
            "citation_support_label": "not_applicable",
            "unsupported_claim_count": 0,
            "claim_count": 0,
            "claims": [],
            "borderline_dimension": ["node_error"],
            "evidence_scope": "actual_citations",
            "evidence_count": 0,
            "notes": f"{type(exc).__name__}: {exc}",
        }
        extra["citation_support"] = report
        _append_step(
            state,
            decision="error",
            input_summary={"evidence_scope": evidence_scope},
            output_summary=report,
            duration_ms=(time.time() - started) * 1000.0,
            error={"error_type": type(exc).__name__, "message": str(exc)},
        )
        return report
