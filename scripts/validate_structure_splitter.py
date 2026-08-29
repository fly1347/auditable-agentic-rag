#!/usr/bin/env python3
"""
程序作用：
在真实语料上验证生产用结构优先 Markdown 切分器，只复用本地 embedding 模型的 tokenizer 与偏移映射，不执行向量化、检索、生成或网络调用。

整体结构：
1）加载语料、ACL 和生产 tokenizer；
2）统计切分覆盖率、Token 分布、结构保持情况与稳定签名；
3）输出 JSON/Markdown 报告，并对硬性违规返回失败退出码。
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Sequence

from agentic_rag.embed.embeddings import EmbeddingConfig, EmbeddingModel
from agentic_rag.ingest.loaders import LoaderConfig, load_documents
from agentic_rag.ingest.splitters import (
    SplitterConfig,
    coverage_ratio,
    split_documents,
    structure_preservation_violations,
)
from agentic_rag.policy.source_registry import SourceACLRegistry, validate_chunk_acl


def _args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", default="data/corpus/phase_a")
    parser.add_argument("--registry", default="policy/source_acl.yaml")
    parser.add_argument("--exclude", action="append", default=["internal/README.md"])
    parser.add_argument("--model", default="BAAI/bge-small-zh-v1.5")
    parser.add_argument("--token-limit", type=int, default=510)
    parser.add_argument("--json-report", required=True)
    parser.add_argument("--markdown-report", required=True)
    parser.add_argument("--inspect-source", action="append", default=[])
    return parser.parse_args()


def _percentile(values: Sequence[int], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * p
    low, high = math.floor(position), math.ceil(position)
    if low == high:
        return float(ordered[low])
    return ordered[low] + (ordered[high] - ordered[low]) * (position - low)


def _chunk_signature(chunk: Any) -> tuple[object, ...]:
    return (
        chunk.chunk_id,
        chunk.source_id,
        int(chunk.offset_start),
        int(chunk.offset_end),
        chunk.text,
        json.dumps(chunk.metadata, ensure_ascii=False, sort_keys=True, default=str),
    )


def _markdown(report: dict[str, Any]) -> str:
    token = report["token_distribution"]
    lines = [
        "# Structure-first Splitter Validation",
        "",
        f"- model: `{report['model']}`",
        f"- token limit: `{report['content_token_limit']}`",
        f"- documents: `{report['document_count']}`",
        f"- chunks: `{report['chunk_count']}`",
        f"- coverage min: `{report['coverage_min']:.6f}`",
        f"- coverage failures: `{report['coverage_failure_count']}`",
        f"- offset/text mismatches: `{report['offset_text_mismatch_count']}`",
        f"- over-budget chunks: `{report['over_budget_chunk_count']}`",
        f"- deterministic: `{str(report['deterministic']).lower()}`",
        f"- fitting subtree preservation violations: `{report['structure_preservation_violation_count']}`",
        f"- forced split chunks: `{report['forced_split_chunk_count']}`",
        f"- fence forced split chunks: `{report['fence_forced_split_chunk_count']}`",
        "",
        "## Token distribution",
        "",
        f"p25={token['p25']:.1f}, p50={token['p50']:.1f}, p75={token['p75']:.1f}, "
        f"p95={token['p95']:.1f}, max={token['max']}",
        "",
        "## Structural units",
        "",
    ]
    for name, count in report["structural_unit_counts"].items():
        lines.append(f"- {name}: {count}")
    if report["structure_preservation_violations"]:
        lines.extend(["", "## Preservation violations", ""])
        for item in report["structure_preservation_violations"][:20]:
            lines.append(
                f"- {item['source_id']} H{item['level']} `{item['title']}` "
                f"@{item['offset_start']}-{item['offset_end']} tokens={item['token_count']}"
            )
    if report["inspection"]:
        lines.extend(["", "## Inspection chunk maps", ""])
        for source_id, rows in report["inspection"].items():
            lines.append(f"### {source_id}")
            lines.append("")
            for row in rows:
                lines.append(
                    f"- `{row['chunk_id']}` tokens={row['token_count']} "
                    f"unit={row['structural_unit']} forced={str(row['forced_split']).lower()} "
                    f"section={row['section_path']}"
                )
            lines.append("")
    lines.extend(
        [
            "## Gate",
            "",
            f"**{report['gate_status']}**",
            "",
        ]
    )
    return "\n".join(lines)


# 运行真实语料切分验证并写出统计报告。
def main() -> int:
    args = _args()
    token_limit = int(args.token_limit)
    registry = SourceACLRegistry.load(args.registry)
    docs = load_documents(
        [
            LoaderConfig(
                root_dir=Path(args.corpus),
                enabled=True,
                priority=0,
                tags=["retrieval_corpus"],
            )
        ],
        acl_registry=registry,
        excluded_source_ids=args.exclude,
    )
    if not docs:
        raise SystemExit("FAIL no documents loaded")

    embedder = EmbeddingModel(EmbeddingConfig(model_name=args.model))
    cfg = SplitterConfig(mode="markdown", content_token_limit=token_limit)
    chunks_first = split_documents(list(docs), cfg, token_provider=embedder)
    chunks_second = split_documents(list(docs), cfg, token_provider=embedder)

    deterministic = [_chunk_signature(item) for item in chunks_first] == [
        _chunk_signature(item) for item in chunks_second
    ]

    by_source: dict[str, list[Any]] = defaultdict(list)
    for chunk in chunks_first:
        validate_chunk_acl(chunk)
        by_source[chunk.source_id].append(chunk)

    coverage_failures: list[dict[str, object]] = []
    offset_text_mismatch_count = 0
    structure_violations: list[dict[str, object]] = []
    for document in docs:
        text = Path(document.path).read_text(encoding="utf-8", errors="ignore")
        source_chunks = by_source.get(document.source_id, [])
        ratio = coverage_ratio(text, source_chunks)
        if ratio != 1.0:
            coverage_failures.append({"source_id": document.source_id, "coverage": ratio})
        for chunk in source_chunks:
            start, end = int(chunk.offset_start), int(chunk.offset_end)
            if chunk.text != text[start:end]:
                offset_text_mismatch_count += 1
        for item in structure_preservation_violations(
            text,
            source_chunks,
            embedder,
            content_token_limit=token_limit,
        ):
            structure_violations.append({"source_id": document.source_id, **item})

    texts = [chunk.text for chunk in chunks_first]
    token_counts = embedder.content_token_counts(texts)
    over_budget = [
        {
            "chunk_id": chunk.chunk_id,
            "source_id": chunk.source_id,
            "token_count": count,
        }
        for chunk, count in zip(chunks_first, token_counts)
        if count > token_limit
    ]

    structural_units = Counter(str(chunk.metadata.get("structural_unit", "")) for chunk in chunks_first)
    forced_split_chunk_count = sum(bool(chunk.metadata.get("forced_split")) for chunk in chunks_first)
    fence_forced_split_chunk_count = sum(
        bool(chunk.metadata.get("forced_split")) and bool(chunk.metadata.get("fence_split"))
        for chunk in chunks_first
    )

    inspection: dict[str, list[dict[str, object]]] = {}
    requested = set(str(item) for item in args.inspect_source)
    for source_id in sorted(requested):
        rows = []
        for chunk in by_source.get(source_id, []):
            rows.append(
                {
                    "chunk_id": chunk.chunk_id,
                    "offset_start": int(chunk.offset_start),
                    "offset_end": int(chunk.offset_end),
                    "token_count": int(chunk.metadata.get("token_count", 0)),
                    "structural_unit": str(chunk.metadata.get("structural_unit", "")),
                    "hierarchy_level": chunk.metadata.get("hierarchy_level"),
                    "forced_split": bool(chunk.metadata.get("forced_split")),
                    "forced_split_type": str(chunk.metadata.get("forced_split_type", "")),
                    "section_path": str(chunk.metadata.get("section_path", "")),
                    "section_paths": list(chunk.metadata.get("section_paths", []) or []),
                }
            )
        inspection[source_id] = rows

    coverage_min = 1.0
    if coverage_failures:
        coverage_min = min(float(item["coverage"]) for item in coverage_failures)

    report: dict[str, Any] = {
        "schema_version": "1.0.0",
        "splitter_strategy": "structure_first_largest_fit",
        "model": args.model,
        "content_token_limit": token_limit,
        "document_count": len(docs),
        "chunk_count": len(chunks_first),
        "coverage_min": coverage_min,
        "coverage_failure_count": len(coverage_failures),
        "coverage_failures": coverage_failures,
        "offset_text_mismatch_count": offset_text_mismatch_count,
        "deterministic": deterministic,
        "token_distribution": {
            "p25": _percentile(token_counts, 0.25),
            "p50": _percentile(token_counts, 0.50),
            "p75": _percentile(token_counts, 0.75),
            "p95": _percentile(token_counts, 0.95),
            "max": max(token_counts) if token_counts else 0,
            "mean": statistics.mean(token_counts) if token_counts else 0.0,
        },
        "over_budget_chunk_count": len(over_budget),
        "over_budget_chunks": over_budget[:50],
        "structure_preservation_violation_count": len(structure_violations),
        "structure_preservation_violations": structure_violations[:100],
        "forced_split_chunk_count": forced_split_chunk_count,
        "fence_forced_split_chunk_count": fence_forced_split_chunk_count,
        "complete_subtree_units": sum(
            int(chunk.metadata.get("complete_subtree_count", 0) or 0) for chunk in chunks_first
        ),
        "structural_unit_counts": dict(sorted(structural_units.items())),
        "inspection": inspection,
    }

    hard_fail = any(
        [
            report["coverage_failure_count"],
            report["offset_text_mismatch_count"],
            report["over_budget_chunk_count"],
            not report["deterministic"],
            report["structure_preservation_violation_count"],
        ]
    )
    report["gate_status"] = "FAIL" if hard_fail else "PASS"

    json_path = Path(args.json_report)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path = Path(args.markdown_report)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(_markdown(report), encoding="utf-8")

    print(
        f"{report['gate_status']} structure-first splitter: "
        f"docs={report['document_count']} chunks={report['chunk_count']} "
        f"p50={report['token_distribution']['p50']:.1f} "
        f"p95={report['token_distribution']['p95']:.1f} "
        f"max={report['token_distribution']['max']} "
        f"forced={report['forced_split_chunk_count']} "
        f"structure_violations={report['structure_preservation_violation_count']}"
    )
    return 1 if hard_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
