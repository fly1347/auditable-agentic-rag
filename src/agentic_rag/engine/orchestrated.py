"""
程序作用：
提供 orchestrated profile 的引擎入口，在共享执行拓扑上启用结构化 sufficiency 合同。

整体结构：
1）OrchestratedEngine 保存配置、检索器和可替换查询函数；
2）execute 创建执行记录并调用共享在线阶段；
3）返回与 baseline 一致的 EngineResult，便于统一服务层处理。
"""

from __future__ import annotations

from typing import Any, Callable, Optional

from agentic_rag.config import AppConfig
from agentic_rag.engine.baseline import EngineResult
from agentic_rag.engine.shared import execute_shared_stages
from agentic_rag.execution.command import QueryCommand
from agentic_rag.execution.record import CanonicalExecutionRecord
from agentic_rag.policy.principal import Principal


class OrchestratedEngine:
    """把 orchestrated 查询链路包装成统一引擎接口。"""
    name = "orchestrated_engine"

    def __init__(
        self,
        config: AppConfig,
        *,
        retriever: Any = None,
        query_func: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.config = config
        self.retriever = retriever
        self._query_func = query_func

    def execute(
        self,
        command: QueryCommand,
        principal: Principal,
        record: CanonicalExecutionRecord,
    ) -> EngineResult:
        query_func = self._query_func
        if query_func is None:
            from agentic_rag.query_pipeline import query as query_func
        answer, record = execute_shared_stages(
            config=self.config,
            command=command,
            principal=principal,
            record=record,
            retriever=self.retriever,
            query_func=query_func,
            execution_profile="orchestrated",
        )
        return EngineResult(answer=answer, record=record)


__all__ = ["OrchestratedEngine"]
