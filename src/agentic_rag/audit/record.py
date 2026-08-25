from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


def _stable_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return str(value)


def hash_text(text: Any) -> str:
    raw = str(text or "")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _plain(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_plain(item) for item in value]
    return value


def _get_attr(obj: Any, name: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _get_query_from_response(response: Any) -> str:
    execution_record = _get_attr(response, "execution_record", {}) or {}
    if isinstance(execution_record, dict) and execution_record.get("query") is not None:
        return str(execution_record.get("query") or "")
    workflow_trace = _get_attr(response, "workflow_trace", {}) or {}
    if isinstance(workflow_trace, dict):
        return str(workflow_trace.get("query") or "")
    return ""


def _summarize_user_context(policy_trace: Dict[str, Any]) -> Dict[str, Any]:
    access = dict(policy_trace.get("access_policy") or {})
    return {
        "user_id": access.get("user_id"),
        "roles": list(access.get("roles") or []),
        "groups": list(access.get("groups") or []),
        "tenant_id": access.get("tenant_id"),
    }


def _extract_prompt_chunk_ids(generation_context: Dict[str, Any]) -> List[str]:
    ids: List[str] = []

    for key in ("prompt_chunk_ids", "used_chunk_ids"):
        value = generation_context.get(key)
        if isinstance(value, list):
            ids.extend(str(item) for item in value if str(item).strip())

    chunks = generation_context.get("chunks_in_prompt")
    if isinstance(chunks, list):
        for item in chunks:
            if isinstance(item, dict):
                chunk_id = item.get("chunk_id") or item.get("id")
                if chunk_id:
                    ids.append(str(chunk_id))

    prompt_acl = generation_context.get("prompt_chunk_acl")
    if isinstance(prompt_acl, list):
        for item in prompt_acl:
            if isinstance(item, dict):
                chunk_id = item.get("chunk_id")
                if chunk_id:
                    ids.append(str(chunk_id))

    out: List[str] = []
    seen: set[str] = set()
    for item in ids:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def _extract_citation_chunk_ids(response: Any) -> List[str]:
    ids: List[str] = []
    citations = _get_attr(response, "citations", []) or []
    for item in citations:
        chunk_id = _get_attr(item, "chunk_id", None)
        if chunk_id:
            ids.append(str(chunk_id))
    return ids


def _summarize_model_calls(usage: Dict[str, Any]) -> Dict[str, Any]:
    calls = list(usage.get("model_calls") or [])
    summarized_calls: List[Dict[str, Any]] = []
    for call in calls:
        if not isinstance(call, dict):
            continue
        summarized_calls.append(
            {
                "role": call.get("role"),
                "stage": call.get("stage"),
                "provider": call.get("provider"),
                "configured_model": call.get("configured_model"),
                "resolved_model": call.get("resolved_model"),
                "latency_ms": call.get("latency_ms"),
                "prompt_tokens": call.get("prompt_tokens"),
                "completion_tokens": call.get("completion_tokens"),
                "total_tokens": call.get("total_tokens"),
                "estimated_cost_usd": call.get("estimated_cost_usd"),
                "api_error": call.get("api_error"),
                "timeout": call.get("timeout"),
                "error_type": call.get("error_type"),
            }
        )

    return {
        "schema_version": usage.get("schema_version"),
        "authoritative": usage.get("authoritative"),
        "totals": dict(usage.get("totals") or {}),
        "coverage": dict(usage.get("coverage") or {}),
        "model_call_count": len(summarized_calls),
        "model_calls": summarized_calls,
    }


def _summarize_timing(timing: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "actual_total_ms": timing.get("actual_total_ms"),
        "service_total_ms": timing.get("service_total_ms"),
        "outer_elapsed_ms": timing.get("outer_elapsed_ms"),
        "workflow_total_ms": timing.get("workflow_total_ms"),
        "legacy_pipeline_ms": timing.get("legacy_pipeline_ms"),
        "queue_wait_ms": timing.get("queue_wait_ms"),
        "api_overhead_ms": timing.get("api_overhead_ms"),
        "serialization_ms": timing.get("serialization_ms"),
        "steps": dict(timing.get("steps") or {}),
    }


@dataclass
class AuditRecord:
    request_id: str
    ts: float
    user_context_summary: Dict[str, Any] = field(default_factory=dict)
    query_hash: str = ""
    policy_decisions: Dict[str, Any] = field(default_factory=dict)
    prompt_chunk_ids: List[str] = field(default_factory=list)
    citation_chunk_ids: List[str] = field(default_factory=list)
    model_call_summary: Dict[str, Any] = field(default_factory=dict)
    timing_summary: Dict[str, Any] = field(default_factory=dict)
    final_status: str = ""
    refused_reason: Optional[str] = None
    audit_schema_version: str = "phase_e_audit_v1"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def build_audit_record_from_debug_response(response: Any) -> AuditRecord:
    request_id = str(_get_attr(response, "request_id", "") or "")
    policy_trace = _plain(_get_attr(response, "policy_trace", {}) or {})
    generation_context = _plain(_get_attr(response, "generation_context", {}) or {})
    usage = _plain(_get_attr(response, "usage", {}) or {})
    timing = _plain(_get_attr(response, "timing", {}) or {})

    query = _get_query_from_response(response)
    refused = bool(_get_attr(response, "refused", False))
    refused_reason = _get_attr(response, "refused_reason", None)

    return AuditRecord(
        request_id=request_id,
        ts=float(time.time()),
        user_context_summary=_summarize_user_context(policy_trace if isinstance(policy_trace, dict) else {}),
        query_hash=hash_text(query),
        policy_decisions=policy_trace if isinstance(policy_trace, dict) else {},
        prompt_chunk_ids=_extract_prompt_chunk_ids(generation_context if isinstance(generation_context, dict) else {}),
        citation_chunk_ids=_extract_citation_chunk_ids(response),
        model_call_summary=_summarize_model_calls(usage if isinstance(usage, dict) else {}),
        timing_summary=_summarize_timing(timing if isinstance(timing, dict) else {}),
        final_status="refused" if refused else "answered",
        refused_reason=str(refused_reason) if refused_reason else None,
    )
