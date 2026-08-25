"""
作用：
- 提供 Phase D-full Step 8 的 generate subqueries workflow node。
- 为 DECOMPOSE / OPEN_MULTI 路径生成检索子查询。
- 子查询由本节点生成，不从 classifier_output.suggested_subqueries 读取。
- 生成失败时 fallback original-only，并记录到 workflow trace。

整体结构：
1. 根据 state.route 判断是否需要子查询。
2. 优先使用 LLM 生成 DECOMPOSE 子查询或 OPEN_MULTI facets。
3. 失败时 fallback 到 original-only。
4. 写入 state.extra["generated_subqueries"] 并追加 GENERATE_SUBQUERIES step。
"""

from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, List

from agentic_rag.workflow.workflow_state import (
    WorkflowRoute,
    WorkflowState,
    WorkflowStep,
    WorkflowStepType,
)


def _route_value(state: WorkflowState) -> str:
    """作用：安全读取当前计划 route。"""
    if state.route is None:
        return WorkflowRoute.DIRECT.value
    return str(state.route.value).strip().upper()


def _dedupe_queries(queries: List[str]) -> List[str]:
    """作用：按顺序去重并过滤空查询。"""
    seen: set[str] = set()
    out: List[str] = []
    for item in queries:
        text = str(item or "").strip()
        if text == "" or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _extract_json(text: str) -> Dict[str, Any]:
    """作用：从 LLM 输出中提取 JSON 对象。"""
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?", "", raw).strip()
        raw = re.sub(r"```$", "", raw).strip()

    try:
        parsed = json.loads(raw)
        return dict(parsed) if isinstance(parsed, dict) else {}
    except Exception:
        pass

    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    if not match:
        return {}

    parsed = json.loads(match.group(0))
    return dict(parsed) if isinstance(parsed, dict) else {}


def _build_prompt(query: str, route: str) -> str:
    """作用：构造子查询生成 prompt。"""
    if route == WorkflowRoute.DECOMPOSE.value:
        return f"""你是企业知识库 RAG 系统的检索子查询生成器。
当前路径是 DECOMPOSE。

请把用户问题拆成两个独立检索子查询。
要求：
- 保留原始问题的核心对象。
- 子查询用于检索，不用于直接回答。
- 不要输出解释。
- 只输出 JSON。

JSON schema:
{{
  "subqueries": ["...", "..."]
}}

query:
{query}
"""

    return f"""你是企业知识库 RAG 系统的检索 facet 生成器。
当前路径是 OPEN_MULTI。

请为用户问题生成 2 到 4 个检索 facet queries。
要求：
- 覆盖不同方面、原因、风险、场景、失败模式或检查项。
- 子查询用于检索，不用于直接回答。
- 不要输出解释。
- 只输出 JSON。

JSON schema:
{{
  "subqueries": ["...", "..."]
}}

query:
{query}
"""


def _call_llm_for_subqueries(query: str, route: str) -> str:
    """
    作用：调用项目默认 LLM client 生成子查询。
    注意：失败由外层捕获，fallback original-only。
    """
    from agentic_rag.config import GeneratorProfileConfig, load_config
    from agentic_rag.llm.client import LLMConfig, OllamaClient

    app_cfg = load_config("config.yaml")
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
    text, _, _ = client.generate(_build_prompt(query=query, route=route))
    return str(text or "").strip()


def _fallback_subqueries(query: str, route: str, reason: str) -> Dict[str, Any]:
    """作用：构造 original-only fallback 子查询结果。"""
    return {
        "route": route,
        "subqueries": [],
        "retrieval_queries": [str(query)],
        "fallback_used": True,
        "fallback_reason": str(reason),
        "raw_output": None,
    }


def run_generate_subqueries_node(
    state: WorkflowState,
    use_llm: bool = True,
) -> List[str]:
    """
    作用：
    - 为 DECOMPOSE / OPEN_MULTI 生成子查询。
    - DIRECT / REJECT / NEEDS_CLARIFICATION 不生成子查询。
    - 返回用于检索的 query 列表，始终包含 original query。
    """
    t0 = time.time()
    route = _route_value(state)
    original_query = str(state.query)

    if route in {WorkflowRoute.REJECT.value, WorkflowRoute.NEEDS_CLARIFICATION.value}:
        result = {
            "route": route,
            "subqueries": [],
            "retrieval_queries": [],
            "fallback_used": False,
            "fallback_reason": None,
            "raw_output": None,
        }
        state.extra["generated_subqueries"] = result
        state.steps.append(
            WorkflowStep(
                step_type=WorkflowStepType.GENERATE_SUBQUERIES,
                name="generate_subqueries_skipped",
                decision="skipped",
                input_summary={"query": original_query, "route": route},
                output_summary=result,
                duration_ms=float((time.time() - t0) * 1000.0),
            )
        )
        return []

    if route not in {WorkflowRoute.DECOMPOSE.value, WorkflowRoute.OPEN_MULTI.value}:
        result = {
            "route": route,
            "subqueries": [],
            "retrieval_queries": [original_query],
            "fallback_used": False,
            "fallback_reason": None,
            "raw_output": None,
        }
        state.extra["generated_subqueries"] = result
        state.steps.append(
            WorkflowStep(
                step_type=WorkflowStepType.GENERATE_SUBQUERIES,
                name="generate_subqueries_skipped",
                decision="skipped",
                input_summary={"query": original_query, "route": route},
                output_summary=result,
                duration_ms=float((time.time() - t0) * 1000.0),
            )
        )
        return list(result["retrieval_queries"])

    if not use_llm:
        result = _fallback_subqueries(query=original_query, route=route, reason="llm_disabled")
        state.extra["generated_subqueries"] = result
        state.steps.append(
            WorkflowStep(
                step_type=WorkflowStepType.GENERATE_SUBQUERIES,
                name="generate_subqueries_fallback_original_only",
                decision="fallback_original_only",
                input_summary={"query": original_query, "route": route, "use_llm": use_llm},
                output_summary=result,
                duration_ms=float((time.time() - t0) * 1000.0),
            )
        )
        return list(result["retrieval_queries"])

    try:
        raw_output = _call_llm_for_subqueries(query=original_query, route=route)
        parsed = _extract_json(raw_output)
        subqueries_raw = parsed.get("subqueries", [])
        subqueries = [str(x).strip() for x in subqueries_raw] if isinstance(subqueries_raw, list) else []
        subqueries = _dedupe_queries(subqueries)

        retrieval_queries = _dedupe_queries([original_query] + subqueries)
        if not retrieval_queries:
            retrieval_queries = [original_query]

        result = {
            "route": route,
            "subqueries": subqueries,
            "retrieval_queries": retrieval_queries,
            "fallback_used": False,
            "fallback_reason": None,
            "raw_output": raw_output,
        }
        state.extra["generated_subqueries"] = result
        state.steps.append(
            WorkflowStep(
                step_type=WorkflowStepType.GENERATE_SUBQUERIES,
                name="generate_subqueries_llm",
                decision=f"queries={len(retrieval_queries)}",
                input_summary={"query": original_query, "route": route, "use_llm": use_llm},
                output_summary={
                    "subqueries": subqueries,
                    "retrieval_queries": retrieval_queries,
                    "fallback_used": False,
                },
                duration_ms=float((time.time() - t0) * 1000.0),
            )
        )
        return retrieval_queries

    except Exception as exc:
        result = _fallback_subqueries(
            query=original_query,
            route=route,
            reason=f"{type(exc).__name__}:{exc}",
        )
        state.extra["generated_subqueries"] = result
        state.steps.append(
            WorkflowStep(
                step_type=WorkflowStepType.GENERATE_SUBQUERIES,
                name="generate_subqueries_fallback_original_only",
                decision="fallback_original_only",
                input_summary={"query": original_query, "route": route, "use_llm": use_llm},
                output_summary=result,
                duration_ms=float((time.time() - t0) * 1000.0),
            )
        )
        return list(result["retrieval_queries"])


# 兼容短命名。
generate_subqueries_node = run_generate_subqueries_node
