"""
文件作用：
定义 Phase E /metrics 路由。

整体结构：
1）调用 MetricsService；
2）返回 Prometheus text format；
3）MetricsService 内部追加 Phase E policy / deployment 指标。
"""

from fastapi import APIRouter, Response

from agentic_rag.service.metrics_service import MetricsService

router = APIRouter()

metrics_service = MetricsService()


@router.get("/metrics")
def metrics() -> Response:
    """返回 Prometheus text format 指标。"""
    return Response(
        content=metrics_service.render(),
        media_type="text/plain; version=0.0.4",
    )
