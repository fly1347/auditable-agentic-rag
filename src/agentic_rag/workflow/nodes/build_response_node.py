"""
作用：
- 提供 D-full Step 15 的最小 build response workflow node。
- 不重构主回答生成逻辑。
- 只把 state.extra["uncertainty"] / state.uncertainty 透传到 response 或 debug payload。
- 追加 BUILD_RESPONSE step。

整体结构：
1. 读取已有 response 或从 WorkflowState 构造最小 payload。
2. 附加 uncertainty 字段。
3. 记录 response_uncertainty。
4. 追加 BUILD_RESPONSE step。
"""

from __future__ import annotations

import time
from dataclasses import asdict, is_dataclass
from types import SimpleNamespace
from typing import Any, Dict, Optional

from agentic_rag.evidence.uncertainty import uncertainty_report_to_dict

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


def _enum_value(value: Any) -> Optional[str]:
    """作用：安全读取 Enum.value 或字符串。"""
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _get_uncertainty_dict(state: Any) -> Dict[str, Any]:
    """作用：从 state / extra 中读取 uncertainty dict。"""
    extra = _get_extra(state)

    if isinstance(extra.get("uncertainty"), dict):
        return extra["uncertainty"]

    report = getattr(state, "uncertainty", None)
    if report is not None:
        return uncertainty_report_to_dict(report)

    return {
        "level": "low",
        "reasons": [],
        "missing_info": [],
        "safe_answer_boundary": None,
        "next_steps": [],
    }


def _append_step(
    state: Any,
    *,
    decision: str,
    input_summary: Dict[str, Any],
    output_summary: Dict[str, Any],
    duration_ms: float,
) -> None:
    """作用：追加 BUILD_RESPONSE step。"""
    steps = getattr(state, "steps", None)
    if steps is None:
        setattr(state, "steps", [])
        steps = getattr(state, "steps")

    step_type = "BUILD_RESPONSE"
    if WorkflowStepType is not None and hasattr(WorkflowStepType, "BUILD_RESPONSE"):
        step_type = getattr(WorkflowStepType, "BUILD_RESPONSE")

    if WorkflowStep is not None:
        try:
            steps.append(
                WorkflowStep(
                    step_type=step_type,
                    name="build_response_node",
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
            name="build_response_node",
            decision=decision,
            input_summary=input_summary,
            output_summary=output_summary,
            duration_ms=duration_ms,
            model_call=None,
            error=None,
        )
    )


def _workflow_trace_summary(state: Any) -> list[dict[str, Any]]:
    """作用：生成轻量 workflow trace，避免复制大字段。"""
    out: list[dict[str, Any]] = []
    for step in getattr(state, "steps", []) or []:
        row = _to_dict(step)
        out.append(
            {
                "step_type": _enum_value(row.get("step_type")),
                "name": row.get("name"),
                "decision": row.get("decision"),
                "duration_ms": row.get("duration_ms"),
            }
        )
    return out


def _minimal_payload_from_state(state: Any, *, include_debug: bool) -> Dict[str, Any]:
    """作用：从 WorkflowState 构造最小兼容 response payload。"""
    extra = _get_extra(state)
    payload: Dict[str, Any] = {
        "request_id": getattr(state, "request_id", None),
        "answer": extra.get("answer") or getattr(state, "answer", ""),
        "citations": extra.get("citations") or getattr(state, "citations", []),
        "path": extra.get("path") or _enum_value(getattr(state, "route", None)),
        "refused": bool(extra.get("refused", getattr(state, "refused", False))),
        "refused_reason": extra.get("refused_reason") or getattr(state, "refused_reason", None),
        "uncertainty": _get_uncertainty_dict(state),
    }

    if include_debug:
        payload["workflow_trace"] = _workflow_trace_summary(state)
        payload["evidence_packet"] = _to_dict(getattr(state, "evidence_packet", None))
        payload["sufficiency"] = extra.get("sufficiency")
        payload["citation_support"] = extra.get("citation_support")
        payload["conflict_detection"] = extra.get("conflict_detection")

    return payload


def _attach_uncertainty(response: Any, uncertainty: Dict[str, Any]) -> Any:
    """作用：把 uncertainty 附加到 dict 或对象 response；失败时原样返回。"""
    if response is None:
        return None

    if isinstance(response, dict):
        response["uncertainty"] = uncertainty
        extra = response.get("extra")
        if isinstance(extra, dict):
            extra["uncertainty"] = uncertainty
        return response

    try:
        setattr(response, "uncertainty", uncertainty)
    except Exception:
        pass

    return response


def run_build_response_node(
    state: Any,
    *,
    response: Any = None,
    include_debug: bool = False,
) -> Any:
    """
    运行最小 response 组装节点。

    response=None 时返回一个最小 dict。
    response 非空时只做 uncertainty 透传，不改原有主字段。
    """
    started = time.time()
    extra = _get_extra(state)
    uncertainty = _get_uncertainty_dict(state)

    if response is None:
        output = _minimal_payload_from_state(state, include_debug=include_debug)
    else:
        output = _attach_uncertainty(response, uncertainty)

    extra["response_uncertainty"] = uncertainty

    _append_step(
        state,
        decision="response_built",
        input_summary={
            "response_provided": response is not None,
            "include_debug": include_debug,
            "uncertainty_level": uncertainty.get("level"),
        },
        output_summary={
            "uncertainty_level": uncertainty.get("level"),
            "has_uncertainty": bool(uncertainty),
        },
        duration_ms=(time.time() - started) * 1000.0,
    )

    return output


# 兼容短命名。
build_response_node = run_build_response_node
