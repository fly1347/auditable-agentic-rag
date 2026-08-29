"""
文件作用：
1）实现 D-lite 的 Evidence Sufficiency Check（证据充分性判断）。
2）输入 query + retrieved_chunks，输出 SUFFICIENT / INSUFFICIENT。
3）judge backend 使用 DeepSeek API。
4）保持最小实现：单次 LLM judge,不接 pipeline，不做 retry / re-retrieve。

整体结构：
1）读取环境变量中的 DeepSeek 配置。
2）构造 chunks 预览与 sufficiency prompt。
3）调用 DeepSeek Chat Completions 接口。
4）解析输出并收敛为二分类标签。
5）返回 (result, total_ms)。

环境变量：
- DEEPSEEK_API_KEY：必填。
- DEEPSEEK_BASE_URL：可选，默认 https://api.deepseek.com。
- DEEPSEEK_MODEL：可选，默认 deepseek-v4-flash。

本版变更（相对上版）：
- max_tokens: 8 -> 32，避免 SUFFICIENT/INSUFFICIENT 被切断。
- system prompt 改为英文严格指令，要求只输出标签。
- 增加 raw output debug 打印，便于排查。
- parse 失败时打印 WARN 日志而非静默兜底。
"""

from __future__ import annotations  # 启用前向引用类型标注，提升兼容性。

import json  # 导入 json 模块，用于编码请求体与解析响应体。
import os  # 导入 os 模块，用于读取环境变量。
import time  # 导入 time 模块，用于统计耗时。
import socket  # 导入 socket，用于识别网络超时。
import urllib.error  # 导入 urllib.error，用于捕获 HTTP 错误。
import urllib.request  # 导入 urllib.request，用于发送 HTTP 请求。
from typing import List, Optional, Tuple  # 导入类型标注。
from agentic_rag.config import GeneratorProfileConfig
from agentic_rag.types import Chunk  # 导入 Chunk 类型，保持与现有项目接口一致。
from agentic_rag.policy.egress import EgressDenied, authorize_provider_attempt, chunk_visibilities


class SufficiencyJudgeError(RuntimeError):
    """证据充分性 judge 异常基类。"""


class SufficiencyJudgeUnavailable(SufficiencyJudgeError):
    """DeepSeek judge 不可达或配置不可用。"""


class SufficiencyJudgeTimeout(SufficiencyJudgeError):
    """DeepSeek judge 调用超时。"""

# ======== 可调参数（先写死，后续再抽 config） ========
_MAX_CHUNKS: int = 5  # 最多取前几个 chunk。
_MAX_CHARS_PER_CHUNK: int = 1200  # 每个 chunk 截断长度。
_DEFAULT_DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"  # DeepSeek 默认基础地址。
_DEFAULT_DEEPSEEK_MODEL: str = "deepseek-v4-flash"  # DeepSeek 默认模型名称。
_REQUEST_TIMEOUT_SECONDS: int = 120  # 单次请求超时时间（秒）。
_MAX_OUTPUT_TOKENS: int = 32  # 输出 token 上限，留足空间防止标签被切断。
_DEBUG_RAW_OUTPUT: bool = False  # 是否打印 DeepSeek 原始输出，便于排查。


def _build_chunks_preview(chunks: List[Chunk]) -> str:
    # 把 chunks 转成 LLM 可读的简化文本。
    blocks: List[str] = []  # 初始化证据文本块列表。
    for i, chunk in enumerate(chunks[:_MAX_CHUNKS]):  # 只取前若干个 chunk。
        text = chunk.text[:_MAX_CHARS_PER_CHUNK]  # 对单个 chunk 做长度截断。
        blocks.append(f"证据{i + 1}：\n{text}")  # 追加当前证据块。
    return "\n\n".join(blocks)  # 返回拼接后的证据预览。


def _build_prompt(query: str, chunks_preview: str) -> str:
    # 构造 sufficiency 判断 prompt。
    return f"""你是一个证据充分性判断器。

问题：
{query}

证据：
{chunks_preview}

任务：
判断“当前证据是否足以支持回答该问题”。

判断标准：
- SUFFICIENT：证据与问题相关，且已经提供回答该问题所需的主要信息；允许做少量归纳总结。
- INSUFFICIENT：证据与问题明显无关，或缺少回答该问题必需的核心信息。

注意：
- 不要求证据逐字逐句出现最终答案。
- 只要基于证据可以做出有依据的回答，就判为 SUFFICIENT。
- 只有明显缺信息，才判为 INSUFFICIENT。

只输出一个词：
SUFFICIENT
或
INSUFFICIENT
"""  # 返回最终 prompt 文本。


def _parse_result(text: str) -> str:
    # 解析模型输出，统一收敛成二分类标签。
    text_upper = text.strip().upper()  # 先做首尾清理并统一转大写。
    lines = [line.strip() for line in text_upper.splitlines() if line.strip()]  # 提取非空行。

    for line in lines:  # 逐行优先做严格匹配。
        if line == "INSUFFICIENT":  # 若命中严格的 INSUFFICIENT。
            return "INSUFFICIENT"  # 直接返回 INSUFFICIENT。
        if line == "SUFFICIENT":  # 若命中严格的 SUFFICIENT。
            return "SUFFICIENT"  # 直接返回 SUFFICIENT。

    # 注意检查顺序：INSUFFICIENT 包含 SUFFICIENT 子串，必须先查 INSUFFICIENT。
    if "INSUFFICIENT" in text_upper:  # 若全文中包含 INSUFFICIENT。
        return "INSUFFICIENT"  # 返回 INSUFFICIENT。
    if "SUFFICIENT" in text_upper:  # 若全文中包含 SUFFICIENT。
        return "SUFFICIENT"  # 返回 SUFFICIENT。

    print(f"[sufficiency][WARN] parse failed, fallback to INSUFFICIENT, raw={text!r}")  # 解析失败时打印 WARN，避免静默兜底。
    return "INSUFFICIENT"  # 解析失败时保守回落为 INSUFFICIENT。


def _read_judge_settings(
    profile: Optional[GeneratorProfileConfig] = None,
) -> tuple[str, str, str, str]:
    # 读取 OpenAI-compatible judge 配置。
    # 默认保持 DeepSeek，不影响现有链路；需要切 OpenRouter 时用 JUDGE_* 覆盖。
    if profile is not None:
        backend_name = str(profile.backend).strip().lower()
        if backend_name not in {"openai_compatible", "openai-compatible", "openai"}:
            raise SufficiencyJudgeUnavailable(
                f"sufficiency judge profile requires OpenAI-compatible backend: {profile.name}"
            )
        api_key_env = str(profile.api_key_env).strip()
        api_key = os.getenv(api_key_env, "").strip() if api_key_env else ""
        if api_key == "":
            raise SufficiencyJudgeUnavailable(
                f"缺少环境变量 {api_key_env or '<empty>'}，无法调用 sufficiency judge"
            )
        return (
            api_key,
            str(profile.base_url).strip().rstrip("/"),
            str(profile.model).strip(),
            str(profile.provider_tag or profile.backend).strip(),
        )

    api_key_env = os.getenv("JUDGE_API_KEY_ENV", "DEEPSEEK_API_KEY").strip()
    if api_key_env == "":
        api_key_env = "DEEPSEEK_API_KEY"

    api_key = os.getenv(api_key_env, "").strip()

    base_url = (
        os.getenv("JUDGE_API_BASE_URL")
        or os.getenv("JUDGE_BASE_URL")
        or os.getenv("DEEPSEEK_BASE_URL")
        or _DEFAULT_DEEPSEEK_BASE_URL
    ).strip().rstrip("/")

    model = (
        os.getenv("JUDGE_MODEL")
        or os.getenv("DEEPSEEK_MODEL")
        or _DEFAULT_DEEPSEEK_MODEL
    ).strip()

    if model == "":
        model = _DEFAULT_DEEPSEEK_MODEL

    backend = os.getenv("JUDGE_BACKEND", "").strip()
    if backend == "":
        backend = "deepseek" if ("deepseek" in model.lower() or "deepseek" in base_url.lower()) else "openai_compatible"

    if api_key == "":
        raise SufficiencyJudgeUnavailable(f"缺少环境变量 {api_key_env}，无法调用 sufficiency judge")

    return api_key, base_url, model, backend

def _call_judge(
    prompt: str,
    *,
    visibilities: Optional[Tuple[str, ...]] = None,
    profile: Optional[GeneratorProfileConfig] = None,
) -> tuple[str, str, str, "ModelCallRecord"]:
    # 调用 OpenAI-compatible Chat Completions 接口并返回文本结果、backend、model、model_call。
    api_key, base_url, model, backend = _read_judge_settings(profile)
    identity = _identity_from_judge_settings(
        backend=backend,
        base_url=base_url,
        model=model,
        api_key=api_key,
    )
    url = f"{base_url}/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": "Output exactly one word: SUFFICIENT or INSUFFICIENT. No explanation, no punctuation, no other text.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": min(
            _MAX_OUTPUT_TOKENS,
            int(profile.max_tokens) if profile is not None else _MAX_OUTPUT_TOKENS,
        ),
        "stream": False,
    }

    # DeepSeek V4 Flash non-thinking 路线需要显式关闭 thinking。
    # OpenRouter / OpenAI-compatible 其它模型不要传这个字段。
    if backend.lower() == "deepseek" or "deepseek" in model.lower() or "deepseek" in base_url.lower():
        payload["thinking"] = {"type": "disabled"}

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url=url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Authorization", f"Bearer {api_key}")

    t_llm0 = time.time()
    try:
        try:
            authorize_provider_attempt(
                identity.provider,
                stage="sufficiency_judge",
                attempt=1,
                visibilities=visibilities,
            )
        except EgressDenied as exc:
            raise SufficiencyJudgeUnavailable(f"egress_policy_denied: {exc}") from exc
        timeout_s = float(profile.timeout_s) if profile is not None else _REQUEST_TIMEOUT_SECONDS
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            raw_text = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise SufficiencyJudgeUnavailable(
            f"Sufficiency judge HTTPError: status={exc.code} body={error_body}"
        ) from exc
    except (socket.timeout, TimeoutError) as exc:
        raise SufficiencyJudgeTimeout(f"Sufficiency judge timeout: {exc}") from exc
    except urllib.error.URLError as exc:
        reason = str(getattr(exc, "reason", exc))
        if "timed out" in reason.lower() or "timeout" in reason.lower():
            raise SufficiencyJudgeTimeout(f"Sufficiency judge URLError timeout: {exc}") from exc
        raise SufficiencyJudgeUnavailable(f"Sufficiency judge URLError: {exc}") from exc

    latency_ms = float((time.time() - t_llm0) * 1000.0)

    try:
        data = json.loads(raw_text)
        text = data["choices"][0]["message"]["content"]
        finish_reason = data["choices"][0].get("finish_reason", "unknown")
        usage = dict(data.get("usage", {}) or {})
        provider_response_model = data.get("model")
    except Exception as exc:
        raise SufficiencyJudgeUnavailable(f"Sufficiency judge 响应解析失败: {raw_text}") from exc

    if provider_response_model:
        identity.provider_response_model = str(provider_response_model)
        identity.resolved_model = str(provider_response_model)

    usage["provider"] = identity.provider
    usage["configured_model"] = identity.configured_model
    usage["provider_response_model"] = identity.provider_response_model
    usage["resolved_model"] = identity.resolved_model
    usage["endpoint"] = identity.endpoint
    usage["api_key_hash"] = identity.api_key_hash
    usage["network_tag"] = identity.network_tag
    usage["proxy_node"] = identity.proxy_node

    call = ModelCallRecord.from_token_usage(
        role="sufficiency_judge",
        token_usage=usage,
        latency_ms=float(latency_ms),
        http_status=200,
    )
    call.identity = identity

    if _DEBUG_RAW_OUTPUT:
        print(f"[sufficiency][DEBUG] raw_output={text!r} finish_reason={finish_reason}")

    return str(text), backend, model, call

def judge_sufficiency_with_model_call(
    query: str,
    chunks: List[Chunk],
    *,
    profile: Optional[GeneratorProfileConfig] = None,
) -> tuple[str, float, "ModelCallRecord"]:
    """
    核心函数：判断证据是否充分，并返回模型调用记录。
    返回：
        ("SUFFICIENT" 或 "INSUFFICIENT", total_ms, ModelCallRecord)
    """

    t0 = time.time()  # 记录总耗时起点。

    if not chunks:  # 若没有任何检索结果。
        print("[sufficiency] cost_ms=0 result=INSUFFICIENT (no chunks)")  # 打印无证据日志。
        call = ModelCallRecord(
            role="sufficiency_judge",
            identity=ModelIdentity(),
            latency_ms=0.0,
        )
        return "INSUFFICIENT", 0.0, call  # 直接返回 INSUFFICIENT。

    chunks_preview = _build_chunks_preview(chunks)  # 构造证据预览。
    prompt = _build_prompt(query, chunks_preview)  # 构造 sufficiency prompt。

    text, backend, model, call = _call_judge(  # 调用 sufficiency judge 获取判断结果和模型调用记录。
        prompt,
        visibilities=chunk_visibilities(chunks),
        profile=profile,
    )
    llm_ms = float(call.latency_ms or 0.0)

    result = _parse_result(text)  # 将模型输出解析为二分类标签。
    total_ms = (time.time() - t0) * 1000  # 计算总耗时。

    if call.latency_ms is None:
        call.latency_ms = float(total_ms)

    print(f"[sufficiency] backend={backend} model={model} total_ms={total_ms:.1f} llm_ms={llm_ms:.1f} result={result}")  # 打印本次判定日志。

    return result, total_ms, call  # 返回最终结果、耗时与模型调用记录。


def judge_sufficiency(
    query: str,
    chunks: List[Chunk],
    *,
    profile: Optional[GeneratorProfileConfig] = None,
) -> tuple[str, float]:
    """
    兼容旧接口：判断证据是否充分。
    返回：
        ("SUFFICIENT" 或 "INSUFFICIENT", total_ms)
    """
    result, total_ms, _ = judge_sufficiency_with_model_call(
        query=query,
        chunks=chunks,
        profile=profile,
    )
    return result, total_ms

# ======== D-full Step 10：基于 EvidencePacket 的结构化充分性判断 ========

from dataclasses import asdict
from hashlib import sha256
from typing import Any, Dict

from agentic_rag.observability.model_identity import ModelIdentity
from agentic_rag.observability.observability_record import ModelCallRecord
from agentic_rag.workflow.workflow_state import EvidencePacket, SufficiencyResult


_STRUCTURED_MAX_OUTPUT_TOKENS: int = 512


def _identity_from_judge_settings(
    *,
    backend: str,
    base_url: str,
    model: str,
    api_key: str,
) -> ModelIdentity:
    """作用：为 sufficiency judge 构造最小 ModelIdentity。"""
    api_key_hash = sha256(api_key.encode("utf-8")).hexdigest()[:12] if api_key else None
    provider = "deepseek" if ("deepseek" in backend.lower() or "deepseek" in base_url.lower() or "deepseek" in model.lower()) else backend

    return ModelIdentity(
        provider=str(provider),
        configured_model=str(model),
        provider_response_model=None,
        resolved_model=str(model),
        endpoint=str(base_url),
        upstream_provider=None,
        api_key_hash=api_key_hash,
        network_tag=os.getenv("NETWORK_TAG", "").strip() or None,
        proxy_node=os.getenv("PROXY_NODE", "").strip() or None,
    )


def _packet_item_id(idx: int, item: Any) -> str:
    """作用：生成稳定 evidence_id，供 judge 输出 supporting_evidence_ids / conflict_evidence_ids。"""
    chunk_id = str(getattr(item, "chunk_id", "") or "").strip()
    if chunk_id:
        return chunk_id
    return f"evidence_{idx + 1}"


def _format_evidence_packet_for_prompt(packet: EvidencePacket) -> str:
    """作用：把 EvidencePacket 转成结构化 judge 可读输入。"""
    items = list(getattr(packet, "items", []) or [])
    if not items:
        return "EvidencePacket.items is empty."

    blocks: List[str] = []
    for idx, item in enumerate(items[:_MAX_CHUNKS]):
        evidence_id = _packet_item_id(idx, item)
        preview = str(getattr(item, "text_preview", "") or "")[:_MAX_CHARS_PER_CHUNK]
        block = {
            "evidence_id": evidence_id,
            "chunk_id": getattr(item, "chunk_id", None),
            "source_id": getattr(item, "source_id", None),
            "source_path": getattr(item, "source_path", None),
            "section_path": getattr(item, "section_path", None),
            "visibility": getattr(item, "visibility", None),
            "retrieval_query": getattr(item, "retrieval_query", None),
            "vector_score": getattr(item, "vector_score", None),
            "rerank_score": getattr(item, "rerank_score", None),
            "known_flags": {
                "is_expected_source": getattr(item, "is_expected_source", None),
                "is_expected_section": getattr(item, "is_expected_section", None),
                "is_answer_bearing": getattr(item, "is_answer_bearing", None),
                "in_prompt": getattr(item, "in_prompt", False),
            },
            "text_preview": preview,
        }
        blocks.append(json.dumps(block, ensure_ascii=False))

    diagnostics = {
        "source_coverage": dict(getattr(packet, "source_coverage", {}) or {}),
        "answer_bearing_summary": dict(getattr(packet, "answer_bearing_summary", {}) or {}),
        "score_summary": dict(getattr(packet, "score_summary", {}) or {}),
        "compression_policy": getattr(packet, "compression_policy", None),
        "known_gaps": list(getattr(packet, "known_gaps", []) or []),
    }

    return "\n".join(blocks) + "\n\nEvidencePacket diagnostics:\n" + json.dumps(diagnostics, ensure_ascii=False, indent=2)


def _build_structured_packet_prompt(
    *,
    query: str,
    question_type: Optional[str],
    route: Optional[str],
    evidence_packet: EvidencePacket,
    instruction: Optional[str],
) -> str:
    """作用：构造 EvidencePacket 版 sufficiency prompt。"""
    packet_text = _format_evidence_packet_for_prompt(evidence_packet)
    extra_instruction = str(instruction or "").strip() or "判断当前 EvidencePacket 是否足以支撑回答用户问题。"

    return f"""你是企业知识库 RAG 系统的证据充分性判断器。

用户问题:
{query}

question_type:
{question_type or "UNKNOWN"}

route:
{route or "UNKNOWN"}

instruction:
{extra_instruction}

EvidencePacket:
{packet_text}

判断标准:
- SUFFICIENT: 当前证据足以回答问题的核心需求，可以做必要归纳。
- INSUFFICIENT: 当前证据缺少回答问题所必需的核心信息，或 EvidencePacket 为空。
- CONFLICTED: 当前证据之间存在直接冲突，无法安全给出单一结论。

输出要求:
- 只输出 JSON。
- 不要 markdown。
- 不要解释 JSON 之外的内容。
- supporting_evidence_ids / conflict_evidence_ids 必须使用 EvidencePacket 中的 evidence_id 或 chunk_id。
- 如果缺证据，missing_evidence 写具体缺口。

JSON schema:
{{
  "verdict": "SUFFICIENT | INSUFFICIENT | CONFLICTED",
  "confidence": "high | medium | low",
  "missing_evidence": ["..."],
  "supporting_evidence_ids": ["..."],
  "conflict_evidence_ids": ["..."],
  "reason": "..."
}}
"""


def _extract_json_object(text: str) -> Dict[str, Any]:
    """作用：从 judge 输出中提取 JSON object。"""
    raw = str(text or "").strip()
    if raw.startswith("```"):
        raw = raw.strip("`").strip()
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()

    try:
        parsed = json.loads(raw)
        return dict(parsed) if isinstance(parsed, dict) else {}
    except Exception:
        pass

    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        parsed = json.loads(raw[start : end + 1])
        return dict(parsed) if isinstance(parsed, dict) else {}

    return {}


def _normalize_structured_sufficiency(data: Dict[str, Any], *, raw_text: str = "") -> SufficiencyResult:
    """作用：把任意 judge JSON 收敛为 SufficiencyResult。"""
    verdict_raw = str(data.get("verdict") or "").strip().upper()
    if verdict_raw not in {"SUFFICIENT", "INSUFFICIENT", "CONFLICTED"}:
        # parse 失败默认 fail-close。
        verdict_raw = "INSUFFICIENT"

    confidence_raw = str(data.get("confidence") or "").strip().lower()
    if confidence_raw not in {"high", "medium", "low"}:
        confidence_raw = "low"

    def _list_str(value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(x) for x in value if str(x).strip()]
        if value is None:
            return []
        text_value = str(value).strip()
        return [text_value] if text_value else []

    reason = str(data.get("reason") or "").strip()
    if not reason and not data:
        reason = f"judge_output_parse_failed raw={raw_text[:200]!r}"

    return SufficiencyResult(
        verdict=verdict_raw,
        confidence=confidence_raw,
        missing_evidence=_list_str(data.get("missing_evidence")),
        supporting_evidence_ids=_list_str(data.get("supporting_evidence_ids")),
        conflict_evidence_ids=_list_str(data.get("conflict_evidence_ids")),
        reason=reason,
    )


def _call_structured_judge(
    prompt: str,
    *,
    visibilities: Optional[Tuple[str, ...]] = None,
    profile: Optional[GeneratorProfileConfig] = None,
) -> Tuple[str, ModelIdentity, ModelCallRecord]:
    """作用：调用 OpenAI-compatible judge，并返回原始文本、模型身份与调用记录。"""
    api_key, base_url, model, backend = _read_judge_settings(profile)
    identity = _identity_from_judge_settings(
        backend=backend,
        base_url=base_url,
        model=model,
        api_key=api_key,
    )

    url = f"{base_url}/chat/completions"
    payload: Dict[str, Any] = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a strict evidence sufficiency judge. "
                    "Output only valid JSON matching the requested schema."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0,
        "max_tokens": min(
            _STRUCTURED_MAX_OUTPUT_TOKENS,
            int(profile.max_tokens) if profile is not None else _STRUCTURED_MAX_OUTPUT_TOKENS,
        ),
        "stream": False,
    }

    if backend.lower() == "deepseek" or "deepseek" in model.lower() or "deepseek" in base_url.lower():
        payload["thinking"] = {"type": "disabled"}

    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url=url, data=body, method="POST")
    request.add_header("Content-Type", "application/json")
    request.add_header("Authorization", f"Bearer {api_key}")

    t0 = time.time()
    try:
        try:
            authorize_provider_attempt(
                identity.provider,
                stage="structured_sufficiency_judge",
                attempt=1,
                visibilities=visibilities,
            )
        except EgressDenied as exc:
            raise SufficiencyJudgeUnavailable(f"egress_policy_denied: {exc}") from exc
        timeout_s = float(profile.timeout_s) if profile is not None else _REQUEST_TIMEOUT_SECONDS
        with urllib.request.urlopen(request, timeout=timeout_s) as response:
            raw_text = response.read().decode("utf-8")
            http_status = int(getattr(response, "status", 200))
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise SufficiencyJudgeUnavailable(
            f"Sufficiency structured judge HTTPError: status={exc.code} body={error_body}"
        ) from exc
    except (socket.timeout, TimeoutError) as exc:
        raise SufficiencyJudgeTimeout(f"Sufficiency structured judge timeout: {exc}") from exc
    except urllib.error.URLError as exc:
        reason = str(getattr(exc, "reason", exc))
        if "timed out" in reason.lower() or "timeout" in reason.lower():
            raise SufficiencyJudgeTimeout(f"Sufficiency structured judge URLError timeout: {exc}") from exc
        raise SufficiencyJudgeUnavailable(f"Sufficiency structured judge URLError: {exc}") from exc

    latency_ms = float((time.time() - t0) * 1000.0)

    try:
        data = json.loads(raw_text)
        message = data["choices"][0]["message"]
        text = str(message.get("content") or "")
        usage = dict(data.get("usage", {}) or {})
        provider_response_model = data.get("model")
    except Exception as exc:
        raise SufficiencyJudgeUnavailable(f"Sufficiency structured judge 响应解析失败: {raw_text}") from exc

    if provider_response_model:
        identity.provider_response_model = str(provider_response_model)
        identity.resolved_model = str(provider_response_model)

    usage["provider"] = identity.provider
    usage["configured_model"] = identity.configured_model
    usage["provider_response_model"] = identity.provider_response_model
    usage["resolved_model"] = identity.resolved_model
    usage["endpoint"] = identity.endpoint
    usage["api_key_hash"] = identity.api_key_hash
    usage["network_tag"] = identity.network_tag
    usage["proxy_node"] = identity.proxy_node

    call = ModelCallRecord.from_token_usage(
        role="sufficiency_judge",
        token_usage=usage,
        latency_ms=latency_ms,
        http_status=http_status,
    )
    call.identity = identity

    return text, identity, call


def judge_sufficiency_with_evidence_packet(
    *,
    query: str,
    evidence_packet: EvidencePacket,
    question_type: Optional[str] = None,
    route: Optional[str] = None,
    instruction: Optional[str] = None,
    profile: Optional[GeneratorProfileConfig] = None,
) -> Tuple[SufficiencyResult, float, ModelCallRecord]:
    """
    作用：D-full Step 10 结构化证据充分性判断。
    返回：
        (SufficiencyResult, total_ms, ModelCallRecord)
    """
    t0 = time.time()

    items = list(getattr(evidence_packet, "items", []) or [])
    if not items:
        result = SufficiencyResult(
            verdict="INSUFFICIENT",
            confidence="high",
            missing_evidence=["EvidencePacket.items is empty."],
            supporting_evidence_ids=[],
            conflict_evidence_ids=[],
            reason="No evidence items are available for sufficiency judgement.",
            model_identity=ModelIdentity(),
        )
        call = ModelCallRecord(
            role="sufficiency_judge",
            identity=ModelIdentity(),
            latency_ms=0.0,
        )
        return result, 0.0, call

    prompt = _build_structured_packet_prompt(
        query=str(query),
        question_type=question_type,
        route=route,
        evidence_packet=evidence_packet,
        instruction=instruction,
    )

    packet_visibilities = []
    for item in items:
        visibility = getattr(item, "visibility", None)
        if visibility not in (None, ""):
            packet_visibilities.append(str(visibility))
    raw_text, identity, call = _call_structured_judge(
        prompt,
        visibilities=tuple(packet_visibilities),
        profile=profile,
    )
    parsed = _extract_json_object(raw_text)
    result = _normalize_structured_sufficiency(parsed, raw_text=raw_text)
    result.model_identity = identity

    total_ms = float((time.time() - t0) * 1000.0)
    if call.latency_ms is None:
        call.latency_ms = total_ms

    print(
        "[sufficiency][structured] "
        f"provider={identity.provider} model={identity.configured_model} "
        f"resolved_model={identity.resolved_model} total_ms={total_ms:.1f} "
        f"verdict={result.verdict} confidence={result.confidence}",
        flush=True,
    )

    return result, total_ms, call
