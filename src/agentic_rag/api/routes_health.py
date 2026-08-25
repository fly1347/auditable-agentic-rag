"""
程序作用：
- 提供 Phase E /health 端点。
- 返回 API、provider 配置、local vector store 与 deployment policy 的结构化健康状态。

整体结构：
1. 创建 APIRouter；
2. 调用 HealthService.get_health；
3. 保持路由层轻量，不在这里写依赖检查细节。
"""

from fastapi import APIRouter, Request

from agentic_rag.service.health_service import HealthService

router = APIRouter()


@router.get("/health")
def health(request: Request):
    """返回服务健康检查结果。"""
    settings = request.app.state.settings
    return HealthService(settings=settings).get_health()
