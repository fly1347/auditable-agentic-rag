"""
程序作用：
- 提供 Phase E 的 /health 健康检查与 deployment policy 状态。
- 只检查服务依赖、配置状态、本地索引文件状态，不改动 RAG pipeline、retriever、generator 或 prompt。

整体结构：
1. 本地 vector store 校验：检查 vectors.npy、chunks.jsonl、manifest.json、数量与 embedding 维度。
2. Phase E policy 状态：暴露 security_mode、audit_enabled、offline_env_status、provider_configured。
3. Provider 配置探测：检查 OpenRouter / DeepSeek / local fallback / legacy Ollama 的配置状态。
4. 汇总健康状态：vector store 缺失为 unhealthy；provider 配置缺失为 degraded。
5. 版本信息：返回 Phase E / D-full 冻结配置与 pipeline_config_hash。
"""

from __future__ import annotations

import json
import hashlib
import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import numpy as np
from agentic_rag import __version__
from agentic_rag.config import AppConfig, load_config
from agentic_rag.indexing.current import load_current_index


SERVICE_VERSION = __version__

DEFAULT_VECTOR_STORE_DIR = "artifacts/vector_store"
DEFAULT_INDEX_MANIFEST = "artifacts/index/manifest.json"

DEFAULT_OPENROUTER_ENDPOINT = "https://openrouter.ai/api/v1"
DEFAULT_GENERATOR_MODEL = "openai/gpt-4o-mini"
DEFAULT_CLASSIFIER_MODEL = "openai/gpt-4o-mini"

DEFAULT_DEEPSEEK_ENDPOINT = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-v4-flash"

DEFAULT_LOCAL_FALLBACK_ENDPOINT = "http://127.0.0.1:8080/v1"
DEFAULT_LOCAL_FALLBACK_MODEL = "Qwen3.5-9B-Q4_K_M.gguf"

DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"
DEFAULT_EMBEDDING_DIM = 512

DEFAULT_COST_BUDGET_USD = "0.05"


class HealthService:
    """Phase E 服务健康检查、配置检查与版本信息。"""

    def __init__(
        self,
        settings: Optional[AppConfig] = None,
        vector_store_dir: str = DEFAULT_VECTOR_STORE_DIR,
        index_manifest: str = DEFAULT_INDEX_MANIFEST,
        dependency_timeout_seconds: float = 1.0,
    ) -> None:
        self.settings = settings or load_config()
        self.vector_store_dir = Path(
            self.settings.index.vector_store_dir if settings is not None else vector_store_dir
        )
        self.index_manifest = Path(
            self.settings.index.manifest_path if settings is not None else index_manifest
        )
        self.index_build_id: Optional[str] = None
        current = load_current_index(self.index_manifest.parent / "current.json")
        if current is not None:
            self.vector_store_dir = current.vector_store_dir
            self.index_manifest = current.manifest_path
            self.index_build_id = current.build_id
        self.dependency_timeout_seconds = float(dependency_timeout_seconds)

    def get_health(self) -> Dict[str, Any]:
        """汇总 API、vector store、provider 配置与 Phase E policy 状态。"""
        started = time.perf_counter()

        api_status = {
            "status": "up",
            "required": True,
            "latency_ms": 0.0,
        }
        vector_store_status = self.check_vector_store()
        openrouter_status = self.check_openrouter_config()
        deepseek_status = self.check_deepseek_config()
        local_fallback_status = self.check_local_fallback_config()
        deployment_policy = self.get_deployment_policy_status(
            vector_store_available=vector_store_status["status"] == "up",
            cloud_generator_configured=openrouter_status["status"] == "configured",
            sufficiency_judge_configured=deepseek_status["status"] == "configured",
        )

        components = {
            "api": api_status,
            "vector_store": vector_store_status,
            "default_generator": openrouter_status,
            "sufficiency_judge": deepseek_status,
            "local_fallback": local_fallback_status,
        }

        if vector_store_status["status"] != "up":
            overall = "unhealthy"
        elif not deployment_policy["provider_configured"]:
            overall = "degraded"
        else:
            overall = "healthy"

        return {
            "status": overall,
            "service": "agentic_rag",
            "service_version": SERVICE_VERSION,
            "checked_at": _utc_now_iso(),
            "dependency_check_ms": round((time.perf_counter() - started) * 1000, 3),
            "deployment_policy": deployment_policy,
            "components": components,
        }

    def get_deployment_policy_status(
        self,
        vector_store_available: bool,
        cloud_generator_configured: bool,
        sufficiency_judge_configured: bool,
    ) -> Dict[str, Any]:
        """返回 Phase E deployment / observability policy 状态。"""
        security_mode = os.getenv("AGENTIC_RAG_SECURITY_MODE", "development")
        audit_enabled = _parse_bool(os.getenv("AGENTIC_RAG_AUDIT_LOG_ENABLED"), default=True)
        cost_budget_usd = _safe_float(os.getenv("AGENTIC_RAG_COST_BUDGET_USD", DEFAULT_COST_BUDGET_USD))

        hf_offline = os.getenv("HF_HUB_OFFLINE", "")
        transformers_offline = os.getenv("TRANSFORMERS_OFFLINE", "")
        offline_env_status = {
            "hf_hub_offline": hf_offline,
            "transformers_offline": transformers_offline,
            "enabled": hf_offline == "1" and transformers_offline == "1",
        }

        provider_configured = bool(cloud_generator_configured and sufficiency_judge_configured)

        return {
            "security_mode": security_mode,
            "audit_enabled": audit_enabled,
            "cost_budget_usd": cost_budget_usd,
            "offline_env_status": offline_env_status,
            "provider_configured": provider_configured,
            "cloud_generator_configured": cloud_generator_configured,
            "sufficiency_judge_configured": sufficiency_judge_configured,
            "vector_store_available": vector_store_available,
        }

    def check_vector_store(self) -> Dict[str, Any]:
        """检查 local_npy_jsonl 向量库文件、数量一致性与 embedding 维度。"""
        started = time.perf_counter()
        errors = []

        vectors_path = self.vector_store_dir / "vectors.npy"
        chunks_path = self.vector_store_dir / "chunks.jsonl"
        manifest_path = self.index_manifest

        files = {
            "vectors": _file_status(vectors_path),
            "chunks": _file_status(chunks_path),
            "manifest": _file_status(manifest_path),
        }

        for name, info in files.items():
            if not info["exists"]:
                errors.append(f"{name}_missing")
            elif not info["readable"]:
                errors.append(f"{name}_not_readable")

        vector_count: Optional[int] = None
        embedding_dim: Optional[int] = None
        chunk_count: Optional[int] = None
        manifest: Dict[str, Any] = {}
        manifest_chunk_count: Optional[int] = None
        manifest_doc_count: Optional[int] = None
        manifest_embedding_dim: Optional[int] = None
        manifest_embedding_model: Optional[str] = None

        if vectors_path.exists():
            try:
                vectors = np.load(vectors_path, mmap_mode="r")
                if len(vectors.shape) != 2:
                    errors.append("vectors_not_2d")
                else:
                    vector_count = int(vectors.shape[0])
                    embedding_dim = int(vectors.shape[1])
            except Exception as exc:
                errors.append("vectors_load_failed")
                files["vectors"]["error"] = type(exc).__name__

        if chunks_path.exists():
            try:
                chunk_count = _count_jsonl_lines(chunks_path)
            except Exception as exc:
                errors.append("chunks_read_failed")
                files["chunks"]["error"] = type(exc).__name__

        if manifest_path.exists():
            try:
                manifest = _read_json(manifest_path)
                artifacts = dict(manifest.get("artifacts") or {})
                corpus = dict(manifest.get("corpus") or {})
                embedding = dict(manifest.get("embedding") or {})
                manifest_chunk_count = _safe_int(artifacts.get("chunk_count") or manifest.get("chunk_count"))
                manifest_doc_count = _safe_int(corpus.get("document_count") or manifest.get("doc_count"))
                manifest_embedding_dim = _safe_int(embedding.get("dimension") or manifest.get("embedding_dim"))
                manifest_embedding_model = _safe_str(embedding.get("model") or manifest.get("embedding_model"))
            except Exception as exc:
                errors.append("manifest_read_failed")
                files["manifest"]["error"] = type(exc).__name__

        if vector_count is not None and chunk_count is not None and vector_count != chunk_count:
            errors.append("vector_chunk_count_mismatch")

        if manifest_chunk_count is not None and chunk_count is not None and manifest_chunk_count != chunk_count:
            errors.append("manifest_chunk_count_mismatch")
        if (
            embedding_dim is not None
            and manifest_embedding_dim is not None
            and embedding_dim != manifest_embedding_dim
        ):
            errors.append("embedding_dim_manifest_mismatch")

        status = "up" if not errors else "down"

        return {
            "status": status,
            "required": True,
            "backend": "local_npy_jsonl",
            "build_id": self.index_build_id or manifest.get("build_id"),
            "vector_count": vector_count,
            "chunk_count": chunk_count,
            "doc_count": manifest_doc_count,
            "embedding_model": manifest_embedding_model or DEFAULT_EMBEDDING_MODEL,
            "embedding_dim": embedding_dim or manifest_embedding_dim,
            "manifest_chunk_count": manifest_chunk_count,
            "files": files,
            "errors": errors,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        }

    def check_openrouter_config(self) -> Dict[str, Any]:
        """Check the typed default generator profile without exposing endpoint/key metadata."""
        profile = self.settings.generator.get_profile()
        local = profile.provider_tag in set(self.settings.egress.local_providers)
        api_key = os.getenv(profile.api_key_env, "") if profile.api_key_env else ""
        configured = bool(profile.enabled and (local or api_key))

        return {
            "status": "configured" if configured else "missing_config",
            "required": True,
            "provider": profile.provider_tag,
            "role": "default_cloud_generator",
            "model": profile.model,
            "error": None if configured else f"missing_key_env:{profile.api_key_env}",
        }

    def check_deepseek_config(self) -> Dict[str, Any]:
        """检查 sufficiency judge / evaluator 的 DeepSeek 配置是否存在。"""
        profile = self.settings.generator.get_profile(self.settings.execution.judge_profile)
        local = profile.provider_tag in set(self.settings.egress.local_providers)
        api_key = os.getenv(profile.api_key_env, "") if profile.api_key_env else ""
        configured = bool(profile.enabled and (local or api_key))

        return {
            "status": "configured" if configured else "missing_config",
            "required": True,
            "provider": profile.provider_tag,
            "role": "sufficiency_judge",
            "model": profile.model,
            "mode": self.settings.execution.orchestrated_sufficiency_mode,
            "error": None if configured else f"missing_key_env:{profile.api_key_env}",
        }

    def check_local_fallback_config(self) -> Dict[str, Any]:
        """检查 preferred local fallback 的 endpoint / model 配置。"""
        local_profiles = [
            profile
            for profile in self.settings.generator.profiles.values()
            if profile.enabled and profile.provider_tag in set(self.settings.egress.local_providers)
        ]
        enabled = bool(local_profiles)

        return {
            "status": "configured" if enabled else "disabled",
            "required": False,
            "provider": "local_fallback",
            "role": "preferred_local_fallback",
            "models": [profile.model for profile in local_profiles],
            "enabled": enabled,
            "note": "configured status only; no external probe in /health",
        }

    def get_version(self) -> Dict[str, Any]:
        """返回服务版本、Phase E / D-full 冻结配置与 pipeline_config_hash。"""
        manifest = {}
        if self.index_manifest.exists():
            try:
                manifest = _read_json(self.index_manifest)
            except Exception:
                manifest = {}

        payload = {
            "service_version": SERVICE_VERSION,
            "code_ref": os.getenv("AGENTIC_RAG_CODE_REF", "workspace"),
            "default_execution_profile": self.settings.execution.default_profile,
            "enabled_execution_profiles": list(self.settings.execution.enabled_profiles),
            "generator_backend": self.settings.generator.get_profile().provider_tag,
            "generator_model": self.settings.generator.get_profile().model,
            "classifier_backend": "offline_replay_only",
            "sufficiency_backend": self.settings.generator.get_profile(
                self.settings.execution.judge_profile
            ).provider_tag,
            "sufficiency_model": self.settings.generator.get_profile(
                self.settings.execution.judge_profile
            ).model,
            "sufficiency_mode": self.settings.execution.orchestrated_sufficiency_mode,
            "preferred_local_fallback": {
                "profiles": [
                    profile.name
                    for profile in self.settings.generator.profiles.values()
                    if profile.enabled and profile.provider_tag in set(self.settings.egress.local_providers)
                ],
            },
            "embedding_model": dict(manifest.get("embedding") or {}).get("model", manifest.get("embedding_model", DEFAULT_EMBEDDING_MODEL)),
            "embedding_dim": dict(manifest.get("embedding") or {}).get("dimension", manifest.get("embedding_dim", DEFAULT_EMBEDDING_DIM)),
            "vector_store_backend": "local_npy_jsonl",
            "index_build_id": self.index_build_id or manifest.get("build_id"),
            "doc_count": dict(manifest.get("corpus") or {}).get("document_count", manifest.get("doc_count")),
            "chunk_count": dict(manifest.get("artifacts") or {}).get("chunk_count", manifest.get("chunk_count")),
            "build_time": manifest.get("built_at_utc", manifest.get("build_time")),
            "deployment_policy": {
                "security_mode": os.getenv("AGENTIC_RAG_SECURITY_MODE", "development"),
                "audit_enabled": _parse_bool(os.getenv("AGENTIC_RAG_AUDIT_LOG_ENABLED"), default=True),
                "cost_budget_usd": _safe_float(os.getenv("AGENTIC_RAG_COST_BUDGET_USD", DEFAULT_COST_BUDGET_USD)),
            },
        }
        payload["pipeline_config_hash"] = _hash_payload(payload)
        return payload


def _utc_now_iso() -> str:
    """返回 UTC ISO 时间戳。"""
    return datetime.now(timezone.utc).isoformat()


def _file_status(path: Path) -> Dict[str, Any]:
    """返回文件存在性、可读性、mtime 与 size。"""
    info: Dict[str, Any] = {
        "name": path.name,
        "exists": path.exists(),
        "readable": False,
        "mtime": None,
        "size_bytes": None,
    }
    if not path.exists():
        return info
    try:
        stat = path.stat()
        with path.open("rb") as f:
            f.read(1)
        info["readable"] = True
        info["mtime"] = datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat()
        info["size_bytes"] = int(stat.st_size)
    except Exception as exc:
        info["error"] = type(exc).__name__
    return info


def _count_jsonl_lines(path: Path) -> int:
    """统计 JSONL 有效行数，并顺手验证 JSON 格式。"""
    count = 0
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                json.loads(line)
                count += 1
    return count


def _read_json(path: Path) -> Dict[str, Any]:
    """读取 JSON object 文件。"""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"json root must be object: {path}")
    return data


def _safe_int(value: Any) -> Optional[int]:
    """把值安全转换为 int。"""
    if value is None:
        return None
    try:
        return int(value)
    except Exception:
        return None


def _safe_float(value: Any) -> Optional[float]:
    """把值安全转换为 float。"""
    if value is None:
        return None
    try:
        return float(value)
    except Exception:
        return None


def _safe_str(value: Any) -> Optional[str]:
    """把值安全转换为 str。"""
    if value is None:
        return None
    return str(value)


def _parse_bool(value: Optional[str], default: bool = False) -> bool:
    """解析常见环境变量布尔值。"""
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _hash_payload(payload: Dict[str, Any]) -> str:
    """计算配置 payload 的稳定短 hash。"""
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def _http_get_json(url: str, timeout: float, headers: Optional[Dict[str, str]] = None) -> Tuple[bool, str]:
    """执行轻量 HTTP GET 探测；默认只给可选依赖使用。"""
    request = urllib.request.Request(url, headers=headers or {}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as resp:
            body = resp.read(4096)
            if resp.status >= 400:
                return False, f"http_status_{resp.status}"
            if body:
                try:
                    json.loads(body.decode("utf-8"))
                except Exception:
                    # 可达性检查不强制要求 body 一定是 JSON，避免不同服务版本导致误判。
                    pass
            return True, "ok"
    except urllib.error.HTTPError as exc:
        return False, f"http_status_{exc.code}"
    except urllib.error.URLError as exc:
        return False, f"url_error:{exc.reason}"
    except TimeoutError:
        return False, "timeout"
    except Exception as exc:
        return False, repr(exc)
