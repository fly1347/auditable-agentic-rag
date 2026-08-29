"""
程序作用：
维护带版本的来源级 ACL 注册表，并把来源权限不可变地传播到文档和 chunk 元数据。

整体结构：
1）normalize_acl 校验并规范化可见级别、角色、用户组和租户字段；
2）SourceACLRegistry 负责从 YAML 加载、查询并导出来源策略；
3）validate_chunk_acl 与 propagate_document_acl 检查 lineage 并防止权限在切分时被篡改或丢失。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping, Optional

try:
    import yaml
except Exception:  # pragma: no cover - reported by load
    yaml = None

from agentic_rag.types import Chunk, Document


ALLOWED_VISIBILITIES = {"public", "internal_demo", "internal", "confidential", "private"}
ACL_FIELDS = {"visibility", "allowed_roles", "allowed_groups", "tenant_id"}


class SourceRegistryError(ValueError):
    pass


class MissingSourcePolicy(SourceRegistryError):
    pass


def normalize_acl(source_id: str, raw: Mapping[str, Any]) -> dict[str, Any]:
    unknown = sorted(set(raw) - ACL_FIELDS - {"source_id"})
    if unknown:
        raise SourceRegistryError(
            f"unknown ACL field(s) for {source_id}: {', '.join(unknown)}"
        )
    visibility = str(raw.get("visibility") or "").strip().lower()
    if visibility not in ALLOWED_VISIBILITIES:
        raise SourceRegistryError(
            f"invalid visibility for {source_id}: {visibility or '<empty>'}"
        )
    declared_source = raw.get("source_id")
    if declared_source not in (None, "", source_id):
        raise SourceRegistryError(
            f"ACL source_id mismatch: registry={source_id} acl={declared_source}"
        )
    # 去重时保留声明顺序，便于迁移前后做字节级核对；实际权限判断仍把这些列表视为集合。
    roles = list(dict.fromkeys(str(item) for item in list(raw.get("allowed_roles", []) or [])))
    groups = list(dict.fromkeys(str(item) for item in list(raw.get("allowed_groups", []) or [])))
    tenant = raw.get("tenant_id")
    return {
        "visibility": visibility,
        "allowed_roles": roles,
        "allowed_groups": groups,
        "tenant_id": None if tenant in (None, "") else str(tenant),
        "source_id": str(source_id),
    }


class SourceACLRegistry:
    def __init__(
        self,
        *,
        schema_version: str,
        registry_id: str,
        sources: Mapping[str, Mapping[str, Any]],
        default_behavior: str = "deny",
    ) -> None:
        if str(default_behavior) != "deny":
            raise SourceRegistryError("source ACL default_behavior must be deny")
        self.schema_version = str(schema_version)
        self.registry_id = str(registry_id)
        self.default_behavior = "deny"
        self._sources = {
            str(source_id): normalize_acl(str(source_id), dict(acl))
            for source_id, acl in sorted(sources.items())
        }

    @classmethod
    def from_dict(cls, raw: Mapping[str, Any]) -> "SourceACLRegistry":
        allowed = {"schema_version", "registry_id", "default_behavior", "sources"}
        unknown = sorted(set(raw) - allowed)
        if unknown:
            raise SourceRegistryError(f"unknown source registry key(s): {', '.join(unknown)}")
        sources = raw.get("sources")
        if not isinstance(sources, Mapping):
            raise SourceRegistryError("source registry sources must be a mapping")
        return cls(
            schema_version=str(raw.get("schema_version") or ""),
            registry_id=str(raw.get("registry_id") or ""),
            default_behavior=str(raw.get("default_behavior") or "deny"),
            sources={str(key): dict(value) for key, value in sources.items()},
        )

    @classmethod
    def load(cls, path: str | Path) -> "SourceACLRegistry":
        if yaml is None:
            raise RuntimeError("pyyaml is required to load source ACL registry")
        source = Path(path)
        raw = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, Mapping):
            raise SourceRegistryError("source ACL registry must be a mapping")
        return cls.from_dict(raw)

    def to_dict(self, *, include_source_id: bool = False) -> dict[str, Any]:
        sources: dict[str, Any] = {}
        for source_id, raw in self._sources.items():
            acl = dict(raw)
            if not include_source_id:
                acl.pop("source_id", None)
            sources[source_id] = acl
        return {
            "schema_version": self.schema_version,
            "registry_id": self.registry_id,
            "default_behavior": self.default_behavior,
            "sources": sources,
        }

    def fingerprint(self) -> str:
        encoded = json.dumps(
            self.to_dict(include_source_id=True),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def source_ids(self) -> tuple[str, ...]:
        return tuple(self._sources)

    def resolve(self, source_id: str) -> Optional[dict[str, Any]]:
        acl = self._sources.get(str(source_id))
        return dict(acl) if acl is not None else None

    def require(self, source_id: str) -> dict[str, Any]:
        acl = self.resolve(source_id)
        if acl is None:
            raise MissingSourcePolicy(
                f"source ACL missing under deny-by-default policy: {source_id}"
            )
        return acl

    def attach(self, document: Document) -> Document:
        metadata = dict(document.metadata or {})
        metadata["acl"] = self.require(document.source_id)
        metadata["acl_registry_id"] = self.registry_id
        metadata["acl_registry_hash"] = self.fingerprint()
        return replace(document, metadata=metadata)


def validate_chunk_acl(chunk: Chunk) -> dict[str, Any]:
    metadata = dict(chunk.metadata or {})
    raw = metadata.get("acl")
    if not isinstance(raw, Mapping):
        raise MissingSourcePolicy(f"chunk ACL missing: {chunk.chunk_id}")
    return normalize_acl(str(chunk.source_id), dict(raw))


def propagate_document_acl(document: Document, metadata: Mapping[str, Any]) -> dict[str, Any]:
    """把文档 ACL 复制到 chunk 元数据，并拒绝权限改写或 lineage 缺失。"""
    document_metadata = dict(document.metadata or {})
    raw = document_metadata.get("acl")
    if not isinstance(raw, Mapping):
        raise MissingSourcePolicy(f"document ACL missing: {document.source_id}")
    acl = normalize_acl(str(document.source_id), dict(raw))
    result = dict(metadata)
    result["acl"] = acl
    for key in ("acl_registry_id", "acl_registry_hash"):
        if key in document_metadata:
            result[key] = document_metadata[key]
    return result


__all__ = [
    "ALLOWED_VISIBILITIES",
    "MissingSourcePolicy",
    "SourceACLRegistry",
    "SourceRegistryError",
    "normalize_acl",
    "propagate_document_acl",
    "validate_chunk_acl",
]
