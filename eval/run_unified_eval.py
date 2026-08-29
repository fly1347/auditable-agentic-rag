#!/usr/bin/env python3
"""
程序作用：
统一执行或回放 CER 评估门禁；只有同时显式启用实时运行和模型调用时，程序才允许访问外部服务。

整体结构：
1）读取题集、既有 CER 与可选质量标注；
2）按 live 或 replay 模式生成、筛选并校验记录；
3）执行预算门禁和质量断言，写出统一评估报告。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import yaml

from agentic_rag.cost.pricing import estimate_usage_costs
from agentic_rag.evaluation.assertions import evaluate_record
from agentic_rag.evaluation.quality import apply_quality_annotations
from agentic_rag.execution.legacy_projection import aggregate_model_call_usage
from agentic_rag.execution.record import CanonicalExecutionRecord
from agentic_rag.reporting.evaluation import build_evaluation_reports


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--records", type=Path, help="evaluate an existing CER JSONL without calls")
    source.add_argument("--run-live", action="store_true", help="execute the dataset through the application service")
    parser.add_argument("--allow-provider-calls", action="store_true")
    parser.add_argument(
        "--confirm-external-evidence-egress",
        action="store_true",
        help="confirm that queries and retrieved evidence may be sent to configured cloud providers",
    )
    parser.add_argument("--dataset", type=Path, default=Path("eval/sample_regression_set.yaml"))
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--profile", choices=["baseline", "orchestrated"], default="orchestrated")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ids", nargs="+", help="run/replay only these case ids")
    parser.add_argument("--limit", type=int, help="run/replay only the first N selected cases")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="resume a live run from output-dir/canonical_records.jsonl",
    )
    parser.add_argument("--run-max-model-calls", type=int)
    parser.add_argument("--run-max-total-tokens", type=int)
    parser.add_argument("--run-max-cost-usd", type=float)
    parser.add_argument("--run-max-service-ms", type=float)
    parser.add_argument("--max-total-ms", type=float)
    parser.add_argument("--max-total-tokens", type=int)
    parser.add_argument("--max-cost-usd", type=float)
    parser.add_argument(
        "--quality-annotations",
        type=Path,
        help="JSONL labels bound to the exact answer SHA-256; no provider call",
    )
    return parser.parse_args()


def _suite_label(path: Path, raw: dict) -> str:
    suite_id = str(raw.get("dataset") or path.stem).strip().lower()
    aliases = {
        "regression_set_b2": "B2",
        "regression_set_dfull": "D-full",
        "regression_set_dlite": "D-lite",
        "regression_set_cplus_min": "C+",
        "phase_e_regression_set": "Phase-E",
        "min_regression_set": "A-min",
    }
    return aliases.get(suite_id, str(raw.get("dataset") or path.stem))


def read_dataset(path: Path) -> tuple[str, list[dict]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cases = list(raw.get("cases") or [])
    if not cases:
        raise ValueError(f"dataset has no cases: {path}")
    return _suite_label(path, dict(raw)), [dict(item) for item in cases]


def read_records(path: Path) -> list[CanonicalExecutionRecord]:
    return [
        CanonicalExecutionRecord.from_dict(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def select_cases(cases: list[dict], ids: list[str] | None, limit: int | None) -> list[dict]:
    selected = list(cases)
    if ids:
        requested = [str(item) for item in ids]
        requested_set = set(requested)
        known = {str(item.get("id") or "") for item in cases}
        missing = [qid for qid in requested if qid not in known]
        if missing:
            raise ValueError(f"unknown dataset case id(s): {', '.join(missing)}")
        order = {qid: index for index, qid in enumerate(requested)}
        selected = sorted(
            (item for item in cases if str(item.get("id") or "") in requested_set),
            key=lambda item: order[str(item.get("id") or "")],
        )
    if limit is not None:
        if limit <= 0:
            raise ValueError("--limit must be positive")
        selected = selected[:limit]
    if not selected:
        raise ValueError("case selection is empty")
    return selected


def _atomic_records(path: Path, records: list[CanonicalExecutionRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        "".join(json.dumps(item.to_dict(), ensure_ascii=False, sort_keys=True) + "\n" for item in records),
        encoding="utf-8",
    )
    temporary.replace(path)


def _run_totals(records: list[CanonicalExecutionRecord]) -> dict[str, Any]:
    calls: list[dict[str, Any]] = []
    service_values: list[float] = []
    for record in records:
        service_value = record.timing.get("service_total_ms")
        if isinstance(service_value, (int, float)) and not isinstance(service_value, bool):
            service_values.append(float(service_value))
        calls.extend(dict(item) for item in record.model_calls)
    token_usage = aggregate_model_call_usage(calls)
    priced = estimate_usage_costs({"model_calls": calls, "totals": {}})
    priced_calls = list(priced.get("model_calls") or [])
    observed_costs = [
        float(item["estimated_cost_usd"])
        for item in priced_calls
        if item.get("estimated_cost_usd") is not None
    ]
    unpriced_calls = len(priced_calls) - len(observed_costs)
    return {
        "model_calls": len(calls),
        "total_tokens": token_usage.get("total_tokens"),
        "total_tokens_observed_sum": token_usage.get("total_tokens_observed_sum", 0),
        "unknown_token_call_count": token_usage.get("total_tokens_unknown_call_count", 0),
        "service_ms": sum(service_values) if len(service_values) == len(records) else None,
        "service_ms_observed_sum": sum(service_values),
        "unknown_service_record_count": len(records) - len(service_values),
        "estimated_cost_usd": sum(observed_costs) if not unpriced_calls else None,
        "unpriced_calls": unpriced_calls,
    }


def _enforce_run_budget(args: argparse.Namespace, records: list[CanonicalExecutionRecord]) -> None:
    totals = _run_totals(records)
    checks = (
        ("model calls", totals["model_calls"], args.run_max_model_calls),
        ("total tokens", totals["total_tokens"], args.run_max_total_tokens),
        ("service ms", totals["service_ms"], args.run_max_service_ms),
    )
    for label, actual, maximum in checks:
        if maximum is not None and actual is None:
            raise SystemExit(
                f"Run {label} budget cannot be enforced because the ledger is incomplete; "
                "the checkpoint is preserved"
            )
        if maximum is not None and actual is not None and actual > maximum:
            raise SystemExit(f"Run budget exceeded after checkpoint: {label}={actual} > {maximum}")
    if args.run_max_cost_usd is not None:
        cost = totals["estimated_cost_usd"]
        if cost is None:
            raise SystemExit(
                "Run cost budget cannot be enforced because at least one model call is unpriced; "
                "the checkpoint is preserved"
            )
        if float(cost) > args.run_max_cost_usd:
            raise SystemExit(
                f"Run budget exceeded after checkpoint: estimated cost USD={cost} > {args.run_max_cost_usd}"
            )


def _require_run_budget_headroom(
    args: argparse.Namespace, records: list[CanonicalExecutionRecord]
) -> None:
    totals = _run_totals(records)
    checks = (
        ("model calls", totals["model_calls"], args.run_max_model_calls),
        ("total tokens", totals["total_tokens"], args.run_max_total_tokens),
        ("service ms", totals["service_ms"], args.run_max_service_ms),
        ("estimated cost USD", totals["estimated_cost_usd"], args.run_max_cost_usd),
    )
    for label, actual, maximum in checks:
        if maximum is None:
            continue
        if actual is None:
            raise SystemExit(
                f"Refusing another case: {label} ledger is incomplete; the checkpoint is preserved"
            )
        if float(actual) >= float(maximum):
            raise SystemExit(
                f"Refusing another case: {label}={actual} has no headroom below limit {maximum}; "
                "the checkpoint is preserved"
            )


def live_records(args: argparse.Namespace, cases: list[dict]) -> list[CanonicalExecutionRecord]:
    if not args.allow_provider_calls:
        raise SystemExit("Refusing live eval: add --allow-provider-calls after confirming budget/provider policy")
    if not args.confirm_external_evidence_egress:
        raise SystemExit(
            "Refusing live evidence egress: add --confirm-external-evidence-egress only after approving external disclosure"
        )
    from agentic_rag.config import load_config
    from agentic_rag.execution.command import QueryCommand
    from agentic_rag.policy.principal import eval_principal
    from agentic_rag.service.application_service import RagApplicationService

    config = load_config(args.config)
    service = RagApplicationService(config, record_sink=None)
    service.record_sink = None
    dataset_sha256 = _sha256_file(args.dataset)
    config_sha256 = config.fingerprint()
    index_provenance = service.container.index_provenance()
    index_build_id = index_provenance.get("index_build_id")
    run_id = f"eval_{uuid4().hex[:12]}"
    checkpoint = args.output_dir / "canonical_records.jsonl"
    records: list[CanonicalExecutionRecord] = []
    if args.resume and checkpoint.exists():
        records = read_records(checkpoint)
        selected_ids = {str(item.get("id") or "") for item in cases}
        seen: set[str] = set()
        for record in records:
            qid = str(record.identity.get("qid") or "")
            if qid not in selected_ids:
                raise ValueError(f"resume checkpoint contains qid outside current selection: {qid}")
            if qid in seen:
                raise ValueError(f"resume checkpoint contains duplicate qid: {qid}")
            seen.add(qid)
            profile = str(record.provenance.get("profile") or "")
            if profile and profile != args.profile:
                raise ValueError(
                    f"resume checkpoint profile mismatch for {qid}: {profile} != {args.profile}"
                )
            if record.provenance.get("dataset_sha256") != dataset_sha256:
                raise ValueError(f"resume checkpoint dataset hash mismatch for {qid}")
            if record.provenance.get("config_hash") != config_sha256:
                raise ValueError(f"resume checkpoint config hash mismatch for {qid}")
            if record.provenance.get("index_build_id") != index_build_id:
                raise ValueError(f"resume checkpoint index build mismatch for {qid}")
        run_ids = {str(record.identity.get("run_id") or "") for record in records}
        run_ids.discard("")
        if len(run_ids) > 1:
            raise ValueError("resume checkpoint contains multiple run_id values")
        if run_ids:
            run_id = next(iter(run_ids))
        _enforce_run_budget(args, records)
        print(f"resuming from checkpoint: {len(records)} case(s)", flush=True)
    completed_ids = {str(item.identity.get("qid") or "") for item in records}
    pending_cases = [item for item in cases if str(item.get("id") or "") not in completed_ids]
    total = len(cases)
    for case in pending_cases:
        qid = str(case.get("id") or "")
        _require_run_budget_headroom(args, records)
        index = next(i for i, item in enumerate(cases, start=1) if str(item.get("id") or "") == qid)
        print(f"[{index:02d}/{total:02d}] {qid} running", flush=True)
        result = service.execute(
            QueryCommand(
                query=str(case["query"]),
                profile=str(args.profile),
                qid=str(case.get("id") or ""),
                run_id=run_id,
                topk=config.topk,
            ),
            eval_principal(),
        )
        result.record.provenance["dataset_class"] = "derived_in_domain_regression"
        result.record.provenance["dataset_sha256"] = dataset_sha256
        records.append(result.record)
        _atomic_records(checkpoint, records)
        _enforce_run_budget(args, records)
        print(
            f"[{index:02d}/{total:02d}] {qid} done "
            f"route={result.record.route.get('actual_route')} "
            f"status={result.record.outcome.get('status')} "
            f"suff={result.record.sufficiency.get('first')}/{result.record.sufficiency.get('second')} "
            f"tokens={result.record.usage.get('total_tokens')} "
            f"ms={result.record.timing.get('service_total_ms')}",
            flush=True,
        )
    return records


# 将规范记录投影成统一评估产物。
def write_outputs(
    args: argparse.Namespace,
    records: list[CanonicalExecutionRecord],
    cases: list[dict],
    *,
    suite_label: str,
) -> bool:
    case_by_qid = {str(item.get("id")): item for item in cases}
    for record in records:
        priced = estimate_usage_costs({"model_calls": record.model_calls, "totals": record.usage})
        record.model_calls = list(priced.get("model_calls") or record.model_calls)
        record.usage = {**record.usage, **dict(priced.get("totals") or {})}
        record.usage["model_call_count"] = len(record.model_calls)
        record.usage["cost_observation"] = dict(priced.get("cost_estimation") or {}).get("coverage", "none")
        record.usage["cost_estimation"] = dict(priced.get("cost_estimation") or {})
        qid = str(record.identity.get("qid") or "")
        case = case_by_qid.get(qid)
        if case is None:
            raise ValueError(f"record qid not present in dataset: {qid}")
        evaluate_record(
            record,
            case,
            max_total_ms=args.max_total_ms,
            max_total_tokens=args.max_total_tokens,
            max_cost_usd=args.max_cost_usd,
        )
    if args.quality_annotations is not None:
        annotations = [
            json.loads(line)
            for line in args.quality_annotations.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        apply_quality_annotations(records, annotations)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    internal_path = args.output_dir / "canonical_records.jsonl"
    public_path = args.output_dir / "canonical_records.sanitized.jsonl"
    internal_path.write_text(
        "".join(json.dumps(item.to_dict(), ensure_ascii=False, sort_keys=True) + "\n" for item in records),
        encoding="utf-8",
    )
    public_path.write_text(
        "".join(json.dumps(item.sanitized_dict(), ensure_ascii=False, sort_keys=True) + "\n" for item in records),
        encoding="utf-8",
    )

    dimension_names = [
        "behavior", "answer_quality", "expected_evidence", "prompt_evidence",
        "citation_validity", "route_invariants", "security_policy", "errors", "resource_budget",
    ]
    rows = []
    for record in records:
        dimensions = dict(record.evaluation.get("dimensions") or {})
        rows.append({
            "qid": record.identity.get("qid"),
            "profile": record.provenance.get("profile"),
            "status": record.outcome.get("status"),
            **{name: dict(dimensions.get(name) or {}).get("status") for name in dimension_names},
            "hard_gate_pass": record.evaluation.get("hard_gate_pass"),
            "hard_gate_complete": record.evaluation.get("hard_gate_complete"),
            "release_ready": record.evaluation.get("release_ready"),
            "blocking_dimensions": ",".join(record.evaluation.get("blocking_dimensions") or []),
            "unobserved_hard_gate_dimensions": ",".join(
                record.evaluation.get("unobserved_hard_gate_dimensions") or []
            ),
        })
    csv_path = args.output_dir / "quality_metrics.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]) if rows else ["qid"])
        writer.writeheader()
        writer.writerows(rows)
    passed = sum(bool(row["hard_gate_pass"]) for row in rows)
    complete = sum(bool(row["hard_gate_complete"]) for row in rows)
    release_ready = sum(bool(row["release_ready"]) for row in rows)
    summary = [
        "# Unified Evaluation Summary",
        "",
        f"- profile: `{args.profile}`",
        f"- cases: {len(rows)}",
        f"- hard gate: {passed}/{len(rows)}",
        f"- hard gate complete: {complete}/{len(rows)}",
        f"- release ready (includes independent answer quality): {release_ready}/{len(rows)}",
        "- answer quality: independent/manual or RAGAS evaluator; never inferred from behavior.",
        "",
        "| qid | behavior | evidence | prompt | citation | route | security | errors | budget | hard gate | complete | release |",
        "| :-- | :--: | :--: | :--: | :--: | :--: | :--: | :--: | :--: | :--: | :--: | :--: |",
    ]
    for row in rows:
        summary.append(
            f"| {row['qid']} | {row['behavior']} | {row['expected_evidence']} | {row['prompt_evidence']} | "
            f"{row['citation_validity']} | {row['route_invariants']} | {row['security_policy']} | "
            f"{row['errors']} | {row['resource_budget']} | {row['hard_gate_pass']} | "
            f"{row['hard_gate_complete']} | {row['release_ready']} |"
        )
    (args.output_dir / "quality_evaluation_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    report_paths = build_evaluation_reports(
        records,
        args.output_dir,
        suite_label=suite_label,
    )
    print("readable reports:", flush=True)
    print(f"  summary: {report_paths['summary']}", flush=True)
    print(f"  per-question: {report_paths['per_question']}", flush=True)
    print(f"  retrieval signal: {report_paths['retrieval_signal']}", flush=True)
    print(f"  retrieval sources: {report_paths['retrieval_source_distribution']}", flush=True)
    print(f"  retrieval workflow: {report_paths['retrieval_workflow']}", flush=True)
    print(f"  timing/usage/cost: {report_paths['timing_usage_cost']}", flush=True)
    print(f"  performance/cost: {report_paths['performance']}", flush=True)
    print(f"  cases csv: {report_paths['cases']}", flush=True)
    return passed == len(rows)


def main() -> int:
    args = arguments()
    suite_label, cases = read_dataset(args.dataset)
    cases = select_cases(cases, args.ids, args.limit)
    if args.run_live:
        records = live_records(args, cases)
    else:
        selected_ids = {str(item.get("id") or "") for item in cases}
        records = [
            record
            for record in read_records(args.records)
            if str(record.identity.get("qid") or "") in selected_ids
        ]
        if len(records) != len(cases):
            found = {str(record.identity.get("qid") or "") for record in records}
            missing = [str(item.get("id") or "") for item in cases if str(item.get("id") or "") not in found]
            raise ValueError(f"selected record(s) missing: {', '.join(missing)}")
    return 0 if write_outputs(args, records, cases, suite_label=suite_label) else 2


if __name__ == "__main__":
    raise SystemExit(main())
