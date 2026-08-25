"""
文件作用：
1）提供 Phase D-full Step 7 的问题分类器入口；
2）LLM 只输出 question_type / answerability / confidence / reason；
3）程序根据 question_type + answerability 派生 route_candidate / route_policy；
4）默认保持保守：classifier 未启用、失败、低置信度时 fallback 到 D-lite rule router；
5）不直接改变 query_pipeline 主链路行为，供 WorkflowRunner / node observe-only 接入。

整体结构：
1）定义 ClassificationResult 数据结构；
2）实现 JSON 解析、枚举校验、route_candidate 派生与 fallback；
3）实现 classify_query(...) 统一入口；
4）预留 LLM classifier 调用，默认可由 config.yaml 的 classifier.enabled 控制。
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from agentic_rag.control.router import route_query
from agentic_rag.workflow.workflow_state import (
    Answerability,
    QuestionType,
    RouteCandidate,
    RoutePolicy,
    WorkflowRoute,
)


@dataclass
class ClassificationResult:
    """作用：承载一次问题分类结果。"""

    question_type: str
    answerability: str
    route_candidate: str
    route_policy: str
    confidence: str
    reason: str
    classifier_used: str = "rule_fallback"
    fallback_used: bool = False
    fallback_reason: Optional[str] = None
    raw_output: Optional[str] = None
    duration_ms: float = 0.0
    model_call: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """作用：转成可写入 workflow_trace / debug response 的 dict。"""
        return {
            "question_type": self.question_type,
            "answerability": self.answerability,
            "route_candidate": self.route_candidate,
            "route_policy": self.route_policy,
            "confidence": self.confidence,
            "reason": self.reason,
            "classifier_used": self.classifier_used,
            "fallback_used": bool(self.fallback_used),
            "fallback_reason": self.fallback_reason,
            "raw_output": self.raw_output,
            "duration_ms": float(self.duration_ms),
            "model_call": self.model_call,
        }


_VALID_QUESTION_TYPES: set[str] = {item.value for item in QuestionType}
_VALID_ANSWERABILITY: set[str] = {item.value for item in Answerability}
_VALID_CONFIDENCE: set[str] = {"high", "medium", "low"}


def _load_classifier_enabled(config_path: str = "config.yaml") -> bool:
    """作用：读取 config.yaml 中 classifier.enabled；读取失败时保守关闭。"""
    try:
        path = Path(config_path)
        if not path.exists():
            return False
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        classifier_cfg = data.get("classifier", {})
        if not isinstance(classifier_cfg, dict):
            return False
        return bool(classifier_cfg.get("enabled", False))
    except Exception:
        return False


def _derive_route_candidate(question_type: str, answerability: str) -> Tuple[str, str]:
    """作用：按 Step 7 schema 决策表派生 route_candidate / route_policy。"""
    qt = str(question_type).strip().upper()
    ans = str(answerability).strip().upper()

    if ans == Answerability.OOD_CANDIDATE.value:
        return RouteCandidate.REJECT_CANDIDATE.value, RoutePolicy.CANDIDATE_REJECT.value
    if ans == Answerability.NEEDS_CLARIFICATION.value:
        return RouteCandidate.NEEDS_CLARIFICATION.value, RoutePolicy.CLARIFY.value

    if qt in {QuestionType.EXPLICIT_COMPARE.value, QuestionType.IMPLICIT_COMPARE.value}:
        candidate = RouteCandidate.DECOMPOSE.value
    elif qt in {QuestionType.OPEN_MULTI.value, QuestionType.SUMMARY.value}:
        candidate = RouteCandidate.OPEN_MULTI.value
    else:
        candidate = RouteCandidate.DIRECT.value

    if ans == Answerability.UNKNOWN.value:
        return candidate, RoutePolicy.STRICT_SUFFICIENCY.value
    return candidate, RoutePolicy.NORMAL.value



def _identity_from_token_usage(token_usage: Dict[str, Any]) -> Dict[str, Any]:
    """作用：从 client token_usage / metadata 中抽取模型身份。"""
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


def _classifier_metadata_from_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """作用：LLM 调用失败时，用配置构造最小模型身份，避免失败调用消失。"""
    try:
        from agentic_rag.config import load_config

        app_cfg = load_config(config_path)
        profile = app_cfg.generator.get_profile()
        return {
            "provider": str(profile.provider_tag),
            "backend": str(profile.backend),
            "configured_model": str(profile.model),
            "provider_response_model": None,
            "resolved_model": str(profile.model),
            "endpoint": str(profile.base_url),
            "upstream_provider": None,
            "api_key_env": str(profile.api_key_env),
            "api_key_hash": None,
            "network_tag": "",
            "proxy_node": "",
            "generator_backend": str(profile.backend),
            "provider_tag": str(profile.provider_tag),
        }
    except Exception:
        return {}


def _build_classifier_model_call(
    token_usage: Optional[Dict[str, Any]],
    latency_ms: float,
    *,
    api_error: bool = False,
    timeout: bool = False,
    error_type: Optional[str] = None,
    error_message: Optional[str] = None,
) -> Dict[str, Any]:
    """作用：构造 classifier 的 usage.model_calls 原始记录。"""
    usage = dict(token_usage or {})
    identity = _identity_from_token_usage(usage) if usage else _classifier_metadata_from_config()

    prompt_details = usage.get("prompt_tokens_details")
    prompt_details = dict(prompt_details) if isinstance(prompt_details, dict) else {}
    completion_details = usage.get("completion_tokens_details")
    completion_details = dict(completion_details) if isinstance(completion_details, dict) else {}

    reasoning_tokens = completion_details.get("reasoning_tokens")
    cached_tokens = prompt_details.get("cached_tokens")
    cache_write_tokens = prompt_details.get("cache_write_tokens")

    return {
        "role": "classifier",
        "stage": "classify_query",
        "identity": identity,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": reasoning_tokens,
        "cached_tokens": cached_tokens,
        "cache_write_tokens": cache_write_tokens,
        "total_tokens": usage.get("total_tokens"),
        "latency_ms": float(latency_ms),
        "estimated_cost_usd": None,
        "http_status": None,
        "api_error": bool(api_error),
        "timeout": bool(timeout),
        "error_type": error_type,
        "error_message": error_message,
    }



def _fallback_by_rule_router(
    query: str,
    reason: str,
    duration_ms: float,
    raw_output: Optional[str] = None,
    model_call: Optional[Dict[str, Any]] = None,
) -> ClassificationResult:
    """作用：使用 D-lite rule router 作为保守 fallback，并标记 strict sufficiency。"""
    decision = route_query(str(query))

    route = str(decision.path or WorkflowRoute.DIRECT.value).strip().upper()
    if route == WorkflowRoute.DECOMPOSE.value:
        question_type = QuestionType.EXPLICIT_COMPARE.value
        route_candidate = RouteCandidate.DECOMPOSE.value
    else:
        question_type = QuestionType.NARROW_FACT.value
        route_candidate = RouteCandidate.DIRECT.value

    return ClassificationResult(
        question_type=question_type,
        answerability=Answerability.UNKNOWN.value,
        route_candidate=route_candidate,
        route_policy=RoutePolicy.STRICT_SUFFICIENCY.value,
        confidence="low",
        reason=f"fallback_to_rule_router:{reason}; matched_keyword={decision.matched_keyword}",
        classifier_used="rule_fallback",
        fallback_used=True,
        fallback_reason=str(reason),
        raw_output=raw_output,
        duration_ms=float(duration_ms),
        model_call=model_call,
    )


def _extract_json_object(text: str) -> Dict[str, Any]:
    """作用：从 LLM 输出中提取 JSON 对象，兼容 markdown fence。"""
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw).strip()
        raw = re.sub(r"```$", "", raw).strip()

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        raise ValueError("no_json_object_found")

    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("json_not_object")
    return parsed


def _validate_and_build(
    parsed: Dict[str, Any],
    raw_output: str,
    duration_ms: float,
    model_call: Optional[Dict[str, Any]] = None,
) -> ClassificationResult:
    """作用：校验 LLM JSON 输出并构造 ClassificationResult。"""
    question_type = str(parsed.get("question_type", "")).strip().upper()
    answerability = str(parsed.get("answerability", "")).strip().upper()
    confidence = str(parsed.get("confidence", "low")).strip().lower()

    if question_type not in _VALID_QUESTION_TYPES:
        raise ValueError(f"invalid_question_type:{question_type}")
    if answerability not in _VALID_ANSWERABILITY:
        raise ValueError(f"invalid_answerability:{answerability}")
    if confidence not in _VALID_CONFIDENCE:
        confidence = "low"

    route_candidate, route_policy = _derive_route_candidate(
        question_type=question_type,
        answerability=answerability,
    )

    return ClassificationResult(
        question_type=question_type,
        answerability=answerability,
        route_candidate=route_candidate,
        route_policy=route_policy,
        confidence=confidence,
        reason=str(parsed.get("reason", "")).strip(),
        classifier_used="llm",
        fallback_used=False,
        fallback_reason=None,
        raw_output=str(raw_output),
        duration_ms=float(duration_ms),
        model_call=model_call,
    )


def _build_classifier_prompt(query: str, optional_history: Optional[List[Dict[str, Any]]] = None) -> str:
    """作用：构造严格 JSON 分类 prompt。"""
    history_text = json.dumps(optional_history or [], ensure_ascii=False)

    return f"""你是企业知识库 RAG 系统的问题分类器。
请根据 query 输出一个 JSON 对象。

你需要并行做出两个判断：

【判断 A】question_type：用户期待什么形态的答案？
- NARROW_FACT：单一事实点。
- EXPLICIT_COMPARE：问题中明确点名两个或多个对象进行比较。
- IMPLICIT_COMPARE：只点名一个对象，但回答需要隐含对照。
- OPEN_MULTI：答案天然是多个并列项、原因、风险、场景、失败模式或清单。
- SUMMARY：整体介绍、综述或总结。
- PROCEDURE：操作、排查、诊断、配置或处理流程。

【判断 B】answerability：问题本身是否存在 query-level 不可答或需澄清风险？
- IN_SCOPE：问题对象明确，且没有明显不可验证风险。
- OOD_CANDIDATE：请求未公开、未发布、未来不可验证或外部私有信息。
- NEEDS_CLARIFICATION：缺少必要对象、范围或约束，无法给出通用回答。
- UNKNOWN：边界不清，无法稳定判断。

判断 A 关注答案形态。
判断 B 关注问题对象和约束。
两个判断使用同一个 query，但关注点不同。

后续系统会处理 route 映射、证据检索和最终回答策略。
你只需输出这两个判断及置信度。

只输出 JSON：
{{
  "question_type": "NARROW_FACT",
  "answerability": "IN_SCOPE",
  "confidence": "high|medium|low",
  "reason": "一句话原因"
}}

history:
{history_text}

query:
{query}
"""


def _call_llm_classifier(
    query: str,
    optional_history: Optional[List[Dict[str, Any]]] = None,
    config_path: str = "config.yaml",
) -> Tuple[str, Dict[str, Any], int]:
    """
    作用：调用项目现有 OpenAI-compatible/Ollama client 做分类。
    注意：这里延迟导入，避免 classifier 与主 pipeline 形成启动期耦合。
    """
    from agentic_rag.config import GeneratorProfileConfig, load_config
    from agentic_rag.llm.client import LLMConfig, OllamaClient

    app_cfg = load_config(config_path)
    profile: GeneratorProfileConfig = app_cfg.generator.get_profile()

    cfg = LLMConfig(
        backend=str(profile.backend),
        model=str(profile.model),
        base_url=str(profile.base_url),
        api_key_env=str(profile.api_key_env),
        provider_tag=str(profile.provider_tag),
        temperature=0.0,
        top_p=1.0,
        num_predict=256,
        timeout_s=min(float(profile.timeout_s), 20.0),
        max_retries=0,
    )
    client = OllamaClient(cfg=cfg)
    text, token_usage, llm_ms = client.generate(_build_classifier_prompt(query=query, optional_history=optional_history))
    return str(text or "").strip(), dict(token_usage or {}), int(llm_ms)


def classify_query(
    query: str,
    optional_history: Optional[List[Dict[str, Any]]] = None,
    enabled: Optional[bool] = None,
    config_path: str = "config.yaml",
) -> ClassificationResult:
    """
    作用：
    - Phase D-full Step 7 的统一分类入口。
    - enabled=False 时只走 rule fallback，保证不影响 D-full-1 行为。
    - LLM 超时、异常、JSON 失败、低置信度时 fallback 到 rule router。
    """
    t0 = time.time()
    text = str(query or "").strip()

    if text == "":
        return ClassificationResult(
            question_type=QuestionType.NARROW_FACT.value,
            answerability=Answerability.NEEDS_CLARIFICATION.value,
            route_candidate=RouteCandidate.NEEDS_CLARIFICATION.value,
            route_policy=RoutePolicy.CLARIFY.value,
            confidence="high",
            reason="empty_query",
            classifier_used="rule_guard",
            fallback_used=False,
            fallback_reason=None,
            raw_output=None,
            duration_ms=float((time.time() - t0) * 1000.0),
        )

    should_enable = _load_classifier_enabled(config_path=config_path) if enabled is None else bool(enabled)
    if not should_enable:
        return _fallback_by_rule_router(
            query=text,
            reason="classifier_disabled",
            duration_ms=float((time.time() - t0) * 1000.0),
        )

    raw_output: Optional[str] = None
    try:
        raw_output, token_usage, llm_ms = _call_llm_classifier(
            query=text,
            optional_history=optional_history,
            config_path=config_path,
        )
        model_call = _build_classifier_model_call(
            token_usage=token_usage,
            latency_ms=float(llm_ms),
            api_error=False,
            timeout=False,
            error_type=None,
            error_message=None,
        )
        parsed = _extract_json_object(raw_output)
        result = _validate_and_build(
            parsed=parsed,
            raw_output=raw_output,
            duration_ms=float((time.time() - t0) * 1000.0),
            model_call=model_call,
        )

        if result.confidence == "low":
            return _fallback_by_rule_router(
                query=text,
                reason="low_confidence",
                duration_ms=float((time.time() - t0) * 1000.0),
                raw_output=raw_output,
                model_call=result.model_call,
            )

        return result

    except Exception as exc:
        elapsed_ms = float((time.time() - t0) * 1000.0)
        model_call = _build_classifier_model_call(
            token_usage=None,
            latency_ms=elapsed_ms,
            api_error=True,
            timeout="timeout" in type(exc).__name__.lower() or "timeout" in str(exc).lower(),
            error_type=type(exc).__name__,
            error_message=str(exc),
        )
        return _fallback_by_rule_router(
            query=text,
            reason=f"{type(exc).__name__}:{exc}",
            duration_ms=elapsed_ms,
            raw_output=raw_output,
            model_call=model_call,
        )
