"""
程序作用：
从 CER 及安全断言生成确定性的发布证据包，明确区分历史桥接证据与最终回归证据。

整体结构：
1）按评估维度汇总可直接观测的断言状态；
2）生成质量表、安全表与通用评估报告；
3）build_release_pack 复制必要产物并写出文件哈希清单。
"""

from __future__ import annotations

import csv
import hashlib
import json
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping

from agentic_rag.execution.record import CanonicalExecutionRecord
from agentic_rag.reporting.evaluation import build_evaluation_reports


DIMENSIONS = (
    "behavior",
    "answer_quality",
    "expected_evidence",
    "prompt_evidence",
    "citation_validity",
    "route_invariants",
    "security_policy",
    "errors",
    "resource_budget",
)


def _dimension_statuses(record: CanonicalExecutionRecord) -> dict[str, str]:
    evaluation = dict(record.evaluation or {})
    dimensions = evaluation.get("dimensions")
    if isinstance(dimensions, Mapping):
        return {
            name: str(dict(dimensions.get(name) or {}).get("status") or "not_observed")
            for name in DIMENSIONS
        }

    # 历史桥接记录早于统一断言结构，只保留当时直接观测到的布尔契约；绝不从答案字符串推断 grounding、引用有效性、安全或答案质量。
    behavior_raw = evaluation.get("behavior_pass")
    path_raw = evaluation.get("path_pass")
    return {
        "behavior": "pass" if behavior_raw is True else "fail" if behavior_raw is False else "not_observed",
        "answer_quality": "not_observed",
        "expected_evidence": "not_observed",
        "prompt_evidence": "not_observed",
        "citation_validity": "not_observed",
        "route_invariants": "pass" if path_raw is True else "fail" if path_raw is False else "not_observed",
        "security_policy": "not_observed",
        "errors": "pass" if not record.errors else "fail",
        "resource_budget": "not_observed",
    }


def _quality_rows(
    records: list[CanonicalExecutionRecord],
    evidence_class: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        statuses = _dimension_statuses(record)
        evaluation = dict(record.evaluation or {})
        unified = isinstance(evaluation.get("dimensions"), Mapping)
        rows.append(
            {
                "qid": record.identity.get("qid"),
                "profile": record.provenance.get("profile"),
                "evidence_class": evidence_class,
                **statuses,
                "hard_gate_pass": evaluation.get("hard_gate_pass", "not_observed") if unified else "not_observed",
                "hard_gate_complete": evaluation.get("hard_gate_complete", False) if unified else False,
                "release_ready": evaluation.get("release_ready", False) if unified else False,
                "blocking_dimensions": ",".join(evaluation.get("blocking_dimensions") or []) if unified else "not_observed",
                "unobserved_hard_gate_dimensions": ",".join(
                    evaluation.get("unobserved_hard_gate_dimensions") or []
                ) if unified else "not_observed",
            }
        )
    return rows


def _write_quality(rows: list[dict[str, Any]], summary_path: Path, csv_path: Path) -> None:
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        fields = list(rows[0]) if rows else ["qid"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    ready = sum(row.get("release_ready") is True for row in rows)
    complete = sum(row.get("hard_gate_complete") is True for row in rows)
    lines = [
        "# Quality Evaluation Summary",
        "",
        "> `hard_gate_pass` 与 `hard_gate_complete` 分开：缺测不能伪装成绿色。`release_ready` 还要求独立答案质量已观测。",
        "",
        f"- cases: {len(rows)}",
        f"- hard gate complete: {complete}/{len(rows)}",
        f"- release ready: {ready}/{len(rows)}",
        "",
        "| dimension | pass | fail | not observed | not applicable |",
        "| :-- | --: | --: | --: | --: |",
    ]
    for name in DIMENSIONS:
        counts = Counter(str(row.get(name)) for row in rows)
        lines.append(
            f"| {name} | {counts['pass']} | {counts['fail']} | "
            f"{counts['not_observed']} | {counts['not_applicable']} |"
        )
    lines.extend(
        [
            "",
            "## Per case",
            "",
            "| qid | profile | behavior | evidence | prompt | citation | route | answer quality | gate complete | release ready |",
            "| :-- | :-- | :--: | :--: | :--: | :--: | :--: | :--: | :--: | :--: |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row['qid']} | {row['profile']} | {row['behavior']} | {row['expected_evidence']} | "
            f"{row['prompt_evidence']} | {row['citation_validity']} | {row['route_invariants']} | "
            f"{row['answer_quality']} | {row['hard_gate_complete']} | {row['release_ready']} |"
        )
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _hash_manifest(root: Path, *, evidence_class: str) -> dict[str, Any]:
    files: dict[str, Any] = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "manifest.json":
            continue
        data = path.read_bytes()
        files[path.relative_to(root).as_posix()] = {
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    return {
        "schema_version": "1.0.0",
        "evidence_class": evidence_class,
        "files": files,
    }


# 汇总评估与安全证据，生成可复核的发布包。
def build_release_pack(
    records: Iterable[CanonicalExecutionRecord],
    output_dir: str | Path,
    *,
    security_summary: str | Path,
    security_assertions: str | Path,
    evidence_class: str = "historical_bridge",
    suite_label: str = "B2",
) -> dict[str, Path]:
    items = list(records)
    if not items:
        raise ValueError("release pack requires at least one CER")
    if evidence_class not in {"historical_bridge", "final_regression"}:
        raise ValueError("evidence_class must be historical_bridge or final_regression")
    if evidence_class == "final_regression":
        historical = [item for item in items if item.provenance.get("historical_import")]
        if historical:
            raise ValueError("historical imported CER cannot be labelled final_regression")
        incomplete = [
            item.identity.get("qid")
            for item in items
            if item.evaluation.get("release_ready") is not True
        ]
        if incomplete:
            raise ValueError(f"final_regression contains non-release-ready cases: {incomplete}")

    output = Path(output_dir)
    if output.exists():
        raise FileExistsError(f"release output already exists: {output}")
    summaries = output / "summaries"
    tables = output / "tables"
    raw = output / "raw"
    for directory in (summaries, tables, raw):
        directory.mkdir(parents=True, exist_ok=False)

    with tempfile.TemporaryDirectory() as tmp:
        bridge = Path(tmp) / "bridge"
        generated = build_evaluation_reports(items, bridge, suite_label=suite_label)
        shutil.copyfile(generated["summary"], summaries / "final_regression_summary.md")
        shutil.copyfile(generated["per_question"], summaries / "final_regression_per_question.md")
        shutil.copyfile(generated["performance"], summaries / "performance_cost_summary.md")
        shutil.copyfile(generated["cases"], tables / "final_regression_cases.csv")
        shutil.copyfile(generated["timing"], tables / "timing_by_case.csv")
        shutil.copyfile(generated["model_calls"], tables / "model_calls.csv")
        shutil.copyfile(generated["cost"], tables / "cost_ledger.csv")
        shutil.copyfile(
            generated["sanitized_cer"],
            raw / "final_regression_records.sanitized.jsonl",
        )

    security_summary_path = Path(security_summary)
    security_assertions_path = Path(security_assertions)
    if not security_summary_path.is_file() or not security_assertions_path.is_file():
        raise FileNotFoundError("security smoke summary/assertions are required")
    shutil.copyfile(security_summary_path, summaries / "security_smoke_summary.md")
    shutil.copyfile(security_assertions_path, tables / "smoke_assertions.csv")

    quality_rows = _quality_rows(items, evidence_class)
    _write_quality(
        quality_rows,
        summaries / "quality_evaluation_summary.md",
        tables / "quality_metrics.csv",
    )

    historical_count = sum(bool(item.provenance.get("historical_import")) for item in items)
    ready_count = sum(row.get("release_ready") is True for row in quality_rows)
    release_status = "READY" if evidence_class == "final_regression" and ready_count == len(items) else "NOT_RELEASE_READY"
    readme = [
        "# Release Evidence Pack",
        "",
        f"- evidence class: `{evidence_class}`",
        f"- release status: `{release_status}`",
        f"- cases: {len(items)}",
        f"- historical imports: {historical_count}",
        f"- release-ready cases: {ready_count}/{len(items)}",
        "",
    ]
    if evidence_class == "historical_bridge":
        readme.extend(
            [
                "## 使用边界",
                "",
                "这是 Phase-E 冻结结果向 CER/报告合同的历史桥接证据，用于验证字段、投影与账本回算。",
                "它不是终版回归：没有在新索引/新主链上重跑，也没有补造 per-query TopK、grounding、verified citation 或答案质量。",
                "最终发布必须用 `final_regression` 模式重建；该模式会拒绝历史 CER 和任一 `release_ready != true` 的题。",
                "",
            ]
        )
    readme.extend(
        [
            "## 目录",
            "",
            "- `summaries/`：全题、逐题、质量、性能成本与安全摘要。",
            "- `tables/`：可回算的题级、模型调用、成本、质量与 smoke 表。",
            "- `raw/`：只包含经过公开投影的 CER；内部 prompt/chunk 正文与 provider 连接信息已移除。",
            "- `manifest.json`：每个文件的 SHA-256 与字节数。",
            "",
        ]
    )
    (output / "README.md").write_text("\n".join(readme), encoding="utf-8")
    (output / "manifest.json").write_text(
        json.dumps(_hash_manifest(output, evidence_class=evidence_class), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {
        "readme": output / "README.md",
        "manifest": output / "manifest.json",
        "sanitized_records": raw / "final_regression_records.sanitized.jsonl",
        "quality": summaries / "quality_evaluation_summary.md",
        "security": summaries / "security_smoke_summary.md",
    }


__all__ = ["build_release_pack"]
