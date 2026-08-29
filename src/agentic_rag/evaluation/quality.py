"""
程序作用：
把独立产出的答案质量标注绑定到已评估 CER，并用答案哈希防止标注串题或套用到旧答案。

整体结构：
1）answer_sha256 计算当前答案的稳定哈希；
2）apply_quality_annotations 按 qid 匹配标注并校验字段与哈希；
3）将合法标注写入对应 CER 的 answer_quality 断言。
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, Mapping

from agentic_rag.evaluation.assertions import NOT_APPLICABLE, PASS
from agentic_rag.execution.record import CanonicalExecutionRecord


def answer_sha256(record: CanonicalExecutionRecord) -> str:
    answer = str(record.outcome.get("answer") or "")
    return hashlib.sha256(answer.encode("utf-8")).hexdigest()


# 校验题号与答案哈希后，把质量标注写入对应记录。
def apply_quality_annotations(
    records: Iterable[CanonicalExecutionRecord],
    annotations: Iterable[Mapping[str, Any]],
) -> None:
    records_by_qid = {str(record.identity.get("qid") or ""): record for record in records}
    seen: set[str] = set()
    for raw in annotations:
        item = dict(raw)
        allowed = {
            "qid", "answer_sha256", "status", "method", "evaluator",
            "evaluated_at", "reason", "metrics",
        }
        unknown = sorted(set(item) - allowed)
        if unknown:
            raise ValueError(f"unknown quality annotation field(s): {', '.join(unknown)}")
        qid = str(item.get("qid") or "")
        if not qid or qid not in records_by_qid:
            raise ValueError(f"quality annotation qid not present in records: {qid or '<empty>'}")
        if qid in seen:
            raise ValueError(f"duplicate quality annotation: {qid}")
        seen.add(qid)
        status = str(item.get("status") or "").lower()
        if status not in {"pass", "fail"}:
            raise ValueError(f"quality annotation status must be pass/fail: {qid}")
        expected_hash = answer_sha256(records_by_qid[qid])
        if str(item.get("answer_sha256") or "") != expected_hash:
            raise ValueError(f"quality annotation answer hash mismatch: {qid}")
        for required in ("method", "evaluator", "evaluated_at"):
            if not str(item.get(required) or "").strip():
                raise ValueError(f"quality annotation {required} is required: {qid}")

        record = records_by_qid[qid]
        evaluation = dict(record.evaluation or {})
        dimensions = dict(evaluation.get("dimensions") or {})
        dimensions["answer_quality"] = {
            "status": status,
            "method": str(item["method"]),
            "evaluator": str(item["evaluator"]),
            "evaluated_at": str(item["evaluated_at"]),
            "answer_sha256": expected_hash,
            "reason": item.get("reason"),
            "metrics": dict(item.get("metrics") or {}),
        }
        evaluation["dimensions"] = dimensions
        evaluation["release_ready"] = bool(
            evaluation.get("hard_gate_pass") is True
            and evaluation.get("hard_gate_complete") is True
            and status == PASS
        )
        record.evaluation = evaluation

    for qid, record in records_by_qid.items():
        dimensions = dict(record.evaluation.get("dimensions") or {})
        quality_status = dict(dimensions.get("answer_quality") or {}).get("status")
        if quality_status == NOT_APPLICABLE:
            record.evaluation["release_ready"] = bool(
                record.evaluation.get("hard_gate_pass") is True
                and record.evaluation.get("hard_gate_complete") is True
            )


__all__ = ["answer_sha256", "apply_quality_annotations"]
