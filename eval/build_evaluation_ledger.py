#!/usr/bin/env python3
"""
程序作用：
汇总在线主链、离线 D-full 与 RAGAS 三类评估记录，生成互不重叠的耗时、Token 和成本账本。

整体结构：
1）读取并清洗三类 JSONL 记录，统一模型调用字段；
2）按评估类别计算覆盖率、耗时、Token 与成本汇总；
3）输出明细 CSV、汇总 JSON 和便于核对的 Markdown 报告。
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional

from agentic_rag.cost.pricing import estimate_usage_costs
from agentic_rag.evaluation.offline_record import OfflineEvaluationRecord, stable_sha256
from agentic_rag.execution.record import CanonicalExecutionRecord


TOKEN_FIELDS = (
    "prompt_tokens",
    "completion_tokens",
    "reasoning_tokens",
    "cached_tokens",
    "cache_write_tokens",
    "total_tokens",
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="build_evaluation_ledger")
    parser.add_argument("--online-records", type=Path, required=True)
    parser.add_argument("--offline-records", type=Path, default=None)
    parser.add_argument("--ragas-records", type=Path, default=None)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(path)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _online(path: Path) -> tuple[list[dict[str, Any]], float, int, int]:
    records = [CanonicalExecutionRecord.from_dict(row) for row in _read_jsonl(path)]
    calls: list[dict[str, Any]] = []
    time_ms = 0.0
    unknown_time_records = 0
    for record in records:
        qid = str(record.identity.get("qid") or "")
        observed_time = _optional_float(record.timing.get("service_total_ms"))
        if observed_time is None:
            unknown_time_records += 1
        else:
            time_ms += observed_time
        priced = estimate_usage_costs({"model_calls": record.model_calls, "totals": record.usage})
        for index, raw in enumerate(list(priced.get("model_calls") or []), start=1):
            call = dict(raw)
            call["category"] = "online"
            call["qid"] = qid
            call["index"] = call.get("index") or index
            call["call_id"] = call.get("call_id") or stable_sha256(
                {
                    "category": "online",
                    "run_id": record.identity.get("run_id"),
                    "qid": qid,
                    "index": call["index"],
                    "stage": call.get("stage"),
                    "role": call.get("role"),
                }
            )[:24]
            calls.append(call)
    return calls, time_ms, len(records), unknown_time_records


def _offline(path: Optional[Path]) -> tuple[list[dict[str, Any]], float, int, int]:
    if path is None:
        return [], 0.0, 0, 0
    records = [OfflineEvaluationRecord.from_dict(row) for row in _read_jsonl(path)]
    calls = []
    time_ms = 0.0
    unknown_time_records = 0
    for record in records:
        observed_time = _optional_float(record.timing.get("offline_total_ms"))
        if observed_time is None:
            unknown_time_records += 1
        else:
            time_ms += observed_time
        for raw in record.model_calls:
            calls.append({"category": "offline_dfull", "qid": record.identity.get("qid"), **dict(raw)})
    return calls, time_ms, len(records), unknown_time_records


def _ragas(path: Optional[Path]) -> tuple[list[dict[str, Any]], float, int, int]:
    if path is None:
        return [], 0.0, 0, 0
    records = _read_jsonl(path)
    calls = []
    time_ms = 0.0
    unknown_time_records = 0
    for record in records:
        observed_time = _optional_float(record.get("duration_ms"))
        if observed_time is None:
            unknown_time_records += 1
        else:
            time_ms += observed_time
        for raw in list(record.get("model_calls") or []):
            if isinstance(raw, Mapping):
                calls.append({"category": "ragas", "qid": record.get("qid"), **dict(raw)})
    return calls, time_ms, len(records), unknown_time_records


def _optional_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _optional_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dedupe(calls: Iterable[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    unique: dict[str, dict[str, Any]] = {}
    duplicates = 0
    for raw in calls:
        call = dict(raw)
        call_id = str(call.get("call_id") or "")
        if not call_id:
            call_id = stable_sha256(call)[:24]
            call["call_id"] = call_id
        if call_id in unique:
            if stable_sha256(unique[call_id]) != stable_sha256(call):
                raise ValueError(f"conflicting model calls share call_id: {call_id}")
            duplicates += 1
            continue
        unique[call_id] = call
    return list(unique.values()), duplicates


def _category_summary(
    category: str,
    calls: list[dict[str, Any]],
    *,
    time_ms: float,
    record_count: int,
    unknown_time_record_count: int = 0,
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "category": category,
        "record_count": record_count,
        "time_sum_ms": time_ms if not unknown_time_record_count else None,
        "time_observed_sum_ms": time_ms,
        "time_unknown_record_count": unknown_time_record_count,
        "model_call_count": len(calls),
    }
    for key in TOKEN_FIELDS:
        observed = [_optional_int(call.get(key)) for call in calls]
        values = [value for value in observed if value is not None]
        unknown_count = len(calls) - len(values)
        observed_sum = sum(values)
        # 部分调用缺字段时，已知小计只用于诊断；规范总计必须留空，不能伪装成完整账单。
        row[key] = observed_sum if not unknown_count else None
        row[f"{key}_observed_sum"] = observed_sum
        row[f"{key}_unknown_call_count"] = unknown_count
    costs = [_optional_float(call.get("estimated_cost_usd")) for call in calls]
    observed_costs = [value for value in costs if value is not None]
    unpriced_count = len(calls) - len(observed_costs)
    observed_cost_sum = sum(observed_costs)
    row["estimated_cost_usd"] = observed_cost_sum if not unpriced_count else None
    row["estimated_cost_usd_observed_sum"] = observed_cost_sum
    row["priced_call_count"] = len(observed_costs)
    row["unpriced_call_count"] = unpriced_count
    return row


def _sanitize_call(call: Mapping[str, Any]) -> dict[str, Any]:
    row = dict(call)
    for key in (
        "endpoint",
        "base_url",
        "api_key",
        "api_key_env",
        "api_key_hash",
        "prompt",
        "error_message",
    ):
        row.pop(key, None)
    return row


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row}) or ["category"]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _source_file(path: Optional[Path]) -> Optional[dict[str, Any]]:
    if path is None:
        return None
    payload = path.read_bytes()
    return {"path": str(path), "bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest()}


def _display(value: Any) -> str:
    return "not_observed" if value in (None, "") else str(value)


def _display_ms(value: Any) -> str:
    number = _optional_float(value)
    return "not_observed" if number is None else f"{number:.3f}"


def _profile_from_online_records(path: Path) -> str:
    rows = _read_jsonl(path)
    if not rows:
        return "unknown"
    profile = str(((rows[0].get("provenance") or {}).get("profile") or "unknown")).strip()
    return profile or "unknown"


def _human_category(category: str) -> str:
    return {
        "online": "在线主链",
        "offline_dfull": "D-full 后置评测",
        "ragas": "RAGAS 离线质量评测",
        "combined": "三类合计",
    }.get(category, category)


def _category_scope(category: str) -> str:
    return {
        "online": "在线回答生产与主链控制调用",
        "offline_dfull": "D-full classifier + 本地 citation/conflict/uncertainty 后置诊断",
        "ragas": "Context Precision / Faithfulness / Answer Relevancy 指标任务",
        "combined": "以上三类互不重叠账目合计",
    }.get(category, "")


def _format_seconds(value: Any) -> str:
    number = _optional_float(value)
    if number is None:
        return "not_observed"
    seconds = number / 1000.0
    if seconds >= 60.0:
        return f"{seconds:.3f} s（{seconds / 60.0:.2f} min）"
    return f"{seconds:.3f} s"


def _format_int(value: Any) -> str:
    number = _optional_int(value)
    return "not_observed" if number is None else f"{number:,}"


def _format_cost(value: Any) -> str:
    number = _optional_float(value)
    return "not_observed" if number is None else f"${number:.6f}"


def _share(value: Any, total: Any) -> str:
    numerator = _optional_float(value)
    denominator = _optional_float(total)
    if numerator is None or denominator in (None, 0.0):
        return "not_observed"
    return f"{numerator / denominator * 100.0:.1f}%"


def _coverage_text(row: Mapping[str, Any], unknown_key: str) -> str:
    unknown = _optional_int(row.get(unknown_key)) or 0
    calls = _optional_int(row.get("model_call_count")) or 0
    if calls == 0:
        return "无模型调用"
    if unknown == 0:
        return "完整"
    return f"部分缺失（{unknown}/{calls} calls 未观测）"


def _summary_markdown(
    profile: str,
    summaries: list[dict[str, Any]],
    *,
    duplicate_count: int,
) -> str:
    by_category = {str(row.get("category")): row for row in summaries}
    combined = by_category["combined"]
    detail_rows = [
        by_category[name]
        for name in ("online", "offline_dfull", "ragas")
        if name in by_category
    ]

    lines = [
        f"# Evaluation {profile} Timing-Usage-Cost 三类总账",
        "",
        "> 本报告把在线主链、D-full 后置评测、RAGAS 离线质量评测分账展示。三类模型调用互不重复；combined 只是账目求和。",
        "> `time_sum` 是各题/各指标任务观测耗时的求和，不等同于整批任务的墙钟运行时间；RAGAS 的 3 个指标按独立任务累计。",
        "> 费用为静态价格表估算，用于工程成本比较，不作为 provider 账单对账结果。",
        "",
        "## 1. 总账摘要",
        "",
        f"- profile: `{profile}`",
        f"- 去重模型调用: `{duplicate_count}`",
        f"- 三类模型调用合计: **{_format_int(combined.get('model_call_count'))} calls**",
        f"- 三类 Token 合计: **{_format_int(combined.get('total_tokens'))}**",
        f"- 三类估算费用合计: **{_format_cost(combined.get('estimated_cost_usd'))}**",
        f"- 三类观测任务耗时累计: **{_format_seconds(combined.get('time_sum_ms'))}**",
        "",
        "| 类别 | 统计对象 | records / tasks | model calls | time_sum | total tokens | estimated cost |",
        "| :-- | :-- | --: | --: | --: | --: | --: |",
    ]
    for row in detail_rows:
        lines.append(
            f"| {_human_category(str(row['category']))} | {_category_scope(str(row['category']))} | "
            f"{_format_int(row.get('record_count'))} | {_format_int(row.get('model_call_count'))} | "
            f"{_format_seconds(row.get('time_sum_ms'))} | {_format_int(row.get('total_tokens'))} | "
            f"{_format_cost(row.get('estimated_cost_usd'))} |"
        )
    lines.append(
        f"| **三类合计** | {_category_scope('combined')} | {_format_int(combined.get('record_count'))} | "
        f"{_format_int(combined.get('model_call_count'))} | {_format_seconds(combined.get('time_sum_ms'))} | "
        f"{_format_int(combined.get('total_tokens'))} | {_format_cost(combined.get('estimated_cost_usd'))} |"
    )

    lines.extend(
        [
            "",
            "### records / tasks 口径",
            "",
            "- `online`：按在线 CER 题目计数。",
            "- `offline_dfull`：按 D-full 后置评测题目计数。",
            "- `ragas`：按“题目 × 指标”任务计数，因此不是参与 RAGAS 的唯一题数。",
            "- `三类合计`：只是三个类别的记录/任务数相加，不代表唯一问题数。",
            "",
            "## 2. 资源占比",
            "",
            "> 这一节用于快速看成本主要花在哪里；占比均以三类合计为分母。",
            "",
            "| 类别 | calls 占比 | Token 占比 | 费用占比 | time_sum 占比 |",
            "| :-- | --: | --: | --: | --: |",
        ]
    )
    for row in detail_rows:
        lines.append(
            f"| {_human_category(str(row['category']))} | "
            f"{_share(row.get('model_call_count'), combined.get('model_call_count'))} | "
            f"{_share(row.get('total_tokens'), combined.get('total_tokens'))} | "
            f"{_share(row.get('estimated_cost_usd'), combined.get('estimated_cost_usd'))} | "
            f"{_share(row.get('time_sum_ms'), combined.get('time_sum_ms'))} |"
        )

    lines.extend(
        [
            "",
            "## 3. Token 与费用明细",
            "",
            "| 类别 | prompt | completion | reasoning | cached | cache write | total tokens | priced / unpriced | estimated cost |",
            "| :-- | --: | --: | --: | --: | --: | --: | :-- | --: |",
        ]
    )
    for row in detail_rows:
        lines.append(
            f"| {_human_category(str(row['category']))} | {_format_int(row.get('prompt_tokens'))} | "
            f"{_format_int(row.get('completion_tokens'))} | {_format_int(row.get('reasoning_tokens'))} | "
            f"{_format_int(row.get('cached_tokens'))} | {_format_int(row.get('cache_write_tokens'))} | "
            f"{_format_int(row.get('total_tokens'))} | {row.get('priced_call_count')}/{row.get('unpriced_call_count')} | "
            f"{_format_cost(row.get('estimated_cost_usd'))} |"
        )
    lines.append(
        f"| **三类合计** | {_format_int(combined.get('prompt_tokens'))} | "
        f"{_format_int(combined.get('completion_tokens'))} | {_format_int(combined.get('reasoning_tokens'))} | "
        f"{_format_int(combined.get('cached_tokens'))} | {_format_int(combined.get('cache_write_tokens'))} | "
        f"{_format_int(combined.get('total_tokens'))} | {combined.get('priced_call_count')}/{combined.get('unpriced_call_count')} | "
        f"{_format_cost(combined.get('estimated_cost_usd'))} |"
    )

    lines.extend(
        [
            "",
            "## 4. 观测完整性",
            "",
            "> Provider 未返回的 token 明细保持 unknown，不用 0 冒充真实值；完整的 `total_tokens` 与费用仍可正常用于总账。",
            "",
            "| 类别 | time | reasoning tokens | cached tokens | cache-write tokens | cost |",
            "| :-- | :-- | :-- | :-- | :-- | :-- |",
        ]
    )
    for row in detail_rows:
        time_unknown = _optional_int(row.get("time_unknown_record_count")) or 0
        time_records = _optional_int(row.get("record_count")) or 0
        time_status = "完整" if time_unknown == 0 else f"部分缺失（{time_unknown}/{time_records} records 未观测）"
        cost_unknown = _optional_int(row.get("unpriced_call_count")) or 0
        call_count = _optional_int(row.get("model_call_count")) or 0
        cost_status = "完整" if cost_unknown == 0 else f"部分缺失（{cost_unknown}/{call_count} calls 未定价）"
        lines.append(
            f"| {_human_category(str(row['category']))} | {time_status} | "
            f"{_coverage_text(row, 'reasoning_tokens_unknown_call_count')} | "
            f"{_coverage_text(row, 'cached_tokens_unknown_call_count')} | "
            f"{_coverage_text(row, 'cache_write_tokens_unknown_call_count')} | {cost_status} |"
        )

    lines.extend(
        [
            "",
            "## 5. 机器底账",
            "",
            "- `evaluation_totals.csv`：三类及 combined 的完整汇总字段。",
            "- `model_calls_combined.csv`：去重后的逐次模型调用明细。",
            "- `manifest.json`：输入文件哈希、去重数量、combined 汇总与输出哈希。",
            "",
        ]
    )
    return "\n".join(lines)


# 读取三类评估产物并生成统一账本。
def main() -> int:
    args = arguments()
    if args.output_dir.exists() and any(args.output_dir.iterdir()):
        raise SystemExit(f"output directory is not empty: {args.output_dir}")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    profile = _profile_from_online_records(args.online_records)
    online_calls, online_time, online_records, online_time_unknown = _online(args.online_records)
    offline_calls, offline_time, offline_records, offline_time_unknown = _offline(args.offline_records)
    ragas_calls, ragas_time, ragas_records, ragas_time_unknown = _ragas(args.ragas_records)
    calls, duplicate_count = _dedupe([*online_calls, *offline_calls, *ragas_calls])
    by_category = {
        "online": [call for call in calls if call.get("category") == "online"],
        "offline_dfull": [call for call in calls if call.get("category") == "offline_dfull"],
        "ragas": [call for call in calls if call.get("category") == "ragas"],
    }
    summaries = [
        _category_summary(
            "online", by_category["online"], time_ms=online_time,
            record_count=online_records, unknown_time_record_count=online_time_unknown,
        ),
        _category_summary(
            "offline_dfull", by_category["offline_dfull"], time_ms=offline_time,
            record_count=offline_records, unknown_time_record_count=offline_time_unknown,
        ),
        _category_summary(
            "ragas", by_category["ragas"], time_ms=ragas_time,
            record_count=ragas_records, unknown_time_record_count=ragas_time_unknown,
        ),
    ]
    combined = _category_summary(
        "combined",
        calls,
        time_ms=online_time + offline_time + ragas_time,
        record_count=online_records + offline_records + ragas_records,
        unknown_time_record_count=online_time_unknown + offline_time_unknown + ragas_time_unknown,
    )
    summaries.append(combined)

    totals_csv = args.output_dir / "evaluation_totals.csv"
    calls_csv = args.output_dir / "model_calls_combined.csv"
    summary_md = args.output_dir / f"Evaluation-{profile}-Timing-Usage-Cost总账.md"
    manifest_path = args.output_dir / "manifest.json"
    _write_csv(totals_csv, summaries)
    _write_csv(calls_csv, [_sanitize_call(call) for call in calls])

    summary_md.write_text(
        _summary_markdown(profile, summaries, duplicate_count=duplicate_count),
        encoding="utf-8",
    )

    manifest = {
        "schema_version": "1.0.0",
        "sources": {
            "online": _source_file(args.online_records),
            "offline_dfull": _source_file(args.offline_records),
            "ragas": _source_file(args.ragas_records),
        },
        "duplicate_model_call_count": duplicate_count,
        "combined": combined,
        "outputs": {},
    }
    for path in (totals_csv, calls_csv, summary_md):
        payload = path.read_bytes()
        manifest["outputs"][path.name] = {
            "bytes": len(payload),
            "sha256": hashlib.sha256(payload).hexdigest(),
        }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"summary: {summary_md}", flush=True)
    print(f"totals: {totals_csv}", flush=True)
    print(f"model calls: {calls_csv}", flush=True)
    print(f"manifest: {manifest_path}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
