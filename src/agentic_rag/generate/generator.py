"""
文件作用：
把检索结果变成最终 Answer：
1）evidence_check（generator 层兜底，避免 rr 异常时失控）；
2）build_prompt；
3）调用 LLM；
4）解析 citations（可选）；
5）引用 fallback（保证可追溯）；
6）输出 Answer（types.py 契约）；
7）统一补齐拒答/观测字段，和 pipeline 层使用同一套 flags 键名。

整体结构：
1. GeneratorConfig：生成配置；
2. RAGGenerator：主生成器；
3. _reject：统一拒答输出；
4. _build_retrieval_signal_flags：构造最小检索信号（generator 层兜底用）；
5. _build_usage_flags：构造 used/citation 相关观测字段；
6. generate：主入口。
"""

from __future__ import annotations  # 启用未来注解，避免前向引用问题。  # noqa: E501

import re  # 用于解析 LLM 输出中的引用格式。  # noqa: E501
import time  # 用于记录耗时。  # noqa: E501
from dataclasses import dataclass  # 用于定义配置对象。  # noqa: E501
from pathlib import Path  # 用于读取 prompt 文件。  # noqa: E501
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Tuple  # 用于类型标注。  # noqa: E501

from agentic_rag.observability.model_identity import ModelIdentity  # 模型身份结构。  # noqa: E501
from agentic_rag.observability.observability_record import ModelCallRecord  # 模型调用观测结构。  # noqa: E501
from agentic_rag.types import Answer, Chunk, Citation, RetrievalResult  # 稳定类型契约。  # noqa: E501
from agentic_rag.execution.snapshots import build_evidence_snapshot, build_prompt_snapshot

if TYPE_CHECKING:
    from agentic_rag.llm.client import OllamaClient


_CIT_RE: re.Pattern[str] = re.compile(r"\[E(?P<index>[1-9]\d*)\]")

_REFUSAL_TEMPLATE: str = (  # 固定拒答模板。  # noqa: E501
    "我在当前语料中找不到足够证据来回答这个问题。\n"  # 第一行。  # noqa: E501
    "请提供更多上下文，或把问题限定在已提供的文档范围内。"  # 第二行。  # noqa: E501
)  # 结束模板。  # noqa: E501

_REFUSAL_BLOCK_RE: re.Pattern[str] = re.compile(  # 严格匹配完整拒答块。  # noqa: E501
    r"^\s*---\s*\n"  # 开始分隔符。  # noqa: E501
    r"我在当前语料中找不到足够证据来回答这个问题。\n"  # 第 1 行拒答。  # noqa: E501
    r"请提供更多上下文，或把问题限定在已提供的文档范围内。\n"  # 第 2 行拒答。  # noqa: E501
    r"\s*---\s*\n",  # 结束分隔符。  # noqa: E501
    re.MULTILINE,  # 多行模式。  # noqa: E501
)  # 结束正则。  # noqa: E501

_ANSWER_HEADER_RE: re.Pattern[str] = re.compile(  # 清洗开头的 Answer 标题。  # noqa: E501
    r"^\s*(?:#+\s*)?(?:\*\*)?Answer(?:\*\*)?(?:\s*[:：])?\s*\n?",  # 兼容 Answer / **Answer** 标题。  # noqa: E501
    re.IGNORECASE,  # 忽略大小写。  # noqa: E501
)  # 结束正则。  # noqa: E501

_CITATIONS_TAIL_RE: re.Pattern[str] = re.compile(  # 清洗正文尾部自带的 Citations 段。  # noqa: E501
    r"\n\s*(?:#+\s*)?(?:\*\*)?Citations(?:\*\*)?(?:\s*[:：])?\s*(?:\n.*)?$",  # 兼容 Citations / **Citations** 段。  # noqa: E501
    re.IGNORECASE | re.DOTALL,  # 忽略大小写 + 跨行匹配。  # noqa: E501
)  # 结束正则。  # noqa: E501


@dataclass(frozen=True)  # 配置冻结，便于回归一致性。  # noqa: E501
class GeneratorConfig:  # 生成配置。  # noqa: E501
    min_evidence_chunks: int = 2  # 证据门槛：<2 则拒答。  # noqa: E501
    max_chunks_in_prompt: int = 5  # prompt 最多放多少 chunks。  # noqa: E501
    max_chars_per_chunk: Optional[int] = None  # None 表示保留完整 chunk。  # noqa: E501
    prompt_relpath: str = "prompts/rag_prompt.txt"  # prompt 相对 agentic_rag 包路径。  # noqa: E501
    citation_fallback_n: int = 0  # 终版默认禁止系统自动补 citation。  # noqa: E501


class RAGGenerator:  # RAG 生成器。  # noqa: E501
    def __init__(self, llm: Optional["OllamaClient"] = None, cfg: Optional[GeneratorConfig] = None) -> None:  # 注入依赖。  # noqa: E501
        if llm is None:
            from agentic_rag.llm.client import OllamaClient

            llm = OllamaClient()
        self._llm = llm  # 默认使用本地 Ollama。  # noqa: E501
        self._cfg: GeneratorConfig = cfg or GeneratorConfig()  # 使用默认配置。  # noqa: E501
        self._prompt_template: str = self._load_prompt_template()  # 启动时加载模板。  # noqa: E501

    def _load_prompt_template(self) -> str:  # 加载 rag_prompt.txt。  # noqa: E501
        base_dir: Path = Path(__file__).resolve().parent.parent  # 定位 agentic_rag/ 目录。  # noqa: E501
        prompt_path: Path = (base_dir / self._cfg.prompt_relpath).resolve()  # 拼接 prompt 路径。  # noqa: E501
        return prompt_path.read_text(encoding="utf-8")  # 读取文本。  # noqa: E501

    def _ordered_unique_source_ids(self, chunks: Sequence[Chunk]) -> List[str]:  # 按原顺序去重 source_id。  # noqa: E501
        out: List[str] = []  # 初始化结果列表。  # noqa: E501
        for chunk in chunks:  # 遍历 chunks。  # noqa: E501
            source_id: str = str(chunk.source_id)  # 读取 source_id。  # noqa: E501
            if source_id not in out:  # 若尚未出现。  # noqa: E501
                out.append(source_id)  # 写入结果。  # noqa: E501
        return out  # 返回去重后的 source_id 列表。  # noqa: E501

    def _ordered_unique_strs(self, values: Sequence[str]) -> List[str]:  # 按原顺序去重字符串列表。  # noqa: E501
        out: List[str] = []  # 初始化输出列表。  # noqa: E501
        for value in values:  # 遍历输入值。  # noqa: E501
            value_str: str = str(value)  # 转成字符串。  # noqa: E501
            if value_str not in out:  # 若尚未出现。  # noqa: E501
                out.append(value_str)  # 追加到结果。  # noqa: E501
        return out  # 返回去重结果。  # noqa: E501

    def _build_retrieval_signal_flags(self, rr: Optional[RetrievalResult]) -> Dict[str, Any]:  # 构造最小检索信号。  # noqa: E501
        if rr is None:  # 若 rr 为空。  # noqa: E501
            return {  # 返回空 rr 的最小结构。  # noqa: E501
                "evidence_count": 0,  # 没有证据。  # noqa: E501
                "min_evidence_required": int(self._cfg.min_evidence_chunks),  # 最小证据门槛。  # noqa: E501
                "top1_score": None,  # top1_score。  # noqa: E501
                "top2_score": None,  # top2_score。  # noqa: E501
                "diff_top1_top2": None,  # 差值。  # noqa: E501
                "unique_source_count": 0,  # 去重来源数。  # noqa: E501
                "unique_source_ids": [],  # 去重来源列表。  # noqa: E501
            }  # 结束返回。  # noqa: E501

        evidence_count: int = int(len(rr.chunks or []))  # 统计 evidence_count。  # noqa: E501
        top1_score: Optional[float] = float(rr.scores[0]) if len(rr.scores) >= 1 else None  # 读取 top1_score。  # noqa: E501
        top2_score: Optional[float] = float(rr.scores[1]) if len(rr.scores) >= 2 else None  # 读取 top2_score。  # noqa: E501
        diff_top1_top2: Optional[float] = None  # 初始化差值。  # noqa: E501
        if top1_score is not None and top2_score is not None:  # 若 top1 与 top2 都存在。  # noqa: E501
            diff_top1_top2 = float(top1_score - top2_score)  # 计算差值。  # noqa: E501
        unique_source_ids: List[str] = self._ordered_unique_source_ids(list(rr.chunks or []))  # 计算去重来源列表。  # noqa: E501
        return {  # 返回统一信号字典。  # noqa: E501
            "evidence_count": int(evidence_count),  # 当前证据条数。  # noqa: E501
            "min_evidence_required": int(self._cfg.min_evidence_chunks),  # 当前最小门槛。  # noqa: E501
            "top1_score": top1_score,  # top1_score。  # noqa: E501
            "top2_score": top2_score,  # top2_score。  # noqa: E501
            "diff_top1_top2": diff_top1_top2,  # diff_top1_top2。  # noqa: E501
            "unique_source_count": int(len(unique_source_ids)),  # 去重来源数量。  # noqa: E501
            "unique_source_ids": unique_source_ids,  # 去重来源列表。  # noqa: E501
        }  # 结束返回。  # noqa: E501

    def _build_usage_flags(self, used_chunks: Sequence[Chunk], citations: Sequence[Citation]) -> Dict[str, Any]:  # 构造 used/citation 相关观测字段。  # noqa: E501
        used_chunk_ids: List[str] = [str(chunk.chunk_id) for chunk in used_chunks]  # used chunk_id 列表。  # noqa: E501
        used_chunk_source_ids: List[str] = self._ordered_unique_strs(  # used source_id 去重列表。  # noqa: E501
            [str(chunk.source_id) for chunk in used_chunks]
        )  # used source_id 计算结束。  # noqa: E501
        citation_source_ids: List[str] = self._ordered_unique_strs(  # citation source_id 去重列表。  # noqa: E501
            [str(citation.source_id) for citation in citations]
        )  # citation source_id 计算结束。  # noqa: E501
        return {  # 返回 usage flags。  # noqa: E501
            "used_chunk_ids": used_chunk_ids,  # 实际参与生成的 chunk_id 列表。  # noqa: E501
            "used_chunk_source_ids": used_chunk_source_ids,  # 实际参与生成的 source_id 列表。  # noqa: E501
            "citation_source_ids": citation_source_ids,  # 最终输出 citations 对应的 source_id 列表（去重版）。  # noqa: E501
            "has_citation": bool(len(citations) > 0),  # 是否有最终有效引用。  # noqa: E501
            "evidence_hit": bool(len(used_chunks) > 0),  # 是否命中过至少一个证据 chunk。  # noqa: E501
        }  # 返回结束。  # noqa: E501

    def _build_generator_observability_flags(  # 构造 generator 模型身份与调用观测字段。  # noqa: E501
        self,  # 实例自身。  # noqa: E501
        token_usage: Dict[str, Any],  # token_usage / metadata。  # noqa: E501
        llm_generate_ms: float,  # LLM 调用耗时。  # noqa: E501
        error_type: Optional[str] = None,  # 异常类型。  # noqa: E501
        api_error: bool = False,  # 是否 API 错误。  # noqa: E501
        timeout: bool = False,  # 是否 timeout。  # noqa: E501
    ) -> Dict[str, Any]:  # 返回 flags。  # noqa: E501
        usage: Dict[str, Any] = dict(token_usage or {})  # 复制 usage，避免原地修改。  # noqa: E501
        if not usage:  # 若没有 token_usage。  # noqa: E501
            usage = self._llm.metadata()  # 使用 client metadata 兜底。  # noqa: E501

        identity = ModelIdentity.from_metadata(usage)  # 构造标准 ModelIdentity。  # noqa: E501
        model_call = ModelCallRecord.from_token_usage(  # 构造标准 ModelCallRecord。  # noqa: E501
            role="generator",  # 调用角色。  # noqa: E501
            token_usage=usage,  # token 与模型元信息。  # noqa: E501
            latency_ms=float(llm_generate_ms),  # LLM 调用耗时。  # noqa: E501
            error_type=error_type,  # 异常类型。  # noqa: E501
            api_error=bool(api_error),  # API 错误标记。  # noqa: E501
            timeout=bool(timeout),  # timeout 标记。  # noqa: E501
        )  # 构造结束。  # noqa: E501

        return {  # 返回稳定 flags。  # noqa: E501
            "generator_identity": identity.to_dict(),  # generator 模型身份。  # noqa: E501
            "generator_model_call": model_call.to_dict(),  # generator 调用记录。  # noqa: E501
        }  # 返回结束。  # noqa: E501

    def _build_generator_error_flags(self, exc: BaseException, llm_generate_ms: float) -> Dict[str, Any]:  # 构造 generator 异常观测字段。  # noqa: E501
        flags = self._build_generator_observability_flags(  # 先构造标准观测字段。  # noqa: E501
            token_usage=self._llm.metadata(),  # 异常时使用 client metadata。  # noqa: E501
            llm_generate_ms=float(llm_generate_ms),  # LLM 调用耗时。  # noqa: E501
            error_type=type(exc).__name__,  # 异常类型。  # noqa: E501
            api_error=True,  # 标记 API/LLM 调用异常。  # noqa: E501
            timeout="timeout" in type(exc).__name__.lower(),  # 粗粒度 timeout 标记。  # noqa: E501
        )  # 构造结束。  # noqa: E501
        flags.update(  # 补充易读错误字段。  # noqa: E501
            {  # 开始补充。  # noqa: E501
                "generator_error_type": type(exc).__name__,  # generator 异常类型。  # noqa: E501
                "generator_error_message": str(exc),  # generator 异常信息。  # noqa: E501
            }  # 结束补充。  # noqa: E501
        )  # update 结束。  # noqa: E501
        return flags  # 返回 flags。  # noqa: E501

    def _reject(  # 统一构造拒答 Answer。  # noqa: E501
        self,  # 实例自身。  # noqa: E501
        query: str,  # query。  # noqa: E501
        timing_ms: float,  # 总耗时。  # noqa: E501
        reason: str,  # 拒答原因。  # noqa: E501
        used_chunks: Optional[Sequence[Chunk]] = None,  # used_chunks。  # noqa: E501
        retrieval_ms: float = 0.0,  # 检索耗时。  # noqa: E501
        generation_ms: float = 0.0,  # 生成耗时。  # noqa: E501
        llm_generate_ms: float = 0.0,  # LLM 调用耗时。  # noqa: E501
        signal_flags: Optional[Dict[str, Any]] = None,  # 检索信号。  # noqa: E501
    ) -> Answer:  # 返回 Answer。  # noqa: E501
        flags: Dict[str, Any] = dict(signal_flags or {})  # 先复制检索信号。  # noqa: E501
        usage_flags: Dict[str, Any] = self._build_usage_flags(  # 构造 usage flags。  # noqa: E501
            used_chunks=list(used_chunks or []),  # used_chunks。  # noqa: E501
            citations=[],  # 拒答时 citations 为空。  # noqa: E501
        )  # usage flags 构造结束。  # noqa: E501
        flags.update(usage_flags)  # 先补 usage flags。  # noqa: E501
        flags.update(  # 统一补充拒答字段。  # noqa: E501
            {  # 开始补充。  # noqa: E501
                "refused": True,  # 标记拒答。  # noqa: E501
                "refuse_reason": str(reason),  # 统一拒答原因字段。  # noqa: E501
                "reason": str(reason),  # 兼容旧字段。  # noqa: E501
                "citation_hallucination": False,  # 拒答时不做引用幻觉判定。  # noqa: E501
                "hallucinated_citations": [],  # 拒答时幻觉引用为空。  # noqa: E501
                "missing_citations_fallback": False,  # 拒答时不涉及 fallback。  # noqa: E501
            }  # 结束补充。  # noqa: E501
        )  # update 结束。  # noqa: E501
        return Answer(  # 构造 Answer。  # noqa: E501
            query=str(query),  # query。  # noqa: E501
            answer_text=str(_REFUSAL_TEMPLATE),  # 拒答正文。  # noqa: E501
            citations=[],  # 拒答时 citations 为空。  # noqa: E501
            used_chunks=list(used_chunks or []),  # 保留 used_chunks。  # noqa: E501
            timing_ms=float(timing_ms),  # 总耗时。  # noqa: E501
            retrieval_ms=float(retrieval_ms),  # 检索耗时。  # noqa: E501
            generation_ms=float(generation_ms),  # 生成耗时。  # noqa: E501
            llm_generate_ms=float(llm_generate_ms),  # LLM 调用耗时。  # noqa: E501
            token_usage={},  # token_usage 为空。  # noqa: E501
            flags=flags,  # flags。  # noqa: E501
        )  # 结束 Answer。  # noqa: E501

    def _chunk_text_for_prompt(self, chunk: Chunk) -> str:  # 返回真正进入 prompt 的 chunk 文本。  # noqa: E501
        text: str = str(chunk.text)  # 读取 chunk 文本。  # noqa: E501
        limit = self._cfg.max_chars_per_chunk  # 读取显式字符上限。  # noqa: E501
        if limit is not None and int(limit) > 0 and len(text) > int(limit):  # 若过长则截断。  # noqa: E501
            text = text[: int(limit)] + "…"  # 截断并加省略号。  # noqa: E501
        return text  # 返回 prompt 中实际使用的文本。  # noqa: E501

    def _metadata_first(self, chunk: Chunk, keys: Sequence[str]) -> str:  # 从 metadata 中按候选 key 读取字符串。  # noqa: E501
        metadata: Dict[str, Any] = dict(getattr(chunk, "metadata", {}) or {})  # 读取 metadata。  # noqa: E501
        for key in keys:  # 遍历候选 key。  # noqa: E501
            value: Any = metadata.get(key)  # 读取值。  # noqa: E501
            if value not in (None, "", [], {}):  # 跳过空值。  # noqa: E501
                return str(value)  # 返回字符串。  # noqa: E501
        return ""  # 缺失时返回空字符串。  # noqa: E501

    def _build_generation_context(self, rr: RetrievalResult) -> Dict[str, Any]:  # 记录真正送进 generator prompt 的 chunks。  # noqa: E501
        chunks: Sequence[Chunk] = list(rr.chunks or [])  # 当前候选 chunks。  # noqa: E501
        scores: Sequence[float] = list(rr.scores or [])  # 当前对齐 scores。  # noqa: E501
        limit: int = min(len(chunks), int(self._cfg.max_chunks_in_prompt))  # prompt 实际 chunk 数。  # noqa: E501
        rerank_applied: bool = bool(getattr(rr, "rerank_applied", False))  # 是否已经 rerank。  # noqa: E501
        rerank_scores: Sequence[float] = list(getattr(rr, "rerank_scores", []) or [])  # rerank scores。  # noqa: E501
        score_type: str = str(getattr(rr, "score_type", "vector_similarity") or "vector_similarity")  # 当前最终排序分数语义。  # noqa: E501

        chunks_in_prompt: List[Dict[str, Any]] = []  # 初始化输出。  # noqa: E501
        for i in range(limit):  # 只遍历真正进入 prompt 的 chunks。  # noqa: E501
            chunk: Chunk = chunks[i]  # 当前 chunk。  # noqa: E501
            score_value: Optional[float] = float(scores[i]) if i < len(scores) else None  # 当前 score。  # noqa: E501
            rerank_score: Optional[float] = None  # 初始化 rerank_score。  # noqa: E501
            vector_score: Optional[float] = None  # 仅 vector_similarity 路径填写。  # noqa: E501
            rrf_score: Optional[float] = None  # 仅 RRF 路径填写。  # noqa: E501
            if rerank_applied:  # rerank 后 rr.scores 通常已是 rerank score。  # noqa: E501
                rerank_score = float(rerank_scores[i]) if i < len(rerank_scores) else score_value  # 读取 rerank score。  # noqa: E501
            elif score_type == "rrf":  # RRF 融合后的 score 不能伪装成 vector similarity。  # noqa: E501
                rrf_score = score_value  # 记录真实 RRF score。  # noqa: E501
            elif score_type == "vector_similarity":  # Dense 直出时才记录 vector score。  # noqa: E501
                vector_score = score_value  # 记录 cosine/vector similarity。  # noqa: E501
            prompt_text: str = self._chunk_text_for_prompt(chunk)  # prompt 中实际文本。  # noqa: E501
            metadata: Dict[str, Any] = dict(getattr(chunk, "metadata", {}) or {})  # 读取 metadata。  # noqa: E501
            acl: Dict[str, Any] = dict(metadata.get("acl") or {}) if isinstance(metadata.get("acl"), dict) else {}  # 读取 ACL。  # noqa: E501
            chunks_in_prompt.append(  # 追加记录。  # noqa: E501
                {  # 开始 chunk 记录。  # noqa: E501
                    "chunk_id": str(chunk.chunk_id),  # chunk_id。  # noqa: E501
                    "source_id": str(chunk.source_id),  # source_id。  # noqa: E501
                    "offset_start": int(chunk.offset_start),
                    "offset_end": int(chunk.offset_end),
                    "evidence_marker": f"E{i + 1}",
                    "source_path": self._metadata_first(  # source_path。  # noqa: E501
                        chunk, ["source_path", "path", "file_path", "relpath", "doc_path"]
                    ),  # source_path 结束。  # noqa: E501
                    "section_path": self._metadata_first(  # section_path。  # noqa: E501
                        chunk, ["section_path", "heading_path", "headers", "section", "title"]
                    ),  # section_path 结束。  # noqa: E501
                    "rank": int(i + 1),  # prompt 内 rank，从 1 开始。  # noqa: E501
                    "score_type": score_type,  # 最终排序分数语义。  # noqa: E501
                    "vector_score": vector_score,  # Dense vector score。  # noqa: E501
                    "rrf_score": rrf_score,  # RRF 融合分数。  # noqa: E501
                    "rerank_score": rerank_score,  # rerank_score。  # noqa: E501
                    "char_len": int(len(prompt_text)),  # 实际送入 prompt 的文本长度。  # noqa: E501
                    "acl": {  # prompt chunk 的 ACL 摘要。  # noqa: E501
                        "visibility": acl.get("visibility"),  # 可见性。  # noqa: E501
                        "source_id": acl.get("source_id") or str(chunk.source_id),  # ACL source_id。  # noqa: E501
                    },  # ACL 摘要结束。  # noqa: E501
                    "text": prompt_text,  # 实际送入 prompt 的文本。  # noqa: E501
                }  # 结束 chunk 记录。  # noqa: E501
            )  # append 结束。  # noqa: E501

        return {  # 返回 generation_context。  # noqa: E501
            "max_chunks_in_prompt": int(self._cfg.max_chunks_in_prompt),  # 配置上限。  # noqa: E501
            "max_chars_per_chunk": int(self._cfg.max_chars_per_chunk) if self._cfg.max_chars_per_chunk is not None else None,  # 单 chunk 截断上限。  # noqa: E501
            "prompt_context_chunk_count": int(len(chunks_in_prompt)),  # 实际进入 prompt 的 chunk 数。  # noqa: E501
            "prompt_context_char_count": int(sum(item["char_len"] for item in chunks_in_prompt)),  # 实际文本总长度。  # noqa: E501
            "prompt_chunk_ids": [item["chunk_id"] for item in chunks_in_prompt],  # prompt chunk ids。  # noqa: E501
            "prompt_sources": self._ordered_unique_strs([item["source_id"] for item in chunks_in_prompt]),  # prompt sources。  # noqa: E501
            "acl_checked": bool(getattr(rr, "acl_checked", False)),  # 是否经过 ACL filter。  # noqa: E501
            "prompt_chunks_allowed_only": bool(getattr(rr, "acl_checked", False)),  # prompt chunk 是否来自 ACL allowed 集合。  # noqa: E501
            "citations_allowed_only": bool(getattr(rr, "acl_checked", False)),  # citations 只能来自 used chunks。  # noqa: E501
            "prompt_chunk_acl": [item.get("acl", {}) for item in chunks_in_prompt],  # prompt ACL 摘要。  # noqa: E501
            "chunks_in_prompt": chunks_in_prompt,  # 完整 prompt chunk 记录。  # noqa: E501
        }  # 返回结束。  # noqa: E501

    def _format_chunk_for_prompt(self, chunk: Chunk, score: Optional[float], marker: str) -> str:  # chunk -> prompt block。  # noqa: E501
        text: str = self._chunk_text_for_prompt(chunk)  # 使用与 generation_context 相同的截断逻辑。  # noqa: E501
        header: str = (  # header 写最小可定位字段。  # noqa: E501
            f"[{marker}]\n"
            f"- source_id: {chunk.source_id}\n"  # source_id。  # noqa: E501
            f"  chunk_id: {chunk.chunk_id}\n"  # chunk_id。  # noqa: E501
            f"  offset_start: {chunk.offset_start}\n"  # offset_start。  # noqa: E501
        )  # header 结束。  # noqa: E501
        body: str = f"  text:\n{text}\n"  # 正文部分。  # noqa: E501
        _ = score  # score 当前不进入 prompt。  # noqa: E501
        return header + body  # 拼接并返回。  # noqa: E501

    def _build_context(self, chunks: Sequence[Chunk], scores: Sequence[float]) -> str:  # 组装 context。  # noqa: E501
        blocks: List[str] = []  # 证据块列表。  # noqa: E501
        limit: int = min(len(chunks), int(self._cfg.max_chunks_in_prompt))  # 限制数量。  # noqa: E501
        for i in range(limit):  # 遍历 top chunks。  # noqa: E501
            score_value: Optional[float] = float(scores[i]) if i < len(scores) else None  # 读取 score。  # noqa: E501
            blocks.append(self._format_chunk_for_prompt(chunks[i], score_value, f"E{i + 1}"))  # 追加格式化块。  # noqa: E501
        return "\n".join(blocks)  # 合并为字符串。  # noqa: E501

    def _parse_citation_markers(self, text: str) -> List[int]:
        """只解析简短证据标记，不接受任意来源 ID 冒充引用。"""
        return [int(match.group("index")) for match in _CIT_RE.finditer(text)]

    def _build_citations(
        self,
        prompt_chunks: Sequence[Chunk],
        scores: Sequence[float],
        cited: List[int],
    ) -> Tuple[List[Citation], List[Dict[str, Any]]]:
        """引用只能绑定到提示中实际对模型可见的证据。"""
        citations: List[Citation] = []
        failures: List[Dict[str, Any]] = []
        seen: set[int] = set()
        for marker_index in cited:
            marker = f"E{marker_index}"
            if marker_index in seen:
                failures.append({"marker": marker, "reason": "duplicate_marker"})
                continue
            seen.add(marker_index)
            if marker_index < 1 or marker_index > len(prompt_chunks):
                failures.append({"marker": marker, "reason": "marker_not_prompt_visible"})
                continue
            chunk = prompt_chunks[marker_index - 1]
            score_value = float(scores[marker_index - 1]) if marker_index - 1 < len(scores) else 0.0
            citations.append(
                Citation(
                    source_id=str(chunk.source_id),
                    chunk_id=str(chunk.chunk_id),
                    offset_start=int(chunk.offset_start),
                    score=float(score_value),
                )
            )
        return citations, failures

    def _fallback_citations(self, rr: RetrievalResult) -> List[Citation]:  # 从 top chunks 构造 fallback citations。  # noqa: E501
        keep: int = min(int(self._cfg.citation_fallback_n), len(rr.chunks))  # 实际保留数量。  # noqa: E501
        out: List[Citation] = []  # 输出 citations。  # noqa: E501
        for i in range(keep):  # 遍历 top chunks。  # noqa: E501
            chunk: Chunk = rr.chunks[i]  # 取 chunk。  # noqa: E501
            score_value: float = float(rr.scores[i]) if i < len(rr.scores) else 0.0  # 取 score。  # noqa: E501
            out.append(  # 追加 Citation。  # noqa: E501
                Citation(  # Citation 对象。  # noqa: E501
                    source_id=str(chunk.source_id),  # source_id。  # noqa: E501
                    chunk_id=str(chunk.chunk_id),  # chunk_id。  # noqa: E501
                    offset_start=int(chunk.offset_start),  # offset_start。  # noqa: E501
                    score=float(score_value),  # score。  # noqa: E501
                )  # 结束 Citation。  # noqa: E501
            )  # append 结束。  # noqa: E501
        return out  # 返回 fallback citations。  # noqa: E501

    def _sanitize_answer_text(self, text_str: str, evidence_ok: bool) -> str:  # 清洗模型输出，避免“证据足够却抄拒答模板”与重复标题。  # noqa: E501
        sanitized: str = str(text_str).strip()  # 标准化文本。  # noqa: E501

        if not evidence_ok:  # 若证据不足。  # noqa: E501
            return sanitized  # 原样返回。  # noqa: E501

        sanitized = _REFUSAL_BLOCK_RE.sub("", sanitized)  # 删除以 --- 包裹的拒答块。  # noqa: E501
        sanitized = sanitized.replace(_REFUSAL_TEMPLATE, "").strip()  # 兜底删除裸模板。  # noqa: E501

        # 连续清洗多种可能的开头 Answer 标题，直到不再匹配。
        while True:  # 循环删除开头标题。  # noqa: E501
            new_sanitized: str = _ANSWER_HEADER_RE.sub("", sanitized, count=1).strip()  # 删除一次开头标题。  # noqa: E501
            if new_sanitized == sanitized:  # 若本轮没有变化。  # noqa: E501
                break  # 结束循环。  # noqa: E501
            sanitized = new_sanitized  # 应用新文本。  # noqa: E501

        sanitized = _CITATIONS_TAIL_RE.sub("", sanitized).strip()  # 删除正文尾部自带的 Citations 段。  # noqa: E501

        return sanitized  # 返回清洗后的文本。  # noqa: E501

    def generate(self, rr: RetrievalResult) -> Answer:  # 主入口。  # noqa: E501
        t0: float = time.time()  # 起始时间。  # noqa: E501
        retrieval_ms: float = float(getattr(rr, "timing_ms", 0.0)) if rr is not None else 0.0  # 读取检索耗时。  # noqa: E501
        signal_flags: Dict[str, Any] = self._build_retrieval_signal_flags(rr=rr)  # 先构造最小检索信号。  # noqa: E501

        if rr is None:  # 防御：rr 为空。  # noqa: E501
            generation_ms_empty: float = float((time.time() - t0) * 1000.0)  # 记录生成耗时。  # noqa: E501
            return self._reject(  # 返回稳定拒答。  # noqa: E501
                query="",  # query。  # noqa: E501
                timing_ms=float(retrieval_ms + generation_ms_empty),  # 总耗时。  # noqa: E501
                reason="empty_retrieval_result",  # 拒答原因。  # noqa: E501
                used_chunks=[],  # 无 chunks。  # noqa: E501
                retrieval_ms=float(retrieval_ms),  # 检索耗时。  # noqa: E501
                generation_ms=float(generation_ms_empty),  # 生成耗时。  # noqa: E501
                llm_generate_ms=0.0,  # 未调用 LLM。  # noqa: E501
                signal_flags=signal_flags,  # 写入信号 flags。  # noqa: E501
            )  # 结束返回。  # noqa: E501

        if rr.chunks is None or len(rr.chunks) < int(self._cfg.min_evidence_chunks):  # generator 层兜底 evidence_check。  # noqa: E501
            generation_ms_insufficient: float = float((time.time() - t0) * 1000.0)  # 记录生成耗时。  # noqa: E501
            return self._reject(  # 返回稳定拒答。  # noqa: E501
                query=str(rr.query),  # query。  # noqa: E501
                timing_ms=float(retrieval_ms + generation_ms_insufficient),  # 总耗时。  # noqa: E501
                reason="insufficient_evidence",  # 拒答原因。  # noqa: E501
                used_chunks=list(rr.chunks or []),  # used_chunks。  # noqa: E501
                retrieval_ms=float(retrieval_ms),  # 检索耗时。  # noqa: E501
                generation_ms=float(generation_ms_insufficient),  # 生成耗时。  # noqa: E501
                llm_generate_ms=0.0,  # 未调用 LLM。  # noqa: E501
                signal_flags=signal_flags,  # 写入信号 flags。  # noqa: E501
            )  # 结束返回。  # noqa: E501

        generation_context: Dict[str, Any] = self._build_generation_context(rr)  # 记录真实 prompt chunks。  # noqa: E501
        evidence_snapshot = build_evidence_snapshot(rr)
        context: str = self._build_context(rr.chunks, rr.scores)  # 构造 context。  # noqa: E501
        prompt: str = self._prompt_template.format(query=str(rr.query), context=context)  # 填充模板。  # noqa: E501
        prompt_snapshot = build_prompt_snapshot(
            list(generation_context.get("chunks_in_prompt", []) or []),
            evidence_snapshot_id=str(evidence_snapshot["snapshot_id"]),
            query=str(rr.query),
            prompt_template=self._prompt_template,
            rendered_prompt=prompt,
        )
        generation_context["evidence_snapshot_id"] = evidence_snapshot["snapshot_id"]
        generation_context["prompt_snapshot_id"] = prompt_snapshot["snapshot_id"]
        signal_flags["generation_context"] = generation_context  # 写入 flags，供 debug / replay 使用。  # noqa: E501
        signal_flags["evidence_snapshot"] = evidence_snapshot
        signal_flags["evidence_snapshot_id"] = evidence_snapshot["snapshot_id"]
        signal_flags["prompt_snapshot"] = prompt_snapshot
        signal_flags["prompt_snapshot_id"] = prompt_snapshot["snapshot_id"]
        signal_flags["prompt_chunk_ids"] = list(generation_context.get("prompt_chunk_ids", []))  # 兼容轻量读取。  # noqa: E501
        signal_flags["prompt_context_chunk_count"] = generation_context.get("prompt_context_chunk_count")  # 兼容轻量读取。  # noqa: E501
        token_usage: Dict[str, Any] = {}  # 初始化 token_usage。  # noqa: E501
        text_str: str = ""  # 初始化生成文本。  # noqa: E501
        llm_generate_ms: float = 0.0  # 初始化 LLM 调用耗时。  # noqa: E501
        raw_text_str: str = ""  # 保留原始 LLM 输出，排查 sanitize 误删。  # noqa: E501
        sanitized_answer_was_empty: bool = False  # 标记 sanitize 是否把非空答案删空。  # noqa: E501

        try:  # 调用 LLM。  # noqa: E501
            text, token_usage, llm_generate_ms_int = self._llm.generate(prompt)  # 生成文本。  # noqa: E501
            llm_generate_ms = float(llm_generate_ms_int)  # 记录 LLM 调用耗时。  # noqa: E501
            raw_text_str = str(text).strip()  # 保留原始生成文本。  # noqa: E501
            sanitized_text_str: str = self._sanitize_answer_text(  # 清洗可能混入的拒答模板与重复标题。  # noqa: E501
                text_str=raw_text_str,  # 原始生成文本。  # noqa: E501
                evidence_ok=(len(rr.chunks) >= int(self._cfg.min_evidence_chunks)),  # evidence_ok。  # noqa: E501
            )  # 清洗结束。  # noqa: E501
            sanitized_answer_was_empty = bool(raw_text_str.strip()) and not bool(sanitized_text_str.strip())  # 记录清洗是否误删空。  # noqa: E501
            text_str = raw_text_str if sanitized_answer_was_empty else sanitized_text_str  # 清洗删空时回退原文。  # noqa: E501
        except Exception as exc:  # LLM 失败也稳定输出。  # noqa: E501
            generation_ms_error: float = float((time.time() - t0) * 1000.0)  # 记录异常分支生成耗时。  # noqa: E501
            error_signal_flags: Dict[str, Any] = dict(signal_flags or {})  # 复制检索信号。  # noqa: E501
            error_signal_flags.update(  # 补充 generator 异常观测字段。  # noqa: E501
                self._build_generator_error_flags(  # 构造异常 flags。  # noqa: E501
                    exc=exc,  # 原始异常。  # noqa: E501
                    llm_generate_ms=float(llm_generate_ms),  # 当前 LLM 耗时。  # noqa: E501
                )  # 构造结束。  # noqa: E501
            )  # update 结束。  # noqa: E501
            return self._reject(  # 返回稳定拒答。  # noqa: E501
                query=str(rr.query),  # query。  # noqa: E501
                timing_ms=float(retrieval_ms + generation_ms_error),  # 总耗时。  # noqa: E501
                reason=f"llm_error:{type(exc).__name__}",  # 拒答原因。  # noqa: E501
                used_chunks=list(rr.chunks),  # used_chunks。  # noqa: E501
                retrieval_ms=float(retrieval_ms),  # 检索耗时。  # noqa: E501
                generation_ms=float(generation_ms_error),  # 生成耗时。  # noqa: E501
                llm_generate_ms=float(llm_generate_ms),  # LLM 耗时。  # noqa: E501
                signal_flags=error_signal_flags,  # 写入信号 flags。  # noqa: E501
            )  # 结束返回。  # noqa: E501

        cited: List[int] = self._parse_citation_markers(text_str)
        prompt_limit = min(len(rr.chunks), int(self._cfg.max_chunks_in_prompt))
        citations, citation_failures = self._build_citations(
            rr.chunks[:prompt_limit], rr.scores[:prompt_limit], cited
        )

        fallback_used: bool = False  # 标记是否使用 fallback 引用。  # noqa: E501
        if len(citations) == 0 and int(self._cfg.citation_fallback_n) > 0:  # 仅显式 legacy 模式允许 fallback。  # noqa: E501
            citations = self._fallback_citations(rr)  # 自动补齐引用。  # noqa: E501
            fallback_used = True  # 记录 fallback 使用。  # noqa: E501

        generation_ms: float = float((time.time() - t0) * 1000.0)  # 记录生成阶段总耗时。  # noqa: E501
        total_ms: float = float(retrieval_ms + generation_ms)  # 总耗时：retrieve + generate。  # noqa: E501

        flags: Dict[str, Any] = dict(signal_flags)  # 先复制最小检索信号。  # noqa: E501
        usage_flags: Dict[str, Any] = self._build_usage_flags(  # 构造 usage flags。  # noqa: E501
            used_chunks=list(rr.chunks),  # used_chunks。  # noqa: E501
            citations=list(citations),  # citations。  # noqa: E501
        )  # usage flags 构造结束。  # noqa: E501
        flags.update(usage_flags)  # 先补 usage flags。  # noqa: E501
        flags.update(  # 补充 generator 模型身份与调用观测字段。  # noqa: E501
            self._build_generator_observability_flags(  # 构造 generator 观测字段。  # noqa: E501
                token_usage=token_usage,  # token_usage。  # noqa: E501
                llm_generate_ms=float(llm_generate_ms),  # LLM 调用耗时。  # noqa: E501
            )  # 构造结束。  # noqa: E501
        )  # update 结束。  # noqa: E501
        flags.update(  # 补充生成阶段 flags。  # noqa: E501
            {  # 开始补充。  # noqa: E501
                "refused": False,  # 标记非拒答。  # noqa: E501
                "refuse_reason": "",  # 非拒答时置空。  # noqa: E501
                "citation_hallucination": bool(len(citation_failures) > 0),
                "hallucinated_citations": [item["marker"] for item in citation_failures],
                "citation_parse": {
                    "contract": "evidence_marker_v1",
                    "markers": [f"E{item}" for item in cited],
                },
                "citation_failures": citation_failures,
                "citation_validity": "pass" if citations and not citation_failures else "fail",
                "missing_citations_fallback": bool(fallback_used),  # 是否启用 fallback。  # noqa: E501
                "citation_missing": bool(len(citations) == 0),  # 模型是否缺少可验证引用。  # noqa: E501
                "citation_origin": "model_emitted" if citations else None,  # 引用来源。  # noqa: E501
                "raw_answer_was_nonempty": bool(raw_text_str.strip()),  # 原始 LLM 输出是否非空。  # noqa: E501
                "sanitized_answer_was_empty": bool(sanitized_answer_was_empty),  # 清洗后是否被删空。  # noqa: E501
                "raw_answer_preview": raw_text_str[:500],  # 原始输出预览，用于排查清洗误删。  # noqa: E501
                "generator_finish_reason": token_usage.get("finish_reason"),  # provider finish_reason。  # noqa: E501
                "generator_native_finish_reason": token_usage.get("native_finish_reason"),  # provider native finish_reason。  # noqa: E501
                "generator_content_was_empty": token_usage.get("content_was_empty"),  # message.content 是否为空。  # noqa: E501
                "generator_message_keys": token_usage.get("message_keys"),  # OpenAI-compatible message 字段列表。  # noqa: E501
                "generator_message_field_lengths": token_usage.get("message_field_lengths"),  # message 非 content 字段长度，不记录 reasoning 原文。  # noqa: E501
                "generator_completion_tokens_details": token_usage.get("completion_tokens_details"),  # completion token 明细。  # noqa: E501
                "generator_prompt_tokens_details": token_usage.get("prompt_tokens_details"),  # prompt token 明细。  # noqa: E501
            }  # 结束补充。  # noqa: E501
        )  # update 结束。  # noqa: E501

        return Answer(  # 构造最终 Answer。  # noqa: E501
            query=str(rr.query),  # query。  # noqa: E501
            answer_text=str(text_str),  # answer_text。  # noqa: E501
            citations=list(citations),  # citations。  # noqa: E501
            used_chunks=list(rr.chunks),  # used_chunks。  # noqa: E501
            timing_ms=float(total_ms),  # 总耗时。  # noqa: E501
            retrieval_ms=float(retrieval_ms),  # 检索耗时。  # noqa: E501
            generation_ms=float(generation_ms),  # 生成耗时。  # noqa: E501
            llm_generate_ms=float(llm_generate_ms),  # LLM 调用耗时。  # noqa: E501
            token_usage=dict(token_usage or {}),  # token_usage。  # noqa: E501
            flags=flags,  # flags。  # noqa: E501
        )  # 结束 Answer。  # noqa: E501
