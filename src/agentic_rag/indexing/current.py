"""Resolve the small atomic pointer to an immutable index build directory."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class CurrentIndex:
    build_id: str
    vector_store_dir: Path
    manifest_path: Path


def _resolve_path(value: str, pointer_path: Path) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path.resolve()
    # Pointers are normally project-relative. Fall back to pointer parent for
    # portable externally supplied pointers.
    project_candidate = (Path.cwd() / path).resolve()
    if project_candidate.exists():
        return project_candidate
    return (pointer_path.parent / path).resolve()


def load_current_index(pointer_path: str | Path) -> Optional[CurrentIndex]:
    pointer = Path(pointer_path).expanduser().resolve()
    if not pointer.exists():
        return None
    raw = json.loads(pointer.read_text(encoding="utf-8"))
    build_id = str(raw.get("build_id") or "")
    vector_store = _resolve_path(str(raw.get("vector_store_dir") or ""), pointer)
    manifest = _resolve_path(str(raw.get("manifest_path") or ""), pointer)
    if not build_id or not (vector_store / "vectors.npy").exists() or not (
        vector_store / "chunks.jsonl"
    ).exists():
        raise RuntimeError(f"current index pointer is invalid: {pointer}")
    if not manifest.exists():
        raise RuntimeError(f"current index manifest is missing: {manifest}")
    return CurrentIndex(build_id, vector_store, manifest)


def resolve_vector_store_dir(
    fallback_dir: str | Path,
    *,
    pointer_path: str | Path = "artifacts/index/current.json",
) -> Path:
    current = load_current_index(pointer_path)
    return current.vector_store_dir if current is not None else Path(fallback_dir).expanduser().resolve()


__all__ = ["CurrentIndex", "load_current_index", "resolve_vector_store_dir"]
