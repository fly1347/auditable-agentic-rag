"""Process-level dependency lifecycle for model and index objects."""

from __future__ import annotations

import threading
import json
from pathlib import Path
from typing import Any, Callable, Optional

from agentic_rag.config import AppConfig
from agentic_rag.engine.baseline import BaselineEngineAdapter
from agentic_rag.engine.orchestrated import OrchestratedEngine
from agentic_rag.indexing.current import load_current_index, resolve_vector_store_dir
from agentic_rag.policy.source_registry import SourceACLRegistry


class RuntimeContainer:
    def __init__(
        self,
        config: AppConfig,
        *,
        retriever_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.config = config
        self._retriever_factory = retriever_factory
        self._retriever: Any = None
        self._lock = threading.RLock()

    def get_retriever(self) -> Any:
        with self._lock:
            if self._retriever is None:
                factory = self._retriever_factory
                if factory is None:
                    from agentic_rag.embed.embeddings import EmbeddingConfig
                    from agentic_rag.retrieve.retriever import Retriever
                    from agentic_rag.store.vector_store import VectorStoreConfig

                    def factory() -> Any:
                        pointer_path = Path(self.config.index.manifest_path).parent / "current.json"
                        return Retriever(
                            embed_cfg=EmbeddingConfig(),
                            store_cfg=VectorStoreConfig(
                                persist_dir=resolve_vector_store_dir(
                                    self.config.index.vector_store_dir,
                                    pointer_path=pointer_path,
                                ).as_posix()
                            ),
                        )

                self._retriever = factory()
            return self._retriever

    def baseline_engine(self) -> BaselineEngineAdapter:
        return BaselineEngineAdapter(
            self.config,
            retriever=self.get_retriever(),
        )

    def orchestrated_engine(self) -> OrchestratedEngine:
        return OrchestratedEngine(
            self.config,
            retriever=self.get_retriever(),
        )

    def index_provenance(self) -> dict[str, Any]:
        pointer_path = Path(self.config.index.manifest_path).parent / "current.json"
        current = load_current_index(pointer_path)
        manifest_path = current.manifest_path if current is not None else Path(self.config.index.manifest_path)
        manifest: dict[str, Any] = {}
        if manifest_path.exists():
            raw = json.loads(manifest_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                manifest = raw
        registry = SourceACLRegistry.load(self.config.index.acl_registry_path)
        return {
            "index_build_id": current.build_id if current is not None else manifest.get("build_id"),
            "corpus_hash": dict(manifest.get("corpus") or {}).get("hash", manifest.get("corpus_hash")),
            "acl_registry_version": registry.registry_id,
            "acl_registry_hash": registry.fingerprint(),
        }

    def reset_index_dependencies(self) -> None:
        with self._lock:
            self._retriever = None


__all__ = ["RuntimeContainer"]
