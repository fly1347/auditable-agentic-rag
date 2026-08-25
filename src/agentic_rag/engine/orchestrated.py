"""Target orchestrated engine over the corrected shared stage graph."""

from __future__ import annotations

from typing import Any, Callable, Optional

from agentic_rag.config import AppConfig
from agentic_rag.engine.baseline import EngineResult
from agentic_rag.engine.shared import execute_shared_stages
from agentic_rag.execution.command import QueryCommand
from agentic_rag.execution.record import CanonicalExecutionRecord
from agentic_rag.policy.principal import Principal


class OrchestratedEngine:
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
