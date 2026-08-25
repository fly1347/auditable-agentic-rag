"""Application command contract shared by CLI, API, UI and eval adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class QueryCommand:
    query: str
    profile: Optional[str] = None
    request_id: Optional[str] = None
    run_id: Optional[str] = None
    qid: Optional[str] = None
    session_id: Optional[str] = None
    topk: Optional[int] = None
    debug: bool = False

    def normalized_query(self) -> str:
        value = str(self.query).strip()
        if not value:
            raise ValueError("query must not be empty")
        return value


__all__ = ["QueryCommand"]
