"""
文件作用：
1）提供 Phase E prompt injection 最小检测；
2）用 pattern-based baseline 标记“忽略指令 / 泄露密钥 / 输出系统提示”等风险文本；
3）只做风险标记，不引入复杂 classifier，不改变 D-full 答案质量评估口径。

结构：
- InjectionAssessment：注入检测结果；
- _PATTERNS：最小注入风险 pattern 集；
- detect_prompt_injection：返回是否命中、命中 pattern 与风险等级。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass(frozen=True)
class InjectionAssessment:
    detected: bool
    matched_patterns: List[str]
    risk_level: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "detected": bool(self.detected),
            "matched_patterns": list(self.matched_patterns),
            "risk_level": str(self.risk_level),
        }


_PATTERNS = {
    "ignore_previous_instructions": re.compile(r"ignore (all )?(previous|above) instructions", re.I),
    "ignore_above_cn": re.compile(r"忽略(以上|上述|前面|所有).*?(指令|提示|要求)"),
    "reveal_secret_cn": re.compile(r"(泄露|输出|打印|展示).{0,12}(密钥|秘钥|api key|API key|token|令牌)", re.I),
    "reveal_system_prompt": re.compile(r"(reveal|print|show|output).{0,20}(system prompt|hidden prompt|developer message)", re.I),
    "system_prompt_cn": re.compile(r"(输出|打印|展示|泄露).{0,12}(系统提示|隐藏提示|开发者消息)"),
}


def detect_prompt_injection(text: Any) -> InjectionAssessment:
    raw = str(text or "")
    matched: List[str] = []

    for label, pattern in _PATTERNS.items():
        if pattern.search(raw):
            matched.append(label)

    risk_level = "low"
    if len(matched) >= 2:
        risk_level = "high"
    elif len(matched) == 1:
        risk_level = "medium"

    return InjectionAssessment(
        detected=bool(matched),
        matched_patterns=matched,
        risk_level=risk_level,
    )
