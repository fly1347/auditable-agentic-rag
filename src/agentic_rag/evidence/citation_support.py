"""
D-full Step 13 citation support offline evaluator.

作用：
- 对最终 answer 做 claim-level citation support 检查；
- citation support 只使用答案实际引用的 evidence，不使用未引用的 prompt evidence 兜底；
- citation 元数据先回连到 prompt / EvidencePacket / selected evidence 中的真实文本，再做支撑判断；
- 输出 citation_support_label / unsupported_claim_count / claims / borderline_dimension；
- 默认规则优先，不依赖 LLM，不进入在线主链路。

整体结构：
1. 从 answer 中切分 claims，并保留答案里的 [E1]/[E2] 标记供人读核对。
2. 将 outcome.citations 回连到实际被引用的 evidence 文本。
3. 仅在实际引用证据之间寻找每个 claim 的 best evidence。
4. 使用规则相似度判断支撑程度并聚合为题目级 CitationSupportReport。
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


class CitationSupportLabel(str, Enum):
    """题目级 citation support 标签。"""

    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    NOT_APPLICABLE = "not_applicable"
    NO_EVIDENCE = "no_evidence"


class ClaimSupportLabel(str, Enum):
    """claim 级支撑标签。"""

    SUPPORTED = "supported"
    PARTIAL = "partial"
    UNSUPPORTED = "unsupported"
    NO_EVIDENCE = "no_evidence"


@dataclass
class EvidenceChunk:
    """citation support 使用的最小证据块。"""

    evidence_id: str
    source_path: str = ""
    chunk_id: str = ""
    text: str = ""
    in_prompt: bool = False
    from_citation: bool = False
    from_retrieved: bool = False


@dataclass
class ClaimSupportResult:
    """单个 claim 的支撑判断结果。"""

    claim: str
    label: str
    best_evidence_id: Optional[str]
    best_source_path: Optional[str]
    best_score: float
    reason: str


@dataclass
class CitationSupportReport:
    """题目级 citation support 报告。"""

    citation_support_label: str
    unsupported_claim_count: int
    claim_count: int
    claims: List[Dict[str, Any]]
    borderline_dimension: List[str]
    evidence_scope: str
    evidence_count: int
    citation_count: int = 0
    resolved_citation_count: int = 0
    unresolved_citation_count: int = 0
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _to_dict(value: Any) -> Dict[str, Any]:
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
    return {}


def _get_any(row: Dict[str, Any], keys: Sequence[str], default: Any = None) -> Any:
    for key in keys:
        if key in row and row[key] is not None:
            return row[key]
    return default


def _normalize_text(text: str) -> str:
    text = str(text or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _strip_inline_citations(text: str) -> str:
    # claim 原文保留 [E#] 供报告核对；只在相似度评分时去掉引用标记。
    text = re.sub(r"\[E\d+\]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\[[0-9,\s]+\]", "", text)
    text = re.sub(r"【[^】]{0,80}】", "", text)
    text = re.sub(r"]{0,160}", "", text)
    return _normalize_text(text)


def split_claims(answer: str, *, min_chars: int = 8) -> List[str]:
    """
    将 answer 切成较粗粒度 claims。

    这里不追求语义最优，只做 offline 评测的稳定最小版本：
    - 按中文/英文句末符、分号、换行切分；
    - 去掉 markdown bullet 前缀；
    - 过滤过短片段。
    """
    answer = _normalize_text(answer)
    if not answer:
        return []

    raw_parts = re.split(r"[。！？!?；;]\s*|\n+", answer)
    claims: List[str] = []
    for part in raw_parts:
        item = re.sub(r"^\s*[-*0-9一二三四五六七八九十]+[.)、：:]\s*", "", part)
        item = _normalize_text(item)
        if len(item) >= min_chars:
            claims.append(item)

    return claims


def _iter_list(value: Any) -> Iterable[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _chunk_from_any(value: Any, *, default_id_prefix: str, index: int) -> Optional[EvidenceChunk]:
    """
    将 service / replay / EvidencePacket 中的多种 chunk 形态统一成 EvidenceChunk。

    兼容：
    - dict chunk: {"text": "...", "source_path": "..."}
    - service chunk: {"content": "...", "metadata": {...}}
    - langchain-like chunk: {"page_content": "...", "metadata": {...}}
    - str chunk: "..."
    """
    if isinstance(value, str):
        text = _normalize_text(value)
        if not text:
            return None
        return EvidenceChunk(
            evidence_id=f"{default_id_prefix}_{index}",
            text=text,
        )

    row = _to_dict(value)
    if not row:
        return None

    metadata = _to_dict(row.get("metadata"))

    def pick(keys: Sequence[str], default: Any = "") -> Any:
        direct = _get_any(row, keys, None)
        if direct is not None:
            return direct
        return _get_any(metadata, keys, default)

    text = pick(
        [
            "text",
            "content",
            "chunk_text",
            "text_preview",
            "snippet",
            "preview",
            "page_content",
            "document",
            "body",
            "raw_text",
        ],
        "",
    )
    text = _normalize_text(str(text or ""))
    if not text:
        return None

    chunk_id = str(pick(["chunk_id", "id", "doc_id"], "") or "")
    source_path = str(
        pick(
            ["source_path", "source", "source_id", "path", "file_path", "title"],
            "",
        )
        or ""
    )
    evidence_id = str(
        pick(["evidence_id", "marker", "chunk_id", "id"], "")
        or chunk_id
        or f"{default_id_prefix}_{index}"
    )

    return EvidenceChunk(
        evidence_id=evidence_id,
        source_path=source_path,
        chunk_id=chunk_id,
        text=text,
        in_prompt=bool(row.get("in_prompt", metadata.get("in_prompt", False))),
        from_citation=bool(row.get("from_citation", metadata.get("from_citation", False))),
        from_retrieved=bool(row.get("from_retrieved", metadata.get("from_retrieved", False))),
    )


def _identity_matches_citation(candidate: EvidenceChunk, citation: Any) -> bool:
    """判断一个带文本的 candidate 是否对应 outcome.citations 中的一条实际引用。"""
    row = _to_dict(citation)
    if not row:
        return False

    citation_chunk_id = str(row.get("chunk_id") or row.get("id") or "")
    citation_source = str(
        row.get("source_id") or row.get("source_path") or row.get("source") or ""
    )
    if citation_chunk_id and candidate.chunk_id:
        return citation_chunk_id == candidate.chunk_id
    if citation_source and candidate.source_path:
        return citation_source == candidate.source_path
    return False


def _resolve_cited_evidence_chunks(
    *,
    citations: Optional[Sequence[Any]],
    prompt_chunks: Optional[Sequence[Any]],
    retrieved_chunks: Optional[Sequence[Any]],
    packet_items: Sequence[Any],
) -> Tuple[List[EvidenceChunk], int]:
    """
    把 outcome.citations 的元数据回连成带正文的 EvidenceChunk。

    优先级：prompt-visible（保留 E1/E2 marker）→ EvidencePacket → selected/retrieved。
    只返回真正出现在 outcome.citations 中的证据；未引用的 prompt chunk 不进入支撑池。
    """
    citation_rows = list(_iter_list(citations))
    if not citation_rows:
        return [], 0

    candidate_chunks: List[EvidenceChunk] = []
    for prefix, values in (
        ("prompt", prompt_chunks),
        ("packet", packet_items),
        ("retrieved", retrieved_chunks),
    ):
        for idx, item in enumerate(_iter_list(values)):
            chunk = _chunk_from_any(item, default_id_prefix=prefix, index=idx)
            if chunk is not None:
                candidate_chunks.append(chunk)

    resolved: List[EvidenceChunk] = []
    unresolved = 0
    seen: set[str] = set()
    for citation_index, citation in enumerate(citation_rows):
        # 少数历史记录可能直接把正文放进 citation；有正文就直接使用。
        direct = _chunk_from_any(citation, default_id_prefix="citation", index=citation_index)
        matched: Optional[EvidenceChunk] = None
        if direct is not None:
            matched = direct
        else:
            for candidate in candidate_chunks:
                if _identity_matches_citation(candidate, citation):
                    matched = EvidenceChunk(**asdict(candidate))
                    break

        if matched is None:
            unresolved += 1
            continue

        matched.from_citation = True
        key = matched.chunk_id or f"{matched.source_path}|{matched.text[:80]}"
        if key in seen:
            continue
        seen.add(key)
        resolved.append(matched)

    return resolved, unresolved


def collect_evidence_chunks(
    *,
    evidence_packet: Any = None,
    citations: Optional[Sequence[Any]] = None,
    prompt_chunks: Optional[Sequence[Any]] = None,
    retrieved_chunks: Optional[Sequence[Any]] = None,
    evidence_scope: str = "actual_citations",
) -> List[EvidenceChunk]:
    """
    收集 citation support 使用的证据块。

    Citation Support 的职责固定为“实际引用证据 ↔ 答案 claim”的支撑关系。
    prompt / EvidencePacket / selected 只用于把 citation 元数据回连到原始文本，
    未出现在 outcome.citations 中的证据不会进入评分池。
    """
    scope = str(evidence_scope or "actual_citations").strip().lower()
    if scope not in {"actual_citations", "citation_only"}:
        raise ValueError("citation support only accepts actual cited evidence")

    packet = _to_dict(evidence_packet)
    packet_items = list(_iter_list(packet.get("items"))) if packet else []
    resolved, _ = _resolve_cited_evidence_chunks(
        citations=citations,
        prompt_chunks=prompt_chunks,
        retrieved_chunks=retrieved_chunks,
        packet_items=packet_items,
    )
    return resolved


def _char_ngrams(text: str, n: int = 2) -> set[str]:
    cleaned = re.sub(r"\s+", "", text.lower())
    if len(cleaned) < n:
        return {cleaned} if cleaned else set()
    return {cleaned[i : i + n] for i in range(0, len(cleaned) - n + 1)}


def _latin_tokens(text: str) -> set[str]:
    return {
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z0-9_.+-]{1,}", text)
        if len(token) >= 2
    }


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / max(len(a | b), 1)


def _claim_evidence_score(claim: str, evidence_text: str) -> float:
    claim_norm = _strip_inline_citations(claim).lower()
    ev_norm = _strip_inline_citations(evidence_text).lower()

    if not claim_norm or not ev_norm:
        return 0.0

    if claim_norm in ev_norm:
        return 1.0

    claim_ngrams = _char_ngrams(claim_norm, n=2)
    ev_ngrams = _char_ngrams(ev_norm, n=2)
    char_score = _jaccard(claim_ngrams, ev_ngrams)

    claim_tokens = _latin_tokens(claim_norm)
    ev_tokens = _latin_tokens(ev_norm)
    token_score = _jaccard(claim_tokens, ev_tokens)

    token_bonus = 0.0
    if claim_tokens and claim_tokens <= ev_tokens:
        token_bonus = 0.12
    elif claim_tokens and claim_tokens & ev_tokens:
        token_bonus = 0.05

    return min(1.0, 0.72 * char_score + 0.28 * token_score + token_bonus)


def classify_claim_support(
    claim: str,
    evidence_chunks: Sequence[EvidenceChunk],
    *,
    supported_threshold: float = 0.22,
    partial_threshold: float = 0.12,
) -> ClaimSupportResult:
    """对单个 claim 做规则支撑判断。"""
    if not evidence_chunks:
        return ClaimSupportResult(
            claim=claim,
            label=ClaimSupportLabel.NO_EVIDENCE.value,
            best_evidence_id=None,
            best_source_path=None,
            best_score=0.0,
            reason="no evidence chunks available",
        )

    best_chunk: Optional[EvidenceChunk] = None
    best_score = 0.0
    for chunk in evidence_chunks:
        score = _claim_evidence_score(claim, chunk.text)
        if score > best_score:
            best_score = score
            best_chunk = chunk

    if best_score >= supported_threshold:
        label = ClaimSupportLabel.SUPPORTED.value
        reason = "claim is sufficiently aligned with an evidence chunk"
    elif best_score >= partial_threshold:
        label = ClaimSupportLabel.PARTIAL.value
        reason = "claim has partial lexical/semantic overlap with evidence but support is incomplete"
    else:
        label = ClaimSupportLabel.UNSUPPORTED.value
        reason = "no evidence chunk provides enough support for the claim"

    return ClaimSupportResult(
        claim=claim,
        label=label,
        best_evidence_id=best_chunk.evidence_id if best_chunk else None,
        best_source_path=best_chunk.source_path if best_chunk else None,
        best_score=round(float(best_score), 4),
        reason=reason,
    )


def aggregate_claim_support(claims: Sequence[ClaimSupportResult]) -> Tuple[str, int, List[str]]:
    """聚合 claim 级结果为题目级 citation_support_label。"""
    if not claims:
        return CitationSupportLabel.NOT_APPLICABLE.value, 0, ["no_claims"]

    unsupported_count = sum(
        1
        for item in claims
        if item.label
        in {
            ClaimSupportLabel.UNSUPPORTED.value,
            ClaimSupportLabel.NO_EVIDENCE.value,
        }
    )
    partial_count = sum(1 for item in claims if item.label == ClaimSupportLabel.PARTIAL.value)
    supported_count = sum(1 for item in claims if item.label == ClaimSupportLabel.SUPPORTED.value)

    borderline: List[str] = []
    if unsupported_count:
        borderline.append("unsupported_claim")
    if partial_count:
        borderline.append("partial_support")

    if unsupported_count == 0 and partial_count == 0 and supported_count > 0:
        label = CitationSupportLabel.SUPPORTED.value
    elif supported_count > 0 or partial_count > 0:
        label = CitationSupportLabel.PARTIAL.value
    else:
        label = CitationSupportLabel.UNSUPPORTED.value

    return label, unsupported_count, borderline


def evaluate_citation_support(
    *,
    answer: str,
    citations: Optional[Sequence[Any]] = None,
    prompt_chunks: Optional[Sequence[Any]] = None,
    retrieved_chunks: Optional[Sequence[Any]] = None,
    evidence_packet: Any = None,
    refused: bool = False,
    expected_behavior: Optional[str] = None,
    evidence_scope: str = "actual_citations",
) -> CitationSupportReport:
    """
    评估 answer 中 claims 是否被答案实际引用的 evidence 支撑。

    拒答题、空 answer、expected_behavior=reject 默认 not_applicable。
    """
    answer = _normalize_text(answer)
    expected_behavior = str(expected_behavior or "").lower()
    scope = str(evidence_scope or "actual_citations").strip().lower()
    if scope == "citation_only":
        scope = "actual_citations"
    if scope != "actual_citations":
        raise ValueError("citation support only accepts actual cited evidence")
    citation_count = len(list(_iter_list(citations)))

    if refused or expected_behavior == "reject":
        return CitationSupportReport(
            citation_support_label=CitationSupportLabel.NOT_APPLICABLE.value,
            unsupported_claim_count=0,
            claim_count=0,
            claims=[],
            borderline_dimension=["refusal_or_expected_reject"],
            evidence_scope=scope,
            evidence_count=0,
            citation_count=citation_count,
            resolved_citation_count=0,
            unresolved_citation_count=0,
            notes="citation support is not applicable to refusal / expected reject case",
        )

    if not answer:
        return CitationSupportReport(
            citation_support_label=CitationSupportLabel.NOT_APPLICABLE.value,
            unsupported_claim_count=0,
            claim_count=0,
            claims=[],
            borderline_dimension=["empty_answer"],
            evidence_scope=scope,
            evidence_count=0,
            citation_count=citation_count,
            resolved_citation_count=0,
            unresolved_citation_count=citation_count,
            notes="empty answer",
        )

    claims_text = split_claims(answer)
    evidence_chunks = collect_evidence_chunks(
        evidence_packet=evidence_packet,
        citations=citations,
        prompt_chunks=prompt_chunks,
        retrieved_chunks=retrieved_chunks,
        evidence_scope=scope,
    )

    packet = _to_dict(evidence_packet)
    _, unresolved_citation_count = _resolve_cited_evidence_chunks(
        citations=citations,
        prompt_chunks=prompt_chunks,
        retrieved_chunks=retrieved_chunks,
        packet_items=list(_iter_list(packet.get("items"))) if packet else [],
    )

    if not evidence_chunks:
        claim_results = [
            ClaimSupportResult(
                claim=claim,
                label=ClaimSupportLabel.NO_EVIDENCE.value,
                best_evidence_id=None,
                best_source_path=None,
                best_score=0.0,
                reason="no evidence chunks available",
            )
            for claim in claims_text
        ]
        label = (
            CitationSupportLabel.NO_EVIDENCE.value
            if claim_results
            else CitationSupportLabel.NOT_APPLICABLE.value
        )
        return CitationSupportReport(
            citation_support_label=label,
            unsupported_claim_count=len(claim_results),
            claim_count=len(claim_results),
            claims=[asdict(item) for item in claim_results],
            borderline_dimension=["no_evidence"],
            evidence_scope=scope,
            evidence_count=0,
            citation_count=citation_count,
            resolved_citation_count=0,
            unresolved_citation_count=unresolved_citation_count or citation_count,
            notes="no usable cited evidence text found",
        )

    claim_results = [
        classify_claim_support(claim, evidence_chunks) for claim in claims_text
    ]
    label, unsupported_count, borderline = aggregate_claim_support(claim_results)

    return CitationSupportReport(
        citation_support_label=label,
        unsupported_claim_count=unsupported_count,
        claim_count=len(claim_results),
        claims=[asdict(item) for item in claim_results],
        borderline_dimension=borderline,
        evidence_scope=scope,
        evidence_count=len(evidence_chunks),
        citation_count=citation_count,
        resolved_citation_count=len(evidence_chunks),
        unresolved_citation_count=unresolved_citation_count,
        notes="rule_based_offline_evaluator",
    )
