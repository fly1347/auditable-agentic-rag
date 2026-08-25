"""
文件作用：
定义 Phase C / D-full API 层请求与响应 schema。

整体结构：
1）ChatRequest：/api/chat 与 /api/chat/debug 入参；
2）CitationDTO：答案引用字段；
3）RetrievedChunkDTO：检索证据字段；
4）ChatResponse：普通响应，保持简洁；
5）DebugChatResponse：debug 响应，增加 D-full workflow / observability / diagnostics。
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    """Chat API 请求体。"""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    profile: Optional[Literal["baseline", "orchestrated"]] = None


class CitationDTO(BaseModel):
    """答案实际引用。对应 types.Citation。"""

    source_id: str
    chunk_id: str
    offset_start: int
    score: float


class RetrievedChunkDTO(BaseModel):
    """普通响应中的检索证据池回显。对应 types.Chunk。"""

    source_id: str
    chunk_id: str
    offset_start: int
    offset_end: int
    text_preview: Optional[str] = None


class TimingsDTO(BaseModel):
    """API 返回耗时字段。"""

    total_ms: Optional[float] = None
    engine_init_ms: Optional[float] = None
    engine_ms: Optional[float] = None
    pipeline_total_ms: Optional[float] = None
    retrieval_ms: Optional[float] = None
    generation_ms: Optional[float] = None
    llm_generate_ms: Optional[float] = None

    first_retrieval_ms: Optional[float] = None
    second_retrieval_ms: Optional[float] = None
    first_sufficiency_ms: Optional[float] = None
    second_sufficiency_ms: Optional[float] = None
    query_rewrite_ms: Optional[float] = None

    queue_wait_ms: Optional[float] = None
    api_overhead_ms: Optional[float] = None
    serialization_ms: Optional[float] = None


class AgenticStepDTO(BaseModel):
    """D-lite 控制流步骤。"""

    step: str
    output: str
    duration_ms: float = 0.0


class ChatResponse(BaseModel):
    """普通 chat 响应。"""

    request_id: Optional[str] = None
    session_id: Optional[str] = None
    profile: Optional[str] = None

    answer: str
    citations: List[CitationDTO]
    retrieved_chunks: List[RetrievedChunkDTO]
    timings: TimingsDTO

    path: Optional[str] = None
    refused: bool = False
    refused_reason: Optional[str] = None

    degraded: bool = False
    degraded_reasons: List[str] = Field(default_factory=list)


class DebugChatResponse(ChatResponse):
    """debug chat 响应，在普通响应基础上增加 D-full 诊断字段。"""

    # Phase C / D-lite 兼容字段。
    flags: Dict[str, Any] = Field(default_factory=dict)
    agentic_steps: List[AgenticStepDTO] = Field(default_factory=list)
    evaluation_context: Dict[str, Any] = Field(default_factory=dict)
    vector_store_context: Dict[str, Any] = Field(default_factory=dict)

    # D-full Step 5 新增字段。
    workflow_trace: Dict[str, Any] = Field(default_factory=dict)
    observability: Dict[str, Any] = Field(default_factory=dict)
    retrieval_diagnostics: Dict[str, Any] = Field(default_factory=dict)
    sufficiency_diagnostics: Dict[str, Any] = Field(default_factory=dict)
    model_identity: Dict[str, Any] = Field(default_factory=dict)

    # Step C：统一 usage / timing 账本。
    usage: Dict[str, Any] = Field(default_factory=dict)
    timing: Dict[str, Any] = Field(default_factory=dict)
    rerank: Dict[str, Any] = Field(default_factory=dict)
    generation_context: Dict[str, Any] = Field(default_factory=dict)
    policy_trace: Dict[str, Any] = Field(default_factory=dict)
    execution_record: Dict[str, Any] = Field(default_factory=dict)
