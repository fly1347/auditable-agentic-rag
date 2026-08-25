"""
文件作用：
提供 Phase C API 层结构化 JSONL 日志。

整体结构：
1）统一写 JSONL；
2）每条日志包含 ts / level / request_id / stage / event；
3）后续可扩展 sufficiency / dependency / fault injection 日志。
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from agentic_rag.observability.tracing_context import get_request_id


LOG_DIR = Path("logs")
SERVICE_LOG_FILE = LOG_DIR / "service.jsonl"


def write_log(
    *,
    level: str,
    stage: str,
    event: str,
    request_id: Optional[str] = None,
    **fields: Any,
) -> None:
    """写入一条结构化日志。"""

    LOG_DIR.mkdir(parents=True, exist_ok=True)

    rid = request_id or get_request_id()

    record: Dict[str, Any] = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": str(level),
        "request_id": rid,
        "stage": str(stage),
        "event": str(event),
    }
    record.update(fields)

    with SERVICE_LOG_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")