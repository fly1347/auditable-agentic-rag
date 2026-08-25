"""
D-full Step 14 detect conflicts workflow node.

作用：
- 将 evidence.conflict.detect_conflicts 包装成 Workflow node；
- 条件触发 conflict detection；
- 写入 state.extra["conflict_detection"] 与 state.extra["conflicts"]；
- 追加 DETECT_CONFLICTS step；
- detector 失败时 skip_with_log，不阻塞主链路。

整体结构：
1. 从 WorkflowState 读取 evidence_packet / question_type / sufficiency verdict。
2. 调用 rule-based conflict detector。
3. 写回 state.extra。
4. 追加 workflow step。
"""

from __future__ import annotations

import time
from types import SimpleNamespace
from typing import Any, Dict, Optional

from agentic_rag.evidence.conflict import detect_conflicts

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


def _enum_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _get_sufficiency_verdict(state: Any) -> Optional[str]:
    extra = _get_extra(state)
    suff = _safe_dict(extra.get("sufficiency"))
    result = _safe_dict(suff.get("result"))
    if result.get("verdict"):
        return str(result.get("verdict"))

    rounds = getattr(state, "sufficiency_rounds", None)
    if rounds:
        last = rounds[-1]
        result_obj = getattr(last, "result", None)
        verdict = getattr(result_obj, "verdict", None)
        if verdict:
            return _enum_value(verdict)

    return None


def _get_question_type(state: Any) -> Optional[str]:
    value = getattr(state, "question_type", None)
    if value:
        return _enum_value(value)

    extra = _get_extra(state)
    classifier = _safe_dict(extra.get("classifier"))
    if classifier.get("question_type"):
        return str(classifier.get("question_type"))

    return None


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

    step_type = "DETECT_CONFLICTS"
    if WorkflowStepType is not None and hasattr(WorkflowStepType, "DETECT_CONFLICTS"):
        step_type = getattr(WorkflowStepType, "DETECT_CONFLICTS")

    if WorkflowStep is not None:
        try:
            step = WorkflowStep(
                step_type=step_type,
                name="detect_conflicts_node",
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
            name="detect_conflicts_node",
            decision=decision,
            input_summary=input_summary,
            output_summary=output_summary,
            duration_ms=duration_ms,
            model_call=None,
            error=error,
        )
    )


def run_detect_conflicts_node(
    state: Any,
    *,
    enabled: bool = True,
    force: bool = False,
    max_conflicts: int = 5,
) -> Dict[str, Any]:
    """
    运行 conflict detection。

    enabled=False 时记录 skipped_disabled。
    force=True 用于专项 smoke，不建议在线默认使用。
    """
    started = time.time()
    extra = _get_extra(state)

    if not enabled:
        report = {
            "triggered": False,
            "trigger_reason": "disabled",
            "conflicts": [],
            "conflict_count": 0,
            "distinct_sources_in_packet": 0,
            "skipped_reason": "disabled",
            "detector": "rule_based_conflict_detector",
        }
        extra["conflict_detection"] = report
        extra["conflicts"] = []
        _append_step(
            state,
            decision="skipped_disabled",
            input_summary={"enabled": False},
            output_summary=report,
            duration_ms=(time.time() - started) * 1000.0,
        )
        return report

    evidence_packet = getattr(state, "evidence_packet", None)
    question_type = _get_question_type(state)
    sufficiency_verdict = _get_sufficiency_verdict(state)

    try:
        report_obj = detect_conflicts(
            evidence_packet=evidence_packet,
            question_type=question_type,
            sufficiency_verdict=sufficiency_verdict,
            force=force,
            max_conflicts=max_conflicts,
        )
        report = report_obj.to_dict()
        extra["conflict_detection"] = report
        extra["conflicts"] = report.get("conflicts", [])

        decision = "triggered" if report.get("triggered") else "skipped"
        _append_step(
            state,
            decision=decision,
            input_summary={
                "enabled": enabled,
                "force": force,
                "question_type": question_type,
                "sufficiency_verdict": sufficiency_verdict,
            },
            output_summary={
                "triggered": report.get("triggered"),
                "trigger_reason": report.get("trigger_reason"),
                "conflict_count": report.get("conflict_count"),
                "distinct_sources_in_packet": report.get("distinct_sources_in_packet"),
                "skipped_reason": report.get("skipped_reason"),
            },
            duration_ms=(time.time() - started) * 1000.0,
        )
        return report

    except Exception as exc:  # noqa: BLE001
        report = {
            "triggered": False,
            "trigger_reason": "detector_error",
            "conflicts": [],
            "conflict_count": 0,
            "distinct_sources_in_packet": 0,
            "skipped_reason": "skip_with_log",
            "detector": "rule_based_conflict_detector",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
        extra["conflict_detection"] = report
        extra["conflicts"] = []
        _append_step(
            state,
            decision="skip_with_log",
            input_summary={
                "enabled": enabled,
                "force": force,
                "question_type": question_type,
                "sufficiency_verdict": sufficiency_verdict,
            },
            output_summary=report,
            duration_ms=(time.time() - started) * 1000.0,
            error={"error_type": type(exc).__name__, "message": str(exc)},
        )
        return report
