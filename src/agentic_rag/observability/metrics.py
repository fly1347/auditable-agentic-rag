"""
文件作用：
提供 Phase C 最小内存指标。

整体结构：
1）记录 request/refusal/path/error 计数；
2）输出 Prometheus text format；
3）Phase C 后续压测前再扩展 latency histogram。
"""

from __future__ import annotations

from collections import Counter
from threading import Lock
from typing import Optional


_lock = Lock()
_request_total: Counter[str] = Counter()
_refusal_total: Counter[str] = Counter()
_path_total: Counter[str] = Counter()
_error_total: Counter[str] = Counter()


def record_chat_result(
    *,
    status: str,
    path: str,
    refused: bool,
    refused_reason: Optional[str],
) -> None:
    """记录一次 chat 结果。"""

    with _lock:
        _request_total[str(status)] += 1
        _path_total[str(path or "UNKNOWN")] += 1

        if refused:
            reason = str(refused_reason or "unknown")
            _refusal_total[reason] += 1


def record_error(*, error_code: str) -> None:
    """记录一次 API 错误。"""

    with _lock:
        _error_total[str(error_code or "unknown")] += 1


def render_prometheus_metrics() -> str:
    """渲染 Prometheus text format。"""

    lines: list[str] = []

    lines.append("# HELP rag_request_total Total RAG API requests.")
    lines.append("# TYPE rag_request_total counter")
    for status, value in sorted(_request_total.items()):
        lines.append(f'rag_request_total{{status="{status}"}} {value}')

    lines.append("# HELP rag_refusal_total Total RAG refusals.")
    lines.append("# TYPE rag_refusal_total counter")
    for reason, value in sorted(_refusal_total.items()):
        lines.append(f'rag_refusal_total{{reason="{reason}"}} {value}')

    lines.append("# HELP rag_agentic_path_total Total RAG agentic path count.")
    lines.append("# TYPE rag_agentic_path_total counter")
    for path, value in sorted(_path_total.items()):
        lines.append(f'rag_agentic_path_total{{path="{path}"}} {value}')

    lines.append("# HELP rag_error_total Total RAG API errors.")
    lines.append("# TYPE rag_error_total counter")
    for error_code, value in sorted(_error_total.items()):
        lines.append(f'rag_error_total{{error_code="{error_code}"}} {value}')

    return "\n".join(lines) + "\n"
