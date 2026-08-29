"""
文件作用：
1）顶层 query 流程编排，接入 D-lite 最小控制流：route → retrieve → sufficiency → re-retrieve → generate/reject；
2）在现有 v1.5 sufficiency / re-retrieve 基础上，新增最小 Router 与 DECOMPOSE 双检索路径；
3）把控制流步骤写入 agentic_steps，便于后续 run_pipeline_regression / summarize 做路径判断；
4）继续保持兼容现有 Retriever / Generator / Answer 结构，不改旧字段语义，只新增 flags 与 agentic_steps；
5）本版新增 selective rerank：仅在分数压缩区间触发重排，并记录 before/after 观测信息；
6）对 rewrite / decompose / rerank 的外部依赖失败做结构化降级，避免服务层裸 500。

整体结构：
1）配置与模型辅助函数负责 generator、rewrite、decompose 和 sufficiency 调用；
2）检索辅助函数执行 ACL、路由、多路融合、可选重排与二轮检索；
3）query 串起受限工作流并返回 Answer，run 提供兼容入口。
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agentic_rag.config import AppConfig, GeneratorProfileConfig, load_config
from agentic_rag.control.router import RouteDecision, route_query
from dataclasses import asdict, is_dataclass

from agentic_rag.control.sufficiency import (
    SufficiencyJudgeError,
    SufficiencyJudgeTimeout,
    judge_sufficiency_with_evidence_packet,
    judge_sufficiency_with_model_call,
)
from agentic_rag.evidence.packet import build_evidence_packet
from agentic_rag.generate.generator import GeneratorConfig, RAGGenerator
from agentic_rag.execution.snapshots import build_evidence_snapshot
from agentic_rag.policy.security import assess_security_policy, build_security_policy_trace
from agentic_rag.policy.egress import chunk_visibilities
from agentic_rag.policy.access import (
    PolicyDecision,
    SourceACL,
    UserContext,
    can_read_source,
    parse_source_acl,
)
from agentic_rag.llm.client import LLMConfig, OllamaClient
from agentic_rag.retrieve.reranker import (
    CrossEncoderReranker,
    compute_top1_topk_gap,
    should_trigger_selective_rerank,
)
from agentic_rag.retrieve.retriever import Retriever
from agentic_rag.retrieve.fusion import FusionInput, retrieval_event, rrf_fuse
from agentic_rag.types import AgenticStep, Answer, Chunk, RetrievalResult

_DEBUG_PIPELINE: bool = True

_PIPELINE_REFUSAL_TEMPLATE: str = (
    "我在当前语料中找不到足够证据来回答这个问题。\n"
    "请提供更多上下文，或把问题限定在已提供的文档范围内。"
)


def _env_has_generator_override() -> bool:
    """判断当前 shell 是否显式设置了 generator 环境变量。"""
    keys = [
        "GENERATOR_BACKEND",
        "GENERATOR_MODEL",
        "GENERATOR_API_BASE_URL",
        "GENERATOR_API_KEY_ENV",
        "GENERATOR_PROVIDER_TAG",
    ]
    return any(str(os.getenv(key, "") or "").strip() for key in keys)


def _llm_config_from_generator_profile(profile: GeneratorProfileConfig) -> LLMConfig:
    """把 config.yaml 中的 generator profile 转成 LLMConfig。"""
    if str(profile.backend).strip().lower() == "fail_close":
        raise RuntimeError("generator profile is fail_close; no LLM client can be created")
    if not bool(profile.enabled):
        raise RuntimeError(f"generator profile disabled: {profile.name}")

    return LLMConfig(
        backend=str(profile.backend),
        model=str(profile.model),
        base_url=str(profile.base_url),
        api_key_env=str(profile.api_key_env),
        provider_tag=str(profile.provider_tag),
        temperature=float(profile.temperature),
        top_p=float(profile.top_p),
        num_predict=int(profile.max_tokens),
        timeout_s=float(profile.timeout_s),
        max_retries=int(profile.max_retries),
    )


def _build_default_llm_config(
    profile: Optional[GeneratorProfileConfig] = None,
) -> LLMConfig:
    """构造默认 LLMConfig：环境变量显式覆盖优先，否则读取 config.yaml 的默认 profile。"""
    if profile is not None:
        return _llm_config_from_generator_profile(profile)
    if _env_has_generator_override():
        return LLMConfig()

    app_cfg = load_config("config.yaml")
    profile = app_cfg.generator.get_profile()
    return _llm_config_from_generator_profile(profile)


def _build_default_llm_client(
    *,
    stage: str = "generator",
    data_visibilities: Optional[Tuple[str, ...]] = None,
    profile: Optional[GeneratorProfileConfig] = None,
) -> OllamaClient:
    """构造 query pipeline 默认 LLM client，供 generate / rewrite / decompose 共用。"""
    return OllamaClient(
        cfg=_build_default_llm_config(profile),
        stage=stage,
        data_visibilities=data_visibilities,
    )


def _append_step(agentic_steps: List[AgenticStep], step: str, output: str, duration_ms: float = 0.0) -> None:
    """向 agentic_steps 追加一步最小记录。"""
    agentic_steps.append(
        AgenticStep(
            step=str(step),
            output=str(output),
            duration_ms=float(duration_ms),
        )
    )


def _exception_summary(exc: Exception, max_chars: int = 240) -> str:
    """把外部依赖异常压缩成可进入 flags / agentic_steps 的稳定字符串。"""
    message = str(exc).replace("\n", " ").strip()
    if len(message) > int(max_chars):
        message = message[: int(max_chars)] + "..."
    return f"{type(exc).__name__}:{message}"


def _model_call_to_usage_dict(call: Any, stage: str) -> Dict[str, Any]:
    """把 ModelCallRecord 转成可进入 flags / usage.model_calls 的 dict，并补 sufficiency stage。"""
    if call is None:
        return {}

    if is_dataclass(call):
        row: Dict[str, Any] = asdict(call)
    elif isinstance(call, dict):
        row = dict(call)
    else:
        row = {}

    row["role"] = str(row.get("role") or "sufficiency_judge")
    row["stage"] = str(stage)
    return row


def _sufficiency_error_model_call(exc: Exception, elapsed_ms: float, stage: str) -> Dict[str, Any]:
    """judge 异常时也记录失败模型调用，避免成本/错误观测消失。"""
    return {
        "role": "sufficiency_judge",
        "stage": str(stage),
        "identity": {},
        "prompt_tokens": None,
        "completion_tokens": None,
        "reasoning_tokens": None,
        "cached_tokens": None,
        "cache_write_tokens": None,
        "total_tokens": None,
        "latency_ms": float(elapsed_ms),
        "estimated_cost_usd": None,
        "http_status": None,
        "api_error": True,
        "timeout": isinstance(exc, SufficiencyJudgeTimeout),
        "error_type": type(exc).__name__,
        "error_message": str(exc),
    }


def _llm_metadata_from_default_config(
    profile: Optional[GeneratorProfileConfig] = None,
) -> Dict[str, Any]:
    """LLM 调用失败时，用当前默认 profile 构造最小模型身份。"""
    try:
        cfg = _build_default_llm_config(profile)
        return {
            "provider": str(getattr(cfg, "provider_tag", "") or getattr(cfg, "backend", "")),
            "backend": str(getattr(cfg, "backend", "")),
            "configured_model": str(getattr(cfg, "model", "")),
            "provider_response_model": None,
            "resolved_model": str(getattr(cfg, "model", "")),
            "endpoint": str(getattr(cfg, "base_url", "")),
            "upstream_provider": None,
            "api_key_env": str(getattr(cfg, "api_key_env", "")),
            "api_key_hash": None,
            "network_tag": "",
            "proxy_node": "",
            "generator_backend": str(getattr(cfg, "backend", "")),
            "provider_tag": str(getattr(cfg, "provider_tag", "")),
        }
    except Exception:
        return {}


def _identity_from_llm_token_usage(token_usage: Dict[str, Any]) -> Dict[str, Any]:
    """从 LLM token_usage / metadata 中抽取模型身份。"""
    usage = dict(token_usage or {})
    return {
        "provider": usage.get("provider"),
        "backend": usage.get("backend"),
        "configured_model": usage.get("configured_model"),
        "provider_response_model": usage.get("provider_response_model"),
        "resolved_model": usage.get("resolved_model"),
        "endpoint": usage.get("endpoint"),
        "upstream_provider": usage.get("upstream_provider"),
        "api_key_env": usage.get("api_key_env"),
        "api_key_hash": usage.get("api_key_hash"),
        "network_tag": usage.get("network_tag"),
        "proxy_node": usage.get("proxy_node"),
        "generator_backend": usage.get("generator_backend"),
        "provider_tag": usage.get("provider_tag"),
    }


def _llm_model_call_dict(
    *,
    role: str,
    stage: str,
    token_usage: Optional[Dict[str, Any]],
    latency_ms: float,
    api_error: bool = False,
    timeout: bool = False,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
    profile: Optional[GeneratorProfileConfig] = None,
) -> Dict[str, Any]:
    """构造 rewrite/subquery 这类 legacy LLM 调用的 usage.model_calls 原始记录。"""
    usage = dict(token_usage or {})
    identity = (
        _identity_from_llm_token_usage(usage)
        if usage
        else _llm_metadata_from_default_config(profile)
    )

    prompt_details = usage.get("prompt_tokens_details")
    prompt_details = dict(prompt_details) if isinstance(prompt_details, dict) else {}
    completion_details = usage.get("completion_tokens_details")
    completion_details = dict(completion_details) if isinstance(completion_details, dict) else {}

    return {
        "role": str(role),
        "stage": str(stage),
        "identity": identity,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": completion_details.get("reasoning_tokens"),
        "cached_tokens": prompt_details.get("cached_tokens"),
        "cache_write_tokens": prompt_details.get("cache_write_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "latency_ms": float(latency_ms),
        "estimated_cost_usd": None,
        "http_status": None,
        "api_error": bool(api_error),
        "timeout": bool(timeout),
        "error_type": error_type,
        "error_message": error_message,
    }


def _llm_error_model_call(
    exc: Exception,
    elapsed_ms: float,
    role: str,
    stage: str,
    *,
    profile: Optional[GeneratorProfileConfig] = None,
) -> Dict[str, Any]:
    """rewrite/subquery LLM 异常时也记录失败调用。"""
    return _llm_model_call_dict(
        role=str(role),
        stage=str(stage),
        token_usage=None,
        latency_ms=float(elapsed_ms),
        api_error=True,
        timeout="timeout" in type(exc).__name__.lower() or "timeout" in str(exc).lower(),
        error_type=type(exc).__name__,
        error_message=str(exc),
        profile=profile,
    )


def _rewrite_query_for_retrieval(
    query: str,
    *,
    generator_profile: Optional[GeneratorProfileConfig] = None,
) -> Tuple[str, Dict[str, Any]]:
    """把原问题改写成更适合检索的查询，并返回 rewrite_query 模型调用记录。"""
    client = _build_default_llm_client(stage="rewrite_query", profile=generator_profile)
    prompt = f"""请把下面的问题改写成更适合知识库检索的简洁查询。

要求：
- 保持原意
- 更具体
- 不要解释
- 只输出改写后的查询

问题：
{query}
"""
    text, token_usage, llm_ms = client.generate(prompt)
    model_call = _llm_model_call_dict(
        role="rewrite_query",
        stage="rewrite_query",
        token_usage=dict(token_usage or {}),
        latency_ms=float(llm_ms),
        api_error=False,
        timeout=False,
        error_type=None,
        error_message=None,
        profile=generator_profile,
    )
    return text.strip(), model_call


def _decompose_query(
    query: str,
    *,
    generator_profile: Optional[GeneratorProfileConfig] = None,
) -> Tuple[str, str, Dict[str, Any]]:
    """把显式对比题拆成两个独立检索子查询，并返回 subquery_generator 模型调用记录。"""
    client = _build_default_llm_client(stage="decompose_query", profile=generator_profile)
    prompt = f"""请把下面的问题拆成两个独立的检索查询。

要求：
- 输出两行
- 第一行以 A: 开头
- 第二行以 B: 开头
- 每个子查询只保留一个对象、机制或侧面
- 不要解释，不要输出别的内容

问题：
{query}
"""
    text, token_usage, llm_ms = client.generate(prompt)
    model_call = _llm_model_call_dict(
        role="subquery_generator",
        stage="first_decompose",
        token_usage=dict(token_usage or {}),
        latency_ms=float(llm_ms),
        api_error=False,
        timeout=False,
        error_type=None,
        error_message=None,
        profile=generator_profile,
    )

    query_a: str = ""
    query_b: str = ""
    for raw_line in str(text or "").splitlines():
        line: str = raw_line.strip()
        line_upper: str = line.upper()
        if line_upper.startswith("A:"):
            query_a = line.split(":", 1)[1].strip()
        elif line_upper.startswith("B:"):
            query_b = line.split(":", 1)[1].strip()

    lines: List[str] = [line.strip("-• ").strip() for line in str(text or "").splitlines() if line.strip()]
    if query_a == "" and len(lines) >= 1:
        query_a = lines[0].split(":", 1)[-1].strip()
    if query_b == "" and len(lines) >= 2:
        query_b = lines[1].split(":", 1)[-1].strip()

    if query_a == "":
        query_a = str(query)
    if query_b == "":
        query_b = str(query)

    return query_a, query_b, model_call


def _hit_to_chunk(hit: Any) -> Chunk:
    offset_start: int = int(getattr(hit, "offset_start", 0))
    offset_end: int = int(getattr(hit, "offset_end", 0))
    if (offset_start == 0 and offset_end == 0) and hasattr(hit, "offset"):
        off: Any = getattr(hit, "offset")
        if isinstance(off, (tuple, list)) and len(off) == 2:
            offset_start = int(off[0])
            offset_end = int(off[1])

    return Chunk(
        chunk_id=str(getattr(hit, "chunk_id", "")),
        source_id=str(getattr(hit, "source_id", "")),
        doc_hash=str(getattr(hit, "doc_hash", "")),
        text=str(getattr(hit, "text", "")),
        offset_start=int(offset_start),
        offset_end=int(offset_end),
        metadata=dict(getattr(hit, "metadata", {}) or {}),
    )


def _retriever_output_to_retrieval_result(query: str, topk: int, out: Any, elapsed_ms: float) -> RetrievalResult:
    if isinstance(out, RetrievalResult):
        return out

    if hasattr(out, "chunks"):
        chunks_any: Any = getattr(out, "chunks", [])
        chunks: List[Chunk] = list(chunks_any or [])
        scores_any: Any = getattr(out, "scores", [])
        scores: List[float] = [float(x) for x in list(scores_any or [])]
        return RetrievalResult(
            query=str(query),
            chunks=chunks,
            scores=scores,
            topk=int(topk),
            timing_ms=float(elapsed_ms),
            access_policy=dict(getattr(out, "access_policy", {}) or {}),
            score_type=str(getattr(out, "score_type", "vector_similarity")),
        )

    hits: List[Any] = []
    if hasattr(out, "hits"):
        hits = list(getattr(out, "hits", []) or [])
    elif isinstance(out, dict):
        hits = list(out.get("hits", []) or [])
    elif isinstance(out, list):
        hits = out

    chunks: List[Chunk] = [_hit_to_chunk(h) for h in hits]
    scores: List[float] = [float(getattr(h, "score", 0.0)) for h in hits]

    return RetrievalResult(
        query=str(query),
        chunks=chunks,
        scores=scores,
        topk=int(topk),
        timing_ms=float(elapsed_ms),
        access_policy=dict(getattr(out, "access_policy", {}) or {}),
    )


def _ordered_unique_source_ids(chunks: List[Chunk]) -> List[str]:
    out: List[str] = []
    for chunk in chunks:
        source_id: str = str(chunk.source_id)
        if source_id not in out:
            out.append(source_id)
    return out


def _user_context_from_payload(payload: Optional[Dict[str, Any]]) -> UserContext:
    """把可信适配器生成的主体投影转换成检索 ACL 所需用户上下文。

    直接调用方若未带 ``trusted`` 标记，不能通过普通字典自行授予角色。
    """
    data = dict(payload or {})
    if data.get("trusted") is not True:
        return UserContext(
            user_id="anonymous",
            roles=frozenset({"anonymous"}),
            groups=frozenset(),
        )
    user_id = str(data.get("user_id") or data.get("id") or "anonymous")
    roles = data.get("roles")
    groups = data.get("groups")
    return UserContext(
        user_id=user_id,
        roles=frozenset(str(item).strip() for item in list(roles or []) if str(item).strip()),
        groups=frozenset(str(item).strip() for item in list(groups or []) if str(item).strip()),
        tenant_id=data.get("tenant_id"),
    )


def _acl_from_chunk(chunk: Chunk) -> SourceACL | None:
    """从 chunk.metadata 中解析 SourceACL。"""
    metadata = dict(getattr(chunk, "metadata", {}) or {})
    metadata.setdefault("source_id", str(chunk.source_id))
    metadata.setdefault("chunk_id", str(chunk.chunk_id))
    return parse_source_acl(metadata)


def _decision_to_dict(decision: PolicyDecision, chunk: Chunk) -> Dict[str, Any]:
    """把 ACL decision 转成 policy_trace 可序列化记录。"""
    return {
        "allowed": bool(decision.allowed),
        "decision": str(decision.decision),
        "reason": str(decision.reason),
        "user_id": str(decision.user_id),
        "visibility": decision.visibility,
        "source_id": decision.source_id or str(chunk.source_id),
        "chunk_id": str(chunk.chunk_id),
        "tenant_id_checked": bool(decision.tenant_id_checked),
    }


def _set_acl_runtime_attrs(rr: RetrievalResult, policy_trace: Dict[str, Any]) -> RetrievalResult:
    """把 ACL 运行时诊断挂到 RetrievalResult，不改变 types.py 契约。"""
    try:
        object.__setattr__(rr, "acl_checked", True)
        object.__setattr__(rr, "policy_trace", policy_trace)
    except Exception:
        pass
    return rr


def _apply_acl_filter(
    rr: RetrievalResult,
    user_context_payload: Optional[Dict[str, Any]],
    phase: str,
) -> Tuple[RetrievalResult, Dict[str, Any]]:
    """TopK 后纵深校验；真正的 ACL 候选过滤已在 vector store 前置。"""
    user = _user_context_from_payload(user_context_payload)
    kept_chunks: List[Chunk] = []
    kept_scores: List[float] = []
    decisions: List[Dict[str, Any]] = []

    missing_acl = 0
    unknown_acl = 0

    for index, chunk in enumerate(list(rr.chunks or [])):
        acl = _acl_from_chunk(chunk)
        decision = can_read_source(user, acl)

        if acl is None:
            missing_acl += 1
        elif str(acl.visibility) not in {"public", "internal_demo", "confidential"}:
            unknown_acl += 1

        decisions.append(_decision_to_dict(decision, chunk))

        if decision.allowed:
            kept_chunks.append(chunk)
            kept_scores.append(float(rr.scores[index]) if index < len(rr.scores) else 0.0)

    denied = [item for item in decisions if not item["allowed"]]
    policy_trace = {
        "access_policy": {
            "enabled": True,
            "phase": str(phase),
            "user_id": user.user_id,
            "roles": sorted(user.roles),
            "groups": sorted(user.groups),
            "tenant_id": user.tenant_id,
            "input_chunk_count": len(list(rr.chunks or [])),
            "allowed_chunk_count": len(kept_chunks),
            "denied_chunk_count": len(denied),
            "source_acl_missing_count": int(missing_acl),
            "unknown_acl_runtime_deny_count": int(unknown_acl),
            "decisions": decisions,
            "denied_chunk_ids": [item["chunk_id"] for item in denied],
            "denied_source_ids": sorted({item["source_id"] for item in denied}),
            "fail_close": True,
            "deny_by_default": True,
            "enforced_before_topk": bool(
                dict(getattr(rr, "access_policy", {}) or {}).get("enforced_before_topk", False)
            ),
            "pre_topk": dict(getattr(rr, "access_policy", {}) or {}),
            "post_topk_defense_in_depth": True,
        }
    }

    filtered = RetrievalResult(
        query=rr.query,
        chunks=kept_chunks,
        scores=kept_scores,
        topk=rr.topk,
        timing_ms=rr.timing_ms,
        rerank_applied=rr.rerank_applied,
        rerank_model=rr.rerank_model,
        rerank_candidate_topk=rr.rerank_candidate_topk,
        rerank_topn=rr.rerank_topn,
        rerank_scores=list(rr.rerank_scores or []),
        rerank_phase=rr.rerank_phase,
        selective_rerank_enabled=rr.selective_rerank_enabled,
        selective_rerank_triggered=rr.selective_rerank_triggered,
        selective_rerank_reason=rr.selective_rerank_reason,
        selective_rerank_threshold=rr.selective_rerank_threshold,
        selective_rerank_gap=rr.selective_rerank_gap,
        selective_rerank_before_source_ids=list(rr.selective_rerank_before_source_ids or []),
        selective_rerank_after_source_ids=list(rr.selective_rerank_after_source_ids or []),
        retrieval_events=list(getattr(rr, "retrieval_events", []) or []),
        merge_trace=dict(getattr(rr, "merge_trace", {}) or {}),
        access_policy=dict(getattr(rr, "access_policy", {}) or {}),
        score_type=str(getattr(rr, "score_type", "vector_similarity")),
    )
    return _set_acl_runtime_attrs(filtered, policy_trace), policy_trace


def _dedupe_chunks_by_chunk_id(chunks: List[Chunk], scores: List[float]) -> Tuple[List[Chunk], List[float]]:
    """按 chunk_id 去重，保留首次出现顺序。"""
    seen: set[str] = set()
    kept_chunks: List[Chunk] = []
    kept_scores: List[float] = []
    for chunk, score in zip(chunks, scores):
        chunk_id: str = str(chunk.chunk_id)
        if chunk_id in seen:
            continue
        seen.add(chunk_id)
        kept_chunks.append(chunk)
        kept_scores.append(float(score))
    return kept_chunks, kept_scores


def _merge_retrieval_results(query: str, topk: int, results: List[RetrievalResult], elapsed_ms: float) -> RetrievalResult:
    """兼容入口：所有多路结果用 RRF，不再 original-first 截断。"""
    return rrf_fuse(
        query=str(query),
        inputs=[
            FusionInput(result=result, query_role=f"query_{index}", round_id=1)
            for index, result in enumerate(results, start=1)
        ],
        topk=int(topk),
        elapsed_ms=float(elapsed_ms),
    )


def _set_rerank_runtime_attrs(
    rr: RetrievalResult,
    latency_ms: Optional[float],
    fallback_used: bool = False,
    error_type: Optional[str] = None,
) -> RetrievalResult:
    """给 RetrievalResult 附加 rerank runtime 观测字段，不改变 types.py 契约。"""
    try:
        object.__setattr__(rr, "rerank_latency_ms", float(latency_ms) if latency_ms is not None else None)
        object.__setattr__(rr, "rerank_fallback_used", bool(fallback_used))
        object.__setattr__(rr, "rerank_error_type", str(error_type) if error_type is not None else None)
    except Exception:
        pass
    return rr


def _retrieval_observation_kwargs(rr: RetrievalResult) -> Dict[str, Any]:
    """在不可变 RetrievalResult 重建时完整传递规范检索观察字段。"""
    return {
        "retrieval_events": list(getattr(rr, "retrieval_events", []) or []),
        "merge_trace": dict(getattr(rr, "merge_trace", {}) or {}),
        "access_policy": dict(getattr(rr, "access_policy", {}) or {}),
        "score_type": str(getattr(rr, "score_type", "vector_similarity")),
    }


def _apply_rerank(
    rr: RetrievalResult,
    rerank_model: str,
    rerank_candidate_topk: int,
    rerank_topn: int,
    rerank_phase: str,
    selective_rerank_enabled: bool,
    selective_rerank_triggered: bool,
    selective_rerank_reason: Optional[str],
    selective_rerank_threshold: Optional[float],
    selective_rerank_gap: Optional[float],
) -> RetrievalResult:
    """执行一次实际 rerank，并把 rerank / selective 元信息写回 RetrievalResult。"""
    candidate_topk: int = max(1, int(rerank_candidate_topk))
    topn: int = max(1, int(rerank_topn))
    candidate_chunks: List[Chunk] = list(rr.chunks[:candidate_topk])
    before_source_ids: List[str] = _ordered_unique_source_ids(candidate_chunks)
    if len(candidate_chunks) == 0:
        out = RetrievalResult(
            query=rr.query,
            chunks=[],
            scores=[],
            topk=rr.topk,
            timing_ms=rr.timing_ms,
            rerank_applied=True,
            rerank_model=str(rerank_model),
            rerank_candidate_topk=candidate_topk,
            rerank_topn=topn,
            rerank_scores=[],
            rerank_phase=str(rerank_phase),
            selective_rerank_enabled=bool(selective_rerank_enabled),
            selective_rerank_triggered=bool(selective_rerank_triggered),
            selective_rerank_reason=str(selective_rerank_reason) if selective_rerank_reason is not None else None,
            selective_rerank_threshold=float(selective_rerank_threshold) if selective_rerank_threshold is not None else None,
            selective_rerank_gap=float(selective_rerank_gap) if selective_rerank_gap is not None else None,
            selective_rerank_before_source_ids=before_source_ids,
            selective_rerank_after_source_ids=[],
            **_retrieval_observation_kwargs(rr),
        )
        return _set_rerank_runtime_attrs(out, latency_ms=0.0, fallback_used=False, error_type=None)

    rerank_t0: float = time.time()
    reranker = CrossEncoderReranker(model_name=str(rerank_model))
    rerank_result = reranker.rerank(query=str(rr.query), chunks=candidate_chunks, topn=topn)
    rerank_latency_ms: float = float((time.time() - rerank_t0) * 1000.0)
    after_source_ids: List[str] = _ordered_unique_source_ids(list(rerank_result.chunks or []))
    out = RetrievalResult(
        query=rr.query,
        chunks=list(rerank_result.chunks),
        scores=list(rerank_result.scores),
        topk=rr.topk,
        timing_ms=rr.timing_ms,
        rerank_applied=True,
        rerank_model=str(rerank_model),
        rerank_candidate_topk=candidate_topk,
        rerank_topn=topn,
        rerank_scores=list(rerank_result.scores),
        rerank_phase=str(rerank_phase),
        selective_rerank_enabled=bool(selective_rerank_enabled),
        selective_rerank_triggered=bool(selective_rerank_triggered),
        selective_rerank_reason=str(selective_rerank_reason) if selective_rerank_reason is not None else None,
        selective_rerank_threshold=float(selective_rerank_threshold) if selective_rerank_threshold is not None else None,
        selective_rerank_gap=float(selective_rerank_gap) if selective_rerank_gap is not None else None,
        selective_rerank_before_source_ids=before_source_ids,
        selective_rerank_after_source_ids=after_source_ids,
        **_retrieval_observation_kwargs(rr),
    )
    return _set_rerank_runtime_attrs(out, latency_ms=rerank_latency_ms, fallback_used=False, error_type=None)


def _rerank_fallback_result(
    rr: RetrievalResult,
    rerank_phase: str,
    selective_rerank_enabled: bool,
    selective_rerank_triggered: bool,
    selective_rerank_threshold: Optional[float],
    selective_rerank_gap: Optional[float],
    before_source_ids: List[str],
    exc: Exception,
) -> RetrievalResult:
    """rerank 外部依赖失败时保留原始检索顺序，避免异常冒泡到服务层。"""
    out = RetrievalResult(
        query=rr.query,
        chunks=list(rr.chunks),
        scores=list(rr.scores),
        topk=rr.topk,
        timing_ms=rr.timing_ms,
        rerank_applied=False,
        rerank_model=None,
        rerank_candidate_topk=None,
        rerank_topn=None,
        rerank_scores=[],
        rerank_phase=str(rerank_phase),
        selective_rerank_enabled=bool(selective_rerank_enabled),
        selective_rerank_triggered=bool(selective_rerank_triggered),
        selective_rerank_reason=f"rerank_error:{type(exc).__name__}",
        selective_rerank_threshold=(
            float(selective_rerank_threshold) if selective_rerank_threshold is not None else None
        ),
        selective_rerank_gap=float(selective_rerank_gap) if selective_rerank_gap is not None else None,
        selective_rerank_before_source_ids=list(before_source_ids or []),
        selective_rerank_after_source_ids=list(before_source_ids or []),
        **_retrieval_observation_kwargs(rr),
    )
    return _set_rerank_runtime_attrs(
        out,
        latency_ms=None,
        fallback_used=True,
        error_type=type(exc).__name__,
    )


def _apply_rerank_policy(
    rr: RetrievalResult,
    rerank_enabled: bool,
    rerank_model: str,
    rerank_candidate_topk: int,
    rerank_topn: int,
    selective_rerank_enabled: bool,
    selective_rerank_gap_threshold: float,
    selective_rerank_apply: bool,
    rerank_phase: str,
    agentic_steps: List[AgenticStep],
) -> RetrievalResult:
    """按 policy 执行 legacy 全局 rerank 或 selective rerank。"""
    candidate_topk: int = max(1, int(rerank_candidate_topk))
    before_source_ids: List[str] = _ordered_unique_source_ids(list(rr.chunks[:candidate_topk]))
    gap: Optional[float] = compute_top1_topk_gap(scores=rr.scores, k=candidate_topk)

    if bool(selective_rerank_enabled) and bool(selective_rerank_apply):
        triggered: bool = should_trigger_selective_rerank(
            scores=rr.scores,
            threshold=float(selective_rerank_gap_threshold),
            k=candidate_topk,
        )
        if triggered:
            try:
                reranked_rr: RetrievalResult = _apply_rerank(
                    rr=rr,
                    rerank_model=str(rerank_model),
                    rerank_candidate_topk=int(candidate_topk),
                    rerank_topn=int(rerank_topn),
                    rerank_phase=str(rerank_phase),
                    selective_rerank_enabled=True,
                    selective_rerank_triggered=True,
                    selective_rerank_reason="gap_below_threshold",
                    selective_rerank_threshold=float(selective_rerank_gap_threshold),
                    selective_rerank_gap=float(gap) if gap is not None else None,
                )
            except Exception as exc:  # noqa: BLE001
                reranked_rr = _rerank_fallback_result(
                    rr=rr,
                    rerank_phase=str(rerank_phase),
                    selective_rerank_enabled=True,
                    selective_rerank_triggered=True,
                    selective_rerank_threshold=float(selective_rerank_gap_threshold),
                    selective_rerank_gap=float(gap) if gap is not None else None,
                    before_source_ids=before_source_ids,
                    exc=exc,
                )
                _append_step(
                    agentic_steps,
                    f"{rerank_phase}_selective_rerank",
                    (
                        f"fallback_original_order gap={gap} threshold={selective_rerank_gap_threshold} "
                        f"sources={before_source_ids} error={_exception_summary(exc)}"
                    ),
                    float(getattr(reranked_rr, "rerank_latency_ms", 0.0) or 0.0),
                )
                return reranked_rr

            _append_step(
                agentic_steps,
                f"{rerank_phase}_selective_rerank",
                (
                    f"triggered=true gap={gap} threshold={selective_rerank_gap_threshold} "
                    f"before={before_source_ids} after={reranked_rr.selective_rerank_after_source_ids}"
                ),
                float(getattr(reranked_rr, "rerank_latency_ms", 0.0) or 0.0),
            )
            return reranked_rr

        skipped_rr: RetrievalResult = RetrievalResult(
            query=rr.query,
            chunks=list(rr.chunks),
            scores=list(rr.scores),
            topk=rr.topk,
            timing_ms=rr.timing_ms,
            rerank_applied=False,
            rerank_model=None,
            rerank_candidate_topk=None,
            rerank_topn=None,
            rerank_scores=[],
            rerank_phase=str(rerank_phase),
            selective_rerank_enabled=True,
            selective_rerank_triggered=False,
            selective_rerank_reason="gap_not_below_threshold",
            selective_rerank_threshold=float(selective_rerank_gap_threshold),
            selective_rerank_gap=float(gap) if gap is not None else None,
            selective_rerank_before_source_ids=before_source_ids,
            selective_rerank_after_source_ids=before_source_ids,
            **_retrieval_observation_kwargs(rr),
        )
        skipped_rr = _set_rerank_runtime_attrs(
            skipped_rr,
            latency_ms=0.0,
            fallback_used=False,
            error_type=None,
        )
        _append_step(
            agentic_steps,
            f"{rerank_phase}_selective_rerank",
            f"triggered=false gap={gap} threshold={selective_rerank_gap_threshold} sources={before_source_ids}",
            0.0,
        )
        return skipped_rr

    if bool(rerank_enabled):
        try:
            reranked_rr = _apply_rerank(
                rr=rr,
                rerank_model=str(rerank_model),
                rerank_candidate_topk=int(candidate_topk),
                rerank_topn=int(rerank_topn),
                rerank_phase=str(rerank_phase),
                selective_rerank_enabled=False,
                selective_rerank_triggered=False,
                selective_rerank_reason="legacy_global_rerank",
                selective_rerank_threshold=None,
                selective_rerank_gap=float(gap) if gap is not None else None,
            )
        except Exception as exc:  # noqa: BLE001
            reranked_rr = _rerank_fallback_result(
                rr=rr,
                rerank_phase=str(rerank_phase),
                selective_rerank_enabled=False,
                selective_rerank_triggered=False,
                selective_rerank_threshold=None,
                selective_rerank_gap=float(gap) if gap is not None else None,
                before_source_ids=before_source_ids,
                exc=exc,
            )
            _append_step(
                agentic_steps,
                f"{rerank_phase}_rerank",
                f"fallback_original_order sources={before_source_ids} error={_exception_summary(exc)}",
                0.0,
            )
            return reranked_rr

        _append_step(
            agentic_steps,
            f"{rerank_phase}_rerank",
            f"legacy_global=true before={before_source_ids} after={reranked_rr.selective_rerank_after_source_ids}",
            float(getattr(reranked_rr, "rerank_latency_ms", 0.0) or 0.0),
        )
        return reranked_rr

    return rr


def _build_retrieval_signal_flags(rr: RetrievalResult, min_required: int) -> Dict[str, Any]:
    evidence_count: int = int(len(rr.chunks or []))
    top1_score: Optional[float] = float(rr.scores[0]) if len(rr.scores) >= 1 else None
    top2_score: Optional[float] = float(rr.scores[1]) if len(rr.scores) >= 2 else None
    diff_top1_top2: Optional[float] = None
    if top1_score is not None and top2_score is not None:
        diff_top1_top2 = float(top1_score - top2_score)

    unique_sources: List[str] = _ordered_unique_source_ids(list(rr.chunks or []))

    return {
        "evidence_count": int(evidence_count),
        "min_evidence_required": int(min_required),
        "top1_score": top1_score,
        "top2_score": top2_score,
        "diff_top1_top2": diff_top1_top2,
        "unique_source_count": int(len(unique_sources)),
        "unique_source_ids": unique_sources,
        "pipeline_evidence_check": True,
        "rerank_enabled": bool(rr.rerank_applied),
        "rerank_model": rr.rerank_model,
        "rerank_candidate_topk": rr.rerank_candidate_topk,
        "rerank_topn": rr.rerank_topn,
        "rerank_scores": list(rr.rerank_scores or []),
        "rerank_phase": rr.rerank_phase,
        "rerank_latency_ms": getattr(rr, "rerank_latency_ms", None),
        "rerank_fallback_used": bool(getattr(rr, "rerank_fallback_used", False)),
        "rerank_error_type": getattr(rr, "rerank_error_type", None),
        "selective_rerank_enabled": bool(rr.selective_rerank_enabled),
        "selective_rerank_triggered": bool(rr.selective_rerank_triggered),
        "selective_rerank_reason": rr.selective_rerank_reason,
        "selective_rerank_threshold": rr.selective_rerank_threshold,
        "selective_rerank_gap": rr.selective_rerank_gap,
        "selective_rerank_before_source_ids": list(rr.selective_rerank_before_source_ids or []),
        "selective_rerank_after_source_ids": list(rr.selective_rerank_after_source_ids or []),
        "retrieval_events": list(getattr(rr, "retrieval_events", []) or []),
        "merge_trace": dict(getattr(rr, "merge_trace", {}) or {}),
        "score_type": str(getattr(rr, "score_type", "vector_similarity")),
    }


def _pipeline_reject_answer(
    query: str,
    rr: RetrievalResult,
    reason: str,
    signal_flags: Dict[str, Any],
    retrieval_ms_total: float,
    total_ms: float,
    agentic_steps: List[AgenticStep],
) -> Answer:
    flags: Dict[str, Any] = dict(signal_flags or {})
    flags.update(
        {
            "refused": True,
            "refuse_reason": str(reason),
            "citation_hallucination": False,
            "hallucinated_citations": [],
            "missing_citations_fallback": False,
            "used_chunk_ids": [str(chunk.chunk_id) for chunk in list(rr.chunks or [])],
            "used_chunk_source_ids": _ordered_unique_source_ids(list(rr.chunks or [])),
            "citation_source_ids": [],
            "has_citation": False,
            "evidence_hit": bool(len(list(rr.chunks or [])) > 0),
            "pipeline_total_ms": float(total_ms),
        }
    )
    return Answer(
        query=str(query),
        answer_text=str(_PIPELINE_REFUSAL_TEMPLATE),
        citations=[],
        used_chunks=list(rr.chunks or []),
        timing_ms=float(total_ms),
        retrieval_ms=float(retrieval_ms_total),
        generation_ms=0.0,
        llm_generate_ms=0.0,
        token_usage={},
        flags=flags,
        agentic_steps=list(agentic_steps or []),
    )



def _sufficiency_judge_error_reason(exc: SufficiencyJudgeError) -> str:
    """把 judge 异常映射为 Phase C 业务拒答原因。"""
    if isinstance(exc, SufficiencyJudgeTimeout):
        return "sufficiency_judge_timeout"
    return "sufficiency_judge_unavailable"


def _reject_for_sufficiency_judge_error(
    query: str,
    rr: RetrievalResult,
    exc: SufficiencyJudgeError,
    signal_flags: Dict[str, Any],
    retrieval_ms_total: float,
    t0_total: float,
    agentic_steps: List[AgenticStep],
    step_name: str,
    elapsed_ms: float,
) -> Answer:
    """DeepSeek judge 不可用时保守业务拒答，不进入 generate。"""
    reason = _sufficiency_judge_error_reason(exc)
    flags: Dict[str, Any] = dict(signal_flags or {})
    flags.update(
        {
            "degraded": True,
            "degraded_reasons": [reason],
            "sufficiency_judge_error": str(exc),
        }
    )

    if step_name == "sufficiency_first":
        flags["first_sufficiency_result"] = "TIMEOUT" if reason.endswith("timeout") else "ERROR"
        flags["first_sufficiency_ms"] = float(elapsed_ms)
    elif step_name == "sufficiency_second":
        flags["second_sufficiency_result"] = "TIMEOUT" if reason.endswith("timeout") else "ERROR"
        flags["second_sufficiency_ms"] = float(elapsed_ms)

    _append_step(agentic_steps, step_name, reason, float(elapsed_ms))
    _append_step(agentic_steps, "reject", reason, 0.0)

    total_ms = float((time.time() - t0_total) * 1000.0)
    ans = _pipeline_reject_answer(
        query=str(query),
        rr=rr,
        reason=reason,
        signal_flags=flags,
        retrieval_ms_total=float(retrieval_ms_total),
        total_ms=float(total_ms),
        agentic_steps=agentic_steps,
    )
    _append_query_log(ans=ans, topk=int(rr.topk))
    return ans

def _append_query_log(ans: Answer, topk: int) -> None:
    log_dir = Path("logs").expanduser().resolve()
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "query.jsonl"

    record = {
        "event": "query",
        "query": str(ans.query),
        "topk": int(topk),
        "answer_text": str(ans.answer_text),
        "citations": [
            {
                "source_id": str(c.source_id),
                "chunk_id": str(c.chunk_id),
                "offset_start": int(c.offset_start),
                "score": float(c.score),
            }
            for c in list(ans.citations or [])
        ],
        "retrieval_ms": float(ans.retrieval_ms),
        "generation_ms": float(ans.generation_ms),
        "llm_generate_ms": float(ans.llm_generate_ms),
        "timing_ms": float(ans.timing_ms),
        "flags": dict(ans.flags or {}),
        "agentic_steps": [
            {"step": step.step, "output": step.output, "duration_ms": float(step.duration_ms)}
            for step in list(ans.agentic_steps or [])
        ],
    }

    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def _retrieve_once(
    retriever: Retriever,
    query: str,
    topk: int,
    *,
    user_context: UserContext,
    round_id: int,
    query_role: str,
) -> Tuple[RetrievalResult, float]:
    """执行一次标准单路检索。"""
    t0: float = time.time()
    try:
        out: Any = retriever.run(
            query=str(query),
            topk=int(topk),
            user_context=user_context,
        )
    except TypeError as exc:
        # 过渡期测试替身或自定义检索器可能仍使用旧签名；生产 Retriever 接受可信用户上下文。
        if "user_context" not in str(exc):
            raise
        out = retriever.run(query=str(query), topk=int(topk))
    elapsed_ms: float = float((time.time() - t0) * 1000.0)
    rr: RetrievalResult = _retriever_output_to_retrieval_result(
        query=str(query),
        topk=int(topk),
        out=out,
        elapsed_ms=elapsed_ms,
    )
    event = retrieval_event(
        rr,
        query_role=str(query_role),
        round_id=int(round_id),
        duration_ms=float(elapsed_ms),
    )
    object.__setattr__(rr, "retrieval_events", [event])
    object.__setattr__(
        rr,
        "merge_trace",
        {
            "strategy": "single_query",
            "dedupe_key": "chunk_id",
            "subquery_quota_enabled": False,
            "final_order": list(event["candidates"]),
        },
    )
    return rr, elapsed_ms


def _retrieve_by_route(
    retriever: Retriever,
    query: str,
    topk: int,
    route_decision: RouteDecision,
    rerank_enabled: bool,
    rerank_model: str,
    rerank_candidate_topk: Optional[int],
    rerank_topn: int,
    selective_rerank_enabled: bool,
    selective_rerank_gap_threshold: float,
    selective_rerank_apply: bool,
    agentic_steps: List[AgenticStep],
    step_prefix: str,
    user_context: UserContext,
    round_id: int,
    generator_profile: Optional[GeneratorProfileConfig] = None,
) -> Tuple[RetrievalResult, float, Dict[str, Any]]:
    """按 DIRECT / DECOMPOSE 执行首轮或二轮检索，并返回统一 RetrievalResult。"""
    retrieval_meta: Dict[str, Any] = {
        "actual_agentic_path": str(route_decision.path),
        "route_keyword": str(route_decision.matched_keyword),
        "decompose_query_a": "",
        "decompose_query_b": "",
        "subquery_model_calls": [],
        "retrieval_events": [],
        "merge_trace": {},
    }
    candidate_topk: int = int(rerank_candidate_topk if rerank_candidate_topk is not None else topk)

    if str(route_decision.path) == "DECOMPOSE":
        t0_decompose: float = time.time()
        try:
            query_a, query_b, subquery_call = _decompose_query(
                str(query),
                generator_profile=generator_profile,
            )
            decompose_ms: float = float((time.time() - t0_decompose) * 1000.0)
            retrieval_meta["subquery_model_calls"].append(
                _model_call_to_usage_dict(subquery_call, stage=f"{step_prefix}_decompose")
            )
            retrieval_meta["decompose_query_a"] = str(query_a)
            retrieval_meta["decompose_query_b"] = str(query_b)
            retrieval_meta["decompose_fallback_used"] = False
            retrieval_meta["decompose_error"] = ""
            _append_step(agentic_steps, f"{step_prefix}_decompose", f"A={query_a} | B={query_b}", decompose_ms)
        except Exception as exc:  # noqa: BLE001
            decompose_ms = float((time.time() - t0_decompose) * 1000.0)
            retrieval_meta["subquery_model_calls"].append(
                _llm_error_model_call(
                    exc=exc,
                    elapsed_ms=float(decompose_ms),
                    role="subquery_generator",
                    stage=f"{step_prefix}_decompose",
                    profile=generator_profile,
                )
            )
            retrieval_meta["decompose_fallback_used"] = True
            retrieval_meta["decompose_error"] = _exception_summary(exc)
            _append_step(
                agentic_steps,
                f"{step_prefix}_decompose",
                f"fallback_original_query error={retrieval_meta['decompose_error']}",
                decompose_ms,
            )

            rr_direct, retrieve_ms_direct = _retrieve_once(
                retriever=retriever,
                query=str(query),
                topk=int(topk),
                user_context=user_context,
                round_id=int(round_id),
                query_role="original",
            )
            rr_direct = _apply_rerank_policy(
                rr=rr_direct,
                rerank_enabled=bool(rerank_enabled),
                rerank_model=str(rerank_model),
                rerank_candidate_topk=int(candidate_topk),
                rerank_topn=int(rerank_topn),
                selective_rerank_enabled=bool(selective_rerank_enabled),
                selective_rerank_gap_threshold=float(selective_rerank_gap_threshold),
                selective_rerank_apply=bool(selective_rerank_apply),
                rerank_phase=str(step_prefix),
                agentic_steps=agentic_steps,
            )
            _append_step(
                agentic_steps,
                f"{step_prefix}_retrieve",
                f"DECOMPOSE_FALLBACK_ORIGINAL chunks={len(rr_direct.chunks)}",
                float(retrieve_ms_direct),
            )
            retrieval_meta["retrieval_events"] = list(rr_direct.retrieval_events)
            retrieval_meta["merge_trace"] = dict(rr_direct.merge_trace)
            return rr_direct, float(retrieve_ms_direct), retrieval_meta

        rr_original, retrieve_ms_original = _retrieve_once(
            retriever=retriever, query=str(query), topk=int(topk), user_context=user_context,
            round_id=int(round_id), query_role="original",
        )
        rr_a, retrieve_ms_a = _retrieve_once(
            retriever=retriever, query=str(query_a), topk=int(topk), user_context=user_context,
            round_id=int(round_id), query_role="subquery_a",
        )
        rr_b, retrieve_ms_b = _retrieve_once(
            retriever=retriever, query=str(query_b), topk=int(topk), user_context=user_context,
            round_id=int(round_id), query_role="subquery_b",
        )
        merged_rr: RetrievalResult = rrf_fuse(
            query=str(query),
            inputs=[
                FusionInput(rr_original, "original", int(round_id)),
                FusionInput(rr_a, "subquery_a", int(round_id)),
                FusionInput(rr_b, "subquery_b", int(round_id)),
            ],
            topk=int(topk),
            elapsed_ms=float(retrieve_ms_original + retrieve_ms_a + retrieve_ms_b),
        )
        merged_rr = _apply_rerank_policy(
            rr=merged_rr,
            rerank_enabled=bool(rerank_enabled),
            rerank_model=str(rerank_model),
            rerank_candidate_topk=int(candidate_topk),
            rerank_topn=int(rerank_topn),
            selective_rerank_enabled=bool(selective_rerank_enabled),
            selective_rerank_gap_threshold=float(selective_rerank_gap_threshold),
            selective_rerank_apply=bool(selective_rerank_apply),
            rerank_phase=str(step_prefix),
            agentic_steps=agentic_steps,
        )

        print(
            f"[debug][{step_prefix}_decompose_merge] "
            f"original={query} | A={query_a} | B={query_b}",
            flush=True,
        )
        print(
            f"[debug][{step_prefix}_decompose_merge] "
            f"source_ids={[chunk.source_id for chunk in merged_rr.chunks]}",
            flush=True,
        )
        print(
            f"[debug][{step_prefix}_decompose_merge] "
            f"chunk_ids={[chunk.chunk_id for chunk in merged_rr.chunks]}",
            flush=True,
        )

        _append_step(
            agentic_steps,
            f"{step_prefix}_retrieve",
            f"DECOMPOSE chunks={len(merged_rr.chunks)}",
            float(retrieve_ms_original + retrieve_ms_a + retrieve_ms_b),
        )
        retrieval_meta["retrieval_events"] = list(merged_rr.retrieval_events)
        retrieval_meta["merge_trace"] = dict(merged_rr.merge_trace)
        return merged_rr, float(retrieve_ms_original + retrieve_ms_a + retrieve_ms_b), retrieval_meta

    rr_direct, retrieve_ms_direct = _retrieve_once(
        retriever=retriever,
        query=str(query),
        topk=int(topk),
        user_context=user_context,
        round_id=int(round_id),
        query_role="original" if int(round_id) == 1 else "rewrite",
    )
    rr_direct = _apply_rerank_policy(
        rr=rr_direct,
        rerank_enabled=bool(rerank_enabled),
        rerank_model=str(rerank_model),
        rerank_candidate_topk=int(candidate_topk),
        rerank_topn=int(rerank_topn),
        selective_rerank_enabled=bool(selective_rerank_enabled),
        selective_rerank_gap_threshold=float(selective_rerank_gap_threshold),
        selective_rerank_apply=bool(selective_rerank_apply),
        rerank_phase=str(step_prefix),
        agentic_steps=agentic_steps,
    )
    _append_step(agentic_steps, f"{step_prefix}_retrieve", f"DIRECT chunks={len(rr_direct.chunks)}", float(retrieve_ms_direct))
    retrieval_meta["retrieval_events"] = list(rr_direct.retrieval_events)
    retrieval_meta["merge_trace"] = dict(rr_direct.merge_trace)
    return rr_direct, float(retrieve_ms_direct), retrieval_meta


def _judge_evidence_sufficiency(
    *,
    query_text: str,
    retrieval_result: RetrievalResult,
    route: str,
    mode: str,
    judge_profile: Optional[GeneratorProfileConfig],
    max_prompt_chunks: int,
) -> Tuple[str, float, Any, Dict[str, Any]]:
    """执行当前配置的 sufficiency 合同，并保留本次判断看到的精确输入。"""

    if mode == "structured":
        packet = build_evidence_packet(
            retrieval_result=retrieval_result,
            route=str(route),
            max_chunks_in_packet=int(max_prompt_chunks),
            dedupe_by_source=False,
            text_preview_chars=1200,
        )
        for item in packet.items:
            item.in_prompt = True
        result, elapsed_ms, call = judge_sufficiency_with_evidence_packet(
            query=str(query_text),
            evidence_packet=packet,
            route=str(route),
            profile=judge_profile,
        )
        verdict = str(result.verdict or "INSUFFICIENT").upper()
        if verdict not in {"SUFFICIENT", "INSUFFICIENT"}:
            verdict = "INSUFFICIENT"
        return verdict, float(elapsed_ms), call, {
            "mode": "structured",
            "evidence_packet": asdict(packet),
            "result": asdict(result),
        }

    verdict, elapsed_ms, call = judge_sufficiency_with_model_call(
        query=str(query_text),
        chunks=list(retrieval_result.chunks or []),
        profile=judge_profile,
    )
    return str(verdict), float(elapsed_ms), call, {
        "mode": "binary",
        "evidence_snapshot_id": build_evidence_snapshot(retrieval_result)["snapshot_id"],
        "result": {"verdict": str(verdict)},
    }


def query(
    query: str,
    topk: int = 5,
    rerank_enabled: bool = False,
    rerank_model: str = "BAAI/bge-reranker-base",
    rerank_candidate_topk: Optional[int] = None,
    rerank_topn: int = 2,
    selective_rerank_enabled: bool = False,
    selective_rerank_gap_threshold: float = 0.05,
    selective_rerank_apply_on_first_round: bool = True,
    selective_rerank_apply_on_second_round: bool = True,
    user_context: Optional[Dict[str, Any]] = None,
    retriever_instance: Optional[Retriever] = None,
    max_chunks_in_prompt: int = 5,
    max_chars_per_chunk: Optional[int] = None,
    citation_fallback_n: int = 0,
    generator_profile: Optional[GeneratorProfileConfig] = None,
    judge_profile: Optional[GeneratorProfileConfig] = None,
    sufficiency_mode: str = "binary",
) -> Answer:
    t0_total: float = time.time()
    retriever: Retriever = retriever_instance or Retriever()
    trusted_user: UserContext = _user_context_from_payload(user_context)
    agentic_steps: List[AgenticStep] = []
    normalized_sufficiency_mode = str(sufficiency_mode).strip().lower()
    if normalized_sufficiency_mode not in {"binary", "structured"}:
        raise ValueError("sufficiency_mode must be binary or structured")

    security_decision = assess_security_policy(query=str(query))
    security_trace = build_security_policy_trace(security_decision)
    _append_step(
        agentic_steps,
        "security_policy",
        str(security_decision.refusal_reason or "checked"),
        0.0,
    )

    if security_decision.refusal_recommended:
        empty_rr = RetrievalResult(
            query=str(query),
            chunks=[],
            scores=[],
            topk=int(topk),
            timing_ms=0.0,
        )
        security_flags: Dict[str, Any] = {
            "refused": True,
            "refuse_reason": str(security_decision.refusal_reason or "unsafe_or_private_boundary"),
            "policy_trace": security_trace,
            "security_refusal_expected": True,
            "injection_detected": bool(security_decision.injection_detected),
            "redaction_applied": bool(security_decision.redaction_applied),
            "redaction_count": int(security_decision.redaction_count),
            "private_boundary_detected": bool(security_decision.private_boundary_detected),
            "unsafe_or_private": bool(security_decision.unsafe_or_private),
            "acl_checked": False,
        }
        _append_step(agentic_steps, "reject", security_flags["refuse_reason"], 0.0)
        total_ms = float((time.time() - t0_total) * 1000.0)
        ans = _pipeline_reject_answer(
            query=str(query),
            rr=empty_rr,
            reason=security_flags["refuse_reason"],
            signal_flags=security_flags,
            retrieval_ms_total=0.0,
            total_ms=float(total_ms),
            agentic_steps=agentic_steps,
        )
        _append_query_log(ans=ans, topk=int(topk))
        return ans

    retrieve_ms_1: float = 0.0
    retrieve_ms_2: float = 0.0
    rewrite_ms: float = 0.0
    rewritten_query: str = ""

    t0_route_1: float = time.time()
    route_decision_1: RouteDecision = route_query(str(query))
    route_ms_1: float = float((time.time() - t0_route_1) * 1000.0)
    _append_step(agentic_steps, "route_first", f"{route_decision_1.path}:{route_decision_1.matched_keyword}", route_ms_1)

    rr, retrieve_ms_1, retrieval_meta_1 = _retrieve_by_route(
        retriever=retriever,
        query=str(query),
        topk=int(topk),
        route_decision=route_decision_1,
        rerank_enabled=bool(rerank_enabled),
        rerank_model=str(rerank_model),
        rerank_candidate_topk=rerank_candidate_topk,
        rerank_topn=int(rerank_topn),
        selective_rerank_enabled=bool(selective_rerank_enabled),
        selective_rerank_gap_threshold=float(selective_rerank_gap_threshold),
        selective_rerank_apply=bool(selective_rerank_apply_on_first_round),
        agentic_steps=agentic_steps,
        step_prefix="first",
        user_context=trusted_user,
        round_id=1,
        generator_profile=generator_profile,
    )

    rr, acl_trace_1 = _apply_acl_filter(rr=rr, user_context_payload=user_context, phase="first_retrieval")

    gcfg: GeneratorConfig = GeneratorConfig(
        min_evidence_chunks=2,
        max_chunks_in_prompt=int(max_chunks_in_prompt),
        max_chars_per_chunk=max_chars_per_chunk,
        citation_fallback_n=int(citation_fallback_n),
    )
    signal_flags: Dict[str, Any] = _build_retrieval_signal_flags(rr=rr, min_required=int(gcfg.min_evidence_chunks))
    evidence_snapshot_1 = build_evidence_snapshot(rr)
    signal_flags.update(
        {
            "first_retrieval_ms": float(retrieve_ms_1),
            "second_retrieval_ms": 0.0,
            "query_rewrite_ms": 0.0,
            "first_sufficiency_result": None,
            "first_sufficiency_ms": 0.0,
            "second_sufficiency_result": None,
            "second_sufficiency_ms": 0.0,
            "sufficiency_model_calls": [],
            "rewrite_model_calls": [],
            "subquery_model_calls": list(retrieval_meta_1.get("subquery_model_calls", [])),
            "first_route_path": str(route_decision_1.path),
            "first_route_keyword": str(route_decision_1.matched_keyword),
            "actual_agentic_path": str(retrieval_meta_1.get("actual_agentic_path", route_decision_1.path)),
            "decompose_query_a": str(retrieval_meta_1.get("decompose_query_a", "")),
            "decompose_query_b": str(retrieval_meta_1.get("decompose_query_b", "")),
            "decompose_fallback_used": bool(retrieval_meta_1.get("decompose_fallback_used", False)),
            "decompose_error": str(retrieval_meta_1.get("decompose_error", "")),
            "selective_rerank_apply_on_first_round": bool(selective_rerank_apply_on_first_round),
            "selective_rerank_apply_on_second_round": bool(selective_rerank_apply_on_second_round),
            "acl_checked": True,
            "policy_trace": {**acl_trace_1, **security_trace},
            "injection_detected": bool(security_decision.injection_detected),
            "redaction_applied": bool(security_decision.redaction_applied),
            "redaction_count": int(security_decision.redaction_count),
            "private_boundary_detected": bool(security_decision.private_boundary_detected),
            "unsafe_or_private": bool(security_decision.unsafe_or_private),
            "acl_allowed_chunk_count": acl_trace_1["access_policy"]["allowed_chunk_count"],
            "acl_denied_chunk_count": acl_trace_1["access_policy"]["denied_chunk_count"],
            "source_acl_missing_count": acl_trace_1["access_policy"]["source_acl_missing_count"],
            "unknown_acl_runtime_deny_count": acl_trace_1["access_policy"]["unknown_acl_runtime_deny_count"],
            "retrieval_events": list(getattr(rr, "retrieval_events", []) or []),
            "merge_trace": dict(getattr(rr, "merge_trace", {}) or {}),
            "evidence_snapshot": evidence_snapshot_1,
            "evidence_snapshot_id": evidence_snapshot_1["snapshot_id"],
            "sufficiency_evidence_ref": evidence_snapshot_1["snapshot_id"],
        }
    )

    if _DEBUG_PIPELINE:
        print(
            f"[debug] route={signal_flags['first_route_path']} "
            f"evidence_count={signal_flags['evidence_count']} "
            f"min_required={signal_flags['min_evidence_required']} "
            f"top1={signal_flags['top1_score']} "
            f"top2={signal_flags['top2_score']} "
            f"diff={signal_flags['diff_top1_top2']} "
            f"unique_sources={signal_flags['unique_source_count']} "
            f"rerank_enabled={signal_flags['rerank_enabled']} "
            f"rerank_topn={signal_flags['rerank_topn']} "
            f"selective_triggered={signal_flags['selective_rerank_triggered']} "
            f"selective_gap={signal_flags['selective_rerank_gap']}",
            flush=True,
        )

    t0_suff_1: float = time.time()
    try:
        suff, suff_ms_1, suff_call_1, suff_detail_1 = _judge_evidence_sufficiency(
            query_text=str(query),
            retrieval_result=rr,
            route=str(route_decision_1.path),
            mode=normalized_sufficiency_mode,
            judge_profile=judge_profile,
            max_prompt_chunks=int(max_chunks_in_prompt),
        )
        signal_flags["first_sufficiency_contract"] = suff_detail_1
        signal_flags["sufficiency_model_calls"].append(
            _model_call_to_usage_dict(suff_call_1, stage="legacy_first_sufficiency")
        )
    except SufficiencyJudgeError as exc:
        suff_ms_1 = float((time.time() - t0_suff_1) * 1000.0)
        signal_flags["sufficiency_model_calls"].append(
            _sufficiency_error_model_call(exc, elapsed_ms=float(suff_ms_1), stage="legacy_first_sufficiency")
        )
        ans = _reject_for_sufficiency_judge_error(
            query=str(query),
            rr=rr,
            exc=exc,
            signal_flags=signal_flags,
            retrieval_ms_total=float(retrieve_ms_1),
            t0_total=t0_total,
            agentic_steps=agentic_steps,
            step_name="sufficiency_first",
            elapsed_ms=float(suff_ms_1),
        )
        return ans

    signal_flags["first_sufficiency_result"] = str(suff)
    signal_flags["first_sufficiency_ms"] = float(suff_ms_1)
    _append_step(agentic_steps, "sufficiency_first", str(suff), float(suff_ms_1))

    if _DEBUG_PIPELINE:
        print(f"[debug] sufficiency={suff} suff_ms={suff_ms_1:.1f}", flush=True)

    if suff == "INSUFFICIENT":
        if _DEBUG_PIPELINE:
            print("[debug] first pass insufficient → trigger re-retrieve", flush=True)

        t0_rewrite: float = time.time()
        try:
            rewritten_query, rewrite_call = _rewrite_query_for_retrieval(
                str(query),
                generator_profile=generator_profile,
            )
            signal_flags["rewrite_model_calls"].append(
                _model_call_to_usage_dict(rewrite_call, stage="rewrite_query")
            )
            rewrite_error = ""
            rewrite_fallback_used = False
        except Exception as exc:  # noqa: BLE001
            rewritten_query = str(query)
            rewrite_error = _exception_summary(exc)
            rewrite_fallback_used = True
            signal_flags["rewrite_model_calls"].append(
                _llm_error_model_call(
                    exc=exc,
                    elapsed_ms=float((time.time() - t0_rewrite) * 1000.0),
                    role="rewrite_query",
                    stage="rewrite_query",
                    profile=generator_profile,
                )
            )

        rewrite_ms = float((time.time() - t0_rewrite) * 1000.0)
        signal_flags["query_rewrite_ms"] = float(rewrite_ms)
        signal_flags["rewritten_query"] = str(rewritten_query)
        signal_flags["query_rewrite_fallback_used"] = bool(rewrite_fallback_used)
        signal_flags["query_rewrite_error"] = str(rewrite_error)

        if rewrite_fallback_used:
            _append_step(
                agentic_steps,
                "rewrite_query",
                f"fallback_original_query error={rewrite_error}",
                float(rewrite_ms),
            )
        else:
            _append_step(agentic_steps, "rewrite_query", str(rewritten_query), float(rewrite_ms))

        if _DEBUG_PIPELINE:
            if rewrite_fallback_used:
                print(f"[debug] rewrite fallback original query error={rewrite_error}", flush=True)
            else:
                print(f"[debug] rewritten_query={rewritten_query}", flush=True)

        route_decision_2: RouteDecision = RouteDecision(path="DIRECT", matched_keyword="")
        _append_step(agentic_steps, "route_second", "DIRECT:forced_for_reretrieve", 0.0)
        signal_flags["second_route_path"] = "DIRECT"
        signal_flags["second_route_keyword"] = "forced_for_reretrieve"

        rr2, retrieve_ms_2, retrieval_meta_2 = _retrieve_by_route(
            retriever=retriever,
            query=str(rewritten_query),
            topk=int(topk),
            route_decision=route_decision_2,
            rerank_enabled=bool(rerank_enabled),
            rerank_model=str(rerank_model),
            rerank_candidate_topk=rerank_candidate_topk,
            rerank_topn=int(rerank_topn),
            selective_rerank_enabled=bool(selective_rerank_enabled),
            selective_rerank_gap_threshold=float(selective_rerank_gap_threshold),
            selective_rerank_apply=bool(selective_rerank_apply_on_second_round),
            agentic_steps=agentic_steps,
            step_prefix="second",
            user_context=trusted_user,
            round_id=2,
            generator_profile=generator_profile,
        )
        second_round_rr = rr2
        rr2 = rrf_fuse(
            query=str(query),
            inputs=[
                FusionInput(rr, "round_1_final", 1),
                FusionInput(second_round_rr, "round_2_rewrite", 2),
            ],
            topk=int(topk),
            elapsed_ms=float(retrieve_ms_1 + retrieve_ms_2),
        )
        object.__setattr__(rr2, "merge_trace", {
            **dict(rr2.merge_trace),
            "scope": "round_union",
            "rounds": [1, 2],
            "second_round_overwrites_first": False,
        })
        rr2, acl_trace_2 = _apply_acl_filter(rr=rr2, user_context_payload=user_context, phase="second_retrieval_union")
        signal_flags["policy_trace"] = {**acl_trace_2, **security_trace}
        signal_flags["acl_allowed_chunk_count"] = acl_trace_2["access_policy"]["allowed_chunk_count"]
        signal_flags["acl_denied_chunk_count"] = acl_trace_2["access_policy"]["denied_chunk_count"]
        signal_flags["source_acl_missing_count"] = acl_trace_2["access_policy"]["source_acl_missing_count"]
        signal_flags["unknown_acl_runtime_deny_count"] = acl_trace_2["access_policy"]["unknown_acl_runtime_deny_count"]
        signal_flags["second_retrieval_ms"] = float(retrieve_ms_2)
        signal_flags["second_decompose_query_a"] = str(retrieval_meta_2.get("decompose_query_a", ""))
        signal_flags["second_decompose_query_b"] = str(retrieval_meta_2.get("decompose_query_b", ""))
        signal_flags["second_decompose_fallback_used"] = bool(retrieval_meta_2.get("decompose_fallback_used", False))
        signal_flags["second_decompose_error"] = str(retrieval_meta_2.get("decompose_error", ""))
        signal_flags["second_selective_rerank_triggered"] = bool(second_round_rr.selective_rerank_triggered)
        signal_flags["second_selective_rerank_reason"] = second_round_rr.selective_rerank_reason
        signal_flags["second_selective_rerank_gap"] = second_round_rr.selective_rerank_gap
        signal_flags["second_selective_rerank_before_source_ids"] = list(second_round_rr.selective_rerank_before_source_ids or [])
        signal_flags["second_selective_rerank_after_source_ids"] = list(second_round_rr.selective_rerank_after_source_ids or [])
        signal_flags["second_rerank_latency_ms"] = getattr(second_round_rr, "rerank_latency_ms", None)
        signal_flags["second_rerank_fallback_used"] = bool(getattr(second_round_rr, "rerank_fallback_used", False))
        signal_flags["second_rerank_error_type"] = getattr(second_round_rr, "rerank_error_type", None)
        signal_flags["retrieval_events"] = list(getattr(rr2, "retrieval_events", []) or [])
        signal_flags["merge_trace"] = dict(getattr(rr2, "merge_trace", {}) or {})
        evidence_snapshot_2 = build_evidence_snapshot(rr2)
        signal_flags["evidence_snapshot"] = evidence_snapshot_2
        signal_flags["evidence_snapshot_id"] = evidence_snapshot_2["snapshot_id"]
        signal_flags["sufficiency_evidence_ref"] = evidence_snapshot_2["snapshot_id"]

        t0_suff_2: float = time.time()
        try:
            suff2, suff_ms_2, suff_call_2, suff_detail_2 = _judge_evidence_sufficiency(
                query_text=str(query),
                retrieval_result=rr2,
                route="DIRECT",
                mode=normalized_sufficiency_mode,
                judge_profile=judge_profile,
                max_prompt_chunks=int(max_chunks_in_prompt),
            )
            signal_flags["second_sufficiency_contract"] = suff_detail_2
            signal_flags["sufficiency_model_calls"].append(
                _model_call_to_usage_dict(suff_call_2, stage="legacy_second_sufficiency")
            )
        except SufficiencyJudgeError as exc:
            suff_ms_2 = float((time.time() - t0_suff_2) * 1000.0)
            signal_flags["sufficiency_model_calls"].append(
                _sufficiency_error_model_call(exc, elapsed_ms=float(suff_ms_2), stage="legacy_second_sufficiency")
            )
            ans = _reject_for_sufficiency_judge_error(
                query=str(query),
                rr=rr2,
                exc=exc,
                signal_flags=signal_flags,
                retrieval_ms_total=float(retrieve_ms_1 + retrieve_ms_2),
                t0_total=t0_total,
                agentic_steps=agentic_steps,
                step_name="sufficiency_second",
                elapsed_ms=float(suff_ms_2),
            )
            return ans

        signal_flags["second_sufficiency_result"] = str(suff2)
        signal_flags["second_sufficiency_ms"] = float(suff_ms_2)
        _append_step(agentic_steps, "sufficiency_second", str(suff2), float(suff_ms_2))

        if _DEBUG_PIPELINE:
            print(f"[debug] second sufficiency={suff2} suff2_ms={suff_ms_2:.1f}", flush=True)

        retrieval_ms_total: float = float(retrieve_ms_1 + retrieve_ms_2)

        if suff2 == "SUFFICIENT":
            generator = RAGGenerator(
                llm=_build_default_llm_client(
                    stage="generator",
                    data_visibilities=chunk_visibilities(rr2.chunks),
                    profile=generator_profile,
                ),
                cfg=gcfg,
            )
            ans = generator.generate(rr2)
            merged_flags: Dict[str, Any] = dict(signal_flags or {})
            merged_flags.update(dict(ans.flags or {}))
            total_ms: float = float((time.time() - t0_total) * 1000.0)
            merged_flags["pipeline_total_ms"] = float(total_ms)
            _append_step(agentic_steps, "generate", "answer", float(ans.generation_ms))
            ans = Answer(
                query=ans.query,
                answer_text=ans.answer_text,
                citations=ans.citations,
                used_chunks=ans.used_chunks,
                timing_ms=float(total_ms),
                retrieval_ms=float(retrieval_ms_total),
                generation_ms=ans.generation_ms,
                llm_generate_ms=ans.llm_generate_ms,
                token_usage=ans.token_usage,
                flags=merged_flags,
                agentic_steps=list(agentic_steps),
            )
        else:
            total_ms = float((time.time() - t0_total) * 1000.0)
            _append_step(agentic_steps, "reject", "insufficient_evidence_after_reretrieve", 0.0)
            ans = _pipeline_reject_answer(
                query=str(query),
                rr=rr2,
                reason="insufficient_evidence_after_reretrieve",
                signal_flags=signal_flags,
                retrieval_ms_total=float(retrieval_ms_total),
                total_ms=float(total_ms),
                agentic_steps=agentic_steps,
            )

        _append_query_log(ans=ans, topk=int(topk))
        return ans

    generator: RAGGenerator = RAGGenerator(
        llm=_build_default_llm_client(
            stage="generator",
            data_visibilities=chunk_visibilities(rr.chunks),
            profile=generator_profile,
        ),
        cfg=gcfg,
    )
    ans: Answer = generator.generate(rr)

    merged_flags: Dict[str, Any] = dict(signal_flags or {})
    merged_flags.update(dict(ans.flags or {}))

    total_ms: float = float((time.time() - t0_total) * 1000.0)
    merged_flags["pipeline_total_ms"] = float(total_ms)
    _append_step(agentic_steps, "generate", "answer", float(ans.generation_ms))

    ans = Answer(
        query=ans.query,
        answer_text=ans.answer_text,
        citations=ans.citations,
        used_chunks=ans.used_chunks,
        timing_ms=float(total_ms),
        retrieval_ms=float(retrieve_ms_1),
        generation_ms=ans.generation_ms,
        llm_generate_ms=ans.llm_generate_ms,
        token_usage=ans.token_usage,
        flags=merged_flags,
        agentic_steps=list(agentic_steps),
    )
    _append_query_log(ans=ans, topk=int(topk))
    return ans


def run(config: AppConfig) -> int:
    if str(config.mode) != "query":
        print(f"ERROR: pipeline.run only supports mode=query for now, got mode={config.mode}", flush=True)
        return 2

    ans: Answer = query(
        query=str(getattr(config, "query", "")) if hasattr(config, "query") else "",
        topk=int(config.topk),
        rerank_enabled=bool(config.rerank.enabled),
        rerank_model=str(config.rerank.model),
        rerank_candidate_topk=int(config.rerank.candidate_topk),
        rerank_topn=int(config.rerank.topn),
        selective_rerank_enabled=bool(config.rerank.selective_enabled),
        selective_rerank_gap_threshold=float(config.rerank.selective_gap_threshold),
        selective_rerank_apply_on_first_round=bool(config.rerank.selective_apply_on_first_round),
        selective_rerank_apply_on_second_round=bool(config.rerank.selective_apply_on_second_round),
    )

    print(ans.answer_text)
    return 0
