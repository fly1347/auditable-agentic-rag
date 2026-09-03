"""
作用：
- 提供 D-full Step 9 EvidencePacket 的轻量诊断函数。
- 只基于 RetrievalResult / EvidenceItem 计算 source coverage、score summary 与 known gaps。
- 不接 sufficiency / citation_support / conflict detection。

整体结构：
1. summarize_source_coverage：统计证据来源覆盖。
2. summarize_scores：统计 vector / rerank 分数。
3. annotate_evidence_items_for_eval：评测模式下标注 expected / answer-bearing / prompt 命中。
4. detect_known_gaps：记录空证据、低覆盖、source hit chunk miss 等诊断缺口。
"""

from __future__ import annotations

from statistics import mean
from typing import Any, Dict, Iterable, List, Optional, Sequence

from agentic_rag.workflow.workflow_state import EvidenceItem


def _safe_float_values(values: Iterable[Optional[float]]) -> List[float]:
    """作用：过滤 None，并统一转成 float。"""
    out: List[float] = []
    for value in values:
        if value is None:
            continue
        try:
            out.append(float(value))
        except (TypeError, ValueError):
            continue
    return out


def _normalize_match_text(value: Any) -> str:
    """作用：归一化路径 / section / 文本，供评测诊断做宽松匹配。"""
    return str(value or "").replace("\\", "/").strip().lower()


def _source_matches_expected(source: Any, expected: Any) -> bool:
    """作用：判断 EvidenceItem 的 source_id / source_path 是否命中 expected_evidence。"""
    source_n = _normalize_match_text(source)
    expected_n = _normalize_match_text(expected)
    if not source_n or not expected_n:
        return False
    return (
        source_n == expected_n
        or source_n.endswith(expected_n)
        or expected_n.endswith(source_n)
    )


def _item_matches_expected_source(item: EvidenceItem, expected_evidence: Sequence[str]) -> bool:
    """作用：判断单个 EvidenceItem 是否命中任一 expected source。"""
    values = [
        getattr(item, "source_path", None),
        getattr(item, "source_id", None),
    ]
    return any(
        _source_matches_expected(value, expected)
        for value in values
        for expected in expected_evidence
    )


def _item_matches_expected_section(item: EvidenceItem, expected_sections: Sequence[str]) -> bool:
    """作用：判断单个 EvidenceItem 是否命中 expected section；无 section 标注时返回 False。"""
    if not expected_sections:
        return False

    section = _normalize_match_text(getattr(item, "section_path", None))
    chunk_id = _normalize_match_text(getattr(item, "chunk_id", None))
    text = _normalize_match_text(getattr(item, "text_preview", None))

    for expected in expected_sections:
        expected_n = _normalize_match_text(expected)
        if not expected_n:
            continue
        if expected_n in section or expected_n in chunk_id or expected_n in text:
            return True
    return False


def _rule_terms(value: Any) -> List[str]:
    """作用：把字符串或字符串数组规整为非空字符串数组。"""
    if value is None:
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, (list, tuple, set)):
        values = list(value)
    else:
        values = [str(value)]

    return [str(item).strip() for item in values if str(item or "").strip()]


def _answer_rule_matches(text: str, rule: Any) -> bool:
    """
    作用：判断文本是否满足 answer-bearing 规则。

    规则支持：
    - "keyword"
    - ["keyword_a", "keyword_b"]  # 任一命中
    - {"all": [...], "any": [...]} # all 全部命中，any 至少一个命中
    """
    text_n = _normalize_match_text(text)
    if not text_n:
        return False

    if isinstance(rule, dict):
        required_terms = _rule_terms(rule.get("all"))
        optional_terms = _rule_terms(rule.get("any"))
        forbidden_terms = _rule_terms(rule.get("not"))

        if any(_normalize_match_text(term) in text_n for term in forbidden_terms):
            return False
        if required_terms and not all(
            _normalize_match_text(term) in text_n for term in required_terms
        ):
            return False
        if optional_terms and not any(
            _normalize_match_text(term) in text_n for term in optional_terms
        ):
            return False
        return bool(required_terms or optional_terms)

    return any(_normalize_match_text(term) in text_n for term in _rule_terms(rule))


def _item_is_answer_bearing(item: EvidenceItem, answer_bearing_rules: Sequence[Any]) -> bool:
    """作用：判断 EvidenceItem 文本是否命中任一 answer-bearing 规则。"""
    if not answer_bearing_rules:
        return False
    text = str(getattr(item, "text_preview", "") or "")
    return any(_answer_rule_matches(text, rule) for rule in answer_bearing_rules)


def _rank_value(item: EvidenceItem, fallback_rank: int) -> int:
    """作用：读取稳定排序名次，优先 rank_after_rerank，其次 rank_before_rerank。"""
    for value in (item.rank_after_rerank, item.rank_before_rerank):
        try:
            if value is not None and int(value) > 0:
                return int(value)
        except (TypeError, ValueError):
            continue
    return int(fallback_rank)


def annotate_evidence_items_for_eval(
    items: List[EvidenceItem],
    *,
    expected_evidence: Optional[Sequence[str]] = None,
    expected_sections: Optional[Sequence[str]] = None,
    answer_bearing_rules: Optional[Sequence[Any]] = None,
    prompt_chunk_ids: Optional[Sequence[str]] = None,
    max_prompt_chunks: int = 2,
) -> Dict[str, Any]:
    """
    作用：
    - 只在评测 / replay 模式下为 EvidenceItem 回填诊断标签。
    - 不改变检索排序、证据包压缩、sufficiency 判定或生成行为。
    """
    expected = list(expected_evidence or [])
    sections = list(expected_sections or [])
    rules = list(answer_bearing_rules or [])
    prompt_ids = {str(item) for item in list(prompt_chunk_ids or []) if str(item or "").strip()}

    answer_bearing_chunk_ids: List[str] = []
    expected_hit_sources: List[str] = []
    answer_bearing_ranks: List[int] = []
    expected_source_answer_bearing_ranks: List[int] = []

    for idx, item in enumerate(items):
        rank = _rank_value(item, idx + 1)
        chunk_id = str(item.chunk_id or "")

        item.is_expected_source = _item_matches_expected_source(item, expected)
        item.is_expected_section = _item_matches_expected_section(item, sections)
        item.is_answer_bearing = _item_is_answer_bearing(item, rules)

        if prompt_ids:
            item.in_prompt = chunk_id in prompt_ids
        else:
            item.in_prompt = rank <= int(max_prompt_chunks)

        if item.is_expected_source:
            for source in (item.source_path, item.source_id):
                for expected_source in expected:
                    if _source_matches_expected(source, expected_source) and expected_source not in expected_hit_sources:
                        expected_hit_sources.append(expected_source)

        if item.is_answer_bearing:
            if chunk_id and chunk_id not in answer_bearing_chunk_ids:
                answer_bearing_chunk_ids.append(chunk_id)
            answer_bearing_ranks.append(rank)
            if item.is_expected_source:
                expected_source_answer_bearing_ranks.append(rank)

    expected_source_hit = any(item.is_expected_source is True for item in items)
    expected_section_hit = any(item.is_expected_section is True for item in items)
    answer_bearing_chunk_hit = any(item.is_answer_bearing is True for item in items)
    prompt_contains_answer_bearing_chunk = any(
        item.is_answer_bearing is True and bool(item.in_prompt) for item in items
    )
    expected_source_answer_bearing_chunk_hit = any(
        item.is_expected_source is True and item.is_answer_bearing is True
        for item in items
    )

    return {
        "expected_source_hit": expected_source_hit,
        "expected_hit_sources": expected_hit_sources,
        "expected_section_hit": expected_section_hit,
        "answer_bearing_chunk_hit": answer_bearing_chunk_hit,
        "answer_bearing_chunk_rank": min(answer_bearing_ranks) if answer_bearing_ranks else None,
        "answer_bearing_chunk_ids": answer_bearing_chunk_ids,
        "prompt_contains_answer_bearing_chunk": prompt_contains_answer_bearing_chunk,
        "expected_source_answer_bearing_chunk_hit": expected_source_answer_bearing_chunk_hit,
        "expected_source_answer_bearing_chunk_rank": (
            min(expected_source_answer_bearing_ranks)
            if expected_source_answer_bearing_ranks
            else None
        ),
        "source_level_hit_but_chunk_miss": (
            bool(expected_source_hit) and not bool(expected_source_answer_bearing_chunk_hit)
        ),
    }


def summarize_source_coverage(items: List[EvidenceItem]) -> Dict[str, Any]:
    """作用：统计 EvidencePacket 中的 source 级覆盖情况。"""
    source_ids: List[str] = []
    source_paths: List[str] = []

    for item in items:
        if item.source_id and item.source_id not in source_ids:
            source_ids.append(item.source_id)
        if item.source_path and item.source_path not in source_paths:
            source_paths.append(item.source_path)

    return {
        "item_count": len(items),
        "distinct_source_count": len(source_ids),
        "source_ids": source_ids,
        "source_paths": source_paths,
    }


def summarize_scores(items: List[EvidenceItem]) -> Dict[str, Any]:
    """作用：按真实分数语义统计 vector / RRF / rerank 摘要，不编造缺失分数。"""
    vector_scores = _safe_float_values(item.vector_score for item in items)
    rrf_scores = _safe_float_values(item.rrf_score for item in items)
    rerank_scores = _safe_float_values(item.rerank_score for item in items)

    summary: Dict[str, Any] = {
        "vector_score_count": len(vector_scores),
        "rrf_score_count": len(rrf_scores),
        "rerank_score_count": len(rerank_scores),
        "has_rrf_scores": bool(rrf_scores),
        "has_rerank_scores": bool(rerank_scores),
    }

    if vector_scores:
        summary.update(
            {
                "vector_score_min": min(vector_scores),
                "vector_score_max": max(vector_scores),
                "vector_score_mean": mean(vector_scores),
            }
        )

    if rrf_scores:
        summary.update(
            {
                "rrf_score_min": min(rrf_scores),
                "rrf_score_max": max(rrf_scores),
                "rrf_score_mean": mean(rrf_scores),
            }
        )

    if rerank_scores:
        summary.update(
            {
                "rerank_score_min": min(rerank_scores),
                "rerank_score_max": max(rerank_scores),
                "rerank_score_mean": mean(rerank_scores),
            }
        )

    return summary


def summarize_answer_bearing(items: List[EvidenceItem]) -> Dict[str, Any]:
    """作用：统计评测模式下 answer-bearing / expected source 标注；在线模式多为 unknown。"""
    expected_source_hits = [item for item in items if item.is_expected_source is True]
    expected_section_hits = [item for item in items if item.is_expected_section is True]
    answer_bearing_hits = [item for item in items if item.is_answer_bearing is True]
    expected_source_answer_bearing_hits = [
        item
        for item in items
        if item.is_expected_source is True and item.is_answer_bearing is True
    ]
    prompt_answer_bearing_hits = [
        item for item in items if item.is_answer_bearing is True and bool(item.in_prompt)
    ]

    answer_bearing_ranks = [
        _rank_value(item, idx + 1)
        for idx, item in enumerate(items)
        if item.is_answer_bearing is True
    ]

    return {
        "expected_source_hit_count": len(expected_source_hits),
        "expected_section_hit_count": len(expected_section_hits),
        "answer_bearing_hit_count": len(answer_bearing_hits),
        "expected_source_answer_bearing_hit_count": len(expected_source_answer_bearing_hits),
        "prompt_answer_bearing_hit_count": len(prompt_answer_bearing_hits),
        "has_expected_source_hit": bool(expected_source_hits),
        "has_expected_section_hit": bool(expected_section_hits),
        "has_answer_bearing_hit": bool(answer_bearing_hits),
        "answer_bearing_chunk_rank": min(answer_bearing_ranks) if answer_bearing_ranks else None,
        "prompt_contains_answer_bearing_chunk": bool(prompt_answer_bearing_hits),
        "has_expected_source_answer_bearing_hit": bool(expected_source_answer_bearing_hits),
        "source_level_hit_but_chunk_miss": bool(
            expected_source_hits and not expected_source_answer_bearing_hits
        ),
    }


def detect_known_gaps(items: List[EvidenceItem], route: Optional[str] = None) -> List[str]:
    """作用：给 EvidencePacket 标记已知缺口，供后续 sufficiency / uncertainty 使用。"""
    gaps: List[str] = []

    if not items:
        gaps.append("empty_evidence_packet")
        if route:
            gaps.append(f"no_evidence_for_route:{route}")
        return gaps

    source_coverage = summarize_source_coverage(items)
    answer_bearing = summarize_answer_bearing(items)

    if int(source_coverage.get("distinct_source_count", 0)) <= 1:
        gaps.append("single_source_coverage")

    if answer_bearing["source_level_hit_but_chunk_miss"]:
        gaps.append("source_level_hit_but_chunk_miss")

    if not any((item.text_preview or "").strip() for item in items):
        gaps.append("missing_text_preview")

    return gaps
