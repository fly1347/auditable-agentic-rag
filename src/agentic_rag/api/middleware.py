"""
文件作用：
定义 FastAPI API 层 middleware。

整体结构：
1）为每个请求生成或接收 request_id；
2）写入 ContextVar；
3）在响应 header 返回 X-Request-ID；
4）保证请求结束后清理上下文。
"""

from __future__ import annotations

import uuid
from typing import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from agentic_rag.observability.tracing_context import (
    reset_request_id,
    set_request_id,
)
from agentic_rag.policy.principal import AuthenticationRequired, anonymous_principal


REQUEST_ID_HEADER = "X-Request-ID"


def generate_request_id() -> str:
    """生成短 request_id。"""

    return f"req_{uuid.uuid4().hex[:12]}"


async def request_id_middleware(
    request: Request,
    call_next: Callable,
) -> Response:
    """为每个请求注入 request_id。"""

    incoming_request_id = request.headers.get(REQUEST_ID_HEADER)
    request_id = incoming_request_id or generate_request_id()
    request.state.request_id = request_id
    token = set_request_id(request_id)

    try:
        settings = request.app.state.settings
        if request.method.upper() == "OPTIONS" or request.url.path in set(settings.auth.public_paths):
            request.state.principal = anonymous_principal()
        else:
            try:
                request.state.principal = request.app.state.auth_adapter.resolve(
                    request.headers.get(settings.auth.header_name)
                )
            except AuthenticationRequired as exc:
                response = JSONResponse(
                    status_code=401,
                    content={
                        "request_id": request_id,
                        "error": "authentication_required",
                        "message": str(exc),
                        "component": "auth_adapter",
                        "retryable": False,
                    },
                )
                response.headers[REQUEST_ID_HEADER] = request_id
                return response
        response: Response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response
    finally:
        reset_request_id(token)
