# 程序作用：提供 Phase C ingest / documents API 路由。
# 整体结构：
# 1) POST /api/ingest：上传 .md/.txt 文档，保存到 data/corpus/phase_a/{internal|external}/ 后全量重建索引。
# 2) GET /api/documents：扫描 corpus 目录，返回当前文档列表。
# 3) DELETE /api/documents/{doc_id:path}：删除指定文档后全量重建索引。
# 说明：本文件只做 HTTP 层参数接收与错误映射；具体文件与索引操作放在 IngestService。

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from agentic_rag.service.ingest_service import (
    DocumentNotFoundError,
    EmptyDocumentError,
    IngestService,
    InvalidDocumentIdError,
    UnsupportedFileTypeError,
    UploadTooLargeError,
    VectorStoreRebuildError,
)

router = APIRouter()


def _require_admin(request: Request) -> None:
    settings = request.app.state.settings
    if not settings.admin.enabled:
        raise _to_http_error(
            request=request,
            status_code=404,
            error="admin_disabled",
            message="管理面当前关闭。",
            component="admin_policy",
            retryable=False,
        )
    principal = getattr(request.state, "principal", None)
    roles = set(getattr(principal, "roles", frozenset()))
    if not roles.intersection(set(settings.admin.allowed_roles)):
        raise _to_http_error(
            request=request,
            status_code=403,
            error="admin_forbidden",
            message="当前身份没有管理面权限。",
            component="admin_policy",
            retryable=False,
        )


def _service(request: Request) -> IngestService:
    settings = request.app.state.settings
    return IngestService(
        corpus_dir=settings.corpus_root,
        vector_store_dir=settings.index.vector_store_dir,
        manifest_path=settings.index.manifest_path,
        artifacts_dir=settings.artifacts_dir,
        acl_registry_path=settings.index.acl_registry_path,
        max_upload_bytes=settings.admin.max_upload_bytes,
        on_index_published=request.app.state.runtime_container.reset_index_dependencies,
    )


def _get_request_id(request: Request) -> str:
    """从 request.state 中读取 request_id；没有时给出兜底值。"""
    return str(getattr(request.state, "request_id", "")) or "unknown"


def _to_http_error(
    *,
    request: Request,
    status_code: int,
    error: str,
    message: str,
    component: str,
    retryable: bool,
) -> HTTPException:
    """构造与 Phase C 错误响应风格一致的 HTTPException。"""
    return HTTPException(
        status_code=status_code,
        detail={
            "request_id": _get_request_id(request),
            "error": error,
            "message": message,
            "component": component,
            "retryable": retryable,
        },
    )


@router.post("/api/ingest")
async def ingest_document(
    request: Request,
    file: UploadFile = File(...),
    source_category: str = Form("external"),
) -> dict:
    """上传单个 .md/.txt 文档，并触发全量 rebuild index。"""
    _require_admin(request)
    service = _service(request)

    try:
        result = await service.ingest_upload(
            file=file,
            source_category=source_category,
        )
    except UnsupportedFileTypeError as exc:
        raise _to_http_error(
            request=request,
            status_code=400,
            error="unsupported_file_type",
            message=str(exc),
            component="ingest",
            retryable=False,
        ) from exc
    except EmptyDocumentError as exc:
        raise _to_http_error(
            request=request,
            status_code=400,
            error="empty_document",
            message=str(exc),
            component="ingest",
            retryable=False,
        ) from exc
    except UploadTooLargeError as exc:
        raise _to_http_error(
            request=request,
            status_code=413,
            error="upload_too_large",
            message=str(exc),
            component="ingest",
            retryable=False,
        ) from exc
    except ValueError as exc:
        raise _to_http_error(
            request=request,
            status_code=400,
            error="invalid_request",
            message=str(exc),
            component="ingest",
            retryable=False,
        ) from exc
    except VectorStoreRebuildError as exc:
        raise _to_http_error(
            request=request,
            status_code=500,
            error="vector_store_write_failed",
            message=str(exc),
            component="local_vector_store",
            retryable=True,
        ) from exc

    return {
        "request_id": _get_request_id(request),
        **result,
    }


@router.get("/api/documents")
def list_documents(request: Request, source_category: Optional[str] = None) -> dict:
    """返回当前 corpus 中的文档列表。"""
    _require_admin(request)
    service = _service(request)

    try:
        documents = service.list_documents(source_category=source_category)
    except ValueError as exc:
        raise _to_http_error(
            request=request,
            status_code=400,
            error="invalid_request",
            message=str(exc),
            component="documents",
            retryable=False,
        ) from exc

    return {
        "request_id": _get_request_id(request),
        "documents": documents,
        "count": len(documents),
    }


@router.delete("/api/documents/{doc_id:path}")
def delete_document(request: Request, doc_id: str) -> dict:
    """删除指定文档，并触发全量 rebuild index。"""
    _require_admin(request)
    service = _service(request)

    try:
        result = service.delete_document(doc_id=doc_id)
    except InvalidDocumentIdError as exc:
        raise _to_http_error(
            request=request,
            status_code=400,
            error="invalid_request",
            message=str(exc),
            component="documents",
            retryable=False,
        ) from exc
    except DocumentNotFoundError as exc:
        raise _to_http_error(
            request=request,
            status_code=404,
            error="document_not_found",
            message=str(exc),
            component="documents",
            retryable=False,
        ) from exc
    except VectorStoreRebuildError as exc:
        raise _to_http_error(
            request=request,
            status_code=500,
            error="vector_store_write_failed",
            message=str(exc),
            component="local_vector_store",
            retryable=True,
        ) from exc

    return {
        "request_id": _get_request_id(request),
        **result,
    }
