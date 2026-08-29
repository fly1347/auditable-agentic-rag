"""
程序作用：
按精确原文偏移切分 Markdown 或纯文本，并保证内容覆盖完整。生产 ``markdown`` 模式以结构优先、Token 预算为硬约束，不会悄悄退回字符长度切分。

整体结构：
1）解析 Markdown 层级、代码围栏、表格、列表和原子文本块；
2）优先保留能放入预算的完整子树，超限时递归拆解并打包相邻单元；
3）只在最后兜底使用 Token 窗口，同时提供覆盖率与结构保持校验；
4）``legacy_char`` 仅用于复现旧索引，``char`` 和 ``token`` 为显式兼容模式。
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, List, Protocol, Sequence

from agentic_rag.policy.source_registry import propagate_document_acl
from agentic_rag.types import Chunk, Document


class TokenBudgetProvider(Protocol):
    """生产 Markdown 切分所需的最小 tokenizer 接口。"""

    def content_token_counts(self, texts: List[str]) -> List[int]: ...

    def content_token_offsets(self, text: str) -> List[tuple[int, int]]: ...


@dataclass(frozen=True)
class SplitterConfig:
    mode: str = "markdown"

    # 这些参数只服务显式 char、token、legacy_char 模式；生产 markdown 模式不靠它们决定普通 chunk 边界。
    chunk_size: int = 420
    overlap: int = 60
    min_size: int = 80
    preserve_code_block: bool = True
    boundary_search: int = 120

    # 生产 Markdown 契约：正常结构绝不按字符数强行切断。
    content_token_limit: int = 510

    def validate(self) -> None:
        if self.mode not in {"markdown", "char", "token", "legacy_char"}:
            raise ValueError(f"unsupported splitter mode: {self.mode}")
        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if self.overlap < 0 or self.overlap >= self.chunk_size:
            raise ValueError("overlap must satisfy 0 <= overlap < chunk_size")
        if self.min_size < 0 or self.min_size > self.chunk_size:
            raise ValueError("min_size must satisfy 0 <= min_size <= chunk_size")
        if self.content_token_limit <= 0:
            raise ValueError("content_token_limit must be positive")


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_LIST_ITEM_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)")


@dataclass
class _SectionNode:
    level: int
    title: str
    start: int
    header_end: int
    end: int = 0
    children: list["_SectionNode"] = field(default_factory=list)


@dataclass(frozen=True)
class _AtomicBlock:
    start: int
    end: int
    kind: str


@dataclass(frozen=True)
class _Unit:
    start: int
    end: int
    structural_unit: str
    hierarchy_level: int | None
    forced_split: bool = False
    forced_split_type: str = ""
    fence_split: bool = False
    complete_subtree_count: int = 0


def _read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="ignore")


def _normalize_chunk_text_for_id(text: str) -> str:
    normalized = str(text).replace("\r\n", "\n").replace("\r", "\n")
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def _build_stable_chunk_id(source_id: str, offset_start: int, offset_end: int, text: str) -> str:
    normalized = _normalize_chunk_text_for_id(text)
    text_hash = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return f"{source_id}@{offset_start}-{offset_end}#{text_hash}"


def _line_spans(text: str) -> list[tuple[int, int, str]]:
    spans: list[tuple[int, int, str]] = []
    offset = 0
    for line in text.splitlines(keepends=True):
        end = offset + len(line)
        spans.append((offset, end, line.rstrip("\r\n")))
        offset = end
    if offset < len(text):
        spans.append((offset, len(text), text[offset:]))
    return spans


def _section_marks(text: str) -> list[tuple[int, str]]:
    stack: list[tuple[int, str]] = []
    marks: list[tuple[int, str]] = []
    for start, _, line in _line_spans(text):
        match = _HEADING_RE.match(line)
        if not match:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        while stack and stack[-1][0] >= level:
            stack.pop()
        stack.append((level, title))
        marks.append((start, " / ".join(value for _, value in stack)))
    return marks


def _section_path(marks: Sequence[tuple[int, str]], offset: int) -> str:
    current = ""
    for position, path in marks:
        if position > offset:
            break
        current = path
    return current


def _section_paths_in_range(
    marks: Sequence[tuple[int, str]],
    start: int,
    end: int,
) -> list[str]:
    paths: list[str] = []
    active = _section_path(marks, start)
    if active:
        paths.append(active)
    for position, path in marks:
        if position < start:
            continue
        if position >= end:
            break
        if path and path not in paths:
            paths.append(path)
    return paths


def _fence_ranges(text: str) -> list[tuple[int, int]]:
    ranges: list[tuple[int, int]] = []
    open_start: int | None = None
    marker: str | None = None
    for start, end, line in _line_spans(text):
        match = _FENCE_RE.match(line)
        if not match:
            continue
        current = match.group(1)
        if open_start is None:
            open_start, marker = start, current
        elif current == marker:
            ranges.append((open_start, end))
            open_start, marker = None, None
    if open_start is not None:
        ranges.append((open_start, len(text)))
    return ranges


def _containing_range(position: int, ranges: Sequence[tuple[int, int]]) -> tuple[int, int] | None:
    for start, end in ranges:
        if start < position < end:
            return start, end
    return None


def _char_windows(text: str, cfg: SplitterConfig) -> Iterable[tuple[int, int, dict[str, object]]]:
    start = 0
    step = cfg.chunk_size - cfg.overlap
    ranges = _fence_ranges(text)
    while start < len(text):
        end = min(len(text), start + cfg.chunk_size)
        yield start, end, {
            "boundary_type": "document_end" if end == len(text) else "hard_limit",
            "fence_split": bool(_containing_range(end, ranges)),
            "coverage_preserving": True,
        }
        if end == len(text):
            break
        start += step


def _legacy_inside_fence(lines: List[str], char_offset: int) -> bool:
    acc = 0
    in_fence = False
    for line in lines:
        if acc >= char_offset:
            break
        if re.match(r"^```", line):
            in_fence = not in_fence
        acc += len(line) + 1
    return in_fence


def _legacy_windows(text: str, cfg: SplitterConfig) -> Iterable[tuple[int, int, dict[str, object]]]:
    lines = text.splitlines()
    for start, end, metadata in _char_windows(text, cfg):
        if cfg.preserve_code_block and _legacy_inside_fence(lines, start):
            continue
        yield start, end, {**metadata, "coverage_preserving": False}


def _token_windows(
    text: str,
    cfg: SplitterConfig,
    tokenizer_name: str,
) -> Iterable[tuple[int, int, dict[str, object]]]:
    try:
        from transformers import AutoTokenizer  # type: ignore
    except Exception as exc:
        raise RuntimeError(
            "token splitter requires transformers and a locally cached fast tokenizer; "
            "it does not silently fall back to char mode"
        ) from exc
    tokenizer = AutoTokenizer.from_pretrained(
        tokenizer_name,
        use_fast=True,
        local_files_only=True,
    )
    encoded = tokenizer(text, return_offsets_mapping=True, add_special_tokens=False)
    offsets = list(encoded.get("offset_mapping", []) or [])
    if not offsets:
        raise RuntimeError("tokenizer did not return offset_mapping")
    step = cfg.chunk_size - cfg.overlap
    token_start = 0
    while token_start < len(offsets):
        token_end = min(len(offsets), token_start + cfg.chunk_size)
        start = int(offsets[token_start][0])
        end = int(offsets[token_end - 1][1])
        yield start, end, {
            "boundary_type": "token_limit",
            "fence_split": bool(_containing_range(end, _fence_ranges(text))),
            "coverage_preserving": True,
            "token_count": token_end - token_start,
        }
        if token_end == len(offsets):
            break
        token_start += step


def _require_token_provider(provider: TokenBudgetProvider | None) -> TokenBudgetProvider:
    if provider is None:
        raise RuntimeError(
            "markdown splitter requires the production token budget provider; "
            "it does not load or guess a tokenizer independently"
        )
    if not callable(getattr(provider, "content_token_counts", None)):
        raise RuntimeError("token budget provider does not expose content_token_counts")
    if not callable(getattr(provider, "content_token_offsets", None)):
        raise RuntimeError("token budget provider does not expose content_token_offsets")
    return provider


def _token_count(provider: TokenBudgetProvider, text: str) -> int:
    counts = provider.content_token_counts([text])
    if len(counts) != 1:
        raise RuntimeError("token budget provider returned an invalid count result")
    return int(counts[0])


def _build_hierarchy(text: str) -> list[_SectionNode]:
    roots: list[_SectionNode] = []
    stack: list[_SectionNode] = []
    for start, end, line in _line_spans(text):
        match = _HEADING_RE.match(line)
        if not match:
            continue
        level = len(match.group(1))
        title = match.group(2).strip()
        while stack and stack[-1].level >= level:
            stack.pop().end = start
        node = _SectionNode(level=level, title=title, start=start, header_end=end)
        if stack:
            stack[-1].children.append(node)
        else:
            roots.append(node)
        stack.append(node)
    while stack:
        stack.pop().end = len(text)
    return roots


def _is_blank(line: str) -> bool:
    return not line.strip()


def _looks_like_table(line: str) -> bool:
    stripped = line.strip()
    return bool(stripped) and "|" in stripped and not _LIST_ITEM_RE.match(line)


def _atomic_blocks(text: str, start: int, end: int) -> list[_AtomicBlock]:
    """把连续章节范围解析成不丢字符的原子块。"""
    if start >= end:
        return []
    local = text[start:end]
    lines = _line_spans(local)
    blocks: list[_AtomicBlock] = []
    index = 0
    while index < len(lines):
        line_start, line_end, line = lines[index]
        abs_start = start + line_start

        fence_match = _FENCE_RE.match(line)
        if fence_match:
            marker = fence_match.group(1)
            cursor = index + 1
            block_end = start + line_end
            while cursor < len(lines):
                _, candidate_end, candidate_line = lines[cursor]
                block_end = start + candidate_end
                candidate = _FENCE_RE.match(candidate_line)
                cursor += 1
                if candidate and candidate.group(1) == marker:
                    break
            blocks.append(_AtomicBlock(abs_start, min(block_end, end), "fence"))
            index = cursor
            continue

        if _is_blank(line):
            cursor = index + 1
            block_end = start + line_end
            while cursor < len(lines) and _is_blank(lines[cursor][2]):
                block_end = start + lines[cursor][1]
                cursor += 1
            blocks.append(_AtomicBlock(abs_start, min(block_end, end), "whitespace"))
            index = cursor
            continue

        if _LIST_ITEM_RE.match(line):
            cursor = index + 1
            block_end = start + line_end
            while cursor < len(lines):
                candidate = lines[cursor][2]
                if _is_blank(candidate) or _FENCE_RE.match(candidate) or _HEADING_RE.match(candidate):
                    break
                if _LIST_ITEM_RE.match(candidate) or candidate.startswith((" ", "\t")):
                    block_end = start + lines[cursor][1]
                    cursor += 1
                    continue
                break
            blocks.append(_AtomicBlock(abs_start, min(block_end, end), "list"))
            index = cursor
            continue

        if _looks_like_table(line):
            cursor = index + 1
            block_end = start + line_end
            while cursor < len(lines) and _looks_like_table(lines[cursor][2]):
                block_end = start + lines[cursor][1]
                cursor += 1
            blocks.append(_AtomicBlock(abs_start, min(block_end, end), "table"))
            index = cursor
            continue

        cursor = index + 1
        block_end = start + line_end
        while cursor < len(lines):
            candidate = lines[cursor][2]
            if (
                _is_blank(candidate)
                or _FENCE_RE.match(candidate)
                or _LIST_ITEM_RE.match(candidate)
                or _looks_like_table(candidate)
                or _HEADING_RE.match(candidate)
            ):
                break
            block_end = start + lines[cursor][1]
            cursor += 1
        blocks.append(_AtomicBlock(abs_start, min(block_end, end), "paragraph"))
        index = cursor

    # 进入 Token 逻辑前先做精确覆盖断言，防止解析阶段已经丢字。
    cursor = start
    for block in blocks:
        if block.start != cursor or block.end < block.start:
            raise RuntimeError(
                f"atomic block parser lost coverage: expected_start={cursor} got={block.start}-{block.end}"
            )
        cursor = block.end
    if cursor != end:
        raise RuntimeError(f"atomic block parser lost tail coverage: expected_end={end} got={cursor}")
    return blocks


def _line_subspans(text: str, start: int, end: int) -> list[tuple[int, int]]:
    return [(start + left, start + right) for left, right, _ in _line_spans(text[start:end])]


def _list_item_subspans(text: str, start: int, end: int) -> list[tuple[int, int]]:
    lines = _line_spans(text[start:end])
    if not lines:
        return []
    spans: list[tuple[int, int]] = []
    item_start = 0
    for index in range(1, len(lines)):
        if _LIST_ITEM_RE.match(lines[index][2]):
            spans.append((start + lines[item_start][0], start + lines[index - 1][1]))
            item_start = index
    spans.append((start + lines[item_start][0], start + lines[-1][1]))
    return spans


def _sentence_subspans(text: str, start: int, end: int) -> list[tuple[int, int]]:
    piece = text[start:end]
    if not piece:
        return []
    boundaries: list[int] = []
    for index, char in enumerate(piece):
        next_char = piece[index + 1] if index + 1 < len(piece) else ""
        if char in "。！？!?；;" or char == "\n" or (char == "." and (not next_char or next_char.isspace())):
            boundaries.append(index + 1)
    spans: list[tuple[int, int]] = []
    cursor = 0
    for boundary in boundaries:
        if boundary > cursor:
            spans.append((start + cursor, start + boundary))
            cursor = boundary
    if cursor < len(piece):
        spans.append((start + cursor, end))
    return spans or [(start, end)]


def _forced_token_units(
    text: str,
    start: int,
    end: int,
    *,
    kind: str,
    level: int | None,
    provider: TokenBudgetProvider,
    cfg: SplitterConfig,
) -> list[_Unit]:
    piece = text[start:end]
    offsets = [(int(left), int(right)) for left, right in provider.content_token_offsets(piece)]
    if not offsets:
        # 不含 Token 的文本通常只是空白，可以作为一个完整单元保留。
        return [_Unit(start, end, kind, level)]
    if any(left < 0 or right < left or right > len(piece) for left, right in offsets):
        raise RuntimeError("token budget provider returned invalid offset mapping")
    offsets = [item for item in offsets if item[1] > item[0]]
    if not offsets:
        return [_Unit(start, end, kind, level)]

    limit = int(cfg.content_token_limit)
    units: list[_Unit] = []
    token_start = 0
    previous_char_end = 0
    while token_start < len(offsets):
        token_end = min(len(offsets), token_start + limit)
        local_start = previous_char_end
        local_end = len(piece) if token_end == len(offsets) else offsets[token_end][0]
        if local_end <= local_start:
            local_end = offsets[token_end - 1][1]
        units.append(
            _Unit(
                start=start + local_start,
                end=start + local_end,
                structural_unit=kind,
                hierarchy_level=level,
                forced_split=True,
                forced_split_type="token_window",
                fence_split=(kind == "fence"),
            )
        )
        previous_char_end = local_end
        if token_end == len(offsets):
            break
        token_start = token_end

    cursor = start
    for unit in units:
        if unit.start != cursor:
            raise RuntimeError("forced token split lost exact contiguous coverage")
        cursor = unit.end
    if cursor != end:
        raise RuntimeError("forced token split lost tail coverage")
    return units


def _split_oversized_atomic(
    text: str,
    block: _AtomicBlock,
    *,
    level: int | None,
    provider: TokenBudgetProvider,
    cfg: SplitterConfig,
) -> list[_Unit]:
    if block.kind == "paragraph":
        candidates = _sentence_subspans(text, block.start, block.end)
        split_type = "sentence"
    elif block.kind == "list":
        candidates = _list_item_subspans(text, block.start, block.end)
        split_type = "list_item"
    elif block.kind in {"table", "fence"}:
        candidates = _line_subspans(text, block.start, block.end)
        split_type = "table_row" if block.kind == "table" else "fence_line"
    else:
        candidates = [(block.start, block.end)]
        split_type = block.kind

    units: list[_Unit] = []
    for start, end in candidates:
        piece = text[start:end]
        if _token_count(provider, piece) <= cfg.content_token_limit:
            units.append(
                _Unit(
                    start=start,
                    end=end,
                    structural_unit=block.kind,
                    hierarchy_level=level,
                    forced_split=True,
                    forced_split_type=split_type,
                    fence_split=(block.kind == "fence"),
                )
            )
        else:
            units.extend(
                _forced_token_units(
                    text,
                    start,
                    end,
                    kind=block.kind,
                    level=level,
                    provider=provider,
                    cfg=cfg,
                )
            )
    return units


def _atomic_units(
    text: str,
    start: int,
    end: int,
    *,
    level: int | None,
    provider: TokenBudgetProvider,
    cfg: SplitterConfig,
) -> list[_Unit]:
    units: list[_Unit] = []
    for block in _atomic_blocks(text, start, end):
        piece = text[block.start:block.end]
        if _token_count(provider, piece) <= cfg.content_token_limit:
            units.append(
                _Unit(
                    start=block.start,
                    end=block.end,
                    structural_unit=block.kind,
                    hierarchy_level=level,
                )
            )
        else:
            units.extend(
                _split_oversized_atomic(
                    text,
                    block,
                    level=level,
                    provider=provider,
                    cfg=cfg,
                )
            )
    return units


def _decompose_section(
    text: str,
    node: _SectionNode,
    *,
    provider: TokenBudgetProvider,
    cfg: SplitterConfig,
) -> list[_Unit]:
    if _token_count(provider, text[node.start:node.end]) <= cfg.content_token_limit:
        return [
            _Unit(
                start=node.start,
                end=node.end,
                structural_unit="subtree",
                hierarchy_level=node.level,
                complete_subtree_count=1,
            )
        ]

    if not node.children:
        return _atomic_units(
            text,
            node.start,
            node.end,
            level=node.level,
            provider=provider,
            cfg=cfg,
        )

    units: list[_Unit] = []
    prefix_end = node.children[0].start
    if node.start < prefix_end:
        units.extend(
            _atomic_units(
                text,
                node.start,
                prefix_end,
                level=node.level,
                provider=provider,
                cfg=cfg,
            )
        )
    for child in node.children:
        units.extend(_decompose_section(text, child, provider=provider, cfg=cfg))
    return units


def _pack_units(
    text: str,
    units: Sequence[_Unit],
    *,
    provider: TokenBudgetProvider,
    cfg: SplitterConfig,
) -> list[_Unit]:
    """连续打包相邻完整单元，标题只提供结构信息，不强制形成硬切点。"""
    if not units:
        return []
    packed: list[_Unit] = []
    current: list[_Unit] = []

    def flush() -> None:
        nonlocal current
        if not current:
            return
        first, last = current[0], current[-1]
        packed.append(
            _Unit(
                start=first.start,
                end=last.end,
                structural_unit=(first.structural_unit if len(current) == 1 else "packed_structural_units"),
                hierarchy_level=(
                    first.hierarchy_level
                    if len(current) == 1
                    else min(
                        (unit.hierarchy_level for unit in current if unit.hierarchy_level is not None),
                        default=None,
                    )
                ),
                forced_split=any(unit.forced_split for unit in current),
                forced_split_type=(
                    first.forced_split_type
                    if len(current) == 1
                    else (
                        next(iter({unit.forced_split_type for unit in current if unit.forced_split_type}))
                        if len({unit.forced_split_type for unit in current if unit.forced_split_type}) == 1
                        else "mixed_forced_split"
                    )
                    if any(unit.forced_split for unit in current)
                    else ""
                ),
                fence_split=any(unit.fence_split for unit in current),
                complete_subtree_count=sum(unit.complete_subtree_count for unit in current),
            )
        )
        current = []

    for unit in units:
        if current and unit.start != current[-1].end:
            raise RuntimeError(
                f"structure decomposition lost contiguity: {current[-1].end} -> {unit.start}"
            )
        if not current:
            current = [unit]
            continue
        candidate_start = current[0].start
        candidate_end = unit.end
        if _token_count(provider, text[candidate_start:candidate_end]) <= cfg.content_token_limit:
            current.append(unit)
        else:
            flush()
            current = [unit]
    flush()
    return packed


def _markdown_units(
    text: str,
    cfg: SplitterConfig,
    provider: TokenBudgetProvider,
) -> list[_Unit]:
    if not text:
        return []
    roots = _build_hierarchy(text)
    units: list[_Unit] = []
    if not roots:
        units.extend(_atomic_units(text, 0, len(text), level=None, provider=provider, cfg=cfg))
    else:
        if roots[0].start > 0:
            units.extend(
                _atomic_units(text, 0, roots[0].start, level=None, provider=provider, cfg=cfg)
            )
        for root in roots:
            units.extend(_decompose_section(text, root, provider=provider, cfg=cfg))

    packed = _pack_units(text, units, provider=provider, cfg=cfg)
    cursor = 0
    for unit in packed:
        if unit.start != cursor:
            raise RuntimeError(
                f"markdown splitter lost exact coverage: expected_start={cursor} got={unit.start}"
            )
        cursor = unit.end
    if cursor != len(text):
        raise RuntimeError(
            f"markdown splitter lost tail coverage: expected_end={len(text)} got={cursor}"
        )
    for unit in packed:
        count = _token_count(provider, text[unit.start:unit.end])
        if count > cfg.content_token_limit:
            raise RuntimeError(
                f"markdown splitter emitted over-budget unit: tokens={count} limit={cfg.content_token_limit}"
            )
    return packed


def split_document(
    doc: Document,
    cfg: SplitterConfig,
    tokenizer_name: str = "BAAI/bge-small-zh-v1.5",
    *,
    token_provider: TokenBudgetProvider | None = None,
) -> List[Chunk]:
    cfg.validate()
    text = _read_text(doc.path)
    marks = _section_marks(text)

    if cfg.mode == "markdown":
        provider = _require_token_provider(token_provider)
        units = _markdown_units(text, cfg, provider)
        windows: Iterable[tuple[int, int, dict[str, object]]] = (
            (
                unit.start,
                unit.end,
                {
                    "boundary_type": "structure_or_token_budget",
                    "fence_split": unit.fence_split,
                    "coverage_preserving": True,
                    "splitter_strategy": "structure_first_largest_fit",
                    "content_token_limit": cfg.content_token_limit,
                    "structural_unit": unit.structural_unit,
                    "hierarchy_level": unit.hierarchy_level,
                    "forced_split": unit.forced_split,
                    "forced_split_type": unit.forced_split_type,
                    "complete_subtree_count": unit.complete_subtree_count,
                    "token_count": _token_count(provider, text[unit.start:unit.end]),
                },
            )
            for unit in units
        )
    elif cfg.mode == "token":
        windows = _token_windows(text, cfg, tokenizer_name)
    elif cfg.mode == "legacy_char":
        windows = _legacy_windows(text, cfg)
    else:
        windows = _char_windows(text, cfg)

    chunks: List[Chunk] = []
    for start, end, window_metadata in windows:
        raw_piece = text[start:end]
        if cfg.mode == "legacy_char":
            piece = raw_piece.strip()
            if len(piece) < cfg.min_size:
                continue
        else:
            piece = raw_piece
            if not piece and text:
                continue
        section_paths = _section_paths_in_range(marks, start, end)
        metadata: dict[str, object] = {
            "section_path": section_paths[0] if section_paths else _section_path(marks, start),
            "section_paths": section_paths,
            "splitter_mode": cfg.mode,
            "chunk_size": cfg.chunk_size,
            "overlap": cfg.overlap,
            "source_path": doc.path,
            **window_metadata,
        }
        metadata = propagate_document_acl(doc, metadata)
        chunks.append(
            Chunk(
                chunk_id=_build_stable_chunk_id(doc.source_id, start, end, piece),
                source_id=doc.source_id,
                doc_hash=doc.doc_hash,
                text=piece,
                offset_start=start,
                offset_end=end,
                metadata=metadata,
            )
        )
    return chunks


def split_documents(
    docs: List[Document],
    cfg: SplitterConfig,
    tokenizer_name: str = "BAAI/bge-small-zh-v1.5",
    *,
    token_provider: TokenBudgetProvider | None = None,
) -> List[Chunk]:
    chunks: List[Chunk] = []
    for document in docs:
        chunks.extend(
            split_document(
                document,
                cfg,
                tokenizer_name=tokenizer_name,
                token_provider=token_provider,
            )
        )
    return chunks




def structure_preservation_violations(
    text: str,
    chunks: Sequence[Chunk],
    token_provider: TokenBudgetProvider,
    *,
    content_token_limit: int = 510,
) -> list[dict[str, object]]:
    """找出本可整体放入预算、却被拆到多个输出 chunk 的 Markdown 子树。

    子树可以与相邻结构合并；所谓结构保持，是指该子树的精确原文范围完整落在同一个输出 chunk 中。
    """

    def walk(nodes: Sequence[_SectionNode]) -> Iterable[_SectionNode]:
        for node in nodes:
            yield node
            yield from walk(node.children)

    violations: list[dict[str, object]] = []
    for node in walk(_build_hierarchy(text)):
        token_count = _token_count(token_provider, text[node.start:node.end])
        if token_count > int(content_token_limit):
            continue
        preserved = any(
            int(chunk.offset_start) <= node.start and int(chunk.offset_end) >= node.end
            for chunk in chunks
        )
        if not preserved:
            violations.append(
                {
                    "level": node.level,
                    "title": node.title,
                    "offset_start": node.start,
                    "offset_end": node.end,
                    "token_count": token_count,
                }
            )
    return violations


def coverage_ratio(text: str, chunks: Sequence[Chunk]) -> float:
    """计算单个来源的字符覆盖率，重叠区间只计一次。"""
    if not text:
        return 1.0
    covered = bytearray(len(text))
    for chunk in chunks:
        start = max(0, int(chunk.offset_start))
        end = min(len(text), int(chunk.offset_end))
        if chunk.text != text[start:end]:
            return 0.0
        covered[start:end] = b"\x01" * max(0, end - start)
    return sum(covered) / len(text)


__all__ = [
    "SplitterConfig",
    "TokenBudgetProvider",
    "coverage_ratio",
    "structure_preservation_violations",
    "split_document",
    "split_documents",
]
