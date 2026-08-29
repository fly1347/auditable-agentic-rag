"""
程序作用：
把 CER 原生的离线 D-full 评估记录整理成逐题报告、阶段账本、模型调用表和运行清单。

整体结构：
1）辅助函数读取阶段、格式化数值并汇总用量和分布；
2）生成总体摘要、逐题分析、耗时成本及机器 CSV；
3）write_offline_reports 写报告集，write_manifest 写输入输出哈希清单。
"""

from __future__ import annotations

import csv
import hashlib
import json
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from agentic_rag.evaluation.offline_record import OfflineEvaluationRecord
from agentic_rag.execution.record import CanonicalExecutionRecord


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _number(value: Any) -> float | None:
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _display(value: Any) -> str:
    if value in (None, ""):
        return "not_observed"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return "；".join(_display(item) for item in value) if value else "none"
    return str(value).replace("|", "\\|").replace("\n", " ")


def _stage(record: OfflineEvaluationRecord, name: str) -> dict[str, Any]:
    for stage in record.stages:
        if stage.name == name:
            return stage.to_dict()
    return {}


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _case_rows(records: Sequence[OfflineEvaluationRecord]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        rows.append(
            {
                "qid": record.identity.get("qid"),
                "source_profile": record.source.get("source_profile"),
                "source_cer_sha256": record.source.get("source_cer_sha256"),
                "answer_sha256": record.source.get("answer_sha256"),
                "status": record.outcome.get("status"),
                "actual_route": record.input_refs.get("actual_route"),
                "classifier_question_type": record.outcome.get("classifier_question_type"),
                "classifier_answerability": record.outcome.get("classifier_answerability"),
                "classifier_route_candidate": record.outcome.get("classifier_route_candidate"),
                "classifier_confidence": record.outcome.get("classifier_confidence"),
                "sufficiency_raw_verdict": record.outcome.get("sufficiency_raw_verdict"),
                "sufficiency_control_verdict": record.outcome.get("sufficiency_control_verdict"),
                "sufficiency_confidence": record.outcome.get("sufficiency_confidence"),
                "citation_support_label": record.outcome.get("citation_support_label"),
                "unsupported_claim_count": record.outcome.get("unsupported_claim_count"),
                "conflict_triggered": record.outcome.get("conflict_triggered"),
                "conflict_count": record.outcome.get("conflict_count"),
                "uncertainty_level": record.outcome.get("uncertainty_level"),
                "offline_total_ms": record.timing.get("offline_total_ms"),
                "model_call_count": record.usage.get("model_call_count"),
                "total_tokens": record.usage.get("total_tokens"),
                "total_tokens_observed_sum": record.usage.get("total_tokens_observed_sum"),
                "total_tokens_unknown_call_count": record.usage.get("total_tokens_unknown_call_count"),
                "reasoning_tokens": record.usage.get("reasoning_tokens"),
                "reasoning_tokens_observed_sum": record.usage.get("reasoning_tokens_observed_sum"),
                "reasoning_tokens_unknown_call_count": record.usage.get("reasoning_tokens_unknown_call_count"),
                "cached_tokens": record.usage.get("cached_tokens"),
                "cached_tokens_observed_sum": record.usage.get("cached_tokens_observed_sum"),
                "cached_tokens_unknown_call_count": record.usage.get("cached_tokens_unknown_call_count"),
                "estimated_cost_usd": record.usage.get("estimated_cost_usd"),
                "estimated_cost_usd_observed_sum": record.usage.get("estimated_cost_usd_observed_sum"),
                "cost_observation": record.usage.get("cost_observation"),
            }
        )
    return rows


def _stage_rows(records: Sequence[OfflineEvaluationRecord]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        for stage in record.stages:
            rows.append(
                {
                    "qid": record.identity.get("qid"),
                    "stage": stage.name,
                    "status": stage.status,
                    "mode": stage.mode,
                    "duration_ms": stage.duration_ms,
                    "model_call_count": len(stage.model_calls),
                    "error_type": _dict(stage.error).get("error_type"),
                }
            )
    return rows


def _call_rows(records: Sequence[OfflineEvaluationRecord]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        for call in record.model_calls:
            rows.append({"category": "offline_dfull", **dict(call)})
    return rows


def _aggregate_usage(records: Sequence[OfflineEvaluationRecord]) -> dict[str, Any]:
    calls = sum(len(record.model_calls) for record in records)
    token_values = [
        int(record.usage["total_tokens"])
        for record in records
        if record.usage.get("total_tokens") not in (None, "")
    ]
    cost_values = [
        float(record.usage["estimated_cost_usd"])
        for record in records
        if record.usage.get("estimated_cost_usd") not in (None, "")
    ]
    unknown_tokens = sum(
        bool(record.model_calls) and record.usage.get("total_tokens") in (None, "")
        for record in records
    )
    unknown_costs = sum(
        bool(record.model_calls) and record.usage.get("estimated_cost_usd") in (None, "")
        for record in records
    )
    return {
        "model_calls": calls,
        "total_tokens": sum(token_values) if not unknown_tokens else None,
        "total_tokens_observed_sum": sum(token_values),
        "unknown_token_record_count": unknown_tokens,
        "estimated_cost_usd": sum(cost_values) if not unknown_costs else None,
        "estimated_cost_usd_observed_sum": sum(cost_values),
        "unknown_cost_record_count": unknown_costs,
    }


def _format_ms(value: Any) -> str:
    number = _number(value)
    return "not_observed" if number is None else f"{number:,.3f}"


def _format_score(value: Any) -> str:
    number = _number(value)
    return "not_observed" if number is None else f"{number:.4f}"


def _format_cost(value: Any) -> str:
    number = _number(value)
    if number is None:
        return "not_observed"
    if number != 0.0 and abs(number) < 0.000001:
        return f"{number:.9f}"
    return f"{number:.6f}"


def _format_int(value: Any) -> str:
    if value in (None, "") or isinstance(value, bool):
        return "not_observed"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return _display(value)


def _count_text(counter: Counter[str]) -> str:
    return "；".join(f"{key}={value}" for key, value in sorted(counter.items())) or "none"


QUESTION_TYPE_DESCRIPTIONS = {
    "NARROW_FACT": "单一事实点，通常适合直接回答",
    "EXPLICIT_COMPARE": "明确比较两个或多个对象，通常倾向拆解",
    "IMPLICIT_COMPARE": "问题隐含对照关系，通常倾向拆解",
    "OPEN_MULTI": "需要多个要点、原因、风险或场景",
    "SUMMARY": "总结或整体说明",
    "PROCEDURE": "操作、排查、配置或流程型问题",
}

ANSWERABILITY_DESCRIPTIONS = {
    "IN_SCOPE": "问题范围明确，可在当前知识范围内回答",
    "OOD_CANDIDATE": "可能超出当前知识范围或涉及未公开信息",
    "NEEDS_CLARIFICATION": "问题缺少必要定义、对象或约束，需要澄清",
    "UNKNOWN": "可答性边界未稳定判断",
}

CONFIDENCE_DESCRIPTIONS = {
    "high": "分类器自报高置信；不是概率值",
    "medium": "分类器自报中等置信；建议结合 reason 查看",
    "low": "分类器自报低置信；应重点复核",
}

ROUTE_CANDIDATE_DESCRIPTIONS = {
    "DIRECT": "候选为直接处理",
    "DECOMPOSE": "候选为拆解问题后处理",
    "OPEN_MULTI": "开放多点回答候选；不是实际执行 path",
    "NEEDS_CLARIFICATION": "建议先澄清问题",
    "REJECT_CANDIDATE": "存在拒答候选；最终仍由后续证据与控制逻辑决定",
}

UNCERTAINTY_DESCRIPTIONS = {
    "high": "不确定性/风险高",
    "medium": "不确定性/风险中等",
    "low": "不确定性/风险低",
}


def _records_profile(records: Sequence[OfflineEvaluationRecord]) -> str:
    profiles = {
        str(record.source.get("source_profile") or "").strip()
        for record in records
        if str(record.source.get("source_profile") or "").strip()
    }
    if len(profiles) == 1:
        return next(iter(profiles))
    return "mixed" if profiles else "unknown"


def _profile_slug(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in str(value or "unknown"))
    return cleaned.strip("-") or "unknown"


def _qid_list(rows: Sequence[Mapping[str, Any]], predicate) -> list[str]:
    return [str(row.get("qid")) for row in rows if predicate(row)]


def _qids_text(qids: Sequence[str]) -> str:
    return "、".join(str(qid) for qid in qids) if qids else "无"


def _distribution_rows(
    rows: Sequence[Mapping[str, Any]],
    key: str,
) -> list[tuple[str, int, list[str]]]:
    grouped: dict[str, list[str]] = {}
    for row in rows:
        value = str(row.get(key) or "not_observed")
        grouped.setdefault(value, []).append(str(row.get("qid") or ""))
    return [(value, len(qids), qids) for value, qids in sorted(grouped.items())]


def _source_by_qid(
    source_records: Sequence[CanonicalExecutionRecord] | None,
) -> dict[str, CanonicalExecutionRecord]:
    if not source_records:
        return {}
    return {
        str(record.identity.get("qid") or ""): record
        for record in source_records
        if str(record.identity.get("qid") or "")
    }


def _actual_citations(source: CanonicalExecutionRecord | None) -> list[dict[str, Any]]:
    if source is None:
        return []
    prompt_by_chunk: dict[str, dict[str, Any]] = {}
    for item in list(source.prompt.get("visible_evidence") or []):
        if not isinstance(item, Mapping):
            continue
        row = dict(item)
        chunk_id = str(row.get("chunk_id") or "")
        if chunk_id:
            prompt_by_chunk[chunk_id] = row
    out: list[dict[str, Any]] = []
    for citation in list(source.outcome.get("citations") or []):
        if not isinstance(citation, Mapping):
            continue
        row = dict(citation)
        chunk_id = str(row.get("chunk_id") or "")
        prompt_row = prompt_by_chunk.get(chunk_id, {})
        out.append(
            {
                "evidence_id": prompt_row.get("marker") or prompt_row.get("evidence_id") or "not_observed",
                "source_id": row.get("source_id") or prompt_row.get("source_id"),
                "chunk_id": chunk_id,
                "retrieval_score": row.get("score"),
            }
        )
    return out


def _sum_known(values: Sequence[Any]) -> float | None:
    parsed = [_number(value) for value in values]
    if any(value is None for value in parsed):
        return None
    return sum(value for value in parsed if value is not None)


def _sufficiency_observation(source: CanonicalExecutionRecord | None) -> dict[str, Any]:
    if source is None:
        return {
            "mode": "not_observed",
            "first_verdict": None,
            "second_verdict": None,
            "first_ms": None,
            "second_ms": None,
            "judge_ms": None,
            "judge_call_count": 0,
            "prompt_tokens": None,
            "completion_tokens": None,
            "reasoning_tokens": None,
            "cached_tokens": None,
            "total_tokens": None,
            "estimated_cost_usd": None,
        }
    first_contract = _dict(source.sufficiency.get("first_contract"))
    second_contract = _dict(source.sufficiency.get("second_contract"))
    mode = str((second_contract or first_contract).get("mode") or "not_observed")
    calls = [
        dict(call)
        for call in list(source.model_calls or [])
        if isinstance(call, Mapping) and str(call.get("role") or "") == "sufficiency_judge"
    ]
    return {
        "mode": mode,
        "first_verdict": source.sufficiency.get("first"),
        "second_verdict": source.sufficiency.get("second"),
        "first_ms": source.timing.get("first_sufficiency_ms"),
        "second_ms": source.timing.get("second_sufficiency_ms"),
        "judge_ms": _sum_known(
            [source.timing.get("first_sufficiency_ms"), source.timing.get("second_sufficiency_ms")]
        ),
        "judge_call_count": len(calls),
        "prompt_tokens": _sum_known([call.get("prompt_tokens") for call in calls]),
        "completion_tokens": _sum_known([call.get("completion_tokens") for call in calls]),
        "reasoning_tokens": _sum_known([call.get("reasoning_tokens") for call in calls]),
        "cached_tokens": _sum_known([call.get("cached_tokens") for call in calls]),
        "total_tokens": _sum_known([call.get("total_tokens") for call in calls]),
        "estimated_cost_usd": _sum_known([call.get("estimated_cost_usd") for call in calls]),
    }


def _trigger_reason_text(value: Any) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "not_observed"
    if raw == "sufficiency_verdict_conflicted":
        return "主链 sufficiency 判为 CONFLICTED，触发规则冲突扫描"
    if raw == "distinct_sources_lt_2":
        return "证据包少于 2 个不同来源，不触发规则冲突扫描"
    if raw.startswith("question_type_") and raw.endswith("_with_multi_source"):
        qt = raw[len("question_type_") : -len("_with_multi_source")]
        return f"{qt} 多来源问题，触发规则冲突扫描"
    if raw.startswith("question_type_") and raw.endswith("_not_triggered"):
        qt = raw[len("question_type_") : -len("_not_triggered")]
        return f"{qt} 不在规则触发类型中，不执行冲突扫描"
    return raw


def _summary_markdown(records: Sequence[OfflineEvaluationRecord]) -> str:
    case_rows = _case_rows(records)
    profile = _records_profile(records)
    classifier_modes = Counter(
        str(_stage(record, "classifier").get("mode") or "not_observed") for record in records
    )
    sufficiency_modes = Counter(
        str(_stage(record, "structured_sufficiency").get("mode") or "not_observed")
        for record in records
    )
    raw_sufficiency_counts = Counter(
        str(row.get("sufficiency_raw_verdict") or "not_observed") for row in case_rows
    )
    citation_counts = Counter(
        str(row.get("citation_support_label") or "not_observed") for row in case_rows
    )
    uncertainty_counts = Counter(
        str(row.get("uncertainty_level") or "not_observed") for row in case_rows
    )
    total_ms = sum(_number(row.get("offline_total_ms")) or 0.0 for row in case_rows)
    usage = _aggregate_usage(records)

    answerability_attention = _qid_list(
        case_rows, lambda row: str(row.get("classifier_answerability") or "") != "IN_SCOPE"
    )
    confidence_attention = _qid_list(
        case_rows, lambda row: str(row.get("classifier_confidence") or "") in {"medium", "low"}
    )
    route_attention = _qid_list(
        case_rows,
        lambda row: str(row.get("classifier_route_candidate") or "") in {"DIRECT", "DECOMPOSE"}
        and str(row.get("classifier_route_candidate") or "") != str(row.get("actual_route") or ""),
    )
    sufficiency_attention = _qid_list(
        case_rows, lambda row: str(row.get("sufficiency_raw_verdict") or "") != "SUFFICIENT"
    )
    citation_severe = _qid_list(
        case_rows,
        lambda row: str(row.get("citation_support_label") or "") in {"unsupported", "no_evidence"},
    )
    unsupported_claims = _qid_list(
        case_rows, lambda row: int(row.get("unsupported_claim_count") or 0) > 0
    )
    conflicts = _qid_list(case_rows, lambda row: int(row.get("conflict_count") or 0) > 0)
    uncertainty_high = _qid_list(
        case_rows, lambda row: str(row.get("uncertainty_level") or "") == "high"
    )

    lines = [
        f"# D-full {profile} 离线评测总览",
        "",
        "> 输入为冻结 CER。Classifier 为本轮 D-full 的 LLM 分类；Sufficiency 读取主链既有判断；Citation Support、Conflict 与 Uncertainty 为后置规则诊断。",
        "",
        "## 五类信号怎么读",
        "",
        "| 模块 | 主要职责 | 方法 | 关键结果 |",
        "| :-- | :-- | :-- | :-- |",
        "| Classifier | 判断问题类型、可答性状态与候选路线 | LLM | question_type / answerability / route_candidate / confidence / reason |",
        f"| Sufficiency Judge | 判断当前证据是否足够回答 | 主链 LLM 结果投影 | {_display(_count_text(sufficiency_modes))}；verdict / confidence / missing_evidence 等 |",
        "| Citation Support | 检查答案 claims 是否被**最终实际引用证据**支撑 | 本地规则 | supported / partial / unsupported；claim-level best_score |",
        "| Conflict | 对多来源 EvidencePacket 做规则型疑似冲突扫描 | 本地规则 | conflict_count / conflict_type |",
        "| Uncertainty | 汇总 sufficiency、citation、conflict 等信号形成回答风险等级 | 本地规则聚合 | high / medium / low；**high 表示不确定性/风险高** |",
        "",
        "## 批次摘要",
        "",
        "| field | value |",
        "| :-- | :-- |",
        f"| source_profile | {_display(profile)} |",
        f"| 评测题数 | {len(records)} |",
        f"| classifier.mode | {_display(_count_text(classifier_modes))} |",
        f"| sufficiency.mode | {_display(_count_text(sufficiency_modes))} |",
        f"| sufficiency_raw_verdict | {_display(_count_text(raw_sufficiency_counts))} |",
        f"| citation_support_label | {_display(_count_text(citation_counts))} |",
        f"| uncertainty_level | {_display(_count_text(uncertainty_counts))} |",
        f"| offline_total_ms | {_format_ms(total_ms)} |",
        f"| model_call_count | {_format_int(usage['model_calls'])} |",
        f"| total_tokens | {_format_int(usage['total_tokens'])} |",
        f"| estimated_cost_usd | {_format_cost(usage['estimated_cost_usd'])} |",
        "",
        "## 重点题索引",
        "",
        "| 观察维度 | 题数 | qids |",
        "| :-- | --: | :-- |",
        f"| answerability 非 IN_SCOPE | {len(answerability_attention)} | {_qids_text(answerability_attention)} |",
        f"| classifier confidence 为 medium / low | {len(confidence_attention)} | {_qids_text(confidence_attention)} |",
        f"| route_candidate 与 actual_route 明确不一致（仅 DIRECT / DECOMPOSE） | {len(route_attention)} | {_qids_text(route_attention)} |",
        f"| sufficiency 非 SUFFICIENT | {len(sufficiency_attention)} | {_qids_text(sufficiency_attention)} |",
        f"| citation_support 为 unsupported / no_evidence | {len(citation_severe)} | {_qids_text(citation_severe)} |",
        f"| unsupported_claim_count > 0 | {len(unsupported_claims)} | {_qids_text(unsupported_claims)} |",
        f"| conflict_count > 0 | {len(conflicts)} | {_qids_text(conflicts)} |",
        f"| uncertainty_level = high | {len(uncertainty_high)} | {_qids_text(uncertainty_high)} |",
        "",
        "## Classifier 分类汇总",
        "",
        "### question_type",
        "",
        "| question_type | 含义 | count | qids |",
        "| :-- | :-- | --: | :-- |",
    ]
    for value, count, qids in _distribution_rows(case_rows, "classifier_question_type"):
        lines.append(
            f"| {_display(value)} | {_display(QUESTION_TYPE_DESCRIPTIONS.get(value, ''))} | {count} | {_qids_text(qids)} |"
        )

    lines.extend(
        [
            "",
            "### answerability",
            "",
            "| answerability | 含义 | count | qids |",
            "| :-- | :-- | --: | :-- |",
        ]
    )
    for value, count, qids in _distribution_rows(case_rows, "classifier_answerability"):
        lines.append(
            f"| {_display(value)} | {_display(ANSWERABILITY_DESCRIPTIONS.get(value, ''))} | {count} | {_qids_text(qids)} |"
        )

    lines.extend(
        [
            "",
            "### route_candidate",
            "",
            "> route_candidate 是 classifier 派生的候选处理方式，不等同于主链实际 `actual_route`。",
            "",
            "| route_candidate | 含义 | count | qids |",
            "| :-- | :-- | --: | :-- |",
        ]
    )
    for value, count, qids in _distribution_rows(case_rows, "classifier_route_candidate"):
        lines.append(
            f"| {_display(value)} | {_display(ROUTE_CANDIDATE_DESCRIPTIONS.get(value, ''))} | {count} | {_qids_text(qids)} |"
        )

    lines.extend(
        [
            "",
            "### confidence",
            "",
            "> classifier confidence 是模型自报分类置信等级，不是校准后的概率。",
            "",
            "| confidence | 含义 | count | qids |",
            "| :-- | :-- | --: | :-- |",
        ]
    )
    for value, count, qids in _distribution_rows(case_rows, "classifier_confidence"):
        lines.append(
            f"| {_display(value)} | {_display(CONFIDENCE_DESCRIPTIONS.get(value, ''))} | {count} | {_qids_text(qids)} |"
        )

    lines.extend(
        [
            "",
            "## D-full 判断结果分类",
            "",
            "| signal | value | count | qids |",
            "| :-- | :-- | --: | :-- |",
        ]
    )
    for key, label in (
        ("sufficiency_raw_verdict", "sufficiency_raw_verdict"),
        ("citation_support_label", "citation_support_label"),
        ("uncertainty_level", "uncertainty_level"),
    ):
        for value, count, qids in _distribution_rows(case_rows, key):
            lines.append(f"| {label} | {_display(value)} | {count} | {_qids_text(qids)} |")
    conflict_zero = [str(row.get("qid")) for row in case_rows if int(row.get("conflict_count") or 0) == 0]
    conflict_nonzero = [str(row.get("qid")) for row in case_rows if int(row.get("conflict_count") or 0) > 0]
    lines.append(f"| conflict_count | 0 | {len(conflict_zero)} | {_qids_text(conflict_zero)} |")
    lines.append(f"| conflict_count | >0 | {len(conflict_nonzero)} | {_qids_text(conflict_nonzero)} |")

    lines.extend(
        [
            "",
            "## 分类器逐题摘要",
            "",
            "| qid | actual_route | question_type | answerability | route_candidate | confidence |",
            "| :-- | :-- | :-- | :-- | :-- | :--: |",
        ]
    )
    for row in case_rows:
        lines.append(
            "| {qid} | {actual_route} | {question_type} | {answerability} | {route_candidate} | {confidence} |".format(
                qid=_display(row.get("qid")),
                actual_route=_display(row.get("actual_route")),
                question_type=_display(row.get("classifier_question_type")),
                answerability=_display(row.get("classifier_answerability")),
                route_candidate=_display(row.get("classifier_route_candidate")),
                confidence=_display(row.get("classifier_confidence")),
            )
        )

    lines.extend(
        [
            "",
            "## D-full 逐题判断信号",
            "",
            "| qid | raw_verdict | control_verdict | citation_support_label | unsupported_claim_count | conflict_count | uncertainty_level |",
            "| :-- | :-- | :-- | :-- | --: | --: | :-- |",
        ]
    )
    for row in case_rows:
        lines.append(
            "| {qid} | {raw_verdict} | {control_verdict} | {citation} | {unsupported} | {conflict_count} | {uncertainty} |".format(
                qid=_display(row.get("qid")),
                raw_verdict=_display(row.get("sufficiency_raw_verdict")),
                control_verdict=_display(row.get("sufficiency_control_verdict")),
                citation=_display(row.get("citation_support_label")),
                unsupported=_format_int(row.get("unsupported_claim_count")),
                conflict_count=_format_int(row.get("conflict_count")),
                uncertainty=_display(row.get("uncertainty_level")),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _field_bullets(lines: list[str], rows: Sequence[tuple[str, Any]]) -> None:
    for key, value in rows:
        lines.append(f"- {key}: {_display(value)}")
    lines.append("")


def _per_question_markdown(
    records: Sequence[OfflineEvaluationRecord],
    source_records: Sequence[CanonicalExecutionRecord] | None = None,
) -> str:
    profile = _records_profile(records)
    source_map = _source_by_qid(source_records)
    sufficiency_modes = Counter(
        str(_stage(record, "structured_sufficiency").get("mode") or "not_observed")
        for record in records
    )
    classifier_modes = Counter(
        str(_stage(record, "classifier").get("mode") or "not_observed") for record in records
    )
    lines = [
        f"# D-full {profile} 逐题评测报告",
        "",
        f"> source_profile: `{profile}`；classifier.mode: `{_count_text(classifier_modes)}`；sufficiency.mode: `{_count_text(sufficiency_modes)}`。批次共同配置不再逐题重复。",
        "",
        "## 阅读口径",
        "",
        "- **Classifier**：LLM 判断 question_type、answerability、route_candidate、confidence，并给出 reason；confidence 是模型自报等级，不是概率。",
        "- **Sufficiency Judge**：读取主链 CER 中已发生的证据充分性判断；baseline 通常为 binary，orchestrated 为 structured。",
        "- **Citation Support**：只使用最终 `Citations` 实际引用的证据作为评分池；答案正文中的 `[E1]` / `[E2]` 标记保留供人读核对，但不决定评分证据池。",
        "- **Citation Support 判定阈值**：`supported >= 0.22`；`partial = 0.12 ~ < 0.22`；`unsupported < 0.12`。best_score 是本地规则相似度诊断分，不等同于语义蕴含概率。",
        "- **Conflict**：对多来源 EvidencePacket 做规则型疑似冲突扫描；命中表示需要复核，不直接等同于事实冲突。",
        "- **Uncertainty**：由 sufficiency、citation、conflict 等信号派生；`high` 表示不确定性/风险高。",
        "",
    ]
    for record in records:
        qid = _display(record.identity.get("qid"))
        query = _display(record.query)
        source = source_map.get(str(record.identity.get("qid") or ""))
        classifier = _stage(record, "classifier")
        sufficiency = _stage(record, "structured_sufficiency")
        citation = _stage(record, "citation_support")
        conflict = _stage(record, "conflict")
        uncertainty = _stage(record, "uncertainty")
        c_out = _dict(classifier.get("output"))
        s_out = _dict(sufficiency.get("output"))
        cit_out = _dict(citation.get("output"))
        con_out = _dict(conflict.get("output"))
        unc_out = _dict(uncertainty.get("output"))

        lines.extend([f"## {qid} — {query}", "", "### 分类与回答边界", ""])
        _field_bullets(
            lines,
            [
                ("actual_route", record.input_refs.get("actual_route")),
                ("question_type", c_out.get("question_type")),
                ("answerability", c_out.get("answerability")),
                ("route_candidate", c_out.get("route_candidate")),
                ("confidence", c_out.get("confidence")),
                ("reason", c_out.get("reason")),
            ],
        )

        lines.extend(["### 证据充分性", ""])
        sufficiency_rows: list[tuple[str, Any]] = [
            ("raw_verdict", s_out.get("raw_verdict")),
            ("control_verdict", s_out.get("control_verdict")),
        ]
        if s_out.get("confidence") not in (None, ""):
            sufficiency_rows.append(("confidence", s_out.get("confidence")))
        if s_out.get("supporting_evidence_ids"):
            sufficiency_rows.append(("supporting_evidence_ids", s_out.get("supporting_evidence_ids")))
        if s_out.get("conflict_evidence_ids"):
            sufficiency_rows.append(("conflict_evidence_ids", s_out.get("conflict_evidence_ids")))
        if s_out.get("missing_evidence"):
            sufficiency_rows.append(("missing_evidence", s_out.get("missing_evidence")))
        if s_out.get("reason"):
            sufficiency_rows.append(("reason", s_out.get("reason")))
        _field_bullets(lines, sufficiency_rows)

        lines.extend(["### 引用证据支撑（规则）", ""])
        citation_rows: list[tuple[str, Any]] = [
            ("citation_support_label", cit_out.get("citation_support_label")),
            ("citation_count", cit_out.get("citation_count")),
            ("resolved_citation_count", cit_out.get("resolved_citation_count")),
            ("unresolved_citation_count", cit_out.get("unresolved_citation_count")),
            ("claim_count", cit_out.get("claim_count")),
            ("unsupported_claim_count", cit_out.get("unsupported_claim_count")),
        ]
        _field_bullets(lines, citation_rows)

        actual_citations = _actual_citations(source)
        if actual_citations:
            lines.extend(
                [
                    "#### 最终实际 Citations",
                    "",
                    "| evidence_id | source_id | chunk_id | retrieval_score |",
                    "| :-- | :-- | :-- | --: |",
                ]
            )
            for item in actual_citations:
                lines.append(
                    f"| {_display(item.get('evidence_id'))} | {_display(item.get('source_id'))} | "
                    f"{_display(item.get('chunk_id'))} | {_format_score(item.get('retrieval_score'))} |"
                )
            lines.append("")

        claims = [item for item in list(cit_out.get("claims") or []) if isinstance(item, Mapping)]
        if claims:
            lines.extend(
                [
                    "#### 引用 claim 明细",
                    "",
                    "> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。",
                    "",
                    "| # | label（支撑判定） | best_score | best_evidence_id | claim |",
                    "| --: | :-- | --: | :-- | :-- |",
                ]
            )
            for index, claim in enumerate(claims, start=1):
                lines.append(
                    f"| {index} | {_display(claim.get('label'))} | {_format_score(claim.get('best_score'))} | "
                    f"{_display(claim.get('best_evidence_id'))} | {_display(claim.get('claim'))} |"
                )
            lines.append("")

        lines.extend(["### 冲突检测（规则型疑似冲突）", ""])
        conflict_rows: list[tuple[str, Any]] = [
            ("triggered", con_out.get("triggered")),
            ("conflict_count", con_out.get("conflict_count")),
        ]
        reason = con_out.get("trigger_reason") or con_out.get("skipped_reason")
        if reason not in (None, ""):
            conflict_rows.append(("trigger_reason", _trigger_reason_text(reason)))
        _field_bullets(lines, conflict_rows)
        conflict_items = [item for item in list(con_out.get("conflicts") or []) if isinstance(item, Mapping)]
        if conflict_items:
            lines.extend(
                [
                    "#### 疑似冲突明细",
                    "",
                    "| # | conflict_type | evidence_a | evidence_b | uncertainty_level | claim_a | claim_b |",
                    "| --: | :-- | :-- | :-- | :-- | :-- | :-- |",
                ]
            )
            for index, item in enumerate(conflict_items, start=1):
                lines.append(
                    f"| {index} | {_display(item.get('conflict_type'))} | {_display(item.get('evidence_a'))} | "
                    f"{_display(item.get('evidence_b'))} | {_display(item.get('uncertainty_level'))} | "
                    f"{_display(item.get('claim_a'))} | {_display(item.get('claim_b'))} |"
                )
            lines.append("")

        lines.extend(["### 综合不确定性（派生信号）", ""])
        uncertainty_rows: list[tuple[str, Any]] = [
            ("level", unc_out.get("level")),
            ("level_meaning", UNCERTAINTY_DESCRIPTIONS.get(str(unc_out.get("level") or ""), "")),
            ("reasons", unc_out.get("reasons")),
        ]
        if unc_out.get("missing_info"):
            uncertainty_rows.append(("missing_info", unc_out.get("missing_info")))
        if unc_out.get("safe_answer_boundary"):
            uncertainty_rows.append(("safe_answer_boundary", unc_out.get("safe_answer_boundary")))
        _field_bullets(lines, uncertainty_rows)

        lines.extend(["### D-full 后置评测耗时与用量", ""])
        lines.extend(
            [
                f"- offline_total_ms: {_format_ms(record.timing.get('offline_total_ms'))}",
                f"- model_call_count: {_format_int(len(record.model_calls))}",
                f"- prompt_tokens: {_format_int(record.usage.get('prompt_tokens'))}",
                f"- completion_tokens: {_format_int(record.usage.get('completion_tokens'))}",
                f"- total_tokens: {_format_int(record.usage.get('total_tokens'))}",
                f"- estimated_cost_usd: {_format_cost(record.usage.get('estimated_cost_usd'))}",
                "",
            ]
        )

        lines.extend(
            [
                "### 追溯信息",
                "",
                f"- source_cer_sha256: `{record.source.get('source_cer_sha256')}`",
                f"- answer_sha256: `{record.source.get('answer_sha256')}`",
                "",
            ]
        )
    return "\n".join(lines)


def _timing_markdown(
    records: Sequence[OfflineEvaluationRecord],
    source_records: Sequence[CanonicalExecutionRecord] | None = None,
) -> str:
    rows = _case_rows(records)
    profile = _records_profile(records)
    source_map = _source_by_qid(source_records)
    durations = [value for row in rows if (value := _number(row.get("offline_total_ms"))) is not None]
    usage = _aggregate_usage(records)
    suff_rows: list[dict[str, Any]] = []
    for record in records:
        qid = str(record.identity.get("qid") or "")
        obs = _sufficiency_observation(source_map.get(qid))
        suff_rows.append({"qid": qid, **obs})
    observed_suff = [row for row in suff_rows if row.get("mode") != "not_observed"]
    judge_ms_values = [_number(row.get("judge_ms")) for row in observed_suff]
    judge_calls = sum(int(row.get("judge_call_count") or 0) for row in observed_suff)
    judge_tokens = _sum_known([row.get("total_tokens") for row in observed_suff]) if observed_suff else None
    judge_cost = _sum_known([row.get("estimated_cost_usd") for row in observed_suff]) if observed_suff else None
    second_round_count = sum(bool(row.get("second_verdict")) for row in observed_suff)

    lines = [
        f"# D-full {profile} Timing-Usage-Cost 明细",
        "",
        "> 本报告分开呈现 **D-full 后置评测开销** 与 **原主链 Sufficiency Judge 观测**。主链 Sufficiency Judge 已计入 online 主链成本，这里只引用展示，绝不重复计入 D-full 离线总成本。",
        "",
        "## D-full 后置评测批次摘要",
        "",
        "| field | value |",
        "| :-- | --: |",
        f"| source_profile | {_display(profile)} |",
        f"| 评测题数 | {len(records)} |",
        f"| offline_total_ms_sum | {_format_ms(sum(durations) if durations else 0.0)} |",
        f"| offline_total_ms_median | {_format_ms(statistics.median(durations) if durations else 0.0)} |",
        f"| offline_total_ms_max | {_format_ms(max(durations) if durations else 0.0)} |",
        f"| model_call_count | {_format_int(usage['model_calls'])} |",
        f"| total_tokens | {_format_int(usage['total_tokens'])} |",
        f"| estimated_cost_usd | {_format_cost(usage['estimated_cost_usd'])} |",
        "",
        "## D-full 后置阶段耗时",
        "",
        "> `structured_sufficiency_ms` 仅是从 CER 投影字段的本地耗时，不代表 Sufficiency Judge 模型耗时，因此从主阅读表移除。真实 Judge 耗时见后文“主链 Sufficiency Judge 观测”。",
        "",
        "| qid | classifier_ms | citation_support_ms | conflict_ms | uncertainty_ms | offline_total_ms |",
        "| :-- | --: | --: | --: | --: | --: |",
    ]
    for record in records:
        lines.append(
            f"| {_display(record.identity.get('qid'))} | {_format_ms(record.timing.get('classifier_ms'))} | "
            f"{_format_ms(record.timing.get('citation_support_ms'))} | {_format_ms(record.timing.get('conflict_ms'))} | "
            f"{_format_ms(record.timing.get('uncertainty_ms'))} | {_format_ms(record.timing.get('offline_total_ms'))} |"
        )

    lines.extend(
        [
            "",
            "## D-full Classifier Token 与成本",
            "",
            "| qid | model_call_count | prompt_tokens | completion_tokens | total_tokens | estimated_cost_usd |",
            "| :-- | --: | --: | --: | --: | --: |",
        ]
    )
    for record in records:
        lines.append(
            f"| {_display(record.identity.get('qid'))} | {_format_int(len(record.model_calls))} | "
            f"{_format_int(record.usage.get('prompt_tokens'))} | {_format_int(record.usage.get('completion_tokens'))} | "
            f"{_format_int(record.usage.get('total_tokens'))} | {_format_cost(record.usage.get('estimated_cost_usd'))} |"
        )

    lines.extend(
        [
            "",
            "## 主链 Sufficiency Judge 批次观测",
            "",
        ]
    )
    if observed_suff:
        mode_counts = Counter(str(row.get("mode") or "not_observed") for row in observed_suff)
        lines.extend(
            [
                "| field | value |",
                "| :-- | --: |",
                f"| sufficiency.mode | {_display(_count_text(mode_counts))} |",
                f"| judge_call_count | {_format_int(judge_calls)} |",
                f"| second_round_case_count | {_format_int(second_round_count)} |",
                f"| judge_ms_sum | {_format_ms(sum(value for value in judge_ms_values if value is not None))} |",
                f"| total_tokens | {_format_int(judge_tokens)} |",
                f"| estimated_cost_usd | {_format_cost(judge_cost)} |",
                "",
                "### 逐题 Verdict 与耗时",
                "",
                "| qid | mode | first_verdict | first_sufficiency_ms | second_verdict | second_sufficiency_ms | judge_ms_total |",
                "| :-- | :-- | :-- | --: | :-- | --: | --: |",
            ]
        )
        for row in suff_rows:
            lines.append(
                f"| {_display(row.get('qid'))} | {_display(row.get('mode'))} | {_display(row.get('first_verdict'))} | "
                f"{_format_ms(row.get('first_ms'))} | {_display(row.get('second_verdict'))} | "
                f"{_format_ms(row.get('second_ms'))} | {_format_ms(row.get('judge_ms'))} |"
            )
        lines.extend(
            [
                "",
                "### 逐题 Token 与成本",
                "",
                "| qid | judge_call_count | prompt_tokens | completion_tokens | total_tokens | estimated_cost_usd |",
                "| :-- | --: | --: | --: | --: | --: |",
            ]
        )
        for row in suff_rows:
            lines.append(
                f"| {_display(row.get('qid'))} | {_format_int(row.get('judge_call_count'))} | "
                f"{_format_int(row.get('prompt_tokens'))} | {_format_int(row.get('completion_tokens'))} | "
                f"{_format_int(row.get('total_tokens'))} | {_format_cost(row.get('estimated_cost_usd'))} |"
            )
    else:
        lines.extend(["> 未提供 source CER，无法读取主链 Sufficiency Judge 的真实耗时与 Token。", ""])

    if usage["unknown_token_record_count"] or usage["unknown_cost_record_count"]:
        lines.extend(
            [
                "",
                "## D-full 后置账观测完整性",
                "",
                f"- total_tokens_observed_sum: {_format_int(usage['total_tokens_observed_sum'])}",
                f"- unknown_token_record_count: {_format_int(usage['unknown_token_record_count'])}",
                f"- estimated_cost_usd_observed_sum: {_format_cost(usage['estimated_cost_usd_observed_sum'])}",
                f"- unknown_cost_record_count: {_format_int(usage['unknown_cost_record_count'])}",
            ]
        )
    lines.append("")
    return "\n".join(lines)


# 将离线 D-full 记录写成完整的人读与机读报告集。
def write_offline_reports(
    records: Iterable[OfflineEvaluationRecord],
    output_dir: str | Path,
    *,
    source_records: Iterable[CanonicalExecutionRecord] | None = None,
) -> dict[str, Path]:
    items = list(records)
    source_items = list(source_records or [])
    output = Path(output_dir)
    summaries = output / "summaries"
    tables = output / "tables"
    summaries.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    profile = _profile_slug(_records_profile(items))
    paths = {
        "summary": summaries / f"D-full-{profile}-离线评测总览.md",
        "per_question": summaries / f"D-full-{profile}-逐题评测报告.md",
        "timing_usage_cost": summaries / f"D-full-{profile}-Timing-Usage-Cost明细.md",
        "cases": tables / "offline_cases.csv",
        "stages": tables / "offline_stages.csv",
        "model_calls": tables / "model_calls.csv",
        "cost_ledger": tables / "cost_ledger.csv",
    }
    paths["summary"].write_text(_summary_markdown(items), encoding="utf-8")
    paths["per_question"].write_text(
        _per_question_markdown(items, source_items), encoding="utf-8"
    )
    paths["timing_usage_cost"].write_text(
        _timing_markdown(items, source_items), encoding="utf-8"
    )

    cases = _case_rows(items)
    stages = _stage_rows(items)
    calls = _call_rows(items)
    cost_rows = [
        {
            "category": "offline_dfull",
            "qid": record.identity.get("qid"),
            "model_call_count": len(record.model_calls),
            "total_tokens": record.usage.get("total_tokens"),
            "total_tokens_observed_sum": record.usage.get("total_tokens_observed_sum"),
            "total_tokens_unknown_call_count": record.usage.get("total_tokens_unknown_call_count"),
            "estimated_cost_usd": record.usage.get("estimated_cost_usd"),
            "estimated_cost_usd_observed_sum": record.usage.get("estimated_cost_usd_observed_sum"),
            "cost_observation": record.usage.get("cost_observation"),
        }
        for record in items
    ]
    _write_csv(paths["cases"], cases, list(cases[0]) if cases else ["qid"])
    _write_csv(paths["stages"], stages, list(stages[0]) if stages else ["qid", "stage"])
    call_fields = sorted({key for row in calls for key in row}) or ["category", "qid", "call_id"]
    _write_csv(paths["model_calls"], calls, call_fields)
    _write_csv(paths["cost_ledger"], cost_rows, list(cost_rows[0]) if cost_rows else ["qid"])
    return paths

def write_manifest(output_dir: str | Path, *, metadata: Mapping[str, Any]) -> Path:
    output = Path(output_dir)
    files: dict[str, Any] = {}
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        payload = path.read_bytes()
        files[path.relative_to(output).as_posix()] = {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    manifest = {
        "schema_version": "1.0.0",
        "metadata": dict(metadata),
        "files": files,
    }
    path = output / "manifest.json"
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


__all__ = ["write_manifest", "write_offline_reports"]
