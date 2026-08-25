"""
文件作用：
1）提供 Phase E security_policy 的最小策略判断；
2）汇总 prompt injection、secret/PII redaction、private boundary 三类安全信号；
3）把安全判断转换成 policy_trace.security_policy，供 debug / audit / replay smoke 使用。

结构：
- SecurityPolicyDecision：安全策略决策结果；
- assess_security_policy：对 query 做最小安全策略判断；
- build_security_policy_trace：生成可并入 response.policy_trace 的 security_policy。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List

from agentic_rag.security.injection import detect_prompt_injection
from agentic_rag.security.redaction import inspect_text


@dataclass(frozen=True)
class SecurityPolicyDecision:
    checked: bool
    injection_detected: bool
    injection_risk_level: str
    injection_patterns: List[str]
    redaction_applied: bool
    redaction_count: int
    redaction_types: List[str]
    private_boundary_detected: bool
    unsafe_or_private: bool
    refusal_recommended: bool
    refusal_reason: str | None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "checked": bool(self.checked),
            "injection_detected": bool(self.injection_detected),
            "injection_risk_level": str(self.injection_risk_level),
            "injection_patterns": list(self.injection_patterns),
            "redaction_applied": bool(self.redaction_applied),
            "redaction_count": int(self.redaction_count),
            "redaction_types": list(self.redaction_types),
            "private_boundary_detected": bool(self.private_boundary_detected),
            "unsafe_or_private": bool(self.unsafe_or_private),
            "refusal_recommended": bool(self.refusal_recommended),
            "refusal_reason": self.refusal_reason,
            "mode": "phase_e_pattern_baseline",
        }


_PRIVATE_PATTERNS = [
    re.compile(r"(系统提示|隐藏提示|开发者消息|system prompt|hidden prompt|developer message)", re.I),
    re.compile(r"(api key|API key|密钥|秘钥|令牌|token|provider secret)", re.I),
    re.compile(r"(内部实现|私有实现|private implementation|internal implementation)", re.I),
]


def _detect_private_boundary(text: Any) -> bool:
    raw = str(text or "")
    return any(pattern.search(raw) for pattern in _PRIVATE_PATTERNS)


def assess_security_policy(query: Any) -> SecurityPolicyDecision:
    injection = detect_prompt_injection(query)
    redaction = inspect_text(query)
    private_boundary = _detect_private_boundary(query)

    refusal_recommended = bool(private_boundary)
    refusal_reason = "unsafe_or_private_boundary" if refusal_recommended else None

    return SecurityPolicyDecision(
        checked=True,
        injection_detected=bool(injection.detected),
        injection_risk_level=str(injection.risk_level),
        injection_patterns=list(injection.matched_patterns),
        redaction_applied=bool(redaction["redaction_applied"]),
        redaction_count=int(redaction["redaction_count"]),
        redaction_types=list(redaction["matched_types"]),
        private_boundary_detected=bool(private_boundary),
        unsafe_or_private=bool(private_boundary),
        refusal_recommended=bool(refusal_recommended),
        refusal_reason=refusal_reason,
    )


def build_security_policy_trace(decision: SecurityPolicyDecision) -> Dict[str, Any]:
    return {
        "security_policy": decision.to_dict()
    }
