"""
文件作用：
提供 request_id 的上下文保存能力。

整体结构：
1）使用 ContextVar 保存当前请求的 request_id；
2）提供 set/get/reset 工具函数；
3）供 middleware、service、logging 读取当前请求链路 ID。
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from typing import Optional


_request_id_var: ContextVar[Optional[str]] = ContextVar(
    "request_id",
    default=None,
)


def set_request_id(request_id: str) -> Token[Optional[str]]:
    """写入当前请求的 request_id。"""

    return _request_id_var.set(str(request_id))


def get_request_id() -> Optional[str]:
    """读取当前请求的 request_id。"""

    return _request_id_var.get()


def reset_request_id(token: Token[Optional[str]]) -> None:
    """重置 request_id 上下文。"""

    _request_id_var.reset(token)