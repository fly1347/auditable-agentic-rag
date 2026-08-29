"""
程序作用：
定义带版本的离线 D-full 评估记录，并统一模型调用、成本、来源绑定和公开投影口径。

整体结构：
1）哈希、时间、来源绑定和模型调用规范化辅助函数；
2）OfflineStageRecord 记录单个离线评估阶段；
3）OfflineEvaluationRecord 汇总逐题离线结果并提供序列化、公开脱敏能力。
"""

from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Optional

from agentic_rag.cost.pricing import estimate_usage_costs
from agentic_rag.execution.record import CanonicalExecutionRecord


STAGE_STATUSES = {"ok", "not_applicable", "not_evaluated", "error", "unknown"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_sha256(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def text_sha256(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()


def source_binding(record: CanonicalExecutionRecord) -> dict[str, Any]:
    answer = record.outcome.get("answer") or ""
    return {
        "source_cer_sha256": stable_sha256(record.to_dict()),
        "source_schema_version": record.schema_version,
        "source_request_id": record.identity.get("request_id"),
        "source_run_id": record.identity.get("run_id"),
        "source_qid": record.identity.get("qid"),
        "source_profile": record.provenance.get("profile"),
        "index_build_id": record.provenance.get("index_build_id"),
        "config_sha256": (
            record.provenance.get("config_sha256")
            or record.provenance.get("config_hash")
        ),
        "dataset_sha256": (
            record.provenance.get("dataset_sha256")
            or record.provenance.get("dataset_hash")
        ),
        "answer_sha256": text_sha256(answer),
        "evidence_snapshot_id": (
            record.prompt.get("evidence_snapshot_id")
            or record.prompt.get("snapshot_id")
            or record.evidence.get("snapshot_id")
        ),
        "prompt_sha256": record.prompt.get("rendered_prompt_sha256"),
    }


def normalize_model_call(
    raw: Optional[Mapping[str, Any]],
    *,
    qid: str,
    stage: str,
    role: str,
    index: int,
    category: str = "offline_dfull",
) -> dict[str, Any]:
    """把历史嵌套模型身份字段整理成 CER 统一的 model_call 结构。"""
    call = dict(raw or {})
    identity = dict(call.pop("identity", {}) or {})
    for key in (
        "provider",
        "backend",
        "configured_model",
        "provider_response_model",
        "resolved_model",
        "endpoint",
        "upstream_provider",
        "api_key_env",
        "api_key_hash",
        "network_tag",
        "proxy_node",
        "generator_backend",
        "provider_tag",
    ):
        if call.get(key) in (None, "") and identity.get(key) not in (None, ""):
            call[key] = identity.get(key)
    call["qid"] = qid
    call["index"] = int(index)
    call["stage"] = str(call.get("stage") or stage)
    call["role"] = str(call.get("role") or role)
    call.setdefault("api_error", False)
    call.setdefault("timeout", False)
    call["call_id"] = stable_sha256(
        {
            "category": category,
            "qid": qid,
            "index": index,
            "stage": call["stage"],
            "role": call["role"],
            "provider": call.get("provider"),
            "model": call.get("resolved_model") or call.get("configured_model"),
            "latency_ms": call.get("latency_ms"),
            "prompt_tokens": call.get("prompt_tokens"),
            "completion_tokens": call.get("completion_tokens"),
        }
    )[:24]
    return call


def _optional_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int_summary(
    calls: Iterable[Mapping[str, Any]], key: str
) -> tuple[Optional[int], int, int]:
    values = [_optional_int(call.get(key)) for call in calls]
    observed = [value for value in values if value is not None]
    observed_sum = sum(observed)
    unknown_count = len(values) - len(observed)
    complete_total = observed_sum if not unknown_count else None
    return complete_total, observed_sum, unknown_count


def price_model_calls(calls: Iterable[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    items = [dict(call) for call in calls]
    if not items:
        return [], {
            "model_call_count": 0,
            "llm_call_count": 0,
            "prompt_tokens": 0,
            "prompt_tokens_observed_sum": 0,
            "prompt_tokens_unknown_call_count": 0,
            "completion_tokens": 0,
            "completion_tokens_observed_sum": 0,
            "completion_tokens_unknown_call_count": 0,
            "reasoning_tokens": 0,
            "reasoning_tokens_observed_sum": 0,
            "reasoning_tokens_unknown_call_count": 0,
            "cached_tokens": 0,
            "cached_tokens_observed_sum": 0,
            "cached_tokens_unknown_call_count": 0,
            "cache_write_tokens": 0,
            "cache_write_tokens_observed_sum": 0,
            "cache_write_tokens_unknown_call_count": 0,
            "total_tokens": 0,
            "total_tokens_observed_sum": 0,
            "total_tokens_unknown_call_count": 0,
            "estimated_cost_usd": 0.0,
            "estimated_cost_usd_observed_sum": 0.0,
            "cost_observation": "not_applicable_no_model_calls",
            "cost_estimation": {
                "coverage": "not_applicable",
                "priced_call_count": 0,
                "unpriced_call_count": 0,
            },
        }

    priced = estimate_usage_costs({"model_calls": items, "totals": {}})
    priced_calls = list(priced.get("model_calls") or [])
    totals = dict(priced.get("totals") or {})
    for key in ("reasoning_tokens", "cached_tokens", "cache_write_tokens"):
        complete_total, observed_sum, unknown_count = _optional_int_summary(priced_calls, key)
        totals[key] = complete_total
        totals[f"{key}_observed_sum"] = observed_sum
        totals[f"{key}_unknown_call_count"] = unknown_count
    totals["model_call_count"] = len(priced_calls)
    totals["cost_estimation"] = dict(priced.get("cost_estimation") or {})
    totals["cost_observation"] = totals["cost_estimation"].get("coverage", "none")
    return priced_calls, totals


@dataclass
class OfflineStageRecord:
    name: str
    status: str
    mode: str
    duration_ms: float
    output: dict[str, Any] = field(default_factory=dict)
    model_calls: list[dict[str, Any]] = field(default_factory=list)
    error: Optional[dict[str, Any]] = None

    def __post_init__(self) -> None:
        if self.status not in STAGE_STATUSES:
            raise ValueError(f"invalid offline stage status: {self.status}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class OfflineEvaluationRecord:
    schema_version: str
    identity: dict[str, Any]
    source: dict[str, Any]
    query: str
    input_refs: dict[str, Any]
    stages: list[OfflineStageRecord]
    model_calls: list[dict[str, Any]]
    usage: dict[str, Any]
    timing: dict[str, Any]
    outcome: dict[str, Any]
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["stages"] = [stage.to_dict() for stage in self.stages]
        return data

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "OfflineEvaluationRecord":
        data = dict(raw)
        stages = [OfflineStageRecord(**dict(item)) for item in list(data.pop("stages", []) or [])]
        return cls(stages=stages, **data)

    def sanitized_dict(self) -> dict[str, Any]:
        data = copy.deepcopy(self.to_dict())
        data["query"] = "[redacted]"
        for call in data.get("model_calls", []):
            if not isinstance(call, dict):
                continue
            for key in (
                "endpoint",
                "base_url",
                "api_key",
                "api_key_env",
                "api_key_hash",
                "prompt",
                "error_message",
            ):
                call.pop(key, None)
        _drop_sensitive_evaluation_text(data.get("stages"))
        return data


def _drop_sensitive_evaluation_text(value: Any) -> None:
    sensitive_keys = {
        "query",
        "answer",
        "claim",
        "claim_a",
        "claim_b",
        "text",
        "text_preview",
        "raw_output",
        "rendered_prompt",
        "reason",
        "reasons",
        "rationale",
        "fallback_reason",
        "trigger_reason",
        "skipped_reason",
        "missing_evidence",
        "missing_info",
        "safe_answer_boundary",
        "next_steps",
        "message",
        "error_message",
    }
    if isinstance(value, dict):
        for key in list(value):
            if key in sensitive_keys:
                value[key] = "[redacted]"
            else:
                _drop_sensitive_evaluation_text(value[key])
    elif isinstance(value, list):
        for item in value:
            _drop_sensitive_evaluation_text(item)


__all__ = [
    "OfflineEvaluationRecord",
    "OfflineStageRecord",
    "normalize_model_call",
    "price_model_calls",
    "source_binding",
    "stable_sha256",
    "text_sha256",
    "utc_now",
]
