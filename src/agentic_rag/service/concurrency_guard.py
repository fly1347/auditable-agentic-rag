"""
文件作用：
提供 Phase C API 层的最小并发控制。该模块只包住服务入口，
不修改 query_pipeline / retriever / generator / sufficiency 等 RAG 内核逻辑。

整体结构：
1）GenerationQueueFull：队列已满时抛出的业务异常；
2）GenerationTicket：记录本次请求的 queue_wait_ms；
3）acquire_generation_slot：控制同时进入生成链路的请求数量，并限制等待队列长度。

关键语义：
- MAX_GENERATION_CONCURRENCY 必须 >= 1；
- MAX_QUEUE_SIZE 允许为 0；
- MAX_QUEUE_SIZE=0 表示不允许排队，执行槽位满时立即返回 429。
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from dataclasses import dataclass
from threading import BoundedSemaphore
from typing import Iterator, Optional


DEFAULT_MAX_GENERATION_CONCURRENCY = 1
DEFAULT_MAX_QUEUE_SIZE = 10


def _read_positive_int_from_env(name: str, default: int) -> int:
    """读取正整数环境变量，非法值回退到 default。"""

    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(1, value)


def _read_non_negative_int_from_env(name: str, default: int) -> int:
    """读取非负整数环境变量，非法值回退到 default。"""

    raw = os.getenv(name)
    if raw is None or str(raw).strip() == "":
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(0, value)


MAX_GENERATION_CONCURRENCY = _read_positive_int_from_env(
    "MAX_GENERATION_CONCURRENCY",
    DEFAULT_MAX_GENERATION_CONCURRENCY,
)
MAX_QUEUE_SIZE = _read_non_negative_int_from_env(
    "MAX_QUEUE_SIZE",
    DEFAULT_MAX_QUEUE_SIZE,
)

_execution_slots = BoundedSemaphore(MAX_GENERATION_CONCURRENCY)
_waiting_queue_slots: Optional[BoundedSemaphore] = (
    BoundedSemaphore(MAX_QUEUE_SIZE) if MAX_QUEUE_SIZE > 0 else None
)


class GenerationQueueFull(Exception):
    """生成队列已满。"""


@dataclass(frozen=True)
class GenerationTicket:
    """一次进入生成链路的排队信息。"""

    queue_wait_ms: float


@contextmanager
def acquire_generation_slot() -> Iterator[GenerationTicket]:
    """
    获取生成执行槽位。

    行为：
    - 若执行槽位可用，直接进入，queue_wait_ms=0；
    - 若执行槽位已满且 MAX_QUEUE_SIZE=0，立即抛出 GenerationQueueFull；
    - 若执行槽位已满但等待队列未满，则排队等待；
    - 若等待队列已满，立即抛出 GenerationQueueFull，由 API 层返回 429。
    """

    if _execution_slots.acquire(blocking=False):
        try:
            yield GenerationTicket(queue_wait_ms=0.0)
        finally:
            _execution_slots.release()
        return

    if MAX_QUEUE_SIZE <= 0 or _waiting_queue_slots is None:
        raise GenerationQueueFull("generation queue is full")

    if not _waiting_queue_slots.acquire(blocking=False):
        raise GenerationQueueFull("generation queue is full")

    wait_start = time.time()
    execution_acquired = False

    try:
        _execution_slots.acquire()
        execution_acquired = True
        queue_wait_ms = float((time.time() - wait_start) * 1000.0)
        yield GenerationTicket(queue_wait_ms=queue_wait_ms)
    finally:
        _waiting_queue_slots.release()
        if execution_acquired:
            _execution_slots.release()
