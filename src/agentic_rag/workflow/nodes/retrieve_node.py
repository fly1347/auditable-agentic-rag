"""
作用：
- 提供 Phase D-full Step 8 的 retrieve workflow node。
- 按 state.route 执行 DIRECT / DECOMPOSE / OPEN_MULTI 的最小检索。
- DECOMPOSE / OPEN_MULTI 使用 state.extra["generated_subqueries"]["retrieval_queries"]。
- 多路检索结果使用 RRF，记录各 query 贡献并按 chunk_id 去重。
- 当前不改 query_pipeline 主链路，不改 rerank / sufficiency / generation。

整体结构：
1. 根据 route 判断是否跳过检索。
2. 使用 Retriever.run 执行一次或多次检索。
3. 将检索输出标准化为 RetrievalResult。
4. 合并多路结果并写入 state.extra["retrieval_result"]。
5. 追加 RetrievalRound 与 RETRIEVE step。
"""

from __future__ import annotations

import time
from typing import Any, List, Optional

from agentic_rag.retrieve.retriever import Retriever
from agentic_rag.retrieve.fusion import FusionInput, rrf_fuse
from agentic_rag.types import Chunk, RetrievalResult
from agentic_rag.workflow.workflow_state import (
    RetrievalRound,
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


def _hit_to_chunk(hit: Any) -> Chunk:
    """作用：兼容 Retriever hit 对象并转成 Chunk。"""
    offset_start = int(getattr(hit, "offset_start", 0))
    offset_end = int(getattr(hit, "offset_end", 0))
    if (offset_start == 0 and offset_end == 0) and hasattr(hit, "offset"):
        offset = getattr(hit, "offset")
        if isinstance(offset, (tuple, list)) and len(offset) == 2:
            offset_start = int(offset[0])
            offset_end = int(offset[1])

    return Chunk(
        chunk_id=str(getattr(hit, "chunk_id", "")),
        source_id=str(getattr(hit, "source_id", "")),
        doc_hash=str(getattr(hit, "doc_hash", "")),
        text=str(getattr(hit, "text", "")),
        offset_start=int(offset_start),
        offset_end=int(offset_end),
        metadata=dict(getattr(hit, "metadata", {}) or {}),
    )


def _retriever_output_to_result(query: str, topk: int, output: Any, elapsed_ms: float) -> RetrievalResult:
    """作用：把 Retriever 输出统一成 RetrievalResult。"""
    if isinstance(output, RetrievalResult):
        return output

    if hasattr(output, "chunks"):
        chunks_any = getattr(output, "chunks", [])
        scores_any = getattr(output, "scores", [])
        return RetrievalResult(
            query=str(query),
            chunks=list(chunks_any or []),
            scores=[float(x) for x in list(scores_any or [])],
            topk=int(topk),
            timing_ms=float(elapsed_ms),
        )

    if isinstance(output, dict):
        hits = list(output.get("hits", []) or [])
    elif isinstance(output, list):
        hits = list(output)
    else:
        hits = list(getattr(output, "hits", []) or [])

    chunks = [_hit_to_chunk(hit) for hit in hits]
    scores = [float(getattr(hit, "score", 0.0)) for hit in hits]

    return RetrievalResult(
        query=str(query),
        chunks=chunks,
        scores=scores,
        topk=int(topk),
        timing_ms=float(elapsed_ms),
    )


def _retrieve_once(retriever: Retriever, query: str, topk: int) -> RetrievalResult:
    """作用：执行一次标准检索。"""
    t0 = time.time()
    output = retriever.run(query=str(query), topk=int(topk))
    elapsed_ms = float((time.time() - t0) * 1000.0)
    return _retriever_output_to_result(
        query=str(query),
        topk=int(topk),
        output=output,
        elapsed_ms=elapsed_ms,
    )


def _dedupe_merge_results(query: str, topk: int, results: List[RetrievalResult]) -> RetrievalResult:
    """作用：按秩融合多路结果，不跨 query 比较原始向量分数。"""
    total_ms = sum(float(item.timing_ms) for item in results)
    return rrf_fuse(
        query=str(query),
        inputs=[
            FusionInput(result=item, query_role=f"workflow_query_{index}", round_id=1)
            for index, item in enumerate(results, start=1)
        ],
        topk=int(topk),
        elapsed_ms=float(total_ms),
    )


def _source_ids(chunks: List[Chunk]) -> List[str]:
    """作用：按顺序提取 source_id 并去重。"""
    out: List[str] = []
    for chunk in chunks:
        source_id = str(chunk.source_id)
        if source_id not in out:
            out.append(source_id)
    return out


def _get_retrieval_queries(state: WorkflowState) -> List[str]:
    """作用：读取 generate_subqueries_node 产出的检索查询；缺失时回退 original query。"""
    generated = state.extra.get("generated_subqueries", {})
    generated_dict = dict(generated) if isinstance(generated, dict) else {}
    queries_raw = generated_dict.get("retrieval_queries", [])

    queries: List[str] = []
    if isinstance(queries_raw, list):
        queries = [str(item).strip() for item in queries_raw if str(item or "").strip()]

    if not queries:
        queries = [str(state.query)]

    seen: set[str] = set()
    deduped: List[str] = []
    for item in queries:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)

    return deduped


def run_retrieve_node(
    state: WorkflowState,
    topk: int = 5,
    retriever: Optional[Retriever] = None,
) -> RetrievalResult:
    """
    作用：
    - 按 state.route 执行最小检索。
    - DIRECT 单路检索。
    - DECOMPOSE / OPEN_MULTI 多路检索后合并去重。
    - REJECT / NEEDS_CLARIFICATION 跳过检索。
    """
    t0 = time.time()
    route = _route_value(state)

    if route in {WorkflowRoute.REJECT.value, WorkflowRoute.NEEDS_CLARIFICATION.value}:
        result = RetrievalResult(
            query=str(state.query),
            chunks=[],
            scores=[],
            topk=int(topk),
            timing_ms=0.0,
        )
        state.extra["retrieval_result"] = result
        state.retrieval_rounds.append(
            RetrievalRound(
                round_id=len(state.retrieval_rounds) + 1,
                retrieval_query=str(state.query),
                route=route,
                topk=int(topk),
                hit_count=0,
                rerank_applied=False,
                diagnostics={"skipped": True, "reason": f"route={route}"},
            )
        )
        state.steps.append(
            WorkflowStep(
                step_type=WorkflowStepType.RETRIEVE,
                name="retrieve_skipped",
                decision="skipped",
                input_summary={"query": state.query, "route": route, "topk": int(topk)},
                output_summary={"hit_count": 0, "reason": f"route={route}"},
                duration_ms=float((time.time() - t0) * 1000.0),
            )
        )
        return result

    actual_retriever = retriever or Retriever()
    retrieval_queries = [str(state.query)] if route == WorkflowRoute.DIRECT.value else _get_retrieval_queries(state)

    per_query_results: List[RetrievalResult] = []
    for idx, retrieval_query in enumerate(retrieval_queries, start=1):
        rr = _retrieve_once(
            retriever=actual_retriever,
            query=str(retrieval_query),
            topk=int(topk),
        )
        per_query_results.append(rr)
        state.retrieval_rounds.append(
            RetrievalRound(
                round_id=len(state.retrieval_rounds) + 1,
                retrieval_query=str(retrieval_query),
                route=route,
                topk=int(topk),
                hit_count=len(list(rr.chunks or [])),
                rerank_applied=bool(rr.rerank_applied),
                diagnostics={
                    "query_index": idx,
                    "source_ids": _source_ids(list(rr.chunks or [])),
                    "timing_ms": float(rr.timing_ms),
                },
            )
        )

    if len(per_query_results) == 1:
        result = per_query_results[0]
    else:
        result = _dedupe_merge_results(
            query=str(state.query),
            topk=int(topk),
            results=per_query_results,
        )

    state.extra["retrieval_result"] = result
    state.extra["retrieval_queries"] = retrieval_queries
    state.extra["retrieval_route"] = route

    state.steps.append(
        WorkflowStep(
            step_type=WorkflowStepType.RETRIEVE,
            name="retrieve_by_planned_route",
            decision=f"retrieved:{len(list(result.chunks or []))}",
            input_summary={
                "query": state.query,
                "route": route,
                "topk": int(topk),
                "retrieval_queries": retrieval_queries,
            },
            output_summary={
                "hit_count": len(list(result.chunks or [])),
                "source_ids": _source_ids(list(result.chunks or [])),
                "merged": len(per_query_results) > 1,
                "round_count": len(per_query_results),
                "timing_ms": float(result.timing_ms),
            },
            duration_ms=float((time.time() - t0) * 1000.0),
        )
    )

    return result


# 兼容短命名。
retrieve_node = run_retrieve_node
