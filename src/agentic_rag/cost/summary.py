"""
文件作用：
1）提供 Phase E 成本汇总工具；
2）从 usage.model_calls / usage.totals 派生 per-answer cost summary；
3）用于 smoke、replay summary、后续报告，不从 answer / citation / retrieval 字段估算成本。

结构：
- build_cost_summary：汇总单条 usage；
- merge_cost_summaries：汇总多条 cost summary；
- _add_group_value：内部聚合辅助函数。
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional

from agentic_rag.cost.pricing import estimate_usage_costs


def _optional_float(value: Any) -> Optional[float]:
    """安全读取 optional float。"""

    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _add_group_value(bucket: Dict[str, float], key: Any, value: Any) -> None:
    """按 role/provider 聚合 estimated_cost_usd。"""

    amount = _optional_float(value)
    if amount is None:
        return
    label = str(key or "UNKNOWN")
    bucket[label] = float(bucket.get(label, 0.0)) + float(amount)


def build_cost_summary(usage: Dict[str, Any], refused: bool = False) -> Dict[str, Any]:
    """从单条 debug response usage 构造成本摘要。"""

    usage = estimate_usage_costs(dict(usage or {}))
    totals = dict(usage.get("totals") or {})
    model_calls = [call for call in list(usage.get("model_calls") or []) if isinstance(call, dict)]

    cost_by_role: Dict[str, float] = {}
    cost_by_provider: Dict[str, float] = {}
    fallback_used = False

    for call in model_calls:
        _add_group_value(cost_by_role, call.get("role"), call.get("estimated_cost_usd"))
        _add_group_value(cost_by_provider, call.get("provider"), call.get("estimated_cost_usd"))

        provider = str(call.get("provider") or "").lower()
        resolved = str(call.get("resolved_model") or call.get("configured_model") or "").lower()
        if bool(call.get("fallback_used")) or provider in {"local", "ollama", "llama.cpp", "llamacpp"}:
            fallback_used = True
        if "qwen" in resolved and ("gguf" in resolved or "ollama" in provider):
            fallback_used = True

    total_cost = _optional_float(totals.get("estimated_cost_usd"))

    return {
        "total_estimated_cost_usd": total_cost,
        "avg_cost_per_answered": None if refused else total_cost,
        "avg_cost_per_refused": total_cost if refused else None,
        "cost_by_role": cost_by_role,
        "cost_by_provider": cost_by_provider,
        "budget_exceeded_count": 0,
        "fallback_used_count": 1 if fallback_used else 0,
        "llm_call_count": totals.get("llm_call_count"),
        "total_tokens": totals.get("total_tokens"),
        "estimated_cost_coverage": (usage.get("cost_estimation") or {}).get("coverage"),
        "priced_call_count": (usage.get("cost_estimation") or {}).get("priced_call_count"),
        "unpriced_call_count": (usage.get("cost_estimation") or {}).get("unpriced_call_count"),
    }


def merge_cost_summaries(rows: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """把多条 cost summary 合并为 replay/report 级摘要。"""

    items = [dict(row or {}) for row in rows]
    total_cost = 0.0
    total_cost_seen = False
    answered_cost = 0.0
    answered_count = 0
    refused_cost = 0.0
    refused_count = 0
    cost_by_role: Dict[str, float] = {}
    cost_by_provider: Dict[str, float] = {}

    for row in items:
        cost = _optional_float(row.get("total_estimated_cost_usd"))
        if cost is not None:
            total_cost += float(cost)
            total_cost_seen = True

        answered = _optional_float(row.get("avg_cost_per_answered"))
        if answered is not None:
            answered_cost += float(answered)
            answered_count += 1

        refused = _optional_float(row.get("avg_cost_per_refused"))
        if refused is not None:
            refused_cost += float(refused)
            refused_count += 1

        for key, value in dict(row.get("cost_by_role") or {}).items():
            _add_group_value(cost_by_role, key, value)
        for key, value in dict(row.get("cost_by_provider") or {}).items():
            _add_group_value(cost_by_provider, key, value)

    return {
        "total_estimated_cost_usd": total_cost if total_cost_seen else None,
        "avg_cost_per_answered": answered_cost / answered_count if answered_count else None,
        "avg_cost_per_refused": refused_cost / refused_count if refused_count else None,
        "cost_by_role": cost_by_role,
        "cost_by_provider": cost_by_provider,
        "budget_exceeded_count": sum(int(row.get("budget_exceeded_count") or 0) for row in items),
        "fallback_used_count": sum(int(row.get("fallback_used_count") or 0) for row in items),
        "record_count": len(items),
    }
