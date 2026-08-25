"""
作用：
Phase C FastAPI 服务入口（最小骨架版）

结构：
- 创建 FastAPI app
- 注册基础路由（health / version / metrics / chat / ingest）
- 后续逐步接入 middleware / service / pipeline
"""

import os

from fastapi import FastAPI

from agentic_rag import __version__
from agentic_rag.api.middleware import request_id_middleware
from agentic_rag.api.routes_health import router as health_router
from agentic_rag.api.routes_version import router as version_router
from agentic_rag.api.routes_metrics import router as metrics_router
from agentic_rag.api.routes_chat import router as chat_router
from agentic_rag.api.routes_ingest import router as ingest_router
from agentic_rag.config import AppConfig, load_config
from agentic_rag.policy.principal import StaticTokenAuthAdapter
from agentic_rag.service.application_service import RagApplicationService
from agentic_rag.service.chat_service import ChatService
from agentic_rag.service.container import RuntimeContainer


def create_app(settings: AppConfig | None = None) -> FastAPI:
    settings = settings or load_config(os.getenv("AGENTIC_RAG_CONFIG", "config.yaml"))
    app = FastAPI(
        title="Agentic RAG Service",
        version=__version__,
    )

    container = RuntimeContainer(settings)
    application_service = RagApplicationService(settings, container=container)
    app.state.settings = settings
    app.state.runtime_container = container
    app.state.application_service = application_service
    app.state.chat_service = ChatService(application_service)
    app.state.auth_adapter = StaticTokenAuthAdapter(settings.auth)

    # 注册 middleware
    app.middleware("http")(request_id_middleware)

    # 注册路由
    app.include_router(health_router)
    app.include_router(version_router, prefix="/api")
    app.include_router(metrics_router)
    app.include_router(chat_router, prefix="/api")
    app.include_router(ingest_router)

    return app


app = create_app()
