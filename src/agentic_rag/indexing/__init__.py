"""Versioned index build and current-pointer utilities."""

from agentic_rag.indexing.current import CurrentIndex, load_current_index, resolve_vector_store_dir

__all__ = ["CurrentIndex", "load_current_index", "resolve_vector_store_dir"]
