# D-full orchestrated 逐题评测报告

> source_profile: `orchestrated`；classifier.mode: `llm=30`；sufficiency.mode: `structured=30`。批次共同配置不再逐题重复。

## 阅读口径

- **Classifier**：LLM 判断 question_type、answerability、route_candidate、confidence，并给出 reason；confidence 是模型自报等级，不是概率。
- **Sufficiency Judge**：读取主链 CER 中已发生的证据充分性判断；baseline 通常为 binary，orchestrated 为 structured。
- **Citation Support**：只使用最终 `Citations` 实际引用的证据作为评分池；答案正文中的 `[E1]` / `[E2]` 标记保留供人读核对，但不决定评分证据池。
- **Citation Support 判定阈值**：`supported >= 0.22`；`partial = 0.12 ~ < 0.22`；`unsupported < 0.12`。best_score 是本地规则相似度诊断分，不等同于语义蕴含概率。
- **Conflict**：对多来源 EvidencePacket 做规则型疑似冲突扫描；命中表示需要复核，不直接等同于事实冲突。
- **Uncertainty**：由 sufficiency、citation、conflict 等信号派生；`high` 表示不确定性/风险高。

## q01 — RAG 的完整流程包括哪些主要步骤？

### 分类与回答边界

- actual_route: DIRECT
- question_type: OPEN_MULTI
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: high
- reason: 问题明确询问 RAG 流程的主要步骤，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/01_RAG基础原理.md@0-871#dfa7ac57160a；external/12-检索增强生成 (RAG) 技术综述-syhya.md@518-1237#59ad08ea7df5；external/11_RAG_intro.md@772-1349#c45ac06e719a
- reason: 证据包中多个来源明确描述了RAG的完整流程，包括离线索引阶段（文档加载、分块、嵌入、存储）和在线检索-生成阶段（查询嵌入、检索、构建提示、生成），以及技术演进分类（初级、高级、模块化）。这些信息足以回答用户关于RAG主要步骤的问题，且各来源描述一致，无冲突。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 11
- unsupported_claim_count: 6

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E2 | internal/01_RAG基础原理.md | internal/01_RAG基础原理.md@0-871#dfa7ac57160a | 0.6580 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1720 | E2 | RAG（检索增强生成）的完整流程主要包括两个阶段：离线索引阶段和在线检索-生成阶段 |
| 2 | unsupported | 0.0217 | E2 | **离线索引阶段**： - 文档加载：从不同数据源加载原始文档 |
| 3 | unsupported | 0.0093 | E2 | - 文本分块：将文档分割成较小的文本块 |
| 4 | partial | 0.1631 | E2 | - Embedding 计算：将文本映射到高维向量空间 |
| 5 | unsupported | 0.0172 | E2 | - 向量存储：将向量写入向量数据库以建立索引 |
| 6 | unsupported | 0.0185 | E2 | **在线检索-生成阶段**： - 用户查询：接收用户的查询请求 |
| 7 | partial | 0.1618 | E2 | - Query Embedding：将查询转化为向量 |
| 8 | unsupported | 0.0249 | E2 | - 向量相似度检索：从数据库中检索与查询最相关的文本块 |
| 9 | partial | 0.1470 | E2 | - 构建 Prompt：将查询和检索到的文本块结合 |
| 10 | partial | 0.1487 | E2 | - LLM 生成回答：使用大语言模型生成最终答案 |
| 11 | unsupported | 0.0154 | E2 | - 返回结果：将生成的答案返回给用户，并包含来源引用 [E2] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: OPEN_MULTI 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=6；unsupported_claim；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 3,052.178
- model_call_count: 1
- prompt_tokens: 373
- completion_tokens: 52
- total_tokens: 425
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `7fb9ec32a2cce39da02bb89c16e7656e42db7eb30d113ea1ba4fe109d9a7c693`
- answer_sha256: `f6662650c3b8404cb0dcaa0bf9ef3d323a1392512ba398d558438a25a844d71e`

## q02 — OpenAI GPT-6 的内部架构是什么？

### 分类与回答边界

- actual_route: DIRECT
- question_type: NARROW_FACT
- answerability: OOD_CANDIDATE
- route_candidate: REJECT_CANDIDATE
- confidence: medium
- reason: 内部架构信息可能未公开或涉及未来不可验证的内容

### 证据充分性

- raw_verdict: INSUFFICIENT
- control_verdict: INSUFFICIENT
- confidence: high
- missing_evidence: 关于 OpenAI GPT-6 内部架构的任何信息，例如模型结构、参数规模、训练方法、组件组成等
- reason: 用户问题询问 OpenAI GPT-6 的内部架构，但提供的证据包中没有任何内容涉及 GPT-6 或 OpenAI 模型架构。所有证据均来自 Kubernetes、向量数据库、vLLM 和 GraphRAG 等无关主题，且 answer_bearing_summary 显示 answer_bearing_hit_count 为 0，因此证据完全不足以回答该问题。

### 引用证据支撑（规则）

- citation_support_label: not_applicable
- citation_count: 0
- resolved_citation_count: 0
- unresolved_citation_count: 0
- claim_count: 0
- unsupported_claim_count: 0

### 冲突检测（规则型疑似冲突）

- triggered: false
- conflict_count: 0
- trigger_reason: NARROW_FACT 不在规则触发类型中，不执行冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: refused；sufficiency_insufficient
- missing_info: insufficient_evidence_after_reretrieve；关于 OpenAI GPT-6 内部架构的任何信息，例如模型结构、参数规模、训练方法、组件组成等；用户问题询问 OpenAI GPT-6 的内部架构，但提供的证据包中没有任何内容涉及 GPT-6 或 OpenAI 模型架构。所有证据均来自 Kubernetes、向量数据库、vLLM 和 GraphRAG 等无关主题，且 answer_bearing_summary 显示 answer_bearing_hit_count 为 0，因此证据完全不足以回答该问题。
- safe_answer_boundary: 当前证据不足，回答边界应限制在已检索到的证据范围内，不能补全缺失信息。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,817.845
- model_call_count: 1
- prompt_tokens: 374
- completion_tokens: 53
- total_tokens: 427
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `78e5e547cb185f5ac532b3850674b4c64c8e9864abf54a85ae8138cf9a0b6609`
- answer_sha256: `76bf36d8ac30d8cd4dbfdd22e7e40a5be87f2d4e53ad995d12f1147b903196cf`

## q03 — 固定长度 chunk 和语义分块有什么区别？

### 分类与回答边界

- actual_route: DECOMPOSE
- question_type: EXPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: high
- reason: 问题明确要求比较两种分块方式，且相关信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: external/12-检索增强生成 (RAG) 技术综述-syhya.md@1237-1865#09b01ab21d25；internal/02_Chunk策略.md@0-685#1411d3bdb16d
- reason: 证据包中多个来源明确对比了固定长度分块与语义分块的定义、优缺点和适用场景，足以回答用户问题。external/12 和 internal/02 均直接描述了两种策略的差异，包括固定长度分块简单但可能切断语义，语义分块保留语义完整性但实现复杂。证据之间无冲突，信息充分。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 2
- unsupported_claim_count: 1

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | external/12-检索增强生成 (RAG) 技术综述-syhya.md | external/12-检索增强生成 (RAG) 技术综述-syhya.md@1237-1865#09b01ab21d25 | 0.0481 |
| E2 | internal/02_Chunk策略.md | internal/02_Chunk策略.md@0-685#1411d3bdb16d | 0.0328 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1889 | E1 | 固定长度分块和语义分块的主要区别在于分块的方式和对语义的考虑： 1. **固定长度分块**：将文本按固定数量的 token 或字符进行分割，简单易实现，但可能会在语义单元中间切断，导致检索精度较差 [E1][E2] |
| 2 | unsupported | 0.0414 | E2 | **语义分块**：利用自然语言处理技术识别文本中的语义边界进行分块，能够保留语义完整性，减少歧义，但实现较为复杂，块大小不固定 [E1][E2] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: EXPLICIT_COMPARE 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=1；unsupported_claim；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 2,959.448
- model_call_count: 1
- prompt_tokens: 374
- completion_tokens: 51
- total_tokens: 425
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `fb40a48593f3ef58f29a2aedddc66516a3fc5d71af857fb1c05cbd0441d464cf`
- answer_sha256: `9b32557fc03962a066dc31b4cc430876f9c6565fed87c446f60a07430fc20776`

## q04 — chunk size 过大会带来什么问题？

### 分类与回答边界

- actual_route: DIRECT
- question_type: OPEN_MULTI
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: high
- reason: 问题明确，涉及多个潜在问题，且可验证

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/02_Chunk策略.md@1391-1768#5c5d7a6818b5；external/14-text-chunking-datawhale.md@597-1194#e880edf6d91e
- reason: 证据包中两条核心证据直接回答了问题：内部文档明确列出chunk过大的三个问题（检索精度下降、占用更多LLM context窗口、embedding向量语义混杂），外部文档详细解释了嵌入过程中的信息损失机制，两者相互补充且无冲突。其余三条证据与问题无关，不影响充分性判断。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 3
- unsupported_claim_count: 0

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/02_Chunk策略.md | internal/02_Chunk策略.md@1391-1768#5c5d7a6818b5 | 0.6302 |
| E2 | external/14-text-chunking-datawhale.md | external/14-text-chunking-datawhale.md@597-1194#e880edf6d91e | 0.5186 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1434 | E1 | chunk size 过大会带来的问题包括： 1. 检索精度下降，相关内容可能被噪声稀释 |
| 2 | supported | 0.2512 | E1 | 占用更多的 LLM context 窗口，导致处理效率降低 |
| 3 | partial | 0.2128 | E1 | embedding 向量的语义混杂，信息表达变得模糊，降低了检索的精度 [E1][E2] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: OPEN_MULTI 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: medium
- level_meaning: 不确定性/风险中等
- reasons: citation_weak
- missing_info: citation_support_label=partial；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,134.891
- model_call_count: 1
- prompt_tokens: 373
- completion_tokens: 45
- total_tokens: 418
- estimated_cost_usd: 0.000083

### 追溯信息

- source_cer_sha256: `cc67529bd872c69f9656121e875d03361c485d10a8dd313cf923dd2cc9bc5033`
- answer_sha256: `43ae2ea2b482a7abc41f7b91ca1588eb90fb430dc39d01c708a2eeca8b7517d7`

## q05 — 为什么 embedding 相似度常用余弦相似度？

### 分类与回答边界

- actual_route: DIRECT
- question_type: NARROW_FACT
- answerability: IN_SCOPE
- route_candidate: DIRECT
- confidence: high
- reason: 问题明确，询问的是余弦相似度在 embedding 相似度中的常用原因，答案可以基于已知的数学和计算原理给出。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/03_Embedding原理与向量空间.md@685-1106#3f0be53594bb；external/16-vector-embedding-datawhale.md@398-804#13940eb805c6
- reason: 证据包中第一条证据（internal/03_Embedding原理与向量空间.md@685-1106#3f0be53594bb）直接回答了用户问题，明确列出余弦相似度最常用的原因：归一化消除向量长度影响、值域直观、适合高维语义向量，并与其他度量方式对比。第二条证据（external/16-vector-embedding-datawhale.md@398-804#13940eb805c6）也确认余弦相似度是最常用的度量方式。两条证据内容一致，无冲突，足以支撑回答。其余证据为补充或无关内容，不影响充分性。

### 引用证据支撑（规则）

- citation_support_label: unsupported
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 3
- unsupported_claim_count: 3

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/03_Embedding原理与向量空间.md | internal/03_Embedding原理与向量空间.md@685-1106#3f0be53594bb | 0.7071 |
| E2 | external/16-vector-embedding-datawhale.md | external/16-vector-embedding-datawhale.md@398-804#13940eb805c6 | 0.6373 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | unsupported | 0.0652 | E1 | 余弦相似度常用的原因包括： 1. **归一化处理**：余弦相似度消除了向量长度的影响，专注于向量的方向，这对于文本长度不一的情况尤为重要 |
| 2 | unsupported | 0.0579 | E1 | **值域直观**：其值域为[-1, 1]，便于理解，1表示完全相同方向，0表示正交，-1表示完全相反 |
| 3 | unsupported | 0.0497 | E1 | **适用性**：余弦相似度适合高维稀疏或密集的语义向量，能够有效反映语义相似性 [E1]、[E2] |

### 冲突检测（规则型疑似冲突）

- triggered: false
- conflict_count: 0
- trigger_reason: NARROW_FACT 不在规则触发类型中，不执行冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=unsupported；unsupported_claim_count=3；unsupported_claim
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 2,409.494
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 73
- total_tokens: 450
- estimated_cost_usd: 0.000100

### 追溯信息

- source_cer_sha256: `3a9efa665b2c176ca51d04e2e98aa9ad146fe923aa212df2122edcd51ca3a4ca`
- answer_sha256: `4389352a62968b41733e6f82e80d232abb43547915915776c6dcd49edc17cf1b`

## q06 — 在 RAG 系统中，什么情况下容易产生 hallucination？

### 分类与回答边界

- actual_route: DIRECT
- question_type: NARROW_FACT
- answerability: IN_SCOPE
- route_candidate: DIRECT
- confidence: high
- reason: 问题明确询问 RAG 系统中产生幻觉的具体情况，且信息可验证。

### 证据充分性

- raw_verdict: INSUFFICIENT
- control_verdict: INSUFFICIENT
- confidence: high
- missing_evidence: 明确阐述RAG系统中产生幻觉（hallucination）的具体情况或原因的证据，例如检索失败、上下文不相关、知识库缺失、生成阶段幻觉等
- reason: 所有证据块仅介绍RAG的基本概念、工作流程、模块化RAG和多模态RAG的评估，未提及任何关于幻觉（hallucination）产生条件的具体信息。证据包中没有任何内容直接回答用户问题，因此证据不足。

### 引用证据支撑（规则）

- citation_support_label: not_applicable
- citation_count: 0
- resolved_citation_count: 0
- unresolved_citation_count: 0
- claim_count: 0
- unsupported_claim_count: 0

### 冲突检测（规则型疑似冲突）

- triggered: false
- conflict_count: 0
- trigger_reason: NARROW_FACT 不在规则触发类型中，不执行冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: refused；sufficiency_insufficient
- missing_info: insufficient_evidence_after_reretrieve；明确阐述RAG系统中产生幻觉（hallucination）的具体情况或原因的证据，例如检索失败、上下文不相关、知识库缺失、生成阶段幻觉等；所有证据块仅介绍RAG的基本概念、工作流程、模块化RAG和多模态RAG的评估，未提及任何关于幻觉（hallucination）产生条件的具体信息。证据包中没有任何内容直接回答用户问题，因此证据不足。
- safe_answer_boundary: 当前证据不足，回答边界应限制在已检索到的证据范围内，不能补全缺失信息。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,821.497
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 57
- total_tokens: 434
- estimated_cost_usd: 0.000091

### 追溯信息

- source_cer_sha256: `a3f24a2299abb535bb5178e4c1d2c1f46084d69ea1a902dd395721bbb46d3a82`
- answer_sha256: `76bf36d8ac30d8cd4dbfdd22e7e40a5be87f2d4e53ad995d12f1147b903196cf`

## q07 — Multi-AZ 部署如何降低系统单点故障风险？

### 分类与回答边界

- actual_route: DIRECT
- question_type: PROCEDURE
- answerability: IN_SCOPE
- route_candidate: DIRECT
- confidence: high
- reason: 问题明确询问 Multi-AZ 部署的具体操作和影响，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/09_MultiAZ高可用设计.md@613-1434#0c95c99cfcbb；internal/09_MultiAZ高可用设计.md@0-613#57a9e750463e；internal/09_MultiAZ高可用设计.md@1434-2292#093c8c8d2e8b；internal/09_MultiAZ高可用设计.md@2292-2547#2844fd98f077
- reason: 证据包包含来自核心文档的多个相关片段，直接回答了问题。第一个片段（613-1434）提供了三个具体机制：故障隔离、同步复制（RPO≈0，RTO 30s-2min）和负载均衡跨AZ分发。第二个片段（0-613）定义了AZ概念和故障隔离单元。第三个片段（1434-2292）补充了Pod反亲和性和TopologySpreadConstraints，确保跨AZ分布。第四个片段（2292-2547）提供了高可用指标（SLA、RPO、RTO）。这些证据共同充分解释了Multi-AZ如何降低单点故障风险。外部存储片段（external/29-Kubernetes存储.md）与问题无关，但不影响充分性。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 5
- unsupported_claim_count: 0

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/09_MultiAZ高可用设计.md | internal/09_MultiAZ高可用设计.md@613-1434#0c95c99cfcbb | 0.7523 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.2116 | E1 | Multi-AZ 部署通过以下方式降低系统单点故障风险： 1. **故障隔离**：每个可用区（AZ）是独立的故障域，若一个 AZ 发生故障，其他 AZ 的副本不受影响，服务可自动切换到健康的副本 |
| 2 | partial | 0.1676 | E1 | 例如，当 AZ-1 故障时，AZ-2 可以自动提升为主节点，确保服务持续可用 [E1] |
| 3 | partial | 0.2153 | E1 | **同步复制**：数据库在写入时会同步复制到多个 AZ 的副本，确保在故障切换时数据不会丢失，恢复点目标（RPO）接近于零，恢复时间目标（RTO）通常在 30 秒到 2 分钟之间 [E1] |
| 4 | partial | 0.1935 | E1 | **负载均衡**：负载均衡器将请求分发到多个 AZ 中的健康实例，确保在单个 AZ 故障时流量能够自动切换，用户体验不受影响 [E1] |
| 5 | partial | 0.1453 | E1 | 通过这些机制，Multi-AZ 部署显著提高了系统的可用性和容错能力 |

### 冲突检测（规则型疑似冲突）

- triggered: false
- conflict_count: 0
- trigger_reason: PROCEDURE 不在规则触发类型中，不执行冲突扫描

### 综合不确定性（派生信号）

- level: medium
- level_meaning: 不确定性/风险中等
- reasons: citation_weak
- missing_info: citation_support_label=partial；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,214.670
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 54
- total_tokens: 431
- estimated_cost_usd: 0.000089

### 追溯信息

- source_cer_sha256: `5df2155ea36d15ed98c2176bbca7ec5af27a7845af305131ad2be23d95a5ad46`
- answer_sha256: `656b3d8d541118957c4e61e612934718958cead777d3be5e9485d8ad3a977ec1`

## q08 — HNSW 和 IVF 向量索引有什么主要区别？

### 分类与回答边界

- actual_route: DECOMPOSE
- question_type: EXPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: high
- reason: 问题明确要求比较两个具体的向量索引方法，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: external/22-milvus-datawhale.md@4526-5014#fc79b169f6c2；internal/07_向量索引算法HNSW与IVF.md@0-301#a87f5dd9a27c
- reason: 证据包中包含直接对比 HNSW 和 IVF 的核心信息：external/22-milvus-datawhale.md@4526-5014 分别详细说明了 IVF 系列（聚类分桶、nlist、变体、优缺点）和 HNSW（多层邻近图、优缺点），覆盖了原理、优缺点和适用场景；internal/07_向量索引算法HNSW与IVF.md@0-301 将两者定位为最主流的 ANN 算法并说明近似搜索的权衡。两者信息互补且无冲突，足以归纳回答主要区别。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 6
- unsupported_claim_count: 0

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E4 | external/22-milvus-datawhale.md | external/22-milvus-datawhale.md@4526-5014#fc79b169f6c2 | 0.0313 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1704 | E4 | HNSW（Hierarchical Navigable Small World）和IVF（Inverted File）是两种主要的向量索引算法，它们的主要区别在于数据结构和检索方式： 1. **数据结构**： - HNSW使用多层邻近图结构，能够快速定位到目标区域并在下层进行精确搜索，适合高维数据和低延迟查询 [E4] |
| 2 | supported | 0.2406 | E4 | - IVF则通过聚类将向量分成多个“桶”，查询时先找到最相似的几个桶，再在这些桶内进行精确搜索 [E4] |
| 3 | partial | 0.2069 | E4 | **检索速度与召回率**： - HNSW提供较高的检索速度和召回率，尤其在处理高维数据时表现优异，但内存占用较大 [E4] |
| 4 | supported | 0.2450 | E4 | - IVF通过缩小搜索范围来提升检索速度，但召回率不是100%，因为相关向量可能被分到未搜索的桶中 [E4] |
| 5 | supported | 0.2283 | E4 | **适用场景**： - HNSW适合对查询延迟有严格要求的场景，如实时推荐和在线搜索 [E4] |
| 6 | partial | 0.2075 | E4 | - IVF适合需要高吞吐量的大规模数据集的通用场景 [E4] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: EXPLICIT_COMPARE 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: medium
- level_meaning: 不确定性/风险中等
- reasons: citation_weak
- missing_info: citation_support_label=partial；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 2,766.766
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 53
- total_tokens: 430
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `8b5e0862ad29c414b8db647c93b5b6c27a52633a27cfd28532d890b32a9ab841`
- answer_sha256: `6cc3802085f7bae1a684e7b4d23027043f00ed51be44637a48c48d04c7c5f593`

## q09 — Kubernetes control plane 包含哪些核心组件？

### 分类与回答边界

- actual_route: DIRECT
- question_type: OPEN_MULTI
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: high
- reason: 问题明确询问 Kubernetes control plane 的核心组件，信息可验证且范围清晰。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/08_Kubernetes基础架构.md@0-1115#f0413c5d9c86；internal/08_Kubernetes基础架构.md@1115-1993#1114731f27b6
- reason: 前两条证据直接且完整地列出了 Kubernetes control plane 的核心组件（API Server、etcd、Scheduler、Controller Manager），并提供了架构图和详细说明，足以回答用户问题。其余证据与问题无关，但不影响充分性。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 4
- unsupported_claim_count: 0

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/08_Kubernetes基础架构.md | internal/08_Kubernetes基础架构.md@0-1115#f0413c5d9c86 | 0.6686 |
| E2 | internal/08_Kubernetes基础架构.md | internal/08_Kubernetes基础架构.md@1115-1993#1114731f27b6 | 0.6252 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1911 | E1 | Kubernetes control plane 包含以下核心组件： 1. **API Server（kube-apiserver）**：K8s 的唯一入口，负责所有组件和客户端的交互 |
| 2 | partial | 0.1643 | E2 | **etcd**：分布式键值存储，保存集群的所有状态 |
| 3 | supported | 0.2224 | E2 | **Scheduler（kube-scheduler）**：负责将新建的 Pod 分配到合适的 Node |
| 4 | supported | 0.2335 | E2 | **Controller Manager（kube-controller-manager）**：多个控制器的集合，负责使实际状态趋向期望状态 [E1][E2] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: OPEN_MULTI 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: medium
- level_meaning: 不确定性/风险中等
- reasons: citation_weak
- missing_info: citation_support_label=partial；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,047.090
- model_call_count: 1
- prompt_tokens: 373
- completion_tokens: 52
- total_tokens: 425
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `8aac33e8800707ae1d89e601cae413b0eca2c71a9ed13852ef9042c9159249b6`
- answer_sha256: `fd6969489b67d178d4b72d1a5765a2b1534723374675122fa3d8130d0a9bcd1b`

## q10 — KV cache 在大模型推理中有什么作用？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: high
- reason: 问题明确，涉及 KV cache 在大模型推理中的作用，信息可验证且范围清晰。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/10_模型服务层vLLM架构.md@0-773#e9b11b984010；external/34-vllm_architecture_cn.md@5634-6214#2c8ba4fa9cdf
- reason: 证据包中第一条证据（internal/10_模型服务层vLLM架构.md@0-773#e9b11b984010）明确解释了KV cache的作用：缓存历史token的Key和Value矩阵，避免重复计算，将复杂度从O(n²)降为O(n)，并指出其代价是占用大量GPU显存。第二条证据（external/34-vllm_architecture_cn.md@5634-6214#2c8ba4fa9cdf）补充了KV cache的缓存管理策略，进一步说明其作用。这两条证据足以回答用户关于KV cache作用的问题。其余证据涉及vLLM参数调优和Milvus索引，与问题不直接相关，但不影响回答的充分性。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 3
- unsupported_claim_count: 0

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/10_模型服务层vLLM架构.md | internal/10_模型服务层vLLM架构.md@0-773#e9b11b984010 | 0.7072 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.2534 | E1 | KV Cache 在大模型推理中的作用是缓存历史 token 的 Key 和 Value 矩阵，以避免在每次生成新 token 时重复计算，从而降低计算复杂度 |
| 2 | partial | 0.1721 | E1 | 具体来说，使用 KV Cache 可以将复杂度从 O(n²) 降低到 O(n)，显著提高推理效率 |
| 3 | partial | 0.2018 | E1 | 然而，KV Cache 也会占用大量 GPU 显存，传统的 KV Cache 管理方式存在内存浪费和碎片化的问题 [E1] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: SUMMARY 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: medium
- level_meaning: 不确定性/风险中等
- reasons: citation_weak
- missing_info: citation_support_label=partial；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 2,716.048
- model_call_count: 1
- prompt_tokens: 374
- completion_tokens: 55
- total_tokens: 429
- estimated_cost_usd: 0.000089

### 追溯信息

- source_cer_sha256: `6b4989b50baad483ff1e3e91ef64165a89eaf4221a4fd5165aec916031e156d8`
- answer_sha256: `771ddefe2195c81d14d6f6c8b0e75d3975613169db31edb12da202610968cc38`

## q11 — Overlap 在文本分块中有什么作用？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: high
- reason: 问题明确，涉及文本分块的作用，答案可以清晰提供。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/02_Chunk策略.md@685-1391#5484310af4bf；external/14-text-chunking-datawhale.md@2550-3384#9b6f0029c9d2
- reason: 证据包中 internal/02_Chunk策略.md 的 2.3 节明确阐述了 Overlap 的定义、作用（防止跨边界信息丢失、保留上下文连贯性、提升边界附近检索召回率）、副作用及经验值，直接且完整地回答了用户问题。external/14-text-chunking-datawhale.md 的 3.1 节也提及 chunk_overlap 用于缓解语义割裂，作为补充佐证。证据之间无冲突，足以支撑回答。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 3
- unsupported_claim_count: 0

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E4 | internal/02_Chunk策略.md | internal/02_Chunk策略.md@685-1391#5484310af4bf | 0.6087 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.2211 | E4 | Overlap 在文本分块中的作用主要有两个： 1. **防止信息丢失**：通过在相邻的文本块之间共享一定数量的 token，Overlap 可以防止跨越边界的关键信息被切断而丢失，从而保持信息的完整性 |
| 2 | partial | 0.1761 | E4 | **提升上下文连贯性**：Overlap 有助于保留上下文的连贯性，特别是在边界附近，能够提升检索的召回率，使得相关信息更容易被捕捉到 |
| 3 | partial | 0.2117 | E4 | 然而，Overlap 也有副作用，如增加存储量和可能导致信息冗余，因此通常建议将其设置为 chunk_size 的 10%~20% [E4] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: SUMMARY 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: medium
- level_meaning: 不确定性/风险中等
- reasons: citation_weak
- missing_info: citation_support_label=partial；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,093.122
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 48
- total_tokens: 420
- estimated_cost_usd: 0.000085

### 追溯信息

- source_cer_sha256: `0139a6c167e9c33d2b01336331877fba77605c84414896a07e63e1e5ae098363`
- answer_sha256: `b98aa3390f078bdf791fbbdbb5758c063c5af6153484d05ef36fa250c607de60`

## q12 — Embedding 维度会影响哪些方面？

### 分类与回答边界

- actual_route: DIRECT
- question_type: OPEN_MULTI
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: medium
- reason: 问题明确询问影响方面，且可以列举多个相关因素。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/03_Embedding原理与向量空间.md@1106-1746#7cc4b717d45c
- reason: 证据包中第一条证据（internal/03_Embedding原理与向量空间.md@1106-1746#7cc4b717d45c）直接且完整地回答了用户问题，明确列出了Embedding维度对语义表达能力、内存与存储、检索延迟和维度灾难四个方面的影响，并提供了工程实践中的维度参考。该证据足以支撑回答问题的核心需求，无需额外信息。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 4
- unsupported_claim_count: 2

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/03_Embedding原理与向量空间.md | internal/03_Embedding原理与向量空间.md@1106-1746#7cc4b717d45c | 0.7832 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.2280 | E1 | Embedding 维度会影响以下几个方面： 1. **语义表达能力**：维度越高，理论上能编码越多信息，但收益递减 |
| 2 | partial | 0.2139 | E1 | **内存与存储**：维度越高，每个向量占用的空间越大（例如，float32格式下1维=4字节） |
| 3 | unsupported | 0.0406 | E1 | **检索延迟**：高维向量计算相似度的速度较慢，索引构建也更耗资源 |
| 4 | unsupported | 0.0403 | E1 | **维度灾难**：当维度极高时，所有点之间的距离趋于相等，可能导致检索失效 [E1] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: OPEN_MULTI 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=2；unsupported_claim；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 2,398.208
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 49
- total_tokens: 421
- estimated_cost_usd: 0.000085

### 追溯信息

- source_cer_sha256: `61319717161e4850e1096e204c7e4aefbc4c8b3a7c49ae46ae6ce965c19d0325`
- answer_sha256: `99cfc7f6ab9a34a2236d0057e769b85c5ff458eefc9c3e17eb59386f2a95807e`

## q13 — Embedding 是否真正“理解”语义？

### 分类与回答边界

- actual_route: DIRECT
- question_type: IMPLICIT_COMPARE
- answerability: NEEDS_CLARIFICATION
- route_candidate: NEEDS_CLARIFICATION
- confidence: medium
- reason: 问题缺少对比对象，无法明确理解'理解'的标准和范围。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/03_Embedding原理与向量空间.md@1106-1746#7cc4b717d45c；internal/03_Embedding原理与向量空间.md@0-685#6f797c7d21d6；external/16-vector-embedding-datawhale.md@804-1403#9a28961b0343
- reason: 证据包中直接包含回答该问题的核心内容：internal/03_Embedding原理与向量空间.md 的第五节明确回答了'Embedding 是否理解语义'，指出其捕捉的是语义的统计规律而非人类意义上的理解，并列举了典型局限（否定词不敏感、精确数字和代码逻辑捕捉弱）。同时，该文档的第一节和外部文档提供了 Embedding 的工作原理（对比学习、上下文感知）及其在 RAG 中的作用，共同支撑了'Embedding 通过统计规律实现语义相似性而非真正理解'的结论。各证据之间不存在冲突，足以回答用户问题。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 3
- unsupported_claim_count: 1

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/03_Embedding原理与向量空间.md | internal/03_Embedding原理与向量空间.md@1106-1746#7cc4b717d45c | 0.6552 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1932 | E1 | Embedding 模型并不真正“理解”语义，而是捕捉语义的统计规律 |
| 2 | unsupported | 0.0852 | E1 | 它通过大量文本训练，将经常出现在相似上下文中的文本映射到相近的向量位置，能够处理语义相似性，但对逻辑推理和因果关系等高阶理解能力有限 |
| 3 | partial | 0.1957 | E1 | 此外，Embedding 对否定词和精确数字的敏感度较低，可能导致相似的向量表示不同的语义内容 [E1] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: IMPLICIT_COMPARE 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=1；unsupported_claim；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 2,333.585
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 56
- total_tokens: 428
- estimated_cost_usd: 0.000089

### 追溯信息

- source_cer_sha256: `eb1e33116e1e2f0514f46e2cce041b447f7f0aab9d46feeeff89f96e1d64a31a`
- answer_sha256: `c8536640881c6b08389f1375752eebfcbca917cf298680eeb8a939ec487bc3ef`

## q14 — 什么叫 evidence insufficient（证据不充分）？

### 分类与回答边界

- actual_route: DIRECT
- question_type: NARROW_FACT
- answerability: IN_SCOPE
- route_candidate: DIRECT
- confidence: high
- reason: 问题明确，询问的是对特定术语的定义，且可以提供清晰的解释。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/04_RAG失败模式.md@1332-1937#311a87398ac2；internal/04_RAG失败模式.md@0-639#222aea480737
- reason: 证据包中两个来自 internal/04_RAG失败模式.md 的 chunk 直接定义了证据充分性（Evidence Sufficiency）及证据不充分的判断标准，包括定义、判断标准（如包含检索内容以外的推断、多跳推理链条不完整、缺乏具体数据）和工程实现，足以回答用户关于'什么叫 evidence insufficient（证据不充分）'的问题。其他 chunk 与问题不相关，但不影响回答。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 4
- unsupported_claim_count: 3

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/04_RAG失败模式.md | internal/04_RAG失败模式.md@1332-1937#311a87398ac2 | 0.6815 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1411 | E1 | “证据不充分”（evidence insufficient）指的是在回答问题时，检索到的内容未能提供足够的信息来支持每个关键声明 |
| 2 | unsupported | 0.0369 | E1 | 这种情况的判断标准包括： 1. 回答中包含了检索内容以外的推断 |
| 3 | unsupported | 0.0357 | E1 | 关键问题需要多跳推理，但仅召回了部分链条 |
| 4 | unsupported | 0.0415 | E1 | 检索结果虽然覆盖了话题方向，但缺乏具体数据或细节 [E1] |

### 冲突检测（规则型疑似冲突）

- triggered: false
- conflict_count: 0
- trigger_reason: NARROW_FACT 不在规则触发类型中，不执行冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=3；unsupported_claim；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,435.578
- model_call_count: 1
- prompt_tokens: 374
- completion_tokens: 57
- total_tokens: 431
- estimated_cost_usd: 0.000090

### 追溯信息

- source_cer_sha256: `37bb8cc9f52d03ef6cb26654bffa61da4da388486fd2620d4e0263f45b030582`
- answer_sha256: `1d6e7d7003984864b7a38e1018f944a0d19b0d79c76e2b7eb324e7a1a6e62e4e`

## q15 — 检索错但回答对，在 RAG 评估里算成功吗？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: NEEDS_CLARIFICATION
- route_candidate: NEEDS_CLARIFICATION
- confidence: medium
- reason: 问题缺少对成功标准的具体定义，无法明确判断。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/04_RAG失败模式.md@1332-1937#311a87398ac2；internal/04_RAG失败模式.md@0-639#222aea480737
- reason: 证据包中第2条（internal/04_RAG失败模式.md@1332-1937）明确回答了用户问题：'检索错但回答对'不算成功，应标记为'Retrieval Failed, Answer Lucky'，不计入正确。第1条（internal/04_RAG失败模式.md@0-639）也提供了相关背景，指出检索正确但回答错误不算成功，从反面支持了'正确性必须来自可追溯的检索证据'的原则。两条证据一致，无冲突，足以支撑回答。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 3
- unsupported_claim_count: 0

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E2 | internal/04_RAG失败模式.md | internal/04_RAG失败模式.md@1332-1937#311a87398ac2 | 0.5874 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1651 | E2 | 检索错但回答对在 RAG 评估里不算成功 |
| 2 | partial | 0.1850 | E2 | 虽然最终回答可能正确，但这源于 LLM 的参数记忆，而非可追溯的检索证据，因此不被视为成功 |
| 3 | supported | 0.2744 | E2 | 这种情况应标记为“Retrieval Failed, Answer Lucky”，不计入正确 [E2] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: SUMMARY 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: medium
- level_meaning: 不确定性/风险中等
- reasons: citation_weak
- missing_info: citation_support_label=partial；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,908.402
- model_call_count: 1
- prompt_tokens: 380
- completion_tokens: 50
- total_tokens: 430
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `367536dfbfd79cd0b30dc8f1ce82002771e6d7696c9e386b53a71484a807fdcf`
- answer_sha256: `0e5c4e3330ea35dde6ded43611651b2c78bf3233e9eae1345a0260309849a0a4`

## q16 — pgvector 和专用向量数据库相比，有什么主要差异？

### 分类与回答边界

- actual_route: DECOMPOSE
- question_type: EXPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: high
- reason: 问题明确比较了 pgvector 和专用向量数据库，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/05_pgvector原理.md@1303-1989#f133a907d82c；external/21-pgvector补充.md@1399-1578#b78856dc35be
- reason: 证据包包含直接对比 pgvector 与专用向量数据库的表格（internal/05_pgvector原理.md 第4节），涵盖架构、集成成本、查询吞吐、过滤检索、事务/ACID、量化压缩、适用规模、运维复杂度等关键维度，并给出结论性建议；external/21-pgvector补充.md 第7节补充了优势与局限的工程侧总结。两份证据内容一致、互补，足以支撑回答用户问题。其余证据为背景信息，不影响充分性判断。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 8
- unsupported_claim_count: 1

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E2 | internal/05_pgvector原理.md | internal/05_pgvector原理.md@1303-1989#f133a907d82c | 0.0320 |
| E1 | external/21-pgvector补充.md | external/21-pgvector补充.md@1399-1578#b78856dc35be | 0.0323 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.3012 | E2 | pgvector 和专用向量数据库（如 Qdrant、Milvus）之间的主要差异包括： 1. **架构**：pgvector 是 PostgreSQL 的扩展，而专用向量数据库是独立的数据库系统 [E2] |
| 2 | supported | 0.3899 | E1 | **集成成本**：pgvector 的集成成本较低，因为可以复用已有的 PostgreSQL 栈 |
| 3 | unsupported | 0.0224 | E2 | 而专用向量数据库需要独立部署和维护 [E2] |
| 4 | supported | 0.2857 | E2 | **查询吞吐量**：pgvector 的查询吞吐量中等（约百级 QPS），而专用向量数据库的吞吐量较高（如 Qdrant 超过 4000 RPS） [E2] |
| 5 | supported | 0.2222 | E2 | **事务支持**：pgvector 完整支持事务和 ACID 特性，而专用向量数据库的事务支持有限或不支持 [E2] |
| 6 | supported | 0.2691 | E1 | **适用规模**：pgvector 适用于小于 1000 万向量的场景，而专用向量数据库可以处理亿级向量 [E2] |
| 7 | supported | 0.2496 | E1 | **运维复杂度**：pgvector 的运维复杂度较低，因为与业务数据同库，而专用向量数据库的运维复杂度中等到高 [E2] |
| 8 | supported | 0.4640 | E1 | 综上所述，pgvector 更适合中小规模、强调与 PostgreSQL 集成的场景，而专用向量数据库则适合大规模、高性能的向量检索需求 [E1][E2] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: EXPLICIT_COMPARE 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=1；unsupported_claim
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,106.126
- model_call_count: 1
- prompt_tokens: 378
- completion_tokens: 52
- total_tokens: 430
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `ecbef275815ffd495785a25c68b57a6dbbcf9459d17b41226a73ccc527535a4a`
- answer_sha256: `cd4dea6b0262962928aa19687a0d0c2b56b6331d568724d92c3d32dd5886a82d`

## q17 — Qdrant 的内存存储和磁盘存储有什么差异？

### 分类与回答边界

- actual_route: DIRECT
- question_type: EXPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: high
- reason: 问题明确比较了 Qdrant 的内存存储和磁盘存储，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/06_Qdrant架构.md@965-1773#50531ea08667
- reason: 证据包中的第一个证据（internal/06_Qdrant架构.md@965-1773#50531ea08667）直接回答了用户问题，明确列出了Qdrant的三种存储模式（In-Memory、Mmap、On-disk）及其在性能、成本上的差异，并提供了配置示例。该证据来自内部文档且章节标题即为“存储模式（内存/磁盘差异）”，内容充分覆盖了内存存储与磁盘存储的核心差异。其他证据涉及Kubernetes和Milvus，与Qdrant无关，但不影响回答的充分性。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 5
- unsupported_claim_count: 2

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/06_Qdrant架构.md | internal/06_Qdrant架构.md@965-1773#50531ea08667 | 0.7167 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.2157 | E1 | Qdrant 的内存存储和磁盘存储主要有以下差异： 1. **存储模式**： - **内存存储（In-Memory）**：向量完全加载到 RAM 中，提供最快的性能，但内存成本较高 |
| 2 | partial | 0.1974 | E1 | - **磁盘存储**： - **Mmap（Memory-mapped）**：向量存储在磁盘上，由操作系统进行缓存管理，性能中等，成本相对友好 |
| 3 | partial | 0.1907 | E1 | - **On-disk（量化+磁盘）**：量化向量存储在磁盘上，原始向量用于重新排序，性能较慢，但成本最低 [E1] |
| 4 | unsupported | 0.0177 | E1 | **性能与成本**： - 内存存储提供最佳性能，但成本高 |
| 5 | unsupported | 0.0174 | E1 | 而磁盘存储则在性能和成本之间提供不同的平衡，适合不同的使用场景 [E1] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: EXPLICIT_COMPARE 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=2；unsupported_claim；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,271.992
- model_call_count: 1
- prompt_tokens: 380
- completion_tokens: 57
- total_tokens: 437
- estimated_cost_usd: 0.000091

### 追溯信息

- source_cer_sha256: `b3e4bb95fe82c95b2574060fe46912716125cb19a10daf6b207c70872ad7bbe9`
- answer_sha256: `e8904487ade0840577127b9e63cd841890c9cc42c1a0258d3353b2e145da0c67`

## q18 — Recall 和 latency 在向量检索中为什么需要权衡？

### 分类与回答边界

- actual_route: DIRECT
- question_type: IMPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: medium
- reason: 问题涉及两个概念的关系，但未明确指出具体的比较标准。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/07_向量索引算法HNSW与IVF.md@1558-2289#f09b34881aa0；internal/07_向量索引算法HNSW与IVF.md@0-301#a87f5dd9a27c；external/22-milvus-datawhale.md@5576-6211#1e7ee82d83d9
- reason: 证据包中第4条证据（internal/07_向量索引算法HNSW与IVF.md@1558-2289）明确解释了Recall与Latency的权衡关系，包括HNSW的ef_search和IVF的nprobe参数对两者的影响，以及90%到99%召回率需要2-5倍查询时间的经验法则。第3条证据（internal/07_向量索引算法HNSW与IVF.md@0-301）提供了ANN检索牺牲精度换取速度的背景。第1条证据（external/22-milvus-datawhale.md@5576-6211）也提到ANN是速度和精度之间的平衡策略。这些证据共同充分回答了用户问题，且无冲突。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 7
- unsupported_claim_count: 0

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E4 | internal/07_向量索引算法HNSW与IVF.md | internal/07_向量索引算法HNSW与IVF.md@1558-2289#f09b34881aa0 | 0.6188 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1896 | E4 | 在向量检索中，Recall（召回率）和Latency（延迟）之间需要权衡的原因在于，提升Recall通常会导致Latency的增加 |
| 2 | partial | 0.1616 | E4 | 具体来说： 1. **Recall的提升**：为了提高Recall，检索算法需要考虑更多的候选向量，这通常意味着增加查询的复杂度 |
| 3 | partial | 0.2085 | E4 | 例如，在HNSW算法中，增加`ef_search`参数可以提高Recall，但同时也会增加查询的延迟 |
| 4 | supported | 0.2253 | E4 | 在IVF算法中，增加`nprobe`参数同样会提高Recall，但也会导致Latency上升 [E4] |
| 5 | partial | 0.1971 | E4 | **性能与精度的平衡**：在实际应用中，通常需要在Recall和Latency之间找到一个合适的平衡点，以满足业务需求 |
| 6 | partial | 0.1785 | E4 | 经验法则表明，从90%到99%的Recall提升，可能需要2到5倍的查询时间代价 [E4] |
| 7 | partial | 0.1856 | E4 | 因此，系统设计者必须根据具体的应用场景和性能要求，合理调整参数，以实现Recall和Latency之间的最佳平衡 [E4] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: IMPLICIT_COMPARE 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: medium
- level_meaning: 不确定性/风险中等
- reasons: citation_weak
- missing_info: citation_support_label=partial；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 2,096.741
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 51
- total_tokens: 428
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `0d1e0bc81f295a36e235ac96db4198bc93ba5352a078c24fc9847e9f3729b5ea`
- answer_sha256: `fcb9885ef2343b1e43d23501a5732c47543c3f37c65ae1b1eb24c6c6b3fd95ea`

## q19 — kube-scheduler 在 Kubernetes 集群里负责什么？

### 分类与回答边界

- actual_route: DIRECT
- question_type: NARROW_FACT
- answerability: IN_SCOPE
- route_candidate: DIRECT
- confidence: high
- reason: 问题明确询问 kube-scheduler 的职责，且信息可验证。

### 证据充分性

- raw_verdict: INSUFFICIENT
- control_verdict: INSUFFICIENT
- confidence: high
- missing_evidence: 明确说明 kube-scheduler 职责（如为新 Pod 选择合适节点、考虑资源需求/约束/亲和性等）的文档片段
- reason: 证据包中仅有一个片段（internal/08_Kubernetes基础架构.md）在架构图中提及 Scheduler 组件，但未提供任何关于其具体职责的描述；其余片段均来自 Kubernetes 网络文档，与调度器无关。因此，当前证据无法回答用户关于 kube-scheduler 负责什么的问题。

### 引用证据支撑（规则）

- citation_support_label: not_applicable
- citation_count: 0
- resolved_citation_count: 0
- unresolved_citation_count: 0
- claim_count: 0
- unsupported_claim_count: 0

### 冲突检测（规则型疑似冲突）

- triggered: false
- conflict_count: 0
- trigger_reason: NARROW_FACT 不在规则触发类型中，不执行冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: refused；sufficiency_insufficient
- missing_info: insufficient_evidence_after_reretrieve；明确说明 kube-scheduler 职责（如为新 Pod 选择合适节点、考虑资源需求/约束/亲和性等）的文档片段；证据包中仅有一个片段（internal/08_Kubernetes基础架构.md）在架构图中提及 Scheduler 组件，但未提供任何关于其具体职责的描述；其余片段均来自 Kubernetes 网络文档，与调度器无关。因此，当前证据无法回答用户关于 kube-scheduler 负责什么的问题。
- safe_answer_boundary: 当前证据不足，回答边界应限制在已检索到的证据范围内，不能补全缺失信息。

### D-full 后置评测耗时与用量

- offline_total_ms: 2,301.714
- model_call_count: 1
- prompt_tokens: 375
- completion_tokens: 51
- total_tokens: 426
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `ca1c50cfaee3eea49d1299b3bf5b73ec555feb411954092bc72c39e1899bf44d`
- answer_sha256: `76bf36d8ac30d8cd4dbfdd22e7e40a5be87f2d4e53ad995d12f1147b903196cf`

## q20 — 连续批处理（Continuous Batching）和传统静态批处理有什么区别？

### 分类与回答边界

- actual_route: DECOMPOSE
- question_type: EXPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: high
- reason: 问题明确要求比较两个处理方式的区别，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/10_模型服务层vLLM架构.md@773-1705#c76695ac0bf6
- reason: 证据包中的第一条证据（internal/10_模型服务层vLLM架构.md）直接包含了'4. 动态批处理（Continuous Batching）'章节，明确对比了传统静态批处理（所有请求同时开始，等最长的请求完成后才能接受新请求，短请求完成后GPU空等）和连续批处理（时间步T1处理[Req1,Req2,Req3,Req4]，T2时Req1完成立即插入Req5，无需等待其他请求，GPU始终满载）的区别，并给出了吞吐量提升数据。该证据足以回答用户问题。其余证据（Kubernetes存储、RAG综述）与问题无关，但不影响充分性判断。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 3
- unsupported_claim_count: 1

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/10_模型服务层vLLM架构.md | internal/10_模型服务层vLLM架构.md@773-1705#c76695ac0bf6 | 0.0489 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.2392 | E1 | 连续批处理（Continuous Batching）与传统静态批处理的主要区别在于请求处理的方式： 1. **传统静态批处理**：所有请求同时开始，必须等到最长的请求完成后才能接受新请求，这导致短请求完成后GPU空闲，利用率低 [E1] |
| 2 | unsupported | 0.0347 | E1 | **连续批处理**：在处理请求时，一旦某个请求完成，可以立即插入新的请求，而无需等待其他请求完成 |
| 3 | partial | 0.1461 | E1 | 这种方式使得GPU始终保持满载，显著提升了吞吐量 [E1] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: EXPLICIT_COMPARE 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=1；unsupported_claim；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 2,025.196
- model_call_count: 1
- prompt_tokens: 380
- completion_tokens: 50
- total_tokens: 430
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `8055feb1c2fc0b2290956e2a957550092dd7353d6c6e61edd083567324775c3e`
- answer_sha256: `69b7d66f599f27c62905ed14d4838c6180dd00c74c59e336ab5ff59d9c8f1bc5`

## q21 — RAG 中 embedding 和 retrieval 之间的关系是什么？

### 分类与回答边界

- actual_route: DIRECT
- question_type: IMPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: medium
- reason: 问题涉及两个概念的关系，但未明确要求比较形式

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: external/16-vector-embedding-datawhale.md@804-1403#9a28961b0343；internal/01_RAG基础原理.md@871-1622#b2cf54881a08
- reason: 证据包中的两个核心片段直接回答了问题：external/16-vector-embedding-datawhale.md 明确说明 Embedding 是语义检索的基础，并详细描述了离线索引构建、在线查询检索、相似度计算和召回上下文的流程，指出 Embedding 质量决定检索质量；internal/01_RAG基础原理.md 明确说明 Embedding 发生在索引和检索两个阶段，且必须使用同一个模型，否则检索结果无意义。两者共同清晰阐述了 embedding 与 retrieval 的关系，足以支撑回答。其余片段提供背景信息，无冲突。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 10
- unsupported_claim_count: 3

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E2 | internal/01_RAG基础原理.md | internal/01_RAG基础原理.md@871-1622#b2cf54881a08 | 0.6534 |
| E1 | external/16-vector-embedding-datawhale.md | external/16-vector-embedding-datawhale.md@804-1403#9a28961b0343 | 0.6795 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.2220 | E2 | 在 RAG（检索增强生成）中，embedding 和 retrieval 之间的关系是密切相关的 |
| 2 | supported | 0.2886 | E1 | 具体来说，embedding 在 RAG 的“检索”环节中起着核心作用，主要体现在以下几个方面： 1. **索引和检索阶段**：在 RAG 流程中，embedding 发生在两个关键阶段：索引阶段和检索阶段 |
| 3 | unsupported | 0.0211 | E1 | 在索引阶段，文档块被转换为向量并存入向量数据库 |
| 4 | unsupported | 0.0207 | E1 | 在检索阶段，用户的查询也被转换为向量，以便进行相似度匹配 |
| 5 | partial | 0.2107 | E1 | 这两个阶段必须使用同一个 embedding 模型，以确保向量空间的一致性，从而保证检索结果的有效性 [E2] |
| 6 | supported | 0.2800 | E1 | **语义检索的基础**：RAG 的检索环节依赖于基于 embedding 的语义搜索 |
| 7 | unsupported | 0.0679 | E1 | 用户的问题和文档块的向量通过相似度计算来确定相关性，选取相似度最高的文档块作为上下文信息，供大语言模型生成最终答案 [E1] |
| 8 | supported | 0.2237 | E1 | **检索质量的决定因素**：embedding 的质量直接影响检索的准确性和相关性 |
| 9 | supported | 0.2428 | E1 | 一个优秀的 embedding 模型能够更好地捕捉问题与文档之间的深层语义联系，从而提高检索的效果 [E1] |
| 10 | supported | 0.2711 | E1 | 综上所述，embedding 是 RAG 中检索过程的基础，确保了信息的有效检索和生成的准确性 |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: IMPLICIT_COMPARE 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=3；unsupported_claim；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 2,114.727
- model_call_count: 1
- prompt_tokens: 375
- completion_tokens: 48
- total_tokens: 423
- estimated_cost_usd: 0.000085

### 追溯信息

- source_cer_sha256: `2f18aa82367f92924a4ce615218604835db3f89ba9050082ff8710325357347b`
- answer_sha256: `48e27aadb319d3a4ced9a17337066172049a3533b5f3cc59448650bd5f1b400c`

## q22 — 为什么 chunk 不是越大越好？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: medium
- reason: 问题明确，涉及对 chunk 大小的整体理解，但可能需要更多背景信息来详细回答。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/02_Chunk策略.md@1391-1768#5c5d7a6818b5；internal/02_Chunk策略.md@0-685#1411d3bdb16d
- reason: 证据包中两个来自 internal/02_Chunk策略.md 的 chunk 直接回答了问题：第一个 chunk 明确列出 chunk 过大的缺点（检索精度下降、占用更多 context 窗口、embedding 向量语义混杂），第二个 chunk 也指出 chunk 太大导致噪声多、相关性稀释。这些信息足以支撑回答'为什么 chunk 不是越大越好'。其他 chunk 与问题无关，但不影响充分性。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 5
- unsupported_claim_count: 0

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/02_Chunk策略.md | internal/02_Chunk策略.md@1391-1768#5c5d7a6818b5 | 0.6013 |
| E2 | internal/02_Chunk策略.md | internal/02_Chunk策略.md@0-685#1411d3bdb16d | 0.4755 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.2241 | E1 | Chunk 不是越大越好，主要原因包括： 1. **检索精度下降**：过大的 chunk 会导致相关内容被噪声稀释，从而降低检索的准确性 [E1] |
| 2 | partial | 0.2060 | E1 | **上下文不完整**：过小的 chunk 则可能导致上下文信息丢失，影响理解 [E2] |
| 3 | supported | 0.3182 | E1 | **占用更多 LLM context 窗口**：过大的 chunk 会占用更多的上下文窗口，限制可处理的信息量 [E1] |
| 4 | supported | 0.2800 | E1 | **embedding 向量语义混杂**：过大的 chunk 可能导致语义混合，影响向量的质量 [E1] |
| 5 | partial | 0.1965 | E1 | 因此，选择合适的 chunk 大小是确保检索和生成质量的关键 |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: SUMMARY 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: medium
- level_meaning: 不确定性/风险中等
- reasons: citation_weak
- missing_info: citation_support_label=partial；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 2,421.696
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 54
- total_tokens: 426
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `1cc9a13d9e4e864a0d59396851aaf37e954fadf7b31e5179b422141797dabce3`
- answer_sha256: `5b0f77a30afb1674cda6370fb2bfc2219ca4d3d88fb0c7ea3775db6572488fa6`

## q23 — 语义分块相比固定分块的主要优势是什么？

### 分类与回答边界

- actual_route: DECOMPOSE
- question_type: EXPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: high
- reason: 问题明确比较了语义分块和固定分块，且可以提供可验证的优势信息。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: external/12-检索增强生成 (RAG) 技术综述-syhya.md@1237-1865#09b01ab21d25；external/14-text-chunking-datawhale.md@4870-5633#4375c0b9c1b3
- reason: 证据包中多个片段直接描述了语义分块与固定分块的区别。片段1（external/12...）明确指出固定大小分块'简单但可能切断语义单元'，而语义分块'利用NLP技术识别语义边界'，隐含了保持语义完整性的优势。片段3（external/14...@4870-5633）更明确地对比了语义分块与固定分块：语义分块'不依赖于固定的字符数或预设的分隔符'，'在语义主题发生显著变化的地方进行切分'，使每个分块具有'高度的内部语义一致性'，而固定分块遇到超长段落只能警告保留。这些信息足以归纳出语义分块相比固定分块的主要优势：保持语义完整性、避免切断语义单元、提高块内语义一致性。因此证据充分。

### 引用证据支撑（规则）

- citation_support_label: unsupported
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 3
- unsupported_claim_count: 3

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | external/12-检索增强生成 (RAG) 技术综述-syhya.md | external/12-检索增强生成 (RAG) 技术综述-syhya.md@1237-1865#09b01ab21d25 | 0.0481 |
| E4 | external/14-text-chunking-datawhale.md | external/14-text-chunking-datawhale.md@4068-4870#3e955ac4ad9e | 0.0323 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | unsupported | 0.0218 | E1 | 语义分块相比固定分块的主要优势在于它能够根据文本的语义内涵进行切分，从而保持每个分块的内部语义一致性 |
| 2 | unsupported | 0.0304 | E1 | 这种方法在语义主题发生显著变化的地方进行切分，避免了固定大小分块可能导致的语义单元被切断的问题 |
| 3 | unsupported | 0.0136 | E1 | 此外，语义分块能够更好地适应文本的结构和内容，提升信息的理解和处理效果 [E1][E4] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: EXPLICIT_COMPARE 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=unsupported；unsupported_claim_count=3；unsupported_claim
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,395.709
- model_call_count: 1
- prompt_tokens: 376
- completion_tokens: 56
- total_tokens: 432
- estimated_cost_usd: 0.000090

### 追溯信息

- source_cer_sha256: `59a2899fc9a56be9a95b0bfbddc6dc32feddbb44abe48810b6e6eb7159d4066c`
- answer_sha256: `83480fd6acc5959ac24f161cc36ef2921541533f7e396b31973b19bd8d1dfa22`

## q24 — Embedding 在 RAG 系统中主要起什么作用？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: high
- reason: 问题明确，涉及 RAG 系统中嵌入的作用，信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: external/16-vector-embedding-datawhale.md@804-1403#9a28961b0343；internal/01_RAG基础原理.md@871-1622#b2cf54881a08
- reason: 证据包中第一条证据（external/16-vector-embedding-datawhale.md）专门论述了Embedding在RAG中的作用，包括作为语义检索的基础、决定检索质量等核心内容；第二条证据（internal/01_RAG基础原理.md）补充说明了Embedding在索引和检索两个阶段的发生位置及必须使用同一模型的要求。两者共同覆盖了用户问题的核心需求，足以支撑回答。其余证据为背景性内容，不构成冲突。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 4
- unsupported_claim_count: 0

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | external/16-vector-embedding-datawhale.md | external/16-vector-embedding-datawhale.md@804-1403#9a28961b0343 | 0.7542 |
| E2 | internal/01_RAG基础原理.md | internal/01_RAG基础原理.md@871-1622#b2cf54881a08 | 0.6469 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.3213 | E1 | 在 RAG（检索增强生成）系统中，Embedding 主要起到以下作用： 1. **语义检索的基础**：Embedding 是 RAG 流程中“检索”环节的核心，负责将知识库中的文档块和用户查询转换为向量，以便进行相似度计算和检索相关文档块 [E1] |
| 2 | supported | 0.2237 | E1 | **检索质量的关键**：Embedding 的质量直接影响检索结果的准确性和相关性 |
| 3 | supported | 0.2472 | E1 | 优秀的 Embedding 模型能够捕捉问题与文档之间的深层语义联系，从而提高最终生成答案的质量 [E1] |
| 4 | partial | 0.2140 | E1 | **发生在两个阶段**：Embedding 在索引阶段和检索阶段都发挥作用，必须使用同一个模型以确保向量空间的一致性 [E2] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: SUMMARY 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: medium
- level_meaning: 不确定性/风险中等
- reasons: citation_weak
- missing_info: citation_support_label=partial；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,140.492
- model_call_count: 1
- prompt_tokens: 375
- completion_tokens: 52
- total_tokens: 427
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `7fd5f41fdb2e1f4eebf2561eb5cc178677ce02b34d19420f4e72a51f57af5481`
- answer_sha256: `32758eb14806f76f5a23a46b2f8187fb6ca5af94e8011642218a4371a86fe5b0`

## q25 — RAG 系统中，检索阶段的错误会如何影响最终回答？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: high
- reason: 问题明确，涉及检索阶段错误对回答的影响，且可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/04_RAG失败模式.md@0-639#222aea480737；external/11_RAG_intro.md@3858-4404#83cbfcf736af；external/18-GraphRAG-datawhale.md@563-1098#80819dfa2d8d；external/18-GraphRAG-datawhale.md@0-563#1ab5e3b347b7
- reason: 证据包中的核心文档（internal/04_RAG失败模式.md）直接且系统地回答了检索阶段错误的影响，明确区分了召回不准（低精度）导致噪声上下文和错误回答、召回遗漏（低召回）导致证据不足和幻觉风险，以及检索正确但生成错误的边界情况。其他外部文档（11_RAG_intro.md、18-GraphRAG-datawhale.md）从检索依赖性和检索噪声角度提供了补充佐证，一致支持检索错误会引发幻觉或错误回答的结论。各证据之间无冲突，信息充分覆盖用户问题的核心需求。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 4
- unsupported_claim_count: 2

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/04_RAG失败模式.md | internal/04_RAG失败模式.md@0-639#222aea480737 | 0.6917 |
| E3 | external/18-GraphRAG-datawhale.md | external/18-GraphRAG-datawhale.md@563-1098#80819dfa2d8d | 0.6353 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.4371 | E3 | 在RAG系统中，检索阶段的错误会对最终回答产生显著影响，主要体现在以下几个方面： 1. **召回不准（低精度）**：如果检索到的内容与用户问题不相关，LLM将获得噪声上下文，从而生成错误或无意义的回答 [E1] |
| 2 | unsupported | 0.0548 | E1 | **召回遗漏（低召回）**：当相关文档未被检索到时，系统可能会面临证据不足的情况，虽然应拒绝回答，但可能会产生幻觉作答 [E1] |
| 3 | supported | 0.3296 | E3 | **检索噪声与幻觉风险**：检索过程返回不相关或部分相关的信息，可能干扰LLM的判断，导致生成与事实不符的内容 [E3] |
| 4 | unsupported | 0.0138 | E3 | 因此，检索阶段的错误直接影响到生成阶段的质量和准确性，可能导致错误信息的传播和用户体验的下降 |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: SUMMARY 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=2；unsupported_claim
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 2,231.476
- model_call_count: 1
- prompt_tokens: 380
- completion_tokens: 50
- total_tokens: 430
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `da12ebb6f11c09e47d438aa3ac1b0feb26a3e64fc74618e503d545f73e456eb7`
- answer_sha256: `28aa25a083384c27a27d4185ceb8284d134820e10f8e7f853c4f47ea08a2f40f`

## q26 — IVF 索引相比 HNSW 的主要特点是什么？

### 分类与回答边界

- actual_route: DECOMPOSE
- question_type: EXPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: high
- reason: 问题明确比较 IVF 索引和 HNSW 的特点，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: external/22-milvus-datawhale.md@4526-5014#fc79b169f6c2；external/26-Milvus-索引解释.md@3003-3627#3603b200df69；internal/05_pgvector原理.md@682-1303#b9f400273076
- reason: 证据包中多个来源直接对比了IVF和HNSW的特点，包括原理、优缺点、适用场景、内存使用和构建方式等，足以回答用户问题。第一份证据详细列出了IVF和HNSW各自的原理、优点、缺点和适用场景；第二份证据提供了决策矩阵和内存使用对比；第三份证据从pgvector角度补充了IVF和HNSW的构建特点。这些信息相互补充，无冲突，足以支撑回答。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 9
- unsupported_claim_count: 2

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | external/22-milvus-datawhale.md | external/22-milvus-datawhale.md@4526-5014#fc79b169f6c2 | 0.0328 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.3300 | E1 | IVF（倒排文件索引）和HNSW（基于图的索引）在原理、优缺点和适用场景上有显著差异： 1. **原理**： - **IVF**：通过聚类将向量分成多个“桶”，查询时先找到最相似的几个桶，再在这些桶内进行精确搜索 |
| 2 | supported | 0.2698 | E1 | [E1] - **HNSW**：构建一个多层的邻近图，查询时从稀疏图开始，快速定位到目标区域，然后在密集图中进行精确搜索 |
| 3 | supported | 0.2214 | E1 | [E1] 2. **优缺点**： - **IVF**： - 优点：提升检索速度，适合高吞吐量的大规模数据集 |
| 4 | unsupported | 0.0320 | E1 | [E1] - 缺点：召回率不是100%，可能漏掉相关向量 |
| 5 | supported | 0.2308 | E1 | [E1] - **HNSW**： - 优点：检索速度极快，召回率高，适合高维数据和低延迟查询 |
| 6 | unsupported | 0.0257 | E1 | [E1] - 缺点：内存占用大，构建索引时间较长 |
| 7 | supported | 0.2333 | E1 | [E1] 3. **适用场景**： - **IVF**：通用场景，尤其适合需要高吞吐量的大规模数据集 |
| 8 | supported | 0.2245 | E1 | [E1] - **HNSW**：对查询延迟有严格要求的场景，如实时推荐和在线搜索 |
| 9 | supported | 0.2536 | E1 | [E1] 综上所述，IVF适合大规模数据集的高吞吐量需求，而HNSW则更适合对查询速度和召回率有高要求的应用 |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: EXPLICIT_COMPARE 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=2；unsupported_claim
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,861.788
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 54
- total_tokens: 431
- estimated_cost_usd: 0.000089

### 追溯信息

- source_cer_sha256: `886ca5367f11e1d3f32bd7eed0971764e0c4da6ede4bda6d9a1d8f740013aa19`
- answer_sha256: `524df6831744fe0390387c35edec6c96fadcf65132caf59a7e50686ecce1e823`

## q27 — 为什么 HNSW 通常具有更高的检索精度？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: high
- reason: 问题明确，涉及 HNSW 的检索精度，且可以提供相关的总结性回答。

### 证据充分性

- raw_verdict: INSUFFICIENT
- control_verdict: INSUFFICIENT
- confidence: medium
- missing_evidence: 直接解释 HNSW 为何通常比 IVF 等算法具有更高检索精度的证据，例如 HNSW 的图结构、分层导航、贪婪搜索等机制如何减少近似误差。
- reason: 当前证据包中没有任何一条证据直接解释 HNSW 为何通常具有更高的检索精度。证据1（Milvus 索引解释）仅提及精炼器提高召回率，未涉及 HNSW 的精度优势；证据2（milvus-datawhale）介绍过滤检索、范围检索等，与 HNSW 精度无关；证据3（HNSW与IVF）仅介绍 ANN 问题背景，未比较精度；证据4（Qdrant架构）列出 HNSW 参数，但未解释精度优势；证据5（RAG综述）仅提及 HNSW 是常见 ANN 算法，未展开。因此，缺少回答该问题的核心信息。

### 引用证据支撑（规则）

- citation_support_label: not_applicable
- citation_count: 0
- resolved_citation_count: 0
- unresolved_citation_count: 0
- claim_count: 0
- unsupported_claim_count: 0

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: SUMMARY 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: refused；sufficiency_insufficient
- missing_info: insufficient_evidence_after_reretrieve；直接解释 HNSW 为何通常比 IVF 等算法具有更高检索精度的证据，例如 HNSW 的图结构、分层导航、贪婪搜索等机制如何减少近似误差。；当前证据包中没有任何一条证据直接解释 HNSW 为何通常具有更高的检索精度。证据1（Milvus 索引解释）仅提及精炼器提高召回率，未涉及 HNSW 的精度优势；证据2（milvus-datawhale）介绍过滤检索、范围检索等，与 HNSW 精度无关；证据3（HNSW与IVF）仅介绍 ANN 问题背景，未比较精度；证据4（Qdrant架构）列出 HNSW 参数，但未解释精度优势；证据5（RAG综述）仅提及 HNSW 是常见 ANN 算法，未展开。因此，缺少回答该问题的核心信息。
- safe_answer_boundary: 当前证据不足，回答边界应限制在已检索到的证据范围内，不能补全缺失信息。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,922.074
- model_call_count: 1
- prompt_tokens: 378
- completion_tokens: 55
- total_tokens: 433
- estimated_cost_usd: 0.000090

### 追溯信息

- source_cer_sha256: `937c0e869fd801b9a09ee41ab68f0539e8e08b664fbf1f474902e81a2402e7c3`
- answer_sha256: `76bf36d8ac30d8cd4dbfdd22e7e40a5be87f2d4e53ad995d12f1147b903196cf`

## q28 — Kubernetes 中 etcd 的作用是什么？

### 分类与回答边界

- actual_route: DIRECT
- question_type: NARROW_FACT
- answerability: IN_SCOPE
- route_candidate: DIRECT
- confidence: high
- reason: 问题明确询问 etcd 的作用，且该信息是公开可验证的。

### 证据充分性

- raw_verdict: INSUFFICIENT
- control_verdict: INSUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/08_Kubernetes基础架构.md@0-1115#f0413c5d9c86
- missing_evidence: 明确描述 etcd 在 Kubernetes 中作用的证据，例如 etcd 作为集群状态存储、保存所有集群数据、提供一致性保证等具体功能说明
- reason: 唯一提及 etcd 的证据仅将其标注为控制平面中的 'KV存储'，未解释其具体作用（如存储集群状态、配置、元数据等）。其余证据均与网络、Service、Pod 相关，不涉及 etcd。因此证据不足以回答用户问题。

### 引用证据支撑（规则）

- citation_support_label: not_applicable
- citation_count: 0
- resolved_citation_count: 0
- unresolved_citation_count: 0
- claim_count: 0
- unsupported_claim_count: 0

### 冲突检测（规则型疑似冲突）

- triggered: false
- conflict_count: 0
- trigger_reason: NARROW_FACT 不在规则触发类型中，不执行冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: refused；sufficiency_insufficient
- missing_info: insufficient_evidence_after_reretrieve；明确描述 etcd 在 Kubernetes 中作用的证据，例如 etcd 作为集群状态存储、保存所有集群数据、提供一致性保证等具体功能说明；唯一提及 etcd 的证据仅将其标注为控制平面中的 'KV存储'，未解释其具体作用（如存储集群状态、配置、元数据等）。其余证据均与网络、Service、Pod 相关，不涉及 etcd。因此证据不足以回答用户问题。
- safe_answer_boundary: 当前证据不足，回答边界应限制在已检索到的证据范围内，不能补全缺失信息。

### D-full 后置评测耗时与用量

- offline_total_ms: 2,456.913
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 54
- total_tokens: 426
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `ba13752051b693c947df5a837b474dcc6f64d527857bb887ca755419d33fa33b`
- answer_sha256: `76bf36d8ac30d8cd4dbfdd22e7e40a5be87f2d4e53ad995d12f1147b903196cf`

## q29 — 在 Multi-AZ 架构中，为什么需要跨 AZ 部署副本？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: high
- reason: 问题明确，涉及 Multi-AZ 架构的副本部署原因，信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/09_MultiAZ高可用设计.md@613-1434#0c95c99cfcbb；internal/09_MultiAZ高可用设计.md@1434-2292#093c8c8d2e8b；internal/09_MultiAZ高可用设计.md@0-613#57a9e750463e；internal/06_Qdrant架构.md@1773-2264#876a0950fb44；external/32-Amazon-RDS的多可用区数据库实例部署.md@650-1315#3b9185283564
- reason: 证据充分覆盖了跨AZ部署副本的核心原因：故障隔离（AZ独立故障域，副本不受影响）、同步复制保证数据不丢（RPO≈0）、负载均衡跨AZ分发实现故障切换、Pod反亲和性强制跨AZ分布、有状态服务（如Qdrant）的副本机制，以及RDS多AZ部署的同步复制和故障转移。这些证据共同回答了'为什么需要跨AZ部署副本'，且无冲突。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 4
- unsupported_claim_count: 0

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/09_MultiAZ高可用设计.md | internal/09_MultiAZ高可用设计.md@613-1434#0c95c99cfcbb | 0.6598 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1637 | E1 | 在 Multi-AZ 架构中，跨 AZ 部署副本的主要原因是为了实现故障隔离和高可用性 |
| 2 | partial | 0.1575 | E1 | 当一个可用区（AZ）发生故障时，其他 AZ 中的副本可以继续提供服务，从而降低单点风险 |
| 3 | partial | 0.1673 | E1 | 例如，如果 AZ-1 发生故障，AZ-2 可以自动提升为主副本，确保服务的持续可用性 [E1] |
| 4 | partial | 0.1751 | E1 | 此外，跨 AZ 部署还可以通过同步复制确保数据不丢失，达到接近零的恢复点目标（RPO），并在故障发生时快速恢复服务 [E1] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: SUMMARY 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: medium
- level_meaning: 不确定性/风险中等
- reasons: citation_weak
- missing_info: citation_support_label=partial；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,178.452
- model_call_count: 1
- prompt_tokens: 381
- completion_tokens: 52
- total_tokens: 433
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `2f48ebfe5b30ac45043b335044626ce622408b1f6ef8297f62ca83f329ce5491`
- answer_sha256: `d4c1b844cee3dee3d40f685e0abe8eca7c7ed0f27665e0cee70bbe347b5fc88d`

## q30 — 为什么 KV cache 会成为大模型推理的关键优化点？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: medium
- reason: 问题明确，涉及 KV cache 在大模型推理中的作用，但需要综合多个因素进行回答。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/10_模型服务层vLLM架构.md@0-773#e9b11b984010；external/34-vllm_architecture_cn.md@5634-6214#2c8ba4fa9cdf；external/34-vllm_architecture_cn.md@18936-20086#a849b646548c
- reason: 证据包中的核心证据（internal/10_模型服务层vLLM架构.md）直接解释了KV cache的定义、作用（避免重复计算，将复杂度从O(n²)降至O(n)）、以及其成为关键优化点的原因（占用大量GPU显存，传统管理方式内存利用率低）。其他证据（external/34-vllm_architecture_cn.md）补充了KV cache的优化策略（如自动前缀缓存、缓存淘汰策略、缓存大小调整），进一步支撑了KV cache作为推理优化关键点的论述。虽然部分证据（external/26-Milvus-索引解释.md）与问题无关，但核心信息已充分覆盖，足以回答用户问题。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 3
- unsupported_claim_count: 0

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/10_模型服务层vLLM架构.md | internal/10_模型服务层vLLM架构.md@0-773#e9b11b984010 | 0.7106 |
| E4 | external/34-vllm_architecture_cn.md | external/34-vllm_architecture_cn.md@5634-6214#2c8ba4fa9cdf | 0.6013 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1640 | E1 | KV cache 成为大模型推理的关键优化点，主要是因为它能够显著提高推理效率 |
| 2 | supported | 0.2764 | E1 | 在 Transformer 自回归生成中，使用 KV cache 可以避免对所有历史 token 进行重复的 attention 计算，从而将复杂度从 O(n²) 降低到 O(n) [E1] |
| 3 | supported | 0.2213 | E1 | 此外，传统的 KV cache 存在内存管理低效和利用率低的问题，而 vLLM 通过改进的缓存管理策略，能够更有效地利用 GPU 显存，提升整体推理性能 [E1][E4] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: SUMMARY 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: medium
- level_meaning: 不确定性/风险中等
- reasons: citation_weak
- missing_info: citation_support_label=partial；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,224.091
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 53
- total_tokens: 430
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `ed12f263fdebffd542619546a79ba5fab0a619d4f9fea8d56fb947e22b23ad17`
- answer_sha256: `51bcc3333fac370bdec4f39790ce8ac5b14a1b83d8715105fd1d8a1a13f39713`
