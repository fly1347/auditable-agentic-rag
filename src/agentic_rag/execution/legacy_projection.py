"""
程序作用：
把历史 Answer 结构中的答案、检索、引用、步骤和模型用量投影到 CER，同时保留缺失字段的真实状态。

整体结构：
1）辅助函数把 dataclass、chunk 和模型调用转换成普通字典；
2）aggregate_model_call_usage 按“未知不等于 0”的原则汇总用量；
3）project_answer_into_record 将历史 Answer 写入 CER，并补充对应执行事件。
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Iterable

from agentic_rag.execution.record import CanonicalExecutionRecord


def _plain(value: Any) -> Any:
    if is_dataclass(value):
        return {key: _plain(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


def _chunk_item(chunk: Any, score: Any = None, rank: int | None = None) -> dict[str, Any]:
    metadata = dict(getattr(chunk, "metadata", {}) or {})
    item = {
        "chunk_id": str(getattr(chunk, "chunk_id", "")),
        "source_id": str(getattr(chunk, "source_id", "")),
        "offset_start": int(getattr(chunk, "offset_start", 0)),
        "offset_end": int(getattr(chunk, "offset_end", 0)),
        "section_path": metadata.get("section_path"),
    }
    if score is not None:
        item["score"] = float(score)
    if rank is not None:
        item["rank"] = int(rank)
    return item


def _model_calls(flags: dict[str, Any]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []
    for key in ("sufficiency_model_calls", "rewrite_model_calls", "subquery_model_calls"):
        for call in list(flags.get(key, []) or []):
            if isinstance(call, dict):
                calls.append(dict(call))
    generator_call = flags.get("generator_model_call")
    if isinstance(generator_call, dict):
        calls.append(dict(generator_call))
    for index, call in enumerate(calls, start=1):
        identity = call.pop("identity", None)
        if isinstance(identity, dict):
            for key, value in identity.items():
                call.setdefault(str(key), value)
        call.setdefault("index", index)
        call.setdefault("stage", call.get("role"))
    return calls


def aggregate_model_call_usage(calls: list[dict[str, Any]]) -> dict[str, Any]:
    """汇总模型调用用量，缺失的 Token 明细保持为空，不擅自记成 0。"""
    token_fields = (
        "prompt_tokens", "completion_tokens", "reasoning_tokens",
        "cached_tokens", "cache_write_tokens", "total_tokens",
    )
    usage: dict[str, Any] = {
        "model_call_count": len(calls),
        "llm_call_count": len(calls),
    }
    for field in token_fields:
        observed = [
            int(value)
            for call in calls
            if (value := call.get(field)) is not None
            and not isinstance(value, bool)
            and isinstance(value, (int, float))
        ]
        unknown_count = len(calls) - len(observed)
        observed_sum = sum(observed)
        usage[field] = observed_sum if not unknown_count else None
        usage[f"{field}_observed_sum"] = observed_sum
        usage[f"{field}_unknown_call_count"] = unknown_count
    numeric_costs = [
        float(value)
        for call in calls
        if (value := call.get("estimated_cost_usd")) is not None
        and not isinstance(value, bool)
        and isinstance(value, (int, float))
    ]
    unknown_cost_count = len(calls) - len(numeric_costs)
    observed_cost_sum = float(sum(numeric_costs))
    usage["estimated_cost_usd"] = observed_cost_sum if not unknown_cost_count else None
    usage["estimated_cost_usd_observed_sum"] = observed_cost_sum
    usage["estimated_cost_usd_unknown_call_count"] = unknown_cost_count
    if not calls:
        usage["cost_observation"] = "not_applicable_no_model_calls"
    elif not unknown_cost_count:
        usage["cost_observation"] = "full"
    elif numeric_costs:
        usage["cost_observation"] = "partial"
    else:
        usage["cost_observation"] = "not_observed"
    return usage


def project_answer_into_record(record: CanonicalExecutionRecord, answer: Any) -> CanonicalExecutionRecord:
    flags = dict(getattr(answer, "flags", {}) or {})
    refused = bool(flags.get("refused", False))
    actual_route = str(flags.get("actual_agentic_path") or flags.get("first_route_path") or "UNKNOWN")
    record.route = {
        "actual_route": actual_route,
        "route_source": "legacy_pipeline",
        "first_route_keyword": flags.get("first_route_keyword"),
        "second_route": flags.get("second_route_path"),
        "rewritten_query": flags.get("rewritten_query"),
        "subqueries": [
            value for value in (flags.get("decompose_query_a"), flags.get("decompose_query_b")) if value
        ],
    }

    chunks = list(getattr(answer, "used_chunks", []) or [])
    final_pool = [_chunk_item(chunk, rank=index) for index, chunk in enumerate(chunks, start=1)]
    retrieval_events = list(flags.get("retrieval_events", []) or [])
    if retrieval_events:
        record.retrieval = {
            "observation_level": "per_query_candidates",
            "events": retrieval_events,
        }
    else:
        record.retrieval = {
            "observation_level": "legacy_final_pool",
            "rounds": [{
                "round_id": 1,
                "query": record.query,
                "duration_ms": flags.get("first_retrieval_ms"),
                "candidates": final_pool,
            }],
        }
        if flags.get("second_retrieval_ms"):
            record.retrieval["rounds"].append({
                "round_id": 2,
                "query": flags.get("rewritten_query") or record.query,
                "duration_ms": flags.get("second_retrieval_ms"),
                "candidates": [],
                "unobserved_fields": ["per_query_candidates"],
            })
    record.rerank = {
        "enabled": bool(flags.get("rerank_enabled", False)),
        "triggered": bool(flags.get("selective_rerank_triggered", False)),
        "before_source_ids": list(flags.get("selective_rerank_before_source_ids", []) or []),
        "after_source_ids": list(flags.get("selective_rerank_after_source_ids", []) or []),
    }
    merge_trace = dict(flags.get("merge_trace", {}) or {})
    record.merge = merge_trace or {
        "strategy": "legacy_original_first_truncate",
        "final_pool": final_pool,
        "unobserved_fields": ["per_query_contributions", "pre_dedupe_candidates"],
    }

    generation_context = dict(flags.get("generation_context", {}) or {})
    prompt_chunks = list(generation_context.get("chunks_in_prompt", []) or [])
    prompt_snapshot = dict(flags.get("prompt_snapshot", {}) or {})
    prompt_visible = []
    for item in prompt_chunks:
        if not isinstance(item, dict):
            continue
        prompt_visible.append(
            {
                "chunk_id": item.get("chunk_id"),
                "source_id": item.get("source_id"),
                "offset_start": item.get("offset_start"),
                "offset_end": item.get("offset_end"),
                "visible_char_count": item.get("char_len"),
                "text": item.get("text"),
            }
        )
    citations = [_plain(item) for item in list(getattr(answer, "citations", []) or [])]
    retrieved = [
        candidate
        for event in retrieval_events
        if isinstance(event, dict)
        for candidate in list(event.get("candidates", []) or [])
        if isinstance(candidate, dict)
    ]
    evidence_snapshot = dict(flags.get("evidence_snapshot", {}) or {})
    selected = list(evidence_snapshot.get("evidence_selected", []) or []) or final_pool
    record.evidence = {
        "snapshot_id": evidence_snapshot.get("snapshot_id"),
        "retrieved": retrieved or final_pool,
        "reranked": final_pool if flags.get("rerank_enabled") else [],
        "selected": selected,
        "prompt_visible": list(prompt_snapshot.get("visible_evidence", []) or []) or prompt_visible,
        "cited": citations,
    }
    record.prompt = {
        "snapshot_id": prompt_snapshot.get("snapshot_id") or flags.get("prompt_snapshot_id"),
        "evidence_snapshot_id": prompt_snapshot.get("evidence_snapshot_id"),
        "citation_contract": prompt_snapshot.get("citation_contract"),
        "query": prompt_snapshot.get("query"),
        "prompt_template_sha256": prompt_snapshot.get("prompt_template_sha256"),
        "rendered_prompt_sha256": prompt_snapshot.get("rendered_prompt_sha256"),
        "rendered_prompt": prompt_snapshot.get("rendered_prompt"),
        "visible_evidence": list(prompt_snapshot.get("visible_evidence", []) or []) or prompt_visible,
        "max_chunks": generation_context.get("max_chunks_in_prompt"),
        "max_chars_per_chunk": generation_context.get("max_chars_per_chunk"),
    }
    record.sufficiency = {
        "first": flags.get("first_sufficiency_result"),
        "second": flags.get("second_sufficiency_result"),
        "evidence_ref": flags.get("sufficiency_evidence_ref"),
        "first_contract": flags.get("first_sufficiency_contract"),
        "second_contract": flags.get("second_sufficiency_contract"),
    }
    record.model_calls = _model_calls(flags)
    record.usage = aggregate_model_call_usage(record.model_calls)
    record.timing = {
        **dict(record.timing or {}),
        "pipeline_total_ms": flags.get("pipeline_total_ms"),
        "retrieval_ms": getattr(answer, "retrieval_ms", None),
        "generation_ms": getattr(answer, "generation_ms", None),
        "llm_generate_ms": getattr(answer, "llm_generate_ms", None),
        "first_retrieval_ms": flags.get("first_retrieval_ms"),
        "second_retrieval_ms": flags.get("second_retrieval_ms"),
        "first_sufficiency_ms": flags.get("first_sufficiency_ms"),
        "second_sufficiency_ms": flags.get("second_sufficiency_ms"),
        "query_rewrite_ms": flags.get("query_rewrite_ms"),
    }
    record.policy = {**dict(record.policy or {}), **dict(flags.get("policy_trace", {}) or {})}

    if retrieval_events:
        for event in retrieval_events:
            record.append_event("RETRIEVAL", stage=str(event.get("query_role") or "query"), payload={
                "round_id": event.get("round_id"),
                "query_role": event.get("query_role"),
                "candidate_count": len(list(event.get("candidates", []) or [])),
            })
        record.append_event("MERGE", stage="rrf", payload={
            "strategy": record.merge.get("strategy"),
            "final_count": len(list(record.merge.get("final_order", []) or [])),
        })
    if evidence_snapshot:
        record.append_event("EVIDENCE_SELECTED", stage="evidence", payload={
            "snapshot_id": evidence_snapshot.get("snapshot_id"),
            "count": len(selected),
        })
    if prompt_snapshot:
        record.append_event("PROMPT_BUILT", stage="generator", payload={
            "snapshot_id": prompt_snapshot.get("snapshot_id"),
            "visible_count": len(list(prompt_snapshot.get("visible_evidence", []) or [])),
        })
    if flags.get("citation_parse") is not None:
        record.append_event("CITATION_PARSE", stage="generator", payload=dict(flags.get("citation_parse") or {}))
        record.append_event("CITATION_VALIDATE", stage="generator", payload={
            "validity": flags.get("citation_validity"),
            "failures": list(flags.get("citation_failures", []) or []),
        })

    for step in list(getattr(answer, "agentic_steps", []) or []):
        step_name = str(getattr(step, "step", "UNKNOWN"))
        if refused and step_name.lower() in {"generate", "generate_answer"}:
            continue
        event_type = _event_type_for_step(step_name)
        record.append_event(
            event_type,
            stage=step_name,
            duration_ms=getattr(step, "duration_ms", None),
            payload={"output": str(getattr(step, "output", ""))},
        )

    if refused:
        reason = str(flags.get("refuse_reason") or flags.get("reason") or "refused")
        record.append_event("REFUSAL", stage="outcome", payload={"reason": reason})
        record.finish("REFUSED", answer=str(getattr(answer, "answer_text", "")), refusal_reason=reason, citations=[])
    else:
        record.append_event("ANSWER_BUILT", stage="outcome", payload={"citation_count": len(citations)})
        record.finish("ANSWERED", answer=str(getattr(answer, "answer_text", "")), refusal_reason=None, citations=citations, verified_citations=citations if not flags.get("missing_citations_fallback") else [])
    return record


def _event_type_for_step(step_name: str) -> str:
    value = step_name.lower()
    if "security" in value:
        return "QUERY_SAFETY_CHECK"
    if "route" in value:
        return "PLAN_ROUTE"
    if "decompose" in value or "subquer" in value:
        return "SUBQUERY_GENERATED"
    if "retriev" in value:
        return "RETRIEVAL"
    if "rerank" in value:
        return "RERANK"
    if "sufficiency" in value:
        return "SUFFICIENCY"
    if "rewrite" in value:
        return "REWRITE"
    if "generate" in value:
        return "MODEL_CALL"
    if "reject" in value:
        return "REFUSAL"
    return "LEGACY_STEP"


__all__ = ["aggregate_model_call_usage", "project_answer_into_record"]
