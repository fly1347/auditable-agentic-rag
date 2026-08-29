#!/usr/bin/env python3
"""
程序作用：
从 CER 中保存的实际提示上下文构造 RAGAS 输入，避免重新检索或重新拼装证据造成口径漂移。

整体结构：
1）读取 CER、回归题集与参考答案；
2）逐题绑定实际上下文、答案、引用和来源信息；
3）输出 RAGAS 输入 JSONL、预览报告与来源校验信息。
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import yaml

from agentic_rag.evaluation.offline_record import source_binding
from agentic_rag.execution.record import CanonicalExecutionRecord


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="prepare_ragas_from_cer")
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--references", type=Path, default=Path("eval/sample_ragas_reference_answers.yaml"))
    parser.add_argument("--dataset", type=Path, default=Path("eval/sample_regression_set.yaml"))
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
    return records


def _read_cases(path: Path) -> dict[str, dict[str, Any]]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return {
        str(item.get("id") or item.get("qid") or ""): dict(item)
        for item in list(raw.get("cases") or [])
        if isinstance(item, Mapping)
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


# 按题号把 CER 的实际执行事实转换成 RAGAS 输入行。
def build_ragas_rows(
    records: list[CanonicalExecutionRecord],
    references: Mapping[str, Mapping[str, Any]],
    cases: Mapping[str, Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for record in records:
        qid = str(record.identity.get("qid") or "")
        reference = dict(references.get(qid) or {})
        case = dict(cases.get(qid) or {})
        if not reference:
            skipped.append({"qid": qid, "reason": "reference_missing"})
            continue
        if reference.get("enable_ragas") is False:
            skipped.append({"qid": qid, "reason": "enable_ragas_false"})
            continue
        if str(record.outcome.get("status") or "") != "ANSWERED":
            skipped.append({"qid": qid, "reason": "source_not_answered"})
            continue

        visible = [
            dict(item)
            for item in list(record.prompt.get("visible_evidence") or [])
            if isinstance(item, Mapping)
        ]
        contexts = [str(item.get("text") or "") for item in visible if str(item.get("text") or "").strip()]
        if not contexts:
            raise ValueError(f"RAGAS-enabled answered case has no prompt-visible contexts: {qid}")
        answer = str(record.outcome.get("answer") or "")
        reference_answer = str(reference.get("reference_answer") or "").strip()
        if not answer:
            raise ValueError(f"RAGAS-enabled case has empty answer: {qid}")
        if reference.get("enable_reference_based_metrics") is not False and not reference_answer:
            raise ValueError(f"reference-based RAGAS case has empty reference: {qid}")

        expected_sources = [str(item) for item in list(case.get("expected_evidence") or [])]
        prompt_sources = {str(item.get("source_id") or "") for item in visible}
        matched = [source for source in expected_sources if source in prompt_sources]
        missing = [source for source in expected_sources if source not in prompt_sources]
        binding = source_binding(record)
        rows.append(
            {
                "qid": qid,
                "user_input": record.query,
                "response": answer,
                "retrieved_contexts": contexts,
                "context_refs": [
                    {
                        "marker": item.get("marker"),
                        "chunk_id": item.get("chunk_id"),
                        "source_id": item.get("source_id"),
                        "visible_offset_start": item.get("visible_offset_start"),
                        "visible_offset_end": item.get("visible_offset_end"),
                    }
                    for item in visible
                    if str(item.get("text") or "").strip()
                ],
                "reference": reference_answer,
                "enable_reference_based_metrics": bool(
                    reference.get("enable_reference_based_metrics", True)
                ),
                "expected_behavior": case.get("expected_behavior"),
                "expected_evidence": expected_sources,
                "expected_evidence_count": len(expected_sources),
                "matched_expected_evidence": matched,
                "missing_expected_evidence": missing,
                "expected_evidence_any_hit": bool(matched) if expected_sources else None,
                "expected_evidence_full_hit": not missing if expected_sources else None,
                "expected_evidence_coverage_ratio": (
                    len(matched) / len(expected_sources) if expected_sources else None
                ),
                "source_profile": binding.get("source_profile"),
                "source_cer_sha256": binding.get("source_cer_sha256"),
                "answer_sha256": binding.get("answer_sha256"),
                "evidence_snapshot_id": binding.get("evidence_snapshot_id"),
                "prompt_sha256": binding.get("prompt_sha256"),
                "timing_ms": record.timing.get("service_total_ms"),
                "retrieval_ms": record.timing.get("retrieval_ms"),
                "generation_ms": record.timing.get("generation_ms"),
                "llm_generate_ms": record.timing.get("llm_generate_ms"),
            }
        )
    return rows, skipped


def _display_list(values: Any) -> str:
    items = [str(item) for item in list(values or []) if str(item).strip()]
    return "；".join(items) if items else "无"


def _display_bool(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    return "not_observed"


def _display_ratio(value: Any) -> str:
    if value is None:
        return "not_observed"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def _skip_reason_text(reason: str) -> str:
    return {
        "reference_missing": "缺少 reference 配置",
        "enable_ragas_false": "该题配置为不进入 RAGAS",
        "source_not_answered": "源 CER 未产生 ANSWERED 结果",
    }.get(str(reason), str(reason))


def _source_profile(rows: list[dict[str, Any]]) -> str:
    profiles = {str(row.get("source_profile") or "").strip() for row in rows}
    profiles.discard("")
    if len(profiles) != 1:
        raise ValueError(f"RAGAS input must contain exactly one source_profile, got: {sorted(profiles)}")
    return next(iter(profiles))


def _context_ref_line(item: Mapping[str, Any]) -> tuple[str, str, str, str]:
    marker = str(item.get("marker") or "")
    source_id = str(item.get("source_id") or "")
    start = item.get("visible_offset_start")
    end = item.get("visible_offset_end")
    visible_range = (
        f"@{start}-{end}"
        if start is not None and end is not None
        else "not_observed"
    )
    chunk_id = str(item.get("chunk_id") or "")
    return marker, source_id, visible_range, chunk_id


def render_ragas_input_preview(
    rows: list[dict[str, Any]],
    skipped: list[dict[str, Any]],
) -> str:
    profile = _source_profile(rows)
    full_hit = sum(1 for row in rows if row.get("expected_evidence_full_hit") is True)
    partial_hit = sum(
        1
        for row in rows
        if row.get("expected_evidence_any_hit") is True
        and row.get("expected_evidence_full_hit") is not True
    )
    no_hit = sum(1 for row in rows if row.get("expected_evidence_any_hit") is False)
    context_counts = [len(list(row.get("retrieved_contexts") or [])) for row in rows]
    context_count_text = (
        str(context_counts[0])
        if context_counts and len(set(context_counts)) == 1
        else f"min={min(context_counts)}；max={max(context_counts)}" if context_counts else "0"
    )

    lines = [
        f"# RAGAS {profile} 输入预览",
        "",
        "> 本报告只说明实际送入 RAGAS 的输入，不包含评测分数。`retrieved_contexts` 只来自冻结 CER 的 `prompt.visible_evidence`，不会重新执行 retrieval 或 query pipeline。",
        "",
        "## 批次摘要",
        "",
        "| field | value |",
        "| :-- | :-- |",
        f"| source_profile | {profile} |",
        f"| included | {len(rows)} |",
        f"| skipped | {len(skipped)} |",
        f"| contexts_per_case | {context_count_text} |",
        f"| expected_evidence_full_hit | {full_hit} |",
        f"| expected_evidence_partial_hit | {partial_hit} |",
        f"| expected_evidence_no_hit | {no_hit} |",
        "",
        "## 输入字段说明",
        "",
        "| 字段 | 含义 |",
        "| :-- | :-- |",
        "| user_input | 原始问题 |",
        "| response | 本轮主链实际生成的答案 |",
        "| reference | RAGAS reference-based 指标使用的参考答案 |",
        "| retrieved_contexts | 模型生成答案时实际看到的 prompt-visible evidence；也是本轮 RAGAS 使用的 contexts |",
        "| context_refs | `retrieved_contexts` 对应的 E 标记、source、可见 offset 与 chunk_id |",
        "| expected_evidence_* | 回归集预期证据与本轮 prompt contexts 的命中诊断；不是 RAGAS 指标分数 |",
        "",
    ]

    incomplete_expected = [
        str(row.get("qid") or "")
        for row in rows
        if row.get("expected_evidence_full_hit") is not True
    ]
    if incomplete_expected:
        lines.extend(
            [
                "## 输入关注项",
                "",
                "| 观察项 | qids |",
                "| :-- | :-- |",
                f"| expected_evidence 未完整进入 prompt contexts | {'、'.join(incomplete_expected)} |",
                "",
            ]
        )

    if skipped:
        lines.extend(
            [
                "## 跳过题",
                "",
                "| qid | reason | 说明 |",
                "| :-- | :-- | :-- |",
            ]
        )
        for item in skipped:
            reason = str(item.get("reason") or "")
            lines.append(
                f"| {item.get('qid')} | {reason} | {_skip_reason_text(reason)} |"
            )
        lines.append("")

    for row in rows:
        qid = str(row.get("qid") or "")
        query = str(row.get("user_input") or "")
        lines.extend(
            [
                f"## {qid} — {query}",
                "",
                "### 输入概览",
                "",
                "| field | value |",
                "| :-- | :-- |",
                f"| expected_behavior | {row.get('expected_behavior')} |",
                f"| expected_evidence | {_display_list(row.get('expected_evidence'))} |",
                f"| matched_expected_evidence | {_display_list(row.get('matched_expected_evidence'))} |",
                f"| missing_expected_evidence | {_display_list(row.get('missing_expected_evidence'))} |",
                f"| expected_evidence_any_hit | {_display_bool(row.get('expected_evidence_any_hit'))} |",
                f"| expected_evidence_full_hit | {_display_bool(row.get('expected_evidence_full_hit'))} |",
                f"| expected_evidence_coverage_ratio | {_display_ratio(row.get('expected_evidence_coverage_ratio'))} |",
                f"| context_count | {len(list(row.get('retrieved_contexts') or []))} |",
                "",
                "### response",
                "",
                "```text",
                str(row.get("response") or ""),
                "```",
                "",
                "### reference",
                "",
                "```text",
                str(row.get("reference") or ""),
                "```",
                "",
                "### RAGAS 实际使用的 contexts",
                "",
                "| evidence | source_id | visible_range | chunk_id |",
                "| :-- | :-- | :-- | :-- |",
            ]
        )
        for item in list(row.get("context_refs") or []):
            marker, source_id, visible_range, chunk_id = _context_ref_line(item)
            lines.append(
                f"| {marker} | {source_id} | {visible_range} | {chunk_id} |"
            )
        lines.extend(
            [
                "",
                "### 追溯信息",
                "",
                f"- source_cer_sha256: `{row.get('source_cer_sha256')}`",
                f"- answer_sha256: `{row.get('answer_sha256')}`",
                f"- prompt_sha256: `{row.get('prompt_sha256')}`",
                "",
            ]
        )
    return "\n".join(lines)


def _preview(rows: list[dict[str, Any]], skipped: list[dict[str, Any]]) -> str:
    return render_ragas_input_preview(rows, skipped)


def main() -> int:
    args = arguments()
    records = _read_cer(args.records)
    references = _read_cases(args.references)
    cases = _read_cases(args.dataset)
    rows, skipped = build_ragas_rows(records, references, cases)
    if not rows:
        raise SystemExit("no RAGAS-enabled rows were prepared")
    dataset_sha256 = _sha256_file(args.dataset)
    references_sha256 = _sha256_file(args.references)
    for row in rows:
        row["dataset_sha256"] = dataset_sha256
        row["references_sha256"] = references_sha256

    args.output_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = args.output_dir / "ragas_input.jsonl"
    legacy_preview_path = args.output_dir / "ragas_input_preview.md"
    if legacy_preview_path.exists():
        legacy_preview_path.unlink()
    profile = _source_profile(rows)
    preview_path = args.output_dir / f"RAGAS-{profile}-输入预览.md"
    manifest_path = args.output_dir / "ragas_prepare_manifest.json"
    jsonl_path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    preview_path.write_text(_preview(rows, skipped), encoding="utf-8")
    manifest = {
        "schema_version": "1.0.0",
        "source_records": str(args.records),
        "source_records_sha256": _sha256_file(args.records),
        "references": str(args.references),
        "references_sha256": references_sha256,
        "dataset": str(args.dataset),
        "dataset_sha256": dataset_sha256,
        "included": len(rows),
        "skipped": skipped,
        "ragas_input_sha256": hashlib.sha256(jsonl_path.read_bytes()).hexdigest(),
        "context_source": "cer.prompt.visible_evidence",
        "query_pipeline_rerun": False,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"included: {len(rows)}", flush=True)
    print(f"skipped: {len(skipped)}", flush=True)
    print(f"input: {jsonl_path}", flush=True)
    print(f"preview: {preview_path}", flush=True)
    print(f"manifest: {manifest_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
