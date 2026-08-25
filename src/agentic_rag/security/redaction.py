"""
文件作用：
1）提供 Phase E security baseline 的统一脱敏能力；
2）识别并替换 api-key-like token、email、phone、long token、private key block；
3）供 audit writer / security smoke / 后续日志出口复用，避免敏感原文进入长期日志。

结构：
- RedactionResult：脱敏后的文本、命中数量、命中类型；
- redact_text：处理单段文本；
- redact_payload：递归处理 dict/list/tuple/string；
- inspect_text：只返回检测摘要，不返回原文。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


@dataclass(frozen=True)
class RedactionResult:
    text: str
    redaction_count: int
    matched_types: List[str]


_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("private_key_block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S)),
    ("api_key_sk", re.compile(r"\bsk-[A-Za-z0-9_\-]{12,}\b")),
    ("api_key_ak", re.compile(r"\bak-[A-Za-z0-9_\-]{12,}\b")),
    ("slack_token", re.compile(r"\bxoxb-[A-Za-z0-9_\-]{12,}\b")),
    ("github_token", re.compile(r"\bghp_[A-Za-z0-9_]{12,}\b")),
    ("hf_token", re.compile(r"\bhf_[A-Za-z0-9_\-]{12,}\b")),
    ("email", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(r"(?<!\d)(?:\+?\d[\d\-\s()]{7,}\d)(?!\d)")),
    ("long_token", re.compile(r"\b[A-Za-z0-9_\-]{32,}\b")),
]


def redact_text(text: Any) -> RedactionResult:
    out = str(text or "")
    count = 0
    matched: List[str] = []

    for label, pattern in _PATTERNS:
        out, n = pattern.subn(f"[REDACTED_{label.upper()}]", out)
        if n > 0:
            count += int(n)
            matched.append(label)

    return RedactionResult(text=out, redaction_count=count, matched_types=matched)


def redact_payload(value: Any) -> Any:
    if isinstance(value, str):
        return redact_text(value).text
    if isinstance(value, dict):
        return {str(k): redact_payload(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact_payload(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_payload(item) for item in value)
    return value


def inspect_text(text: Any) -> Dict[str, Any]:
    result = redact_text(text)
    return {
        "redaction_applied": result.redaction_count > 0,
        "redaction_count": result.redaction_count,
        "matched_types": result.matched_types,
    }
