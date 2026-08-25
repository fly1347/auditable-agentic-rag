"""
文件作用：
1）提供 Phase D-full Step 7 的 classify query workflow node；
2）把 classifier 输出写入 WorkflowState.question_type / answerability / extra["classifier"]；
3）追加 CLASSIFY_QUERY 类型的 WorkflowStep；
4）当前只负责分类记录，不覆盖 state.route，不直接执行 retrieve / generate。

整体结构：
1）定义 run_classify_query_node(...)；
2）调用 agentic_rag.control.classifier.classify_query；
3）把结果映射到 WorkflowState 与 WorkflowStep。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from agentic_rag.control.classifier import ClassificationResult, classify_query
from agentic_rag.observability.model_identity import ModelIdentity
from agentic_rag.observability.observability_record import ModelCallRecord
from agentic_rag.workflow.workflow_state import (
    Answerability,
    QuestionType,
    WorkflowState,
    WorkflowStep,
    WorkflowStepType,
)


def _to_question_type(value: str) -> Optional[QuestionType]:
    """作用：安全转换 QuestionType。"""
    try:
        return QuestionType(str(value).strip().upper())
    except Exception:
        return None


def _to_answerability(value: str) -> Optional[Answerability]:
    """作用：安全转换 Answerability。"""
    try:
        return Answerability(str(value).strip().upper())
    except Exception:
        return None


def _model_call_from_dict(raw: Dict[str, Any]) -> ModelCallRecord:
    """作用：把 classifier model_call dict 还原为 ModelCallRecord。"""
    identity_raw = raw.get("identity")
    identity_dict = dict(identity_raw) if isinstance(identity_raw, dict) else {}

    def _safe_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except Exception:
            return None

    def _safe_float(value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None

    return ModelCallRecord(
        role=str(raw.get("role") or "classifier"),
        identity=ModelIdentity.from_metadata(identity_dict),
        prompt_tokens=_safe_int(raw.get("prompt_tokens")),
        completion_tokens=_safe_int(raw.get("completion_tokens")),
        reasoning_tokens=_safe_int(raw.get("reasoning_tokens")),
        total_tokens=_safe_int(raw.get("total_tokens")),
        latency_ms=_safe_float(raw.get("latency_ms")),
        estimated_cost_usd=_safe_float(raw.get("estimated_cost_usd")),
        timeout=bool(raw.get("timeout", False)),
        api_error=bool(raw.get("api_error", False)),
        http_status=_safe_int(raw.get("http_status")),
        error_type=str(raw.get("error_type")) if raw.get("error_type") is not None else None,
    )


def run_classify_query_node(
    state: WorkflowState,
    optional_history: Optional[List[Dict[str, Any]]] = None,
    enabled: Optional[bool] = None,
) -> ClassificationResult:
    """
    作用：
    - 执行 D-full Step 7 分类节点。
    - 写入 state.question_type / state.answerability / state.extra["classifier"]。
    - 不覆盖 state.route，不触发 final reject。
    - 追加 CLASSIFY_QUERY step。
    """
    result = classify_query(
        query=str(state.query),
        optional_history=optional_history,
        enabled=enabled,
    )

    state.question_type = _to_question_type(result.question_type)
    state.answerability = _to_answerability(result.answerability)
    result_dict = result.to_dict()
    state.extra["classifier"] = result_dict
    state.extra["classifier_route_candidate"] = result.route_candidate
    state.extra["classifier_route_policy"] = result.route_policy

    raw_model_call = result_dict.get("model_call")
    model_call = _model_call_from_dict(raw_model_call) if isinstance(raw_model_call, dict) else None
    if state.observability is not None and model_call is not None:
        state.observability.model_calls.append(model_call)

    state.steps.append(
        WorkflowStep(
            step_type=WorkflowStepType.CLASSIFY_QUERY,
            name="llm_question_classifier",
            decision=result.route_candidate,
            input_summary={
                "query": state.query,
                "enabled": enabled,
            },
            output_summary={
                "question_type": result.question_type,
                "answerability": result.answerability,
                "route_candidate": result.route_candidate,
                "route_policy": result.route_policy,
                "confidence": result.confidence,
                "reason": result.reason,
                "classifier_used": result.classifier_used,
                "fallback_used": bool(result.fallback_used),
                "fallback_reason": result.fallback_reason,
                "actual_route_preserved": state.route.value if state.route else None,
                "model_call_present": model_call is not None,
            },
            duration_ms=float(result.duration_ms),
            model_call=model_call,
            error=None,
        )
    )

    return result


# 兼容更短的 node 调用命名。
classify_query_node = run_classify_query_node

