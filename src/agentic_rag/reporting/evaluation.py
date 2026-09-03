"""
程序作用：
把规范执行记录投影成通用 Markdown 与 CSV 评估报告，所有统计尽量直接读取冻结执行事实。

整体结构：
1）基础辅助函数统一兼容当前与历史 CER、显示格式和逐题字段；
2）分别生成总览、逐题答案、检索信号、来源分布、工作流、耗时用量成本等章节；
3）build_evaluation_reports 一次写出完整报告集及机器表格。
"""

from __future__ import annotations

import csv
import json
import math
import re
import statistics
from datetime import datetime
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from agentic_rag.execution.legacy_import import NOT_APPLICABLE, NOT_OBSERVED
from agentic_rag.execution.record import CanonicalExecutionRecord


def _suite_label(value: Any) -> str:
    """生成简短、可读且适合写入 Markdown 的评估集名称。"""
    label = str(value or "Evaluation").strip()
    return label or "Evaluation"


def _suite_prefix(value: Any) -> str:
    """生成文件系统安全的报告前缀，不改动数据集原始内容。"""
    label = _suite_label(value)
    cleaned = re.sub(r"[^0-9A-Za-z._+\-\u4e00-\u9fff]+", "-", label).strip("-._")
    return cleaned or "Evaluation"


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value in (None, "", NOT_OBSERVED, NOT_APPLICABLE):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _display(value: Any) -> str:
    if value is None or value == "":
        return NOT_OBSERVED
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, (list, tuple)):
        return ", ".join(_display(item) for item in value) if value else NOT_APPLICABLE
    return str(value).replace("|", "\\|").replace("\n", " ")


def _percentile(values: Sequence[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * p
    low = math.floor(position)
    high = math.ceil(position)
    if low == high:
        return ordered[low]
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _report_record(record: CanonicalExecutionRecord) -> CanonicalExecutionRecord:
    """为当前和历史 CER 生成仅供报告使用的兼容视图。"""
    clone = CanonicalExecutionRecord.from_dict(record.to_dict())
    dimensions = _dict(clone.evaluation.get("dimensions"))

    if dimensions:
        behavior = _dict(dimensions.get("behavior"))
        route_dimension = _dict(dimensions.get("route_invariants"))
        clone.evaluation.setdefault("expected_behavior", behavior.get("expected", NOT_OBSERVED))
        clone.evaluation.setdefault("expected_path", route_dimension.get("expected_path", NOT_APPLICABLE))
        if behavior.get("status") in {"pass", "fail"}:
            clone.evaluation.setdefault("behavior_pass", behavior.get("status") == "pass")
        if route_dimension.get("status") in {"pass", "fail"}:
            clone.evaluation.setdefault("path_pass", route_dimension.get("status") == "pass")
        clone.evaluation.setdefault("final_pass", clone.evaluation.get("hard_gate_pass", NOT_OBSERVED))
        clone.evaluation.setdefault("drift", clone.evaluation.get("blocking_dimensions", NOT_OBSERVED))

    clone.route.setdefault("direct_query", clone.query)
    if "rewrite_query" not in clone.route:
        clone.route["rewrite_query"] = clone.route.get("rewritten_query")
    clone.outcome.setdefault("refused", clone.outcome.get("status") == "REFUSED")

    events = [_dict(item) for item in _list(clone.retrieval.get("events"))]
    if events:
        rounds: list[dict[str, Any]] = []
        round_ids: set[str] = set()
        for raw in events:
            item = dict(raw)
            round_id = item.get("round_id")
            if round_id not in (None, ""):
                round_ids.add(str(round_id))
            query_role = item.get("query_role", NOT_OBSERVED)
            candidates: list[dict[str, Any]] = []
            for raw_candidate in _list(item.get("candidates")):
                candidate = _dict(raw_candidate)
                candidate.setdefault("query_role", query_role)
                score_type = str(candidate.get("score_type") or "vector_similarity")
                score = candidate.get("score", NOT_OBSERVED)
                if score_type == "vector_similarity":
                    candidate.setdefault("vector_score", score)
                elif score_type == "rrf":
                    candidate.setdefault("rrf_score", score)
                elif score_type == "bm25":
                    candidate.setdefault("bm25_score", score)
                candidate.setdefault("rerank_score", NOT_OBSERVED)
                candidates.append(candidate)
            item["candidates"] = candidates
            item.setdefault("route", clone.route.get("actual_route", NOT_OBSERVED))
            item.setdefault("hit_count", len(candidates))
            item.setdefault("observation_level", "current_per_query_topk")
            item.setdefault("unobserved_fields", [])
            rounds.append(item)
        clone.retrieval["rounds"] = rounds
        clone.retrieval["round_count"] = len(round_ids) if round_ids else 1
        clone.retrieval["retrieved_count"] = len(_list(clone.evidence.get("retrieved")))
        clone.retrieval.setdefault("final_pool", _list(clone.evidence.get("selected")))
        clone.retrieval["observation_limit"] = "current live CER records per-query TopK events"
    else:
        clone.retrieval.setdefault("round_count", len(_list(clone.retrieval.get("rounds"))))

    selected_by_chunk = {
        str(item.get("chunk_id")): item
        for item in (_dict(raw) for raw in _list(clone.evidence.get("selected")))
        if item.get("chunk_id")
    }
    prompt_items: list[dict[str, Any]] = []
    for raw in _list(clone.prompt.get("visible_evidence")):
        item = _dict(raw)
        selected = selected_by_chunk.get(str(item.get("chunk_id")), {})
        score_type = str(selected.get("score_type") or "vector_similarity")
        score = selected.get("score", NOT_OBSERVED)
        item.setdefault("score_type", score_type)
        if score_type == "vector_similarity":
            item.setdefault("vector_score", selected.get("vector_score", score))
        elif score_type == "rrf":
            item.setdefault("rrf_score", selected.get("rrf_score", score))
        elif score_type == "bm25":
            item.setdefault("bm25_score", selected.get("bm25_score", score))
        item.setdefault("rerank_score", selected.get("rerank_score", NOT_OBSERVED))
        item.setdefault("text_preview", str(item.get("text") or "")[:240])
        prompt_items.append(item)
    clone.prompt["visible_evidence"] = prompt_items

    clone.sufficiency.setdefault("first_ms", clone.timing.get("first_sufficiency_ms", NOT_OBSERVED))
    clone.sufficiency.setdefault("second_ms", clone.timing.get("second_sufficiency_ms", NOT_OBSERVED))
    clone.sufficiency.setdefault("judge_error", NOT_OBSERVED)
    clone.timing.setdefault("actual_total_ms", clone.timing.get("service_total_ms", NOT_OBSERVED))
    clone.timing.setdefault("workflow_total_ms", clone.timing.get("engine_ms", NOT_OBSERVED))

    if "per_query_contributions" not in clone.merge:
        clone.merge["per_query_contributions"] = [
            {"chunk_id": item.get("chunk_id"), "contributions": _list(item.get("contributions"))}
            for item in (_dict(raw) for raw in _list(clone.merge.get("final_order")))
            if item.get("chunk_id")
        ] or NOT_OBSERVED
    return clone


def _record_row(record: CanonicalExecutionRecord) -> dict[str, Any]:
    identity = record.identity
    evaluation = record.evaluation
    outcome = record.outcome
    route = record.route
    timing = record.timing
    usage = record.usage
    rounds = _list(record.retrieval.get("rounds"))
    prompt_items = _list(record.prompt.get("visible_evidence"))
    citations = _list(outcome.get("citations"))
    return {
        "qid": identity.get("qid"),
        "question": record.query,
        "expected_behavior": evaluation.get("expected_behavior"),
        "expected_path": evaluation.get("expected_path"),
        "question_type": route.get("question_type"),
        "route": route.get("actual_route"),
        "final_status": outcome.get("status"),
        "refused": outcome.get("refused"),
        "retrieval_rounds": record.retrieval.get("round_count", len(rounds)),
        "rerank_triggered": record.rerank.get("triggered"),
        "retrieved_count": record.retrieval.get("retrieved_count", len(_list(record.retrieval.get("final_pool")))),
        "prompt_chunk_count": len(prompt_items),
        "first_sufficiency": record.sufficiency.get("first"),
        "second_sufficiency": record.sufficiency.get("second"),
        "citation_count": len(citations),
        "conflict_count": NOT_OBSERVED,
        "uncertainty_level": NOT_OBSERVED,
        "actual_total_ms": timing.get("actual_total_ms"),
        "model_call_count": len(record.model_calls),
        "total_tokens": usage.get("total_tokens"),
        "estimated_cost_usd": usage.get("estimated_cost_usd"),
        "behavior_pass": evaluation.get("behavior_pass"),
        "path_pass": evaluation.get("path_pass"),
        "final_pass": evaluation.get("final_pass"),
        "drift": evaluation.get("drift"),
        "error": record.errors[0].get("error_type") if record.errors else NOT_APPLICABLE,
    }


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fields), extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, NOT_OBSERVED) for field in fields})


def _summary_markdown(
    records: Sequence[CanonicalExecutionRecord],
    rows: Sequence[dict[str, Any]],
    *,
    suite_label: str,
) -> str:
    status_counts = Counter(str(row["final_status"]) for row in rows)
    route_counts = Counter(str(row["route"]) for row in rows)
    behavior_observed = [row for row in rows if isinstance(row.get("behavior_pass"), bool)]
    behavior_passed = sum(bool(row["behavior_pass"]) for row in behavior_observed)
    path_observed = [row for row in rows if isinstance(row.get("path_pass"), bool)]
    path_passed = sum(bool(row["path_pass"]) for row in path_observed)
    historical_only = bool(records) and all(
        bool(record.provenance.get("historical_import")) for record in records
    )
    source_note = (
        "> 来源：Phase-E 冻结历史 JSONL → loss-aware legacy CER importer。"
        if historical_only
        else "> 来源：当前 live CanonicalExecutionRecord（CER）确定性投影。"
    )
    lines = [
        f"# {suite_label} Final Regression Summary",
        "",
        source_note,
        "> `not_observed` 表示 CER 没有记录该事实；本报告不会从最终结果反推中间过程。",
        "",
        "## Batch",
        "",
        f"- cases: {len(records)}",
        f"- status: {_display([f'{k}={v}' for k, v in sorted(status_counts.items())])}",
        f"- route: {_display([f'{k}={v}' for k, v in sorted(route_counts.items())])}",
        f"- behavior contract: {behavior_passed}/{len(behavior_observed)}",
        f"- expected-path contract: {path_passed}/{len(path_observed)}",
        "- final column uses the current evaluation hard-gate when available; independent answer quality is still evaluated separately.",
        "",
        "## Per-question overview",
        "",
        "| qid | question | expected | route/status | rounds/rerank | retrieved→prompt | sufficiency | citations | ms | calls/tokens/cost | behavior/path/final | error |",
        "| :-- | :-- | :-- | :-- | :-- | :-- | :-- | --: | --: | :-- | :-- | :-- |",
    ]
    for row in rows:
        lines.append(
            "| {qid} | {question} | {expected_behavior}/{expected_path} | {route}/{final_status} | "
            "{retrieval_rounds}/{rerank_triggered} | {retrieved_count}→{prompt_chunk_count} | "
            "{first_sufficiency}/{second_sufficiency} | {citation_count} | {actual_total_ms} | "
            "{model_call_count}/{total_tokens}/{estimated_cost_usd} | "
            "{behavior_pass}/{path_pass}/{final_pass} | {error} |".format(
                **{key: _display(value) for key, value in row.items()}
            )
        )
    if historical_only:
        lines.extend(
            [
                "",
                "## Historical observation limits",
                "",
                "- Phase-E artifact contains the final returned Top5, but not DIRECT/subquery individual Top5 candidate lists.",
                "- It contains prompt-visible chunks, but not a versioned EvidenceSnapshot ID or verified citation result.",
                "- Behavior and expected-path contracts can be recomputed; answer quality and final pass cannot be inferred without an evaluator.",
                "- Conflict and uncertainty are separate evaluation artifacts and are not joined by guesswork here.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## Current-run notes",
                "",
                "- DIRECT/DECOMPOSE/rewrite retrieval TopK comes from current CER retrieval events.",
                "- Online classifier fields remain not_observed/not_evaluated by design; classifier analysis is produced by offline replay.",
                "- Answer quality remains independent/manual or evaluator-derived and is not inferred here.",
                "",
            ]
        )
    return "\n".join(lines)


def _candidate_table(candidates: Sequence[Any]) -> list[str]:
    lines = [
        "| rank | query_role | chunk_id | source_id | offset | score_type | score | selected |",
        "| --: | :-- | :-- | :-- | :-- | :-- | --: | :-- |",
    ]
    if not candidates:
        lines.append("| — | not_observed | not_observed | not_observed | not_observed | not_observed | not_observed | false |")
        return lines
    for raw in candidates:
        item = _dict(raw)
        offset = f"{_display(item.get('offset_start', item.get('source_offset_start')))}-{_display(item.get('offset_end', item.get('source_offset_end')))}"
        lines.append(
            "| {rank} | {role} | {chunk} | {source} | {offset} | {score_type} | {score} | {selected} |".format(
                rank=_display(item.get("rank")),
                role=_display(item.get("query_role")),
                chunk=_display(item.get("chunk_id")),
                source=_display(item.get("source_id")),
                offset=offset,
                score_type=_display(item.get("score_type")),
                score=_display(item.get("score")),
                selected=_display(item.get("selected")),
            )
        )
    return lines


def _expected_evidence_flags(record: CanonicalExecutionRecord) -> tuple[list[str], bool, bool, str]:
    dimensions = _dict(record.evaluation.get("dimensions"))
    expected_dimension = _dict(dimensions.get("expected_evidence"))
    prompt_dimension = _dict(dimensions.get("prompt_evidence"))
    expected = [str(item) for item in _list(expected_dimension.get("expected"))]
    observed = {str(item) for item in _list(expected_dimension.get("observed"))}
    if expected:
        any_hit = any(item in observed for item in expected)
        full_hit = all(item in observed for item in expected)
    else:
        any_hit = False
        full_hit = True
    prompt_status = str(prompt_dimension.get("status") or NOT_OBSERVED)
    return expected, any_hit, full_hit, prompt_status


def _actual_behavior(record: CanonicalExecutionRecord) -> str:
    if record.outcome.get("refused") is True or record.outcome.get("status") == "REFUSED":
        return "reject"
    return "answer"


def _concise_agentic_steps(record: CanonicalExecutionRecord) -> list[str]:
    route = str(record.route.get("actual_route") or NOT_OBSERVED)
    steps = [f"route_first: {route}"]
    subqueries = [str(item) for item in _list(record.route.get("subqueries")) if str(item).strip()]
    if route == "DECOMPOSE" or subqueries:
        steps.append(f"decompose: {len(subqueries)} subqueries")
    first_count = sum(
        len(_list(_dict(event).get("candidates")))
        for event in _list(record.retrieval.get("rounds"))
        if _dict(event).get("round_id") == 1
    )
    if first_count:
        steps.append(f"first_retrieve: candidates={first_count}")
    first = record.sufficiency.get("first")
    if first not in (None, "", NOT_OBSERVED):
        steps.append(f"sufficiency_first: {first}")
    rewritten = record.route.get("rewrite_query") or record.route.get("rewritten_query")
    if rewritten:
        steps.append(f"rewrite_query: {rewritten}")
    second_count = sum(
        len(_list(_dict(event).get("candidates")))
        for event in _list(record.retrieval.get("rounds"))
        if _dict(event).get("round_id") == 2
    )
    if second_count:
        steps.append(f"second_retrieve: candidates={second_count}")
    second = record.sufficiency.get("second")
    if second not in (None, "", NOT_OBSERVED):
        steps.append(f"sufficiency_second: {second}")
    if record.outcome.get("refused") is True or record.outcome.get("status") == "REFUSED":
        steps.append(f"reject: {record.outcome.get('refusal_reason') or 'refused'}")
    else:
        steps.append("generate: answer")
    return steps


def _citation_lines(record: CanonicalExecutionRecord) -> list[str]:
    marker_by_chunk = {
        str(item.get("chunk_id")): str(item.get("marker"))
        for item in (_dict(raw) for raw in _list(record.evidence.get("prompt_visible")))
        if item.get("chunk_id") and item.get("marker")
    }
    citations = [_dict(raw) for raw in _list(record.outcome.get("citations"))]
    if not citations:
        return ["- not_applicable"]
    lines: list[str] = []
    for item in citations:
        chunk_id = str(item.get("chunk_id") or NOT_OBSERVED)
        marker = marker_by_chunk.get(chunk_id)
        prefix = f"{marker} | " if marker else ""
        lines.append(
            f"- {prefix}chunk_id={_display(chunk_id)} | "
            f"source_id={_display(item.get('source_id'))} | score={_display(item.get('score'))}"
        )
    return lines


def _per_question_markdown(
    records: Sequence[CanonicalExecutionRecord],
    *,
    suite_label: str,
) -> str:
    profile = _display(records[0].provenance.get("profile")) if records else NOT_OBSERVED
    build_id = _display(records[0].provenance.get("index_build_id")) if records else NOT_OBSERVED
    rerank_values = {bool(record.rerank.get("enabled")) for record in records}
    rerank_display = _display(next(iter(rerank_values))) if len(rerank_values) == 1 else "mixed"

    answered_count = sum(1 for record in records if _actual_behavior(record) == "answer")
    refused_count = len(records) - answered_count
    direct_count = sum(1 for record in records if record.route.get("actual_route") == "DIRECT")
    decompose_count = sum(1 for record in records if record.route.get("actual_route") == "DECOMPOSE")
    behavior_failed_cases: list[str] = []
    abnormal_refusal_cases: list[str] = []
    unexpected_answer_cases: list[str] = []
    prompt_status_counts = {"pass": 0, "fail": 0, "not_applicable": 0, "not_observed": 0}
    prompt_failed_cases: list[str] = []
    for record in records:
        qid = str(record.identity.get("qid") or NOT_OBSERVED)
        dimensions = _dict(record.evaluation.get("dimensions"))
        behavior_status = str(_dict(dimensions.get("behavior")).get("status") or NOT_OBSERVED)
        expected_behavior = str(record.evaluation.get("expected_behavior") or NOT_OBSERVED)
        actual_behavior = _actual_behavior(record)
        if behavior_status != "pass":
            behavior_failed_cases.append(qid)
        if expected_behavior == "answer" and actual_behavior == "reject":
            abnormal_refusal_cases.append(qid)
        if expected_behavior == "reject" and actual_behavior == "answer":
            unexpected_answer_cases.append(qid)
        _, _, _, prompt_status = _expected_evidence_flags(record)
        if prompt_status not in prompt_status_counts:
            prompt_status_counts[prompt_status] = 0
        prompt_status_counts[prompt_status] += 1
        if prompt_status == "fail":
            prompt_failed_cases.append(qid)
    behavior_pass_count = len(records) - len(behavior_failed_cases)
    review_priority = list(dict.fromkeys([*behavior_failed_cases, *prompt_failed_cases]))

    lines = [
        f"# {suite_label} 逐题运行报告",
        "",
        f"> 用于连续阅读本轮 {len(records)} 题的主报告。详细 TopK / merge / prompt / model-call 信息放到专门诊断报告。",
        "",
        "## 本轮信息",
        "",
        f"- profile: {profile}",
        f"- cases: {len(records)}",
        f"- index_build_id: {build_id}",
        f"- rerank_enabled: {rerank_display}",
        "- classifier_online: not_evaluated",
        "",
        "### 运行结果",
        "",
        f"- answered / refused: {answered_count} / {refused_count}",
        f"- DIRECT / DECOMPOSE: {direct_count} / {decompose_count}",
        f"- behavior_pass: {behavior_pass_count}/{len(records)}",
        f"- behavior_failed_cases: {', '.join(behavior_failed_cases) if behavior_failed_cases else 'none'}",
        "- prompt_evidence_status: "
        f"pass={prompt_status_counts.get('pass', 0)}, "
        f"fail={prompt_status_counts.get('fail', 0)}, "
        f"not_applicable={prompt_status_counts.get('not_applicable', 0)}, "
        f"not_observed={prompt_status_counts.get('not_observed', 0)}",
        f"- prompt_evidence_failed_cases: {', '.join(prompt_failed_cases) if prompt_failed_cases else 'none'}",
        "",
        "### 重点关注",
        "",
        f"- abnormal_refusal: {', '.join(abnormal_refusal_cases) if abnormal_refusal_cases else 'none'}",
        f"- unexpected_answer: {', '.join(unexpected_answer_cases) if unexpected_answer_cases else 'none'}",
        f"- evidence_issue: {', '.join(qid for qid in prompt_failed_cases if qid not in behavior_failed_cases) or 'none'}",
        f"- review_priority: {', '.join(review_priority) if review_priority else 'none'}",
        "",
    ]
    for record in records:
        qid = _display(record.identity.get("qid"))
        expected, any_hit, full_hit, prompt_status = _expected_evidence_flags(record)
        outcome = record.outcome
        evaluation = record.evaluation
        dimensions = _dict(evaluation.get("dimensions"))
        behavior_dimension = _dict(dimensions.get("behavior"))
        route_dimension = _dict(dimensions.get("route_invariants"))
        retrieval_round_ids = {
            str(_dict(event).get("round_id"))
            for event in _list(record.retrieval.get("rounds"))
            if _dict(event).get("round_id") not in (None, "")
        }
        selected_count = len(_list(record.evidence.get("selected")))
        prompt_count = len(_list(record.evidence.get("prompt_visible")))
        citation_count = len(_list(outcome.get("citations")))
        subqueries = [str(item) for item in _list(record.route.get("subqueries")) if str(item).strip()]
        rewritten = record.route.get("rewrite_query") or record.route.get("rewritten_query")
        error_types = [str(_dict(item).get("error_type")) for item in record.errors if _dict(item).get("error_type")]

        lines.extend(
            [
                f"## {qid} — {_display(record.query)}",
                "",
                f"- expected_behavior: {_display(evaluation.get('expected_behavior'))}",
                f"- expected_evidence: {_display(expected)}",
                f"- actual_behavior: {_actual_behavior(record)}",
                f"- refused: {_display(outcome.get('refused'))}",
                f"- path: {_display(record.route.get('actual_route'))}",
                f"- retrieval_rounds: {len(retrieval_round_ids) if retrieval_round_ids else 1}",
            ]
        )
        if subqueries:
            for index, subquery in enumerate(subqueries, start=1):
                lines.append(f"- subquery_{index}: {_display(subquery)}")
        if rewritten:
            lines.append(f"- rewritten_query: {_display(rewritten)}")
        lines.extend(
            [
                f"- first_sufficiency: {_display(record.sufficiency.get('first'))}",
                f"- second_sufficiency: {_display(record.sufficiency.get('second')) if record.sufficiency.get('second') is not None else 'None'}",
                f"- retrieved_count: {len(_list(record.evidence.get('retrieved')))}",
                f"- selected_count: {selected_count}",
                f"- prompt_chunk_count: {prompt_count}",
                f"- citation_count: {citation_count}",
                f"- expected_evidence_any_hit: {_display(any_hit)}",
                f"- expected_evidence_full_hit: {_display(full_hit)}",
                f"- prompt_evidence_status: {_display(prompt_status)}",
                f"- behavior_pass: {_display(behavior_dimension.get('status') == 'pass')}",
                f"- path_pass: {_display(route_dimension.get('status') == 'pass')}",
                f"- total_ms: {_display(record.timing.get('actual_total_ms'))}",
                f"- model_call_count: {len(record.model_calls)}",
                f"- total_tokens: {_display(record.usage.get('total_tokens'))}",
                f"- estimated_cost_usd: {_display(record.usage.get('estimated_cost_usd'))}",
            ]
        )
        if outcome.get("refusal_reason"):
            lines.append(f"- refuse_reason: {_display(outcome.get('refusal_reason'))}")
        if error_types:
            lines.append(f"- errors: {_display(error_types)}")
        lines.extend(["- agentic_steps:"])
        for step in _concise_agentic_steps(record):
            lines.append(f"  - {step}")
        lines.extend(
            [
                "",
                "### Answer",
                "",
                str(outcome.get("answer") or NOT_OBSERVED).strip(),
                "",
                "### Citations",
                "",
                *_citation_lines(record),
                "",
            ]
        )
    return "\n".join(lines)


def _source_ids(items: Sequence[Any]) -> set[str]:
    return {
        str(item.get("source_id"))
        for item in (_dict(raw) for raw in items)
        if item.get("source_id")
    }


def _expected_source_list(record: CanonicalExecutionRecord) -> list[str]:
    dimensions = _dict(record.evaluation.get("dimensions"))
    expected_dimension = _dict(dimensions.get("expected_evidence"))
    return [str(item) for item in _list(expected_dimension.get("expected")) if str(item).strip()]


def _hit_metrics(expected: Sequence[str], observed_sources: set[str]) -> dict[str, Any]:
    expected_set = {str(item) for item in expected if str(item).strip()}
    if not expected_set:
        return {
            "matched": NOT_APPLICABLE,
            "any_hit": NOT_APPLICABLE,
            "full_hit": NOT_APPLICABLE,
            "coverage_ratio": NOT_APPLICABLE,
        }
    matched = len(expected_set & observed_sources)
    return {
        "matched": matched,
        "any_hit": matched > 0,
        "full_hit": matched == len(expected_set),
        "coverage_ratio": matched / len(expected_set),
    }


def _round1_original_candidates(record: CanonicalExecutionRecord) -> list[dict[str, Any]]:
    for raw_event in _list(record.retrieval.get("rounds")):
        event = _dict(raw_event)
        if str(event.get("round_id")) == "1" and str(event.get("query_role")) == "original":
            candidates = [_dict(raw) for raw in _list(event.get("candidates"))]
            return sorted(
                candidates,
                key=lambda item: (
                    _number(item.get("rank")) if _number(item.get("rank")) is not None else math.inf
                ),
            )
    return []


def _retrieval_signal_row(record: CanonicalExecutionRecord) -> dict[str, Any]:
    expected = _expected_source_list(record)
    expected_set = set(expected)
    candidates = _round1_original_candidates(record)
    raw_sources = _source_ids(candidates)
    final_items = _list(record.evidence.get("selected"))
    final_sources = _source_ids(final_items)
    prompt_items = _list(record.evidence.get("prompt_visible")) or _list(record.prompt.get("visible_evidence"))
    prompt_sources = _source_ids(prompt_items)

    raw_metrics = _hit_metrics(expected, raw_sources)
    final_metrics = _hit_metrics(expected, final_sources)
    prompt_metrics = _hit_metrics(expected, prompt_sources)

    scores = [
        _number(item.get("vector_score", item.get("score")))
        for item in candidates[:2]
    ]
    top1 = scores[0] if len(scores) >= 1 else None
    top2 = scores[1] if len(scores) >= 2 else None
    diff = top1 - top2 if top1 is not None and top2 is not None else None

    expected_ranks = [
        int(rank)
        for item in candidates
        if str(item.get("source_id")) in expected_set
        and (rank := _number(item.get("rank"))) is not None
    ]
    if not expected:
        expected_first_rank: Any = NOT_APPLICABLE
    elif expected_ranks:
        expected_first_rank = min(expected_ranks)
    else:
        expected_first_rank = "not_found"

    return {
        "qid": record.identity.get("qid"),
        "route": record.route.get("actual_route"),
        "expected_evidence_count": len(expected) if expected else NOT_APPLICABLE,
        "top1": top1 if top1 is not None else NOT_OBSERVED,
        "top2": top2 if top2 is not None else NOT_OBSERVED,
        "diff": diff if diff is not None else NOT_OBSERVED,
        "unique_source_count": len(raw_sources),
        "raw_retrieval_any_hit": raw_metrics["any_hit"],
        "raw_retrieval_full_hit": raw_metrics["full_hit"],
        "raw_retrieval_coverage_ratio": raw_metrics["coverage_ratio"],
        "expected_first_rank": expected_first_rank,
        "final_evidence_any_hit": final_metrics["any_hit"],
        "final_evidence_full_hit": final_metrics["full_hit"],
        "final_evidence_coverage_ratio": final_metrics["coverage_ratio"],
        "prompt_evidence_any_hit": prompt_metrics["any_hit"],
        "prompt_evidence_full_hit": prompt_metrics["full_hit"],
        "prompt_evidence_coverage_ratio": prompt_metrics["coverage_ratio"],
        "_raw_matched": raw_metrics["matched"],
        "_final_matched": final_metrics["matched"],
        "_prompt_matched": prompt_metrics["matched"],
    }


def _retrieval_signal_markdown(
    records: Sequence[CanonicalExecutionRecord],
    signal_rows: Sequence[dict[str, Any]],
    *,
    suite_label: str,
) -> str:
    applicable = [
        row for row in signal_rows
        if isinstance(row.get("_raw_matched"), int)
    ]

    def _count_true(field: str) -> int:
        return sum(row.get(field) is True for row in applicable)

    improved = [
        str(row.get("qid"))
        for row in applicable
        if int(row["_final_matched"]) > int(row["_raw_matched"])
    ]
    degraded = [
        str(row.get("qid"))
        for row in applicable
        if int(row["_final_matched"]) < int(row["_raw_matched"])
    ]
    prompt_loss = [
        str(row.get("qid"))
        for row in applicable
        if int(row["_prompt_matched"]) < int(row["_final_matched"])
    ]

    profile = _display(records[0].provenance.get("profile")) if records else NOT_OBSERVED
    build_id = _display(records[0].provenance.get("index_build_id")) if records else NOT_OBSERVED
    lines = [
        f"# {suite_label} 检索信号摘要",
        "",
        "> 来源：当前 live CanonicalExecutionRecord（CER）确定性投影。",
        "> `top1 / top2 / diff` 只使用 `round_id=1 + query_role=original` 的原始向量检索结果；",
        "> DECOMPOSE 子问题、rewrite、RRF merge 分数不混入这组三个基础 Retriever 信号。",
        "",
        "## 本轮信息",
        "",
        f"- profile: {profile}",
        f"- cases: {len(records)}",
        f"- index_build_id: {build_id}",
        f"- expected-evidence applicable cases: {len(applicable)}",
        "",
        "## 批次摘要",
        "",
        f"- raw_retrieval_any_hit: {_count_true('raw_retrieval_any_hit')}/{len(applicable)}",
        f"- raw_retrieval_full_hit: {_count_true('raw_retrieval_full_hit')}/{len(applicable)}",
        f"- final_evidence_any_hit: {_count_true('final_evidence_any_hit')}/{len(applicable)}",
        f"- final_evidence_full_hit: {_count_true('final_evidence_full_hit')}/{len(applicable)}",
        f"- prompt_evidence_any_hit: {_count_true('prompt_evidence_any_hit')}/{len(applicable)}",
        f"- prompt_evidence_full_hit: {_count_true('prompt_evidence_full_hit')}/{len(applicable)}",
        f"- agentic_recovery (final matched > original matched): {', '.join(improved) if improved else 'none'}",
        f"- agentic_loss (final matched < original matched): {', '.join(degraded) if degraded else 'none'}",
        f"- prompt_loss (prompt matched < final matched): {', '.join(prompt_loss) if prompt_loss else 'none'}",
        "",
        "## 逐题信号",
        "",
        "| qid | route | expected_count | top1 | top2 | diff | unique_sources | raw any/full | raw coverage | first_expected_rank | final any/full | final coverage | prompt any/full | prompt coverage |",
        "| :-- | :-- | --: | --: | --: | --: | --: | :--: | --: | :--: | :--: | --: | :--: | --: |",
    ]
    for row in signal_rows:
        lines.append(
            "| {qid} | {route} | {expected_evidence_count} | {top1} | {top2} | {diff} | "
            "{unique_source_count} | {raw_any}/{raw_full} | {raw_cov} | {first_rank} | "
            "{final_any}/{final_full} | {final_cov} | {prompt_any}/{prompt_full} | {prompt_cov} |".format(
                qid=_display(row.get("qid")),
                route=_display(row.get("route")),
                expected_evidence_count=_display(row.get("expected_evidence_count")),
                top1=_display(row.get("top1")),
                top2=_display(row.get("top2")),
                diff=_display(row.get("diff")),
                unique_source_count=_display(row.get("unique_source_count")),
                raw_any=_display(row.get("raw_retrieval_any_hit")),
                raw_full=_display(row.get("raw_retrieval_full_hit")),
                raw_cov=_display(row.get("raw_retrieval_coverage_ratio")),
                first_rank=_display(row.get("expected_first_rank")),
                final_any=_display(row.get("final_evidence_any_hit")),
                final_full=_display(row.get("final_evidence_full_hit")),
                final_cov=_display(row.get("final_evidence_coverage_ratio")),
                prompt_any=_display(row.get("prompt_evidence_any_hit")),
                prompt_full=_display(row.get("prompt_evidence_full_hit")),
                prompt_cov=_display(row.get("prompt_evidence_coverage_ratio")),
            )
        )
    lines.extend(
        [
            "",
            "## 最终检索分布",
            "",
            "> 查阅表：保留 expected evidence、最终选中的 Top5 文档与对应分数。",
            "> DIRECT 通常是 vector score；DECOMPOSE / 二轮 merge 的 final score 可能是 RRF/merge score，只用于本行排序，不与 vector score 横向比较。",
            "",
            "| qid | expected_evidence | final_sources | scores |",
            "| :-- | :-- | :-- | :-- |",
        ]
    )
    for record in records:
        expected = _expected_source_list(record)
        selected = _list(record.evidence.get("selected")) or _merged_items(record)
        lines.append(
            "| {qid} | {expected} | {sources} | {scores} |".format(
                qid=_display(record.identity.get("qid")),
                expected=_short_source_list(expected),
                sources=_source_sequence(selected),
                scores=_score_sequence(selected),
            )
        )

    lines.extend(
        [
            "",
            "## Agentic 检索过程",
            "",
            "> 仅列 DECOMPOSE 与发生二轮检索的题；每题第一行是文档号，第二行是对应 score。",
            "",
            "| qid | item | original / round1 | subquery_1 / rewrite | subquery_2 | final |",
            "| :-- | :-- | :-- | :-- | :-- | :-- |",
        ]
    )
    for record in records:
        events = _event_map(record)
        round_ids = {round_id for round_id, _ in events}
        subquery_events = [
            (role, event)
            for (round_id, role), event in events.items()
            if round_id == 1 and role.startswith("subquery_")
        ]
        has_round2 = any(round_id >= 2 for round_id in round_ids)
        if not subquery_events and not has_round2:
            continue

        original_items = _list(_dict(events.get((1, "original"))).get("candidates"))
        if has_round2:
            branch1_items = _list(_dict(events.get((2, "rewrite"))).get("candidates"))
            branch2_items: list[Any] = []
        else:
            subquery_events = sorted(subquery_events, key=lambda pair: pair[0])
            branch1_items = _list(subquery_events[0][1].get("candidates")) if subquery_events else []
            branch2_items = _list(subquery_events[1][1].get("candidates")) if len(subquery_events) > 1 else []
        final_items = _list(record.evidence.get("selected")) or _merged_items(record)
        qid = _display(record.identity.get("qid"))
        lines.append(
            f"| {qid} | source | {_source_sequence(original_items)} | {_source_sequence(branch1_items)} | "
            f"{_source_sequence(branch2_items)} | {_source_sequence(final_items)} |"
        )
        lines.append(
            f"|  | score | {_score_sequence(original_items)} | {_score_sequence(branch1_items)} | "
            f"{_score_sequence(branch2_items)} | {_score_sequence(final_items)} |"
        )

    lines.extend(
        [
            "",
            "## 口径说明",
            "",
            "- `raw_retrieval_*`：仅看第一轮 original query 的 TopK；用于和历史纯 Retriever signal 对齐。",
            "- `final_evidence_*`：看 Agentic 检索/merge 后 `evidence.selected` 中保留下来的来源。",
            "- `prompt_evidence_*`：看最终实际进入 prompt 的 evidence 来源。",
            "- `any_hit` 与 `full_hit` 在本报告中同时展示，不改变 unified evaluation 的 hard-gate 判定逻辑。",
            "- expected evidence 不适用的拒答题显示 `not_applicable`，不参与命中率分母。",
            "",
        ]
    )
    return "\n".join(lines)



def _source_label(source_id: Any) -> str:
    """生成简短来源标签，并保留可选的数字前缀。"""
    value = str(source_id or "").strip()
    if not value:
        return NOT_OBSERVED
    name = value.rsplit("/", 1)[-1]
    match = re.match(r"^(\d+)", name)
    return match.group(1) if match else name


def _short_source_list(source_ids: Sequence[Any]) -> str:
    values = [_source_label(item) for item in source_ids if str(item or "").strip()]
    return ",".join(values) if values else NOT_APPLICABLE


def _ordered_sources(items: Sequence[Any]) -> list[str]:
    return [
        str(item.get("source_id"))
        for item in (_dict(raw) for raw in items)
        if item.get("source_id")
    ]


def _source_sequence(items: Sequence[Any]) -> str:
    sources = _ordered_sources(items)
    if not sources:
        return NOT_APPLICABLE
    return ",".join(_source_label(source_id) for source_id in sources)


def _effective_score(item: Mapping[str, Any]) -> float | None:
    for key in ("rerank_score", "score", "vector_score", "rrf_score"):
        value = _number(item.get(key))
        if value is not None:
            return value
    return None


def _score_sequence(items: Sequence[Any], decimals: int = 4) -> str:
    values: list[str] = []
    for raw in items:
        score = _effective_score(_dict(raw))
        values.append(f"{score:.{decimals}f}" if score is not None else "")
    return ",".join(values) if values else NOT_APPLICABLE


def _offset_pair(item: Mapping[str, Any]) -> tuple[Any, Any]:
    start = item.get("offset_start", item.get("source_offset_start"))
    end = item.get("offset_end", item.get("source_offset_end"))
    if start is not None and end is not None:
        return start, end
    chunk_id = str(item.get("chunk_id") or "")
    match = re.search(r"@(\d+)-(\d+)(?:#|$)", chunk_id)
    if match:
        return match.group(1), match.group(2)
    return None, None


def _chunk_ref(raw: Any) -> str:
    item = _dict(raw)
    source = _source_label(item.get("source_id"))
    start, end = _offset_pair(item)
    if start is None or end is None:
        return source
    return f"{source}@{start}-{end}"


def _chunk_sequence(items: Sequence[Any]) -> str:
    refs = [_chunk_ref(raw) for raw in items if _dict(raw).get("source_id")]
    return ", ".join(refs) if refs else NOT_APPLICABLE


def _prompt_sequence(items: Sequence[Any]) -> str:
    values: list[str] = []
    for index, raw in enumerate(items, start=1):
        item = _dict(raw)
        if not item.get("source_id"):
            continue
        marker = str(item.get("marker") or f"E{index}")
        values.append(f"{marker}={_chunk_ref(item)}")
    return ", ".join(values) if values else NOT_APPLICABLE


def _citation_marker_sequence(record: CanonicalExecutionRecord) -> str:
    marker_by_chunk = {
        str(item.get("chunk_id")): str(item.get("marker"))
        for item in (_dict(raw) for raw in (_list(record.evidence.get("prompt_visible")) or _list(record.prompt.get("visible_evidence"))))
        if item.get("chunk_id") and item.get("marker")
    }
    markers: list[str] = []
    for raw in _list(record.outcome.get("citations")):
        item = _dict(raw)
        marker = marker_by_chunk.get(str(item.get("chunk_id")))
        markers.append(marker or _chunk_ref(item))
    return ", ".join(markers) if markers else NOT_APPLICABLE


def _event_map(record: CanonicalExecutionRecord) -> dict[tuple[int, str], dict[str, Any]]:
    result: dict[tuple[int, str], dict[str, Any]] = {}
    for raw_event in _list(record.retrieval.get("rounds")):
        event = _dict(raw_event)
        round_number = _number(event.get("round_id"))
        if round_number is None:
            continue
        role = str(event.get("query_role") or NOT_OBSERVED)
        result[(int(round_number), role)] = event
    return result


def _merged_items(record: CanonicalExecutionRecord) -> list[dict[str, Any]]:
    return [_dict(raw) for raw in _list(record.merge.get("final_order"))]


def _source_distribution_case_row(record: CanonicalExecutionRecord) -> dict[str, Any]:
    events = _event_map(record)
    selected = _list(record.evidence.get("selected"))
    prompt_items = _list(record.evidence.get("prompt_visible")) or _list(record.prompt.get("visible_evidence"))
    return {
        "qid": record.identity.get("qid"),
        "route": record.route.get("actual_route"),
        "expected_evidence": _short_source_list(_expected_source_list(record)),
        "original_chunks": _source_sequence(_list(_dict(events.get((1, "original"))).get("candidates"))),
        "subquery_a_chunks": _source_sequence(_list(_dict(events.get((1, "subquery_a"))).get("candidates"))),
        "subquery_b_chunks": _source_sequence(_list(_dict(events.get((1, "subquery_b"))).get("candidates"))),
        "rewrite_chunks": _source_sequence(_list(_dict(events.get((2, "rewrite"))).get("candidates"))),
        "merged_chunks": _source_sequence(_merged_items(record)),
        "final_evidence_chunks": _source_sequence(selected),
        "prompt_chunks": _source_sequence(prompt_items),
        "cited_markers": _citation_marker_sequence(record),
    }


def _source_distribution_summary_rows(
    records: Sequence[CanonicalExecutionRecord],
) -> list[dict[str, Any]]:
    retrieved = Counter()
    top1 = Counter()
    final_evidence = Counter()
    prompt = Counter()
    cited = Counter()
    all_sources: set[str] = set()

    for record in records:
        for raw_event in _list(record.retrieval.get("rounds")):
            event = _dict(raw_event)
            for raw_candidate in _list(event.get("candidates")):
                candidate = _dict(raw_candidate)
                source_id = str(candidate.get("source_id") or "").strip()
                if not source_id:
                    continue
                all_sources.add(source_id)
                retrieved[source_id] += 1
                rank = _number(candidate.get("rank"))
                if rank == 1:
                    top1[source_id] += 1
        for raw_item in _list(record.evidence.get("selected")):
            source_id = str(_dict(raw_item).get("source_id") or "").strip()
            if source_id:
                all_sources.add(source_id)
                final_evidence[source_id] += 1
        prompt_items = _list(record.evidence.get("prompt_visible")) or _list(record.prompt.get("visible_evidence"))
        for raw_item in prompt_items:
            source_id = str(_dict(raw_item).get("source_id") or "").strip()
            if source_id:
                all_sources.add(source_id)
                prompt[source_id] += 1
        for raw_item in _list(record.outcome.get("citations")):
            source_id = str(_dict(raw_item).get("source_id") or "").strip()
            if source_id:
                all_sources.add(source_id)
                cited[source_id] += 1

    rows = [
        {
            "label": _source_label(source_id),
            "source_id": source_id,
            "retrieved_count": retrieved[source_id],
            "top1_count": top1[source_id],
            "final_evidence_count": final_evidence[source_id],
            "prompt_count": prompt[source_id],
            "citation_count": cited[source_id],
        }
        for source_id in all_sources
    ]
    return sorted(
        rows,
        key=lambda row: (
            -int(row["retrieved_count"]),
            -int(row["top1_count"]),
            str(row["source_id"]),
        ),
    )


def _retrieval_source_distribution_markdown(
    records: Sequence[CanonicalExecutionRecord],
    summary_rows: Sequence[dict[str, Any]],
    *,
    suite_label: str,
) -> str:
    profile = _display(records[0].provenance.get("profile")) if records else NOT_OBSERVED
    build_id = _display(records[0].provenance.get("index_build_id")) if records else NOT_OBSERVED
    total_events = sum(len(_list(record.retrieval.get("rounds"))) for record in records)
    lines = [
        f"# {suite_label} 运行检索来源分布",
        "",
        "> 来源：当前 live CanonicalExecutionRecord（CER）确定性投影。",
        "> 文档编号：01–10 = internal，11–34 = external；逐题链保留重复来源。",
        "> 逐题链只显示文档序号；prompt 按顺序对应 E1–E5，cited 只列实际引用的 E 编号。",
        "",
        "## 本轮信息",
        "",
        f"- profile: {profile}",
        f"- cases: {len(records)}",
        f"- retrieval_events: {total_events}",
        f"- index_build_id: {build_id}",
        "",
        "## 逐题来源链",
        "",
    ]

    for record in records:
        qid = _display(record.identity.get("qid"))
        route = str(record.route.get("actual_route") or NOT_OBSERVED)
        events = _event_map(record)
        round_ids = sorted({round_id for round_id, _ in events})
        has_round2 = any(round_id >= 2 for round_id in round_ids)
        merged = _merged_items(record)
        selected = _list(record.evidence.get("selected"))
        prompt_items = _list(record.evidence.get("prompt_visible")) or _list(record.prompt.get("visible_evidence"))
        expected = _short_source_list(_expected_source_list(record))

        lines.extend([f"### {qid} — {route}", "", f"- expected_evidence: {expected}"])
        original_items = _list(_dict(events.get((1, "original"))).get("candidates"))

        if has_round2:
            rewrite_event = _dict(events.get((2, "rewrite")))
            rewritten_query = record.route.get("rewrite_query") or record.route.get("rewritten_query")
            lines.append(f"- round1_original: {_source_sequence(original_items)}")
            if rewritten_query:
                lines.append(f"- rewritten_query: {_display(rewritten_query)}")
            if rewrite_event:
                lines.append(f"- round2_rewrite: {_source_sequence(_list(rewrite_event.get('candidates')))}")
            lines.append(f"- merged: {_source_sequence(merged)}")
        else:
            lines.append(f"- original: {_source_sequence(original_items)}")
            subquery_events = [
                (role, event)
                for (round_id, role), event in events.items()
                if round_id == 1 and role.startswith("subquery_")
            ]
            for role, event in sorted(subquery_events, key=lambda pair: pair[0]):
                lines.append(f"- {role}: {_source_sequence(_list(event.get('candidates')))}")
            if route == "DECOMPOSE" or subquery_events:
                lines.append(f"- merged: {_source_sequence(merged)}")

        # 只有 final 与 original 或 merged 确实不同时，才单独展示 final，避免重复信息。
        baseline_items = merged if (route == "DECOMPOSE" or has_round2) and merged else original_items
        if _source_sequence(selected) != _source_sequence(baseline_items):
            lines.append(f"- final: {_source_sequence(selected)}")
        lines.append(f"- prompt: {_source_sequence(prompt_items)}")
        lines.append(f"- cited: {_citation_marker_sequence(record)}")
        lines.append("")

    lines.extend(
        [
            "## 批次级来源统计",
            "",
            "| doc | source_id | retrieved | Top1 | final_evidence | prompt | citation |",
            "| :-- | :-- | --: | --: | --: | --: | --: |",
        ]
    )
    for row in summary_rows:
        lines.append(
            "| {label} | {source_id} | {retrieved_count} | {top1_count} | "
            "{final_evidence_count} | {prompt_count} | {citation_count} |".format(
                **{key: _display(value) for key, value in row.items()}
            )
        )
    lines.extend(
        [
            "",
            "## 口径说明",
            "",
            "- `retrieved`：所有真实 retrieval event 中 candidate 的出现次数；DECOMPOSE 子问题与 Round 2 rewrite 都计入。",
            "- `Top1`：各 retrieval event 中 rank=1 的来源次数。",
            "- `final_evidence`：`evidence.selected` 中该来源的 chunk 数。",
            "- `prompt`：最终进入 prompt 的 chunk 数。",
            "- `citation`：最终回答实际引用该来源的 citation 数。",
            "- 逐题链只使用文档号；重复 source 不去重。prompt 中第 1–5 个来源依次对应 E1–E5。",
            "",
        ]
    )
    return "\n".join(lines)



def _diagnostic_chunk_ref(raw: Any) -> str:
    """为详细检索诊断生成简短但可唯一定位的 chunk 引用。"""
    item = _dict(raw)
    base = _chunk_ref(item)
    chunk_id = str(item.get("chunk_id") or "")
    suffix = chunk_id.rsplit("#", 1)[-1] if "#" in chunk_id else ""
    return f"{base}#{suffix[:12]}" if suffix else base


def _workflow_candidate_table(candidates: Sequence[Any]) -> list[str]:
    lines = [
        "| rank | chunk | score_type | score |",
        "| --: | :-- | :-- | --: |",
    ]
    if not candidates:
        lines.append("| — | not_observed | not_observed | not_observed |")
        return lines
    for raw in candidates:
        item = _dict(raw)
        score = _number(item.get("score"))
        lines.append(
            f"| {_display(item.get('rank'))} | {_diagnostic_chunk_ref(item)} | "
            f"{_display(item.get('score_type'))} | {f'{score:.4f}' if score is not None else NOT_OBSERVED} |"
        )
    return lines


def _format_rrf_contributions(raw: Any) -> str:
    item = _dict(raw)
    parts: list[str] = []
    for contribution_raw in _list(item.get("contributions")):
        contribution = _dict(contribution_raw)
        role = str(contribution.get("query_role") or NOT_OBSERVED)
        round_id = _display(contribution.get("round_id"))
        rank = _display(contribution.get("rank"))
        raw_score = _number(contribution.get("raw_score"))
        rrf = _number(contribution.get("rrf_contribution"))
        raw_text = f"{raw_score:.4f}" if raw_score is not None else NOT_OBSERVED
        rrf_text = f"{rrf:.5f}" if rrf is not None else NOT_OBSERVED
        parts.append(f"r{round_id}/{role}: rank={rank}, raw={raw_text}, +rrf={rrf_text}")
    return "；".join(parts) if parts else NOT_OBSERVED


def _workflow_merge_table(record: CanonicalExecutionRecord) -> list[str]:
    merged = _merged_items(record)
    strategy = str(record.merge.get("strategy") or NOT_OBSERVED)
    lines = [
        f"- strategy: {strategy}",
        f"- rrf_k: {_display(record.merge.get('rrf_k'))}",
        f"- unique_candidate_count: {_display(record.merge.get('unique_candidate_count'))}",
        "",
        "| final_rank | chunk | merge_score | contributions |",
        "| --: | :-- | --: | :-- |",
    ]
    if not merged:
        lines.append("| — | not_observed | not_observed | not_observed |")
        return lines
    for raw in merged:
        item = _dict(raw)
        score = _number(item.get("rrf_score", item.get("score")))
        lines.append(
            f"| {_display(item.get('rank'))} | {_diagnostic_chunk_ref(item)} | "
            f"{f'{score:.5f}' if score is not None else NOT_OBSERVED} | "
            f"{_format_rrf_contributions(item)} |"
        )
    return lines


def _workflow_final_evidence_table(record: CanonicalExecutionRecord) -> list[str]:
    selected = [_dict(raw) for raw in _list(record.evidence.get("selected"))]
    prompt_items = [
        _dict(raw)
        for raw in (_list(record.evidence.get("prompt_visible")) or _list(record.prompt.get("visible_evidence")))
    ]
    marker_by_chunk = {
        str(item.get("chunk_id")): str(item.get("marker"))
        for item in prompt_items
        if item.get("chunk_id") and item.get("marker")
    }
    cited_chunks = {
        str(_dict(raw).get("chunk_id"))
        for raw in _list(record.outcome.get("citations"))
        if _dict(raw).get("chunk_id")
    }
    lines = [
        "| rank | chunk | selected_score | prompt_marker | cited |",
        "| --: | :-- | --: | :--: | :--: |",
    ]
    if not selected:
        lines.append("| — | not_observed | not_observed | not_applicable | false |")
        return lines
    for raw in selected:
        item = _dict(raw)
        chunk_id = str(item.get("chunk_id") or "")
        score = _effective_score(item)
        marker = marker_by_chunk.get(chunk_id, NOT_APPLICABLE)
        lines.append(
            f"| {_display(item.get('rank'))} | {_diagnostic_chunk_ref(item)} | "
            f"{f'{score:.5f}' if score is not None else NOT_OBSERVED} | "
            f"{marker} | {'true' if chunk_id in cited_chunks else 'false'} |"
        )
    return lines


def _workflow_event_heading(event: Mapping[str, Any]) -> str:
    round_id = int(_number(event.get("round_id")) or 1)
    role = str(event.get("query_role") or NOT_OBSERVED)
    if role == "original":
        return f"Round {round_id} — original"
    if role == "rewrite":
        return f"Round {round_id} — rewrite"
    return f"Round {round_id} — {role}"


def _retrieval_workflow_markdown(
    records: Sequence[CanonicalExecutionRecord],
    *,
    suite_label: str,
) -> str:
    profile = _display(records[0].provenance.get("profile")) if records else NOT_OBSERVED
    build_id = _display(records[0].provenance.get("index_build_id")) if records else NOT_OBSERVED
    rerank_values = {bool(record.rerank.get("enabled")) for record in records}
    rerank_display = _display(next(iter(rerank_values))) if len(rerank_values) == 1 else "mixed"
    agentic_cases = [
        str(record.identity.get("qid"))
        for record in records
        if str(record.route.get("actual_route")) == "DECOMPOSE"
        or any(int(_number(_dict(event).get("round_id")) or 1) >= 2 for event in _list(record.retrieval.get("rounds")))
    ]
    lines = [
        f"# {suite_label} 检索工作流明细",
        "",
        "> 来源：当前 live CanonicalExecutionRecord（CER）确定性投影。",
        "> 这是异常诊断报告：02 用于快速看信号，03 用于查来源/chunk；本报告展开每个 retrieval event、merge/RRF 和最终 evidence 去留。",
        "> 文档编号：01–10 = internal，11–34 = external；`07@301-849#hash` 可唯一定位 chunk。默认不铺 chunk 正文 preview。",
        "",
        "## 本轮信息",
        "",
        f"- profile: {profile}",
        f"- cases: {len(records)}",
        f"- index_build_id: {build_id}",
        f"- rerank_enabled: {rerank_display}",
        f"- multi-query / round2 cases: {', '.join(agentic_cases) if agentic_cases else 'none'}",
        "",
    ]

    for record in records:
        qid = _display(record.identity.get("qid"))
        route = str(record.route.get("actual_route") or NOT_OBSERVED)
        expected = _short_source_list(_expected_source_list(record))
        first = record.sufficiency.get("first")
        second = record.sufficiency.get("second")
        lines.extend(
            [
                f"## {qid} — {route}",
                "",
                f"- query: {_display(record.query)}",
                f"- expected_evidence: {expected}",
                f"- first_sufficiency: {_display(first)}",
            ]
        )
        rewritten = record.route.get("rewrite_query") or record.route.get("rewritten_query")
        if rewritten:
            lines.append(f"- rewritten_query: {_display(rewritten)}")
        if second not in (None, "", NOT_OBSERVED):
            lines.append(f"- second_sufficiency: {_display(second)}")
        lines.append(f"- final_status: {_display(record.outcome.get('status'))}")
        if record.outcome.get("refusal_reason"):
            lines.append(f"- refusal_reason: {_display(record.outcome.get('refusal_reason'))}")
        lines.append("")

        events = [_dict(raw) for raw in _list(record.retrieval.get("rounds"))]
        events.sort(
            key=lambda event: (
                int(_number(event.get("round_id")) or 1),
                {"original": 0, "subquery_a": 1, "subquery_b": 2, "rewrite": 3}.get(
                    str(event.get("query_role") or ""), 9
                ),
            )
        )
        for event in events:
            lines.extend(
                [
                    f"### {_workflow_event_heading(event)}",
                    "",
                    f"- query: {_display(event.get('query'))}",
                    "",
                    *_workflow_candidate_table(_list(event.get("candidates"))),
                    "",
                ]
            )

        merge_strategy = str(record.merge.get("strategy") or "")
        if merge_strategy == "rrf" or len(events) > 1:
            lines.extend(["### Merge / RRF", "", *_workflow_merge_table(record), ""])

        lines.extend(
            [
                "### Final Evidence / Prompt / Citation",
                "",
                *_workflow_final_evidence_table(record),
                "",
            ]
        )

    lines.extend(
        [
            "## 口径说明",
            "",
            "- retrieval event 表按 `score_type + score` 展示真实分数语义：Dense 为 `vector_similarity`，BM25 为 `bm25`；RRF 融合分数在 Merge / RRF 表单独展示。",
            "- `Merge / RRF` 仅在实际发生多 query / 多轮 merge 时展示；contributions 展开到 query role、原 rank、raw score 与 RRF contribution。",
            "- `selected_score` 是最终 `evidence.selected` 中记录的排序分数；RRF 路径通常为 merge score，DIRECT 单查询通常为 vector score。",
            "- `prompt_marker` 显示该 final evidence 是否真正进入 prompt；`cited=true` 表示最终回答实际引用了该 chunk。",
            "- rerank 全局关闭时不生成逐题空 rerank 表；后续若真实开启，再显示 before/after/rerank score/latency。",
            f"- 本报告不默认展开 chunk 正文，避免 {len(records)} 题诊断文件膨胀；正文可由 chunk locator 回查 CER。",
            "",
        ]
    )
    return "\n".join(lines)

def _model_calls_for_role(record: CanonicalExecutionRecord, role: str) -> list[dict[str, Any]]:
    return [
        _dict(call)
        for call in record.model_calls
        if str(_dict(call).get("role") or "") == role
    ]


def _sum_call_latency(record: CanonicalExecutionRecord, role: str | None = None) -> float:
    calls = record.model_calls if role is None else _model_calls_for_role(record, role)
    return sum(_number(_dict(call).get("latency_ms")) or 0.0 for call in calls)


def _expected_model_roles(record: CanonicalExecutionRecord) -> list[str]:
    roles = ["sufficiency_judge"]
    if str(record.route.get("actual_route") or "") == "DECOMPOSE":
        roles.append("subquery_generator")
    if record.route.get("rewrite_query") or record.route.get("rewritten_query") or record.sufficiency.get("second") not in (None, "", NOT_OBSERVED):
        roles.append("rewrite_query")
    if record.outcome.get("status") == "ANSWERED" and record.outcome.get("refused") is not True:
        roles.append("generator")
    return roles


def _timing_usage_row(record: CanonicalExecutionRecord) -> dict[str, Any]:
    timing = record.timing
    service_total_ms = _number(timing.get("service_total_ms", timing.get("actual_total_ms")))
    engine_ms = _number(timing.get("engine_ms", timing.get("workflow_total_ms")))
    pipeline_total_ms = _number(timing.get("pipeline_total_ms"))
    retrieval_ms = _number(timing.get("retrieval_ms")) or 0.0
    engine_init_ms = _number(timing.get("engine_init_ms")) or 0.0
    queue_wait_ms = _number(timing.get("queue_wait_ms")) or 0.0
    observed_model_ms = _sum_call_latency(record)
    engine_observed_components_ms = engine_init_ms + retrieval_ms + observed_model_ms
    service_unaccounted_ms = (
        None
        if service_total_ms is None or engine_ms is None
        else max(0.0, service_total_ms - queue_wait_ms - engine_ms)
    )
    return {
        "qid": record.identity.get("qid"),
        "route": record.route.get("actual_route"),
        "status": record.outcome.get("status"),
        "service_total_ms": service_total_ms if service_total_ms is not None else NOT_OBSERVED,
        "engine_ms": engine_ms if engine_ms is not None else NOT_OBSERVED,
        "pipeline_total_ms": pipeline_total_ms if pipeline_total_ms is not None else NOT_OBSERVED,
        "engine_init_ms": engine_init_ms,
        "queue_wait_ms": queue_wait_ms,
        "observed_model_ms": observed_model_ms,
        "retrieval_ms": retrieval_ms,
        "engine_observed_components_ms": engine_observed_components_ms,
        "service_unaccounted_ms": (
            service_unaccounted_ms if service_unaccounted_ms is not None else NOT_OBSERVED
        ),
        "tokens": record.usage.get("total_tokens", NOT_OBSERVED),
        "cost_usd": record.usage.get("estimated_cost_usd", NOT_OBSERVED),
    }


def _timing_stage_row(record: CanonicalExecutionRecord) -> dict[str, Any]:
    timing = record.timing
    rerank_enabled = bool(record.rerank.get("enabled"))
    merge_ms = timing.get("merge_ms", NOT_OBSERVED)
    rerank_ms: Any = timing.get("rerank_ms", NOT_OBSERVED) if rerank_enabled else NOT_APPLICABLE
    build_response_ms = timing.get("build_response_ms", NOT_OBSERVED)
    decompose_ms = _sum_call_latency(record, "subquery_generator")
    if not _model_calls_for_role(record, "subquery_generator"):
        decompose_ms = NOT_APPLICABLE
    return {
        "qid": record.identity.get("qid"),
        "engine_init_ms": timing.get("engine_init_ms", NOT_OBSERVED),
        "decompose_ms": decompose_ms,
        "rewrite_ms": timing.get("query_rewrite_ms", NOT_OBSERVED),
        "retrieve_total_ms": timing.get("retrieval_ms", NOT_OBSERVED),
        "first_retrieve_ms": timing.get("first_retrieval_ms", NOT_OBSERVED),
        "second_retrieve_ms": timing.get("second_retrieval_ms", NOT_OBSERVED),
        "merge_ms": merge_ms,
        "rerank_ms": rerank_ms,
        "first_suff_ms": timing.get("first_sufficiency_ms", NOT_OBSERVED),
        "second_suff_ms": timing.get("second_sufficiency_ms", NOT_OBSERVED),
        "generate_ms": timing.get("generation_ms", NOT_OBSERVED),
        "generator_llm_ms": timing.get("llm_generate_ms", NOT_OBSERVED),
        "build_response_ms": build_response_ms,
    }


def _usage_detail_row(record: CanonicalExecutionRecord) -> dict[str, Any]:
    expected_roles = _expected_model_roles(record)
    observed_roles = sorted({
        str(_dict(call).get("role"))
        for call in record.model_calls
        if _dict(call).get("role")
    })
    missing_roles = [role for role in expected_roles if role not in observed_roles]
    usage = record.usage
    full_ledger = not missing_roles and _number(usage.get("total_tokens")) is not None
    return {
        "qid": record.identity.get("qid"),
        "route": record.route.get("actual_route"),
        "status": record.outcome.get("status"),
        "full_ledger": full_ledger,
        "expected_roles": expected_roles,
        "observed_roles": observed_roles,
        "missing_roles": missing_roles,
        "model_calls": len(record.model_calls),
        "prompt_tokens": usage.get("prompt_tokens", NOT_OBSERVED),
        "completion_tokens": usage.get("completion_tokens", NOT_OBSERVED),
        "reasoning_tokens": usage.get("reasoning_tokens", NOT_OBSERVED),
        "cached_tokens": usage.get("cached_tokens", NOT_OBSERVED),
        "cache_write_tokens": usage.get("cache_write_tokens", NOT_OBSERVED),
        "total_tokens": usage.get("total_tokens", NOT_OBSERVED),
        "observed_model_ms": _sum_call_latency(record),
        "generator_llm_ms": record.timing.get("llm_generate_ms", NOT_OBSERVED),
        "cost_usd": usage.get("estimated_cost_usd", NOT_OBSERVED),
    }


def _fmt_ms(value: Any) -> str:
    number = _number(value)
    return str(int(round(number))) if number is not None else _display(value)


def _fmt_cost(value: Any) -> str:
    number = _number(value)
    return f"{number:.6f}" if number is not None else _display(value)


def _fmt_tokens(value: Any) -> str:
    number = _number(value)
    return str(int(round(number))) if number is not None else _display(value)


def _role_summary_rows(records: Sequence[CanonicalExecutionRecord]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        for raw_call in record.model_calls:
            call = _dict(raw_call)
            role = str(call.get("role") or NOT_OBSERVED)
            grouped.setdefault(role, []).append(call)
    rows: list[dict[str, Any]] = []
    for role, calls in grouped.items():
        latencies = [value for call in calls if (value := _number(call.get("latency_ms"))) is not None]
        tokens = [value for call in calls if (value := _number(call.get("total_tokens"))) is not None]
        costs = [value for call in calls if (value := _number(call.get("estimated_cost_usd"))) is not None]
        rows.append({
            "role": role,
            "calls": len(calls),
            "total_ms": sum(latencies),
            "median_ms": statistics.median(latencies) if latencies else NOT_OBSERVED,
            "total_tokens": sum(tokens) if len(tokens) == len(calls) else NOT_OBSERVED,
            "total_tokens_observed_sum": sum(tokens),
            "token_unknown_calls": len(calls) - len(tokens),
            "cost_usd": sum(costs) if len(costs) == len(calls) else NOT_OBSERVED,
            "cost_usd_observed_sum": sum(costs),
            "cost_unknown_calls": len(calls) - len(costs),
        })
    return sorted(rows, key=lambda row: (-int(row["calls"]), str(row["role"])))


def _timing_usage_cost_markdown(
    records: Sequence[CanonicalExecutionRecord],
    *,
    suite_label: str,
) -> str:
    timing_rows = [_timing_usage_row(record) for record in records]
    stage_rows = [_timing_stage_row(record) for record in records]
    usage_rows = [_usage_detail_row(record) for record in records]
    calls = [(_display(record.identity.get("qid")), _dict(call)) for record in records for call in record.model_calls]

    route_counts = Counter(str(record.route.get("actual_route")) for record in records)
    status_counts = Counter(str(record.outcome.get("status")) for record in records)
    role_counts = Counter(str(call.get("role")) for _, call in calls)
    provider_counts = Counter(str(call.get("provider")) for _, call in calls)
    model_counts = Counter(str(call.get("resolved_model")) for _, call in calls)
    upstream_counts = Counter(str(call.get("upstream_provider")) for _, call in calls if call.get("upstream_provider"))

    service_values = [
        value
        for row in timing_rows
        if (value := _number(row.get("service_total_ms"))) is not None
    ]
    token_values = [value for row in usage_rows if (value := _number(row.get("total_tokens"))) is not None]
    cost_values = [value for row in usage_rows if (value := _number(row.get("cost_usd"))) is not None]
    token_unknown_records = len(usage_rows) - len(token_values)
    cost_unknown_records = len(usage_rows) - len(cost_values)
    full_ledgers = sum(row.get("full_ledger") is True for row in usage_rows)

    generator_models = sorted({
        str(call.get("resolved_model"))
        for _, call in calls
        if call.get("role") == "generator" and call.get("resolved_model")
    })
    judge_models = sorted({
        str(call.get("resolved_model"))
        for _, call in calls
        if call.get("role") == "sufficiency_judge" and call.get("resolved_model")
    })
    run_ids = sorted({str(record.identity.get("run_id")) for record in records if record.identity.get("run_id")})
    profile = _display(records[0].provenance.get("profile")) if records else NOT_OBSERVED
    build_id = _display(records[0].provenance.get("index_build_id")) if records else NOT_OBSERVED

    cost_coverages = Counter(str(_dict(record.usage.get("cost_estimation")).get("coverage") or NOT_OBSERVED) for record in records)
    price_versions = sorted({
        str(_dict(record.usage.get("cost_estimation")).get("price_table_version"))
        for record in records
        if _dict(record.usage.get("cost_estimation")).get("price_table_version")
    })
    billing_reconciled = sorted({
        str(_dict(record.usage.get("cost_estimation")).get("provider_billing_reconciled"))
        for record in records
        if _dict(record.usage.get("cost_estimation")).get("provider_billing_reconciled") is not None
    })

    budget_limits = []
    for record in records:
        budget_dim = _dict(_dict(record.evaluation.get("dimensions")).get("resource_budget"))
        limits = _dict(budget_dim.get("limits"))
        if any(value is not None for value in limits.values()):
            budget_limits.append(limits)
    budget_text = _display(budget_limits[0]) if budget_limits else "not_configured"

    lines = [
        f"# {suite_label} Timing-Usage-Cost 明细",
        "",
        "> 来源：当前 live CanonicalExecutionRecord（CER）确定性投影。",
        "> `engine_ms` 已包含 `engine_init_ms`；两者分别展示，不相加作为总耗时。",
        "> `service_unaccounted_ms = service_total_ms - queue_wait_ms - engine_ms`；`engine_observed_components_ms` 仅用于观察已记录的 engine 内部组件。",
        "> 当前 CER 未记录独立 `merge_ms` / `build_response_ms` 时保留 `not_observed`；rerank 关闭时记为 `not_applicable`。",
        "",
        "## 0. 运行信息",
        "",
        f"- profile: {profile}",
        f"- cases: {len(records)}",
        f"- run_id: {_display(run_ids)}",
        f"- index_build_id: {build_id}",
        f"- generator: {_display(generator_models)}",
        f"- sufficiency_judge: {_display(judge_models)}",
        f"- cost_estimation_coverage: {_display([f'{key}={value}' for key, value in sorted(cost_coverages.items())])}",
        f"- price_table_version: {_display(price_versions)}",
        f"- provider_billing_reconciled: {_display(billing_reconciled)}",
        f"- resource_budget: {budget_text}",
        "",
        "## 1. 分布摘要",
        "",
        "| 类型 | 分布 |",
        "| :-- | :-- |",
        f"| route | {'；'.join(f'{key}: {value}' for key, value in sorted(route_counts.items()))} |",
        f"| final_status | {'；'.join(f'{key}: {value}' for key, value in sorted(status_counts.items()))} |",
        f"| model_role | {'；'.join(f'{key}: {value}' for key, value in sorted(role_counts.items()))} |",
        f"| provider | {'；'.join(f'{key}: {value}' for key, value in sorted(provider_counts.items()))} |",
        f"| model | {'；'.join(f'{key}: {value}' for key, value in sorted(model_counts.items()))} |",
        f"| upstream_provider | {'；'.join(f'{key}: {value}' for key, value in sorted(upstream_counts.items())) if upstream_counts else NOT_OBSERVED} |",
        f"| usage ledger | full={full_ledgers}/{len(records)} |",
        "",
        "## 2. Timing 总体逐题表",
        "",
        "| qid | route | status | service_total_ms | engine_ms | pipeline_total_ms | engine_init_ms | queue_wait_ms | observed_model_ms | retrieval_ms | engine_observed_components_ms | service_unaccounted_ms | tokens | cost_usd |",
        "| :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |",
    ]
    for row in timing_rows:
        lines.append(
            f"| {_display(row['qid'])} | {_display(row['route'])} | {_display(row['status'])} | "
            f"{_fmt_ms(row['service_total_ms'])} | {_fmt_ms(row['engine_ms'])} | {_fmt_ms(row['pipeline_total_ms'])} | "
            f"{_fmt_ms(row['engine_init_ms'])} | {_fmt_ms(row['queue_wait_ms'])} | {_fmt_ms(row['observed_model_ms'])} | "
            f"{_fmt_ms(row['retrieval_ms'])} | {_fmt_ms(row['engine_observed_components_ms'])} | "
            f"{_fmt_ms(row['service_unaccounted_ms'])} | {_fmt_tokens(row['tokens'])} | {_fmt_cost(row['cost_usd'])} |"
        )

    lines.extend([
        "",
        "## 3. Timing 阶段明细表",
        "",
        "| qid | engine_init_ms | decompose_ms | rewrite_ms | retrieve_total_ms | first_retrieve_ms | second_retrieve_ms | merge_ms | rerank_ms | first_suff_ms | second_suff_ms | generate_ms | generator_llm_ms | build_response_ms |",
        "| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |",
    ])
    for row in stage_rows:
        lines.append(
            f"| {_display(row['qid'])} | {_fmt_ms(row['engine_init_ms'])} | {_fmt_ms(row['decompose_ms'])} | "
            f"{_fmt_ms(row['rewrite_ms'])} | {_fmt_ms(row['retrieve_total_ms'])} | {_fmt_ms(row['first_retrieve_ms'])} | "
            f"{_fmt_ms(row['second_retrieve_ms'])} | {_fmt_ms(row['merge_ms'])} | {_fmt_ms(row['rerank_ms'])} | "
            f"{_fmt_ms(row['first_suff_ms'])} | {_fmt_ms(row['second_suff_ms'])} | {_fmt_ms(row['generate_ms'])} | "
            f"{_fmt_ms(row['generator_llm_ms'])} | {_fmt_ms(row['build_response_ms'])} |"
        )

    lines.extend([
        "",
        "## 4. Token / Usage 汇总表",
        "",
        "| qid | route | status | full_ledger | expected_roles | observed_roles | missing_roles | calls | prompt_tokens | completion_tokens | reasoning_tokens | cached_tokens | cache_write_tokens | total_tokens | observed_model_ms | generator_llm_ms | cost_usd |",
        "| :-- | :-- | :-- | :--: | :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |",
    ])
    for row in usage_rows:
        lines.append(
            f"| {_display(row['qid'])} | {_display(row['route'])} | {_display(row['status'])} | {_display(row['full_ledger'])} | "
            f"{'；'.join(row['expected_roles']) if row['expected_roles'] else NOT_APPLICABLE} | "
            f"{'；'.join(row['observed_roles']) if row['observed_roles'] else NOT_OBSERVED} | "
            f"{'；'.join(row['missing_roles']) if row['missing_roles'] else NOT_APPLICABLE} | "
            f"{row['model_calls']} | {_fmt_tokens(row['prompt_tokens'])} | {_fmt_tokens(row['completion_tokens'])} | "
            f"{_fmt_tokens(row['reasoning_tokens'])} | {_fmt_tokens(row['cached_tokens'])} | {_fmt_tokens(row['cache_write_tokens'])} | "
            f"{_fmt_tokens(row['total_tokens'])} | {_fmt_ms(row['observed_model_ms'])} | {_fmt_ms(row['generator_llm_ms'])} | {_fmt_cost(row['cost_usd'])} |"
        )

    lines.extend([
        "",
        "## 5. Model-call 明细",
        "",
        "| qid | idx | role | stage | provider | model | upstream | latency_ms | prompt_tokens | completion_tokens | reasoning_tokens | cached_tokens | total_tokens | cost_usd | timeout | api_error | error_type |",
        "| :-- | --: | :-- | :-- | :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | --: | :--: | :--: | :-- |",
    ])
    for qid, call in calls:
        lines.append(
            f"| {qid} | {_display(call.get('index'))} | {_display(call.get('role'))} | {_display(call.get('stage'))} | "
            f"{_display(call.get('provider'))} | {_display(call.get('resolved_model'))} | {_display(call.get('upstream_provider'))} | "
            f"{_fmt_ms(call.get('latency_ms'))} | {_fmt_tokens(call.get('prompt_tokens'))} | {_fmt_tokens(call.get('completion_tokens'))} | "
            f"{_fmt_tokens(call.get('reasoning_tokens'))} | {_fmt_tokens(call.get('cached_tokens'))} | {_fmt_tokens(call.get('total_tokens'))} | "
            f"{_fmt_cost(call.get('estimated_cost_usd'))} | {_display(call.get('timeout'))} | {_display(call.get('api_error'))} | {_display(call.get('error_type') or NOT_APPLICABLE)} |"
        )

    role_rows = _role_summary_rows(records)
    lines.extend([
        "",
        "## 6. Model role 汇总",
        "",
        "| role | calls | total_ms | median_ms | total_tokens | token observed/unknown | cost_usd | cost observed/unknown |",
        "| :-- | --: | --: | --: | --: | :-- | --: | :-- |",
    ])
    for row in role_rows:
        lines.append(
            f"| {_display(row['role'])} | {row['calls']} | {_fmt_ms(row['total_ms'])} | {_fmt_ms(row['median_ms'])} | "
            f"{_fmt_tokens(row['total_tokens'])} | {_fmt_tokens(row['total_tokens_observed_sum'])}/{row['token_unknown_calls']} | "
            f"{_fmt_cost(row['cost_usd'])} | {_fmt_cost(row['cost_usd_observed_sum'])}/{row['cost_unknown_calls']} |"
        )

    def _top(rows: Sequence[dict[str, Any]], field: str, count: int = 5) -> list[dict[str, Any]]:
        return sorted(
            [row for row in rows if _number(row.get(field)) is not None],
            key=lambda row: _number(row.get(field)) or 0.0,
            reverse=True,
        )[:count]

    slowest = _top(timing_rows, "service_total_ms")
    token_top = _top(usage_rows, "total_tokens")
    cost_top = _top(usage_rows, "cost_usd")
    init_top = [row for row in _top(timing_rows, "engine_init_ms") if (_number(row.get("engine_init_ms")) or 0.0) >= 100.0]
    unaccounted_top = [
        row
        for row in _top(timing_rows, "service_unaccounted_ms")
        if (_number(row.get("service_unaccounted_ms")) or 0.0) >= 100.0
    ]

    slowest_text = ", ".join(f"{row['qid']}={_fmt_ms(row['service_total_ms'])}ms" for row in slowest) if slowest else "none"
    token_top_text = ", ".join(f"{row['qid']}={_fmt_tokens(row['total_tokens'])}" for row in token_top) if token_top else "none"
    cost_top_text = ", ".join(f"{row['qid']}=${_fmt_cost(row['cost_usd'])}" for row in cost_top) if cost_top else "none"
    init_top_text = ", ".join(f"{row['qid']}={_fmt_ms(row['engine_init_ms'])}ms" for row in init_top) if init_top else "none"
    unaccounted_top_text = ", ".join(f"{row['qid']}={_fmt_ms(row['service_unaccounted_ms'])}ms" for row in unaccounted_top) if unaccounted_top else "none"

    lines.extend([
        "",
        "## 7. 批次分析",
        "",
        f"- service latency min / median / p95 / max / total ms: {_fmt_ms(min(service_values) if service_values else None)} / {_fmt_ms(statistics.median(service_values) if service_values else None)} / {_fmt_ms(_percentile(service_values, .95))} / {_fmt_ms(max(service_values) if service_values else None)} / {_fmt_ms(sum(service_values) if service_values else None)}",
        f"- model_call_count: {len(calls)}",
        f"- total_tokens: {_fmt_tokens(sum(token_values) if not token_unknown_records else NOT_OBSERVED)}",
        f"- total_tokens observed subtotal / unknown records: {_fmt_tokens(sum(token_values))} / {token_unknown_records}",
        f"- total_estimated_cost_usd: {_fmt_cost(sum(cost_values) if not cost_unknown_records else NOT_OBSERVED)}",
        f"- estimated cost observed subtotal / unknown records: {_fmt_cost(sum(cost_values))} / {cost_unknown_records}",
        f"- slowest_cases: {slowest_text}",
        f"- highest_token_cases: {token_top_text}",
        f"- highest_cost_cases: {cost_top_text}",
        f"- engine_init_outliers (>=100ms): {init_top_text}",
        f"- unaccounted_outliers (>=100ms): {unaccounted_top_text}",
        "",
        "### 口径说明",
        "",
        "- `service_total_ms`：应用服务本题总耗时。",
        "- `engine_ms`：engine 执行总耗时，已包含 `engine_init_ms`；`pipeline_total_ms`：pipeline 内部总耗时。",
        "- `observed_model_ms`：所有已记录 model call latency 的合计；它是调用观测总量，不代表 provider 并发情况下的关键路径耗时。",
        "- `engine_observed_components_ms = engine_init_ms + retrieval_ms + observed_model_ms`，仅用于组件覆盖观察。",
        "- `service_unaccounted_ms = service_total_ms - queue_wait_ms - engine_ms`，用于观察 service 层剩余开销。",
        "- `decompose_ms`：当前 CER 没有独立 decompose stage timer，直接使用已观测 `subquery_generator` model-call latency；未发生 DECOMPOSE 时为 `not_applicable`。",
        "- `merge_ms` / `build_response_ms`：当前 CER 未独立记录时保留 `not_observed`，不从总耗时反推。",
        "- `rerank_ms`：本轮 rerank 全局关闭，因此为 `not_applicable`。",
        "- cost 为静态价格表估算值；`provider_billing_reconciled=false` 时不等同于供应商账单实扣。",
        "",
    ])
    return "\n".join(lines)


def _performance_markdown(
    records: Sequence[CanonicalExecutionRecord],
    *,
    suite_label: str,
) -> str:
    latencies = [
        value
        for record in records
        if (value := _number(record.timing.get("service_total_ms", record.timing.get("actual_total_ms"))))
        is not None
    ]
    token_values = [value for record in records if (value := _number(record.usage.get("total_tokens"))) is not None]
    costs = [value for record in records if (value := _number(record.usage.get("estimated_cost_usd"))) is not None]
    token_unknown_records = len(records) - len(token_values)
    cost_unknown_records = len(records) - len(costs)
    calls = [call for record in records for call in record.model_calls]
    role_counts = Counter(str(call.get("role")) for call in calls)
    provider_counts = Counter(str(call.get("provider")) for call in calls)
    model_counts = Counter(str(call.get("resolved_model")) for call in calls)
    lines = [
        f"# {suite_label} Performance, Token and Cost Summary",
        "",
        f"- latency observed: {len(latencies)}/{len(records)}",
        f"- latency min/median/p95/max/total ms: {_display(min(latencies) if latencies else None)} / {_display(statistics.median(latencies) if latencies else None)} / {_display(_percentile(latencies, .95))} / {_display(max(latencies) if latencies else None)} / {_display(sum(latencies) if latencies else None)}",
        f"- model call count: {len(calls)}",
        f"- total tokens: {_display(sum(token_values) if not token_unknown_records else None)}; observed subtotal={_display(sum(token_values))}; unknown records={token_unknown_records}",
        f"- estimated cost observed: {len(costs)}/{len(records)}; total={_display(sum(costs) if not cost_unknown_records else None)}; observed subtotal={_display(sum(costs))}",
        f"- by role: {_display([f'{k}={v}' for k, v in sorted(role_counts.items())])}",
        f"- by provider: {_display([f'{k}={v}' for k, v in sorted(provider_counts.items())])}",
        f"- by model: {_display([f'{k}={v}' for k, v in sorted(model_counts.items())])}",
        "",
        "> Estimated cost comes from the CER/static price table when available; missing prices remain `not_observed`.",
        "",
    ]
    return "\n".join(lines)


def build_evaluation_reports(
    records: Iterable[CanonicalExecutionRecord],
    output_dir: str | Path,
    *,
    suite_label: str = "Evaluation",
) -> dict[str, Path]:
    """为任意项目评估集写出确定性的 CER 报告投影。"""
    items = list(records)
    report_items = [_report_record(record) for record in items]
    label = _suite_label(suite_label)
    prefix = _suite_prefix(label)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = Path(output_dir)
    summaries = output / "summaries"
    tables = output / "tables"
    raw = output / "raw"
    for directory in (summaries, tables, raw):
        directory.mkdir(parents=True, exist_ok=True)

    rows = [_record_row(record) for record in report_items]
    paths = {
        "summary": summaries / "final_regression_summary.md",
        "per_question": summaries / f"{prefix}-逐题运行报告-{timestamp}.md",
        "retrieval_signal": summaries / f"{prefix}-检索信号摘要-{timestamp}.md",
        "retrieval_source_distribution": summaries / f"{prefix}-运行检索来源分布-{timestamp}.md",
        "retrieval_workflow": summaries / f"{prefix}-检索工作流明细-{timestamp}.md",
        "timing_usage_cost": summaries / f"{prefix}-Timing-Usage-Cost明细-{timestamp}.md",
        "performance": summaries / "performance_cost_summary.md",
        "cases": tables / "final_regression_cases.csv",
        "retrieval_signal_csv": tables / "retrieval_signal_summary.csv",
        "retrieval_source_by_case_csv": tables / "retrieval_source_distribution_by_case.csv",
        "retrieval_source_by_source_csv": tables / "retrieval_source_distribution_by_source.csv",
        "timing": tables / "timing_by_case.csv",
        "model_calls": tables / "model_calls.csv",
        "cost": tables / "cost_ledger.csv",
        "cer": raw / "canonical_records.jsonl",
        "sanitized_cer": raw / "canonical_records.sanitized.jsonl",
        "readme": output / "README.md",
    }
    paths["summary"].write_text(
        _summary_markdown(report_items, rows, suite_label=label),
        encoding="utf-8",
    )
    paths["per_question"].write_text(
        _per_question_markdown(report_items, suite_label=label),
        encoding="utf-8",
    )
    signal_rows = [_retrieval_signal_row(record) for record in report_items]
    paths["retrieval_signal"].write_text(
        _retrieval_signal_markdown(report_items, signal_rows, suite_label=label),
        encoding="utf-8",
    )
    source_case_rows = [_source_distribution_case_row(record) for record in report_items]
    source_summary_rows = _source_distribution_summary_rows(report_items)
    paths["retrieval_source_distribution"].write_text(
        _retrieval_source_distribution_markdown(
            report_items,
            source_summary_rows,
            suite_label=label,
        ),
        encoding="utf-8",
    )
    paths["retrieval_workflow"].write_text(
        _retrieval_workflow_markdown(report_items, suite_label=label),
        encoding="utf-8",
    )
    paths["timing_usage_cost"].write_text(
        _timing_usage_cost_markdown(report_items, suite_label=label),
        encoding="utf-8",
    )
    paths["performance"].write_text(
        _performance_markdown(report_items, suite_label=label),
        encoding="utf-8",
    )

    _write_csv(paths["cases"], rows, list(rows[0]) if rows else ["qid"])
    signal_csv_rows = [
        {key: value for key, value in row.items() if not key.startswith("_")}
        for row in signal_rows
    ]
    _write_csv(
        paths["retrieval_signal_csv"],
        signal_csv_rows,
        list(signal_csv_rows[0]) if signal_csv_rows else ["qid"],
    )
    _write_csv(
        paths["retrieval_source_by_case_csv"],
        source_case_rows,
        list(source_case_rows[0]) if source_case_rows else ["qid"],
    )
    _write_csv(
        paths["retrieval_source_by_source_csv"],
        source_summary_rows,
        list(source_summary_rows[0]) if source_summary_rows else ["source_id"],
    )
    timing_rows = [
        {"qid": record.identity.get("qid"), **record.timing, **_dict(record.timing.get("steps"))}
        for record in report_items
    ]
    timing_fields = sorted({key for row in timing_rows for key in row if key != "steps"})
    _write_csv(paths["timing"], timing_rows, timing_fields or ["qid"])
    call_rows = []
    for record in report_items:
        for call in record.model_calls:
            call_rows.append({"qid": record.identity.get("qid"), **call})
    call_fields = [
        "qid", "index", "role", "stage", "provider", "configured_model", "resolved_model",
        "latency_ms", "prompt_tokens", "completion_tokens", "reasoning_tokens", "cached_tokens",
        "cache_write_tokens", "total_tokens", "estimated_cost_usd", "timeout", "api_error",
        "error_type", "fallback_used",
    ]
    _write_csv(paths["model_calls"], call_rows, call_fields)
    cost_rows = [
        {
            "qid": record.identity.get("qid"),
            "model_call_count": len(record.model_calls),
            "total_tokens": record.usage.get("total_tokens", NOT_OBSERVED),
            "estimated_cost_usd": record.usage.get("estimated_cost_usd", NOT_OBSERVED),
            "cost_observation": "observed"
            if _number(record.usage.get("estimated_cost_usd")) is not None
            else NOT_OBSERVED,
        }
        for record in report_items
    ]
    _write_csv(paths["cost"], cost_rows, list(cost_rows[0]) if cost_rows else ["qid"])

    paths["cer"].write_text(
        "".join(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True) + "\n" for record in items),
        encoding="utf-8",
    )
    paths["sanitized_cer"].write_text(
        "".join(json.dumps(record.sanitized_dict(), ensure_ascii=False, sort_keys=True) + "\n" for record in items),
        encoding="utf-8",
    )
    paths["readme"].write_text(
        f"# {label} CER Report Pack\n\n"
        "Generated deterministically from CanonicalExecutionRecord. The `raw/canonical_records.jsonl` "
        "file is internal; use `raw/canonical_records.sanitized.jsonl` for release preparation.\n\n"
        "Human-readable reports include the per-question run report, retrieval signal summary, "
        "retrieval source distribution, retrieval workflow detail, Timing-Usage-Cost detail, "
        "and performance/cost summary.\n\n"
        f"Cases: {len(items)}. Model calls: {len(call_rows)}.\n",
        encoding="utf-8",
    )
    return paths


__all__ = ["build_evaluation_reports"]
