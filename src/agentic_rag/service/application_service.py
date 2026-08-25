"""Single controlled application service for every query entry point."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional
from uuid import uuid4

from agentic_rag.config import AppConfig
from agentic_rag.execution.command import QueryCommand
from agentic_rag.execution.record import CanonicalExecutionRecord, JsonlRecordSink
from agentic_rag.policy.principal import Principal
from agentic_rag.policy.security import assess_security_policy, build_security_policy_trace
from agentic_rag.service.container import RuntimeContainer
from agentic_rag.service.concurrency_guard import GenerationQueueFull, acquire_generation_slot
from agentic_rag.types import Answer


class ProfileUnavailable(RuntimeError):
    pass


class ApplicationExecutionError(RuntimeError):
    def __init__(self, message: str, record: CanonicalExecutionRecord) -> None:
        super().__init__(message)
        self.record = record


@dataclass(frozen=True)
class ApplicationResult:
    answer: Answer
    record: CanonicalExecutionRecord


class RagApplicationService:
    def __init__(
        self,
        config: AppConfig,
        *,
        container: Optional[RuntimeContainer] = None,
        engines: Optional[Mapping[str, Any]] = None,
        record_sink: Optional[JsonlRecordSink] = None,
    ) -> None:
        self.config = config
        self.container = container or RuntimeContainer(config)
        self._engines = dict(engines or {})
        self.record_sink = record_sink
        if self.record_sink is None and config.records.enabled:
            self.record_sink = JsonlRecordSink(config.records.path)

    def execute(self, command: QueryCommand, principal: Principal) -> ApplicationResult:
        service_started = time.perf_counter()
        query = command.normalized_query()
        profile = str(command.profile or self.config.execution.default_profile)
        if profile not in self.config.execution.enabled_profiles:
            raise ProfileUnavailable(f"execution profile is not enabled: {profile}")

        request_id = command.request_id or f"req_{uuid4().hex[:12]}"
        index_provenance = self.container.index_provenance()
        record = CanonicalExecutionRecord(
            schema_version=self.config.records.schema_version,
            identity={
                "request_id": request_id,
                "run_id": command.run_id,
                "qid": command.qid,
                "session_id": command.session_id,
            },
            provenance={
                "code_ref": os.getenv("AGENTIC_RAG_CODE_REF", "workspace"),
                "config_hash": self.config.fingerprint(),
                **index_provenance,
                "profile": profile,
                "engine": "baseline_adapter" if profile == "baseline" else "orchestrated_engine",
            },
            principal=principal.to_dict(),
            query=query,
        )
        record.append_event("REQUEST_ACCEPTED", stage="application_service")
        record.append_event(
            "PRINCIPAL_RESOLVED",
            stage="trusted_adapter",
            payload={"principal_id": principal.principal_id, "auth_mode": principal.auth_mode},
        )

        safety = assess_security_policy(query=query)
        record.policy["query_safety"] = build_security_policy_trace(safety).get(
            "security_policy", {}
        )
        record.append_event(
            "QUERY_SAFETY_CHECK",
            stage="query_safety",
            payload={
                "allowed": not bool(safety.refusal_recommended),
                "reason": safety.refusal_reason,
            },
        )
        if safety.refusal_recommended:
            reason = str(safety.refusal_reason or "unsafe_or_private_boundary")
            answer = _refusal_answer(query, reason)
            record.append_event("REFUSAL", stage="query_safety", payload={"reason": reason})
            record.finish("REFUSED", answer=answer.answer_text, refusal_reason=reason, citations=[])
            record.timing = {
                "queue_wait_ms": 0.0,
                "engine_ms": 0.0,
                "service_total_ms": (time.perf_counter() - service_started) * 1000.0,
            }
            self._write(record)
            return ApplicationResult(answer=answer, record=record)

        try:
            with acquire_generation_slot() as ticket:
                engine_started = time.perf_counter()
                engine = self._engine(profile)
                engine_init_ms = (time.perf_counter() - engine_started) * 1000.0
                result = engine.execute(command, principal, record)
                engine_ms = (time.perf_counter() - engine_started) * 1000.0
            result.record.timing = {
                **dict(result.record.timing or {}),
                "queue_wait_ms": float(ticket.queue_wait_ms),
                "engine_init_ms": engine_init_ms,
                "engine_ms": engine_ms,
                "service_total_ms": (time.perf_counter() - service_started) * 1000.0,
            }
            self._write(result.record)
            return ApplicationResult(answer=result.answer, record=result.record)
        except Exception as exc:
            record.errors.append(
                {
                    "stage": "engine",
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                    "retryable": isinstance(exc, GenerationQueueFull),
                }
            )
            record.append_event(
                "EXECUTION_ERROR",
                stage="engine",
                payload={"error_type": type(exc).__name__},
            )
            record.finish("ERROR", answer=None, refusal_reason=None, citations=[])
            record.timing = {
                "service_total_ms": (time.perf_counter() - service_started) * 1000.0,
            }
            self._write(record)
            raise ApplicationExecutionError(str(exc), record) from exc

    def _engine(self, profile: str) -> Any:
        if profile in self._engines:
            return self._engines[profile]
        if profile == "baseline":
            engine = self.container.baseline_engine()
            self._engines[profile] = engine
            return engine
        if profile == "orchestrated":
            engine = self.container.orchestrated_engine()
            self._engines[profile] = engine
            return engine
        raise ProfileUnavailable(f"execution profile is not implemented: {profile}")

    def _write(self, record: CanonicalExecutionRecord) -> None:
        if self.record_sink is not None:
            self.record_sink.append(record)


def _refusal_answer(query: str, reason: str) -> Answer:
    text = (
        "我不能按当前请求继续处理。\n"
        "请移除敏感内容或将问题限定在允许访问的文档范围内。"
    )
    return Answer(
        query=query,
        answer_text=text,
        citations=[],
        used_chunks=[],
        timing_ms=0.0,
        flags={
            "refused": True,
            "refuse_reason": reason,
            "has_citation": False,
            "policy_trace": {"query_safety": {"allowed": False, "reason": reason}},
        },
        agentic_steps=[],
    )


__all__ = [
    "ApplicationExecutionError",
    "ApplicationResult",
    "ProfileUnavailable",
    "RagApplicationService",
]
