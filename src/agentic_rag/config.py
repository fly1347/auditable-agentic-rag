"""严格、类型化的运行时配置。

配置优先级：默认值 < YAML < 调用方显式覆盖。
配置模块启动时自动读取项目根目录 `.env`；已经存在的系统、终端或容器环境变量优先。
密钥值不写入 YAML；provider client 与身份适配器在实际调用时，
按照本配置声明的环境变量名读取密钥。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from dotenv import load_dotenv


def load_project_env() -> bool:
    """读取项目根目录 `.env`，且不覆盖外部已经设置的环境变量。"""
    env_path = Path(__file__).resolve().parents[2] / ".env"
    return bool(load_dotenv(dotenv_path=env_path, override=False))


load_project_env()


try:
    import yaml
except Exception:  # pragma: no cover - reported by load_config
    yaml = None


def _expect_keys(raw: Mapping[str, Any], allowed: set[str], context: str) -> None:
    unknown = sorted(set(raw) - allowed)
    if unknown:
        raise ValueError(f"unknown configuration key(s) in {context}: {', '.join(unknown)}")


def _mapping(value: Any, context: str) -> Dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ValueError(f"{context} must be a mapping/dict")
    return dict(value)


def _deep_merge(base: Dict[str, Any], overlay: Mapping[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    for key, value in overlay.items():
        if isinstance(value, Mapping) and isinstance(merged.get(key), Mapping):
            merged[key] = _deep_merge(dict(merged[key]), value)
        else:
            merged[key] = value
    return merged


@dataclass(frozen=True)
class RerankConfig:
    enabled: bool = False
    model: str = "BAAI/bge-reranker-base"
    candidate_topk: int = 5
    topn: int = 5
    selective_enabled: bool = False
    selective_gap_threshold: float = 0.05
    selective_apply_on_first_round: bool = True
    selective_apply_on_second_round: bool = True


@dataclass(frozen=True)
class ExecutionConfig:
    default_profile: str = "baseline"
    enabled_profiles: tuple[str, ...] = ("baseline", "orchestrated")
    debug_trace_enabled: bool = True
    judge_profile: str = "deepseek_judge"
    orchestrated_sufficiency_mode: str = "structured"


@dataclass(frozen=True)
class AuthConfig:
    mode: str = "static_token"
    required: bool = True
    header_name: str = "X-API-Key"
    principals_env: str = "AGENTIC_RAG_STATIC_PRINCIPALS_JSON"
    public_paths: tuple[str, ...] = ("/health", "/api/version")


@dataclass(frozen=True)
class AdminConfig:
    enabled: bool = False
    allowed_roles: tuple[str, ...] = ("admin",)
    max_upload_bytes: int = 2_000_000


@dataclass(frozen=True)
class EgressConfig:
    public_cloud_allowed: bool = True
    restricted_cloud_allowed: bool = False
    cloud_providers: tuple[str, ...] = ("openrouter", "deepseek")
    local_providers: tuple[str, ...] = ("ollama", "local_llama_cpp", "local")


@dataclass(frozen=True)
class RecordConfig:
    enabled: bool = True
    path: str = "artifacts/executions/records.jsonl"
    schema_version: str = "1.0.0"


@dataclass(frozen=True)
class PromptConfig:
    max_chunks: int = 5
    max_chars_per_chunk: Optional[int] = None
    context_token_budget: int = 4096


@dataclass(frozen=True)
class CitationConfig:
    syntax: str = "evidence_marker"
    missing_policy: str = "record"
    allow_system_fallback: bool = False


@dataclass(frozen=True)
class IndexConfig:
    vector_store_dir: str = "artifacts/vector_store"
    manifest_path: str = "artifacts/index/manifest.json"
    acl_registry_path: str = "policy/source_acl.yaml"


@dataclass(frozen=True)
class GeneratorProfileConfig:
    name: str
    backend: str = "ollama"
    model: str = "qwen2.5:7b"
    base_url: str = "http://localhost:11434"
    api_key_env: str = ""
    provider_tag: str = "ollama"
    network_tag: str = ""
    timeout_s: float = 120.0
    max_retries: int = 0
    max_tokens: int = 512
    temperature: float = 0.0
    top_p: float = 1.0
    enabled: bool = True
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class GeneratorConfigBlock:
    default_profile: str = "openrouter_gpt4o_mini"
    fallback_chain: List[str] = field(default_factory=list)
    profiles: Dict[str, GeneratorProfileConfig] = field(default_factory=dict)

    def get_profile(self, name: Optional[str] = None) -> GeneratorProfileConfig:
        profile_name = str(name or self.default_profile)
        try:
            return self.profiles[profile_name]
        except KeyError as exc:
            raise KeyError(f"generator profile not found: {profile_name}") from exc


@dataclass(frozen=True)
class AppConfig:
    mode: str = "query"
    corpus_root: str = "sample_data/corpus"
    artifacts_dir: str = "artifacts"
    topk: int = 5
    log_dir: str = "logs"
    rerank: RerankConfig = field(default_factory=RerankConfig)
    execution: ExecutionConfig = field(default_factory=ExecutionConfig)
    auth: AuthConfig = field(default_factory=AuthConfig)
    admin: AdminConfig = field(default_factory=AdminConfig)
    egress: EgressConfig = field(default_factory=EgressConfig)
    records: RecordConfig = field(default_factory=RecordConfig)
    prompt: PromptConfig = field(default_factory=PromptConfig)
    citation: CitationConfig = field(default_factory=CitationConfig)
    index: IndexConfig = field(default_factory=IndexConfig)
    generator: GeneratorConfigBlock = field(default_factory=GeneratorConfigBlock)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def fingerprint(self) -> str:
        encoded = json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()


def _default_generator_profiles() -> Dict[str, Dict[str, Any]]:
    """Profiles required by the public default runtime.

    Local/Ollama-compatible clients remain supported by the implementation,
    but local profiles must be configured explicitly instead of being silently
    registered as runtime defaults.
    """
    return {
        "openrouter_gpt4o_mini": {
            "name": "openrouter_gpt4o_mini", "backend": "openai_compatible",
            "model": "openai/gpt-4o-mini", "base_url": "https://openrouter.ai/api/v1",
            "api_key_env": "OPENROUTER_API_KEY", "provider_tag": "openrouter",
            "timeout_s": 120.0, "max_retries": 2,
        },
        "deepseek_judge": {
            "name": "deepseek_judge", "backend": "openai_compatible",
            "model": "deepseek-v4-flash", "base_url": "https://api.deepseek.com",
            "api_key_env": "DEEPSEEK_API_KEY", "provider_tag": "deepseek",
            "timeout_s": 120.0, "max_retries": 0, "max_tokens": 512,
        },
    }


def _defaults() -> Dict[str, Any]:
    return {
        "mode": "query", "corpus_root": "sample_data/corpus", "artifacts_dir": "artifacts",
        "topk": 5, "log_dir": "logs", "rerank": asdict(RerankConfig()),
        "execution": {
            "default_profile": "baseline",
            "enabled_profiles": ["baseline", "orchestrated"],
            "debug_trace_enabled": True,
            "judge_profile": "deepseek_judge",
            "orchestrated_sufficiency_mode": "structured",
        },
        "auth": {"mode": "static_token", "required": True, "header_name": "X-API-Key", "principals_env": "AGENTIC_RAG_STATIC_PRINCIPALS_JSON", "public_paths": ["/health", "/api/version"]},
        "admin": asdict(AdminConfig()), "egress": asdict(EgressConfig()),
        "records": asdict(RecordConfig()), "prompt": asdict(PromptConfig()),
        "citation": asdict(CitationConfig()), "index": asdict(IndexConfig()),
        "generator": {
            "default_profile": "openrouter_gpt4o_mini",
            "fallback_chain": [],
            "profiles": _default_generator_profiles(),
        },
    }


def _build_generator_profile(name: str, raw: Mapping[str, Any]) -> GeneratorProfileConfig:
    allowed = {"name", "backend", "model", "base_url", "api_key_env", "provider_tag", "network_tag", "timeout_s", "max_retries", "max_tokens", "temperature", "top_p", "enabled", "extra"}
    _expect_keys(raw, allowed, f"generator.profiles.{name}")
    return GeneratorProfileConfig(
        name=str(raw.get("name", name)), backend=str(raw.get("backend", "ollama")),
        model=str(raw.get("model", "qwen2.5:7b")), base_url=str(raw.get("base_url", "http://localhost:11434")),
        api_key_env=str(raw.get("api_key_env", "")), provider_tag=str(raw.get("provider_tag", raw.get("backend", "ollama"))),
        network_tag=str(raw.get("network_tag", "")), timeout_s=float(raw.get("timeout_s", 120.0)),
        max_retries=int(raw.get("max_retries", 0)), max_tokens=int(raw.get("max_tokens", 512)),
        temperature=float(raw.get("temperature", 0.0)), top_p=float(raw.get("top_p", 1.0)),
        enabled=bool(raw.get("enabled", True)), extra=_mapping(raw.get("extra"), f"generator.profiles.{name}.extra"),
    )


def _build_generator(raw: Mapping[str, Any]) -> GeneratorConfigBlock:
    _expect_keys(raw, {"default_profile", "fallback_chain", "profiles"}, "generator")
    profiles_raw = _mapping(raw.get("profiles"), "generator.profiles")
    profiles = {str(name): _build_generator_profile(str(name), _mapping(value, f"generator.profiles.{name}")) for name, value in profiles_raw.items()}
    default_profile = str(raw.get("default_profile", "openrouter_gpt4o_mini"))
    fallback_chain = [str(item) for item in list(raw.get("fallback_chain", []) or [])]
    missing = sorted({name for name in [default_profile, *fallback_chain] if name not in profiles})
    if missing:
        raise ValueError(f"generator references undefined profile(s): {', '.join(missing)}")
    return GeneratorConfigBlock(default_profile=default_profile, fallback_chain=fallback_chain, profiles=profiles)


def _build_config(data: Mapping[str, Any]) -> AppConfig:
    _expect_keys(data, {"mode", "corpus_root", "artifacts_dir", "topk", "log_dir", "rerank", "execution", "auth", "admin", "egress", "records", "prompt", "citation", "index", "generator"}, "root")
    rerank = _mapping(data.get("rerank"), "rerank"); _expect_keys(rerank, set(asdict(RerankConfig())), "rerank")
    execution = _mapping(data.get("execution"), "execution"); _expect_keys(
        execution,
        {
            "default_profile", "enabled_profiles", "debug_trace_enabled",
            "judge_profile", "orchestrated_sufficiency_mode",
        },
        "execution",
    )
    auth = _mapping(data.get("auth"), "auth"); _expect_keys(auth, {"mode", "required", "header_name", "principals_env", "public_paths"}, "auth")
    admin = _mapping(data.get("admin"), "admin"); _expect_keys(admin, {"enabled", "allowed_roles", "max_upload_bytes"}, "admin")
    egress = _mapping(data.get("egress"), "egress"); _expect_keys(egress, {"public_cloud_allowed", "restricted_cloud_allowed", "cloud_providers", "local_providers"}, "egress")
    records = _mapping(data.get("records"), "records"); _expect_keys(records, {"enabled", "path", "schema_version"}, "records")
    prompt = _mapping(data.get("prompt"), "prompt"); _expect_keys(prompt, {"max_chunks", "max_chars_per_chunk", "context_token_budget"}, "prompt")
    citation = _mapping(data.get("citation"), "citation"); _expect_keys(citation, {"syntax", "missing_policy", "allow_system_fallback"}, "citation")
    index = _mapping(data.get("index"), "index"); _expect_keys(index, {"vector_store_dir", "manifest_path", "acl_registry_path"}, "index")

    enabled_profiles = tuple(str(item) for item in execution.get("enabled_profiles", ["baseline", "orchestrated"]))
    default_profile = str(execution.get("default_profile", "baseline"))
    if default_profile not in {"baseline", "orchestrated"} or not set(enabled_profiles).issubset({"baseline", "orchestrated"}):
        raise ValueError("execution profiles must be baseline and/or orchestrated")
    if default_profile not in enabled_profiles:
        raise ValueError("execution.default_profile must be present in enabled_profiles")
    sufficiency_mode = str(execution.get("orchestrated_sufficiency_mode", "structured"))
    if sufficiency_mode not in {"binary", "structured"}:
        raise ValueError("execution.orchestrated_sufficiency_mode must be binary or structured")
    missing_policy = str(citation.get("missing_policy", "record"))
    if missing_policy not in {"record", "refuse"}:
        raise ValueError("citation.missing_policy must be record or refuse")
    max_chars_raw = prompt.get("max_chars_per_chunk")
    max_chars = None if max_chars_raw in {None, 0, ""} else int(max_chars_raw)

    generator_block = _build_generator(_mapping(data.get("generator"), "generator"))
    judge_profile = str(execution.get("judge_profile", "deepseek_judge"))
    if judge_profile not in generator_block.profiles:
        raise ValueError(f"execution.judge_profile references undefined profile: {judge_profile}")

    return AppConfig(
        mode=str(data.get("mode", "query")), corpus_root=str(data.get("corpus_root", "data/corpus/phase_a")),
        artifacts_dir=str(data.get("artifacts_dir", "artifacts")), topk=int(data.get("topk", 5)), log_dir=str(data.get("log_dir", "logs")),
        rerank=RerankConfig(**rerank),
        execution=ExecutionConfig(
            default_profile=default_profile,
            enabled_profiles=enabled_profiles,
            debug_trace_enabled=bool(execution.get("debug_trace_enabled", True)),
            judge_profile=judge_profile,
            orchestrated_sufficiency_mode=sufficiency_mode,
        ),
        auth=AuthConfig(mode=str(auth.get("mode", "static_token")), required=bool(auth.get("required", True)), header_name=str(auth.get("header_name", "X-API-Key")), principals_env=str(auth.get("principals_env", "AGENTIC_RAG_STATIC_PRINCIPALS_JSON")), public_paths=tuple(str(item) for item in auth.get("public_paths", []))),
        admin=AdminConfig(enabled=bool(admin.get("enabled", False)), allowed_roles=tuple(str(item) for item in admin.get("allowed_roles", ["admin"])), max_upload_bytes=int(admin.get("max_upload_bytes", 2_000_000))),
        egress=EgressConfig(public_cloud_allowed=bool(egress.get("public_cloud_allowed", True)), restricted_cloud_allowed=bool(egress.get("restricted_cloud_allowed", False)), cloud_providers=tuple(str(item) for item in egress.get("cloud_providers", [])), local_providers=tuple(str(item) for item in egress.get("local_providers", []))),
        records=RecordConfig(enabled=bool(records.get("enabled", True)), path=str(records.get("path", "artifacts/executions/records.jsonl")), schema_version=str(records.get("schema_version", "1.0.0"))),
        prompt=PromptConfig(max_chunks=int(prompt.get("max_chunks", 5)), max_chars_per_chunk=max_chars, context_token_budget=int(prompt.get("context_token_budget", 4096))),
        citation=CitationConfig(syntax=str(citation.get("syntax", "evidence_marker")), missing_policy=missing_policy, allow_system_fallback=bool(citation.get("allow_system_fallback", False))),
        index=IndexConfig(vector_store_dir=str(index.get("vector_store_dir", "artifacts/vector_store")), manifest_path=str(index.get("manifest_path", "artifacts/index/manifest.json")), acl_registry_path=str(index.get("acl_registry_path", "policy/source_acl.yaml"))),
        generator=generator_block,
    )


def load_config(config_path: Optional[str] = None, cli_overrides: Optional[Dict[str, Any]] = None) -> AppConfig:
    data = _defaults()
    if config_path is not None:
        if yaml is None:
            raise RuntimeError("Missing dependency: pyyaml is required to load YAML configuration")
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"config file not found: {config_path}")
        parsed = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(parsed, Mapping):
            raise ValueError("configuration must be a mapping/dict at top level")
        data = _deep_merge(data, parsed)
    if cli_overrides:
        data = _deep_merge(data, cli_overrides)
    return _build_config(data)


__all__ = ["AdminConfig", "AppConfig", "AuthConfig", "CitationConfig", "EgressConfig", "ExecutionConfig", "GeneratorConfigBlock", "GeneratorProfileConfig", "IndexConfig", "PromptConfig", "RecordConfig", "RerankConfig", "load_config", "load_project_env"]
