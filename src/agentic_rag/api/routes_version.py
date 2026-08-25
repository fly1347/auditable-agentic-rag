"""
程序作用：
- 提供 Phase C /api/version 端点。
- 返回服务版本、D-lite-7-run3 冻结配置、模型与向量库配置摘要。

整体结构：
1. 创建 APIRouter；
2. 调用 HealthService.get_version；
3. version 只读配置和 manifest，不触发 RAG pipeline。
"""

from fastapi import APIRouter, Request

from agentic_rag.service.health_service import HealthService

router = APIRouter()


@router.get("/version")
def version(request: Request):
    """返回服务与 pipeline 配置版本信息。"""
    settings = request.app.state.settings
    return HealthService(settings=settings).get_version()
