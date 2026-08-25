"""
文件作用：
定义 chat 相关 API 路由。

整体结构：
1）POST /api/chat：普通问答；
2）POST /api/chat/debug：debug 问答；
3）路由层只处理 HTTP 入参、前置依赖 guard 和 response_model，不写业务映射逻辑。
"""

from fastapi import APIRouter, HTTPException, Request

from agentic_rag.api.schemas import ChatRequest, ChatResponse, DebugChatResponse
from agentic_rag.observability.tracing_context import get_request_id
from agentic_rag.policy.principal import Principal
from agentic_rag.service.application_service import ApplicationExecutionError, ProfileUnavailable

router = APIRouter()

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request):
    """普通 chat，不返回完整 debug 字段。"""

    request_id = get_request_id()
    return _run_chat(req, request, request_id=request_id, debug=False)


@router.post("/chat/debug", response_model=DebugChatResponse)
def chat_debug(req: ChatRequest, request: Request):
    """debug chat，返回 agentic_steps、workflow_trace 与诊断上下文。"""

    request_id = get_request_id()
    principal = _principal(request)
    if not (principal.roles & {"admin", "debug"}):
        raise HTTPException(status_code=403, detail="debug access requires admin or debug role")
    return _run_chat(req, request, request_id=request_id, debug=True)


def _principal(request: Request) -> Principal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, Principal):
        raise HTTPException(status_code=401, detail="trusted principal is missing")
    return principal


def _run_chat(req: ChatRequest, request: Request, *, request_id: str, debug: bool):
    try:
        return request.app.state.chat_service.chat(
            query=req.query,
            principal=_principal(request),
            session_id=req.session_id,
            request_id=request_id,
            debug=debug,
            profile=req.profile,
        )
    except ProfileUnavailable as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ApplicationExecutionError as exc:
        is_queue = any(
            item.get("error_type") == "GenerationQueueFull"
            for item in exc.record.errors
        )
        raise HTTPException(
            status_code=429 if is_queue else 500,
            detail={
                "request_id": exc.record.identity.get("request_id"),
                "error": exc.record.errors[-1].get("error_type") if exc.record.errors else "execution_error",
                "message": str(exc),
                "retryable": is_queue,
            },
        ) from exc
