#!/usr/bin/env python3
"""Run the CER-native post-run D-full evaluation and write one auditable pack."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import yaml

from agentic_rag.evaluation.offline_dfull import run_offline_dfull_record
from agentic_rag.evaluation.offline_record import (
    OfflineEvaluationRecord,
    source_binding,
    stable_sha256,
)
from agentic_rag.execution.record import CanonicalExecutionRecord
from agentic_rag.reporting.offline_dfull import write_manifest, write_offline_reports


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="run_offline_dfull_eval")
    parser.add_argument("--records", type=Path, required=True, help="source CER JSONL")
    parser.add_argument("--dataset", type=Path, default=Path("eval/sample_regression_set.yaml"))
    parser.add_argument("--config", type=Path, default=Path("config.yaml"))
    parser.add_argument("--classifier-mode", choices=["rule", "llm", "skip", "reuse"], default="rule")
    parser.add_argument(
        "--reuse-classifier-records",
        type=Path,
        default=None,
        help="existing offline_dfull_records.jsonl whose classifier stage/model call should be reused",
    )
    parser.add_argument("--allow-provider-calls", action="store_true")
    parser.add_argument(
        "--confirm-external-query-egress",
        action="store_true",
        help="confirm that evaluation queries may be sent to the classifier provider",
    )
    parser.add_argument(
        "--data-visibility",
        choices=["public", "internal_demo", "internal", "confidential", "private"],
        default="internal",
    )
    parser.add_argument("--ids", nargs="+", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--require-structured-sufficiency", action="store_true")
    parser.add_argument("--max-total-tokens", type=int, default=None)
    parser.add_argument("--max-cost-usd", type=float, default=None)
    parser.add_argument("--max-model-calls", type=int, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def _read_cer(path: Path) -> list[CanonicalExecutionRecord]:
    records = [
        CanonicalExecutionRecord.from_dict(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not records:
        raise ValueError(f"CER input is empty: {path}")
    qids = [str(record.identity.get("qid") or "") for record in records]
    duplicates = sorted({qid for qid in qids if qids.count(qid) > 1})
    if duplicates:
        raise ValueError(f"CER input has duplicate qid(s): {', '.join(duplicates)}")
    return records


def _read_cases(path: Path) -> dict[str, dict]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    cases = [dict(item) for item in list(raw.get("cases") or [])]
    if not cases:
        raise ValueError(f"dataset has no cases: {path}")
    return {str(item.get("id") or item.get("qid") or ""): item for item in cases}


def _read_offline(path: Path) -> list[OfflineEvaluationRecord]:
    if not path.exists():
        return []
    return [
        OfflineEvaluationRecord.from_dict(json.loads(line))
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _atomic_write_records(records: list[OfflineEvaluationRecord], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    internal = output_dir / "offline_dfull_records.jsonl"
    sanitized = output_dir / "offline_dfull_records.sanitized.jsonl"
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output_dir, delete=False) as handle:
        for record in records:
            handle.write(json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        internal_tmp = Path(handle.name)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output_dir, delete=False) as handle:
        for record in records:
            handle.write(json.dumps(record.sanitized_dict(), ensure_ascii=False, sort_keys=True) + "\n")
        sanitized_tmp = Path(handle.name)
    os.replace(internal_tmp, internal)
    os.replace(sanitized_tmp, sanitized)


def _run_id() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"offline_dfull_{now}_{uuid4().hex[:8]}"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _totals(records: list[OfflineEvaluationRecord]) -> dict[str, int | float | None]:
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
    unknown_token_records = sum(
        bool(record.model_calls) and record.usage.get("total_tokens") in (None, "")
        for record in records
    )
    unknown_cost_records = sum(
        bool(record.model_calls) and record.usage.get("estimated_cost_usd") in (None, "")
        for record in records
    )
    return {
        "model_calls": calls,
        "total_tokens": sum(token_values) if not unknown_token_records else None,
        "total_tokens_observed_sum": sum(token_values),
        "unknown_token_record_count": unknown_token_records,
        "estimated_cost_usd": sum(cost_values) if not unknown_cost_records else None,
        "estimated_cost_usd_observed_sum": sum(cost_values),
        "unknown_cost_record_count": unknown_cost_records,
    }


def _preflight_budget_reason(
    records: list[OfflineEvaluationRecord], args: argparse.Namespace
) -> str | None:
    totals = _totals(records)
    if args.max_model_calls is not None and int(totals["model_calls"] or 0) >= args.max_model_calls:
        return "model-call budget has no remaining headroom"
    if args.max_total_tokens is not None:
        if totals["total_tokens"] is None:
            return "total-token budget cannot be enforced because usage is incomplete"
        if int(totals["total_tokens"]) >= args.max_total_tokens:
            return "total-token budget has no remaining headroom"
    if args.max_cost_usd is not None:
        if totals["estimated_cost_usd"] is None:
            return "cost budget cannot be enforced because pricing is incomplete"
        if float(totals["estimated_cost_usd"]) >= args.max_cost_usd:
            return "cost budget has no remaining headroom"
    return None


def main() -> int:
    args = arguments()
    if args.classifier_mode == "llm" and not args.allow_provider_calls:
        raise SystemExit(
            "Refusing LLM classifier: add --allow-provider-calls after confirming budget and egress"
        )
    if args.classifier_mode == "llm" and not args.confirm_external_query_egress:
        raise SystemExit(
            "Refusing classifier query egress: add --confirm-external-query-egress only after approving external disclosure"
        )
    if args.classifier_mode != "llm" and args.allow_provider_calls:
        raise SystemExit("--allow-provider-calls is valid only with --classifier-mode llm")
    if args.classifier_mode == "reuse" and args.reuse_classifier_records is None:
        raise SystemExit("--classifier-mode reuse requires --reuse-classifier-records")
    if args.classifier_mode != "reuse" and args.reuse_classifier_records is not None:
        raise SystemExit("--reuse-classifier-records is valid only with --classifier-mode reuse")
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be positive")

    source_records = _read_cer(args.records)
    cases = _read_cases(args.dataset)
    dataset_sha256 = _sha256_file(args.dataset)
    source_records_sha256 = _sha256_file(args.records)
    config_sha256 = _sha256_file(args.config)
    reuse_classifier_sha256 = (
        _sha256_file(args.reuse_classifier_records)
        if args.reuse_classifier_records is not None
        else None
    )
    reused_classifier_records = (
        _read_offline(args.reuse_classifier_records)
        if args.reuse_classifier_records is not None
        else []
    )
    reused_classifier_by_source = {
        (
            str(item.identity.get("qid") or ""),
            str(item.source.get("source_cer_sha256") or ""),
        ): item
        for item in reused_classifier_records
    }
    wanted = {str(item) for item in list(args.ids or [])}
    if wanted:
        known = {str(record.identity.get("qid") or "") for record in source_records}
        missing = sorted(wanted - known)
        if missing:
            raise SystemExit(f"unknown source CER qid(s): {', '.join(missing)}")
        source_records = [
            record for record in source_records if str(record.identity.get("qid") or "") in wanted
        ]
    if args.limit is not None:
        source_records = source_records[: args.limit]
    if not source_records:
        raise SystemExit("no source CER rows selected")
    evaluation_config_sha256 = stable_sha256(
        {
            "source_records_sha256": source_records_sha256,
            "dataset_sha256": dataset_sha256,
            "config_sha256": config_sha256,
            "classifier_mode": args.classifier_mode,
            "reuse_classifier_records_sha256": reuse_classifier_sha256,
            "data_visibility": args.data_visibility,
            "citation_support_evidence_scope": "actual_citations",
        }
    )

    internal_path = args.output_dir / "offline_dfull_records.jsonl"
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.resume:
        raise SystemExit(f"output directory is not empty; use a new path or --resume: {args.output_dir}")
    existing = _read_offline(internal_path) if args.resume else []
    allowed_sources = {
        (
            str(record.identity.get("qid") or ""),
            str(source_binding(record).get("source_cer_sha256")),
        )
        for record in source_records
    }
    seen_existing: set[tuple[str, str]] = set()
    for record in existing:
        if record.identity.get("evaluation_config_sha256") != evaluation_config_sha256:
            raise SystemExit(
                "resume checkpoint evaluation configuration differs from the current source/config/mode selection"
            )
        key = (
            str(record.identity.get("qid") or ""),
            str(record.source.get("source_cer_sha256") or ""),
        )
        if key not in allowed_sources:
            raise SystemExit("resume checkpoint contains a record outside the current source selection")
        if key in seen_existing:
            raise SystemExit("resume checkpoint contains duplicate evaluation records")
        seen_existing.add(key)
    evaluation_run_id = (
        str(existing[0].identity.get("evaluation_run_id")) if existing else _run_id()
    )
    completed = {
        (str(record.identity.get("qid")), str(record.source.get("source_cer_sha256")))
        for record in existing
    }

    egress_events: list[dict] = []
    outputs = list(existing)
    budget_exceeded = False
    if args.classifier_mode == "llm":
        from agentic_rag.config import load_config
        from agentic_rag.policy.egress import egress_scope

        config = load_config(str(args.config))
        scope = egress_scope(
            config.egress,
            default_visibilities=[args.data_visibility],
            recorder=egress_events.append,
        )
    else:
        scope = nullcontext()
    with scope:
        total = len(source_records)
        for index, source in enumerate(source_records, start=1):
            qid = str(source.identity.get("qid") or "")
            case = cases.get(qid)
            if case is None:
                raise ValueError(f"source qid not present in dataset: {qid}")
            binding = source_binding(source)
            key = (qid, str(binding.get("source_cer_sha256")))
            if key in completed:
                print(f"[{index:02d}/{total:02d}] {qid} skipped (resume)", flush=True)
                continue
            if args.classifier_mode == "llm":
                budget_reason = _preflight_budget_reason(outputs, args)
                if budget_reason:
                    budget_exceeded = True
                    print(f"budget stop before {qid}: {budget_reason}", flush=True)
                    break
            print(f"[{index:02d}/{total:02d}] {qid} running", flush=True)
            reused_classifier_record = None
            if args.classifier_mode == "reuse":
                reused_classifier_record = reused_classifier_by_source.get(key)
                if reused_classifier_record is None:
                    raise ValueError(f"missing reusable classifier record for {qid}")
            result = run_offline_dfull_record(
                source,
                case,
                evaluation_run_id=evaluation_run_id,
                classifier_mode=args.classifier_mode,
                config_path=str(args.config),
                dataset_sha256=dataset_sha256,
                evaluation_config_sha256=evaluation_config_sha256,
                reused_classifier_record=reused_classifier_record,
            )
            outputs.append(result)
            completed.add(key)
            _atomic_write_records(outputs, args.output_dir)
            totals = _totals(outputs)
            if args.classifier_mode == "reuse":
                print(
                    f"[{index:02d}/{total:02d}] {qid} done "
                    f"status={result.outcome.get('status')} classifier=reused "
                    f"historical_calls={len(result.model_calls)}",
                    flush=True,
                )
            else:
                print(
                    f"[{index:02d}/{total:02d}] {qid} done "
                    f"status={result.outcome.get('status')} calls={len(result.model_calls)} "
                    f"tokens={result.usage.get('total_tokens')} cost={result.usage.get('estimated_cost_usd')}",
                    flush=True,
                )
            if args.classifier_mode == "llm" and args.max_model_calls is not None and int(totals["model_calls"] or 0) > args.max_model_calls:
                budget_exceeded = True
                print(
                    f"budget stop: model_calls={totals['model_calls']} > {args.max_model_calls}",
                    flush=True,
                )
                break
            if args.classifier_mode == "llm" and args.max_total_tokens is not None:
                if totals["total_tokens"] is None:
                    budget_exceeded = True
                    print("budget stop: total_tokens is not fully observed", flush=True)
                    break
                if int(totals["total_tokens"]) > args.max_total_tokens:
                    budget_exceeded = True
                    print(
                        f"budget stop: total_tokens={totals['total_tokens']} > {args.max_total_tokens}",
                        flush=True,
                    )
                    break
            if args.classifier_mode == "llm" and args.max_cost_usd is not None:
                if totals["estimated_cost_usd"] is None:
                    budget_exceeded = True
                    print("budget stop: cost_usd is not fully observed", flush=True)
                    break
                if float(totals["estimated_cost_usd"]) > args.max_cost_usd:
                    budget_exceeded = True
                    print(
                        f"budget stop: cost_usd={float(totals['estimated_cost_usd']):.9f} > {args.max_cost_usd}",
                        flush=True,
                    )
                    break

    _atomic_write_records(outputs, args.output_dir)
    report_paths = write_offline_reports(outputs, args.output_dir, source_records=source_records)
    egress_path = args.output_dir / "egress_decisions.json"
    egress_path.write_text(
        json.dumps(egress_events, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest_path = write_manifest(
        args.output_dir,
        metadata={
            "evaluation_run_id": evaluation_run_id,
            "source_records": str(args.records),
            "source_records_sha256": source_records_sha256,
            "dataset": str(args.dataset),
            "dataset_sha256": dataset_sha256,
            "config_sha256": config_sha256,
            "evaluation_config_sha256": evaluation_config_sha256,
            "classifier_mode": args.classifier_mode,
            "reuse_classifier_records": str(args.reuse_classifier_records) if args.reuse_classifier_records else None,
            "reuse_classifier_records_sha256": reuse_classifier_sha256,
            "citation_support_evidence_scope": "actual_citations",
            "case_count": len(outputs),
        },
    )

    structured_missing = [
        str(record.identity.get("qid"))
        for record in outputs
        if record.outcome.get("structured_sufficiency_observed") is not True
    ]
    error_stages = [
        f"{record.identity.get('qid')}:{stage.name}"
        for record in outputs
        for stage in record.stages
        if stage.status == "error"
    ]
    totals = _totals(outputs)
    print(f"records: {internal_path}", flush=True)
    print(f"summary: {report_paths['summary']}", flush=True)
    print(f"timing/usage/cost: {report_paths['timing_usage_cost']}", flush=True)
    print(f"manifest: {manifest_path}", flush=True)
    if args.classifier_mode == "reuse":
        print(
            "totals (reused historical classifier accounting): "
            f"cases={len(outputs)} calls={totals['model_calls']} "
            f"tokens={totals['total_tokens']} "
            f"cost_usd={totals['estimated_cost_usd']} new_provider_calls=0",
            flush=True,
        )
    else:
        print(
            "totals: "
            f"cases={len(outputs)} calls={totals['model_calls']} "
            f"tokens={totals['total_tokens']} "
            f"cost_usd={totals['estimated_cost_usd']}",
            flush=True,
        )

    failed = bool(error_stages) or budget_exceeded
    if args.require_structured_sufficiency and structured_missing:
        print(f"structured sufficiency missing: {', '.join(structured_missing)}", flush=True)
        failed = True
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
