"""
文件作用：
定义 Phase C API 层统一错误响应与 chat 前置依赖 guard。

整体结构：
1）ApiError：API 错误响应 schema；
2）build_error_response：生成统一 JSONResponse；
3）preflight_chat_dependencies：在进入 D-lite pipeline 前检查必需依赖；
4）错误码常量：集中维护 Phase C 最小错误码。

注意：
- 本文件只做 API 包装层错误映射；
- 不修改 query_pipeline / retriever / generator / sufficiency / rerank；
- vector store 或 Ollama 不可用时，必须在进入 generate 前中止。
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agentic_rag.observability.structured_logging import write_log
from agentic_rag.observability.tracing_context import get_request_id
from agentic_rag.service.health_service import HealthService


class ApiError(BaseModel):
    """统一 API 错误响应。"""

    request_id: Optional[str]
    error: str
    message: str
    component: str
    retryable: bool = False


ERROR_STATUS: Dict[str, int] = {
    "invalid_request": 400,
    "unsupported_file_type": 400,
    "empty_document": 400,
    "document_split_failed": 500,
    "embedding_failed": 500,
    "vector_store_write_failed": 500,
    "vector_store_unavailable": 503,
    "vector_store_corrupted": 503,
    "llm_service_unavailable": 503,
    "sufficiency_judge_unavailable": 200,
    "sufficiency_judge_timeout": 200,
    "generation_timeout": 504,
    "too_many_requests": 429,
    "internal_error": 500,
}


def build_error_response(
    *,
    error: str,
    message: str,
    component: str,
    retryable: bool,
    request_id: Optional[str] = None,
    status_code: Optional[int] = None,
    log_fields: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """构造统一错误响应，并写入 service.jsonl。"""

    rid = request_id or get_request_id()
    http_status = int(status_code or ERROR_STATUS.get(error, 500))

    body = ApiError(
        request_id=rid,
        error=error,
        message=message,
        component=component,
        retryable=retryable,
    )

    write_log(
        level="ERROR" if http_status >= 500 else "WARN",
        stage="api_error",
        event="request_rejected",
        request_id=rid,
        error_code=error,
        component=component,
        retryable=retryable,
        http_status=http_status,
        **(log_fields or {}),
    )

    return JSONResponse(
        status_code=http_status,
        content=body.model_dump(),
    )


def preflight_chat_dependencies(request_id: Optional[str] = None) -> Optional[JSONResponse]:
    """在 /api/chat 进入 RAG pipeline 前检查必需依赖。

    Phase E 口径：
    - vector store 是必需依赖；
    - cloud generator / sufficiency judge 需要配置；
    - Ollama 只是 legacy local baseline，不再作为 chat preflight 必需依赖。

    返回：
    - None：依赖可用，可以继续执行 query_pipeline；
    - JSONResponse：依赖不可用，路由应直接返回，不得进入 generate。
    """

    rid = request_id or get_request_id()
    health_service = HealthService()

    vector_status = health_service.check_vector_store()
    if vector_status.get("status") != "up":
        errors = list(vector_status.get("errors") or [])
        if any(str(item).endswith("_missing") for item in errors):
            error_code = "vector_store_unavailable"
            message = "本地向量库文件缺失，无法执行检索。"
        else:
            error_code = "vector_store_corrupted"
            message = "本地向量库文件不可读、维度异常或数量不一致，无法执行检索。"

        return build_error_response(
            request_id=rid,
            error=error_code,
            message=message,
            component="local_vector_store",
            retryable=False,
            log_fields={
                "vector_store_dir": vector_status.get("vector_store_dir"),
                "manifest_path": vector_status.get("manifest_path"),
                "vector_count": vector_status.get("vector_count"),
                "chunk_count": vector_status.get("chunk_count"),
                "embedding_dim": vector_status.get("embedding_dim"),
                "errors": errors,
            },
        )

    openrouter_status = health_service.check_openrouter_config()
    deepseek_status = health_service.check_deepseek_config()

    if openrouter_status.get("status") != "configured":
        return build_error_response(
            request_id=rid,
            error="llm_service_unavailable",
            message="OpenRouter generator 配置缺失，无法执行问答。",
            component="openrouter_generator",
            retryable=False,
            log_fields={
                "endpoint": openrouter_status.get("endpoint"),
                "model": openrouter_status.get("model"),
                "dependency_error": openrouter_status.get("error"),
            },
        )

    if deepseek_status.get("status") != "configured":
        return build_error_response(
            request_id=rid,
            error="llm_service_unavailable",
            message="DeepSeek sufficiency judge 配置缺失，无法执行问答。",
            component="deepseek_sufficiency_judge",
            retryable=False,
            log_fields={
                "endpoint": deepseek_status.get("endpoint"),
                "model": deepseek_status.get("model"),
                "dependency_error": deepseek_status.get("error"),
            },
        )

    return None
