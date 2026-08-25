"""
作用：
- 提供 D-full Step 15 的 UncertaintyReport 规则聚合逻辑。
- 消费 sufficiency / conflicts / citation_support / EvidencePacket.known_gaps / refused_reason。
- 输出 level / reasons / missing_info / safe_answer_boundary / next_steps。
- 不调用 LLM，不进入生成逻辑，不生成通用空话 next_steps。

整体结构：
1. 兼容 dict / dataclass / SimpleNamespace 的输入读取。
2. 从 sufficiency、conflict、citation_support、known_gaps 中提取风险信号。
3. 按规则聚合 uncertainty level。
4. 生成有限模板化 next_steps。
"""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

from agentic_rag.workflow.workflow_state import UncertaintyReport


class UncertaintyLevel(str, Enum):
    """作用：标识最终回答的不确定性等级；high 表示不确定性/风险高。"""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class UncertaintyReason(str, Enum):
    """作用：记录触发 uncertainty 的规则原因。"""

    REFUSED = "refused"
    SUFFICIENCY_INSUFFICIENT = "sufficiency_insufficient"
    SUFFICIENCY_CONFLICTED = "sufficiency_conflicted"
    CONFLICT_DETECTED = "conflict_detected"
    CITATION_WEAK = "citation_weak"
    KNOWN_GAPS = "known_gaps"


_LEVEL_RANK = {
    UncertaintyLevel.LOW.value: 0,
    UncertaintyLevel.MEDIUM.value: 1,
    UncertaintyLevel.HIGH.value: 2,
}


def _to_dict(value: Any) -> Dict[str, Any]:
    """作用：兼容 dict / dataclass / to_dict / SimpleNamespace-like 对象。"""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if is_dataclass(value):
        return asdict(value)
    if hasattr(value, "to_dict"):
        try:
            out = value.to_dict()
            return out if isinstance(out, dict) else {}
        except Exception:
            return {}
    if hasattr(value, "__dict__"):
        try:
            return dict(value.__dict__)
        except Exception:
            return {}
    return {}


def _listify(value: Any) -> List[Any]:
    """作用：把输入安全转成 list。"""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return list(value)
    return [value]


def _dedupe_text(items: Sequence[Any]) -> List[str]:
    """作用：去重并过滤空字符串。"""
    out: List[str] = []
    seen: set[str] = set()
    for item in items:
        text = str(item or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        out.append(text)
    return out


def _raise_level(current: str, candidate: str) -> str:
    """作用：取更高 uncertainty level。"""
    return candidate if _LEVEL_RANK[candidate] > _LEVEL_RANK[current] else current


def _extract_sufficiency(sufficiency: Any) -> Tuple[Optional[str], Optional[str], List[str], Optional[str]]:
    """作用：从 sufficiency node 输出中提取 verdict / confidence / missing_evidence / reason。"""
    row = _to_dict(sufficiency)
    result = _to_dict(row.get("result")) if row.get("result") is not None else row

    verdict = result.get("verdict") or row.get("verdict")
    confidence = result.get("confidence") or row.get("confidence")
    reason = result.get("reason") or row.get("reason")
    missing = (
        result.get("missing_evidence")
        or row.get("missing_evidence")
        or row.get("sufficiency_missing_evidence")
        or []
    )

    return (
        str(verdict).upper() if verdict else None,
        str(confidence).lower() if confidence else None,
        _dedupe_text(_listify(missing)),
        str(reason).strip() if reason else None,
    )


def _extract_conflicts(conflicts: Any) -> Tuple[int, List[str]]:
    """作用：从 conflict_detection report 或 conflicts list 中提取冲突数量与冲突等级。"""
    row = _to_dict(conflicts)
    if row:
        conflict_items = _listify(row.get("conflicts"))
        count = int(row.get("conflict_count") or len(conflict_items))
    else:
        conflict_items = _listify(conflicts)
        count = len(conflict_items)

    levels: List[str] = []
    for item in conflict_items:
        item_row = _to_dict(item)
        level = item_row.get("uncertainty_level")
        if level:
            levels.append(str(level).lower())

    return count, levels


def _extract_citation_support(citation_support: Any) -> Tuple[Optional[str], int, List[str]]:
    """作用：读取 citation_support label / unsupported_claim_count / borderline_dimension。"""
    row = _to_dict(citation_support)
    label = row.get("citation_support_label")
    unsupported = row.get("unsupported_claim_count") or 0
    borderline = row.get("borderline_dimension") or []

    try:
        unsupported_count = int(unsupported)
    except (TypeError, ValueError):
        unsupported_count = 0

    return (
        str(label).lower() if label else None,
        unsupported_count,
        _dedupe_text(_listify(borderline)),
    )


def _extract_known_gaps(evidence_packet: Any) -> List[str]:
    """作用：读取 EvidencePacket.known_gaps。"""
    row = _to_dict(evidence_packet)
    return _dedupe_text(_listify(row.get("known_gaps")))


def _build_safe_answer_boundary(reasons: Sequence[str]) -> Optional[str]:
    """作用：根据触发原因生成回答边界，不在 low 风险时输出空话。"""
    parts: List[str] = []

    if UncertaintyReason.SUFFICIENCY_INSUFFICIENT.value in reasons:
        parts.append("当前证据不足，回答边界应限制在已检索到的证据范围内，不能补全缺失信息。")
    if UncertaintyReason.SUFFICIENCY_CONFLICTED.value in reasons or UncertaintyReason.CONFLICT_DETECTED.value in reasons:
        parts.append("证据之间存在冲突，不能合并成单一确定结论。")
    if UncertaintyReason.CITATION_WEAK.value in reasons:
        parts.append("部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。")
    if UncertaintyReason.KNOWN_GAPS.value in reasons:
        parts.append("EvidencePacket 已记录证据缺口，未覆盖部分不能视为已证实结论。")
    if UncertaintyReason.REFUSED.value in reasons and not parts:
        parts.append("当前问题未形成可安全回答的证据边界。")

    return "；".join(parts) if parts else None


def _build_next_steps(reasons: Sequence[str]) -> List[str]:
    """作用：只在拒答、冲突、citation_weak、known_gaps 场景生成模板化 next_steps。"""
    steps: List[str] = []

    if (
        UncertaintyReason.REFUSED.value in reasons
        or UncertaintyReason.SUFFICIENCY_INSUFFICIENT.value in reasons
    ):
        steps.append("补充缺失证据后重新运行检索与 sufficiency 判定。")

    if (
        UncertaintyReason.SUFFICIENCY_CONFLICTED.value in reasons
        or UncertaintyReason.CONFLICT_DETECTED.value in reasons
    ):
        steps.append("人工核对冲突证据，确认采用哪一份来源，或标注冲突仍未解决。")

    if UncertaintyReason.CITATION_WEAK.value in reasons:
        steps.append("回看 partial / unsupported claims 与实际引用证据，必要时收紧回答或修正引用。")

    if UncertaintyReason.KNOWN_GAPS.value in reasons:
        steps.append("针对 known_gaps 定向补检索或补充语料。")

    return _dedupe_text(steps)


def uncertainty_report_to_dict(report: UncertaintyReport) -> Dict[str, Any]:
    """作用：把 UncertaintyReport 转成可序列化 dict。"""
    if is_dataclass(report):
        return asdict(report)
    return {
        "level": getattr(report, "level", None),
        "reasons": list(getattr(report, "reasons", []) or []),
        "missing_info": list(getattr(report, "missing_info", []) or []),
        "safe_answer_boundary": getattr(report, "safe_answer_boundary", None),
        "next_steps": list(getattr(report, "next_steps", []) or []),
    }


def build_uncertainty_report(
    *,
    sufficiency: Any = None,
    conflicts: Any = None,
    citation_support: Any = None,
    evidence_packet: Any = None,
    refused_reason: Optional[str] = None,
) -> UncertaintyReport:
    """
    作用：
    - 聚合 Step 10 / 13 / 14 / EvidencePacket 的风险信号。
    - 返回 workflow_state.UncertaintyReport。
    """
    level = UncertaintyLevel.LOW.value
    reasons: List[str] = []
    missing_info: List[str] = []

    refused_text = str(refused_reason or "").strip()
    if refused_text:
        level = _raise_level(level, UncertaintyLevel.MEDIUM.value)
        reasons.append(UncertaintyReason.REFUSED.value)
        missing_info.append(refused_text)

    verdict, confidence, suff_missing, suff_reason = _extract_sufficiency(sufficiency)
    if verdict == "INSUFFICIENT":
        target = (
            UncertaintyLevel.HIGH.value
            if confidence in {"high", "medium"} or bool(refused_text)
            else UncertaintyLevel.MEDIUM.value
        )
        level = _raise_level(level, target)
        reasons.append(UncertaintyReason.SUFFICIENCY_INSUFFICIENT.value)
        missing_info.extend(suff_missing)
        if suff_reason:
            missing_info.append(suff_reason)
    elif verdict == "CONFLICTED":
        level = _raise_level(level, UncertaintyLevel.HIGH.value)
        reasons.append(UncertaintyReason.SUFFICIENCY_CONFLICTED.value)
        missing_info.extend(suff_missing)
        if suff_reason:
            missing_info.append(suff_reason)

    conflict_count, conflict_levels = _extract_conflicts(conflicts)
    if conflict_count > 0:
        target = (
            UncertaintyLevel.HIGH.value
            if "high" in conflict_levels
            else UncertaintyLevel.MEDIUM.value
        )
        level = _raise_level(level, target)
        reasons.append(UncertaintyReason.CONFLICT_DETECTED.value)
        missing_info.append("conflict_resolution_required")

    citation_label, unsupported_count, borderline = _extract_citation_support(citation_support)
    if citation_label in {"unsupported", "no_evidence"}:
        level = _raise_level(level, UncertaintyLevel.HIGH.value)
        reasons.append(UncertaintyReason.CITATION_WEAK.value)
        missing_info.append(f"citation_support_label={citation_label}")
        if unsupported_count:
            missing_info.append(f"unsupported_claim_count={unsupported_count}")
        missing_info.extend(borderline)
    elif citation_label == "partial" or unsupported_count > 0:
        target = UncertaintyLevel.HIGH.value if unsupported_count > 0 else UncertaintyLevel.MEDIUM.value
        level = _raise_level(level, target)
        reasons.append(UncertaintyReason.CITATION_WEAK.value)
        missing_info.append(f"citation_support_label={citation_label or 'unknown'}")
        if unsupported_count:
            missing_info.append(f"unsupported_claim_count={unsupported_count}")
        missing_info.extend(borderline)

    known_gaps = _extract_known_gaps(evidence_packet)
    if known_gaps:
        level = _raise_level(level, UncertaintyLevel.MEDIUM.value)
        reasons.append(UncertaintyReason.KNOWN_GAPS.value)
        missing_info.extend(known_gaps)

    reasons = _dedupe_text(reasons)
    missing_info = _dedupe_text(missing_info)

    return UncertaintyReport(
        level=level,
        reasons=reasons,
        missing_info=missing_info,
        safe_answer_boundary=_build_safe_answer_boundary(reasons),
        next_steps=_build_next_steps(reasons),
    )
