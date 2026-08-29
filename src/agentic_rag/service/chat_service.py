"""
程序作用：
把统一应用服务与 CER 投影成普通或调试版聊天 API 响应，并补充审计、指标和结构化日志。

整体结构：
1）ChatService 接收请求、解析可信身份并调用 RagApplicationService；
2）将答案、引用、步骤、策略、用量和耗时转换成 API DTO；
3）辅助函数从模型调用底账重算规范用量，避免未知字段被静默记成 0。
"""

from __future__ import annotations

import os
import time
from typing import Any, Optional

from agentic_rag.api.schemas import (
    AgenticStepDTO,
    ChatResponse,
    CitationDTO,
    DebugChatResponse,
    RetrievedChunkDTO,
    TimingsDTO,
)
from agentic_rag.audit.record import build_audit_record_from_debug_response
from agentic_rag.audit.writer import append_audit_record
from agentic_rag.config import load_config
from agentic_rag.execution.command import QueryCommand
from agentic_rag.execution.legacy_projection import aggregate_model_call_usage
from agentic_rag.execution.record import CanonicalExecutionRecord
from agentic_rag.observability.metrics import record_chat_result, record_error
from agentic_rag.observability.structured_logging import write_log
from agentic_rag.policy.principal import Principal
from agentic_rag.service.application_service import RagApplicationService
from agentic_rag.types import Answer


class ChatService:
    """执行一次聊天请求并生成对应 API 响应。"""
    def __init__(self, application_service: Optional[RagApplicationService] = None) -> None:
        if application_service is None:
            config_path = os.getenv("AGENTIC_RAG_CONFIG", "config.yaml")
            application_service = RagApplicationService(load_config(config_path))
        self.application_service = application_service

    def chat(
        self,
        query: str,
        principal: Principal,
        *,
        session_id: Optional[str] = None,
        request_id: Optional[str] = None,
        debug: bool = False,
        profile: Optional[str] = None,
    ) -> ChatResponse:
        started = time.perf_counter()
        command = QueryCommand(
            query=query,
            profile=profile or self.application_service.config.execution.default_profile,
            request_id=request_id,
            session_id=session_id,
            debug=debug,
        )
        result = self.application_service.execute(command, principal)
        answer = result.answer
        record = result.record

        projection_started = time.perf_counter()
        if debug:
            response: ChatResponse = self._debug_response(answer, record, session_id)
        else:
            response = self._chat_response(answer, record, session_id)
        serialization_ms = (time.perf_counter() - projection_started) * 1000.0
        response.timings.serialization_ms = serialization_ms
        response.timings.api_overhead_ms = max(
            0.0,
            (time.perf_counter() - started) * 1000.0
            - float(record.timing.get("service_total_ms") or 0.0)
            - serialization_ms,
        )

        audit_projection = (
            response
            if isinstance(response, DebugChatResponse)
            else self._debug_response(answer, record, session_id)
        )
        self._write_audit(audit_projection, record)
        self._record_metrics(response, record)
        return response

    def _chat_response(
        self,
        answer: Answer,
        record: CanonicalExecutionRecord,
        session_id: Optional[str],
    ) -> ChatResponse:
        flags = dict(answer.flags or {})
        status = str(record.outcome.get("status") or "")
        refused = status == "REFUSED" or bool(flags.get("refused", False))
        return ChatResponse(
            request_id=record.identity.get("request_id"),
            session_id=session_id,
            profile=record.provenance.get("profile"),
            answer=str(answer.answer_text),
            citations=[
                CitationDTO(
                    source_id=str(item.source_id),
                    chunk_id=str(item.chunk_id),
                    offset_start=int(item.offset_start),
                    score=float(item.score),
                )
                for item in list(answer.citations or [])
            ],
            retrieved_chunks=[
                RetrievedChunkDTO(
                    source_id=str(item.source_id),
                    chunk_id=str(item.chunk_id),
                    offset_start=int(item.offset_start),
                    offset_end=int(item.offset_end),
                    text_preview=None,
                )
                for item in list(answer.used_chunks or [])
            ],
            timings=TimingsDTO(
                total_ms=_optional_float(record.timing.get("service_total_ms") or answer.timing_ms),
                engine_init_ms=_optional_float(record.timing.get("engine_init_ms")),
                engine_ms=_optional_float(record.timing.get("engine_ms")),
                pipeline_total_ms=_optional_float(record.timing.get("pipeline_total_ms")),
                retrieval_ms=_optional_float(answer.retrieval_ms),
                generation_ms=_optional_float(answer.generation_ms),
                llm_generate_ms=_optional_float(answer.llm_generate_ms),
                first_retrieval_ms=_optional_float(flags.get("first_retrieval_ms")),
                second_retrieval_ms=_optional_float(flags.get("second_retrieval_ms")),
                first_sufficiency_ms=_optional_float(flags.get("first_sufficiency_ms")),
                second_sufficiency_ms=_optional_float(flags.get("second_sufficiency_ms")),
                query_rewrite_ms=_optional_float(flags.get("query_rewrite_ms")),
                queue_wait_ms=_optional_float(record.timing.get("queue_wait_ms")),
                api_overhead_ms=0.0,
                serialization_ms=0.0,
            ),
            path=record.route.get("actual_route"),
            refused=refused,
            refused_reason=record.outcome.get("refusal_reason") or flags.get("refuse_reason"),
            degraded=bool(flags.get("degraded", False)),
            degraded_reasons=list(flags.get("degraded_reasons", []) or []),
        )

    def _debug_response(
        self,
        answer: Answer,
        record: CanonicalExecutionRecord,
        session_id: Optional[str],
    ) -> DebugChatResponse:
        base = self._chat_response(answer, record, session_id)
        flags = dict(answer.flags or {})
        record_dict = record.to_dict()
        usage = _usage_projection(record)
        return DebugChatResponse(
            **base.model_dump(),
            flags=flags,
            agentic_steps=[
                AgenticStepDTO(
                    step=str(step.step),
                    output=str(step.output),
                    duration_ms=float(step.duration_ms),
                )
                for step in list(answer.agentic_steps or [])
            ],
            evaluation_context=dict(record.evaluation or {}),
            vector_store_context={
                "index_build_id": record.provenance.get("index_build_id"),
                "corpus_hash": record.provenance.get("corpus_hash"),
            },
            workflow_trace={
                "events": record_dict["events"],
                "route": record.route,
                "outcome": record.outcome,
            },
            observability={"model_calls": record.model_calls, "errors": record.errors},
            retrieval_diagnostics={
                "retrieval": record.retrieval,
                "rerank": record.rerank,
                "merge": record.merge,
                "evidence": record.evidence,
                "prompt": record.prompt,
            },
            sufficiency_diagnostics=dict(record.sufficiency or {}),
            model_identity={
                "generator": next(
                    (call.get("identity", {}) for call in reversed(record.model_calls) if call.get("role") == "generator"),
                    {},
                )
            },
            usage=usage,
            timing=dict(record.timing or {}),
            rerank=dict(record.rerank or {}),
            generation_context=dict(flags.get("generation_context", {}) or {}),
            policy_trace=dict(record.policy or {}),
            execution_record=record_dict,
        )

    def _write_audit(
        self,
        response: DebugChatResponse,
        record: CanonicalExecutionRecord,
    ) -> None:
        try:
            append_audit_record(build_audit_record_from_debug_response(response))
        except Exception as exc:  # audit failure is visible but does not erase the answer
            record_error(error_code="audit_write_failed")
            write_log(
                level="WARNING",
                stage="audit",
                event="audit_write_failed",
                request_id=str(record.identity.get("request_id") or ""),
                error_code=type(exc).__name__,
                duration_ms=0.0,
            )

    def _record_metrics(self, response: ChatResponse, record: CanonicalExecutionRecord) -> None:
        record_chat_result(
            status="refused" if response.refused else "success",
            path=str(response.path or "UNKNOWN"),
            refused=response.refused,
            refused_reason=response.refused_reason,
        )
        write_log(
            level="INFO",
            stage="api_chat",
            event="chat_completed",
            request_id=str(record.identity.get("request_id") or ""),
            session_id=response.session_id,
            path=str(response.path or "UNKNOWN"),
            refused=response.refused,
            refused_reason=response.refused_reason,
            duration_ms=response.timings.total_ms,
            queue_wait_ms=response.timings.queue_wait_ms,
            api_overhead_ms=response.timings.api_overhead_ms,
            serialization_ms=response.timings.serialization_ms,
            citation_count=len(response.citations),
            retrieved_chunk_count=len(response.retrieved_chunks),
        )


def _usage_projection(record: CanonicalExecutionRecord) -> dict[str, Any]:
    # 从逐次调用底账重算规范总计，避免缺失的 reasoning、cache、Token 或成本字段在 API 视图中静默变成 0。
    totals = aggregate_model_call_usage(list(record.model_calls))
    return {**dict(record.usage or {}), **totals, "model_calls": list(record.model_calls)}


def _optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


__all__ = ["ChatService"]
