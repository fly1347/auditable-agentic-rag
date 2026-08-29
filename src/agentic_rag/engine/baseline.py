"""
程序作用：
为公开默认 baseline 链路提供引擎适配器，复用历史 query pipeline，并把执行过程统一投影成 CER。

整体结构：
1）EngineResult 统一返回业务答案与规范执行记录；
2）BaselineEngineAdapter 保存配置和进程级依赖；
3）execute 调用共享在线阶段完成一次 baseline 查询。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from agentic_rag.config import AppConfig
from agentic_rag.execution.command import QueryCommand
from agentic_rag.execution.record import CanonicalExecutionRecord
from agentic_rag.policy.principal import Principal
from agentic_rag.engine.shared import execute_shared_stages


@dataclass(frozen=True)
class EngineResult:
    answer: Any
    record: CanonicalExecutionRecord


class BaselineEngineAdapter:
    """把 baseline 查询链路包装成统一引擎接口。"""
    name = "baseline_adapter"

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
            execution_profile="baseline",
        )
        return EngineResult(answer=answer, record=record)


__all__ = ["BaselineEngineAdapter", "EngineResult"]
