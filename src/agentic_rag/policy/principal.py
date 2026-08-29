"""
程序作用：
定义可信调用身份及本地认证适配器，避免请求方通过业务参数自行声明角色、用户组或租户。

整体结构：
1）Principal 保存主体身份、角色、用户组、租户和认证方式；
2）anonymous、local_cli、eval 三类构造函数生成固定权限边界的可信身份；
3）StaticTokenAuthAdapter 用服务端配置的 opaque token 解析 API 调用身份。
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field
from typing import Any, Mapping, Optional

from agentic_rag.config import AuthConfig


class AuthenticationRequired(PermissionError):
    pass


class AuthenticationConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class Principal:
    principal_id: str
    roles: frozenset[str] = field(default_factory=frozenset)
    groups: frozenset[str] = field(default_factory=frozenset)
    tenant_id: Optional[str] = None
    auth_mode: str = "unknown"

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles

    def to_dict(self) -> dict[str, Any]:
        return {
            "principal_id": self.principal_id,
            "roles": sorted(self.roles),
            "groups": sorted(self.groups),
            "tenant_id": self.tenant_id,
            "auth_mode": self.auth_mode,
        }


def anonymous_principal() -> Principal:
    return Principal(
        principal_id="anonymous",
        roles=frozenset({"anonymous"}),
        auth_mode="anonymous",
    )


def local_cli_principal() -> Principal:
    """生成可信本地 CLI 身份；调用方不能自行传入角色或租户。"""

    return Principal(
        principal_id="local-cli",
        # 出站始终按专用能力判断，admin 身份本身不授予导出权；本地可信适配器只显式允许公开查询使用云端 profile，受限证据仍由 ACL 拒绝。
        roles=frozenset({"admin", "operator", "public_egress"}),
        groups=frozenset({"local"}),
        auth_mode="local_cli",
    )


def eval_principal() -> Principal:
    return Principal(
        principal_id="eval-runner",
        roles=frozenset({"admin", "evaluator", "public_egress"}),
        groups=frozenset({"evaluation"}),
        auth_mode="trusted_eval",
    )


def _string_set(value: Any, field_name: str) -> frozenset[str]:
    if value is None:
        return frozenset()
    if not isinstance(value, (list, tuple, set, frozenset)):
        raise AuthenticationConfigurationError(f"principal {field_name} must be a list")
    return frozenset(str(item).strip() for item in value if str(item).strip())


def _principal_from_mapping(raw: Mapping[str, Any], auth_mode: str) -> Principal:
    allowed = {"principal_id", "roles", "groups", "tenant_id"}
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise AuthenticationConfigurationError(
            f"unknown principal field(s): {', '.join(unknown)}"
        )
    principal_id = str(raw.get("principal_id") or "").strip()
    if not principal_id:
        raise AuthenticationConfigurationError("principal_id is required")
    tenant_raw = raw.get("tenant_id")
    return Principal(
        principal_id=principal_id,
        roles=_string_set(raw.get("roles"), "roles"),
        groups=_string_set(raw.get("groups"), "groups"),
        tenant_id=str(tenant_raw) if tenant_raw not in {None, ""} else None,
        auth_mode=auth_mode,
    )


class StaticTokenAuthAdapter:
    """使用 opaque 本地 API token 解析身份，不在主体对象中保留 token 明文。"""

    def __init__(self, config: AuthConfig, raw_json: Optional[str] = None) -> None:
        self.config = config
        source = raw_json if raw_json is not None else os.getenv(config.principals_env, "")
        self._principals_by_digest: dict[str, Principal] = {}
        if source.strip():
            try:
                parsed = json.loads(source)
            except json.JSONDecodeError as exc:
                raise AuthenticationConfigurationError(
                    f"{config.principals_env} must contain a JSON object"
                ) from exc
            if not isinstance(parsed, Mapping):
                raise AuthenticationConfigurationError(
                    f"{config.principals_env} must contain a JSON object"
                )
            for token, principal_raw in parsed.items():
                if not isinstance(principal_raw, Mapping):
                    raise AuthenticationConfigurationError("each token must map to a principal object")
                token_text = str(token)
                if len(token_text) < 12:
                    raise AuthenticationConfigurationError("static token must contain at least 12 characters")
                digest = hashlib.sha256(token_text.encode("utf-8")).hexdigest()
                self._principals_by_digest[digest] = _principal_from_mapping(
                    principal_raw,
                    auth_mode=config.mode,
                )

    def resolve(self, token: Optional[str]) -> Principal:
        token_text = str(token or "").strip()
        if not token_text:
            if self.config.required:
                raise AuthenticationRequired("authentication credential is required")
            return anonymous_principal()
        digest = hashlib.sha256(token_text.encode("utf-8")).hexdigest()
        principal = self._principals_by_digest.get(digest)
        if principal is None:
            raise AuthenticationRequired("authentication credential is invalid")
        return principal


__all__ = [
    "AuthenticationConfigurationError",
    "AuthenticationRequired",
    "Principal",
    "StaticTokenAuthAdapter",
    "anonymous_principal",
    "eval_principal",
    "local_cli_principal",
]
