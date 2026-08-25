from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic_rag.ingest.loaders import LoaderConfig, load_documents
from agentic_rag.ingest.splitters import SplitterConfig, split_documents
from agentic_rag.policy.source_registry import (
    MissingSourcePolicy,
    SourceACLRegistry,
    validate_chunk_acl,
)


class _CharacterTokenBudgetProvider:
    """Deterministic test double; production Markdown still requires its tokenizer."""

    def content_token_counts(self, texts: list[str]) -> list[int]:
        return [len(text) for text in texts]

    def content_token_offsets(self, text: str) -> list[tuple[int, int]]:
        return [(index, index + 1) for index in range(len(text))]


def _registry() -> SourceACLRegistry:
    return SourceACLRegistry(
        schema_version="1.0.0",
        registry_id="test",
        sources={
            "doc.md": {
                "visibility": "internal_demo",
                "allowed_roles": ["engineer"],
                "allowed_groups": ["platform"],
                "tenant_id": None,
            }
        },
    )


class SourceRegistryTests(unittest.TestCase):
    def test_loader_splitter_propagates_acl(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.md"
            path.write_text("# Title\n\n" + ("evidence " * 80), encoding="utf-8")
            docs = load_documents([LoaderConfig(Path(tmp))], acl_registry=_registry())
            chunks = split_documents(
                docs,
                SplitterConfig(mode="char", chunk_size=300, overlap=50, min_size=20),
            )
            self.assertTrue(chunks)
            acl = validate_chunk_acl(chunks[0])
            self.assertEqual(acl["source_id"], "doc.md")
            self.assertEqual(acl["visibility"], "internal_demo")

    def test_unknown_source_fails_during_load(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "unknown.md").write_text("knowledge", encoding="utf-8")
            with self.assertRaises(MissingSourcePolicy):
                load_documents([LoaderConfig(Path(tmp))], acl_registry=_registry())

    def test_source_id_mismatch_fails(self) -> None:
        with self.assertRaises(Exception):
            SourceACLRegistry(
                schema_version="1.0.0",
                registry_id="bad",
                sources={
                    "doc.md": {
                        "source_id": "other.md",
                        "visibility": "public",
                        "allowed_roles": [],
                        "allowed_groups": [],
                        "tenant_id": None,
                    }
                },
            )

    def test_markdown_splitter_preserves_fence_tail_and_offsets(self) -> None:
        text = (
            "# Intro\n\n" + ("中文证据。" * 30) + "\n\n```python\n" +
            ("print('kept')\n" * 12) + "```\n\nTail evidence."
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "doc.md"
            path.write_text(text, encoding="utf-8")
            docs = load_documents([LoaderConfig(Path(tmp))], acl_registry=_registry())
            chunks = split_documents(
                docs,
                SplitterConfig(
                    mode="markdown",
                    chunk_size=180,
                    overlap=30,
                    min_size=40,
                    boundary_search=50,
                    content_token_limit=180,
                ),
                token_provider=_CharacterTokenBudgetProvider(),
            )
            covered = bytearray(len(text))
            for chunk in chunks:
                self.assertEqual(chunk.text, text[chunk.offset_start : chunk.offset_end])
                self.assertLessEqual(len(chunk.text), 180)
                covered[chunk.offset_start : chunk.offset_end] = b"\x01" * (
                    chunk.offset_end - chunk.offset_start
                )
            self.assertTrue(all(covered))
            self.assertIn("print('kept')", "".join(chunk.text for chunk in chunks))
            self.assertIn("Tail evidence.", "".join(chunk.text for chunk in chunks))


if __name__ == "__main__":
    unittest.main()
