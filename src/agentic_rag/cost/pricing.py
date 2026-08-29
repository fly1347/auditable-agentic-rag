"""
文件作用：
1）提供带来源和生效日期的静态预算估算表；
2）根据 usage.model_calls 中的模型身份与 token usage 估算 estimated_cost_usd；
3）只做请求级成本估算，不对接 provider billing API，也不代表真实账单。

结构：
- PriceEntry：单个模型的静态价格配置；
- PRICE_TABLE：当前项目最小价格表；
- estimate_model_call_cost：估算单次模型调用成本；
- estimate_usage_costs：为 usage.model_calls 与 usage.totals 写入估算成本。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional


@dataclass(frozen=True)
class PriceEntry:
    """记录一个模型的静态估算单价。"""

    input_usd_per_1m_tokens: float
    output_usd_per_1m_tokens: float
    cached_input_usd_per_1m_tokens: Optional[float] = None
    currency: str = "USD"
    source: str = "operator_policy"
    effective_date: str = "2026-08-18"
    pricing_basis: str = "standard"
    current_price_verified: bool = False


PRICE_TABLE_VERSION = "phase_f_official_reference_2026-08-18"


PRICE_TABLE: Dict[str, PriceEntry] = {
    # OpenRouter 账单可能与模型开发商公价不同；因此保留为预算参考，
    # 不声称已与 OpenRouter billing 对账。
    "openrouter:openai/gpt-4o-mini": PriceEntry(
        input_usd_per_1m_tokens=0.15,
        output_usd_per_1m_tokens=0.60,
        cached_input_usd_per_1m_tokens=0.075,
        source="openai_official_reference_via_openrouter_unreconciled",
        current_price_verified=False,
    ),
    # OpenAI 官方标准价，核对日期 2026-08-18。
    "openai/gpt-4o-mini": PriceEntry(
        input_usd_per_1m_tokens=0.15,
        output_usd_per_1m_tokens=0.60,
        cached_input_usd_per_1m_tokens=0.075,
        source="openai_official_model_page",
        current_price_verified=True,
    ),
    "gpt-4o-mini": PriceEntry(
        input_usd_per_1m_tokens=0.15,
        output_usd_per_1m_tokens=0.60,
        cached_input_usd_per_1m_tokens=0.075,
        source="openai_official_model_page",
        current_price_verified=True,
    ),
    "openai:gpt-5.6-luna": PriceEntry(
        input_usd_per_1m_tokens=0.20,
        output_usd_per_1m_tokens=1.20,
        cached_input_usd_per_1m_tokens=0.02,
        source="openai_official_model_page",
        current_price_verified=True,
    ),
    "gpt-5.6-luna": PriceEntry(
        input_usd_per_1m_tokens=0.20,
        output_usd_per_1m_tokens=1.20,
        cached_input_usd_per_1m_tokens=0.02,
        source="openai_official_model_page",
        current_price_verified=True,
    ),
    # DeepSeek 价格随 UTC 时段变化。预算门禁采用较高的 peak 价，避免
    # 在静态估算中低估；真实账单仍需 provider reconciliation。
    "deepseek:deepseek-v4-flash": PriceEntry(
        input_usd_per_1m_tokens=0.44,
        output_usd_per_1m_tokens=1.32,
        cached_input_usd_per_1m_tokens=0.014,
        source="deepseek_official_pricing",
        pricing_basis="peak_conservative",
        current_price_verified=True,
    ),
    "deepseek/deepseek-v4-flash": PriceEntry(
        input_usd_per_1m_tokens=0.44,
        output_usd_per_1m_tokens=1.32,
        cached_input_usd_per_1m_tokens=0.014,
        source="deepseek_official_pricing",
        pricing_basis="peak_conservative",
        current_price_verified=True,
    ),
    "deepseek-v4-flash": PriceEntry(
        input_usd_per_1m_tokens=0.44,
        output_usd_per_1m_tokens=1.32,
        cached_input_usd_per_1m_tokens=0.014,
        source="deepseek_official_pricing",
        pricing_basis="peak_conservative",
        current_price_verified=True,
    ),
    # 本地 fallback 只按本项目估算口径记 0；机器、电费、运维成本不在本轮范围内。
    "local": PriceEntry(
        input_usd_per_1m_tokens=0.0,
        output_usd_per_1m_tokens=0.0,
        source="local_compute_excluded",
        pricing_basis="api_cost_only",
        current_price_verified=True,
    ),
    "ollama": PriceEntry(
        input_usd_per_1m_tokens=0.0,
        output_usd_per_1m_tokens=0.0,
        source="local_compute_excluded",
        pricing_basis="api_cost_only",
        current_price_verified=True,
    ),
    "llama.cpp": PriceEntry(
        input_usd_per_1m_tokens=0.0,
        output_usd_per_1m_tokens=0.0,
        source="local_compute_excluded",
        pricing_basis="api_cost_only",
        current_price_verified=True,
    ),
    "qwen3.5-9b-q4_k_m.gguf": PriceEntry(
        input_usd_per_1m_tokens=0.0,
        output_usd_per_1m_tokens=0.0,
        source="local_compute_excluded",
        pricing_basis="api_cost_only",
        current_price_verified=True,
    ),
}


def _optional_int(value: Any) -> Optional[int]:
    """安全读取 optional int。"""

    if value in (None, ""):
        return None
    try:
        return int(value)
    except Exception:
        return None


def _optional_float(value: Any) -> Optional[float]:
    """安全读取 optional float。"""

    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _normalize_key(value: Any) -> str:
    """规范化 provider/model key，便于价格表匹配。"""

    return str(value or "").strip().lower()


def _is_local_call(call: Dict[str, Any]) -> bool:
    """判断一次调用是否属于本地 fallback。"""

    provider = _normalize_key(call.get("provider"))
    resolved = _normalize_key(call.get("resolved_model") or call.get("configured_model"))
    return (
        provider in {"local", "ollama", "llama.cpp", "llamacpp"}
        or "gguf" in resolved
        or ("qwen" in resolved and provider in {"local", "ollama", "llama.cpp", "llamacpp"})
    )


def _candidate_price_keys(call: Dict[str, Any]) -> List[str]:
    """生成价格表匹配候选 key。"""

    keys: List[str] = []
    provider = _normalize_key(call.get("provider"))
    if _is_local_call(call):
        keys.extend(["local", provider])

    models: List[str] = []
    for raw in (
        call.get("resolved_model"),
        call.get("configured_model"),
        call.get("provider_response_model"),
    ):
        model = _normalize_key(raw)
        if not model:
            continue
        models.append(model)
        if provider:
            keys.append(f"{provider}:{model}")
    for model in models:
        keys.append(model)
        if "/" in model:
            keys.append(model.rsplit("/", 1)[-1])

    out: List[str] = []
    for key in keys:
        if key and key not in out:
            out.append(key)
    return out


def get_price_entry_for_call(call: Dict[str, Any]) -> Optional[PriceEntry]:
    """根据 model call 的 provider/model 字段查找静态价格。"""

    for key in _candidate_price_keys(call):
        if key in PRICE_TABLE:
            return PRICE_TABLE[key]
    return None


def estimate_model_call_cost(call: Dict[str, Any]) -> Optional[float]:
    """根据 prompt/cache/completion tokens 与静态价格估算单次调用成本。"""

    row = dict(call or {})
    entry = get_price_entry_for_call(row)
    if entry is None:
        return None

    prompt_tokens = _optional_int(row.get("prompt_tokens"))
    cached_tokens = _optional_int(row.get("cached_tokens"))
    completion_tokens = _optional_int(row.get("completion_tokens"))
    total_tokens = _optional_int(row.get("total_tokens"))

    if prompt_tokens is None and completion_tokens is not None and total_tokens is not None:
        prompt_tokens = max(total_tokens - completion_tokens, 0)
    if completion_tokens is None and prompt_tokens is not None and total_tokens is not None:
        completion_tokens = max(total_tokens - prompt_tokens, 0)

    if float(entry.input_usd_per_1m_tokens) == 0.0 and float(entry.output_usd_per_1m_tokens) == 0.0:
        return 0.0
    if prompt_tokens is None or completion_tokens is None:
        return None

    cached_input_price = entry.cached_input_usd_per_1m_tokens
    if cached_input_price is None:
        cached_tokens_for_price = 0
        non_cached_prompt_tokens = prompt_tokens
    else:
        cached_tokens_for_price = min(int(cached_tokens or 0), int(prompt_tokens or 0))
        non_cached_prompt_tokens = max(int(prompt_tokens or 0) - cached_tokens_for_price, 0)

    input_cost = (
        float(non_cached_prompt_tokens) * float(entry.input_usd_per_1m_tokens) / 1_000_000.0
        if non_cached_prompt_tokens is not None
        else 0.0
    )
    cached_input_cost = (
        float(cached_tokens_for_price) * float(cached_input_price) / 1_000_000.0
        if cached_input_price is not None
        else 0.0
    )
    output_cost = (
        float(completion_tokens) * float(entry.output_usd_per_1m_tokens) / 1_000_000.0
        if completion_tokens is not None
        else 0.0
    )
    return round(float(input_cost + cached_input_cost + output_cost), 12)


def _sum_optional_costs(values: Iterable[Any]) -> Optional[float]:
    """汇总 optional cost；全空时返回 None。"""

    total = 0.0
    seen = False
    for value in values:
        amount = _optional_float(value)
        if amount is None:
            continue
        total += amount
        seen = True
    return round(total, 12) if seen else None


def estimate_usage_costs(usage: Dict[str, Any]) -> Dict[str, Any]:
    """为 usage.model_calls 与 usage.totals 写入 estimated_cost_usd 估算值。"""

    data = dict(usage or {})
    model_calls = [dict(call) for call in list(data.get("model_calls") or []) if isinstance(call, dict)]
    estimated_calls: List[Dict[str, Any]] = []

    priced_count = 0
    unpriced_count = 0
    missing_token_count = 0
    verification_values: List[bool] = []

    for call in model_calls:
        entry = get_price_entry_for_call(call)
        estimated_cost = estimate_model_call_cost(call)

        if call.get("estimated_cost_usd") in (None, ""):
            call["estimated_cost_usd"] = estimated_cost

        if entry is not None:
            verification_values.append(bool(entry.current_price_verified))
            call["cost_price_source"] = entry.source
            call["cost_currency"] = entry.currency
            call["cost_effective_date"] = entry.effective_date
            call["cost_pricing_basis"] = entry.pricing_basis
            call["cost_price_verified"] = entry.current_price_verified
            call["input_usd_per_1m_tokens"] = entry.input_usd_per_1m_tokens
            call["cached_input_usd_per_1m_tokens"] = entry.cached_input_usd_per_1m_tokens
            call["output_usd_per_1m_tokens"] = entry.output_usd_per_1m_tokens
            if (
                call.get("cached_tokens") in (None, "")
                and entry.cached_input_usd_per_1m_tokens is not None
                and entry.cached_input_usd_per_1m_tokens != entry.input_usd_per_1m_tokens
            ):
                call["cached_usage_assumption"] = "unknown_treated_as_uncached_conservative"

        if call.get("estimated_cost_usd") is None:
            unpriced_count += 1
            if _optional_int(call.get("prompt_tokens")) is None and _optional_int(call.get("completion_tokens")) is None:
                missing_token_count += 1
            call["cost_estimation_status"] = "not_estimated"
        else:
            priced_count += 1
            call["cost_estimation_status"] = "estimated"

        estimated_calls.append(call)

    totals = dict(data.get("totals") or {})
    totals["llm_call_count"] = len(estimated_calls)
    totals["model_call_count"] = len(estimated_calls)

    for token_key in (
        "prompt_tokens",
        "completion_tokens",
        "reasoning_tokens",
        "cached_tokens",
        "cache_write_tokens",
        "total_tokens",
    ):
        observed = [_optional_int(call.get(token_key)) for call in estimated_calls]
        values = [value for value in observed if value is not None]
        unknown_count = len(estimated_calls) - len(values)
        observed_sum = sum(values)
        totals[f"{token_key}_observed_sum"] = observed_sum
        totals[f"{token_key}_unknown_call_count"] = unknown_count
        # 逐次调用底账才是规范来源；不要沿用可能把缺失明细错误转成 0 的历史汇总值。
        totals[token_key] = observed_sum if not unknown_count else None

    observed_cost_sum = _sum_optional_costs(
        call.get("estimated_cost_usd") for call in estimated_calls
    )
    totals["estimated_cost_usd_observed_sum"] = observed_cost_sum or 0.0
    totals["estimated_cost_usd"] = (
        observed_cost_sum or 0.0
        if unpriced_count == 0
        else None
    )

    if priced_count and unpriced_count:
        coverage = "partial"
    elif priced_count:
        coverage = "full"
    else:
        coverage = "none"

    data["model_calls"] = estimated_calls
    data["totals"] = totals
    data["cost_estimation"] = {
        "enabled": True,
        "source": "static_price_table",
        "price_table_version": PRICE_TABLE_VERSION,
        "current_price_verified": bool(verification_values) and all(verification_values),
        "price_reference_verified_at": "2026-08-18",
        "currency": "USD",
        "coverage": coverage,
        "priced_call_count": int(priced_count),
        "unpriced_call_count": int(unpriced_count),
        "missing_token_count": int(missing_token_count),
        "price_table_size": int(len(PRICE_TABLE)),
        "provider_billing_reconciled": False,
    }
    return data
