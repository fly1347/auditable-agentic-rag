"""
程序作用：
将审计记录统一脱敏后追加写入 JSONL 日志，并返回便于接口层确认的写入摘要。

整体结构：
1）audit_log_path 从环境变量解析审计日志位置；
2）append_audit_record 脱敏、创建目录并追加写入单条记录。
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

from agentic_rag.audit.record import AuditRecord
from agentic_rag.security.redaction import redact_payload


def audit_log_path() -> Path:
    raw = os.getenv("AUDIT_LOG_PATH", "logs/audit.jsonl")
    return Path(raw).expanduser()


# 脱敏并追加写入一条审计记录。
def append_audit_record(record: AuditRecord, path: str | Path | None = None) -> Dict[str, Any]:
    target = Path(path).expanduser() if path is not None else audit_log_path()
    target.parent.mkdir(parents=True, exist_ok=True)

    payload = redact_payload(record.to_dict())
    with target.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")

    return {
        "audit_record_written": True,
        "audit_log_path": str(target),
        "request_id": record.request_id,
    }
