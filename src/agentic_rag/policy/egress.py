"""Provider data-egress decisions evaluated before every provider attempt.

The application service opens one request-scoped policy context.  Low-level
provider clients still perform the check themselves immediately before each
network attempt, so retries and future fallback providers cannot bypass policy.
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Callable, Iterable, Iterator, Optional, Sequence

from agentic_rag.config import EgressConfig


RESTRICTED_VISIBILITIES = {"internal_demo", "internal", "confidential", "private"}


class EgressDenied(RuntimeError):
    """Raised before a provider request when data-egress policy denies it."""


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
    """Extract source visibility from chunk metadata without reading chunk text."""
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
    """Install request-scoped policy inputs for all nested provider clients."""
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
    """Authorize and record one concrete provider attempt, then fail closed."""
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
