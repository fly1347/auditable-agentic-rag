"""
作用：
- 提供 Phase D-full Step 8 的 plan route workflow node。
- 消费 Step 7 classifier 派生的 route_candidate / route_policy。
- 将候选路径映射为 WorkflowRoute，并写入 WorkflowState.route。
- 当前只做路径计划，不执行 retrieve / generate，不直接 final reject。

整体结构：
1. 安全读取 state.extra["classifier"] 与兼容字段。
2. 将 RouteCandidate 映射为 WorkflowRoute。
3. 写入 state.route / state.extra["route_policy"]。
4. 追加 PLAN_ROUTE 类型 WorkflowStep。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from agentic_rag.workflow.workflow_state import (
    RouteCandidate,
    RoutePolicy,
    WorkflowRoute,
    WorkflowState,
    WorkflowStep,
    WorkflowStepType,
)


def _read_classifier_fields(state: WorkflowState) -> Tuple[Optional[str], Optional[str], Dict[str, Any]]:
    """作用：从 WorkflowState.extra 中读取 classifier 派生字段。"""
    classifier = state.extra.get("classifier", {})
    classifier_dict: Dict[str, Any] = dict(classifier) if isinstance(classifier, dict) else {}

    route_candidate = (
        state.extra.get("classifier_route_candidate")
        or classifier_dict.get("route_candidate")
    )
    route_policy = (
        state.extra.get("classifier_route_policy")
        or classifier_dict.get("route_policy")
    )

    return (
        str(route_candidate).strip().upper() if route_candidate is not None else None,
        str(route_policy).strip().upper() if route_policy is not None else None,
        classifier_dict,
    )


def _candidate_to_route(route_candidate: Optional[str], fallback_route: Optional[WorkflowRoute]) -> WorkflowRoute:
    """作用：把 Step 7 route_candidate 映射为 Step 8 实际计划路径。"""
    value = str(route_candidate or "").strip().upper()

    if value == RouteCandidate.DECOMPOSE.value:
        return WorkflowRoute.DECOMPOSE
    if value == RouteCandidate.OPEN_MULTI.value:
        return WorkflowRoute.OPEN_MULTI
    if value == RouteCandidate.NEEDS_CLARIFICATION.value:
        return WorkflowRoute.NEEDS_CLARIFICATION
    if value == RouteCandidate.REJECT_CANDIDATE.value:
        return WorkflowRoute.REJECT
    if value == RouteCandidate.DIRECT.value:
        return WorkflowRoute.DIRECT

    if fallback_route is not None:
        return fallback_route
    return WorkflowRoute.DIRECT


def _normalize_route_policy(route_policy: Optional[str]) -> str:
    """作用：规范化 route_policy，缺失时使用 STRICT_SUFFICIENCY 保守记录。"""
    value = str(route_policy or "").strip().upper()
    allowed = {item.value for item in RoutePolicy}
    if value in allowed:
        return value
    return RoutePolicy.STRICT_SUFFICIENCY.value


def run_plan_route_node(state: WorkflowState) -> WorkflowRoute:
    """
    作用：
    - 消费 classifier route_candidate / route_policy。
    - 写入 state.route，作为后续 workflow 节点的实际计划路径。
    - 不执行最终拒答，也不调用检索。
    """
    previous_route = state.route
    route_candidate, route_policy_raw, classifier_dict = _read_classifier_fields(state)

    planned_route = _candidate_to_route(
        route_candidate=route_candidate,
        fallback_route=previous_route,
    )
    route_policy = _normalize_route_policy(route_policy_raw)

    state.route = planned_route
    state.extra["route_policy"] = route_policy
    state.extra["planned_route_source"] = "classifier_route_candidate" if route_candidate else "fallback_existing_route"
    state.extra["planned_route_candidate"] = route_candidate
    state.extra["planned_route"] = planned_route.value

    state.steps.append(
        WorkflowStep(
            step_type=WorkflowStepType.PLAN_ROUTE,
            name="plan_route_from_classifier_candidate",
            decision=planned_route.value,
            input_summary={
                "query": state.query,
                "previous_route": previous_route.value if previous_route else None,
                "route_candidate": route_candidate,
                "route_policy": route_policy_raw,
                "classifier_present": bool(classifier_dict),
            },
            output_summary={
                "planned_route": planned_route.value,
                "route_policy": route_policy,
                "route_source": state.extra["planned_route_source"],
                "question_type": classifier_dict.get("question_type"),
                "answerability": classifier_dict.get("answerability"),
                "confidence": classifier_dict.get("confidence"),
                "note": "REJECT_CANDIDATE maps to route=REJECT only as a planned path; no final reject here.",
            },
            duration_ms=None,
        )
    )

    return planned_route


# 兼容短命名。
plan_route_node = run_plan_route_node
