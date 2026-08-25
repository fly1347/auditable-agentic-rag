"""
文件作用：
提供项目统一 LLM generator client。

整体结构：
1）LLMConfig：从环境变量读取 generator 配置；
2）OllamaClient：保留旧类名以兼容既有调用，但内部支持 ollama 与 openai_compatible 两种 backend；
3）generate()：统一返回 (text, token_usage, generate_ms)，供 RAGGenerator、rewrite、decompose 共用；
4）metadata / token_usage：输出 D-full 标准 ModelIdentity 字段，并兼容 C+ 旧字段。

环境变量约定：
- GENERATOR_BACKEND=ollama|openai_compatible
- GENERATOR_MODEL=...
- GENERATOR_API_BASE_URL=...
- GENERATOR_API_KEY_ENV=...
- GENERATOR_PROVIDER_TAG=...
- OLLAMA_HOST=...（ollama backend 使用）
- NETWORK_TAG=...（可选，记录网络标签）
- PROXY_NODE=...（可选，记录代理节点）
"""

from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import requests

from agentic_rag.policy.egress import EgressDenied, authorize_provider_attempt


def _env(name: str, default: str = "") -> str:
    """读取环境变量并去掉首尾空白。"""
    return str(os.getenv(name, default) or "").strip()


def _hash_key(value: str) -> Optional[str]:
    """只记录 API key hash 前缀，避免明文落盘。"""
    if value.strip() == "":
        return None
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _env_int(name: str, default: int) -> int:
    """读取 int 环境变量；非法时回退默认值。"""
    raw = _env(name, "")
    if raw == "":
        return int(default)
    try:
        return int(raw)
    except ValueError:
        return int(default)


def _env_float(name: str, default: float) -> float:
    """读取 float 环境变量；非法时回退默认值。"""
    raw = _env(name, "")
    if raw == "":
        return float(default)
    try:
        return float(raw)
    except ValueError:
        return float(default)


@dataclass(frozen=True)
class LLMConfig:
    """统一 generator 配置；默认保持本地 Ollama 行为。"""

    backend: str = _env("GENERATOR_BACKEND", "ollama")
    model: str = _env("GENERATOR_MODEL", _env("OLLAMA_MODEL", "qwen2.5:7b"))
    base_url: str = _env("GENERATOR_API_BASE_URL", _env("OLLAMA_HOST", "http://localhost:11434"))
    api_key_env: str = _env("GENERATOR_API_KEY_ENV", "")
    provider_tag: str = _env("GENERATOR_PROVIDER_TAG", "ollama")
    temperature: float = _env_float("GENERATOR_TEMPERATURE", 0.0)
    top_p: float = _env_float("GENERATOR_TOP_P", 1.0)
    num_predict: int = _env_int("GENERATOR_MAX_TOKENS", _env_int("GENERATOR_NUM_PREDICT", 512))
    seed: Optional[int] = None
    timeout_s: float = _env_float("GENERATOR_TIMEOUT_S", 120.0)
    max_retries: int = _env_int("GENERATOR_MAX_RETRIES", 2)


class OllamaClient:
    """
    兼容旧调用名的统一 generator client。

    注意：类名仍叫 OllamaClient，是为了不大改 RAGGenerator / query_pipeline 调用链。
    实际 backend 由 GENERATOR_BACKEND 控制。
    """

    def __init__(
        self,
        cfg: Optional[LLMConfig] = None,
        *,
        stage: str = "generator",
        data_visibilities: Optional[Tuple[str, ...]] = None,
    ) -> None:
        self._cfg: LLMConfig = cfg or LLMConfig()
        self._stage = str(stage)
        self._data_visibilities = tuple(data_visibilities or ())

    @property
    def config(self) -> LLMConfig:
        """暴露只读配置，供 bench / debug 记录 metadata。"""
        return self._cfg

    def _base_metadata(self) -> Dict[str, Any]:
        """
        返回标准化模型身份 metadata；不包含 API key 明文。

        D-full 标准字段：
        - provider / backend / configured_model
        - provider_response_model / resolved_model / upstream_provider
        - endpoint / api_key_env / api_key_hash
        - network_tag / proxy_node

        同时保留 C+ 旧字段：
        - generator_backend
        - provider_tag
        """
        api_key_hash: Optional[str] = None
        if self._cfg.api_key_env:
            api_key_hash = _hash_key(_env(self._cfg.api_key_env, ""))

        provider = str(self._cfg.provider_tag or self._cfg.backend)

        return {
            # D-full 标准字段。
            "provider": provider,
            "backend": str(self._cfg.backend),
            "configured_model": str(self._cfg.model),
            "provider_response_model": None,
            "resolved_model": str(self._cfg.model),
            "endpoint": str(self._cfg.base_url),
            "upstream_provider": None,
            "api_key_env": str(self._cfg.api_key_env),
            "api_key_hash": api_key_hash,
            "network_tag": _env("NETWORK_TAG", ""),
            "proxy_node": _env("PROXY_NODE", ""),

            # 兼容 C+ / 旧字段。
            "generator_backend": str(self._cfg.backend),
            "provider_tag": provider,
        }

    def metadata(self) -> Dict[str, Any]:
        """返回不含密钥明文的 generator metadata。"""
        return self._base_metadata()

    def generate(self, prompt: str) -> Tuple[str, Dict[str, Any], int]:
        """按 backend 生成文本，统一返回 (text, token_usage, generate_ms)。"""
        backend = str(self._cfg.backend).strip().lower()
        if backend == "ollama":
            return self._generate_ollama(prompt=prompt)
        if backend in {"openai_compatible", "openai-compatible", "openai"}:
            return self._generate_openai_compatible(prompt=prompt)
        raise ValueError(f"Unsupported GENERATOR_BACKEND: {self._cfg.backend}")

    def _generate_ollama(self, prompt: str) -> Tuple[str, Dict[str, Any], int]:
        """调用 Ollama /api/generate。"""
        t0: float = time.time()
        payload: Dict[str, Any] = {
            "model": self._cfg.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self._cfg.temperature,
                "top_p": self._cfg.top_p,
                "num_predict": self._cfg.num_predict,
            },
        }
        if self._cfg.seed is not None:
            payload["options"]["seed"] = int(self._cfg.seed)

        last_err: Optional[BaseException] = None
        for attempt in range(self._cfg.max_retries + 1):
            try:
                authorize_provider_attempt(
                    self._cfg.provider_tag,
                    stage=self._stage,
                    attempt=attempt + 1,
                    visibilities=self._data_visibilities,
                )
                url = self._cfg.base_url.rstrip("/") + "/api/generate"
                resp = requests.post(url, json=payload, timeout=self._cfg.timeout_s)
                try:
                    resp.raise_for_status()
                except requests.HTTPError as exc:
                    body = resp.text[:2000] if resp is not None else ""
                    raise RuntimeError(f"HTTP {resp.status_code} from Ollama endpoint: {body}") from exc

                data: Dict[str, Any] = resp.json()
                text = str(data.get("response", ""))

                provider_model = data.get("model")
                usage: Dict[str, Any] = self._base_metadata()
                usage.update(
                    {
                        "prompt_eval_count": data.get("prompt_eval_count"),
                        "eval_count": data.get("eval_count"),
                        "total_count": None,
                        "generator_backend": "ollama",
                        "backend": "ollama",
                        "provider_response_model": provider_model,
                        "resolved_model": provider_model or self._cfg.model,
                        "provider_tag": self._cfg.provider_tag,
                        "provider": self._cfg.provider_tag,
                    }
                )

                ms = int((time.time() - t0) * 1000)
                return text, usage, ms
            except Exception as e:  # noqa: BLE001
                last_err = e
                if isinstance(e, EgressDenied):
                    break
                if attempt >= self._cfg.max_retries:
                    break
                time.sleep(0.3 * (attempt + 1))

        raise RuntimeError(f"Ollama generate failed after retries: {last_err!r}")

    def _generate_openai_compatible(self, prompt: str) -> Tuple[str, Dict[str, Any], int]:
        """调用 OpenAI-compatible /chat/completions。"""
        t0: float = time.time()
        api_key_env = str(self._cfg.api_key_env or "").strip()
        if api_key_env == "":
            raise ValueError("GENERATOR_API_KEY_ENV is required for openai_compatible backend")
        api_key = _env(api_key_env, "")
        if api_key == "":
            raise ValueError(f"缺少环境变量：{api_key_env}")

        payload: Dict[str, Any] = {
            "model": self._cfg.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self._cfg.temperature,
            "top_p": self._cfg.top_p,
            "max_tokens": int(self._cfg.num_predict),
            "stream": False,
        }
        # 这里保持原生 OpenAI-compatible JSON，不额外塞 LangChain 的 extra_body。
        # 若某个 provider 需要 thinking 开关，后续单独通过 provider-specific 字段补，不污染通用路径。

        headers: Dict[str, str] = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        if str(self._cfg.provider_tag).lower() == "openrouter":
            site_url = _env("OPENROUTER_SITE_URL", "")
            app_name = _env("OPENROUTER_APP_NAME", "agentic_rag")
            if site_url:
                headers["HTTP-Referer"] = site_url
            if app_name:
                headers["X-Title"] = app_name

        last_err: Optional[BaseException] = None
        for attempt in range(self._cfg.max_retries + 1):
            try:
                authorize_provider_attempt(
                    self._cfg.provider_tag,
                    stage=self._stage,
                    attempt=attempt + 1,
                    visibilities=self._data_visibilities,
                )
                url = self._cfg.base_url.rstrip("/") + "/chat/completions"
                resp = requests.post(url, json=payload, headers=headers, timeout=self._cfg.timeout_s)
                try:
                    resp.raise_for_status()
                except requests.HTTPError as exc:
                    body = resp.text[:2000] if resp is not None else ""
                    raise RuntimeError(
                        f"HTTP {resp.status_code} from OpenAI-compatible endpoint: {body}"
                    ) from exc

                data: Dict[str, Any] = resp.json()
                choices = list(data.get("choices", []) or [])
                first_choice = dict(choices[0] or {}) if choices else {}
                message = dict(first_choice.get("message", {}) or {}) if first_choice else {}

                content_value = message.get("content", "")
                if isinstance(content_value, list):
                    content_parts = []
                    for item in content_value:
                        if isinstance(item, dict):
                            content_parts.append(str(item.get("text") or item.get("content") or ""))
                        else:
                            content_parts.append(str(item))
                    text = "\n".join(part for part in content_parts if part.strip())
                else:
                    text = str(content_value or "")

                message_keys = sorted([str(k) for k in message.keys()])
                message_field_lengths = {
                    str(k): len(str(v))
                    for k, v in message.items()
                    if str(k) != "content"
                }
                finish_reason = first_choice.get("finish_reason")
                native_finish_reason = first_choice.get("native_finish_reason")

                usage_raw = dict(data.get("usage", {}) or {})
                provider_model = data.get("model") or self._cfg.model

                usage: Dict[str, Any] = self._base_metadata()
                usage.update(
                    {
                        "prompt_eval_count": usage_raw.get("prompt_tokens"),
                        "eval_count": usage_raw.get("completion_tokens"),
                        "total_count": usage_raw.get("total_tokens"),
                        "prompt_tokens": usage_raw.get("prompt_tokens"),
                        "completion_tokens": usage_raw.get("completion_tokens"),
                        "total_tokens": usage_raw.get("total_tokens"),
                        "generator_backend": "openai_compatible",
                        "backend": "openai_compatible",
                        "configured_model": self._cfg.model,
                        "provider_response_model": provider_model,
                        "resolved_model": provider_model,
                        "provider_tag": self._cfg.provider_tag,
                        "provider": self._cfg.provider_tag,
                        "upstream_provider": data.get("provider") or data.get("upstream_provider"),
                        "system_fingerprint": data.get("system_fingerprint"),
                        "finish_reason": finish_reason,
                        "native_finish_reason": native_finish_reason,
                        "message_keys": message_keys,
                        "message_field_lengths": message_field_lengths,
                        "content_was_empty": not bool(text.strip()),
                        "prompt_tokens_details": usage_raw.get("prompt_tokens_details"),
                        "completion_tokens_details": usage_raw.get("completion_tokens_details"),
                    }
                )

                ms = int((time.time() - t0) * 1000)
                return text, usage, ms
            except Exception as e:  # noqa: BLE001
                last_err = e
                if isinstance(e, EgressDenied):
                    break
                if attempt >= self._cfg.max_retries:
                    break
                time.sleep(0.5 * (attempt + 1))

        raise RuntimeError(f"OpenAI-compatible generate failed after retries: {last_err!r}")
