"""
文件作用：
封装 /metrics 输出服务，并追加 Phase E policy / deployment observability 指标。

整体结构：
1）调用 observability.metrics 渲染已有 Prometheus text format；
2）从 logs/audit.jsonl 轻量汇总 Phase E policy 指标；
3）追加 acl / security / audit / fallback / cost 相关指标，供 Step 11 验收。
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List

from agentic_rag.observability.metrics import render_prometheus_metrics


DEFAULT_AUDIT_LOG_PATH = "logs/audit.jsonl"


class MetricsService:
    """Metrics 服务。"""

    def __init__(self, audit_log_path: str = DEFAULT_AUDIT_LOG_PATH) -> None:
        self.audit_log_path = Path(audit_log_path)

    def render(self) -> str:
        """返回 Prometheus text format，并追加 Phase E policy 指标。"""
        base = render_prometheus_metrics().rstrip()
        phase_e = self.render_phase_e_metrics().rstrip()

        if base and phase_e:
            return f"{base}\n\n{phase_e}\n"
        if phase_e:
            return f"{phase_e}\n"
        return f"{base}\n"

    def render_phase_e_metrics(self) -> str:
        """从 audit log 与环境变量派生 Phase E 指标。"""
        records = list(_iter_jsonl_records(self.audit_log_path))
        summary = _summarize_phase_e_records(records)

        lines: List[str] = [
            "# HELP agentic_rag_phase_e_audit_record_count Phase E audit record count parsed from logs/audit.jsonl.",
            "# TYPE agentic_rag_phase_e_audit_record_count counter",
            f"agentic_rag_phase_e_audit_record_count {_fmt(summary['audit_record_count'])}",
            "# HELP agentic_rag_acl_filtered_count Total ACL-filtered retrieval candidates observed in audit policy decisions.",
            "# TYPE agentic_rag_acl_filtered_count counter",
            f"agentic_rag_acl_filtered_count {_fmt(summary['acl_filtered_count'])}",
            "# HELP agentic_rag_injection_blocked_count Total requests with injection detected and blocked/refused.",
            "# TYPE agentic_rag_injection_blocked_count counter",
            f"agentic_rag_injection_blocked_count {_fmt(summary['injection_blocked_count'])}",
            "# HELP agentic_rag_redaction_count Total redaction count observed in security policy decisions.",
            "# TYPE agentic_rag_redaction_count counter",
            f"agentic_rag_redaction_count {_fmt(summary['redaction_count'])}",
            "# HELP agentic_rag_audit_failed_count Audit write failures observed by the metrics layer.",
            "# TYPE agentic_rag_audit_failed_count counter",
            f"agentic_rag_audit_failed_count {_fmt(summary['audit_failed_count'])}",
            "# HELP agentic_rag_fallback_used_count Total fallback-used events observed in cost policy decisions.",
            "# TYPE agentic_rag_fallback_used_count counter",
            f"agentic_rag_fallback_used_count {_fmt(summary['fallback_used_count'])}",
            "# HELP agentic_rag_cost_estimated_total Total estimated model cost observed in audit model call summaries.",
            "# TYPE agentic_rag_cost_estimated_total counter",
            f"agentic_rag_cost_estimated_total {_fmt(summary['cost_estimated_total'])}",
            "# HELP agentic_rag_phase_e_audit_enabled Whether Phase E audit logging is enabled by env.",
            "# TYPE agentic_rag_phase_e_audit_enabled gauge",
            f"agentic_rag_phase_e_audit_enabled {_fmt(1 if _parse_bool(os.getenv('AGENTIC_RAG_AUDIT_LOG_ENABLED'), default=True) else 0)}",
            "# HELP agentic_rag_phase_e_offline_env_enabled Whether HF_HUB_OFFLINE and TRANSFORMERS_OFFLINE are both set to 1.",
            "# TYPE agentic_rag_phase_e_offline_env_enabled gauge",
            f"agentic_rag_phase_e_offline_env_enabled {_fmt(1 if _offline_env_enabled() else 0)}",
        ]
        return "\n".join(lines)


def _iter_jsonl_records(path: Path) -> Iterable[Dict[str, Any]]:
    """安全读取 JSONL audit records；坏行跳过。"""
    if not path.exists():
        return []

    records: List[Dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    value = json.loads(raw)
                except Exception:
                    continue
                if isinstance(value, dict):
                    records.append(value)
    except Exception:
        return []
    return records


def _summarize_phase_e_records(records: List[Dict[str, Any]]) -> Dict[str, float]:
    """汇总 Phase E audit records 中的 policy / cost 指标。"""
    acl_filtered_count = 0.0
    injection_blocked_count = 0.0
    redaction_count = 0.0
    fallback_used_count = 0.0
    cost_estimated_total = 0.0

    for record in records:
        policy = _get_policy_decisions(record)
        access_policy = _as_dict(policy.get("access_policy"))
        security_policy = _as_dict(policy.get("security_policy"))
        cost_policy = _as_dict(policy.get("cost_policy"))

        acl_filtered_count += _sum_numeric_values(access_policy, {"filtered_count", "acl_filtered_count"})

        injection_detected = _truthy_value(security_policy, {"injection_detected", "injection_blocked"})
        refused_or_blocked = _truthy_value(security_policy, {"refused", "blocked", "refusal_recommended"})
        final_status = str(record.get("final_status") or "").lower()
        refused_reason = str(record.get("refused_reason") or "").lower()

        if injection_detected and (refused_or_blocked or final_status in {"refused", "blocked"} or refused_reason):
            injection_blocked_count += 1.0

        redaction_count += _sum_numeric_values(security_policy, {"redaction_count", "redacted_count"})

        if _truthy_value(cost_policy, {"fallback_used"}):
            fallback_used_count += 1.0

        cost_estimated_total += _record_estimated_cost(record, cost_policy)

    return {
        "audit_record_count": float(len(records)),
        "acl_filtered_count": acl_filtered_count,
        "injection_blocked_count": injection_blocked_count,
        "redaction_count": redaction_count,
        "audit_failed_count": 0.0,
        "fallback_used_count": fallback_used_count,
        "cost_estimated_total": cost_estimated_total,
    }


def _get_policy_decisions(record: Dict[str, Any]) -> Dict[str, Any]:
    """兼容不同 AuditRecord 字段名读取 policy decisions。"""
    for key in ("policy_decisions", "policy_trace", "policy"):
        value = record.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _record_estimated_cost(record: Dict[str, Any], cost_policy: Dict[str, Any]) -> float:
    """从 cost_policy 或 model_call_summary 中提取 estimated cost。"""
    direct = _sum_numeric_values(cost_policy, {"estimated_cost_usd", "total_estimated_cost_usd", "cost_estimated_total"})
    if direct > 0:
        return direct

    model_call_summary = _as_dict(record.get("model_call_summary"))
    direct = _sum_numeric_values(model_call_summary, {"estimated_cost_usd", "total_estimated_cost_usd"})
    if direct > 0:
        return direct

    total = 0.0
    calls = model_call_summary.get("model_calls")
    if isinstance(calls, list):
        for call in calls:
            total += _sum_numeric_values(_as_dict(call), {"estimated_cost_usd"})
    return total


def _sum_numeric_values(payload: Any, keys: set[str]) -> float:
    """递归累计目标 key 的数值。"""
    total = 0.0
    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in keys:
                total += _safe_float(value)
            if isinstance(value, (dict, list)):
                total += _sum_numeric_values(value, keys)
    elif isinstance(payload, list):
        for item in payload:
            total += _sum_numeric_values(item, keys)
    return total


def _truthy_value(payload: Dict[str, Any], keys: set[str]) -> bool:
    """判断 payload 中任一目标 key 是否为真。"""
    for key in keys:
        if _parse_bool_like(payload.get(key)):
            return True
    return False


def _as_dict(value: Any) -> Dict[str, Any]:
    """把非 dict 值安全降级为空 dict。"""
    return value if isinstance(value, dict) else {}


def _safe_float(value: Any) -> float:
    """把值安全转换为 float，失败返回 0。"""
    if value is None:
        return 0.0
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    try:
        result = float(value)
    except Exception:
        return 0.0
    if math.isnan(result) or math.isinf(result):
        return 0.0
    return result


def _parse_bool(value: Any, default: bool = False) -> bool:
    """解析环境变量布尔值。"""
    if value is None or value == "":
        return default
    return _parse_bool_like(value)


def _parse_bool_like(value: Any) -> bool:
    """解析常见 bool-like 值。"""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on", "blocked", "refused"}
    return False


def _offline_env_enabled() -> bool:
    """判断离线环境变量是否同时启用。"""
    return os.getenv("HF_HUB_OFFLINE") == "1" and os.getenv("TRANSFORMERS_OFFLINE") == "1"


def _fmt(value: float | int) -> str:
    """格式化 Prometheus 数值。"""
    if isinstance(value, int):
        return str(value)
    if float(value).is_integer():
        return str(int(value))
    return f"{float(value):.10f}".rstrip("0").rstrip(".")
