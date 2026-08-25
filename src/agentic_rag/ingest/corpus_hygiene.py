"""Recoverable corpus transformations kept outside the online loader root."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


FAQ_HEADING = re.compile(
    r"^#{1,6}\s+.*常见问答(?:（可用于评估出题）|\(可用于评估出题\))?.*$",
    re.MULTILINE,
)
FAQ_QUESTION = re.compile(r"^\*\*Q\d+:", re.MULTILINE)


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class FAQIsolationItem:
    source_id: str
    heading: str
    cut_offset: int
    original_sha256: str
    indexed_sha256: str
    original_char_count: int
    indexed_char_count: int
    faq_question_count: int

    def to_dict(self) -> dict[str, object]:
        return {
            "source_id": self.source_id,
            "heading": self.heading,
            "cut_offset": self.cut_offset,
            "original_sha256": self.original_sha256,
            "indexed_sha256": self.indexed_sha256,
            "original_char_count": self.original_char_count,
            "indexed_char_count": self.indexed_char_count,
            "faq_question_count": self.faq_question_count,
        }


def plan_faq_isolation(corpus_root: str | Path) -> list[tuple[Path, str, str, FAQIsolationItem]]:
    root = Path(corpus_root).resolve()
    planned: list[tuple[Path, str, str, FAQIsolationItem]] = []
    for path in sorted((root / "internal").glob("*.md")):
        original = path.read_text(encoding="utf-8")
        match = FAQ_HEADING.search(original)
        if match is None:
            continue
        indexed = original[: match.start()].rstrip() + "\n"
        item = FAQIsolationItem(
            source_id=path.relative_to(root).as_posix(),
            heading=match.group(0),
            cut_offset=match.start(),
            original_sha256=_hash(original),
            indexed_sha256=_hash(indexed),
            original_char_count=len(original),
            indexed_char_count=len(indexed),
            faq_question_count=len(FAQ_QUESTION.findall(original[match.start() :])),
        )
        planned.append((path, original, indexed, item))
    return planned


def apply_faq_isolation(
    corpus_root: str | Path,
    archive_root: str | Path,
) -> dict[str, object]:
    corpus = Path(corpus_root).resolve()
    archive = Path(archive_root).resolve()
    if archive == corpus or corpus in archive.parents:
        raise ValueError("FAQ archive must be outside the retrieval corpus root")
    planned = plan_faq_isolation(corpus)
    full_documents = archive / "full_documents"
    full_documents.mkdir(parents=True, exist_ok=True)
    for path, original, indexed, item in planned:
        archived_path = full_documents / item.source_id
        archived_path.parent.mkdir(parents=True, exist_ok=True)
        if archived_path.exists():
            existing = archived_path.read_text(encoding="utf-8")
            if existing != original:
                raise ValueError(f"archive conflict: {item.source_id}")
        else:
            archived_path.write_text(original, encoding="utf-8")
        path.write_text(indexed, encoding="utf-8")
    manifest = {
        "schema_version": "1.0.0",
        "dataset_class": "derived_in_domain_regression",
        "archive_policy": "full original documents; excluded from retrieval loader root",
        "document_count": len(planned),
        "faq_question_count": sum(item.faq_question_count for *_, item in planned),
        "items": [item.to_dict() for *_, item in planned],
    }
    archive.mkdir(parents=True, exist_ok=True)
    (archive / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def restore_faq_archive(corpus_root: str | Path, archive_root: str | Path) -> int:
    corpus = Path(corpus_root).resolve()
    archive = Path(archive_root).resolve()
    manifest = json.loads((archive / "manifest.json").read_text(encoding="utf-8"))
    restored = 0
    for raw in list(manifest.get("items", []) or []):
        item = dict(raw)
        source_id = str(item["source_id"])
        target = corpus / source_id
        current = target.read_text(encoding="utf-8")
        if _hash(current) != str(item["indexed_sha256"]):
            raise ValueError(f"refusing to overwrite changed indexed document: {source_id}")
        original = (archive / "full_documents" / source_id).read_text(encoding="utf-8")
        if _hash(original) != str(item["original_sha256"]):
            raise ValueError(f"archive hash mismatch: {source_id}")
        target.write_text(original, encoding="utf-8")
        restored += 1
    return restored


__all__ = [
    "FAQIsolationItem",
    "apply_faq_isolation",
    "plan_faq_isolation",
    "restore_faq_archive",
]
