"""
作用：
- 定义 Phase D-full 的模型身份记录结构。
- 为 generator / classifier / sufficiency judge / RAGAS evaluator 提供统一 ModelIdentity。
- 只记录可观测元信息，不记录 API key 明文。

整体结构：
1. ModelIdentity：一次模型调用对应的模型、provider、endpoint、网络与密钥 hash。
2. from_metadata：从 client.metadata() / token_usage / C+ candidate_meta 中构造 ModelIdentity。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class ModelIdentity:
    """作用：记录一次模型调用对应的模型身份与网络路径。"""

    provider: Optional[str] = None
    configured_model: Optional[str] = None
    provider_response_model: Optional[str] = None
    resolved_model: Optional[str] = None
    endpoint: Optional[str] = None
    upstream_provider: Optional[str] = None
    api_key_hash: Optional[str] = None
    network_tag: Optional[str] = None
    proxy_node: Optional[str] = None

    @classmethod
    def from_metadata(cls, metadata: Dict[str, Any]) -> "ModelIdentity":
        """
        作用：
        - 从已有 metadata / token_usage 构造 ModelIdentity。
        - 兼容旧字段 provider_tag / generator_backend。
        - 拿不到的字段显式保留为 None。
        """
        data: Dict[str, Any] = dict(metadata or {})

        provider = (
            data.get("provider")
            or data.get("provider_tag")
            or data.get("generator_provider")
            or data.get("backend")
            or data.get("generator_backend")
        )

        configured_model = (
            data.get("configured_model")
            or data.get("model")
            or data.get("generator_model")
        )

        provider_response_model = data.get("provider_response_model")
        resolved_model = data.get("resolved_model") or provider_response_model or configured_model

        return cls(
            provider=str(provider) if provider is not None else None,
            configured_model=str(configured_model) if configured_model is not None else None,
            provider_response_model=(
                str(provider_response_model) if provider_response_model is not None else None
            ),
            resolved_model=str(resolved_model) if resolved_model is not None else None,
            endpoint=str(data.get("endpoint")) if data.get("endpoint") is not None else None,
            upstream_provider=(
                str(data.get("upstream_provider")) if data.get("upstream_provider") is not None else None
            ),
            api_key_hash=(
                str(data.get("api_key_hash")) if data.get("api_key_hash") is not None else None
            ),
            network_tag=(
                str(data.get("network_tag")) if data.get("network_tag") is not None else None
            ),
            proxy_node=(
                str(data.get("proxy_node")) if data.get("proxy_node") is not None else None
            ),
        )

    def to_dict(self) -> Dict[str, Any]:
        """作用：输出稳定 JSON 结构，字段缺失时保留 None。"""
        return {
            "provider": self.provider,
            "configured_model": self.configured_model,
            "provider_response_model": self.provider_response_model,
            "resolved_model": self.resolved_model,
            "endpoint": self.endpoint,
            "upstream_provider": self.upstream_provider,
            "api_key_hash": self.api_key_hash,
            "network_tag": self.network_tag,
            "proxy_node": self.proxy_node,
        }
