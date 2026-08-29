"""
程序作用：
基于 CER 中已经记录的执行事实计算相互独立的评估断言，避免从答案文本反推未观测信号。

整体结构：
1）定义 pass、fail、not_observed、not_applicable 四种状态；
2）辅助函数规范化映射、来源与断言明细；
3）evaluate_record 分别评估行为、证据、引用、路由、安全、错误和资源预算。
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from agentic_rag.execution.record import CanonicalExecutionRecord


PASS = "pass"
FAIL = "fail"
NOT_OBSERVED = "not_observed"
NOT_APPLICABLE = "not_applicable"


def _mappings(value: Any) -> list[dict[str, Any]]:
    return [dict(item) for item in list(value or []) if isinstance(item, Mapping)]


def _result(status: str, **detail: Any) -> dict[str, Any]:
    return {"status": status, **detail}


def _source_ids(items: Sequence[Mapping[str, Any]]) -> set[str]:
    return {str(item.get("source_id")) for item in items if item.get("source_id")}


# 对一条 CER 的各评估维度分别给出状态与依据。
def evaluate_record(
    record: CanonicalExecutionRecord,
    case: Mapping[str, Any],
    *,
    max_total_ms: float | None = None,
    max_total_tokens: int | None = None,
    max_cost_usd: float | None = None,
) -> dict[str, Any]:
    expected_behavior = str(case.get("expected_behavior") or "answer").strip().lower()
    expected_behavior = "reject" if expected_behavior in {"reject", "refuse", "refused"} else "answer"
    actual_status = str(record.outcome.get("status") or "")
    actual_behavior = "reject" if actual_status == "REFUSED" else "answer" if actual_status == "ANSWERED" else "error"
    behavior = _result(
        PASS if expected_behavior == actual_behavior else FAIL,
        expected=expected_behavior,
        actual=actual_behavior,
    )

    expected_sources = {str(item) for item in list(case.get("expected_evidence") or [])}
    selected = _mappings(record.evidence.get("selected"))
    prompt_visible = _mappings(record.prompt.get("visible_evidence"))
    if expected_behavior == "reject":
        expected_evidence = _result(NOT_APPLICABLE)
        prompt_evidence = _result(NOT_APPLICABLE)
    elif not expected_sources:
        expected_evidence = _result(NOT_OBSERVED, reason="case_has_no_expected_evidence")
        prompt_evidence = _result(NOT_OBSERVED, reason="case_has_no_expected_evidence")
    else:
        selected_sources = _source_ids(selected)
        prompt_sources = _source_ids(prompt_visible)
        expected_evidence = _result(
            PASS if expected_sources.issubset(selected_sources) else FAIL,
            expected=sorted(expected_sources),
            observed=sorted(selected_sources),
            missing=sorted(expected_sources - selected_sources),
        )
        prompt_evidence = _result(
            PASS if expected_sources.issubset(prompt_sources) else FAIL,
            expected=sorted(expected_sources),
            observed=sorted(prompt_sources),
            missing=sorted(expected_sources - prompt_sources),
        )

    citations = _mappings(record.outcome.get("citations"))
    verified = _mappings(record.outcome.get("verified_citations"))
    prompt_chunk_ids = {str(item.get("chunk_id")) for item in prompt_visible if item.get("chunk_id")}
    cited_chunk_ids = {str(item.get("chunk_id")) for item in citations if item.get("chunk_id")}
    citation_failures = sorted(cited_chunk_ids - prompt_chunk_ids)
    if expected_behavior == "reject":
        citation_validity = _result(NOT_APPLICABLE)
    else:
        citation_validity = _result(
            PASS if citations and len(verified) == len(citations) and not citation_failures else FAIL,
            parsed_count=len(citations),
            verified_count=len(verified),
            non_visible_chunk_ids=citation_failures,
        )

    expected_path = str(case.get("expected_agentic_path") or "").strip().upper()
    actual_path = str(record.route.get("actual_route") or "").strip().upper()
    route_failures: list[str] = []
    if expected_path and actual_path != expected_path:
        route_failures.append("expected_path_mismatch")
    if actual_path not in {"DIRECT", "DECOMPOSE"}:
        route_failures.append("unknown_actual_route")
    if actual_path == "DECOMPOSE":
        events = _mappings(record.retrieval.get("events"))
        roles = {str(item.get("query_role")) for item in events}
        if not {"original", "subquery_a", "subquery_b"}.issubset(roles):
            route_failures.append("decompose_query_contributions_missing")
        if str(record.merge.get("strategy")) != "rrf":
            route_failures.append("decompose_merge_not_rrf")
    if record.merge.get("scope") == "round_union" and record.merge.get("second_round_overwrites_first") is not False:
        route_failures.append("round_union_contract_missing")
    route_invariants = _result(
        PASS if not route_failures else FAIL,
        actual_path=actual_path,
        expected_path=expected_path or NOT_APPLICABLE,
        failures=route_failures,
    )

    query_safety = dict(record.policy.get("query_safety") or {})
    safety_allowed = query_safety.get("allowed")
    if not isinstance(safety_allowed, bool) and query_safety.get("checked") is True:
        refusal_recommended = query_safety.get("refusal_recommended")
        unsafe_or_private = query_safety.get("unsafe_or_private")
        if isinstance(refusal_recommended, bool) and isinstance(unsafe_or_private, bool):
            safety_allowed = not (refusal_recommended or unsafe_or_private)
    if safety_allowed is False:
        security_ok = actual_status == "REFUSED" and not record.model_calls
        security_policy = _result(
            PASS if security_ok else FAIL,
            safety_allowed=False,
            stopped_before_model_calls=not record.model_calls,
        )
    elif safety_allowed is True:
        security_policy = _result(PASS, safety_allowed=True)
    else:
        security_policy = _result(NOT_OBSERVED, reason="query_safety_snapshot_missing_or_incomplete")

    errors = _result(
        PASS if not record.errors and actual_status != "ERROR" else FAIL,
        count=len(record.errors),
        error_types=[str(item.get("error_type")) for item in record.errors],
    )

    limits = {
        "total_ms": max_total_ms,
        "total_tokens": max_total_tokens,
        "cost_usd": max_cost_usd,
    }
    observed = {
        "total_ms": record.timing.get("service_total_ms") or record.timing.get("actual_total_ms"),
        "total_tokens": record.usage.get("total_tokens"),
        "cost_usd": record.usage.get("estimated_cost_usd"),
    }
    budget_failures: list[str] = []
    budget_observations = 0
    for key, limit in limits.items():
        if limit is None:
            continue
        value = observed.get(key)
        if value in (None, "", NOT_OBSERVED):
            budget_failures.append(f"{key}_not_observed")
            continue
        budget_observations += 1
        if float(value) > float(limit):
            budget_failures.append(f"{key}_exceeded")
    resource_budget = (
        _result(NOT_APPLICABLE, limits=limits, observed=observed)
        if all(value is None for value in limits.values())
        else _result(PASS if not budget_failures else FAIL, limits=limits, observed=observed, failures=budget_failures)
    )

    answer_quality = (
        _result(NOT_APPLICABLE, reason="expected_refusal")
        if expected_behavior == "reject"
        else _result(NOT_OBSERVED, reason="requires human or quality evaluator")
    )
    dimensions = {
        "behavior": behavior,
        "answer_quality": answer_quality,
        "expected_evidence": expected_evidence,
        "prompt_evidence": prompt_evidence,
        "citation_validity": citation_validity,
        "route_invariants": route_invariants,
        "security_policy": security_policy,
        "errors": errors,
        "resource_budget": resource_budget,
    }
    hard_gate_names = [
        "behavior", "expected_evidence", "prompt_evidence", "citation_validity",
        "route_invariants", "security_policy", "errors", "resource_budget",
    ]
    blocking = [
        name for name in hard_gate_names
        if dimensions[name]["status"] == FAIL
    ]
    unobserved_hard_gates = [
        name for name in hard_gate_names
        if dimensions[name]["status"] == NOT_OBSERVED
    ]
    quality_pass = dimensions["answer_quality"]["status"] in {PASS, NOT_APPLICABLE}
    result = {
        "schema_version": "1.0.0",
        "dimensions": dimensions,
        "hard_gate_pass": not blocking,
        "hard_gate_complete": not unobserved_hard_gates,
        "blocking_dimensions": blocking,
        "unobserved_hard_gate_dimensions": unobserved_hard_gates,
        "release_ready": not blocking and not unobserved_hard_gates and quality_pass,
    }
    record.evaluation = result
    return result


__all__ = [
    "FAIL", "NOT_APPLICABLE", "NOT_OBSERVED", "PASS", "evaluate_record",
]
