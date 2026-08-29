"""
程序作用：
在每次模型服务请求前执行数据出站判断，确保重试或未来新增 provider 也不能绕过权限策略。

整体结构：
1）EgressDecision 与 EgressRuntimeContext 描述出站结果和请求级策略上下文；
2）assess_provider_egress 根据数据敏感度、身份能力和目标 provider 判断是否允许；
3）egress_scope 安装请求级上下文，authorize_provider_attempt 在真正联网前再次检查并记录。
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Callable, Iterable, Iterator, Optional, Sequence

from agentic_rag.config import EgressConfig


RESTRICTED_VISIBILITIES = {"internal_demo", "internal", "confidential", "private"}


class EgressDenied(RuntimeError):
    """数据出站策略拒绝请求时，在联网前抛出的异常。"""


@dataclass(frozen=True)
class EgressDecision:
    allowed: bool
    reason: str
    provider: str
    sensitivity: str

    def to_dict(self) -> dict[str, object]:
        return {
            "allowed": self.allowed,
            "reason": self.reason,
            "provider": self.provider,
            "sensitivity": self.sensitivity,
        }


@dataclass(frozen=True)
class EgressRuntimeContext:
    config: EgressConfig
    default_visibilities: tuple[str, ...]
    recorder: Optional[Callable[[dict[str, object]], None]] = None


_RUNTIME_CONTEXT: ContextVar[Optional[EgressRuntimeContext]] = ContextVar(
    "agentic_rag_egress_context",
    default=None,
)


def classify_sensitivity(visibilities: Iterable[str]) -> str:
    values = {str(item).strip().lower() for item in visibilities if str(item).strip()}
    if values & RESTRICTED_VISIBILITIES:
        return "restricted"
    if values and values <= {"public"}:
        return "public"
    if not values:
        return "unknown"
    return "restricted"


def assess_provider_egress(
    provider: str,
    visibilities: Iterable[str],
    config: EgressConfig,
) -> EgressDecision:
    normalized = str(provider).strip().lower()
    sensitivity = classify_sensitivity(visibilities)
    if normalized in set(config.local_providers):
        return EgressDecision(True, "local_provider", normalized, sensitivity)
    if normalized not in set(config.cloud_providers):
        return EgressDecision(False, "provider_not_allowlisted", normalized, sensitivity)
    if sensitivity == "public" and config.public_cloud_allowed:
        return EgressDecision(True, "public_cloud_allowed", normalized, sensitivity)
    if sensitivity == "restricted" and config.restricted_cloud_allowed:
        return EgressDecision(True, "restricted_cloud_explicitly_allowed", normalized, sensitivity)
    return EgressDecision(False, f"{sensitivity}_cloud_denied", normalized, sensitivity)


def chunk_visibilities(chunks: Iterable[object]) -> tuple[str, ...]:
    """只读取 chunk 元数据中的来源可见级别，不接触正文。"""
    values: list[str] = []
    for chunk in chunks:
        metadata = dict(getattr(chunk, "metadata", {}) or {})
        acl = dict(metadata.get("acl", {}) or {})
        visibility = acl.get("visibility", metadata.get("visibility"))
        if visibility not in (None, ""):
            values.append(str(visibility))
    return tuple(values)


@contextmanager
def egress_scope(
    config: EgressConfig,
    *,
    default_visibilities: Sequence[str],
    recorder: Optional[Callable[[dict[str, object]], None]] = None,
) -> Iterator[None]:
    """为当前请求下的所有模型客户端安装统一出站策略输入。"""
    token = _RUNTIME_CONTEXT.set(
        EgressRuntimeContext(
            config=config,
            default_visibilities=tuple(str(item) for item in default_visibilities),
            recorder=recorder,
        )
    )
    try:
        yield
    finally:
        _RUNTIME_CONTEXT.reset(token)


def authorize_provider_attempt(
    provider: str,
    *,
    stage: str,
    attempt: int,
    visibilities: Optional[Iterable[str]] = None,
) -> EgressDecision:
    """检查并记录一次实际模型服务调用；无法确认时按拒绝处理。"""
    context = _RUNTIME_CONTEXT.get()
    config = context.config if context is not None else EgressConfig()
    selected = tuple(visibilities or ())
    if not selected and context is not None:
        selected = context.default_visibilities

    decision = assess_provider_egress(provider, selected, config)
    event = {
        **decision.to_dict(),
        "stage": str(stage),
        "attempt": int(attempt),
    }
    if context is not None and context.recorder is not None:
        context.recorder(event)
    if not decision.allowed:
        raise EgressDenied(
            f"provider egress denied at {stage} attempt={attempt}: "
            f"provider={decision.provider} sensitivity={decision.sensitivity} "
            f"reason={decision.reason}"
        )
    return decision


__all__ = [
    "EgressDecision",
    "EgressDenied",
    "assess_provider_egress",
    "authorize_provider_attempt",
    "chunk_visibilities",
    "classify_sensitivity",
    "egress_scope",
]
