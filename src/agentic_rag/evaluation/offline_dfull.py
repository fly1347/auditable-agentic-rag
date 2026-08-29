"""
程序作用：
在主链运行结束后，直接基于冻结 CER 执行 D-full 分类、引用支持、冲突与不确定性评估。

整体结构：
1）辅助函数从 CER 提取题目预期、提示证据、最终证据和 sufficiency 观察；
2）依次运行 classifier、citation、conflict、uncertainty 四类离线阶段；
3）run_offline_dfull_record 汇总阶段记录、模型调用、用量和来源绑定。
"""

from __future__ import annotations

import time
from typing import Any, Mapping, Optional

from agentic_rag.control.classifier import classify_query
from agentic_rag.evaluation.offline_record import (
    OfflineEvaluationRecord,
    OfflineStageRecord,
    normalize_model_call,
    price_model_calls,
    source_binding,
    stable_sha256,
)
from agentic_rag.evidence.citation_support import evaluate_citation_support
from agentic_rag.evidence.conflict import detect_conflicts
from agentic_rag.evidence.uncertainty import (
    build_uncertainty_report,
    uncertainty_report_to_dict,
)
from agentic_rag.execution.record import CanonicalExecutionRecord


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _duration_ms(started: float) -> float:
    return float((time.perf_counter() - started) * 1000.0)


def _expected_behavior(case: Mapping[str, Any]) -> str:
    value = str(case.get("expected_behavior") or "answer").strip().lower()
    return "reject" if value in {"reject", "refuse", "refused"} else "answer"


def _latest_sufficiency(record: CanonicalExecutionRecord) -> dict[str, Any]:
    second_contract = _dict(record.sufficiency.get("second_contract"))
    first_contract = _dict(record.sufficiency.get("first_contract"))
    contract = second_contract or first_contract
    contract_round = 2 if second_contract else 1 if first_contract else None
    result = _dict(contract.get("result"))
    raw_verdict = str(result.get("verdict") or "").strip().upper() or None
    control_verdict = (
        record.sufficiency.get("second")
        if record.sufficiency.get("second") not in (None, "")
        else record.sufficiency.get("first")
    )
    return {
        "contract_round": contract_round,
        "mode": contract.get("mode") or "not_observed",
        "raw_verdict": raw_verdict,
        "control_verdict": control_verdict,
        "confidence": result.get("confidence"),
        "missing_evidence": list(result.get("missing_evidence") or []),
        "supporting_evidence_ids": list(result.get("supporting_evidence_ids") or []),
        "conflict_evidence_ids": list(result.get("conflict_evidence_ids") or []),
        "reason": result.get("reason"),
        "evidence_packet": _dict(contract.get("evidence_packet")),
    }


def _prompt_chunks(record: CanonicalExecutionRecord) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    for raw in _list(record.prompt.get("visible_evidence")):
        item = _dict(raw)
        if not item:
            continue
        chunks.append(
            {
                **item,
                "evidence_id": item.get("marker") or item.get("chunk_id"),
                "source_path": item.get("source_id"),
                "in_prompt": True,
            }
        )
    return chunks


def _selected_chunks(record: CanonicalExecutionRecord) -> list[dict[str, Any]]:
    return [_dict(item) for item in _list(record.evidence.get("selected")) if _dict(item)]


def _evidence_packet(
    record: CanonicalExecutionRecord,
    sufficiency: Mapping[str, Any],
) -> tuple[dict[str, Any], str]:
    packet = _dict(sufficiency.get("evidence_packet"))
    if _list(packet.get("items")):
        return packet, "structured_sufficiency_contract"

    items = _prompt_chunks(record)
    if not items:
        items = [
            {
                **item,
                "evidence_id": item.get("chunk_id"),
                "source_path": item.get("source_id"),
                "in_prompt": False,
            }
            for item in _selected_chunks(record)
        ]
    return {
        "items": items,
        "known_gaps": [],
        "source_coverage": {
            "unique_source_count": len(
                {str(item.get("source_id") or item.get("source_path") or "") for item in items}
                - {""}
            )
        },
        "compression_policy": "cer_prompt_visible_projection",
    }, "cer_prompt_visible_projection"


def _error_stage(name: str, mode: str, started: float, exc: Exception) -> OfflineStageRecord:
    return OfflineStageRecord(
        name=name,
        status="error",
        mode=mode,
        duration_ms=_duration_ms(started),
        output={},
        error={"error_type": type(exc).__name__, "message": str(exc)},
    )


def run_offline_dfull_record(
    record: CanonicalExecutionRecord,
    case: Mapping[str, Any],
    *,
    evaluation_run_id: str,
    classifier_mode: str,
    config_path: str,
    dataset_sha256: str | None = None,
    evaluation_config_sha256: str | None = None,
    reused_classifier_record: OfflineEvaluationRecord | None = None,
) -> OfflineEvaluationRecord:
    """针对一条冻结 CER 运行分类、引用、冲突和不确定性评估。"""
    mode = str(classifier_mode).strip().lower()
    if mode not in {"rule", "llm", "skip", "reuse"}:
        raise ValueError("classifier_mode must be rule, llm, skip, or reuse")
    if mode == "reuse" and reused_classifier_record is None:
        raise ValueError("classifier_mode=reuse requires reused_classifier_record")

    qid = str(record.identity.get("qid") or "")
    binding = source_binding(record)
    if dataset_sha256:
        binding["dataset_sha256"] = str(dataset_sha256)
    stages: list[OfflineStageRecord] = []
    all_model_calls: list[dict[str, Any]] = []
    total_started = time.perf_counter()

    prompt_chunks = _prompt_chunks(record)
    selected_chunks = _selected_chunks(record)
    sufficiency = _latest_sufficiency(record)
    packet, packet_source = _evidence_packet(record, sufficiency)

    classifier_output: dict[str, Any] = {}
    classifier_started = time.perf_counter()
    classifier_reused_from_run_id: str | None = None
    if mode == "reuse":
        previous = reused_classifier_record
        assert previous is not None
        if str(previous.identity.get("qid") or "") != qid:
            raise ValueError(f"reused classifier qid mismatch: expected {qid}")
        if str(previous.source.get("source_cer_sha256") or "") != str(binding.get("source_cer_sha256") or ""):
            raise ValueError(f"reused classifier source CER mismatch for {qid}")
        previous_stage = next((stage for stage in previous.stages if stage.name == "classifier"), None)
        if previous_stage is None:
            raise ValueError(f"reused classifier stage missing for {qid}")
        classifier_output = dict(previous_stage.output or {})
        classifier_reused_from_run_id = str(previous.identity.get("evaluation_run_id") or "") or None
        previous_call_ids = {
            str(ref.get("call_id") or "")
            for ref in list(previous_stage.model_calls or [])
            if isinstance(ref, Mapping) and ref.get("call_id")
        }
        reused_calls = [
            dict(call)
            for call in list(previous.model_calls or [])
            if isinstance(call, Mapping)
            and (
                str(call.get("call_id") or "") in previous_call_ids
                or str(call.get("role") or "") == "classifier"
            )
        ]
        all_model_calls.extend(reused_calls)
        stages.append(
            OfflineStageRecord(
                name="classifier",
                status=previous_stage.status,
                mode=previous_stage.mode,
                duration_ms=float(previous_stage.duration_ms or 0.0),
                output=classifier_output,
                model_calls=[dict(ref) for ref in list(previous_stage.model_calls or [])],
                error=(
                    dict(previous_stage.error)
                    if isinstance(previous_stage.error, Mapping)
                    else previous_stage.error
                ),
            )
        )
    elif mode == "skip":
        stages.append(
            OfflineStageRecord(
                name="classifier",
                status="not_evaluated",
                mode="skip",
                duration_ms=_duration_ms(classifier_started),
                output={"reason": "classifier_skipped"},
            )
        )
    else:
        try:
            classification = classify_query(
                record.query,
                enabled=mode == "llm",
                config_path=config_path,
            ).to_dict()
            raw_call = classification.pop("model_call", None)
            if isinstance(raw_call, Mapping):
                call = normalize_model_call(
                    raw_call,
                    qid=qid,
                    stage="offline_classify_query",
                    role="classifier",
                    index=len(all_model_calls) + 1,
                )
                all_model_calls.append(call)
                call_refs = [{"call_id": call["call_id"]}]
            else:
                call_refs = []
            classifier_output = classification
            provider_failed = any(bool(call.get("api_error")) for call in all_model_calls)
            stages.append(
                OfflineStageRecord(
                    name="classifier",
                    status="error" if provider_failed else "ok",
                    mode=mode,
                    duration_ms=_duration_ms(classifier_started),
                    output=classification,
                    model_calls=call_refs,
                    error=(
                        {
                            "error_type": all_model_calls[-1].get("error_type"),
                            "message": all_model_calls[-1].get("error_message"),
                        }
                        if provider_failed
                        else None
                    ),
                )
            )
        except Exception as exc:  # noqa: BLE001
            stages.append(_error_stage("classifier", mode, classifier_started, exc))

    suff_started = time.perf_counter()
    suff_status = "ok" if sufficiency.get("raw_verdict") else "unknown"
    stages.append(
        OfflineStageRecord(
            name="structured_sufficiency",
            status=suff_status,
            mode=str(sufficiency.get("mode") or "not_observed"),
            duration_ms=_duration_ms(suff_started),
            output={key: value for key, value in sufficiency.items() if key != "evidence_packet"},
        )
    )

    citation_output: dict[str, Any] = {}
    citation_started = time.perf_counter()
    try:
        citation_output = evaluate_citation_support(
            answer=str(record.outcome.get("answer") or ""),
            citations=_list(record.outcome.get("citations")),
            prompt_chunks=prompt_chunks,
            retrieved_chunks=selected_chunks,
            evidence_packet=packet,
            refused=str(record.outcome.get("status") or "") == "REFUSED",
            expected_behavior=_expected_behavior(case),
        ).to_dict()
        citation_status = (
            "not_applicable"
            if citation_output.get("citation_support_label") == "not_applicable"
            else "ok"
        )
        stages.append(
            OfflineStageRecord(
                name="citation_support",
                status=citation_status,
                mode="rule",
                duration_ms=_duration_ms(citation_started),
                output=citation_output,
            )
        )
    except Exception as exc:  # noqa: BLE001
        stages.append(_error_stage("citation_support", "rule", citation_started, exc))

    conflict_output: dict[str, Any] = {}
    conflict_started = time.perf_counter()
    try:
        conflict_output = detect_conflicts(
            evidence_packet=packet,
            question_type=classifier_output.get("question_type"),
            sufficiency_verdict=sufficiency.get("raw_verdict"),
            force=False,
            max_conflicts=5,
        ).to_dict()
        conflict_status = "ok" if conflict_output.get("triggered") is True else "not_applicable"
        stages.append(
            OfflineStageRecord(
                name="conflict",
                status=conflict_status,
                mode="rule_conditional",
                duration_ms=_duration_ms(conflict_started),
                output=conflict_output,
            )
        )
    except Exception as exc:  # noqa: BLE001
        stages.append(_error_stage("conflict", "rule_conditional", conflict_started, exc))

    uncertainty_output: dict[str, Any] = {}
    uncertainty_started = time.perf_counter()
    dependency_errors = {
        stage.name for stage in stages if stage.name in {"citation_support", "conflict"} and stage.status == "error"
    }
    if dependency_errors:
        stages.append(
            OfflineStageRecord(
                name="uncertainty",
                status="not_evaluated",
                mode="rule_aggregate",
                duration_ms=_duration_ms(uncertainty_started),
                output={"missing_dependencies": sorted(dependency_errors)},
            )
        )
    else:
        try:
            report = build_uncertainty_report(
                sufficiency={
                    "result": {
                        "verdict": sufficiency.get("raw_verdict"),
                        "confidence": sufficiency.get("confidence"),
                        "missing_evidence": sufficiency.get("missing_evidence") or [],
                        "reason": sufficiency.get("reason"),
                    }
                },
                conflicts=conflict_output,
                citation_support=citation_output,
                evidence_packet=packet,
                refused_reason=record.outcome.get("refusal_reason"),
            )
            uncertainty_output = uncertainty_report_to_dict(report)
            stages.append(
                OfflineStageRecord(
                    name="uncertainty",
                    status="ok",
                    mode="rule_aggregate",
                    duration_ms=_duration_ms(uncertainty_started),
                    output=uncertainty_output,
                )
            )
        except Exception as exc:  # noqa: BLE001
            stages.append(_error_stage("uncertainty", "rule_aggregate", uncertainty_started, exc))

    priced_calls, usage = price_model_calls(all_model_calls)
    priced_by_id = {str(call.get("call_id")): call for call in priced_calls}
    for stage in stages:
        stage.model_calls = [
            {"call_id": ref.get("call_id")}
            for ref in stage.model_calls
            if str(ref.get("call_id")) in priced_by_id
        ]

    stage_durations = {f"{stage.name}_ms": stage.duration_ms for stage in stages}
    offline_total_ms = (
        sum(float(stage.duration_ms or 0.0) for stage in stages)
        if mode == "reuse"
        else _duration_ms(total_started)
    )
    problematic = [stage.name for stage in stages if stage.status in {"error", "unknown", "not_evaluated"}]
    overall_status = "complete" if not problematic else "partial"
    identity = {
        "evaluation_run_id": evaluation_run_id,
        "evaluation_record_id": stable_sha256(
            {
                "evaluation_run_id": evaluation_run_id,
                "source_cer_sha256": binding["source_cer_sha256"],
                "evaluation_config_sha256": evaluation_config_sha256,
            }
        )[:24],
        "qid": qid,
        "evaluation_config_sha256": evaluation_config_sha256,
        "classifier_reused": mode == "reuse",
        "classifier_reused_from_evaluation_run_id": classifier_reused_from_run_id,
    }
    return OfflineEvaluationRecord(
        schema_version="1.0.0",
        identity=identity,
        source=binding,
        query=record.query,
        input_refs={
            "expected_behavior": _expected_behavior(case),
            "actual_route": record.route.get("actual_route"),
            "answer_status": record.outcome.get("status"),
            "prompt_visible_count": len(prompt_chunks),
            "selected_evidence_count": len(selected_chunks),
            "citation_count": len(_list(record.outcome.get("citations"))),
            "evidence_packet_source": packet_source,
            "evidence_packet_item_count": len(_list(packet.get("items"))),
            "citation_support_evidence_scope": "actual_citations",
            "classifier_reused_from_evaluation_run_id": classifier_reused_from_run_id,
        },
        stages=stages,
        model_calls=priced_calls,
        usage=usage,
        timing={**stage_durations, "offline_total_ms": offline_total_ms},
        outcome={
            "status": overall_status,
            "problematic_stages": problematic,
            "classifier_question_type": classifier_output.get("question_type"),
            "classifier_answerability": classifier_output.get("answerability"),
            "classifier_route_candidate": classifier_output.get("route_candidate"),
            "classifier_confidence": classifier_output.get("confidence"),
            "structured_sufficiency_observed": sufficiency.get("mode") == "structured",
            "sufficiency_raw_verdict": sufficiency.get("raw_verdict"),
            "sufficiency_control_verdict": sufficiency.get("control_verdict"),
            "sufficiency_confidence": sufficiency.get("confidence"),
            "citation_support_label": citation_output.get("citation_support_label"),
            "unsupported_claim_count": citation_output.get("unsupported_claim_count"),
            "conflict_triggered": conflict_output.get("triggered"),
            "conflict_count": conflict_output.get("conflict_count"),
            "uncertainty_level": uncertainty_output.get("level"),
        },
    )


__all__ = ["run_offline_dfull_record"]
