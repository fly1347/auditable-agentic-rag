#!/usr/bin/env python3
"""Compare the frozen baseline and orchestrated final-evaluation bundles.

This is a zero-provider-call projection over already-produced machine records.  It
compares online behavior/resources, sufficiency-judge overhead, D-full signals,
RAGAS scores/grade migrations, and the three-category evaluation ledger.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional, Sequence

from eval.run_ragas_from_cer import RAGAS_SEGMENT_DISPLAY, _grade_ragas_metric


METRICS = ("context_precision", "faithfulness", "answer_relevancy")
GRADE_ORDER = {"A": 0, "B": 1, "C": 2, "D": 3}
UNCERTAINTY_ORDER = {"low": 0, "medium": 1, "high": 2}
GRADE_DISPLAY = {"A": "A", "B": "B", "C": "C", "D": "D", "": "—"}
CATEGORY_DISPLAY = {
    "online": "在线主链",
    "offline_dfull": "D-full 后置评测",
    "ragas": "RAGAS 离线质量评测",
    "combined": "三类合计",
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="compare_final_evaluations")
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--orchestrated-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return json.loads(path.read_text(encoding="utf-8"))


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _optional_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _sum_known(values: Iterable[Any]) -> Optional[float]:
    parsed = [_optional_float(value) for value in values]
    if any(value is None for value in parsed):
        return None
    return sum(value for value in parsed if value is not None)


def _safe_sum(values: Iterable[Any]) -> float:
    return sum(value for value in (_optional_float(v) for v in values) if value is not None)


def _mean(values: Sequence[float]) -> Optional[float]:
    return statistics.fmean(values) if values else None


def _median(values: Sequence[float]) -> Optional[float]:
    return statistics.median(values) if values else None


def _p95(values: Sequence[float]) -> Optional[float]:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, math.ceil(len(ordered) * 0.95) - 1)
    return ordered[index]


def _fmt_int(value: Any) -> str:
    number = _optional_int(value)
    return "not_observed" if number is None else f"{number:,}"


def _fmt_float(value: Any, digits: int = 3) -> str:
    number = _optional_float(value)
    return "not_observed" if number is None else f"{number:,.{digits}f}"


def _fmt_score(value: Any) -> str:
    number = _optional_float(value)
    return "—" if number is None else f"{number:.4f}"


def _fmt_cost(value: Any) -> str:
    number = _optional_float(value)
    return "not_observed" if number is None else f"${number:.6f}"


def _fmt_seconds_from_ms(value: Any) -> str:
    number = _optional_float(value)
    return "not_observed" if number is None else f"{number / 1000.0:,.3f} s"


def _fmt_delta(value: Optional[float], *, digits: int = 4, unit: str = "") -> str:
    if value is None:
        return "—"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{digits}f}{unit}"


def _fmt_pct_delta(baseline: Any, orchestrated: Any) -> str:
    left = _optional_float(baseline)
    right = _optional_float(orchestrated)
    if left is None or right is None or left == 0:
        return "—"
    delta = (right - left) / left * 100.0
    sign = "+" if delta > 0 else ""
    return f"{sign}{delta:.1f}%"


def _qids_text(qids: Sequence[str]) -> str:
    return "、".join(qids) if qids else "无"


def _profile_from_canonical(records: Sequence[Mapping[str, Any]]) -> str:
    profiles = {
        str((record.get("provenance") or {}).get("profile") or "").strip()
        for record in records
    }
    profiles.discard("")
    if len(profiles) != 1:
        raise ValueError(f"expected exactly one profile in canonical records, got {sorted(profiles)}")
    return next(iter(profiles))


def _bundle(root: Path) -> dict[str, Any]:
    canonical = _read_jsonl(root / "canonical_records.jsonl")
    dfull = _read_jsonl(root / "offline_dfull" / "offline_dfull_records.jsonl")
    ragas = _read_jsonl(root / "ragas_results" / "ragas_evaluation_records.jsonl")
    prepare_manifest = _read_json(root / "ragas_prepare" / "ragas_prepare_manifest.json")
    ledger = _read_csv(root / "evaluation_ledger" / "evaluation_totals.csv")
    profile = _profile_from_canonical(canonical)
    return {
        "root": root,
        "profile": profile,
        "canonical": canonical,
        "dfull": dfull,
        "ragas": ragas,
        "prepare_manifest": prepare_manifest,
        "ledger": ledger,
    }


def _canonical_map(records: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {
        str((record.get("identity") or {}).get("qid") or ""): record
        for record in records
        if str((record.get("identity") or {}).get("qid") or "")
    }


def _dfull_map(records: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {
        str((record.get("identity") or {}).get("qid") or ""): record
        for record in records
        if str((record.get("identity") or {}).get("qid") or "")
    }


def _ragas_matrix(records: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Mapping[str, Any]]]:
    matrix: dict[str, dict[str, Mapping[str, Any]]] = {}
    for record in records:
        qid = str(record.get("qid") or "")
        metric = str(record.get("metric") or "")
        if qid and metric:
            matrix.setdefault(qid, {})[metric] = record
    return matrix


def _ledger_map(rows: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    return {str(row.get("category") or ""): row for row in rows if str(row.get("category") or "")}


def _main_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    qids = [str((record.get("identity") or {}).get("qid") or "") for record in records]
    route_counter: Counter[str] = Counter()
    status_counter: Counter[str] = Counter()
    refusal_qids: list[str] = []
    second_round_qids: list[str] = []
    insufficient_qids: list[str] = []
    service_values: list[float] = []
    prompt_evidence_fail_qids: list[str] = []

    for record in records:
        qid = str((record.get("identity") or {}).get("qid") or "")
        route_counter[str((record.get("route") or {}).get("actual_route") or "not_observed")] += 1
        status = str((record.get("outcome") or {}).get("status") or "not_observed")
        status_counter[status] += 1
        if status == "REFUSED":
            refusal_qids.append(qid)
        sufficiency = record.get("sufficiency") or {}
        if sufficiency.get("second") not in (None, ""):
            second_round_qids.append(qid)
        final_verdict = sufficiency.get("second") or sufficiency.get("first")
        if final_verdict != "SUFFICIENT":
            insufficient_qids.append(qid)
        value = _optional_float((record.get("timing") or {}).get("service_total_ms"))
        if value is not None:
            service_values.append(value)
        prompt_status = (
            ((record.get("evaluation") or {}).get("dimensions") or {}).get("prompt_evidence") or {}
        ).get("status")
        if prompt_status == "fail":
            prompt_evidence_fail_qids.append(qid)

    total_calls = sum(_optional_int((record.get("usage") or {}).get("model_call_count")) or 0 for record in records)
    total_tokens = sum(_optional_int((record.get("usage") or {}).get("total_tokens")) or 0 for record in records)
    total_cost = sum(_optional_float((record.get("usage") or {}).get("estimated_cost_usd")) or 0.0 for record in records)

    return {
        "cases": len(qids),
        "routes": dict(route_counter),
        "statuses": dict(status_counter),
        "refusal_qids": refusal_qids,
        "second_round_qids": second_round_qids,
        "insufficient_qids": insufficient_qids,
        "prompt_evidence_fail_qids": prompt_evidence_fail_qids,
        "service_sum_ms": sum(service_values),
        "service_mean_ms": _mean(service_values),
        "service_median_ms": _median(service_values),
        "service_p95_ms": _p95(service_values),
        "model_calls": total_calls,
        "total_tokens": total_tokens,
        "estimated_cost_usd": total_cost,
    }


def _sufficiency_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    modes: Counter[str] = Counter()
    calls: list[Mapping[str, Any]] = []
    second_round_qids: list[str] = []
    insufficient_qids: list[str] = []
    for record in records:
        qid = str((record.get("identity") or {}).get("qid") or "")
        suff = record.get("sufficiency") or {}
        first_contract = suff.get("first_contract") or {}
        second_contract = suff.get("second_contract") or {}
        mode = str((second_contract or first_contract).get("mode") or "not_observed")
        modes[mode] += 1
        if suff.get("second") not in (None, ""):
            second_round_qids.append(qid)
        final_verdict = suff.get("second") or suff.get("first")
        if final_verdict != "SUFFICIENT":
            insufficient_qids.append(qid)
        for call in list(record.get("model_calls") or []):
            if isinstance(call, Mapping) and str(call.get("role") or "") == "sufficiency_judge":
                calls.append(call)

    return {
        "modes": dict(modes),
        "judge_call_count": len(calls),
        "second_round_qids": second_round_qids,
        "insufficient_qids": insufficient_qids,
        "provider_latency_ms": _safe_sum(call.get("latency_ms") for call in calls),
        "prompt_tokens": sum(_optional_int(call.get("prompt_tokens")) or 0 for call in calls),
        "completion_tokens": sum(_optional_int(call.get("completion_tokens")) or 0 for call in calls),
        "total_tokens": sum(_optional_int(call.get("total_tokens")) or 0 for call in calls),
        "estimated_cost_usd": sum(_optional_float(call.get("estimated_cost_usd")) or 0.0 for call in calls),
    }


def _online_role_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for record in records:
        for call in list(record.get("model_calls") or []):
            if not isinstance(call, Mapping):
                continue
            role = str(call.get("role") or "not_observed")
            row = grouped.setdefault(
                role,
                {
                    "model_call_count": 0,
                    "total_tokens": 0,
                    "estimated_cost_usd": 0.0,
                    "provider_latency_ms": 0.0,
                },
            )
            row["model_call_count"] += 1
            row["total_tokens"] += _optional_int(call.get("total_tokens")) or 0
            row["estimated_cost_usd"] += _optional_float(call.get("estimated_cost_usd")) or 0.0
            row["provider_latency_ms"] += _optional_float(call.get("latency_ms")) or 0.0
    return grouped


def _dfull_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    citation: Counter[str] = Counter()
    uncertainty: Counter[str] = Counter()
    uncertainty_qids: dict[str, list[str]] = {}
    unsupported_claim_qids: list[str] = []
    conflict_qids: list[str] = []
    for record in records:
        qid = str((record.get("identity") or {}).get("qid") or "")
        outcome = record.get("outcome") or {}
        citation[str(outcome.get("citation_support_label") or "not_observed")] += 1
        uncertainty_level = str(outcome.get("uncertainty_level") or "not_observed")
        uncertainty[uncertainty_level] += 1
        uncertainty_qids.setdefault(uncertainty_level, []).append(qid)
        if (_optional_int(outcome.get("unsupported_claim_count")) or 0) > 0:
            unsupported_claim_qids.append(qid)
        if (_optional_int(outcome.get("conflict_count")) or 0) > 0:
            conflict_qids.append(qid)
    return {
        "citation": dict(citation),
        "uncertainty": dict(uncertainty),
        "uncertainty_qids": {key: sorted(value) for key, value in uncertainty_qids.items()},
        "unsupported_claim_qids": unsupported_claim_qids,
        "conflict_qids": conflict_qids,
    }


def _uncertainty_migrations(per_case: Sequence[Mapping[str, Any]]) -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = {"improved": [], "same": [], "worse": []}
    for row in per_case:
        qid = str(row.get("qid") or "")
        baseline = str(row.get("baseline_uncertainty") or "")
        orchestrated = str(row.get("orchestrated_uncertainty") or "")
        if baseline not in UNCERTAINTY_ORDER or orchestrated not in UNCERTAINTY_ORDER:
            continue
        item = {"qid": qid, "baseline": baseline, "orchestrated": orchestrated}
        if UNCERTAINTY_ORDER[orchestrated] < UNCERTAINTY_ORDER[baseline]:
            result["improved"].append(item)
        elif UNCERTAINTY_ORDER[orchestrated] > UNCERTAINTY_ORDER[baseline]:
            result["worse"].append(item)
        else:
            result["same"].append(item)
    return result


def _ragas_scores(matrix: Mapping[str, Mapping[str, Mapping[str, Any]]], metric: str) -> dict[str, float]:
    out: dict[str, float] = {}
    for qid, metric_map in matrix.items():
        record = metric_map.get(metric)
        if not record or str(record.get("status") or "") != "ok":
            continue
        score = _optional_float(record.get("score"))
        if score is not None:
            out[qid] = score
    return out


def _ragas_profile_summary(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    matrix = _ragas_matrix(records)
    metrics: dict[str, Any] = {}
    for metric in METRICS:
        scores = _ragas_scores(matrix, metric)
        metrics[metric] = {
            "count": len(scores),
            "mean": _mean(list(scores.values())),
            "median": _median(list(scores.values())),
            "scores": scores,
        }
    qids = sorted({str(record.get("qid") or "") for record in records if str(record.get("qid") or "")})
    return {"qids": qids, "metrics": metrics, "matrix": matrix}


def _ragas_matched_comparison(
    baseline_records: Sequence[Mapping[str, Any]],
    orchestrated_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    baseline = _ragas_profile_summary(baseline_records)
    orchestrated = _ragas_profile_summary(orchestrated_records)
    result: dict[str, Any] = {"metrics": {}}

    for metric in METRICS:
        b_scores = dict(baseline["metrics"][metric]["scores"])
        o_scores = dict(orchestrated["metrics"][metric]["scores"])
        shared = sorted(set(b_scores) & set(o_scores))
        b_values = [b_scores[qid] for qid in shared]
        o_values = [o_scores[qid] for qid in shared]
        deltas = {qid: o_scores[qid] - b_scores[qid] for qid in shared}

        migrations: dict[str, list[str]] = {"improved": [], "same": [], "worse": []}
        transitions: Counter[str] = Counter()
        grades: dict[str, dict[str, str]] = {}
        for qid in shared:
            b_grade = _grade_ragas_metric(metric, b_scores[qid])
            o_grade = _grade_ragas_metric(metric, o_scores[qid])
            grades[qid] = {"baseline": b_grade, "orchestrated": o_grade}
            transitions[f"{b_grade}->{o_grade}"] += 1
            if GRADE_ORDER.get(o_grade, 99) < GRADE_ORDER.get(b_grade, 99):
                migrations["improved"].append(qid)
            elif GRADE_ORDER.get(o_grade, 99) > GRADE_ORDER.get(b_grade, 99):
                migrations["worse"].append(qid)
            else:
                migrations["same"].append(qid)

        positive = {qid: value for qid, value in deltas.items() if value > 0}
        negative = {qid: value for qid, value in deltas.items() if value < 0}
        result["metrics"][metric] = {
            "shared_qids": shared,
            "baseline_mean": _mean(b_values),
            "orchestrated_mean": _mean(o_values),
            "mean_delta": (_mean(o_values) - _mean(b_values)) if shared else None,
            "deltas": deltas,
            "grades": grades,
            "migrations": migrations,
            "transitions": dict(transitions),
            "top_gains": sorted(positive, key=positive.get, reverse=True)[:5],
            "top_losses": sorted(negative, key=negative.get)[:5],
        }

    all_shared = sorted(set(baseline["qids"]) & set(orchestrated["qids"]))
    result["shared_ragas_qids"] = all_shared
    result["baseline_only_qids"] = sorted(set(baseline["qids"]) - set(orchestrated["qids"]))
    result["orchestrated_only_qids"] = sorted(set(orchestrated["qids"]) - set(baseline["qids"]))
    result["baseline_profile"] = baseline
    result["orchestrated_profile"] = orchestrated
    return result


def _skipped_rows(manifest: Mapping[str, Any]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for item in list(manifest.get("skipped") or []):
        if isinstance(item, Mapping):
            rows.append({"qid": str(item.get("qid") or ""), "reason": str(item.get("reason") or "")})
    return rows


def _ledger_value(row: Mapping[str, Any], key: str) -> Optional[float]:
    return _optional_float(row.get(key))


def _per_case_rows(baseline: Mapping[str, Any], orchestrated: Mapping[str, Any]) -> list[dict[str, Any]]:
    b_can = _canonical_map(baseline["canonical"])
    o_can = _canonical_map(orchestrated["canonical"])
    b_dfull = _dfull_map(baseline["dfull"])
    o_dfull = _dfull_map(orchestrated["dfull"])
    b_ragas = _ragas_matrix(baseline["ragas"])
    o_ragas = _ragas_matrix(orchestrated["ragas"])
    qids = sorted(set(b_can) | set(o_can))
    rows: list[dict[str, Any]] = []

    for qid in qids:
        b = b_can.get(qid, {})
        o = o_can.get(qid, {})
        b_out = b.get("outcome") or {}
        o_out = o.get("outcome") or {}
        b_suff = b.get("sufficiency") or {}
        o_suff = o.get("sufficiency") or {}
        b_df_out = (b_dfull.get(qid, {}).get("outcome") or {}) if qid in b_dfull else {}
        o_df_out = (o_dfull.get(qid, {}).get("outcome") or {}) if qid in o_dfull else {}
        row: dict[str, Any] = {
            "qid": qid,
            "query": b.get("query") or o.get("query") or "",
            "baseline_status": b_out.get("status"),
            "orchestrated_status": o_out.get("status"),
            "baseline_route": (b.get("route") or {}).get("actual_route"),
            "orchestrated_route": (o.get("route") or {}).get("actual_route"),
            "baseline_final_sufficiency": b_suff.get("second") or b_suff.get("first"),
            "orchestrated_final_sufficiency": o_suff.get("second") or o_suff.get("first"),
            "baseline_service_total_ms": (b.get("timing") or {}).get("service_total_ms"),
            "orchestrated_service_total_ms": (o.get("timing") or {}).get("service_total_ms"),
            "baseline_total_tokens": (b.get("usage") or {}).get("total_tokens"),
            "orchestrated_total_tokens": (o.get("usage") or {}).get("total_tokens"),
            "baseline_cost_usd": (b.get("usage") or {}).get("estimated_cost_usd"),
            "orchestrated_cost_usd": (o.get("usage") or {}).get("estimated_cost_usd"),
            "baseline_citation_support": b_df_out.get("citation_support_label"),
            "orchestrated_citation_support": o_df_out.get("citation_support_label"),
            "baseline_uncertainty": b_df_out.get("uncertainty_level"),
            "orchestrated_uncertainty": o_df_out.get("uncertainty_level"),
        }
        for metric in METRICS:
            b_rec = b_ragas.get(qid, {}).get(metric, {})
            o_rec = o_ragas.get(qid, {}).get(metric, {})
            b_score = _optional_float(b_rec.get("score")) if b_rec.get("status") == "ok" else None
            o_score = _optional_float(o_rec.get("score")) if o_rec.get("status") == "ok" else None
            row[f"baseline_{metric}"] = b_score
            row[f"orchestrated_{metric}"] = o_score
            row[f"delta_{metric}"] = (o_score - b_score) if b_score is not None and o_score is not None else None
            row[f"baseline_{metric}_grade"] = _grade_ragas_metric(metric, b_score) if b_score is not None else ""
            row[f"orchestrated_{metric}_grade"] = _grade_ragas_metric(metric, o_score) if o_score is not None else ""
        rows.append(row)
    return rows


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _metric_name(metric: str) -> str:
    return RAGAS_SEGMENT_DISPLAY.get(metric, metric)


def _status_change_qids(per_case: Sequence[Mapping[str, Any]]) -> list[str]:
    return [
        str(row.get("qid") or "")
        for row in per_case
        if row.get("baseline_status") != row.get("orchestrated_status")
    ]


def _route_change_qids(per_case: Sequence[Mapping[str, Any]]) -> list[str]:
    return [
        str(row.get("qid") or "")
        for row in per_case
        if row.get("baseline_route") != row.get("orchestrated_route")
    ]


def _markdown(
    baseline: Mapping[str, Any],
    orchestrated: Mapping[str, Any],
    *,
    per_case: Sequence[Mapping[str, Any]],
) -> tuple[str, dict[str, Any]]:
    b_main = _main_summary(baseline["canonical"])
    o_main = _main_summary(orchestrated["canonical"])
    b_suff = _sufficiency_summary(baseline["canonical"])
    o_suff = _sufficiency_summary(orchestrated["canonical"])
    b_roles = _online_role_summary(baseline["canonical"])
    o_roles = _online_role_summary(orchestrated["canonical"])
    b_dfull = _dfull_summary(baseline["dfull"])
    o_dfull = _dfull_summary(orchestrated["dfull"])
    ragas = _ragas_matched_comparison(baseline["ragas"], orchestrated["ragas"])
    b_ledger = _ledger_map(baseline["ledger"])
    o_ledger = _ledger_map(orchestrated["ledger"])
    b_skipped = _skipped_rows(baseline["prepare_manifest"])
    o_skipped = _skipped_rows(orchestrated["prepare_manifest"])
    status_changes = _status_change_qids(per_case)
    route_changes = _route_change_qids(per_case)
    uncertainty_migrations = _uncertainty_migrations(per_case)

    b_online_cost = _ledger_value(b_ledger.get("online", {}), "estimated_cost_usd")
    o_online_cost = _ledger_value(o_ledger.get("online", {}), "estimated_cost_usd")
    b_combined_cost = _ledger_value(b_ledger.get("combined", {}), "estimated_cost_usd")
    o_combined_cost = _ledger_value(o_ledger.get("combined", {}), "estimated_cost_usd")

    lines = [
        "# Baseline vs Orchestrated 最终评测对比",
        "",
        "> 本报告只读取两套冻结评测机器底账，零模型调用。RAGAS 同时给出各 profile 原始统计与共同题集（matched cohort）统计；由于 orchestrated 会把证据不足题挡在 RAGAS 之外，跨 profile 质量结论优先看共同题集。",
        "",
        "## 结论先看",
        "",
        "| 观察项 | baseline | orchestrated | 变化 |",
        "| :-- | --: | --: | --: |",
        f"| 在线主链 estimated cost | {_fmt_cost(b_online_cost)} | {_fmt_cost(o_online_cost)} | {_fmt_pct_delta(b_online_cost, o_online_cost)} |",
        f"| 在线主链 total tokens | {_fmt_int(b_main['total_tokens'])} | {_fmt_int(o_main['total_tokens'])} | {_fmt_pct_delta(b_main['total_tokens'], o_main['total_tokens'])} |",
        f"| 在线主链 service time sum | {_fmt_seconds_from_ms(b_main['service_sum_ms'])} | {_fmt_seconds_from_ms(o_main['service_sum_ms'])} | {_fmt_pct_delta(b_main['service_sum_ms'], o_main['service_sum_ms'])} |",
        f"| 最终拒答题 | {len(b_main['refusal_qids'])} | {len(o_main['refusal_qids'])} | {_fmt_delta(float(len(o_main['refusal_qids']) - len(b_main['refusal_qids'])), digits=0)} |",
        f"| 二轮 sufficiency 题 | {len(b_main['second_round_qids'])} | {len(o_main['second_round_qids'])} | {_fmt_delta(float(len(o_main['second_round_qids']) - len(b_main['second_round_qids'])), digits=0)} |",
    ]
    for metric in METRICS:
        item = ragas["metrics"][metric]
        lines.append(
            f"| RAGAS {_metric_name(metric)} 共同题均值 | {_fmt_score(item['baseline_mean'])} | "
            f"{_fmt_score(item['orchestrated_mean'])} | {_fmt_delta(item['mean_delta'])} |"
        )
    lines.extend(
        [
            f"| 全套 evaluation estimated cost | {_fmt_cost(b_combined_cost)} | {_fmt_cost(o_combined_cost)} | {_fmt_pct_delta(b_combined_cost, o_combined_cost)} |",
            "",
            "### 发生控制结果变化的题",
            "",
            f"- 最终 ANSWERED / REFUSED 状态变化：{_qids_text(status_changes)}",
            f"- actual_route 变化：{_qids_text(route_changes)}",
            f"- baseline 最终证据不足：{_qids_text(b_main['insufficient_qids'])}",
            f"- orchestrated 最终证据不足：{_qids_text(o_main['insufficient_qids'])}",
            "",
            "## 1. 主链控制结果",
            "",
            "| signal | baseline | orchestrated |",
            "| :-- | :-- | :-- |",
            f"| cases | {b_main['cases']} | {o_main['cases']} |",
            f"| ANSWERED | {b_main['statuses'].get('ANSWERED', 0)} | {o_main['statuses'].get('ANSWERED', 0)} |",
            f"| REFUSED | {b_main['statuses'].get('REFUSED', 0)}（{_qids_text(b_main['refusal_qids'])}） | {o_main['statuses'].get('REFUSED', 0)}（{_qids_text(o_main['refusal_qids'])}） |",
            f"| DIRECT | {b_main['routes'].get('DIRECT', 0)} | {o_main['routes'].get('DIRECT', 0)} |",
            f"| DECOMPOSE | {b_main['routes'].get('DECOMPOSE', 0)} | {o_main['routes'].get('DECOMPOSE', 0)} |",
            f"| second sufficiency / reretrieve | {len(b_main['second_round_qids'])}（{_qids_text(b_main['second_round_qids'])}） | {len(o_main['second_round_qids'])}（{_qids_text(o_main['second_round_qids'])}） |",
            f"| final insufficiency | {len(b_main['insufficient_qids'])}（{_qids_text(b_main['insufficient_qids'])}） | {len(o_main['insufficient_qids'])}（{_qids_text(o_main['insufficient_qids'])}） |",
            f"| prompt_evidence fail | {len(b_main['prompt_evidence_fail_qids'])}（{_qids_text(b_main['prompt_evidence_fail_qids'])}） | {len(o_main['prompt_evidence_fail_qids'])}（{_qids_text(o_main['prompt_evidence_fail_qids'])}） |",
            "",
            "## 2. 在线主链性能与成本",
            "",
            "> service time 为 30 题逐题 `service_total_ms` 的统计；sum 是题级耗时求和，不等同于批任务真实墙钟时长。",
            "",
            "| metric | baseline | orchestrated | delta / ratio |",
            "| :-- | --: | --: | --: |",
            f"| service time sum | {_fmt_seconds_from_ms(b_main['service_sum_ms'])} | {_fmt_seconds_from_ms(o_main['service_sum_ms'])} | {_fmt_pct_delta(b_main['service_sum_ms'], o_main['service_sum_ms'])} |",
            f"| service time mean | {_fmt_seconds_from_ms(b_main['service_mean_ms'])} | {_fmt_seconds_from_ms(o_main['service_mean_ms'])} | {_fmt_pct_delta(b_main['service_mean_ms'], o_main['service_mean_ms'])} |",
            f"| service time median | {_fmt_seconds_from_ms(b_main['service_median_ms'])} | {_fmt_seconds_from_ms(o_main['service_median_ms'])} | {_fmt_pct_delta(b_main['service_median_ms'], o_main['service_median_ms'])} |",
            f"| service time p95 | {_fmt_seconds_from_ms(b_main['service_p95_ms'])} | {_fmt_seconds_from_ms(o_main['service_p95_ms'])} | {_fmt_pct_delta(b_main['service_p95_ms'], o_main['service_p95_ms'])} |",
            f"| model calls | {_fmt_int(b_main['model_calls'])} | {_fmt_int(o_main['model_calls'])} | {_fmt_pct_delta(b_main['model_calls'], o_main['model_calls'])} |",
            f"| total tokens | {_fmt_int(b_main['total_tokens'])} | {_fmt_int(o_main['total_tokens'])} | {_fmt_pct_delta(b_main['total_tokens'], o_main['total_tokens'])} |",
            f"| estimated cost | {_fmt_cost(b_main['estimated_cost_usd'])} | {_fmt_cost(o_main['estimated_cost_usd'])} | {_fmt_pct_delta(b_main['estimated_cost_usd'], o_main['estimated_cost_usd'])} |",
            "",
            "### 在线模型角色成本分解",
            "",
            "| role | baseline calls | orchestrated calls | baseline tokens | orchestrated tokens | baseline cost | orchestrated cost |",
            "| :-- | --: | --: | --: | --: | --: | --: |",
        ]
    )
    for role in sorted(set(b_roles) | set(o_roles)):
        b_role = b_roles.get(role, {})
        o_role = o_roles.get(role, {})
        lines.append(
            f"| {role} | {_fmt_int(b_role.get('model_call_count'))} | {_fmt_int(o_role.get('model_call_count'))} | "
            f"{_fmt_int(b_role.get('total_tokens'))} | {_fmt_int(o_role.get('total_tokens'))} | "
            f"{_fmt_cost(b_role.get('estimated_cost_usd'))} | {_fmt_cost(o_role.get('estimated_cost_usd'))} |"
        )
    lines.extend(
        [
            "",
            "## 3. Sufficiency Judge 代价",
            "",
            "> 这里只拆主链中 `role=sufficiency_judge` 的真实模型调用；baseline 为 binary，orchestrated 为 structured。",
            "",
            "| metric | baseline | orchestrated | delta / ratio |",
            "| :-- | :-- | :-- | :-- |",
            f"| mode | {'；'.join(f'{k}={v}' for k,v in sorted(b_suff['modes'].items()))} | {'；'.join(f'{k}={v}' for k,v in sorted(o_suff['modes'].items()))} | — |",
            f"| judge calls | {b_suff['judge_call_count']} | {o_suff['judge_call_count']} | {_fmt_pct_delta(b_suff['judge_call_count'], o_suff['judge_call_count'])} |",
            f"| second-round cases | {len(b_suff['second_round_qids'])}（{_qids_text(b_suff['second_round_qids'])}） | {len(o_suff['second_round_qids'])}（{_qids_text(o_suff['second_round_qids'])}） | — |",
            f"| provider latency sum | {_fmt_seconds_from_ms(b_suff['provider_latency_ms'])} | {_fmt_seconds_from_ms(o_suff['provider_latency_ms'])} | {_fmt_pct_delta(b_suff['provider_latency_ms'], o_suff['provider_latency_ms'])} |",
            f"| prompt tokens | {_fmt_int(b_suff['prompt_tokens'])} | {_fmt_int(o_suff['prompt_tokens'])} | {_fmt_pct_delta(b_suff['prompt_tokens'], o_suff['prompt_tokens'])} |",
            f"| completion tokens | {_fmt_int(b_suff['completion_tokens'])} | {_fmt_int(o_suff['completion_tokens'])} | {_fmt_pct_delta(b_suff['completion_tokens'], o_suff['completion_tokens'])} |",
            f"| total tokens | {_fmt_int(b_suff['total_tokens'])} | {_fmt_int(o_suff['total_tokens'])} | {_fmt_pct_delta(b_suff['total_tokens'], o_suff['total_tokens'])} |",
            f"| estimated cost | {_fmt_cost(b_suff['estimated_cost_usd'])} | {_fmt_cost(o_suff['estimated_cost_usd'])} | {_fmt_pct_delta(b_suff['estimated_cost_usd'], o_suff['estimated_cost_usd'])} |",
            "",
            "## 4. D-full 后置诊断",
            "",
            "> D-full classifier 是独立 LLM 后置诊断，不作为 baseline / orchestrated 质量胜负项；这里重点比较与最终答案和证据直接相关的 Citation Support、Conflict、Uncertainty。",
            "",
            "### Citation Support",
            "",
            "| label | baseline | orchestrated |",
            "| :-- | --: | --: |",
        ]
    )
    citation_labels = sorted(set(b_dfull["citation"]) | set(o_dfull["citation"]))
    for label in citation_labels:
        lines.append(f"| {label} | {b_dfull['citation'].get(label, 0)} | {o_dfull['citation'].get(label, 0)} |")
    lines.extend(
        [
            "",
            "- **unsupported_claim_count > 0**：",
            f"  - baseline：{len(b_dfull['unsupported_claim_qids'])} 题（{_qids_text(b_dfull['unsupported_claim_qids'])}）",
            f"  - orchestrated：{len(o_dfull['unsupported_claim_qids'])} 题（{_qids_text(o_dfull['unsupported_claim_qids'])}）",
            "",
            "- **conflict_count > 0**：",
            f"  - baseline：{len(b_dfull['conflict_qids'])} 题（{_qids_text(b_dfull['conflict_qids'])}）",
            f"  - orchestrated：{len(o_dfull['conflict_qids'])} 题（{_qids_text(o_dfull['conflict_qids'])}）",
            "",
            "### Uncertainty",
            "",
            "> `high` 表示不确定性/风险高；`low` 表示不确定性/风险低。",
            "",
            "| level | baseline | orchestrated |",
            "| :-- | --: | --: |",
        ]
    )
    uncertainty_levels = sorted(
        set(b_dfull["uncertainty"]) | set(o_dfull["uncertainty"]),
        key=lambda value: UNCERTAINTY_ORDER.get(value, 99),
    )
    for level in uncertainty_levels:
        lines.append(f"| {level} | {b_dfull['uncertainty'].get(level, 0)} | {o_dfull['uncertainty'].get(level, 0)} |")

    lines.extend(
        [
            "",
            "#### 各等级题号",
            "",
            "| level | baseline qids | orchestrated qids |",
            "| :-- | :-- | :-- |",
        ]
    )
    for level in uncertainty_levels:
        lines.append(
            f"| {level} | {_qids_text(b_dfull['uncertainty_qids'].get(level, []))} | "
            f"{_qids_text(o_dfull['uncertainty_qids'].get(level, []))} |"
        )

    changed_uncertainty = uncertainty_migrations["improved"] + uncertainty_migrations["worse"]
    lines.extend(["", "#### Uncertainty 等级发生变化的题", ""])
    if changed_uncertainty:
        lines.extend(
            [
                "| qid | baseline | orchestrated | direction |",
                "| :-- | :-: | :-: | :-- |",
            ]
        )
        for item in changed_uncertainty:
            direction = (
                "不确定性下降"
                if item in uncertainty_migrations["improved"]
                else "不确定性上升"
            )
            lines.append(
                f"| {item['qid']} | {item['baseline']} | {item['orchestrated']} | {direction} |"
            )
    else:
        lines.append("- 无等级变化。")

    b_profile_ragas = ragas["baseline_profile"]
    o_profile_ragas = ragas["orchestrated_profile"]
    lines.extend(
        [
            "",
            "## 5. RAGAS 质量对比",
            "",
            "> orchestrated 对证据不足题先拒答，因此进入 RAGAS 的题数少于 baseline。各 profile 全量均值用于描述各自实际评测集；跨 profile 的质量变化优先看共同题集，避免把“跳过难题”误当成质量提升。A/B/C/D 为本项目工程分档，不是 RAGAS 官方等级。",
            "",
            "### 参与范围",
            "",
            f"- baseline 进入 RAGAS：{len(b_profile_ragas['qids'])} 题；跳过：{_qids_text([row['qid'] for row in b_skipped])}。",
            f"- orchestrated 进入 RAGAS：{len(o_profile_ragas['qids'])} 题；跳过：{_qids_text([row['qid'] for row in o_skipped])}。",
            f"- 两套共同可比题：{len(ragas['shared_ragas_qids'])} 题。",
            "",
            "### Orchestrated 新增拒答题回看 baseline 质量信号",
            "",
            "> 这些题在 baseline 中回答、在 orchestrated 中因最终证据不足被拒答。这里回看 baseline 当时已有的 RAGAS 与 D-full 信号，帮助判断更严格的控制实际挡住了什么。",
            "",
        ]
    )
    newly_refused = [
        qid for qid in status_changes
        if (_canonical_map(baseline["canonical"]).get(qid, {}).get("outcome") or {}).get("status") == "ANSWERED"
        and (_canonical_map(orchestrated["canonical"]).get(qid, {}).get("outcome") or {}).get("status") == "REFUSED"
    ]
    if newly_refused:
        b_ragas_matrix = _ragas_matrix(baseline["ragas"])
        b_dfull_map = _dfull_map(baseline["dfull"])
        lines.extend(
            [
                "| qid | CP | Faith | AR | baseline citation | baseline uncertainty |",
                "| :-- | :-- | :-- | :-- | :-- | :-- |",
            ]
        )
        for qid in newly_refused:
            cells = []
            for metric in METRICS:
                record = b_ragas_matrix.get(qid, {}).get(metric, {})
                score = _optional_float(record.get("score")) if record.get("status") == "ok" else None
                grade = _grade_ragas_metric(metric, score) if score is not None else ""
                cells.append(f"{_fmt_score(score)} / {GRADE_DISPLAY.get(grade, '—')}")
            dfout = (b_dfull_map.get(qid, {}).get("outcome") or {}) if qid in b_dfull_map else {}
            lines.append(
                f"| {qid} | {cells[0]} | {cells[1]} | {cells[2]} | "
                f"{dfout.get('citation_support_label') or '—'} | {dfout.get('uncertainty_level') or '—'} |"
            )
    else:
        lines.append("无。")
    lines.extend(
        [
            "",
            "### 各 profile 原始均值",
            "",
            "| metric | baseline n | baseline mean | orchestrated n | orchestrated mean |",
            "| :-- | --: | --: | --: | --: |",
        ]
    )
    for metric in METRICS:
        b_item = b_profile_ragas["metrics"][metric]
        o_item = o_profile_ragas["metrics"][metric]
        lines.append(
            f"| {_metric_name(metric)} | {b_item['count']} | {_fmt_score(b_item['mean'])} | "
            f"{o_item['count']} | {_fmt_score(o_item['mean'])} |"
        )
    lines.extend(
        [
            "",
            "### 共同题集均值与分档迁移",
            "",
            "| metric | shared n | baseline mean | orchestrated mean | mean delta | 升档 | 同档 | 降档 |",
            "| :-- | --: | --: | --: | --: | --: | --: | --: |",
        ]
    )
    for metric in METRICS:
        item = ragas["metrics"][metric]
        lines.append(
            f"| {_metric_name(metric)} | {len(item['shared_qids'])} | {_fmt_score(item['baseline_mean'])} | "
            f"{_fmt_score(item['orchestrated_mean'])} | {_fmt_delta(item['mean_delta'])} | "
            f"{len(item['migrations']['improved'])} | {len(item['migrations']['same'])} | {len(item['migrations']['worse'])} |"
        )

    lines.extend(["", "### 分档发生变化的题", ""])
    for metric in METRICS:
        item = ragas["metrics"][metric]
        changed = item["migrations"]["improved"] + item["migrations"]["worse"]
        lines.append(f"#### {_metric_name(metric)}")
        lines.append("")
        if not changed:
            lines.append("- 无分档变化。")
            lines.append("")
            continue
        lines.append("| qid | baseline | orchestrated | score delta | direction |")
        lines.append("| :-- | :-: | :-: | --: | :-- |")
        for qid in changed:
            grade = item["grades"][qid]
            direction = "升档" if qid in item["migrations"]["improved"] else "降档"
            lines.append(
                f"| {qid} | {GRADE_DISPLAY.get(grade['baseline'], '—')} | {GRADE_DISPLAY.get(grade['orchestrated'], '—')} | "
                f"{_fmt_delta(item['deltas'][qid])} | {direction} |"
            )
        lines.append("")

    lines.extend(["### 共同题集分数变化 Top 5", ""])
    for metric in METRICS:
        item = ragas["metrics"][metric]
        gains = "；".join(f"{qid} {_fmt_delta(item['deltas'][qid])}" for qid in item["top_gains"]) or "无正向变化"
        losses = "；".join(f"{qid} {_fmt_delta(item['deltas'][qid])}" for qid in item["top_losses"]) or "无负向变化"
        lines.append(f"- **{_metric_name(metric)} 最大提升**：{gains}")
        lines.append(f"- **{_metric_name(metric)} 最大下降**：{losses}")
    lines.extend(
        [
            "",
            "## 6. Evaluation 三类总账对比",
            "",
            "> `time_sum` 是各题 / 各指标任务耗时求和，不等同于整批任务真实墙钟时间。RAGAS 两套参与题数不同，因此 combined 总成本同时受运行策略和 RAGAS 题数变化影响。",
            "",
            "| category | baseline calls | orchestrated calls | baseline tokens | orchestrated tokens | baseline cost | orchestrated cost | cost delta |",
            "| :-- | --: | --: | --: | --: | --: | --: | --: |",
        ]
    )
    for category in ("online", "offline_dfull", "ragas", "combined"):
        b_row = b_ledger.get(category, {})
        o_row = o_ledger.get(category, {})
        lines.append(
            f"| {CATEGORY_DISPLAY[category]} | {_fmt_int(b_row.get('model_call_count'))} | {_fmt_int(o_row.get('model_call_count'))} | "
            f"{_fmt_int(b_row.get('total_tokens'))} | {_fmt_int(o_row.get('total_tokens'))} | "
            f"{_fmt_cost(b_row.get('estimated_cost_usd'))} | {_fmt_cost(o_row.get('estimated_cost_usd'))} | "
            f"{_fmt_pct_delta(b_row.get('estimated_cost_usd'), o_row.get('estimated_cost_usd'))} |"
        )

    lines.extend(
        [
            "",
            "## 7. 多花了什么，换来了什么",
            "",
            "| 维度 | 事实变化 |",
            "| :-- | :-- |",
            f"| 在线成本 | orchestrated 相比 baseline {_fmt_pct_delta(b_online_cost, o_online_cost)}；{_fmt_cost(b_online_cost)} → {_fmt_cost(o_online_cost)} |",
            f"| 在线 Token | {_fmt_int(b_main['total_tokens'])} → {_fmt_int(o_main['total_tokens'])}（{_fmt_pct_delta(b_main['total_tokens'], o_main['total_tokens'])}） |",
            f"| 在线题级耗时总和 | {_fmt_seconds_from_ms(b_main['service_sum_ms'])} → {_fmt_seconds_from_ms(o_main['service_sum_ms'])}（{_fmt_pct_delta(b_main['service_sum_ms'], o_main['service_sum_ms'])}） |",
            f"| Sufficiency Judge | {b_suff['judge_call_count']} → {o_suff['judge_call_count']} calls；{_fmt_cost(b_suff['estimated_cost_usd'])} → {_fmt_cost(o_suff['estimated_cost_usd'])} |",
            f"| 控制结果 | 最终拒答 {len(b_main['refusal_qids'])} → {len(o_main['refusal_qids'])}；新增/变化题：{_qids_text(status_changes)} |",
        ]
    )
    for metric in METRICS:
        item = ragas["metrics"][metric]
        lines.append(
            f"| RAGAS {_metric_name(metric)}（共同题） | mean {_fmt_score(item['baseline_mean'])} → {_fmt_score(item['orchestrated_mean'])} "
            f"({_fmt_delta(item['mean_delta'])})；升档 {len(item['migrations']['improved'])}，降档 {len(item['migrations']['worse'])} |"
        )
    lines.extend(
        [
            f"| 全套评测成本 | {_fmt_cost(b_combined_cost)} → {_fmt_cost(o_combined_cost)}（{_fmt_pct_delta(b_combined_cost, o_combined_cost)}）；注意 RAGAS 参与题数 {len(b_profile_ragas['qids'])} → {len(o_profile_ragas['qids'])} |",
            "",
            "> 本报告不合成一个“总质量分”。控制收益、RAGAS 质量信号与资源代价分别保留，便于按工程目标做取舍。",
            "",
            "## 机器底账",
            "",
            f"- baseline: `{baseline['root']}`",
            f"- orchestrated: `{orchestrated['root']}`",
            "- 逐题对比 CSV：`tables/baseline_vs_orchestrated_per_case.csv`",
            "- 结构化对比 JSON：`baseline_vs_orchestrated_comparison.json`",
        ]
    )

    payload = {
        "baseline_profile": baseline["profile"],
        "orchestrated_profile": orchestrated["profile"],
        "baseline_root": str(baseline["root"]),
        "orchestrated_root": str(orchestrated["root"]),
        "main_chain": {"baseline": b_main, "orchestrated": o_main},
        "sufficiency": {"baseline": b_suff, "orchestrated": o_suff},
        "online_model_roles": {"baseline": b_roles, "orchestrated": o_roles},
        "dfull": {
            "baseline": b_dfull,
            "orchestrated": o_dfull,
            "uncertainty_migrations": uncertainty_migrations,
        },
        "ragas": ragas,
        "ragas_skipped": {"baseline": b_skipped, "orchestrated": o_skipped},
        "evaluation_ledger": {"baseline": b_ledger, "orchestrated": o_ledger},
        "status_change_qids": status_changes,
        "route_change_qids": route_changes,
    }
    return "\n".join(lines) + "\n", payload


def build_comparison(
    baseline_dir: Path,
    orchestrated_dir: Path,
    output_dir: Path,
) -> dict[str, Path]:
    baseline = _bundle(baseline_dir)
    orchestrated = _bundle(orchestrated_dir)
    if baseline["profile"] != "baseline":
        raise ValueError(f"--baseline-dir profile is {baseline['profile']!r}, expected 'baseline'")
    if orchestrated["profile"] != "orchestrated":
        raise ValueError(
            f"--orchestrated-dir profile is {orchestrated['profile']!r}, expected 'orchestrated'"
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    tables = output_dir / "tables"
    tables.mkdir(parents=True, exist_ok=True)
    per_case = _per_case_rows(baseline, orchestrated)
    markdown, payload = _markdown(baseline, orchestrated, per_case=per_case)

    report_path = output_dir / "Baseline-vs-Orchestrated-最终评测对比.md"
    json_path = output_dir / "baseline_vs_orchestrated_comparison.json"
    csv_path = tables / "baseline_vs_orchestrated_per_case.csv"
    report_path.write_text(markdown, encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    _write_csv(csv_path, per_case)
    return {"report": report_path, "json": json_path, "per_case_csv": csv_path}


def main() -> int:
    args = arguments()
    paths = build_comparison(args.baseline_dir, args.orchestrated_dir, args.output_dir)
    for key, path in paths.items():
        print(f"{key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
