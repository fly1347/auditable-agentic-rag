"""
程序作用：
定义带版本的规范执行记录 CER、执行事件和只追加 JSONL 写入器，并提供对外脱敏投影。

整体结构：
1）ExecutionEvent 描述有序执行事件；
2）CanonicalExecutionRecord 汇总身份、策略、检索、提示、模型调用、断言与结果；
3）脱敏辅助函数清除私有正文和连接信息，JsonlRecordSink 负责线程安全落盘。
"""

from __future__ import annotations

import copy
import hashlib
import json
import re
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ExecutionEvent:
    sequence: int
    event_type: str
    timestamp: str
    stage: Optional[str] = None
    duration_ms: Optional[float] = None
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class CanonicalExecutionRecord:
    schema_version: str
    identity: dict[str, Any]
    provenance: dict[str, Any]
    principal: dict[str, Any]
    query: str
    started_at: str = field(default_factory=_utc_now)
    completed_at: Optional[str] = None
    policy: dict[str, Any] = field(default_factory=dict)
    route: dict[str, Any] = field(default_factory=dict)
    retrieval: dict[str, Any] = field(default_factory=lambda: {"rounds": []})
    rerank: dict[str, Any] = field(default_factory=dict)
    merge: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)
    prompt: dict[str, Any] = field(default_factory=dict)
    sufficiency: dict[str, Any] = field(default_factory=dict)
    model_calls: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)
    timing: dict[str, Any] = field(default_factory=dict)
    outcome: dict[str, Any] = field(default_factory=dict)
    evaluation: dict[str, Any] = field(default_factory=dict)
    errors: list[dict[str, Any]] = field(default_factory=list)
    sanitization: dict[str, Any] = field(default_factory=dict)
    events: list[ExecutionEvent] = field(default_factory=list)

    def append_event(
        self,
        event_type: str,
        *,
        stage: Optional[str] = None,
        duration_ms: Optional[float] = None,
        payload: Optional[Mapping[str, Any]] = None,
    ) -> ExecutionEvent:
        event = ExecutionEvent(
            sequence=len(self.events) + 1,
            event_type=str(event_type),
            timestamp=_utc_now(),
            stage=stage,
            duration_ms=float(duration_ms) if duration_ms is not None else None,
            payload=dict(payload or {}),
        )
        self.events.append(event)
        return event

    def finish(self, status: str, **outcome: Any) -> None:
        self.outcome = {**self.outcome, "status": str(status), **outcome}
        self.completed_at = _utc_now()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["events"] = [asdict(event) for event in self.events]
        return value

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "CanonicalExecutionRecord":
        data = dict(raw)
        events = [ExecutionEvent(**dict(item)) for item in list(data.pop("events", []) or [])]
        return cls(events=events, **data)

    def parity_fingerprint(self) -> str:
        data = self.to_dict()
        data.pop("started_at", None)
        data.pop("completed_at", None)
        identity = dict(data.get("identity", {}))
        for key in ("request_id", "session_id"):
            identity.pop(key, None)
        data["identity"] = identity
        for event in data.get("events", []):
            event.pop("timestamp", None)
        encoded = json.dumps(data, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def sanitized_dict(self) -> dict[str, Any]:
        data = copy.deepcopy(self.to_dict())
        dropped = 0

        principal = dict(data.get("principal", {}))
        for key in ("roles", "groups", "tenant_id"):
            if key in principal:
                principal.pop(key, None)
                dropped += 1
        data["principal"] = principal

        # 敏感证据预览可能出现在检索、提示、事件或历史兼容字段中，因此对完整投影统一执行白名单式正文清除，不能只假设一种旧结构。
        for container in list(data.values()):
            dropped += _drop_sensitive_text(container)

        for call in data.get("model_calls", []):
            if isinstance(call, dict):
                for key in (
                    "api_key",
                    "api_key_env",
                    "api_key_hash",
                    "endpoint",
                    "base_url",
                    "prompt",
                    "error_message",
                ):
                    if key in call:
                        call.pop(key, None)
                        dropped += 1

        for error in data.get("errors", []):
            if isinstance(error, dict) and isinstance(error.get("message"), str):
                error["message"] = _sanitize_paths(error["message"])

        dropped += _sanitize_paths_in_place(data)

        data["sanitization"] = {
            "profile": "public_release_v1",
            "applied_rules": ["drop_private_principal", "drop_evidence_text", "drop_prompt_text", "drop_provider_endpoints", "sanitize_paths"],
            "dropped_field_count": dropped,
        }
        return data


def _drop_sensitive_text(value: Any) -> int:
    dropped = 0
    if isinstance(value, dict):
        for key in list(value):
            if key in {"text", "text_preview", "prompt", "prompt_text", "raw_prompt", "rendered_prompt", "chunk_text"}:
                value.pop(key, None)
                dropped += 1
            else:
                dropped += _drop_sensitive_text(value[key])
    elif isinstance(value, list):
        for item in value:
            dropped += _drop_sensitive_text(item)
    return dropped


_UNIX_PATH = re.compile(r"/(?:home|Users)/[^\s]+")
_WINDOWS_PATH = re.compile(r"(?i)[A-Z]:\\Users\\[^\s]+")


def _sanitize_paths(text: str) -> str:
    return _WINDOWS_PATH.sub("<local-path>", _UNIX_PATH.sub("<local-path>", text))


def _sanitize_paths_in_place(value: Any) -> int:
    changed = 0
    if isinstance(value, dict):
        for key, item in list(value.items()):
            if isinstance(item, str):
                sanitized = _sanitize_paths(item)
                if sanitized != item:
                    value[key] = sanitized
                    changed += 1
            else:
                changed += _sanitize_paths_in_place(item)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            if isinstance(item, str):
                sanitized = _sanitize_paths(item)
                if sanitized != item:
                    value[index] = sanitized
                    changed += 1
            else:
                changed += _sanitize_paths_in_place(item)
    return changed


class JsonlRecordSink:
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self._lock = threading.Lock()

    def append(self, record: CanonicalExecutionRecord) -> None:
        line = json.dumps(record.to_dict(), ensure_ascii=False, sort_keys=True)
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")


__all__ = ["CanonicalExecutionRecord", "ExecutionEvent", "JsonlRecordSink"]
