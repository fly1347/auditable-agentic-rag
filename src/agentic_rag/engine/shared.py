"""Shared online stages used by both migration and target engines."""

from __future__ import annotations

from typing import Any, Callable

from agentic_rag.config import AppConfig
from agentic_rag.execution.command import QueryCommand
from agentic_rag.execution.legacy_projection import project_answer_into_record
from agentic_rag.execution.record import CanonicalExecutionRecord
from agentic_rag.policy.egress import egress_scope
from agentic_rag.policy.principal import Principal


def execute_shared_stages(
    *,
    config: AppConfig,
    command: QueryCommand,
    principal: Principal,
    record: CanonicalExecutionRecord,
    retriever: Any,
    query_func: Callable[..., Any],
    execution_profile: str,
) -> tuple[Any, CanonicalExecutionRecord]:
    """Run the one corrected retrieval/generation chain and project one CER."""

    egress_decisions: list[dict[str, object]] = []
    # Query text has no source ACL yet.  Treat it as restricted unless a
    # trusted adapter explicitly grants the narrowly scoped public-egress role;
    # admin status must never imply permission to export data.
    query_visibility = "public" if "public_egress" in principal.roles else "internal"
    try:
        generator_profile = config.generator.get_profile()
        judge_profile = config.generator.get_profile(config.execution.judge_profile)
        sufficiency_mode = (
            config.execution.orchestrated_sufficiency_mode
            if execution_profile == "orchestrated"
            else "binary"
        )
        with egress_scope(
            config.egress,
            default_visibilities=(query_visibility,),
            recorder=egress_decisions.append,
        ):
            answer = query_func(
                query=command.normalized_query(),
                topk=int(command.topk or config.topk),
                rerank_enabled=bool(config.rerank.enabled),
                rerank_model=str(config.rerank.model),
                rerank_candidate_topk=int(config.rerank.candidate_topk),
                rerank_topn=int(config.rerank.topn),
                selective_rerank_enabled=bool(config.rerank.selective_enabled),
                selective_rerank_gap_threshold=float(config.rerank.selective_gap_threshold),
                selective_rerank_apply_on_first_round=bool(config.rerank.selective_apply_on_first_round),
                selective_rerank_apply_on_second_round=bool(config.rerank.selective_apply_on_second_round),
                user_context={
                    "user_id": principal.principal_id,
                    "roles": sorted(principal.roles),
                    "groups": sorted(principal.groups),
                    "tenant_id": principal.tenant_id,
                    "trusted": True,
                },
                retriever_instance=retriever,
                max_chunks_in_prompt=int(config.prompt.max_chunks),
                max_chars_per_chunk=config.prompt.max_chars_per_chunk,
                citation_fallback_n=0 if not config.citation.allow_system_fallback else 2,
                generator_profile=generator_profile,
                judge_profile=judge_profile,
                sufficiency_mode=sufficiency_mode,
            )
    finally:
        record.policy["egress"] = list(egress_decisions)
        for decision in egress_decisions:
            record.append_event(
                "EGRESS_DECISION",
                stage=str(decision.get("stage") or "provider"),
                payload=dict(decision),
            )
    answer.flags["egress_decisions"] = list(egress_decisions)
    answer.flags["execution_profile"] = str(execution_profile)
    project_answer_into_record(record, answer)
    return answer, record


__all__ = ["execute_shared_stages"]
