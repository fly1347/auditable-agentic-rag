"""
D-full Step 14 conflict detection.

作用：
- 对 EvidencePacket 中的多来源证据做轻量冲突检测；
- 仅在显式对比、隐式对比、OPEN_MULTI、SUMMARY 或 sufficiency=CONFLICTED 时触发；
- 默认规则实现，不调用 LLM；
- 输出 ConflictItem[] 与触发/跳过原因；
- detector 失败时由 workflow node 记录 skip_with_log，不阻塞主链路。

整体结构：
1. 判断是否应触发 conflict detection。
2. 从 EvidencePacket 中抽取证据文本与来源。
3. 在不同 source 的证据之间做规则冲突检测。
4. 聚合为 ConflictDetectionReport。
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from itertools import combinations
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


class ConflictType(str, Enum):
    """冲突类型。"""

    NUMERIC_MISMATCH = "numeric_mismatch"
    NEGATION_MISMATCH = "negation_mismatch"
    TERM_LEVEL_TENSION = "term_level_tension"


@dataclass
class ConflictEvidence:
    """用于冲突检测的最小证据块。"""

    evidence_id: str
    source_path: str
    chunk_id: str
    text: str


@dataclass
class ConflictItem:
    """单条冲突记录。"""

    conflict_type: str
    claim_a: str
    claim_b: str
    evidence_a: str
    evidence_b: str
    resolution: str
    uncertainty_level: str


@dataclass
class ConflictDetectionReport:
    """冲突检测报告。"""

    triggered: bool
    trigger_reason: str
    conflicts: List[Dict[str, Any]]
    conflict_count: int
    distinct_sources_in_packet: int
    skipped_reason: Optional[str] = None
    detector: str = "rule_based_conflict_detector"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_TRIGGER_QUESTION_TYPES = {
    "EXPLICIT_COMPARE",
    "IMPLICIT_COMPARE",
    "OPEN_MULTI",
    "SUMMARY",
}


_NEGATION_PATTERNS = [
    r"不是",
    r"不能",
    r"不会",
    r"无需",
    r"不需要",
    r"没有",
    r"并非",
    r"禁止",
    r"无法",
    r"不可",
    r"不支持",
    r"不允许",
    r"不推荐",
    r"\bnever\b",
    r"\bnot\b",
    r"\bno\b",
    r"\bwithout\b",
    r"\bcannot\b",
    r"\bcan't\b",
    r"\bdoes\s+not\b",
    r"\bdo\s+not\b",
]


# 只保留方向明确的成对术语。
# “批处理/连续批处理”“传统/连续”“安全/风险”并不天然互斥，移出冲突规则。
_TENSION_PAIRS = [
    ("同步", "异步"),
    ("有状态", "无状态"),
    ("强一致", "最终一致"),
    ("静态", "动态"),
    ("必须", "可选"),
    ("启用", "禁用"),
    ("允许", "禁止"),
    ("支持", "不支持"),
    ("推荐", "不推荐"),
]


_NUMERIC_FACT_RE = re.compile(
    r"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>%|ms|秒|分钟|小时|GB|MB|KB|TB|tokens?|QPS|RPS|倍|个|项|层|维)",
    flags=re.IGNORECASE,
)


def _to_dict(value: Any) -> Dict[str, Any]:
    """兼容 dict / dataclass / pydantic-like / SimpleNamespace-like 对象。"""
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


def _normalize_text(text: str) -> str:
    text = str(text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _enum_value(value: Any) -> Optional[str]:
    if value is None:
        return None
    if hasattr(value, "value"):
        return str(value.value)
    return str(value)


def _packet_items(evidence_packet: Any) -> List[Any]:
    packet = _to_dict(evidence_packet)
    items = packet.get("items")
    if isinstance(items, list):
        return items
    return []


def _item_get(row: Dict[str, Any], keys: Sequence[str], default: str = "") -> str:
    metadata = _to_dict(row.get("metadata"))
    for key in keys:
        if row.get(key) not in (None, ""):
            return str(row.get(key))
        if metadata.get(key) not in (None, ""):
            return str(metadata.get(key))
    return default


def collect_conflict_evidence(evidence_packet: Any, *, max_items: int = 8) -> List[ConflictEvidence]:
    """从 EvidencePacket 中抽取冲突检测所需证据。"""
    out: List[ConflictEvidence] = []

    for idx, item in enumerate(_packet_items(evidence_packet)):
        row = _to_dict(item)
        if not row:
            continue

        text = _item_get(
            row,
            ["text", "content", "chunk_text", "text_preview", "snippet", "preview", "page_content"],
            "",
        )
        text = _normalize_text(text)
        if not text:
            continue

        chunk_id = _item_get(row, ["chunk_id", "id"], "")
        source_path = _item_get(row, ["source_path", "source", "source_id", "path", "file_path", "title"], "")
        evidence_id = _item_get(row, ["evidence_id", "chunk_id", "id"], "") or chunk_id or f"evidence_{idx}"

        out.append(
            ConflictEvidence(
                evidence_id=evidence_id,
                source_path=source_path,
                chunk_id=chunk_id,
                text=text,
            )
        )

    return out[:max_items]


def distinct_sources(evidence_packet: Any) -> List[str]:
    """统计 EvidencePacket 中不同来源。"""
    sources: List[str] = []
    for item in collect_conflict_evidence(evidence_packet):
        source = item.source_path or item.evidence_id
        if source and source not in sources:
            sources.append(source)
    return sources


def should_trigger_conflict_detection(
    *,
    evidence_packet: Any,
    question_type: Optional[str],
    sufficiency_verdict: Optional[str],
) -> Tuple[bool, str]:
    """
    判断是否触发 conflict detection。

    触发条件：
    - sufficiency_verdict == CONFLICTED；或
    - distinct_sources_in_packet >= 2 且 question_type 属于对比/开放聚合类。
    """
    sources = distinct_sources(evidence_packet)
    source_count = len(sources)
    qt = str(question_type or "").upper()
    verdict = str(sufficiency_verdict or "").upper()

    if verdict == "CONFLICTED":
        return True, "sufficiency_verdict_conflicted"

    if source_count < 2:
        return False, "distinct_sources_lt_2"

    if qt in _TRIGGER_QUESTION_TYPES:
        return True, f"question_type_{qt}_with_multi_source"

    return False, f"question_type_{qt or 'UNKNOWN'}_not_triggered"


def _sentences(text: str, *, max_sentences: int = 4) -> List[str]:
    parts = re.split(r"[。！？!?；;]\s*|\n+", text)
    out: List[str] = []
    for part in parts:
        item = _normalize_text(part)
        if len(item) >= 8:
            out.append(item)
    return out[:max_sentences]


def _numeric_facts(text: str) -> Dict[str, set[str]]:
    """只抽取带明确单位的数字事实，避免标题编号、向量样例等裸数字造成假冲突。"""
    facts: Dict[str, set[str]] = {}
    for match in _NUMERIC_FACT_RE.finditer(text):
        unit = str(match.group("unit") or "").lower()
        value = str(match.group("value") or "")
        if not unit or not value:
            continue
        facts.setdefault(unit, set()).add(value)
    return facts


def _has_negation(text: str) -> bool:
    """识别明确否定表达；不再用单字“不”做触发，避免“不同/不知”等误报。"""
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in _NEGATION_PATTERNS)


def _has_exclusive_term(text: str, term: str, opposite: str) -> bool:
    """仅当本句包含一侧且不同时包含另一侧时，才视为方向性术语。"""
    return term in text and opposite not in text


def _latin_tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_.+-]{1,}", text)
        if len(token) >= 2
    }


def _cn_terms(text: str) -> set[str]:
    terms = set(re.findall(r"[\u4e00-\u9fff]{2,}", text))
    return {term for term in terms if len(term) >= 2}


def _overlap_score(a: str, b: str) -> float:
    a_terms = _latin_tokens(a) | _cn_terms(a)
    b_terms = _latin_tokens(b) | _cn_terms(b)
    if not a_terms or not b_terms:
        return 0.0
    return len(a_terms & b_terms) / max(len(a_terms | b_terms), 1)


def _detect_pair_conflict(a: ConflictEvidence, b: ConflictEvidence) -> Optional[ConflictItem]:
    if a.source_path and b.source_path and a.source_path == b.source_path:
        return None

    best: Optional[Tuple[str, str, str, float]] = None

    for sent_a in _sentences(a.text):
        for sent_b in _sentences(b.text):
            overlap = _overlap_score(sent_a, sent_b)
            if overlap < 0.08:
                continue

            facts_a = _numeric_facts(sent_a)
            facts_b = _numeric_facts(sent_b)
            shared_units = set(facts_a) & set(facts_b)
            numeric_mismatch = any(facts_a[unit] != facts_b[unit] for unit in shared_units)
            if numeric_mismatch and overlap >= 0.18:
                score = overlap + 0.3
                if best is None or score > best[3]:
                    best = (ConflictType.NUMERIC_MISMATCH.value, sent_a, sent_b, score)

            if _has_negation(sent_a) != _has_negation(sent_b) and overlap >= 0.20:
                score = overlap + 0.2
                if best is None or score > best[3]:
                    best = (ConflictType.NEGATION_MISMATCH.value, sent_a, sent_b, score)

            for left, right in _TENSION_PAIRS:
                opposite = (
                    _has_exclusive_term(sent_a, left, right)
                    and _has_exclusive_term(sent_b, right, left)
                ) or (
                    _has_exclusive_term(sent_a, right, left)
                    and _has_exclusive_term(sent_b, left, right)
                )
                if opposite and overlap >= 0.16:
                    score = overlap + 0.1
                    if best is None or score > best[3]:
                        best = (ConflictType.TERM_LEVEL_TENSION.value, sent_a, sent_b, score)

    if best is None:
        return None

    conflict_type, claim_a, claim_b, score = best
    # score 越高，规则证据越强；high 表示冲突导致的不确定性更高。
    uncertainty = "high" if score >= 0.45 else "medium"

    return ConflictItem(
        conflict_type=conflict_type,
        claim_a=claim_a,
        claim_b=claim_b,
        evidence_a=a.evidence_id,
        evidence_b=b.evidence_id,
        resolution="needs_manual_review",
        uncertainty_level=uncertainty,
    )


def detect_conflicts(
    *,
    evidence_packet: Any,
    question_type: Optional[str] = None,
    sufficiency_verdict: Optional[str] = None,
    force: bool = False,
    max_conflicts: int = 5,
) -> ConflictDetectionReport:
    """
    执行规则冲突检测。

    默认先判断触发条件；force=True 用于 smoke / 专项测试。
    """
    trigger, reason = should_trigger_conflict_detection(
        evidence_packet=evidence_packet,
        question_type=question_type,
        sufficiency_verdict=sufficiency_verdict,
    )
    sources = distinct_sources(evidence_packet)

    if not trigger and not force:
        return ConflictDetectionReport(
            triggered=False,
            trigger_reason=reason,
            conflicts=[],
            conflict_count=0,
            distinct_sources_in_packet=len(sources),
            skipped_reason=reason,
        )

    evidence = collect_conflict_evidence(evidence_packet)
    conflicts: List[ConflictItem] = []

    for a, b in combinations(evidence, 2):
        item = _detect_pair_conflict(a, b)
        if item is None:
            continue
        conflicts.append(item)
        if len(conflicts) >= max_conflicts:
            break

    return ConflictDetectionReport(
        triggered=True,
        trigger_reason=reason if not force else f"force:{reason}",
        conflicts=[asdict(item) for item in conflicts],
        conflict_count=len(conflicts),
        distinct_sources_in_packet=len(sources),
        skipped_reason=None,
    )
