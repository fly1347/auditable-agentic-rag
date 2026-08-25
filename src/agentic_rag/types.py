"""
作用：
- 定义 Phase A 必需的稳定数据结构（类型契约）
- 这些字段在 Phase A 冻结：后续阶段只允许“新增字段”，不允许改名/改语义
- 本版为 D-lite selective rerank：在 RetrievalResult 中新增 selective rerank 观测字段

结构：
- Document: 原始文档对象（loader 输出）
- Chunk: 切分后的片段对象（splitter 输出）
- RetrievalResult: 检索结果对象（retriever 输出）
- Citation: 引用对象（用于 Answer.citations）
- AgenticStep: D-lite 控制流步骤对象（用于可观测）
- Answer: 最终回答对象（generator 输出）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class Document:
    source_id: str
    path: str
    mtime: float
    doc_hash: str
    title: Optional[str] = None
    lang: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source_id: str
    doc_hash: str
    text: str
    offset_start: int
    offset_end: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RetrievalResult:
    query: str
    chunks: List[Chunk]
    scores: List[float]
    topk: int
    timing_ms: float
    rerank_applied: bool = False
    rerank_model: Optional[str] = None
    rerank_candidate_topk: Optional[int] = None
    rerank_topn: Optional[int] = None
    rerank_scores: List[float] = field(default_factory=list)
    rerank_phase: Optional[str] = None
    selective_rerank_enabled: bool = False
    selective_rerank_triggered: bool = False
    selective_rerank_reason: Optional[str] = None
    selective_rerank_threshold: Optional[float] = None
    selective_rerank_gap: Optional[float] = None
    selective_rerank_before_source_ids: List[str] = field(default_factory=list)
    selective_rerank_after_source_ids: List[str] = field(default_factory=list)
    # Canonical retrieval observations.  These fields are additive so callers
    # using the historical contract keep working while CER can stop guessing.
    retrieval_events: List[Dict[str, Any]] = field(default_factory=list)
    merge_trace: Dict[str, Any] = field(default_factory=dict)
    access_policy: Dict[str, Any] = field(default_factory=dict)
    score_type: str = "vector_similarity"


@dataclass(frozen=True)
class Citation:
    source_id: str
    chunk_id: str
    offset_start: int
    score: float


@dataclass(frozen=True)
class AgenticStep:
    step: str
    output: str
    duration_ms: float = 0.0


@dataclass(frozen=True)
class Answer:
    query: str
    answer_text: str
    citations: List[Citation]
    used_chunks: List[Chunk]
    timing_ms: float
    retrieval_ms: float = 0.0
    generation_ms: float = 0.0
    llm_generate_ms: float = 0.0
    token_usage: Dict[str, Any] = field(default_factory=dict)
    flags: Dict[str, Any] = field(default_factory=dict)
    agentic_steps: List[AgenticStep] = field(default_factory=list)
