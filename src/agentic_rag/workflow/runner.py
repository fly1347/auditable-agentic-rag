"""
作用：
- 提供 Phase D-full 的 WorkflowRunner。
- 在 D-full-1 阶段以 lift-and-shift 方式包装现有 query_pipeline.query。
- 不改变旧 pipeline 的 router、retrieve、rerank、sufficiency、rewrite、generate、prompt 行为。
- 只额外生成 WorkflowState / WorkflowStep，供 debug、replay、report 使用。

整体结构：
1. WorkflowRunResult：包装旧 Answer 与新增 WorkflowState。
2. WorkflowRunner.run：调用旧 query_pipeline.query，并构造 workflow trace。
3. 若旧 Answer 中缺少细分字段，则显式使用 None / 空数组，不编造数据。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import uuid4

from agentic_rag.observability.model_identity import ModelIdentity
from agentic_rag.observability.observability_record import (
    ModelCallRecord,
    ObservabilityRecord,
)
from agentic_rag.workflow.workflow_state import (
    RetrievalRound,
    WorkflowFinalStatus,
    WorkflowRoute,
    WorkflowState,
    WorkflowStep,
    WorkflowStepType,
)


@dataclass
class WorkflowRunResult:
    """作用：承载旧 pipeline 的回答结果与 D-full 新增 workflow 状态。"""

    answer: Any
    workflow_state: WorkflowState


class WorkflowRunner:
    """作用：D-full 工作流入口；D-full-1 只包装旧 query pipeline，不改变行为。"""

    def run(
        self,
        query: str,
        topk: int = 5,
        request_id: Optional[str] = None,
        run_id: Optional[str] = None,
        qid: Optional[str] = None,
        **query_kwargs: Any,
    ) -> WorkflowRunResult:
        """
        作用：
        - 调用旧 query_pipeline.query。
        - 从旧 Answer 中提取 path、flags、timings、agentic_steps。
        - 构造 WorkflowState。
        """
        rid = request_id or str(uuid4())

        # 延迟导入，避免 query_pipeline 未来接入 WorkflowRunner 时形成循环导入。
        from agentic_rag.query_pipeline import query as legacy_query

        answer = legacy_query(query=str(query), topk=int(topk), **query_kwargs)
        flags = self._get_flags(answer)

        route = self._infer_route(answer=answer, flags=flags)
        final_status = self._infer_final_status(flags=flags)

        state = WorkflowState(
            request_id=rid,
            query=str(query),
            run_id=run_id,
            qid=qid,
            route=route,
            final_status=final_status,
            failure_attribution=[],
            observability=ObservabilityRecord(
                request_id=rid,
                run_id=run_id,
                qid=qid,
                latency_ms=self._safe_float(getattr(answer, "timing_ms", None)),
            ),
        )
        user_context = query_kwargs.get("user_context")
        if isinstance(user_context, dict):
            state.extra["user_context_id"] = str(user_context.get("user_id") or "anonymous")
            state.extra["user_context_present"] = True
        self._add_observability_model_calls(state=state, flags=flags)
        self._add_route_steps(state=state, answer=answer, flags=flags)
        self._add_retrieval_round(state=state, answer=answer, flags=flags, topk=topk)
        self._add_sufficiency_steps(state=state, flags=flags)
        self._add_generation_step(state=state, answer=answer, flags=flags)
        self._add_build_response_step(state=state, answer=answer, flags=flags)

        return WorkflowRunResult(answer=answer, workflow_state=state)

    def _get_flags(self, answer: Any) -> Dict[str, Any]:
        """作用：安全读取旧 Answer.flags。"""
        raw = getattr(answer, "flags", None)
        return dict(raw) if isinstance(raw, dict) else {}

    def _add_observability_model_calls(self, state: WorkflowState, flags: Dict[str, Any]) -> None:
        """作用：把旧 Answer.flags 中的模型调用观测记录汇总进 WorkflowState.observability。"""
        if state.observability is None:
            return

        raw_call = flags.get("generator_model_call")
        if isinstance(raw_call, dict):
            state.observability.model_calls.append(self._model_call_from_dict(raw_call))

    def _model_call_from_dict(self, raw: Dict[str, Any]) -> ModelCallRecord:
        """作用：把 flags.generator_model_call dict 还原为 ModelCallRecord。"""
        identity_raw = raw.get("identity")
        identity_dict = dict(identity_raw) if isinstance(identity_raw, dict) else {}

        return ModelCallRecord(
            role=str(raw.get("role") or "generator"),
            identity=ModelIdentity.from_metadata(identity_dict),
            prompt_tokens=self._safe_int(raw.get("prompt_tokens")),
            completion_tokens=self._safe_int(raw.get("completion_tokens")),
            reasoning_tokens=self._safe_int(raw.get("reasoning_tokens")),
            total_tokens=self._safe_int(raw.get("total_tokens")),
            latency_ms=self._safe_float(raw.get("latency_ms")),
            estimated_cost_usd=self._safe_float(raw.get("estimated_cost_usd")),
            timeout=bool(raw.get("timeout", False)),
            api_error=bool(raw.get("api_error", False)),
            http_status=self._safe_int(raw.get("http_status")),
            error_type=str(raw.get("error_type")) if raw.get("error_type") is not None else None,
        )

    def _infer_route(self, answer: Any, flags: Dict[str, Any]) -> Optional[WorkflowRoute]:
        """作用：从旧 Answer / flags 中推断 D-full route。"""
        raw = (
            flags.get("actual_agentic_path")
            or flags.get("agentic_path")
            or flags.get("path")
            or getattr(answer, "path", None)
        )
        value = str(raw or "").strip().upper()

        if value == "DECOMPOSE":
            return WorkflowRoute.DECOMPOSE
        if value == "DIRECT":
            return WorkflowRoute.DIRECT
        if value == "OPEN_MULTI":
            return WorkflowRoute.OPEN_MULTI
        if value == "NEEDS_CLARIFICATION":
            return WorkflowRoute.NEEDS_CLARIFICATION
        if value == "REJECT":
            return WorkflowRoute.REJECT

        # D-full-1 不新增路径判断；旧流程缺字段时先默认 DIRECT，占位并等待 replay 对照。
        return WorkflowRoute.DIRECT

    def _infer_final_status(self, flags: Dict[str, Any]) -> WorkflowFinalStatus:
        """作用：从旧 refused 标志推断最终状态。"""
        refused = bool(flags.get("refused", False))
        if refused:
            return WorkflowFinalStatus.REFUSED
        return WorkflowFinalStatus.ANSWERED

    def _add_route_steps(self, state: WorkflowState, answer: Any, flags: Dict[str, Any]) -> None:
        """只记录本次实际控制执行路径的 route。

        classifier 对比已经移到离线 CER 回放；在线包装器不能在回答或拒答之后再次调用模型。
        """
        legacy_steps = getattr(answer, "agentic_steps", None)
        if legacy_steps is None:
            legacy_steps = flags.get("agentic_steps", [])
        state.extra["classifier"] = {"mode": "offline_replay_only", "executed": False}
        state.extra["actual_route_source"] = "legacy_pipeline"

        state.steps.append(
            WorkflowStep(
                step_type=WorkflowStepType.PLAN_ROUTE,
                name="legacy_route_observed",
                decision=state.route.value if state.route else None,
                input_summary={"query": state.query},
                output_summary={
                    "route": state.route.value if state.route else None,
                    "route_source": "legacy_pipeline",
                    "legacy_agentic_steps": legacy_steps,
                },
                duration_ms=None,
            )
        )

    def _add_retrieval_round(
        self,
        state: WorkflowState,
        answer: Any,
        flags: Dict[str, Any],
        topk: int,
    ) -> None:
        """作用：把旧检索结果摘要映射为 RetrievalRound + RETRIEVE step。"""
        evidence_count = flags.get("evidence_count")
        used_chunk_source_ids = flags.get("used_chunk_source_ids", [])
        evidence_pool_source_ids = flags.get("evidence_pool_source_ids", [])

        round_record = RetrievalRound(
            round_id=1,
            retrieval_query=state.query,
            route=state.route.value if state.route else None,
            topk=int(topk),
            hit_count=self._safe_int(evidence_count),
            rerank_applied=bool(flags.get("rerank_enabled", False)),
            diagnostics={
                "top1_score": flags.get("top1_score"),
                "top2_score": flags.get("top2_score"),
                "diff_top1_top2": flags.get("diff_top1_top2"),
                "unique_source_count": flags.get("unique_source_count"),
                "used_chunk_source_ids": used_chunk_source_ids,
                "evidence_pool_source_ids": evidence_pool_source_ids,
            },
        )
        state.retrieval_rounds.append(round_record)

        state.steps.append(
            WorkflowStep(
                step_type=WorkflowStepType.RETRIEVE,
                name="legacy_retrieval_observed",
                decision="retrieved",
                input_summary={"query": state.query, "topk": int(topk)},
                output_summary={
                    "hit_count": round_record.hit_count,
                    "used_chunk_source_ids": used_chunk_source_ids,
                    "evidence_pool_source_ids": evidence_pool_source_ids,
                },
                duration_ms=self._safe_float(getattr(answer, "retrieval_ms", None)),
            )
        )

        second_ms = self._safe_float(flags.get("second_retrieval_ms"))
        if second_ms is not None and second_ms > 0:
            second_query = str(flags.get("rewritten_query") or state.query)
            state.retrieval_rounds.append(
                RetrievalRound(
                    round_id=2,
                    retrieval_query=second_query,
                    route=str(flags.get("second_route_path") or "DIRECT"),
                    topk=int(topk),
                    hit_count=None,
                    rerank_applied=bool(flags.get("second_selective_rerank_triggered", False)),
                    diagnostics={
                        "second_route_keyword": flags.get("second_route_keyword"),
                        "second_selective_rerank_triggered": flags.get("second_selective_rerank_triggered"),
                        "second_selective_rerank_reason": flags.get("second_selective_rerank_reason"),
                        "second_selective_rerank_gap": flags.get("second_selective_rerank_gap"),
                        "second_selective_rerank_before_source_ids": flags.get("second_selective_rerank_before_source_ids", []),
                        "second_selective_rerank_after_source_ids": flags.get("second_selective_rerank_after_source_ids", []),
                    },
                )
            )

        if bool(flags.get("selective_rerank_triggered", False)) or bool(flags.get("rerank_enabled", False)):
            state.steps.append(
                WorkflowStep(
                    step_type=WorkflowStepType.RERANK,
                    name="legacy_rerank_observed",
                    decision="observed",
                    input_summary={
                        "rerank_enabled": flags.get("rerank_enabled"),
                        "selective_rerank_enabled": flags.get("selective_rerank_enabled"),
                    },
                    output_summary={
                        "selective_rerank_triggered": flags.get("selective_rerank_triggered"),
                        "selective_rerank_gap": flags.get("selective_rerank_gap"),
                        "selective_rerank_before_source_ids": flags.get("selective_rerank_before_source_ids"),
                        "selective_rerank_after_source_ids": flags.get("selective_rerank_after_source_ids"),
                    },
                    duration_ms=None,
                )
            )

    def _add_sufficiency_steps(self, state: WorkflowState, flags: Dict[str, Any]) -> None:
        """作用：把旧 sufficiency 字段映射为 CHECK_SUFFICIENCY step。"""
        first = flags.get("first_sufficiency_result", flags.get("first_sufficiency"))
        second = flags.get("second_sufficiency_result", flags.get("second_sufficiency"))

        if first is None and second is None:
            return

        state.steps.append(
            WorkflowStep(
                step_type=WorkflowStepType.CHECK_SUFFICIENCY,
                name="legacy_sufficiency_observed",
                decision=str(second or first),
                input_summary={"source": "legacy_flags"},
                output_summary={
                    "first_sufficiency_result": first,
                    "second_sufficiency_result": second,
                    "refused": flags.get("refused"),
                    "refuse_reason": flags.get("refuse_reason"),
                },
                duration_ms=self._safe_float(flags.get("first_sufficiency_ms")),
            )
        )

    def _add_generation_step(self, state: WorkflowState, answer: Any, flags: Dict[str, Any]) -> None:
        """作用：记录旧生成阶段耗时，不改变生成逻辑。"""
        if bool(flags.get("refused", False)):
            return
        generator_error_type = flags.get("generator_error_type")
        generator_model_call = flags.get("generator_model_call")

        state.steps.append(
            WorkflowStep(
                step_type=WorkflowStepType.GENERATE_ANSWER,
                name="legacy_generation_observed",
                decision="llm_error" if generator_error_type else "generated",
                input_summary={},
                output_summary={
                    "answer_len": len(str(getattr(answer, "answer_text", "") or "")),
                    "generator_identity": flags.get("generator_identity"),
                    "generator_model_call_present": isinstance(generator_model_call, dict),
                    "generator_error_type": generator_error_type,
                },
                duration_ms=self._safe_float(getattr(answer, "generation_ms", None)),
                model_call=self._model_call_from_dict(generator_model_call)
                if isinstance(generator_model_call, dict)
                else None,
            )
        )

    def _add_build_response_step(self, state: WorkflowState, answer: Any, flags: Dict[str, Any]) -> None:
        """作用：记录响应组装阶段摘要。"""
        citations = getattr(answer, "citations", []) or []

        state.steps.append(
            WorkflowStep(
                step_type=WorkflowStepType.BUILD_RESPONSE,
                name="legacy_response_observed",
                decision=state.final_status.value if state.final_status else None,
                input_summary={},
                output_summary={
                    "citation_count": len(citations),
                    "refused": flags.get("refused"),
                    "refuse_reason": flags.get("refuse_reason"),
                },
                duration_ms=None,
            )
        )

    def _safe_float(self, value: Any) -> Optional[float]:
        """作用：安全转换 float，失败则返回 None。"""
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None

    def _safe_int(self, value: Any) -> Optional[int]:
        """作用：安全转换 int，失败则返回 None。"""
        if value is None:
            return None
        try:
            return int(value)
        except Exception:
            return None
