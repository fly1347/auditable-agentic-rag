"""
作用：
- 定义 Phase D-full 的请求级观测结构。
- 聚合一次请求中的模型调用、token、耗时、错误、成本与扩展字段。
- 供 WorkflowState、/api/chat/debug、replay、per-question report 共用。

整体结构：
1. ModelCallRecord：一次 LLM 调用记录。
2. ObservabilityRecord：一次请求的整体观测记录。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from agentic_rag.observability.model_identity import ModelIdentity


@dataclass
class ModelCallRecord:
    """作用：记录一次 LLM 调用的耗时、token、错误与模型身份。"""

    role: str
    identity: ModelIdentity = field(default_factory=ModelIdentity)
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    reasoning_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    latency_ms: Optional[float] = None
    estimated_cost_usd: Optional[float] = None
    timeout: bool = False
    api_error: bool = False
    http_status: Optional[int] = None
    error_type: Optional[str] = None

    @classmethod
    def from_token_usage(
        cls,
        *,
        role: str,
        token_usage: Dict[str, Any],
        latency_ms: Optional[float] = None,
        error_type: Optional[str] = None,
        api_error: bool = False,
        timeout: bool = False,
        http_status: Optional[int] = None,
    ) -> "ModelCallRecord":
        """
        作用：
        - 从 generator token_usage / client metadata 构造一次模型调用记录。
        - 兼容 prompt_eval_count / eval_count 与 OpenAI-style token 字段。
        """
        usage: Dict[str, Any] = dict(token_usage or {})

        prompt_tokens = usage.get("prompt_tokens", usage.get("prompt_eval_count"))
        completion_tokens = usage.get("completion_tokens", usage.get("eval_count"))
        total_tokens = usage.get("total_tokens", usage.get("total_count"))

        completion_details = usage.get("completion_tokens_details") or {}
        if not isinstance(completion_details, dict):
            completion_details = {}

        reasoning_tokens = usage.get("reasoning_tokens", completion_details.get("reasoning_tokens"))

        return cls(
            role=str(role),
            identity=ModelIdentity.from_metadata(usage),
            prompt_tokens=int(prompt_tokens) if prompt_tokens is not None else None,
            completion_tokens=int(completion_tokens) if completion_tokens is not None else None,
            reasoning_tokens=int(reasoning_tokens) if reasoning_tokens is not None else None,
            total_tokens=int(total_tokens) if total_tokens is not None else None,
            latency_ms=float(latency_ms) if latency_ms is not None else None,
            estimated_cost_usd=None,
            timeout=bool(timeout),
            api_error=bool(api_error),
            http_status=int(http_status) if http_status is not None else None,
            error_type=str(error_type) if error_type is not None else None,
        )

    def to_dict(self) -> Dict[str, Any]:
        """作用：输出稳定 JSON 结构。"""
        return {
            "role": self.role,
            "identity": self.identity.to_dict(),
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "total_tokens": self.total_tokens,
            "latency_ms": self.latency_ms,
            "estimated_cost_usd": self.estimated_cost_usd,
            "timeout": self.timeout,
            "api_error": self.api_error,
            "http_status": self.http_status,
            "error_type": self.error_type,
        }


@dataclass
class ObservabilityRecord:
    """作用：聚合一次请求中的模型、网络、成本与耗时观测字段。"""

    request_id: str
    run_id: Optional[str] = None
    qid: Optional[str] = None
    timestamp_utc: Optional[str] = None
    model_calls: List[ModelCallRecord] = field(default_factory=list)
    latency_ms: Optional[float] = None
    estimated_cost_usd: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)

    def add_model_call(self, call: ModelCallRecord) -> None:
        """作用：追加一次模型调用记录。"""
        self.model_calls.append(call)

    def to_dict(self) -> Dict[str, Any]:
        """作用：输出稳定 JSON 结构。"""
        return {
            "request_id": self.request_id,
            "run_id": self.run_id,
            "qid": self.qid,
            "timestamp_utc": self.timestamp_utc,
            "model_calls": [call.to_dict() for call in self.model_calls],
            "latency_ms": self.latency_ms,
            "estimated_cost_usd": self.estimated_cost_usd,
            "extra": dict(self.extra or {}),
        }
