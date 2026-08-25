"""Atomic offline index build: load → ACL → tokenizer-budgeted split → hard gate → embed → publish."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, List, Optional, Sequence
from uuid import uuid4

import numpy as np

from agentic_rag.embed.embeddings import EmbeddingConfig, EmbeddingModel
from agentic_rag.ingest.loaders import LoaderConfig, load_documents
from agentic_rag.ingest.splitters import SplitterConfig, coverage_ratio, split_documents
from agentic_rag.policy.source_registry import SourceACLRegistry, validate_chunk_acl
from agentic_rag.store.vector_store import LocalVectorStore, VectorStoreConfig


@dataclass(frozen=True)
class IndexStats:
    doc_count: int
    chunk_count: int
    embed_model: str
    dim: int
    index_time_ms: int
    build_id: str = ""
    vector_store_dir: str = ""
    manifest_path: str = ""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _canonical_hash(value: object) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(encoded).hexdigest()


def _portable_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / f".{path.name}.{uuid4().hex}.tmp"
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _build_id(corpus_hash: str, config_hash: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return f"{timestamp}-{corpus_hash[:8]}-{config_hash[:8]}"


def index_corpus(
    corpus_dir: str = "data/corpus/phase_a",
    splitter_cfg: Optional[SplitterConfig] = None,
    embed_cfg: Optional[EmbeddingConfig] = None,
    store_cfg: Optional[VectorStoreConfig] = None,
    rebuild: bool = False,
    *,
    artifacts_dir: str = "artifacts",
    acl_registry_path: str = "policy/source_acl.yaml",
    excluded_source_ids: Sequence[str] = ("internal/README.md",),
    embedder_factory: Optional[Callable[[EmbeddingConfig], object]] = None,
) -> IndexStats:
    """Build an immutable index and atomically advance `current.json`.

    `rebuild` is retained for CLI compatibility. It never deletes the previous
    build; a successful pointer switch makes rollback a one-file operation.
    """
    del rebuild, store_cfg
    started = time.perf_counter()
    corpus = Path(corpus_dir).expanduser().resolve()
    artifacts = Path(artifacts_dir).expanduser().resolve()
    builds_root = artifacts / "index" / "builds"
    builds_root.mkdir(parents=True, exist_ok=True)
    registry = SourceACLRegistry.load(acl_registry_path)
    documents = load_documents(
        [LoaderConfig(root_dir=corpus, enabled=corpus.exists(), priority=0, tags=["retrieval_corpus"])],
        acl_registry=registry,
        excluded_source_ids=excluded_source_ids,
    )
    if not documents:
        raise RuntimeError("index build has no documents")
    embedding = embed_cfg or EmbeddingConfig()
    embedder = (
        embedder_factory(embedding) if embedder_factory is not None else EmbeddingModel(embedding)
    )
    splitter = splitter_cfg or SplitterConfig(
        mode="markdown",
        preserve_code_block=True,
        content_token_limit=510,
    )
    chunks = split_documents(documents, splitter, token_provider=embedder)
    if not chunks:
        raise RuntimeError("index build has no chunks")
    by_source: dict[str, list[object]] = {}
    for chunk in chunks:
        validate_chunk_acl(chunk)
        by_source.setdefault(chunk.source_id, []).append(chunk)
    coverage_failures = []
    for document in documents:
        text = Path(document.path).read_text(encoding="utf-8", errors="ignore")
        ratio = coverage_ratio(text, by_source.get(document.source_id, []))
        if ratio != 1.0:
            coverage_failures.append({"source_id": document.source_id, "coverage": ratio})
    if coverage_failures:
        raise RuntimeError(f"splitter coverage gate failed: {coverage_failures[:5]}")

    texts = [chunk.text for chunk in chunks]
    token_gate = embedder.validate_content_token_budget(
        texts,
        max_content_tokens=int(splitter.content_token_limit),
    )
    vectors = embedder.embed(texts)
    dim = int(getattr(embedder, "dim"))
    if len(vectors) != len(chunks):
        raise RuntimeError("embedding row count does not match chunk count")

    corpus_hash = _canonical_hash(
        [{"source_id": document.source_id, "doc_hash": document.doc_hash} for document in documents]
    )
    build_config = {
        "splitter": asdict(splitter),
        "embedding": asdict(embedding),
        "excluded_source_ids": sorted(str(item) for item in excluded_source_ids),
        "acl_registry_hash": registry.fingerprint(),
    }
    config_hash = _canonical_hash(build_config)
    build_id = _build_id(corpus_hash, config_hash)
    staging = Path(tempfile.mkdtemp(prefix=f".staging-{build_id}-", dir=builds_root))
    final_build = builds_root / build_id
    try:
        vector_dir = staging / "vector_store"
        store = LocalVectorStore(VectorStoreConfig(persist_dir=vector_dir.as_posix()))
        store.upsert(chunks, vectors)
        persisted_vectors = np.load(vector_dir / "vectors.npy", mmap_mode="r")
        persisted_rows = sum(
            1
            for line in (vector_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
        if persisted_vectors.shape != (len(chunks), dim) or persisted_rows != len(chunks):
            raise RuntimeError(
                "persisted index shape mismatch: "
                f"vectors={persisted_vectors.shape} rows={persisted_rows} chunks={len(chunks)} dim={dim}"
            )
        manifest = {
            "schema_version": "2.0.0",
            "build_id": build_id,
            "built_at_utc": datetime.now(timezone.utc).isoformat(),
            "corpus": {
                "root": str(corpus_dir),
                "hash": corpus_hash,
                "document_count": len(documents),
                "excluded_source_ids": sorted(str(item) for item in excluded_source_ids),
                "dataset_class": "retrieval_corpus_without_eval_seed_faq",
            },
            "splitter": {
                **asdict(splitter),
                "strategy": (
                    "structure_first_largest_fit"
                    if splitter.mode == "markdown"
                    else splitter.mode
                ),
                "coverage_min": 1.0,
            },
            "embedding": {
                "model": embedding.model_name,
                "dimension": dim,
                "normalize": embedding.normalize,
                "max_sequence_length": 512,
                **token_gate,
            },
            "acl": {
                "registry_id": registry.registry_id,
                "registry_hash": registry.fingerprint(),
                "registered_source_count": len(registry.source_ids()),
                "indexed_source_count": len(documents),
                "missing_count": 0,
                "conflict_count": 0,
            },
            "artifacts": {
                "chunk_count": len(chunks),
                "vector_rows": int(persisted_vectors.shape[0]),
                "vectors_sha256": _sha256_file(vector_dir / "vectors.npy"),
                "chunks_sha256": _sha256_file(vector_dir / "chunks.jsonl"),
            },
            "build_config_hash": config_hash,
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        os.replace(staging, final_build)
        final_vector_dir = final_build / "vector_store"
        final_manifest = final_build / "manifest.json"
        pointer = {
            "schema_version": "1.0.0",
            "build_id": build_id,
            "vector_store_dir": _portable_path(final_vector_dir),
            "manifest_path": _portable_path(final_manifest),
        }
        _atomic_json(artifacts / "index" / "current.json", pointer)
    except Exception:
        if staging.exists() and staging.parent == builds_root:
            shutil.rmtree(staging)
        raise

    elapsed_ms = int(round((time.perf_counter() - started) * 1000.0))
    return IndexStats(
        doc_count=len(documents),
        chunk_count=len(chunks),
        embed_model=embedding.model_name,
        dim=dim,
        index_time_ms=elapsed_ms,
        build_id=build_id,
        vector_store_dir=final_vector_dir.as_posix(),
        manifest_path=final_manifest.as_posix(),
    )


__all__ = ["IndexStats", "index_corpus"]
