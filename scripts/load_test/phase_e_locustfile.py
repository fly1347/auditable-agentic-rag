"""
程序作用：
- Phase E Step 11D 的最小 Locust 部署观测压测脚本。
- 默认只压测已启动的 Phase E API：/health、/metrics。
- 用于验证 Docker API 在轻量请求下 health / metrics 持续可用。
- 不压测 /api/chat/debug，避免把功能链路、模型调用、payload schema 问题混入部署观测 smoke。

结构：
- PhaseELoadUser: Locust HttpUser，包含 health / metrics 两类请求。
"""

from __future__ import annotations

from locust import HttpUser, between, task


class PhaseELoadUser(HttpUser):
    """Phase E 最小部署观测压测用户。"""

    wait_time = between(1, 2)

    @task(3)
    def health(self) -> None:
        """验证 /health 在压测期间持续可用。"""
        self.client.get("/health", name="/health")

    @task(2)
    def metrics(self) -> None:
        """验证 /metrics 在压测期间持续可用。"""
        self.client.get("/metrics", name="/metrics")
