"""
程序作用：
定义来源 ACL 的基础数据模型与判定规则，并在检索候选进入 TopK 结果前执行用户、角色、用户组和租户过滤。

整体结构：
1）UserContext、SourceACL、PolicyDecision 描述调用者、来源权限和判定结果；
2）parse_source_acl 与 can_read_source 解析并判断单个来源；
3）filter_sources_by_acl 批量过滤候选并保留允许、拒绝明细。
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any, Mapping


PUBLIC = "public"
INTERNAL_DEMO = "internal_demo"
INTERNAL = "internal"
CONFIDENTIAL = "confidential"
PRIVATE = "private"

KNOWN_VISIBILITIES = {PUBLIC, INTERNAL_DEMO, INTERNAL, CONFIDENTIAL, PRIVATE}


@dataclass(frozen=True)
class UserContext:
    """最小用户上下文。

    tenant_id 仅预留，不在 Step 5 默认强制拦截。
    """

    user_id: str
    roles: frozenset[str] = field(default_factory=frozenset)
    groups: frozenset[str] = field(default_factory=frozenset)
    tenant_id: str | None = None

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles


@dataclass(frozen=True)
class SourceACL:
    """Source / chunk 级 ACL 描述。

    visibility:
      - public: 所有用户可见
      - internal_demo / internal / confidential / private: 必须显式授权
    """

    visibility: str
    allowed_roles: frozenset[str] = field(default_factory=frozenset)
    allowed_groups: frozenset[str] = field(default_factory=frozenset)
    tenant_id: str | None = None
    source_id: str | None = None


@dataclass(frozen=True)
class PolicyDecision:
    """ACL 判定结果。"""

    allowed: bool
    decision: str
    reason: str
    user_id: str
    visibility: str | None = None
    source_id: str | None = None
    tenant_id_checked: bool = False


def anonymous_user_context() -> UserContext:
    return UserContext(user_id="anonymous", roles=frozenset({"anonymous"}), groups=frozenset())


def build_demo_user_context(user_id: str | None) -> UserContext:
    """构造 Phase E demo 用户。

    unknown user 按 anonymous 处理，避免把未识别身份误放行为内部用户。
    """

    normalized = (user_id or "anonymous").strip().lower()

    if normalized == "alice":
        return UserContext(
            user_id="alice",
            roles=frozenset({"engineer"}),
            groups=frozenset({"platform"}),
            tenant_id="demo",
        )

    if normalized == "bob":
        return UserContext(
            user_id="bob",
            roles=frozenset({"analyst"}),
            groups=frozenset({"product"}),
            tenant_id="demo",
        )

    if normalized == "admin":
        return UserContext(
            user_id="admin",
            roles=frozenset({"admin"}),
            groups=frozenset({"admin"}),
            tenant_id="demo",
        )

    return anonymous_user_context()


def _as_frozenset(value: Any) -> frozenset[str]:
    if value is None:
        return frozenset()

    if isinstance(value, str):
        stripped = value.strip()
        return frozenset({stripped}) if stripped else frozenset()

    if isinstance(value, (list, tuple, set, frozenset)):
        return frozenset(str(item).strip() for item in value if str(item).strip())

    return frozenset({str(value).strip()}) if str(value).strip() else frozenset()


def parse_source_acl(metadata: Mapping[str, Any] | None) -> SourceACL | None:
    """从 source/chunk metadata 中解析 ACL。

    支持两种形式：
      metadata["acl"] = {...}
      metadata 直接含 visibility / allowed_roles / allowed_groups

    返回 None 表示 ACL 缺失；运行时必须 deny。
    """

    if not metadata:
        return None

    raw_acl = metadata.get("acl") if isinstance(metadata.get("acl"), Mapping) else metadata

    visibility = raw_acl.get("visibility")
    if visibility is None:
        return None

    return SourceACL(
        visibility=str(visibility).strip(),
        allowed_roles=_as_frozenset(raw_acl.get("allowed_roles")),
        allowed_groups=_as_frozenset(raw_acl.get("allowed_groups")),
        tenant_id=raw_acl.get("tenant_id"),
        source_id=raw_acl.get("source_id") or metadata.get("source_id") or metadata.get("chunk_id"),
    )


def can_read_source(
    user_context: UserContext | None,
    source_acl: SourceACL | None,
) -> PolicyDecision:
    """判断用户是否可读某 source/chunk。

    Phase E Step 5 固定原则：
      - acl 缺失 -> deny
      - user_context 缺失 -> anonymous / public-only
      - unknown visibility -> deny
      - admin 可见全部
      - public 对所有用户可见
      - internal_demo / internal / confidential / private 必须显式授权
      - source 声明 tenant_id 时必须与可信 user tenant 匹配
    """

    user = user_context or anonymous_user_context()

    if source_acl is None:
        return PolicyDecision(
            allowed=False,
            decision="DENY",
            reason="acl_missing",
            user_id=user.user_id,
        )

    visibility = source_acl.visibility

    if visibility not in KNOWN_VISIBILITIES:
        return PolicyDecision(
            allowed=False,
            decision="DENY",
            reason="unknown_visibility",
            user_id=user.user_id,
            visibility=visibility,
            source_id=source_acl.source_id,
        )

    if user.is_admin:
        return PolicyDecision(
            allowed=True,
            decision="ALLOW",
            reason="admin_override",
            user_id=user.user_id,
            visibility=visibility,
            source_id=source_acl.source_id,
        )

    if visibility == PUBLIC:
        return PolicyDecision(
            allowed=True,
            decision="ALLOW",
            reason="public",
            user_id=user.user_id,
            visibility=visibility,
            source_id=source_acl.source_id,
        )

    if source_acl.tenant_id is not None:
        if user.tenant_id is None or str(user.tenant_id) != str(source_acl.tenant_id):
            return PolicyDecision(
                allowed=False,
                decision="DENY",
                reason="tenant_mismatch",
                user_id=user.user_id,
                visibility=visibility,
                source_id=source_acl.source_id,
                tenant_id_checked=True,
            )

    role_match = bool(user.roles & source_acl.allowed_roles)
    group_match = bool(user.groups & source_acl.allowed_groups)

    if role_match or group_match:
        return PolicyDecision(
            allowed=True,
            decision="ALLOW",
            reason="explicit_role_or_group_grant",
            user_id=user.user_id,
            visibility=visibility,
            source_id=source_acl.source_id,
            tenant_id_checked=source_acl.tenant_id is not None,
        )

    return PolicyDecision(
        allowed=False,
        decision="DENY",
        reason="no_matching_role_or_group",
        user_id=user.user_id,
        visibility=visibility,
        source_id=source_acl.source_id,
        tenant_id_checked=source_acl.tenant_id is not None,
    )


def filter_sources_by_acl(
    sources: list[Mapping[str, Any]],
    user_context: UserContext | None,
) -> tuple[list[Mapping[str, Any]], list[PolicyDecision]]:
    """按 ACL 过滤 source/chunk metadata 列表。

    返回 allowed sources 与每条 source 的判定记录。
    """

    allowed_sources: list[Mapping[str, Any]] = []
    decisions: list[PolicyDecision] = []

    for source in sources:
        acl = parse_source_acl(source)
        decision = can_read_source(user_context, acl)

        # ACL 缺失时 can_read_source 只知道“deny”，不知道是哪条 source。
        # filter 层持有原始 metadata，需要把 source_id / chunk_id 补回 decision，
        # 方便 smoke、replay summary 和后续 retrieval_diagnostics 做归因。
        if decision.source_id is None:
            source_id = source.get("source_id") or source.get("chunk_id")
            if source_id is not None:
                decision = replace(decision, source_id=str(source_id))

        decisions.append(decision)
        if decision.allowed:
            allowed_sources.append(source)

    return allowed_sources, decisions


__all__ = [
    "PUBLIC",
    "INTERNAL_DEMO",
    "CONFIDENTIAL",
    "KNOWN_VISIBILITIES",
    "UserContext",
    "SourceACL",
    "PolicyDecision",
    "anonymous_user_context",
    "build_demo_user_context",
    "parse_source_acl",
    "can_read_source",
    "filter_sources_by_acl",
]
