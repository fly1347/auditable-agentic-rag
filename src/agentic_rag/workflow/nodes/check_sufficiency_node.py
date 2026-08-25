"""
作用：
- 提供 D-full Step 10 的 check sufficiency workflow node。
- 消费 state.evidence_packet，而不是直接消费 chunks preview。
- 输出结构化 SufficiencyResult，并写入 state.sufficiency_rounds / state.extra["sufficiency"]。
- judge 异常时 fail-close：记录错误并返回 INSUFFICIENT，不启用 degraded_answer。

整体结构：
1. 读取 query / question_type / route / EvidencePacket。
2. 调用 judge_sufficiency_with_evidence_packet。
3. 写入 SufficiencyRound 与 CHECK_SUFFICIENCY WorkflowStep。
4. 记录 ModelCallRecord 与 judge identity。
"""

from __future__ import annotations

import time
from dataclasses import asdict, is_dataclass
from typing import Any, Callable, Dict, Optional, Tuple

from agentic_rag.control.sufficiency import (
    SufficiencyJudgeError,
    SufficiencyJudgeTimeout,
    judge_sufficiency_with_evidence_packet,
)
from agentic_rag.observability.model_identity import ModelIdentity
from agentic_rag.observability.observability_record import ModelCallRecord
from agentic_rag.workflow.workflow_state import (
    ErrorRecord,
    EvidencePacket,
    SufficiencyResult,
    SufficiencyRound,
    WorkflowRoute,
    WorkflowState,
    WorkflowStep,
    WorkflowStepType,
)


JudgeFunc = Callable[..., Tuple[SufficiencyResult, float, ModelCallRecord]]


def _enum_value(value: Any) -> Optional[str]:
    """作用：安全读取 Enum.value 或字符串。"""
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _packet_to_dict(packet: EvidencePacket) -> Dict[str, Any]:
    """作用：把 EvidencePacket 转成可序列化 dict。"""
    if is_dataclass(packet):
        return asdict(packet)
    return dict(packet)  # type: ignore[arg-type]


def _result_to_dict(result: SufficiencyResult) -> Dict[str, Any]:
    """作用：把 SufficiencyResult 转成可序列化 dict。"""
    if is_dataclass(result):
        data = asdict(result)
    else:
        data = dict(result)  # type: ignore[arg-type]

    identity = getattr(result, "model_identity", None)
    if isinstance(identity, ModelIdentity):
        data["model_identity"] = identity.to_dict()
    return data


def _empty_packet() -> EvidencePacket:
    """作用：在 state.evidence_packet 缺失时构造空 EvidencePacket。"""
    return EvidencePacket(
        items=[],
        source_coverage={"item_count": 0, "distinct_source_count": 0},
        known_gaps=["missing_evidence_packet", "empty_evidence_packet"],
        compression_policy="empty_packet_from_check_sufficiency_node",
    )


def _fail_close_result(exc: Exception) -> SufficiencyResult:
    """作用：judge 异常时构造保守 INSUFFICIENT 结果。"""
    return SufficiencyResult(
        verdict="INSUFFICIENT",
        confidence="low",
        missing_evidence=["sufficiency_judge_failed"],
        supporting_evidence_ids=[],
        conflict_evidence_ids=[],
        reason=f"fail_close due to {type(exc).__name__}: {exc}",
        model_identity=ModelIdentity(),
    )


def _error_record(exc: Exception) -> ErrorRecord:
    """作用：将异常转成 workflow error record。"""
    return ErrorRecord(
        error_type=type(exc).__name__,
        message=str(exc),
        retryable=isinstance(exc, SufficiencyJudgeTimeout),
        details={"failure_policy": "fail_close"},
    )


def _model_call_for_error(exc: Exception, elapsed_ms: float) -> ModelCallRecord:
    """作用：judge 异常时记录一次失败模型调用。"""
    return ModelCallRecord(
        role="sufficiency_judge",
        identity=ModelIdentity(),
        latency_ms=float(elapsed_ms),
        timeout=isinstance(exc, SufficiencyJudgeTimeout),
        api_error=True,
        error_type=type(exc).__name__,
    )


def run_check_sufficiency_node(
    state: WorkflowState,
    *,
    instruction: Optional[str] = None,
    judge_func: JudgeFunc = judge_sufficiency_with_evidence_packet,
) -> SufficiencyResult:
    """
    作用：
    - 执行 EvidencePacket 版 sufficiency node。
    - judge_func 可注入，用于 smoke / 单测中避免真实联网。
    """
    t0 = time.time()

    packet = state.evidence_packet if state.evidence_packet is not None else _empty_packet()
    question_type = _enum_value(state.question_type)
    route = _enum_value(state.route)

    input_summary = {
        "query": state.query,
        "question_type": question_type,
        "route": route,
        "evidence_item_count": len(list(packet.items or [])),
        "known_gaps": list(packet.known_gaps or []),
        "instruction": instruction,
    }

    error: Optional[ErrorRecord] = None
    try:
        result, judge_ms, model_call = judge_func(
            query=str(state.query),
            evidence_packet=packet,
            question_type=question_type,
            route=route,
            instruction=instruction,
        )
        decision = str(result.verdict or "INSUFFICIENT")
    except SufficiencyJudgeError as exc:
        judge_ms = float((time.time() - t0) * 1000.0)
        result = _fail_close_result(exc)
        model_call = _model_call_for_error(exc, elapsed_ms=judge_ms)
        error = _error_record(exc)
        decision = "fail_close:INSUFFICIENT"
        if "sufficiency_judge_failure" not in state.failure_attribution:
            state.failure_attribution.append("sufficiency_judge_failure")

    total_ms = float((time.time() - t0) * 1000.0)

    round_record = SufficiencyRound(
        round_id=len(state.sufficiency_rounds) + 1,
        input_summary=input_summary,
        result=result,
    )
    state.sufficiency_rounds.append(round_record)

    if state.observability is not None and model_call is not None:
        state.observability.add_model_call(model_call)

    result_dict = _result_to_dict(result)
    state.extra["sufficiency"] = {
        "round_id": round_record.round_id,
        "input_summary": dict(input_summary),
        "result": result_dict,
        "judge_ms": float(judge_ms),
        "total_ms": float(total_ms),
        "failure_policy": "fail_close",
    }
    state.extra["sufficiency_result"] = str(result.verdict or "INSUFFICIENT")
    state.extra["sufficiency_confidence"] = result.confidence
    state.extra["sufficiency_missing_evidence"] = list(result.missing_evidence or [])
    state.extra["sufficiency_supporting_evidence_ids"] = list(result.supporting_evidence_ids or [])
    state.extra["sufficiency_conflict_evidence_ids"] = list(result.conflict_evidence_ids or [])

    state.steps.append(
        WorkflowStep(
            step_type=WorkflowStepType.CHECK_SUFFICIENCY,
            name="check_sufficiency_with_evidence_packet",
            decision=decision,
            input_summary=input_summary,
            output_summary={
                "verdict": result.verdict,
                "confidence": result.confidence,
                "missing_evidence": list(result.missing_evidence or []),
                "supporting_evidence_ids": list(result.supporting_evidence_ids or []),
                "conflict_evidence_ids": list(result.conflict_evidence_ids or []),
                "reason": result.reason,
                "judge_identity": result.model_identity.to_dict()
                if isinstance(result.model_identity, ModelIdentity)
                else None,
                "failure_policy": "fail_close",
            },
            duration_ms=total_ms,
            model_call=model_call,
            error=error,
        )
    )

    return result


# 兼容短命名。
check_sufficiency_node = run_check_sufficiency_node
