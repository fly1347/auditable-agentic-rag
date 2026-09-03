"""
作用：
- 定义 Phase D-full 的工作流状态、步骤记录、证据包与诊断结果类型。
- 为 WorkflowRunner、/api/chat/debug、replay 与 per-question report 提供统一结构。
- Step 7 schema 已拆分为 question_type 与 answerability，route_candidate 由程序派生。

整体结构：
1. 枚举：WorkflowStepType / WorkflowRoute / QuestionType / Answerability / RouteCandidate / RoutePolicy / WorkflowFinalStatus
2. 检索与证据结构：RetrievalRound / EvidenceItem / EvidencePacket
3. 判定结构：SufficiencyResult / SufficiencyRound / CitationSupportReport / ConflictItem / UncertaintyReport
4. 工作流结构：WorkflowStep / WorkflowState
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from agentic_rag.observability.model_identity import ModelIdentity
from agentic_rag.observability.observability_record import (
    ModelCallRecord,
    ObservabilityRecord,
)


class WorkflowStepType(str, Enum):
    """作用：标识 D-full workflow 中的节点类型。"""

    CLASSIFY_QUERY = "CLASSIFY_QUERY"
    PLAN_ROUTE = "PLAN_ROUTE"
    GENERATE_SUBQUERIES = "GENERATE_SUBQUERIES"
    RETRIEVE = "RETRIEVE"
    RERANK = "RERANK"
    BUILD_EVIDENCE_PACKET = "BUILD_EVIDENCE_PACKET"
    CHECK_SUFFICIENCY = "CHECK_SUFFICIENCY"
    REWRITE_QUERY = "REWRITE_QUERY"
    GENERATE_ANSWER = "GENERATE_ANSWER"
    CHECK_CITATION_SUPPORT = "CHECK_CITATION_SUPPORT"
    DETECT_CONFLICTS = "DETECT_CONFLICTS"
    BUILD_UNCERTAINTY = "BUILD_UNCERTAINTY"
    BUILD_RESPONSE = "BUILD_RESPONSE"
    BUILD_REFUSAL_OR_CLARIFICATION_RESPONSE = "BUILD_REFUSAL_OR_CLARIFICATION_RESPONSE"


class WorkflowRoute(str, Enum):
    """作用：标识 D-full 的实际执行路径。"""

    DIRECT = "DIRECT"
    DECOMPOSE = "DECOMPOSE"
    OPEN_MULTI = "OPEN_MULTI"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    REJECT = "REJECT"


class QuestionType(str, Enum):
    """作用：标识用户问题的答案形态，不承载可答性或交互状态。"""

    NARROW_FACT = "NARROW_FACT"
    EXPLICIT_COMPARE = "EXPLICIT_COMPARE"
    IMPLICIT_COMPARE = "IMPLICIT_COMPARE"
    OPEN_MULTI = "OPEN_MULTI"
    SUMMARY = "SUMMARY"
    PROCEDURE = "PROCEDURE"


class Answerability(str, Enum):
    """作用：标识 query-level 可答性风险，不判断证据是否充分。"""

    IN_SCOPE = "IN_SCOPE"
    OOD_CANDIDATE = "OOD_CANDIDATE"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    UNKNOWN = "UNKNOWN"


class RouteCandidate(str, Enum):
    """作用：记录 classifier 派生的候选路径；Step 7 阶段不等于实际执行路径。"""

    DIRECT = "DIRECT"
    DECOMPOSE = "DECOMPOSE"
    OPEN_MULTI = "OPEN_MULTI"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    REJECT_CANDIDATE = "REJECT_CANDIDATE"


class RoutePolicy(str, Enum):
    """作用：记录候选路径的执行策略；最终是否采用由后续 plan_route_node 决定。"""

    NORMAL = "NORMAL"
    STRICT_SUFFICIENCY = "STRICT_SUFFICIENCY"
    CANDIDATE_REJECT = "CANDIDATE_REJECT"
    CLARIFY = "CLARIFY"


class WorkflowFinalStatus(str, Enum):
    """作用：标识 workflow 最终状态。"""

    ANSWERED = "ANSWERED"
    REFUSED = "REFUSED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    ERROR = "ERROR"


@dataclass
class RetrievalRound:
    """作用：记录一次检索轮次的 query、命中、重排与诊断信息。"""

    round_id: int
    retrieval_query: str
    route: Optional[str] = None
    topk: Optional[int] = None
    hit_count: Optional[int] = None
    rerank_applied: bool = False
    diagnostics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceItem:
    """作用：记录一个 chunk 在检索、重排、prompt 与评测中的证据属性。"""

    chunk_id: str
    source_id: str
    source_path: Optional[str] = None
    section_path: Optional[str] = None
    offset_start: Optional[int] = None
    offset_end: Optional[int] = None
    text_preview: Optional[str] = None
    visibility: Optional[str] = None

    vector_score: Optional[float] = None
    rrf_score: Optional[float] = None
    rerank_score: Optional[float] = None
    retrieval_round: Optional[int] = None
    retrieval_query: Optional[str] = None
    rank_before_rerank: Optional[int] = None
    rank_after_rerank: Optional[int] = None

    is_expected_source: Optional[bool] = None
    is_expected_section: Optional[bool] = None
    is_answer_bearing: Optional[bool] = None
    in_prompt: bool = False


@dataclass
class EvidencePacket:
    """作用：聚合进入 sufficiency / citation_support / conflict detection 的证据视图。"""

    items: List[EvidenceItem] = field(default_factory=list)
    source_coverage: Dict[str, Any] = field(default_factory=dict)
    answer_bearing_summary: Dict[str, Any] = field(default_factory=dict)
    score_summary: Dict[str, Any] = field(default_factory=dict)
    compression_policy: Optional[str] = None
    known_gaps: List[str] = field(default_factory=list)


@dataclass
class SufficiencyResult:
    """作用：记录 sufficiency judge 的结构化输出。"""

    verdict: Optional[str] = None
    confidence: Optional[str] = None
    missing_evidence: List[str] = field(default_factory=list)
    supporting_evidence_ids: List[str] = field(default_factory=list)
    conflict_evidence_ids: List[str] = field(default_factory=list)
    reason: Optional[str] = None
    model_identity: ModelIdentity = field(default_factory=ModelIdentity)


@dataclass
class SufficiencyRound:
    """作用：记录一轮 sufficiency 判定，包括输入摘要与输出结果。"""

    round_id: int
    input_summary: Dict[str, Any] = field(default_factory=dict)
    result: SufficiencyResult = field(default_factory=SufficiencyResult)


@dataclass
class CitationSupportReport:
    """作用：记录 citation_support 离线校验结果。"""

    citation_support_label: Optional[str] = None
    unsupported_claim_count: Optional[int] = None
    claims: List[Dict[str, Any]] = field(default_factory=list)
    borderline_dimension: Optional[str] = None


@dataclass
class ConflictItem:
    """作用：记录多证据之间的冲突。"""

    conflict_type: Optional[str] = None
    claim_a: Optional[str] = None
    claim_b: Optional[str] = None
    evidence_a: List[str] = field(default_factory=list)
    evidence_b: List[str] = field(default_factory=list)
    resolution: Optional[str] = None
    uncertainty_level: Optional[str] = None


@dataclass
class UncertaintyReport:
    """作用：记录最终回答的不确定性边界。"""

    level: Optional[str] = None
    reasons: List[str] = field(default_factory=list)
    missing_info: List[str] = field(default_factory=list)
    safe_answer_boundary: Optional[str] = None
    next_steps: List[str] = field(default_factory=list)


@dataclass
class ErrorRecord:
    """作用：记录 workflow 节点级错误。"""

    error_type: str
    message: Optional[str] = None
    http_status: Optional[int] = None
    retryable: Optional[bool] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkflowStep:
    """作用：记录一次 workflow 节点执行结果。"""

    step_type: WorkflowStepType
    name: Optional[str] = None
    decision: Optional[str] = None
    input_summary: Dict[str, Any] = field(default_factory=dict)
    output_summary: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None
    model_call: Optional[ModelCallRecord] = None
    error: Optional[ErrorRecord] = None


@dataclass
class WorkflowState:
    """作用：记录一次 D-full 请求的完整 workflow 状态。"""

    request_id: str
    query: str

    run_id: Optional[str] = None
    qid: Optional[str] = None

    question_type: Optional[QuestionType] = None
    answerability: Optional[Answerability] = None
    route: Optional[WorkflowRoute] = None
    final_status: Optional[WorkflowFinalStatus] = None
    failure_attribution: List[str] = field(default_factory=list)

    steps: List[WorkflowStep] = field(default_factory=list)
    retrieval_rounds: List[RetrievalRound] = field(default_factory=list)
    evidence_packet: Optional[EvidencePacket] = None
    sufficiency_rounds: List[SufficiencyRound] = field(default_factory=list)
    citation_support: Optional[CitationSupportReport] = None
    conflicts: List[ConflictItem] = field(default_factory=list)
    uncertainty: Optional[UncertaintyReport] = None

    observability: Optional[ObservabilityRecord] = None
    extra: Dict[str, Any] = field(default_factory=dict)
