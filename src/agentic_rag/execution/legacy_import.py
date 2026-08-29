"""
程序作用：
把 Phase E 调试 JSONL 尽可能无损地导入 CER；历史产物未记录的候选、合并贡献、答案质量或 grounding 结果一律明确标成未观测，不凭空补值。

整体结构：
1）辅助函数规范化历史字典、列表、模型调用和提示证据；
2）import_phase_e_row 把单条历史回归结果转换成 CER；
3）import_phase_e_rows 批量导入并保持原始记录顺序。
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping

from agentic_rag.execution.record import CanonicalExecutionRecord, ExecutionEvent


NOT_OBSERVED = "not_observed"
NOT_APPLICABLE = "not_applicable"


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _present(value: Any, *, default: Any = NOT_OBSERVED) -> Any:
    return default if value is None or value == "" else value


def _model_call(call: Mapping[str, Any], index: int) -> dict[str, Any]:
    row = dict(call)
    identity = _dict(row.pop("identity", {}))
    return {
        "index": int(index),
        "role": _present(row.get("role")),
        "stage": _present(row.get("stage")),
        "provider": _present(row.get("provider", identity.get("provider"))),
        "configured_model": _present(
            row.get("configured_model", identity.get("configured_model"))
        ),
        "resolved_model": _present(
            row.get("resolved_model", identity.get("resolved_model"))
        ),
        "latency_ms": _present(row.get("latency_ms")),
        "prompt_tokens": _present(row.get("prompt_tokens")),
        "completion_tokens": _present(row.get("completion_tokens")),
        "reasoning_tokens": _present(row.get("reasoning_tokens")),
        "cached_tokens": _present(row.get("cached_tokens")),
        "cache_write_tokens": _present(row.get("cache_write_tokens")),
        "total_tokens": _present(row.get("total_tokens")),
        "estimated_cost_usd": _present(row.get("estimated_cost_usd")),
        "http_status": _present(row.get("http_status")),
        "api_error": bool(row.get("api_error", False)),
        "timeout": bool(row.get("timeout", False)),
        "error_type": _present(row.get("error_type")),
        "fallback_used": _present(row.get("fallback_used")),
        # 这些字段只保留在内部 CER 中，对外投影会将其移除。
        "endpoint": row.get("endpoint", identity.get("endpoint")),
        "api_key_hash": row.get("api_key_hash", identity.get("api_key_hash")),
    }


def _final_pool(response: Mapping[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for rank, item in enumerate(_list(response.get("retrieved_chunks")), start=1):
        chunk = _dict(item)
        out.append(
            {
                "rank": rank,
                "query_role": NOT_OBSERVED,
                "chunk_id": _present(chunk.get("chunk_id")),
                "source_id": _present(chunk.get("source_id")),
                "offset_start": _present(chunk.get("offset_start")),
                "offset_end": _present(chunk.get("offset_end")),
                "vector_score": NOT_OBSERVED,
                "rerank_score": NOT_OBSERVED,
                "selected": True,
                "text_preview": chunk.get("text_preview"),
            }
        )
    return out


def _prompt_items(response: Mapping[str, Any]) -> list[dict[str, Any]]:
    generation = _dict(response.get("generation_context"))
    out: list[dict[str, Any]] = []
    for item in _list(generation.get("chunks_in_prompt")):
        chunk = _dict(item)
        out.append(
            {
                "rank": _present(chunk.get("rank")),
                "chunk_id": _present(chunk.get("chunk_id")),
                "source_id": _present(chunk.get("source_id")),
                "source_path": _present(chunk.get("source_path")),
                "section_path": _present(chunk.get("section_path")),
                "vector_score": _present(chunk.get("vector_score")),
                "rerank_score": _present(chunk.get("rerank_score")),
                "visible_char_count": _present(chunk.get("char_len")),
                "text_preview": str(chunk.get("text") or "")[:240],
            }
        )
    return out


def _behavior_pass(expected: Any, refused: bool) -> Any:
    value = str(expected or "").strip().lower()
    if value in {"answer", "answered"}:
        return not refused
    if value in {"refuse", "refused", "reject"}:
        return refused
    return NOT_OBSERVED


def import_phase_e_row(raw: Mapping[str, Any]) -> CanonicalExecutionRecord:
    """把一条冻结的 Phase E 回归结果转换成历史 CER。"""
    row = dict(raw)
    response = _dict(row.get("response"))
    flags = _dict(response.get("flags"))
    workflow = _dict(response.get("workflow_trace"))
    retrieval_diagnostics = _dict(response.get("retrieval_diagnostics"))
    sufficiency = _dict(response.get("sufficiency_diagnostics"))
    usage = _dict(response.get("usage"))
    timing = _dict(response.get("timing"))
    rerank = _dict(response.get("rerank"))
    generation = _dict(response.get("generation_context"))
    final_pool = _final_pool(response)
    prompt_items = _prompt_items(response)

    qid = str(row.get("qid") or NOT_OBSERVED)
    request_id = response.get("request_id") or f"legacy:{row.get('case_key') or qid}"
    record = CanonicalExecutionRecord(
        schema_version="1.0.0",
        identity={
            "request_id": request_id,
            "run_id": workflow.get("run_id"),
            "qid": qid,
            "case_key": row.get("case_key"),
            "set_name": row.get("set_name"),
            "session_id": response.get("session_id"),
        },
        provenance={
            "profile": "baseline",
            "engine": "legacy_phase_e_import",
            "source_schema": "phase_e_debug_response",
            "source_index": row.get("index"),
            "historical_import": True,
            "code_ref": NOT_OBSERVED,
            "config_hash": NOT_OBSERVED,
            "index_build_id": NOT_OBSERVED,
            "corpus_hash": NOT_OBSERVED,
            "acl_registry_version": NOT_OBSERVED,
        },
        principal={
            "principal_id": NOT_OBSERVED,
            "auth_mode": NOT_OBSERVED,
            "roles": NOT_OBSERVED,
            "groups": NOT_OBSERVED,
            "tenant_id": NOT_OBSERVED,
        },
        query=str(row.get("query") or workflow.get("query") or ""),
        started_at=NOT_OBSERVED,
    )
    record.completed_at = NOT_OBSERVED
    record.policy = _dict(flags.get("policy_trace"))
    record.policy["observation"] = (
        "historical response projection; trusted principal and request policy snapshot were not recorded"
    )

    route = response.get("path") or workflow.get("route") or flags.get("actual_agentic_path")
    record.route = {
        "question_type": _present(workflow.get("question_type")),
        "planned_route": _present(workflow.get("route")),
        "actual_route": _present(route),
        "route_source": "legacy_workflow_projection",
        "route_reason": NOT_OBSERVED,
        "classifier_fallback": NOT_OBSERVED,
        "direct_query": record.query,
        "subqueries": [
            value
            for value in (flags.get("decompose_query_a"), flags.get("decompose_query_b"))
            if value
        ],
        "rewrite_query": _present(flags.get("rewritten_query")),
    }

    diagnostic_rounds = _list(retrieval_diagnostics.get("retrieval_rounds"))
    rounds: list[dict[str, Any]] = []
    for index, raw_round in enumerate(diagnostic_rounds, start=1):
        item = _dict(raw_round)
        rounds.append(
            {
                "round_id": item.get("round_id", index),
                "query": _present(item.get("retrieval_query")),
                "route": _present(item.get("route")),
                "topk": _present(item.get("topk")),
                "hit_count": _present(item.get("hit_count")),
                "duration_ms": _present(
                    timing.get("steps", {}).get(
                        "first_retrieval_ms" if index == 1 else "second_retrieval_ms"
                    )
                    if isinstance(timing.get("steps"), Mapping)
                    else None
                ),
                "candidates": final_pool if index == len(diagnostic_rounds) else [],
                "observation_level": "legacy_final_pool"
                if index == len(diagnostic_rounds)
                else "metadata_only",
                "unobserved_fields": [
                    "per_query_candidates",
                    "query_role",
                    "candidate_vector_scores",
                ],
            }
        )
    if not rounds:
        rounds.append(
            {
                "round_id": 1,
                "query": record.query,
                "route": _present(route),
                "topk": len(final_pool),
                "hit_count": len(final_pool),
                "duration_ms": NOT_OBSERVED,
                "candidates": final_pool,
                "observation_level": "legacy_final_pool",
                "unobserved_fields": ["per_query_candidates", "candidate_vector_scores"],
            }
        )
    record.retrieval = {
        "rounds": rounds,
        "final_pool": final_pool,
        "observation_limit": (
            "historical artifact exposes the final returned pool, not direct/subquery TopK events"
        ),
    }
    record.rerank = {
        "enabled": bool(retrieval_diagnostics.get("rerank_enabled", False)),
        "triggered": bool(rerank.get("triggered", False)),
        "reason": _present(rerank.get("reason")),
        "model": _present(retrieval_diagnostics.get("rerank_model")),
        "latency_ms": _present(rerank.get("latency_ms")),
        "before_source_ids": _list(flags.get("selective_rerank_before_source_ids")),
        "after_source_ids": _list(flags.get("selective_rerank_after_source_ids")),
        "before_candidates": NOT_OBSERVED,
        "after_candidates": NOT_OBSERVED,
    }
    record.merge = {
        "strategy": "legacy_original_first_truncate",
        "final_order": [item.get("chunk_id") for item in final_pool],
        "pre_dedupe_candidates": NOT_OBSERVED,
        "per_query_contributions": NOT_OBSERVED,
    }
    citations = _list(response.get("citations"))
    record.evidence = {
        "retrieved": final_pool,
        "reranked": NOT_OBSERVED,
        "selected": final_pool,
        "prompt_visible": prompt_items,
        "cited": citations,
        "observation_limit": "selected evidence is inferred only from the historical returned pool",
    }
    record.prompt = {
        "snapshot_id": NOT_OBSERVED,
        "max_chunks": _present(generation.get("max_chunks_in_prompt")),
        "max_chars_per_chunk": _present(generation.get("max_chars_per_chunk")),
        "context_char_count": _present(generation.get("prompt_context_char_count")),
        "visible_evidence": prompt_items,
        "prompt_text": NOT_OBSERVED,
    }
    record.sufficiency = {
        "first": _present(sufficiency.get("first_sufficiency_result")),
        "second": _present(
            sufficiency.get("second_sufficiency_result"),
            default=NOT_APPLICABLE if len(rounds) < 2 else NOT_OBSERVED,
        ),
        "first_ms": _present(sufficiency.get("first_sufficiency_ms")),
        "second_ms": _present(sufficiency.get("second_sufficiency_ms")),
        "judge_error": _present(sufficiency.get("sufficiency_judge_error")),
        "evidence_snapshot_ref": NOT_OBSERVED,
    }

    calls = [_model_call(call, idx) for idx, call in enumerate(_list(usage.get("model_calls")), 1)]
    record.model_calls = calls
    record.usage = {
        **_dict(usage.get("totals")),
        "coverage": _dict(usage.get("coverage")),
        "authoritative": bool(usage.get("authoritative", False)),
    }
    record.timing = timing

    refused = bool(response.get("refused", False))
    actual_status = workflow.get("final_status") or ("REFUSED" if refused else "ANSWERED")
    expected_path = str(row.get("expected_agentic_path") or "").strip()
    behavior_pass = _behavior_pass(row.get("expected_behavior"), refused)
    path_pass: Any = (
        str(route).upper() == expected_path.upper() if expected_path else NOT_APPLICABLE
    )
    record.evaluation = {
        "dataset_class": "derived_in_domain_regression",
        "expected_behavior": _present(row.get("expected_behavior")),
        "expected_path": expected_path or NOT_APPLICABLE,
        "behavior_pass": behavior_pass,
        "path_pass": path_pass,
        "answer_quality": NOT_OBSERVED,
        "expected_evidence": NOT_OBSERVED,
        "prompt_evidence": NOT_OBSERVED,
        "citation_validity": NOT_OBSERVED,
        "final_pass": NOT_OBSERVED,
        "drift": NOT_OBSERVED,
        "http_status": _present(row.get("http_status")),
    }
    if row.get("error") is not None:
        record.errors.append(
            {
                "stage": "historical_run",
                "error_type": "legacy_error",
                "message": str(row.get("error")),
                "retryable": NOT_OBSERVED,
            }
        )
    for item in _list(workflow.get("steps")):
        step = _dict(item)
        duration = step.get("duration_ms")
        record.events.append(
            ExecutionEvent(
                sequence=len(record.events) + 1,
                event_type="LEGACY_WORKFLOW_STEP",
                timestamp=NOT_OBSERVED,
                stage=str(step.get("name") or step.get("step_type") or NOT_OBSERVED),
                duration_ms=float(duration) if isinstance(duration, (int, float)) else None,
                payload={
                "step_type": step.get("step_type"),
                "decision": step.get("decision"),
                "historical_projection": True,
                },
            )
        )
    record.outcome = {
        "status": str(actual_status),
        "answer": response.get("answer"),
        "refused": refused,
        "refusal_reason": response.get("refused_reason"),
        "citations": citations,
        "verified_citations": NOT_OBSERVED,
        "degraded": bool(response.get("degraded", False)),
        "degraded_reasons": _list(response.get("degraded_reasons")),
    }
    return record


def import_phase_e_rows(rows: Iterable[Mapping[str, Any]]) -> list[CanonicalExecutionRecord]:
    return [import_phase_e_row(row) for row in rows]


__all__ = [
    "NOT_APPLICABLE",
    "NOT_OBSERVED",
    "import_phase_e_row",
    "import_phase_e_rows",
]
