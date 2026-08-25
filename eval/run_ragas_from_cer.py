#!/usr/bin/env python3
"""Run per-case/per-metric RAGAS with an explicit model-call ledger."""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import json
import math
import os
import statistics
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping, Optional

from agentic_rag.evaluation.offline_record import (
    normalize_model_call,
    price_model_calls,
    stable_sha256,
)


METRIC_ALIASES = {
    "context_precision": ["context_precision", "llm_context_precision_with_reference"],
    "faithfulness": ["faithfulness"],
    "answer_relevancy": ["answer_relevancy", "response_relevancy"],
}


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="run_ragas_from_cer")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--allow-provider-calls", action="store_true")
    parser.add_argument(
        "--confirm-external-evidence-egress",
        action="store_true",
        help="confirm that query, answer, references, and prompt-visible evidence may leave the host",
    )
    parser.add_argument("--llm-model", default=os.getenv("EVAL_MODEL", "deepseek-v4-flash"))
    parser.add_argument("--api-base-url", default=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))
    parser.add_argument("--api-key-env", default="DEEPSEEK_API_KEY")
    parser.add_argument("--embedding-model", default="BAAI/bge-small-zh-v1.5")
    parser.add_argument(
        "--embedding-model-id",
        default="BAAI/bge-small-zh-v1.5",
        help="stable model identity used when --embedding-model is a local path",
    )
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--ids", nargs="+", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--max-total-tokens", type=int, default=None)
    parser.add_argument("--max-cost-usd", type=float, default=None)
    parser.add_argument("--max-model-calls", type=int, default=None)
    parser.add_argument("--no-context-precision", action="store_true")
    parser.add_argument("--no-faithfulness", action="store_true")
    parser.add_argument("--no-answer-relevancy", action="store_true")
    return parser.parse_args()


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise ValueError(f"RAGAS input is empty: {path}")
    for index, row in enumerate(rows, start=1):
        for key in ("qid", "user_input", "response", "retrieved_contexts", "source_cer_sha256"):
            if key not in row:
                raise ValueError(f"RAGAS input row {index} missing {key}")
        if not isinstance(row.get("retrieved_contexts"), list) or not row["retrieved_contexts"]:
            raise ValueError(f"RAGAS input row {index} has no contexts")
    qids = [str(row.get("qid")) for row in rows]
    duplicates = sorted({qid for qid in qids if qids.count(qid) > 1})
    if duplicates:
        raise ValueError(f"RAGAS input has duplicate qid(s): {', '.join(duplicates)}")
    return rows


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _embedding_binding(runtime_value: str, model_id: str) -> dict[str, Any]:
    path = Path(runtime_value).expanduser()
    if not path.exists():
        return {
            "model_id": str(runtime_value),
            "runtime_source": "configured_model_id",
            "local_content_sha256": None,
        }
    digest = hashlib.sha256()
    for child in sorted(item for item in path.rglob("*") if item.is_file()):
        digest.update(child.relative_to(path).as_posix().encode("utf-8"))
        digest.update(b"\0")
        with child.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    return {
        "model_id": str(model_id),
        "runtime_source": "explicit_local_path",
        "local_content_sha256": digest.hexdigest(),
    }


def _first_generation(response: Any) -> Any:
    generations = getattr(response, "generations", None) or []
    if generations and isinstance(generations[0], list) and generations[0]:
        return generations[0][0]
    if generations:
        return generations[0]
    return None


def extract_usage(response: Any) -> dict[str, Any]:
    """Extract OpenAI-compatible usage without converting unknown fields to zero."""
    llm_output = getattr(response, "llm_output", None)
    llm_output = dict(llm_output) if isinstance(llm_output, Mapping) else {}
    raw = llm_output.get("token_usage") or llm_output.get("usage") or {}
    raw = dict(raw) if isinstance(raw, Mapping) else {}

    generation = _first_generation(response)
    message = getattr(generation, "message", None) if generation is not None else None
    usage_metadata = getattr(message, "usage_metadata", None)
    usage_metadata = dict(usage_metadata) if isinstance(usage_metadata, Mapping) else {}
    response_metadata = getattr(message, "response_metadata", None)
    response_metadata = dict(response_metadata) if isinstance(response_metadata, Mapping) else {}
    metadata_usage = response_metadata.get("token_usage") or response_metadata.get("usage") or {}
    metadata_usage = dict(metadata_usage) if isinstance(metadata_usage, Mapping) else {}

    def pick(*keys: str) -> Any:
        for container in (usage_metadata, raw, metadata_usage):
            for key in keys:
                if container.get(key) not in (None, ""):
                    return container.get(key)
        return None

    def detail_pick(container: Mapping[str, Any], *keys: str) -> Any:
        for key in keys:
            if container.get(key) not in (None, ""):
                return container.get(key)
        return None

    input_details = usage_metadata.get("input_token_details") or raw.get("prompt_tokens_details") or {}
    output_details = usage_metadata.get("output_token_details") or raw.get("completion_tokens_details") or {}
    input_details = dict(input_details) if isinstance(input_details, Mapping) else {}
    output_details = dict(output_details) if isinstance(output_details, Mapping) else {}
    return {
        "prompt_tokens": pick("input_tokens", "prompt_tokens"),
        "completion_tokens": pick("output_tokens", "completion_tokens"),
        "total_tokens": pick("total_tokens"),
        "reasoning_tokens": detail_pick(output_details, "reasoning", "reasoning_tokens"),
        "cached_tokens": detail_pick(input_details, "cache_read", "cached_tokens"),
        "cache_write_tokens": detail_pick(
            input_details, "cache_creation", "cache_write_tokens"
        ),
        "provider_response_model": (
            llm_output.get("model_name")
            or response_metadata.get("model_name")
            or response_metadata.get("model")
        ),
    }


def _provider(model: str, base_url: str) -> str:
    combined = f"{model} {base_url}".lower()
    if "deepseek" in combined:
        return "deepseek"
    if "openrouter" in combined:
        return "openrouter"
    if "openai" in combined:
        return "openai"
    return "openai_compatible"


def _completion_transport(model: str, base_url: str) -> str:
    """Describe how multi-generation metric requests reach the provider.

    DeepSeek's OpenAI-compatible endpoint currently accepts only ``n=1``.
    RAGAS ResponseRelevancy defaults to three generations, so the evaluator
    preserves that metric contract by issuing three bounded concurrent single-
    generation requests and merging the generations locally.
    """
    if _provider(model, base_url) == "deepseek":
        return "parallel_n1_merge"
    return "provider_native_n"


def _merge_single_prompt_results(results: list[Any], result_type: Any) -> Any:
    """Merge repeated n=1 LLMResults into one result with n generations."""
    if not results:
        raise ValueError("cannot merge an empty result list")
    generations: list[Any] = []
    for result in results:
        batches = list(getattr(result, "generations", None) or [])
        if len(batches) != 1:
            raise ValueError("sequential completion result must contain exactly one prompt batch")
        generations.extend(list(batches[0]))
    # Usage is recorded on each underlying provider call by UsageLedgerCallback.
    # Do not synthesize a combined token_usage object that could be counted twice.
    return result_type(generations=[generations], llm_output=None)


def _multi_n_compat_wrapper_class(base_wrapper_type: Any, result_type: Any) -> Any:
    """Build a RAGAS wrapper that adapts unsupported n>1 calls to n=1."""

    class MultiNCompatWrapper(base_wrapper_type):
        def generate_text(
            self,
            prompt: Any,
            n: int = 1,
            temperature: float = 1e-8,
            stop: Any = None,
            callbacks: Any = None,
            **kwargs: Any,
        ) -> Any:
            if n <= 1:
                return super().generate_text(
                    prompt=prompt,
                    n=n,
                    temperature=temperature,
                    stop=stop,
                    callbacks=callbacks,
                    **kwargs,
                )
            parent_generate = super().generate_text
            results = [
                parent_generate(
                    prompt=prompt,
                    n=1,
                    temperature=temperature,
                    stop=stop,
                    callbacks=callbacks,
                    **kwargs,
                )
                for _ in range(n)
            ]
            return _merge_single_prompt_results(results, result_type)

        async def agenerate_text(
            self,
            prompt: Any,
            n: int = 1,
            temperature: float = 1e-8,
            stop: Any = None,
            callbacks: Any = None,
            **kwargs: Any,
        ) -> Any:
            if n <= 1:
                return await super().agenerate_text(
                    prompt=prompt,
                    n=n,
                    temperature=temperature,
                    stop=stop,
                    callbacks=callbacks,
                    **kwargs,
                )
            parent_generate = super().agenerate_text
            results = await asyncio.gather(
                *(
                    parent_generate(
                        prompt=prompt,
                        n=1,
                        temperature=temperature,
                        stop=stop,
                        callbacks=callbacks,
                        **kwargs,
                    )
                    for _ in range(n)
                )
            )
            return _merge_single_prompt_results(results, result_type)

    return MultiNCompatWrapper


def _instantiate_ragas_wrapper(
    wrapper_factory: Any,
    chat: Any,
    result_type: Any,
    completion_transport: str,
) -> Any:
    """Instantiate the concrete wrapper before applying the compatibility subclass.

    RAGAS 0.4.3 exports ``LangchainLLMWrapper`` through a deprecation proxy.
    The proxy is callable but is not itself a class, so it cannot be used as a
    subclass base.  Resolve one native instance first, then subclass its real
    concrete type for the DeepSeek-only transport adapter.
    """
    wrapper = wrapper_factory(chat)
    if completion_transport != "parallel_n1_merge":
        return wrapper
    wrapper_type = _multi_n_compat_wrapper_class(type(wrapper), result_type)
    return wrapper_type(chat)


def _build_callback(model: str, base_url: str) -> Any:
    from langchain_core.callbacks import BaseCallbackHandler

    provider = _provider(model, base_url)

    class UsageLedgerCallback(BaseCallbackHandler):
        def __init__(self) -> None:
            self.starts: dict[str, float] = {}
            self.calls: list[dict[str, Any]] = []
            self.qid = ""
            self.metric = ""

        def set_context(self, qid: str, metric: str) -> None:
            self.qid = qid
            self.metric = metric

        def _start(self, run_id: Any) -> None:
            self.starts[str(run_id)] = time.perf_counter()

        def on_llm_start(self, serialized: Any, prompts: Any, *, run_id: Any, **kwargs: Any) -> None:
            self._start(run_id)

        def on_chat_model_start(self, serialized: Any, messages: Any, *, run_id: Any, **kwargs: Any) -> None:
            self._start(run_id)

        def _duration(self, run_id: Any) -> float:
            started = self.starts.pop(str(run_id), time.perf_counter())
            return float((time.perf_counter() - started) * 1000.0)

        def on_llm_end(self, response: Any, *, run_id: Any, **kwargs: Any) -> None:
            usage = extract_usage(response)
            raw = {
                "provider": provider,
                "configured_model": model,
                "resolved_model": usage.pop("provider_response_model") or model,
                "latency_ms": self._duration(run_id),
                "api_error": False,
                "timeout": False,
                **usage,
            }
            call = normalize_model_call(
                raw,
                qid=self.qid,
                stage=f"ragas_{self.metric}",
                role="ragas_evaluator",
                index=len(self.calls) + 1,
                category="ragas",
            )
            call["category"] = "ragas"
            call["metric"] = self.metric
            self.calls.append(call)

        def on_llm_error(self, error: BaseException, *, run_id: Any, **kwargs: Any) -> None:
            raw = {
                "provider": provider,
                "configured_model": model,
                "resolved_model": model,
                "latency_ms": self._duration(run_id),
                "api_error": True,
                "timeout": "timeout" in type(error).__name__.lower() or "timeout" in str(error).lower(),
                "error_type": type(error).__name__,
                "error_message": str(error),
            }
            call = normalize_model_call(
                raw,
                qid=self.qid,
                stage=f"ragas_{self.metric}",
                role="ragas_evaluator",
                index=len(self.calls) + 1,
                category="ragas",
            )
            call["category"] = "ragas"
            call["metric"] = self.metric
            self.calls.append(call)

    return UsageLedgerCallback()


def _load_runtime(args: argparse.Namespace, callback: Any) -> tuple[Any, Any, Any, Any, Any]:
    try:
        from datasets import Dataset
        from langchain_core.outputs import LLMResult
        from langchain_openai import ChatOpenAI
        from ragas import evaluate
        from ragas.llms import LangchainLLMWrapper
        from ragas.run_config import RunConfig
    except ImportError as exc:
        raise RuntimeError(
            "RAGAS runtime is incomplete; install the project RAGAS/LangChain/datasets dependencies"
        ) from exc

    key = os.getenv(args.api_key_env)
    if not key:
        raise RuntimeError(f"missing environment variable: {args.api_key_env}")
    kwargs: dict[str, Any] = {
        "model": args.llm_model,
        "api_key": key,
        "base_url": args.api_base_url,
        "temperature": 0.0,
        "timeout": float(args.timeout),
        "callbacks": [callback],
    }
    if "deepseek" in str(args.llm_model).lower() or "deepseek" in str(args.api_base_url).lower():
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    chat = ChatOpenAI(**kwargs)
    wrapper = _instantiate_ragas_wrapper(
        LangchainLLMWrapper,
        chat,
        LLMResult,
        _completion_transport(args.llm_model, args.api_base_url),
    )
    run_config = RunConfig(timeout=args.timeout, max_retries=1, max_wait=10, max_workers=1)
    wrapper.set_run_config(run_config)

    encode_kwargs = {"normalize_embeddings": True}
    try:
        from langchain_huggingface import HuggingFaceEmbeddings
    except ImportError:
        from langchain_community.embeddings import HuggingFaceEmbeddings
    embeddings = HuggingFaceEmbeddings(
        model_name=args.embedding_model,
        encode_kwargs=encode_kwargs,
        model_kwargs={"local_files_only": True},
    )
    return Dataset, evaluate, wrapper, embeddings, run_config


def _metrics(args: argparse.Namespace) -> list[tuple[str, Any]]:
    from ragas.metrics import Faithfulness, LLMContextPrecisionWithReference, ResponseRelevancy

    metrics: list[tuple[str, Any]] = []
    if not args.no_context_precision:
        metrics.append(("context_precision", LLMContextPrecisionWithReference()))
    if not args.no_faithfulness:
        metrics.append(("faithfulness", Faithfulness()))
    if not args.no_answer_relevancy:
        metrics.append(("answer_relevancy", ResponseRelevancy()))
    if not metrics:
        raise ValueError("at least one RAGAS metric must be enabled")
    return metrics


def _metric_names(args: argparse.Namespace) -> list[str]:
    names: list[str] = []
    if not args.no_context_precision:
        names.append("context_precision")
    if not args.no_faithfulness:
        names.append("faithfulness")
    if not args.no_answer_relevancy:
        names.append("answer_relevancy")
    if not names:
        raise ValueError("at least one RAGAS metric must be enabled")
    return names


def _dataset_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "question": str(row["user_input"]),
        "answer": str(row["response"]),
        "contexts": [str(item) for item in list(row["retrieved_contexts"])],
        "ground_truth": str(row.get("reference") or ""),
        "user_input": str(row["user_input"]),
        "response": str(row["response"]),
        "retrieved_contexts": [str(item) for item in list(row["retrieved_contexts"])],
        "reference": str(row.get("reference") or ""),
    }


def _score(result: Any, metric: str) -> Optional[float]:
    frame = result.to_pandas()
    if frame.empty:
        return None
    for column in METRIC_ALIASES[metric]:
        if column not in frame.columns:
            continue
        try:
            value = float(frame.iloc[0][column])
        except (TypeError, ValueError):
            return None
        return value if math.isfinite(value) else None
    return None


def _atomic_write(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
        tmp = Path(handle.name)
    os.replace(tmp, path)


def _load_existing(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _budget_totals(records: list[dict[str, Any]]) -> dict[str, int | float | None]:
    model_calls = sum(len(record.get("model_calls") or []) for record in records)
    token_values = [
        int(usage["total_tokens"])
        for record in records
        if (usage := dict(record.get("usage") or {})).get("total_tokens") not in (None, "")
    ]
    cost_values = [
        float(usage["estimated_cost_usd"])
        for record in records
        if (usage := dict(record.get("usage") or {})).get("estimated_cost_usd") not in (None, "")
    ]
    unknown_token_records = sum(
        bool(record.get("model_calls"))
        and dict(record.get("usage") or {}).get("total_tokens") in (None, "")
        for record in records
    )
    unknown_cost_records = sum(
        bool(record.get("model_calls"))
        and dict(record.get("usage") or {}).get("estimated_cost_usd") in (None, "")
        for record in records
    )
    return {
        "model_calls": model_calls,
        "total_tokens": sum(token_values) if not unknown_token_records else None,
        "total_tokens_observed_sum": sum(token_values),
        "unknown_token_record_count": unknown_token_records,
        "estimated_cost_usd": sum(cost_values) if not unknown_cost_records else None,
        "estimated_cost_usd_observed_sum": sum(cost_values),
        "unknown_cost_record_count": unknown_cost_records,
    }


def _preflight_budget_reason(
    records: list[dict[str, Any]], args: argparse.Namespace
) -> Optional[str]:
    totals = _budget_totals(records)
    if args.max_model_calls is not None and int(totals["model_calls"] or 0) >= args.max_model_calls:
        return "model-call budget has no remaining headroom"
    if args.max_total_tokens is not None:
        if totals["total_tokens"] is None:
            return "total-token budget cannot be enforced because usage is incomplete"
        if int(totals["total_tokens"]) >= args.max_total_tokens:
            return "total-token budget has no remaining headroom"
    if args.max_cost_usd is not None:
        if totals["estimated_cost_usd"] is None:
            return "cost budget cannot be enforced because pricing is incomplete"
        if float(totals["estimated_cost_usd"]) >= args.max_cost_usd:
            return "cost budget has no remaining headroom"
    return None


def _format_score(value: Any) -> str:
    if value in (None, ""):
        return "not_observed"
    try:
        return f"{float(value):.4f}"
    except (TypeError, ValueError):
        return str(value)


def _format_int(value: Any) -> str:
    if value in (None, ""):
        return "not_observed"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value)


def _format_cost(value: Any) -> str:
    if value in (None, ""):
        return "not_observed"
    try:
        return f"{float(value):.6f}"
    except (TypeError, ValueError):
        return str(value)


def _profile_from_input_rows(input_rows: Optional[list[dict[str, Any]]]) -> str:
    profiles = {
        str(row.get("source_profile") or "").strip()
        for row in list(input_rows or [])
        if str(row.get("source_profile") or "").strip()
    }
    if len(profiles) == 1:
        return next(iter(profiles))
    return "mixed" if profiles else "unknown"


def _skip_reason_zh(reason: str) -> str:
    return {
        "enable_ragas_false": "该题按配置不启用 RAGAS",
        "source_not_answered": "主链未产生 ANSWERED 结果",
        "reference_missing": "缺少 reference",
    }.get(str(reason), str(reason))


def _metric_usage(rows: list[dict[str, Any]]) -> dict[str, Any]:
    calls = [dict(call) for row in rows for call in list(row.get("model_calls") or [])]
    token_unknown = False
    token_sum = 0
    cost_unknown = False
    cost_sum = 0.0
    duration_sum = 0.0
    for row in rows:
        duration = row.get("duration_ms")
        if duration not in (None, ""):
            duration_sum += float(duration)
        usage = dict(row.get("usage") or {})
        tokens = usage.get("total_tokens")
        if tokens in (None, ""):
            token_unknown = True
        else:
            token_sum += int(tokens)
        cost = usage.get("estimated_cost_usd")
        if cost in (None, ""):
            cost_unknown = True
        else:
            cost_sum += float(cost)
    return {
        "model_calls": len(calls),
        "total_tokens": None if token_unknown else token_sum,
        "estimated_cost_usd": None if cost_unknown else cost_sum,
        "duration_ms_sum": duration_sum,
    }


def _sum_call_field(calls: list[dict[str, Any]], field: str, *, integer: bool = True) -> Any:
    values = [call.get(field) for call in calls]
    if not values or any(value in (None, "") for value in values):
        return None
    if integer:
        return sum(int(value) for value in values)
    return sum(float(value) for value in values)


def _record_usage_detail(record: Mapping[str, Any]) -> dict[str, Any]:
    calls = [dict(call) for call in list(record.get("model_calls") or [])]
    usage = dict(record.get("usage") or {})
    return {
        "model_calls": len(calls),
        "provider_latency_ms": _sum_call_field(calls, "latency_ms", integer=False),
        "prompt_tokens": _sum_call_field(calls, "prompt_tokens"),
        "completion_tokens": _sum_call_field(calls, "completion_tokens"),
        "cached_tokens": _sum_call_field(calls, "cached_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "estimated_cost_usd": usage.get("estimated_cost_usd"),
    }


def render_ragas_timing_usage_cost_report(
    records: list[dict[str, Any]],
    *,
    input_rows: Optional[list[dict[str, Any]]] = None,
    run_manifest: Optional[Mapping[str, Any]] = None,
) -> tuple[str, str]:
    """Render per-metric RAGAS timing / token / cost details from existing records."""
    run_manifest = dict(run_manifest or {})
    profile = _profile_from_input_rows(input_rows)
    if profile == "unknown":
        input_text = str(run_manifest.get("input") or "").lower()
        if "baseline" in input_text:
            profile = "baseline"
        elif "orchestrated" in input_text:
            profile = "orchestrated"

    by_metric: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        by_metric.setdefault(str(record.get("metric") or ""), []).append(record)
    metric_order = [name for name in METRIC_ALIASES if name in by_metric]
    metric_order.extend(sorted(set(by_metric) - set(metric_order)))

    qid_count = len({str(record.get("qid") or "") for record in records if str(record.get("qid") or "")})
    all_calls = [dict(call) for record in records for call in list(record.get("model_calls") or [])]
    totals = _budget_totals(records)
    duration_sum_ms = sum(float(record.get("duration_ms") or 0.0) for record in records)
    provider_latency_ms = _sum_call_field(all_calls, "latency_ms", integer=False)
    prompt_tokens = _sum_call_field(all_calls, "prompt_tokens")
    completion_tokens = _sum_call_field(all_calls, "completion_tokens")
    cached_tokens = _sum_call_field(all_calls, "cached_tokens")

    lines = [
        f"# RAGAS {profile} Timing-Usage-Cost 明细",
        "",
        "> 本报告直接读取既有 `ragas_evaluation_records.jsonl`。`duration_s` 是单题单指标 RAGAS 任务墙钟耗时，包含 RAGAS 包装与该指标内部多次 evaluator 调用；各任务耗时求和不等同于整批真实墙钟时间。",
        "> `provider_latency_s` 是该任务内部 evaluator 模型调用 latency 的求和，用于区分模型等待与 RAGAS 侧额外开销。Token / Cost 均来自当次已记录的模型调用与定价快照；`cached_tokens` 是 prompt token 的子集，不再额外加到 `total_tokens`。",
        "",
        "## 批次摘要",
        "",
        "| field | value |",
        "| :-- | --: |",
        f"| source_profile | {profile} |",
        f"| 进入评测题数 | {qid_count} |",
        f"| metric_records | {len(records)} |",
        f"| model_calls | {_format_int(totals.get('model_calls'))} |",
        f"| metric_duration_sum_s | {duration_sum_ms / 1000.0:.3f} |",
        f"| provider_latency_sum_s | {_format_ms_as_seconds(provider_latency_ms)} |",
        f"| prompt_tokens | {_format_int(prompt_tokens)} |",
        f"| completion_tokens | {_format_int(completion_tokens)} |",
        f"| cached_tokens | {_format_int(cached_tokens)} |",
        f"| total_tokens | {_format_int(totals.get('total_tokens'))} |",
        f"| estimated_cost_usd | {_format_cost(totals.get('estimated_cost_usd'))} |",
        "",
        "## 各指标资源汇总",
        "",
        "| metric | records | calls | duration_sum_s | median_s | prompt_tokens | completion_tokens | cached_tokens | total_tokens | cost_usd |",
        "| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |",
    ]
    for metric in metric_order:
        rows = by_metric[metric]
        calls = [dict(call) for row in rows for call in list(row.get("model_calls") or [])]
        durations = [float(row.get("duration_ms") or 0.0) for row in rows]
        usage = _metric_usage(rows)
        lines.append(
            f"| {metric} | {len(rows)} | {len(calls)} | {sum(durations) / 1000.0:.3f} | "
            f"{statistics.median(durations) / 1000.0:.3f} | {_format_int(_sum_call_field(calls, 'prompt_tokens'))} | "
            f"{_format_int(_sum_call_field(calls, 'completion_tokens'))} | {_format_int(_sum_call_field(calls, 'cached_tokens'))} | "
            f"{_format_int(usage.get('total_tokens'))} | {_format_cost(usage.get('estimated_cost_usd'))} |"
        )
    lines.extend(
        [
            "",
            "## 逐题逐指标明细",
            "",
            "| qid | metric | score | duration_s | provider_latency_s | calls | prompt_tokens | completion_tokens | cached_tokens | total_tokens | cost_usd |",
            "| :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: |",
        ]
    )
    metric_rank = {metric: index for index, metric in enumerate(metric_order)}
    ordered = sorted(
        records,
        key=lambda row: (str(row.get("qid") or ""), metric_rank.get(str(row.get("metric") or ""), 999)),
    )
    for record in ordered:
        detail = _record_usage_detail(record)
        lines.append(
            f"| {record.get('qid')} | {record.get('metric')} | {_format_score(record.get('score'))} | "
            f"{float(record.get('duration_ms') or 0.0) / 1000.0:.3f} | "
            f"{_format_ms_as_seconds(detail.get('provider_latency_ms'))} | {detail['model_calls']} | "
            f"{_format_int(detail.get('prompt_tokens'))} | {_format_int(detail.get('completion_tokens'))} | "
            f"{_format_int(detail.get('cached_tokens'))} | {_format_int(detail.get('total_tokens'))} | "
            f"{_format_cost(detail.get('estimated_cost_usd'))} |"
        )
    lines.extend(
        [
            "",
            "## 机器底账",
            "",
            "- `ragas_evaluation_records.jsonl`：逐题逐指标的 score、duration、model_calls 与 usage。",
            "- `tables/model_calls.csv`：每一次 evaluator 模型调用的 latency / token / cost。",
            "- `tables/cost_ledger.csv`：逐题逐指标 Token / Cost 分账。",
            "",
        ]
    )
    return profile, "\n".join(lines)


def _format_ms_as_seconds(value: Any) -> str:
    if value in (None, ""):
        return "not_observed"
    try:
        return f"{float(value) / 1000.0:.3f}"
    except (TypeError, ValueError):
        return str(value)


RAGAS_SEGMENT_DISPLAY = {
    "context_precision": "ContextPrecision",
    "faithfulness": "Faithfulness",
    "answer_relevancy": "AnswerRelevancy",
}


def _grade_ragas_metric(metric: str, raw_value: Any) -> str:
    """Project-local A/B/C/D segmentation; round to two decimals first."""
    try:
        value = round(float(raw_value), 2)
    except (TypeError, ValueError):
        return ""

    if metric == "context_precision":
        if value >= 0.90:
            return "A"
        if value >= 0.70:
            return "B"
        if value >= 0.50:
            return "C"
        return "D"

    if metric in {"faithfulness", "answer_relevancy"}:
        if value >= 0.85:
            return "A"
        if value >= 0.70:
            return "B"
        if value >= 0.50:
            return "C"
        return "D"

    return ""


def _dash_qids(qids: list[str]) -> str:
    return "、".join(qids) if qids else "—"


def _build_ragas_segment_data(
    records: list[dict[str, Any]],
    *,
    input_rows: Optional[list[dict[str, Any]]] = None,
    profile: str = "unknown",
) -> dict[str, Any]:
    by_qid: dict[str, dict[str, dict[str, Any]]] = {}
    for record in records:
        qid = str(record.get("qid") or "")
        metric = str(record.get("metric") or "")
        if qid and metric:
            by_qid.setdefault(qid, {})[metric] = record

    qid_order = [str(row.get("qid")) for row in list(input_rows or []) if str(row.get("qid") or "")]
    if not qid_order:
        qid_order = sorted(by_qid)
    else:
        qid_order.extend(sorted(set(by_qid) - set(qid_order)))

    metric_grades = {
        metric: {grade: [] for grade in "ABCD"}
        for metric in RAGAS_SEGMENT_DISPLAY
    }
    row_grades: dict[str, dict[str, str]] = {}

    for qid in qid_order:
        metric_map = by_qid.get(qid, {})
        grades: dict[str, str] = {}
        for metric in RAGAS_SEGMENT_DISPLAY:
            record = metric_map.get(metric)
            grade = ""
            if record and record.get("status") == "ok" and record.get("score") is not None:
                grade = _grade_ragas_metric(metric, record.get("score"))
                if grade:
                    metric_grades[metric][grade].append(qid)
            grades[metric] = grade
        row_grades[qid] = grades

    same_grade_all = {grade: [] for grade in "ABCD"}
    cp_faith_intersection = {grade: [] for grade in "ABCD"}
    for qid in qid_order:
        grades = row_grades[qid]
        cp = grades["context_precision"]
        faith = grades["faithfulness"]
        ar = grades["answer_relevancy"]
        if cp and cp == faith == ar:
            same_grade_all[cp].append(qid)
        if cp and cp == faith:
            cp_faith_intersection[cp].append(qid)

    detail_rows = [
        {"metric": RAGAS_SEGMENT_DISPLAY[metric], "grades": metric_grades[metric]}
        for metric in RAGAS_SEGMENT_DISPLAY
    ]
    detail_rows.extend(
        [
            {"metric": "三指标同档交集", "grades": same_grade_all},
            {"metric": "CP ∩ Faith", "grades": cp_faith_intersection},
        ]
    )
    count_rows = [
        {
            "metric": row["metric"],
            "counts": {grade: len(row["grades"][grade]) for grade in "ABCD"},
        }
        for row in detail_rows
    ]

    return {
        "source_profile": profile,
        "grading_rules": {
            "context_precision": {"A": ">=0.90", "B": "0.70<=x<0.90", "C": "0.50<=x<0.70", "D": "<0.50"},
            "faithfulness": {"A": ">=0.85", "B": "0.70<=x<0.85", "C": "0.50<=x<0.70", "D": "<0.50"},
            "answer_relevancy": {"A": ">=0.85", "B": "0.70<=x<0.85", "C": "0.50<=x<0.70", "D": "<0.50"},
            "implementation_note": "判档前先 round(raw_value, 2)，与报告两位小数判档口径保持一致。",
        },
        "row_grades": row_grades,
        "detail_rows": detail_rows,
        "count_rows": count_rows,
    }


def _render_ragas_segment_section(segment_data: Mapping[str, Any]) -> list[str]:
    lines = [
        "## RAGAS 分段评估",
        "",
        "> A/B/C/D 是本项目用于结果分层与问题定位的工程判档规则，不是 RAGAS 官方等级。实际判档前先将原始分数四舍五入到两位小数。",
        "",
        "### 分段标准",
        "",
        "| 档位 | 简称 | ContextPrecision | Faithfulness | AnswerRelevancy |",
        "| :-: | :--: | :--: | :--: | :--: |",
        "| A | 优 | ≥ 0.90 | ≥ 0.85 | ≥ 0.85 |",
        "| B | 可用 | 0.70–<0.90 | 0.70–<0.85 | 0.70–<0.85 |",
        "| C | 风险观察 | 0.50–<0.70 | 0.50–<0.70 | 0.50–<0.70 |",
        "| D | 重点诊断 | < 0.50 | < 0.50 | < 0.50 |",
        "",
        "### 分段详情",
        "",
        "| 指标 | A 档 | B 档 | C 档 | D 档 |",
        "| :-- | :-- | :-- | :-- | :-- |",
    ]
    for row in list(segment_data.get("detail_rows") or []):
        grades = dict(row.get("grades") or {})
        lines.append(
            f"| {row.get('metric')} | {_dash_qids(list(grades.get('A') or []))} | "
            f"{_dash_qids(list(grades.get('B') or []))} | {_dash_qids(list(grades.get('C') or []))} | "
            f"{_dash_qids(list(grades.get('D') or []))} |"
        )
    lines.extend(
        [
            "",
            "### 分段题数",
            "",
            "| 指标 | A 档 | B 档 | C 档 | D 档 |",
            "| :-- | --: | --: | --: | --: |",
        ]
    )
    for row in list(segment_data.get("count_rows") or []):
        counts = dict(row.get("counts") or {})
        lines.append(
            f"| {row.get('metric')} | {counts.get('A', 0)} | {counts.get('B', 0)} | "
            f"{counts.get('C', 0)} | {counts.get('D', 0)} |"
        )
    lines.append("")
    return lines

def render_ragas_result_report(
    records: list[dict[str, Any]],
    *,
    input_rows: Optional[list[dict[str, Any]]] = None,
    run_manifest: Optional[Mapping[str, Any]] = None,
    prepare_manifest: Optional[Mapping[str, Any]] = None,
) -> tuple[str, str]:
    """Render one human-readable RAGAS result report from existing records."""
    run_manifest = dict(run_manifest or {})
    prepare_manifest = dict(prepare_manifest or {})
    profile = _profile_from_input_rows(input_rows)
    if profile == "unknown":
        input_text = str(run_manifest.get("input") or "").lower()
        if "baseline" in input_text:
            profile = "baseline"
        elif "orchestrated" in input_text:
            profile = "orchestrated"

    by_metric: dict[str, list[dict[str, Any]]] = {}
    by_qid: dict[str, dict[str, dict[str, Any]]] = {}
    for record in records:
        metric = str(record.get("metric") or "")
        qid = str(record.get("qid") or "")
        by_metric.setdefault(metric, []).append(record)
        by_qid.setdefault(qid, {})[metric] = record

    metric_order = [name for name in METRIC_ALIASES if name in by_metric]
    metric_order.extend(sorted(set(by_metric) - set(metric_order)))
    qid_order = [str(row.get("qid")) for row in list(input_rows or []) if str(row.get("qid") or "")]
    if not qid_order:
        qid_order = sorted(by_qid)
    else:
        qid_order.extend(sorted(set(by_qid) - set(qid_order)))

    errors = sum(record.get("status") != "ok" for record in records)
    totals = _budget_totals(records)
    skipped = list(prepare_manifest.get("skipped") or [])
    llm_model = str(run_manifest.get("llm_model") or "not_observed")
    embedding = dict(run_manifest.get("embedding") or {})
    embedding_model = str(embedding.get("model_id") or "not_observed")
    completion_transport = str(run_manifest.get("completion_transport") or "not_observed")
    duration_sum_ms = sum(float(record.get("duration_ms") or 0.0) for record in records)

    lines = [
        f"# RAGAS {profile} 评测结果",
        "",
        "> 本报告只整理既有 `ragas_evaluation_records.jsonl`，不重新执行 RAGAS。分数越高通常越好；RAGAS 是辅助质量评估，不单独作为最终 PASS / FAIL 门禁。",
        "",
        "## 三项指标怎么读",
        "",
        "| metric | 主要看什么 | 读取重点 |",
        "| :-- | :-- | :-- |",
        "| `context_precision` | 检索上下文中与 reference 相关的证据是否更靠前 | 低分优先检查检索排序、无关 context 占位 |",
        "| `faithfulness` | 回答中的陈述能否由 RAGAS 实际使用的 contexts 支撑 | 低分表示回答更可能脱离已给证据；最接近‘基于证据的幻觉’检查 |",
        "| `answer_relevancy` | 回答是否切中用户问题 | 低分表示答非所问或回答重点偏移；不等同于事实正确性 |",
        "",
        "## 批次信息",
        "",
        "| field | value |",
        "| :-- | :-- |",
        f"| source_profile | {profile} |",
        f"| 进入评测题数 | {len(qid_order)} |",
        f"| metric records | {len(records)} |",
        f"| errors | {errors} |",
        f"| llm_model | {llm_model} |",
        f"| embedding_model | {embedding_model} |",
        f"| completion_transport | {completion_transport} |",
        f"| model_calls | {_format_int(totals.get('model_calls'))} |",
        f"| total_tokens | {_format_int(totals.get('total_tokens'))} |",
        f"| estimated_cost_usd | {_format_cost(totals.get('estimated_cost_usd'))} |",
        f"| metric_duration_sum_s | {duration_sum_ms / 1000.0:.3f} |",
        "",
    ]
    if skipped:
        lines.extend(
            [
                "### 未进入 RAGAS 的题",
                "",
                "| qid | reason |",
                "| :-- | :-- |",
            ]
        )
        for item in skipped:
            lines.append(f"| {item.get('qid')} | {_skip_reason_zh(str(item.get('reason') or ''))} |")
        lines.append("")

    lines.extend(
        [
            "## 指标汇总",
            "",
            "| metric | valid | error | mean | median | min | max |",
            "| :-- | --: | --: | --: | --: | --: | --: |",
        ]
    )
    for metric in metric_order:
        rows = by_metric[metric]
        values = [
            float(row["score"])
            for row in rows
            if row.get("status") == "ok" and row.get("score") is not None
        ]
        error_count = sum(row.get("status") != "ok" for row in rows)
        lines.append(
            "| "
            + " | ".join(
                [
                    metric,
                    str(len(values)),
                    str(error_count),
                    _format_score(sum(values) / len(values) if values else None),
                    _format_score(statistics.median(values) if values else None),
                    _format_score(min(values) if values else None),
                    _format_score(max(values) if values else None),
                ]
            )
            + " |"
        )
    lines.append("")

    segment_data = _build_ragas_segment_data(
        records,
        input_rows=input_rows,
        profile=profile,
    )
    lines.extend(_render_ragas_segment_section(segment_data))

    lines.extend(
        [
            "## 低分题索引",
            "",
            "> 这里只按分数从低到高列出每项最低 5 题，帮助快速定位；未设置人为 PASS / FAIL 阈值。",
            "",
            "| metric | lowest 5 |",
            "| :-- | :-- |",
        ]
    )
    for metric in metric_order:
        ranked = sorted(
            (
                (str(row.get("qid")), float(row["score"]))
                for row in by_metric[metric]
                if row.get("status") == "ok" and row.get("score") is not None
            ),
            key=lambda item: (item[1], item[0]),
        )[:5]
        text = "；".join(f"{qid}={score:.4f}" for qid, score in ranked) if ranked else "none"
        lines.append(f"| {metric} | {text} |")
    lines.append("")

    lines.extend(
        [
            "## 逐题三指标",
            "",
            "| qid | context_precision | faithfulness | answer_relevancy |",
            "| :-- | --: | --: | --: |",
        ]
    )
    for qid in qid_order:
        metric_map = by_qid.get(qid, {})
        cells: list[str] = []
        for metric in ("context_precision", "faithfulness", "answer_relevancy"):
            record = metric_map.get(metric)
            if not record:
                cells.append("not_observed")
            elif record.get("status") != "ok":
                error = dict(record.get("error") or {})
                cells.append(f"ERROR:{error.get('error_type') or 'unknown'}")
            else:
                cells.append(_format_score(record.get("score")))
        lines.append(f"| {qid} | {' | '.join(cells)} |")
    lines.append("")

    lines.extend(
        [
            "## 各指标评测资源消耗",
            "",
            "| metric | records | model_calls | duration_sum_s | total_tokens | estimated_cost_usd |",
            "| :-- | --: | --: | --: | --: | --: |",
        ]
    )
    for metric in metric_order:
        rows = by_metric[metric]
        usage = _metric_usage(rows)
        lines.append(
            f"| {metric} | {len(rows)} | {usage['model_calls']} | "
            f"{float(usage['duration_ms_sum']) / 1000.0:.3f} | "
            f"{_format_int(usage['total_tokens'])} | {_format_cost(usage['estimated_cost_usd'])} |"
        )
    lines.append("")

    if errors:
        lines.extend(
            [
                "## 错误记录",
                "",
                "| qid | metric | error_type | message |",
                "| :-- | :-- | :-- | :-- |",
            ]
        )
        for record in records:
            if record.get("status") == "ok":
                continue
            error = dict(record.get("error") or {})
            message = str(error.get("message") or "").replace("|", "\\|").replace("\n", " ")
            lines.append(
                f"| {record.get('qid')} | {record.get('metric')} | "
                f"{error.get('error_type') or 'unknown'} | {message} |"
            )
        lines.append("")

    lines.extend(
        [
            "## 机器底账",
            "",
            "- `ragas_evaluation_records.jsonl`：逐题逐指标事实记录。",
            "- `tables/ragas_results.csv`：逐题逐指标扁平表。",
            "- `tables/model_calls.csv`：每次 evaluator 模型调用。",
            "- `tables/cost_ledger.csv`：逐题逐指标 Token / Cost 分账。",
            "- `tables/ragas_evaluation_segments.json`：A/B/C/D 分段、逐题档位与交集底账。",
            "",
        ]
    )
    return profile, "\n".join(lines)


def _write_reports(
    records: list[dict[str, Any]],
    output_dir: Path,
    *,
    input_rows: Optional[list[dict[str, Any]]] = None,
    run_manifest: Optional[Mapping[str, Any]] = None,
    prepare_manifest: Optional[Mapping[str, Any]] = None,
) -> Path:
    summaries = output_dir / "summaries"
    tables = output_dir / "tables"
    summaries.mkdir(parents=True, exist_ok=True)
    tables.mkdir(parents=True, exist_ok=True)

    profile, report = render_ragas_result_report(
        records,
        input_rows=input_rows,
        run_manifest=run_manifest,
        prepare_manifest=prepare_manifest,
    )
    report_path = summaries / f"RAGAS-{profile}-评测结果.md"
    legacy_path = summaries / "RAGAS-评测总览.md"
    if legacy_path.exists() and legacy_path != report_path:
        legacy_path.unlink()
    report_path.write_text(report, encoding="utf-8")

    timing_profile, timing_report = render_ragas_timing_usage_cost_report(
        records,
        input_rows=input_rows,
        run_manifest=run_manifest,
    )
    timing_path = summaries / f"RAGAS-{timing_profile}-Timing-Usage-Cost明细.md"
    timing_path.write_text(timing_report, encoding="utf-8")

    segment_data = _build_ragas_segment_data(
        records,
        input_rows=input_rows,
        profile=profile,
    )
    (tables / "ragas_evaluation_segments.json").write_text(
        json.dumps(segment_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    calls = [dict(call) for record in records for call in list(record.get("model_calls") or [])]
    result_fields = [
        "qid", "metric", "status", "score", "duration_ms", "source_cer_sha256",
        "answer_sha256", "prompt_sha256", "model_call_count", "total_tokens", "estimated_cost_usd", "error_type",
    ]
    result_rows = []
    for record in records:
        usage = dict(record.get("usage") or {})
        error = dict(record.get("error") or {})
        result_rows.append(
            {
                "qid": record.get("qid"),
                "metric": record.get("metric"),
                "status": record.get("status"),
                "score": record.get("score"),
                "duration_ms": record.get("duration_ms"),
                "source_cer_sha256": record.get("source_cer_sha256"),
                "answer_sha256": record.get("answer_sha256"),
                "prompt_sha256": record.get("prompt_sha256"),
                "model_call_count": len(record.get("model_calls") or []),
                "total_tokens": usage.get("total_tokens"),
                "estimated_cost_usd": usage.get("estimated_cost_usd"),
                "error_type": error.get("error_type"),
            }
        )
    with (tables / "ragas_results.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=result_fields)
        writer.writeheader()
        writer.writerows(result_rows)
    call_fields = sorted({key for call in calls for key in call}) or ["qid", "call_id"]
    with (tables / "model_calls.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=call_fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(calls)
    with (tables / "cost_ledger.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "qid",
                "metric",
                "model_call_count",
                "total_tokens",
                "total_tokens_observed_sum",
                "total_tokens_unknown_call_count",
                "estimated_cost_usd",
                "estimated_cost_usd_observed_sum",
                "cost_observation",
            ],
        )
        writer.writeheader()
        for record in records:
            usage = dict(record.get("usage") or {})
            writer.writerow(
                {
                    "qid": record.get("qid"),
                    "metric": record.get("metric"),
                    "model_call_count": len(record.get("model_calls") or []),
                    "total_tokens": usage.get("total_tokens"),
                    "total_tokens_observed_sum": usage.get("total_tokens_observed_sum"),
                    "total_tokens_unknown_call_count": usage.get("total_tokens_unknown_call_count"),
                    "estimated_cost_usd": usage.get("estimated_cost_usd"),
                    "estimated_cost_usd_observed_sum": usage.get("estimated_cost_usd_observed_sum"),
                    "cost_observation": usage.get("cost_observation"),
                }
            )
    return report_path


def main() -> int:
    args = arguments()
    if not args.allow_provider_calls:
        raise SystemExit("Refusing RAGAS provider calls: add --allow-provider-calls after a one-case review")
    if not args.confirm_external_evidence_egress:
        raise SystemExit(
            "Refusing RAGAS evidence egress: add --confirm-external-evidence-egress only after approving external disclosure"
        )
    if args.limit is not None and args.limit <= 0:
        raise SystemExit("--limit must be positive")
    rows = _load_rows(args.input)
    wanted = {str(item) for item in list(args.ids or [])}
    if wanted:
        known = {str(row.get("qid")) for row in rows}
        missing = sorted(wanted - known)
        if missing:
            raise SystemExit(f"unknown RAGAS qid(s): {', '.join(missing)}")
        rows = [row for row in rows if str(row.get("qid")) in wanted]
    if args.limit is not None:
        rows = rows[: args.limit]
    if not rows:
        raise SystemExit("no RAGAS rows selected")

    records_path = args.output_dir / "ragas_evaluation_records.jsonl"
    if args.output_dir.exists() and any(args.output_dir.iterdir()) and not args.resume:
        raise SystemExit(f"output directory is not empty; use a new path or --resume: {args.output_dir}")
    existing = _load_existing(records_path) if args.resume else []
    metric_names = _metric_names(args)
    input_sha256 = _sha256_file(args.input)
    embedding_binding = _embedding_binding(args.embedding_model, args.embedding_model_id)
    evaluation_config_sha256 = stable_sha256(
        {
            "input_sha256": input_sha256,
            "metrics": metric_names,
            "llm_model": args.llm_model,
            "api_base_url_sha256": hashlib.sha256(
                str(args.api_base_url).encode("utf-8")
            ).hexdigest(),
            "embedding": embedding_binding,
            "timeout": args.timeout,
            "completion_transport": _completion_transport(args.llm_model, args.api_base_url),
        }
    )
    allowed_qids = {str(row.get("qid")) for row in rows}
    seen_existing: set[tuple[str, str, str]] = set()
    for record in existing:
        if record.get("evaluation_config_sha256") != evaluation_config_sha256:
            raise SystemExit(
                "resume checkpoint evaluation configuration differs from the current input/model/metric selection"
            )
        if str(record.get("qid")) not in allowed_qids:
            raise SystemExit("resume checkpoint contains a qid outside the current selection")
        if str(record.get("metric")) not in metric_names:
            raise SystemExit("resume checkpoint contains a metric outside the current selection")
        key = (
            str(record.get("qid")),
            str(record.get("metric")),
            str(record.get("source_cer_sha256")),
        )
        if key in seen_existing:
            raise SystemExit("resume checkpoint contains duplicate evaluation records")
        seen_existing.add(key)
    complete_keys = {
        (str(row.get("qid")), str(row.get("metric")), str(row.get("source_cer_sha256")))
        for row in existing
    }

    pending_count = sum(
        1
        for row in rows
        for metric_name in metric_names
        if not (
            metric_name == "context_precision"
            and row.get("enable_reference_based_metrics") is False
        )
        and (
            str(row.get("qid")),
            metric_name,
            str(row.get("source_cer_sha256")),
        )
        not in complete_keys
    )
    if pending_count:
        budget_reason = _preflight_budget_reason(existing, args)
        if budget_reason:
            raise SystemExit(f"Refusing resume: {budget_reason}")

    callback = _build_callback(args.llm_model, args.api_base_url)
    Dataset, evaluate, evaluator_llm, embeddings, run_config = _load_runtime(args, callback)
    metrics = _metrics(args)
    outputs = list(existing)
    budget_exceeded = False
    total_tasks = sum(
        1
        for row in rows
        for metric, _ in metrics
        if not (metric == "context_precision" and row.get("enable_reference_based_metrics") is False)
    )
    task_index = 0
    for row in rows:
        qid = str(row["qid"])
        for metric_name, metric in metrics:
            if metric_name == "context_precision" and row.get("enable_reference_based_metrics") is False:
                continue
            task_index += 1
            key = (qid, metric_name, str(row.get("source_cer_sha256")))
            if key in complete_keys:
                print(f"[{task_index:03d}/{total_tasks:03d}] {qid}/{metric_name} skipped (resume)", flush=True)
                continue
            callback.set_context(qid, metric_name)
            calls_before = len(callback.calls)
            started = time.perf_counter()
            error: Optional[dict[str, Any]] = None
            score: Optional[float] = None
            try:
                result = evaluate(
                    Dataset.from_list([_dataset_row(row)]),
                    metrics=[metric],
                    llm=evaluator_llm,
                    embeddings=embeddings,
                    raise_exceptions=False,
                    show_progress=False,
                    run_config=run_config,
                )
                score = _score(result, metric_name)
                if score is None:
                    error = {"error_type": "MetricScoreNotObserved", "message": "metric returned NaN or no score column"}
            except Exception as exc:  # noqa: BLE001
                error = {"error_type": type(exc).__name__, "message": str(exc)}
            duration_ms = float((time.perf_counter() - started) * 1000.0)
            raw_calls = callback.calls[calls_before:]
            priced_calls, usage = price_model_calls(raw_calls)
            record = {
                "schema_version": "1.0.0",
                "evaluation_record_id": stable_sha256(
                    {
                        "qid": qid,
                        "metric": metric_name,
                        "source_cer_sha256": row.get("source_cer_sha256"),
                        "evaluation_config_sha256": evaluation_config_sha256,
                    }
                )[:24],
                "evaluation_config_sha256": evaluation_config_sha256,
                "qid": qid,
                "metric": metric_name,
                "status": "ok" if error is None else "error",
                "score": score,
                "duration_ms": duration_ms,
                "source_cer_sha256": row.get("source_cer_sha256"),
                "answer_sha256": row.get("answer_sha256"),
                "prompt_sha256": row.get("prompt_sha256"),
                "model_calls": priced_calls,
                "usage": usage,
                "error": error,
            }
            outputs.append(record)
            complete_keys.add(key)
            _atomic_write(records_path, outputs)
            print(
                f"[{task_index:03d}/{total_tasks:03d}] {qid}/{metric_name} "
                f"status={record['status']} score={score} calls={len(priced_calls)} "
                f"tokens={usage.get('total_tokens')} cost={usage.get('estimated_cost_usd')}",
                flush=True,
            )
            totals = _budget_totals(outputs)
            if args.max_model_calls is not None and int(totals["model_calls"] or 0) > args.max_model_calls:
                budget_exceeded = True
                print("budget stop: model-call limit exceeded", flush=True)
                break
            if args.max_total_tokens is not None:
                if totals["total_tokens"] is None:
                    budget_exceeded = True
                    print("budget stop: total tokens are not fully observed", flush=True)
                    break
                if int(totals["total_tokens"]) > args.max_total_tokens:
                    budget_exceeded = True
                    print("budget stop: total-token limit exceeded", flush=True)
                    break
            if args.max_cost_usd is not None:
                if totals["estimated_cost_usd"] is None:
                    budget_exceeded = True
                    print("budget stop: cost is not fully observed", flush=True)
                    break
                if float(totals["estimated_cost_usd"]) > args.max_cost_usd:
                    budget_exceeded = True
                    print("budget stop: cost limit exceeded", flush=True)
                    break
        if budget_exceeded:
            break

    _atomic_write(records_path, outputs)
    totals = _budget_totals(outputs)
    manifest = {
        "schema_version": "1.0.0",
        "input": str(args.input),
        "input_sha256": input_sha256,
        "evaluation_config_sha256": evaluation_config_sha256,
        "llm_model": args.llm_model,
        "completion_transport": _completion_transport(args.llm_model, args.api_base_url),
        "embedding": embedding_binding,
        "metrics": metric_names,
        "selected_qids": [str(row.get("qid")) for row in rows],
        "records": len(outputs),
        "source_cer_sha256_count": len(
            {str(row.get("source_cer_sha256") or "") for row in rows}
        ),
        "totals": totals,
        "provider_billing_reconciled": False,
        "budget_exceeded": budget_exceeded,
    }
    (args.output_dir / "ragas_run_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    prepare_manifest_path = args.input.parent / "ragas_prepare_manifest.json"
    prepare_manifest = (
        json.loads(prepare_manifest_path.read_text(encoding="utf-8"))
        if prepare_manifest_path.exists()
        else {}
    )
    report_path = _write_reports(
        outputs,
        args.output_dir,
        input_rows=rows,
        run_manifest=manifest,
        prepare_manifest=prepare_manifest,
    )
    errors = sum(record.get("status") != "ok" for record in outputs)
    print(f"records: {records_path}", flush=True)
    print(f"report: {report_path}", flush=True)
    timing_report_path = report_path.parent / f"RAGAS-{_profile_from_input_rows(rows)}-Timing-Usage-Cost明细.md"
    if timing_report_path.exists():
        print(f"timing/usage/cost: {timing_report_path}", flush=True)
    print(f"completed: {len(outputs)}; errors: {errors}; budget_exceeded: {budget_exceeded}", flush=True)
    return 2 if errors or budget_exceeded else 0


if __name__ == "__main__":
    raise SystemExit(main())
