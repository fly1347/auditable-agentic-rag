"""
文件作用：
1）提供 Phase E cost / provider policy 的最小策略判断；
2）只从 usage.model_calls / usage.totals 派生成本与预算状态；
3）把预算、provider、fallback 信号转换为 policy_trace.cost_policy，供 debug / audit / replay smoke 使用。

结构：
- CostPolicy：最小成本策略配置；
- CostPolicyDecision：单次请求的成本策略判断结果；
- assess_cost_policy：根据 usage 判断是否超出预算；
- build_cost_policy_trace：生成可并入 response.policy_trace 的 cost_policy。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from agentic_rag.cost.pricing import estimate_usage_costs


@dataclass(frozen=True)
class CostPolicy:
    """定义 Phase E 最小成本策略阈值。"""

    max_llm_calls: int = 8
    max_total_tokens: int = 12000
    max_estimated_cost_usd: Optional[float] = 0.05
    allow_cloud_generator: bool = True
    allow_local_fallback: bool = False

    @classmethod
    def from_env(cls) -> "CostPolicy":
        """从环境变量读取成本策略，缺失时使用 demo 默认值。"""

        budget_raw = os.getenv("AGENTIC_RAG_COST_BUDGET_USD", "0.05").strip()
        try:
            budget = float(budget_raw)
        except Exception:
            budget = 0.05

        return cls(
            max_llm_calls=int(os.getenv("AGENTIC_RAG_MAX_LLM_CALLS", "8")),
            max_total_tokens=int(os.getenv("AGENTIC_RAG_MAX_TOTAL_TOKENS", "12000")),
            max_estimated_cost_usd=budget,
            allow_cloud_generator=os.getenv("AGENTIC_RAG_ALLOW_CLOUD_GENERATOR", "true").lower() != "false",
            allow_local_fallback=os.getenv("AGENTIC_RAG_ALLOW_LOCAL_FALLBACK", "false").lower() != "false",
        )


@dataclass(frozen=True)
class CostPolicyDecision:
    """记录单次请求的成本策略判断结果。"""

    checked: bool
    max_llm_calls: int
    max_total_tokens: int
    max_estimated_cost_usd: Optional[float]
    llm_call_count: int
    total_tokens: Optional[int]
    estimated_cost_usd: Optional[float]
    estimated_cost_coverage: Optional[str]
    priced_call_count: int
    unpriced_call_count: int
    budget_exceeded: bool
    exceeded_reasons: List[str]
    fallback_used: bool
    allow_cloud_generator: bool
    allow_local_fallback: bool

    def to_dict(self) -> Dict[str, Any]:
        """转换为可进入 policy_trace 的字典。"""

        return {
            "checked": bool(self.checked),
            "max_llm_calls": int(self.max_llm_calls),
            "max_total_tokens": int(self.max_total_tokens),
            "max_estimated_cost_usd": self.max_estimated_cost_usd,
            "llm_call_count": int(self.llm_call_count),
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "estimated_cost_coverage": self.estimated_cost_coverage,
            "priced_call_count": int(self.priced_call_count),
            "unpriced_call_count": int(self.unpriced_call_count),
            "budget_exceeded": bool(self.budget_exceeded),
            "exceeded_reasons": list(self.exceeded_reasons),
            "fallback_used": bool(self.fallback_used),
            "allow_cloud_generator": bool(self.allow_cloud_generator),
            "allow_local_fallback": bool(self.allow_local_fallback),
            "mode": "phase_e_cost_baseline",
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


def _detect_fallback_used(usage: Dict[str, Any]) -> bool:
    """从 usage.model_calls 中判断是否出现 fallback 迹象。"""

    calls = list(usage.get("model_calls") or [])
    for call in calls:
        if not isinstance(call, dict):
            continue
        if bool(call.get("fallback_used")):
            return True
        provider = str(call.get("provider") or "").lower()
        resolved = str(call.get("resolved_model") or call.get("configured_model") or "").lower()
        if provider in {"local", "ollama", "llama.cpp", "llamacpp"}:
            return True
        if "qwen" in resolved and ("gguf" in resolved or "ollama" in provider):
            return True
    return False


def assess_cost_policy(usage: Dict[str, Any], policy: CostPolicy | None = None) -> CostPolicyDecision:
    """根据 usage.totals 判断当前请求是否超过成本策略。"""

    cfg = policy or CostPolicy.from_env()
    usage = estimate_usage_costs(dict(usage or {}))
    totals = dict((usage or {}).get("totals") or {})
    cost_estimation = dict((usage or {}).get("cost_estimation") or {})

    llm_call_count = _optional_int(totals.get("llm_call_count")) or len(list((usage or {}).get("model_calls") or []))
    total_tokens = _optional_int(totals.get("total_tokens"))
    estimated_cost = _optional_float(totals.get("estimated_cost_usd"))

    exceeded: List[str] = []
    if llm_call_count > int(cfg.max_llm_calls):
        exceeded.append("max_llm_calls")
    if total_tokens is not None and total_tokens > int(cfg.max_total_tokens):
        exceeded.append("max_total_tokens")
    if (
        cfg.max_estimated_cost_usd is not None
        and estimated_cost is not None
        and estimated_cost > float(cfg.max_estimated_cost_usd)
    ):
        exceeded.append("estimated_cost_usd_over_budget")

    return CostPolicyDecision(
        checked=True,
        max_llm_calls=int(cfg.max_llm_calls),
        max_total_tokens=int(cfg.max_total_tokens),
        max_estimated_cost_usd=cfg.max_estimated_cost_usd,
        llm_call_count=int(llm_call_count),
        total_tokens=total_tokens,
        estimated_cost_usd=estimated_cost,
        estimated_cost_coverage=cost_estimation.get("coverage"),
        priced_call_count=int(cost_estimation.get("priced_call_count") or 0),
        unpriced_call_count=int(cost_estimation.get("unpriced_call_count") or 0),
        budget_exceeded=bool(exceeded),
        exceeded_reasons=exceeded,
        fallback_used=_detect_fallback_used(usage or {}),
        allow_cloud_generator=bool(cfg.allow_cloud_generator),
        allow_local_fallback=bool(cfg.allow_local_fallback),
    )


def build_cost_policy_trace(decision: CostPolicyDecision) -> Dict[str, Any]:
    """生成 policy_trace.cost_policy 结构。"""

    return {
        "cost_policy": decision.to_dict()
    }
