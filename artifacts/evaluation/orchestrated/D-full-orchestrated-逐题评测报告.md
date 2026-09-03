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
- supporting_evidence_ids: internal/01_RAG基础原理.md@0-871#dfa7ac57160a；external/12-检索增强生成 (RAG) 技术综述-syhya.md@518-1237#59ad08ea7df5
- reason: 证据包中第一条证据（internal/01_RAG基础原理.md）明确描述了RAG的完整流程，包括离线索引阶段（文档加载、文本分块、Embedding计算、存入向量数据库）和在线检索-生成阶段（Query Embedding、向量相似度检索、构建Prompt、LLM生成回答、返回结果），直接回答了用户问题。第三条证据（external/12-检索增强生成 (RAG) 技术综述-syhya.md@518-1237）也概述了数据处理与索引、检索、生成三个阶段，与第一条证据一致，进一步支持回答。其他证据涉及RAG技术演进分类和GraphRAG等高级变体，虽非核心但无冲突。证据充分，足以归纳出RAG完整流程的主要步骤。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 11
- unsupported_claim_count: 4

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/01_RAG基础原理.md | internal/01_RAG基础原理.md@0-871#dfa7ac57160a | 0.0325 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1753 | E1 | RAG（检索增强生成）的完整流程主要分为两个阶段：离线索引阶段和在线检索-生成阶段 |
| 2 | unsupported | 0.0345 | E1 | **离线索引阶段**： - 文档加载：支持多种格式，提取纯文本 |
| 3 | partial | 0.1518 | E1 | - 文本分块：将文档切分为较小的文本块（chunk） |
| 4 | partial | 0.1631 | E1 | - Embedding 计算：将文本映射到高维向量空间 |
| 5 | unsupported | 0.0188 | E1 | - 向量存储：将向量写入向量数据库，建立索引 |
| 6 | partial | 0.1564 | E1 | **在线检索-生成阶段**： - 用户 Query：用户输入查询 |
| 7 | partial | 0.1634 | E1 | - Query Embedding：将查询进行向量化 |
| 8 | unsupported | 0.0235 | E1 | - 向量相似度检索：从数据库中检索最相关的文本块 |
| 9 | partial | 0.1470 | E1 | - 构建 Prompt：将查询和检索到的文本块结合 |
| 10 | partial | 0.1487 | E1 | - LLM 生成回答：使用大语言模型生成最终答案 |
| 11 | unsupported | 0.0124 | E1 | - 返回结果：将结果返回给用户，并包含来源引用 [E1] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: OPEN_MULTI 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=4；unsupported_claim；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 2,532.476
- model_call_count: 1
- prompt_tokens: 373
- completion_tokens: 52
- total_tokens: 425
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `1363d73e0e0a564eb67f548be0904eb32a4638a2bdfe9c175ac9d208ed62b548`
- answer_sha256: `bcd521094c9707f2135fbe20f681310676de0379efdce28b657f9c23b9b4105c`

## q02 — OpenAI GPT-6 的内部架构是什么？

### 分类与回答边界

- actual_route: DIRECT
- question_type: NARROW_FACT
- answerability: OOD_CANDIDATE
- route_candidate: REJECT_CANDIDATE
- confidence: medium
- reason: 内部架构信息可能未公开或受限于保密协议

### 证据充分性

- raw_verdict: INSUFFICIENT
- control_verdict: INSUFFICIENT
- confidence: high
- missing_evidence: 关于 OpenAI GPT-6 内部架构的任何文档、技术报告或官方说明
- reason: 用户问题询问 OpenAI GPT-6 的内部架构，但所有证据均涉及 Kubernetes、vLLM、Qdrant 等基础设施或推理引擎，未包含任何关于 GPT-6 模型架构的信息，证据完全不相关。

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
- missing_info: insufficient_evidence_after_reretrieve；关于 OpenAI GPT-6 内部架构的任何文档、技术报告或官方说明；用户问题询问 OpenAI GPT-6 的内部架构，但所有证据均涉及 Kubernetes、vLLM、Qdrant 等基础设施或推理引擎，未包含任何关于 GPT-6 模型架构的信息，证据完全不相关。
- safe_answer_boundary: 当前证据不足，回答边界应限制在已检索到的证据范围内，不能补全缺失信息。

### D-full 后置评测耗时与用量

- offline_total_ms: 2,870.990
- model_call_count: 1
- prompt_tokens: 374
- completion_tokens: 53
- total_tokens: 427
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `4de7f593b3686bf07d662c16f6d59c0d7a6aed51ae0330a2a2d11ba286467e27`
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
- supporting_evidence_ids: internal/02_Chunk策略.md@0-685#1411d3bdb16d；external/12-检索增强生成 (RAG) 技术综述-syhya.md@1237-1865#09b01ab21d25；external/14-text-chunking-datawhale.md@4870-5633#4375c0b9c1b3
- reason: 证据包包含多个来源，明确对比了固定长度分块和语义分块的定义、优缺点、适用场景及实现原理，足以回答用户问题。内部文档02_Chunk策略.md提供了直接对比，外部综述和Datawhale文档补充了细节，信息充分且一致。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 3
- unsupported_claim_count: 1

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E2 | internal/02_Chunk策略.md | internal/02_Chunk策略.md@0-685#1411d3bdb16d | 0.0482 |
| E1 | external/12-检索增强生成 (RAG) 技术综述-syhya.md | external/12-检索增强生成 (RAG) 技术综述-syhya.md@1237-1865#09b01ab21d25 | 0.0484 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.2654 | E2 | 固定长度分块和语义分块的主要区别在于分块的依据和效果： 1. **固定长度分块**（Fixed-size Chunking）是根据固定的字符数或token数进行切分，简单易实现，但可能在语义上切断句子或段落，导致检索精度较差 [E2] |
| 2 | supported | 0.2222 | E2 | **语义分块**（Semantic Chunking）则是利用自然语言处理技术，根据文本的语义边界进行切分，能够保留语义完整性，减少歧义，适用于需要高语义一致性的场景 [E1][E2] |
| 3 | unsupported | 0.0194 | E2 | 因此，固定长度分块更注重实现的简单性，而语义分块则强调语义的连贯性和检索的准确性 |

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

- offline_total_ms: 1,986.307
- model_call_count: 1
- prompt_tokens: 374
- completion_tokens: 50
- total_tokens: 424
- estimated_cost_usd: 0.000086

### 追溯信息

- source_cer_sha256: `cef98be9925a8f9e600d266b3df36a36c79bec4c24fd148e19a18d5e232fd623`
- answer_sha256: `96801b41704d782efd2c967485fa1ab8261f405b17519c2c2213909f162bc3c3`

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
- supporting_evidence_ids: internal/02_Chunk策略.md@1391-1768#5c5d7a6818b5；internal/02_Chunk策略.md@0-685#1411d3bdb16d；external/14-text-chunking-datawhale.md@597-1194#e880edf6d91e
- reason: 证据充分覆盖了chunk size过大的主要问题：内部文档明确列出检索精度下降、占用更多LLM context窗口、embedding向量语义混杂；外部文档详细解释了嵌入过程中的信息损失导致语义稀释。外部文档15和34与问题无关，但不影响回答。证据间无冲突，足以归纳回答。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 4
- unsupported_claim_count: 1

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/02_Chunk策略.md | internal/02_Chunk策略.md@1391-1768#5c5d7a6818b5 | 0.0328 |
| E4 | external/14-text-chunking-datawhale.md | external/14-text-chunking-datawhale.md@597-1194#e880edf6d91e | 0.0161 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1436 | E1 | chunk size 过大会带来以下问题： 1. 检索精度下降，相关内容可能被噪声稀释 |
| 2 | supported | 0.2517 | E1 | 占用更多的 LLM context 窗口，导致资源浪费 |
| 3 | partial | 0.2095 | E1 | embedding 向量的语义混杂，降低了信息的清晰度和检索的准确性 |
| 4 | unsupported | 0.0788 | E4 | 在嵌入过程中，信息损失不可避免，长文本块的语义点过多，导致单一向量的表示变得笼统，关键细节被模糊化，从而影响检索精度 [E1][E4] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: OPEN_MULTI 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=1；unsupported_claim；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 2,875.727
- model_call_count: 1
- prompt_tokens: 373
- completion_tokens: 46
- total_tokens: 419
- estimated_cost_usd: 0.000084

### 追溯信息

- source_cer_sha256: `1e387db43b9fa39b8dd79ec1aa0f7b6cb0e425ab01e65daed7c140d5cc51bbee`
- answer_sha256: `9ae347a2398252948b4c8b94c39a5ebbe781af0b34040008c92ff0c0a0d7a0c1`

## q05 — 为什么 embedding 相似度常用余弦相似度？

### 分类与回答边界

- actual_route: DIRECT
- question_type: NARROW_FACT
- answerability: IN_SCOPE
- route_candidate: DIRECT
- confidence: high
- reason: 问题明确询问余弦相似度的使用原因，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/03_Embedding原理与向量空间.md@685-1106#3f0be53594bb；external/16-vector-embedding-datawhale.md@398-804#13940eb805c6；external/21-pgvector补充.md@0-585#45ac5b536066
- reason: 证据包中多个来源直接回答了问题：内部文档明确列出余弦相似度最常用的原因（归一化消除长度影响、值域直观、适合高维向量），外部文档也指出余弦相似度是最常用度量方式且与语义相似度最一致。证据之间无冲突，足以支撑回答。

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
| E1 | internal/03_Embedding原理与向量空间.md | internal/03_Embedding原理与向量空间.md@685-1106#3f0be53594bb | 0.0328 |
| E2 | external/16-vector-embedding-datawhale.md | external/16-vector-embedding-datawhale.md@398-804#13940eb805c6 | 0.0320 |

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

- offline_total_ms: 2,376.457
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 55
- total_tokens: 432
- estimated_cost_usd: 0.000090

### 追溯信息

- source_cer_sha256: `f975627734d40974a14e53254355416afeb7a94458c2d432f83f36ced2fdfce0`
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

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/04_RAG失败模式.md@639-1332#2b5bc2c58bf3
- reason: 证据包中包含内部文档《RAG失败模式》中专门讨论幻觉的章节，明确列出了RAG中幻觉的来源和发生情况（如知识库无相关文档、用户问题超出覆盖范围、LLM被诱导强制生成、检索chunks信息不足），直接回答了用户问题。其他证据（如RAG综述、Kubernetes存储）与问题无关，但不影响核心证据的充分性。

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
| E2 | internal/04_RAG失败模式.md | internal/04_RAG失败模式.md@639-1332#2b5bc2c58bf3 | 0.0164 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1845 | E2 | 在 RAG 系统中，容易产生幻觉的情况包括： 1. 知识库中没有相关文档（召回失败） |
| 2 | supported | 1.0000 | E2 | 用户问题超出知识库覆盖范围 |
| 3 | supported | 1.0000 | E2 | LLM 被过于自信的 Prompt 诱导强制生成答案 |
| 4 | supported | 1.0000 | E2 | 检索到的 chunks 信息不足以支撑完整回答 [E2] |

### 冲突检测（规则型疑似冲突）

- triggered: false
- conflict_count: 0
- trigger_reason: NARROW_FACT 不在规则触发类型中，不执行冲突扫描

### 综合不确定性（派生信号）

- level: medium
- level_meaning: 不确定性/风险中等
- reasons: citation_weak
- missing_info: citation_support_label=partial；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 3,090.355
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 57
- total_tokens: 434
- estimated_cost_usd: 0.000091

### 追溯信息

- source_cer_sha256: `0f5f4f47e198785ce613d48d225391afc53171d5228360b4440bdb284e211f90`
- answer_sha256: `91d81c9415ce419f7d7fd0fb5e1e7becdd8718b873f9335c2cfacdafcdf8a766`

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
- supporting_evidence_ids: internal/09_MultiAZ高可用设计.md@613-1434#0c95c99cfcbb；internal/09_MultiAZ高可用设计.md@1434-2292#093c8c8d2e8b；external/32-Amazon-RDS的多可用区数据库实例部署.md@0-650#0d728feefe33；internal/09_MultiAZ高可用设计.md@0-613#57a9e750463e
- reason: 证据包包含多个直接回答问题的证据：内部文档详细阐述了Multi-AZ通过故障隔离、同步复制、负载均衡跨AZ分发、Pod反亲和性、TopologySpreadConstraints等机制降低单点故障风险；外部AWS RDS文档补充了数据库层Multi-AZ的同步备用副本和故障转移机制；核心概念文档提供了AZ定义和故障隔离单元的背景。这些证据覆盖了问题核心需求，足以支撑归纳回答。外部GraphRAG文档与问题无关，但不影响充分性。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 6
- unsupported_claim_count: 1

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/09_MultiAZ高可用设计.md | internal/09_MultiAZ高可用设计.md@613-1434#0c95c99cfcbb | 0.0328 |
| E2 | internal/09_MultiAZ高可用设计.md | internal/09_MultiAZ高可用设计.md@1434-2292#093c8c8d2e8b | 0.0310 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.2116 | E1 | Multi-AZ 部署通过以下方式降低系统单点故障风险： 1. **故障隔离**：每个可用区（AZ）是独立的故障域，若一个 AZ 发生故障，其他 AZ 的副本不受影响，服务可自动切换到健康的副本 |
| 2 | partial | 0.1713 | E1 | 例如，当 AZ-1 故障时，AZ-2 可以自动提升为主实例，确保服务持续可用 [E1] |
| 3 | partial | 0.1934 | E1 | **同步复制**：数据库在写入时会同步复制到多个 AZ 的副本，确保数据在故障切换时不会丢失，恢复点目标（RPO）接近于零 [E1] |
| 4 | partial | 0.1898 | E1 | **负载均衡**：负载均衡器将请求分发到多个 AZ 中的健康实例，单个 AZ 故障时流量会自动切换，用户不会感知到服务中断 [E1] |
| 5 | partial | 0.1983 | E1 | **Pod 反亲和性和均匀分布**：在 Kubernetes 中，可以通过反亲和性和拓扑分布约束确保 Pods 被调度到不同的 AZ，从而减少单个 AZ 故障对整体服务的影响 [E2] |
| 6 | unsupported | 0.0055 | E2 | 这些机制共同作用，显著提高了系统的可用性和容错能力 |

### 冲突检测（规则型疑似冲突）

- triggered: false
- conflict_count: 0
- trigger_reason: PROCEDURE 不在规则触发类型中，不执行冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=1；unsupported_claim；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,342.200
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 54
- total_tokens: 431
- estimated_cost_usd: 0.000089

### 追溯信息

- source_cer_sha256: `b9951835c22a0772edd9a7002b5b4a6871f5fdae17f9d13f0764c0a5f9d5b39b`
- answer_sha256: `78f1c873098fbfc038c6819c73952020946e560c216931eccf92321545a45ce8`

## q08 — HNSW 和 IVF 向量索引有什么主要区别？

### 分类与回答边界

- actual_route: DECOMPOSE
- question_type: EXPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: high
- reason: 问题明确比较了两个向量索引的主要区别，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: external/22-milvus-datawhale.md@4526-5014#fc79b169f6c2；internal/07_向量索引算法HNSW与IVF.md@849-1558#5387fc2754ce；external/26-Milvus-索引解释.md@3003-3627#3603b200df69
- reason: 证据包包含多个来源，明确对比了HNSW和IVF的原理、优缺点、适用场景、内存占用和构建速度等核心区别，足以回答用户问题。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 3
- resolved_citation_count: 3
- unresolved_citation_count: 0
- claim_count: 7
- unsupported_claim_count: 0

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E3 | external/22-milvus-datawhale.md | external/22-milvus-datawhale.md@4526-5014#fc79b169f6c2 | 0.0320 |
| E5 | internal/07_向量索引算法HNSW与IVF.md | internal/07_向量索引算法HNSW与IVF.md@849-1558#5387fc2754ce | 0.0164 |
| E4 | external/26-Milvus-索引解释.md | external/26-Milvus-索引解释.md@3003-3627#3603b200df69 | 0.0313 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.2813 | E3 | HNSW 和 IVF 向量索引的主要区别在于它们的结构和工作原理： 1. **数据结构**： - HNSW 使用基于图的结构，通过多层邻近图来进行搜索，能够快速定位目标区域并进行精确搜索 [E3] |
| 2 | supported | 0.2275 | E3 | - IVF 则通过聚类将向量空间划分为多个“桶”，查询时只在最相似的几个桶内进行精确搜索 [E3][E5] |
| 3 | partial | 0.2175 | E3 | **性能与精度**： - HNSW 在高维数据和低延迟查询中表现优异，检索速度快且召回率高，但内存占用较大 [E3] |
| 4 | supported | 0.2260 | E3 | - IVF 通过缩小搜索范围提升检索速度，适合大规模数据集，但召回率不是100% [E3][E5] |
| 5 | partial | 0.1959 | E3 | **构建与内存**： - HNSW 的索引构建时间较长，内存占用也较高 [E3][E4] |
| 6 | partial | 0.1931 | E4 | - IVF 的构建速度较快，尤其是其变体（如 IVFPQ）在内存占用上更为节省 [E5] |
| 7 | supported | 0.2645 | E3 | 综上所述，HNSW 更适合对查询延迟有严格要求的场景，而 IVF 则在大规模数据集的通用场景中表现更好 |

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

- offline_total_ms: 3,121.200
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 53
- total_tokens: 430
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `c8568bb3cd8edd64356feb813b5bc04f38a45fa4d16e1012c25e6521bf566dd8`
- answer_sha256: `a14a363fb35c46c7555ecf42cf1d72336d588ef08a3905fb7ba54b13f4b24614`

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
- reason: 证据包中的两个内部文档块直接回答了问题：第一个块通过架构图明确列出 Control Plane 包含 API Server、Scheduler、etcd、Controller Manager；第二个块详细解释了这四个组件的功能。外部文档块（存储和网络）与问题无关，但不影响回答。证据充分且无冲突。

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
| E1 | internal/08_Kubernetes基础架构.md | internal/08_Kubernetes基础架构.md@0-1115#f0413c5d9c86 | 0.0328 |
| E2 | internal/08_Kubernetes基础架构.md | internal/08_Kubernetes基础架构.md@1115-1993#1114731f27b6 | 0.0323 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1911 | E1 | Kubernetes control plane 包含以下核心组件： 1. **API Server**（kube-apiserver）：K8s 的唯一入口，负责所有组件和客户端的交互 |
| 2 | partial | 0.1663 | E2 | **etcd**：分布式键值存储，保存集群所有状态 |
| 3 | supported | 0.2204 | E2 | **Scheduler**（kube-scheduler）：负责将新建的 Pod 分配到合适的 Node |
| 4 | supported | 0.2315 | E2 | **Controller Manager**（kube-controller-manager）：多个控制器的集合，负责使实际状态趋向期望状态 [E1][E2] |

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

- offline_total_ms: 1,520.342
- model_call_count: 1
- prompt_tokens: 373
- completion_tokens: 52
- total_tokens: 425
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `223fc14d2eff3c01e1db8df3e5117271f25e52662a20de51a18b65fb2c517b40`
- answer_sha256: `44dbf45dbecbed8fdc671ecd7dff5bc38c2e7e0bc84ad1e3a5811e9fef2e116e`

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
- supporting_evidence_ids: internal/10_模型服务层vLLM架构.md@0-773#e9b11b984010；external/34-vllm_architecture_cn.md@5634-6214#2c8ba4fa9cdf；external/33-vllm_architecture_official.md@10352-11802#b6c74b9545b0；external/34-vllm_architecture_cn.md@39324-40078#1a8fd10f7e73；external/33-vllm_architecture_official.md@14859-16543#a6de9219f6ee
- reason: 证据包中第一条内部文档明确解释了KV cache的定义和作用（缓存历史token的Key和Value矩阵，避免重复计算，将复杂度从O(n²)降为O(n)），直接回答了用户问题。其余外部文档从vLLM实现角度补充了KV cache的缓存管理、前缀缓存、内存优化等细节，进一步佐证了其作用。证据之间无冲突，信息充分。

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
| E1 | internal/10_模型服务层vLLM架构.md | internal/10_模型服务层vLLM架构.md@0-773#e9b11b984010 | 0.0328 |
| E2 | external/34-vllm_architecture_cn.md | external/34-vllm_architecture_cn.md@5634-6214#2c8ba4fa9cdf | 0.0161 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.2529 | E1 | KV Cache 在大模型推理中的作用主要是缓存历史 token 的 Key 和 Value 矩阵，以避免在每次生成新 token 时重复计算，从而显著降低计算复杂度 |
| 2 | partial | 0.1722 | E1 | 具体来说，使用 KV Cache 可以将复杂度从 O(n²) 降低到 O(n)，提高推理效率 [E1] |
| 3 | partial | 0.1775 | E1 | 此外，KV Cache 还面临传统内存管理低效的问题，如内存碎片和利用率低 |
| 4 | partial | 0.2126 | E1 | vLLM 通过改进的缓存策略和管理机制，优化了 KV Cache 的使用，提升了 GPU 内存的利用率和推理性能 [E1][E2] |

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

- offline_total_ms: 1,384.638
- model_call_count: 1
- prompt_tokens: 374
- completion_tokens: 54
- total_tokens: 428
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `e78c0bb9c637ad87f20bbb112cf3e188739a6e702bcb03da9c8a62636fec221a`
- answer_sha256: `72614edff50309d742536b12abf4ed6e197204df0c1145b70c547503af9195f3`

## q11 — Overlap 在文本分块中有什么作用？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: high
- reason: 问题明确，涉及文本分块的作用，能够提供清晰的总结性回答。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/02_Chunk策略.md@685-1391#5484310af4bf；external/12-检索增强生成 (RAG) 技术综述-syhya.md@1237-1865#09b01ab21d25
- reason: 证据充分回答了Overlap在文本分块中的作用。internal/02_Chunk策略.md@685-1391#5484310af4bf明确说明Overlap防止跨越边界的关键信息被切断而丢失、保留上下文连贯性、提升边界附近的检索召回率，并提及副作用和经验值。external/12-检索增强生成 (RAG) 技术综述-syhya.md@1237-1865#09b01ab21d25也指出Overlap保证语义连续性、避免关键信息在分块边界被切断。两处证据一致且互补，足以支撑回答。其余证据与Overlap作用无关，不影响充分性。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 2
- unsupported_claim_count: 0

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/02_Chunk策略.md | internal/02_Chunk策略.md@685-1391#5484310af4bf | 0.0320 |
| E2 | external/12-检索增强生成 (RAG) 技术综述-syhya.md | external/12-检索增强生成 (RAG) 技术综述-syhya.md@1237-1865#09b01ab21d25 | 0.0313 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1966 | E1 | Overlap 在文本分块中的作用主要是防止关键信息在分块边界被切断，从而保留上下文的连贯性，提升边界附近的检索召回率 [E1] |
| 2 | supported | 0.2247 | E1 | 具体来说，Overlap 是指相邻 chunk 之间共享一定数量的 token，这样可以确保信息的完整性和连贯性 [E2] |

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

- offline_total_ms: 1,437.891
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 51
- total_tokens: 423
- estimated_cost_usd: 0.000086

### 追溯信息

- source_cer_sha256: `05e6de3ae0020d996a16666b8d942e9a08b5f00da394ea889b9b726910ef7782`
- answer_sha256: `e81168786bf2318bff11aad3ea9461c6539814241c73941d1ee6fc56efafb245`

## q12 — Embedding 维度会影响哪些方面？

### 分类与回答边界

- actual_route: DIRECT
- question_type: OPEN_MULTI
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: high
- reason: 问题明确，涉及多个方面的影响，且可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/03_Embedding原理与向量空间.md@1106-1746#7cc4b717d45c；external/16-vector-embedding-datawhale.md@3945-4583#7a47e180d0cc
- reason: 证据包中第一条证据（internal/03_Embedding原理与向量空间.md 第4节）直接以表格形式列出了Embedding维度对语义表达能力、内存与存储、检索延迟、维度灾难四个方面的影响，并给出了工程实践中的维度范围，完整覆盖了用户问题'Embedding维度会影响哪些方面'的核心需求。第四条证据（external/16-vector-embedding-datawhale.md 4.1节）补充说明了维度与存储和计算资源的关系，进一步佐证。其余证据虽非直接回答，但不构成冲突。证据充分，足以归纳回答。

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
| E1 | internal/03_Embedding原理与向量空间.md | internal/03_Embedding原理与向量空间.md@1106-1746#7cc4b717d45c | 0.0328 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.2280 | E1 | Embedding 维度会影响以下几个方面： 1. **语义表达能力**：维度越高，理论上能编码越多信息，但收益递减 |
| 2 | partial | 0.2102 | E1 | **内存与存储**：维度越高，每个向量占用的空间越大（例如，float32格式下1维占用4字节） |
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

- offline_total_ms: 1,234.132
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 46
- total_tokens: 418
- estimated_cost_usd: 0.000083

### 追溯信息

- source_cer_sha256: `0f3c7b52442b0b01305c0389eadbc1807c865cab4cdc03122966d18dad89899f`
- answer_sha256: `6bf597c1ce3f3118a6ba5374c2060c4e141f7324c83a6f0c215954e6a913f3e2`

## q13 — Embedding 是否真正“理解”语义？

### 分类与回答边界

- actual_route: DIRECT
- question_type: IMPLICIT_COMPARE
- answerability: NEEDS_CLARIFICATION
- route_candidate: NEEDS_CLARIFICATION
- confidence: medium
- reason: 问题缺少对比对象，无法明确理解的标准或范围。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/03_Embedding原理与向量空间.md@1106-1746#7cc4b717d45c；internal/03_Embedding原理与向量空间.md@0-685#6f797c7d21d6；external/16-vector-embedding-datawhale.md@398-804#13940eb805c6
- reason: EvidencePacket 直接回答了用户问题。internal/03_Embedding原理与向量空间.md 的 section 5 明确给出准确答案：Embedding 模型捕捉的是语义的统计规律，而非人类意义上的理解，并列举了局限（否定词不敏感、逻辑推理有限等）。其他证据补充了 Embedding 的工作原理（对比学习、上下文感知）和语义表示机制，共同支撑对问题的完整回答。无证据冲突。

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
| E1 | internal/03_Embedding原理与向量空间.md | internal/03_Embedding原理与向量空间.md@1106-1746#7cc4b717d45c | 0.0328 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1932 | E1 | Embedding 模型并不真正“理解”语义，而是捕捉语义的统计规律 |
| 2 | unsupported | 0.0852 | E1 | 它通过大量文本训练，将经常出现在相似上下文中的文本映射到相近的向量位置，能够处理语义相似性，但对逻辑推理和因果关系等高阶理解能力有限 |
| 3 | partial | 0.1957 | E1 | 此外，Embedding 对否定词和精确数字的敏感性较差，可能导致相似的向量表示不同的语义内容 [E1] |

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

- offline_total_ms: 2,113.814
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 53
- total_tokens: 425
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `95fc5c227f775b1bbb73d3fb7e0b32c8abf96d8e9847096dd5cc4e285f1129d2`
- answer_sha256: `d9eb1ff87c7dfa2a302f2aaa818070fb85b21bcd4d3d6a84ae764b3c02abc0e6`

## q14 — 什么叫 evidence insufficient（证据不充分）？

### 分类与回答边界

- actual_route: DIRECT
- question_type: NARROW_FACT
- answerability: IN_SCOPE
- route_candidate: DIRECT
- confidence: high
- reason: 问题明确，询问的是对特定术语的定义，且没有不可验证的风险。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/04_RAG失败模式.md@1332-1937#311a87398ac2；internal/04_RAG失败模式.md@0-639#222aea480737；internal/04_RAG失败模式.md@639-1332#2b5bc2c58bf3
- reason: 证据包中多个chunk直接定义了evidence insufficient（证据不充分）的概念、判断标准和相关场景。chunk 311a87398ac2明确给出定义和判断标准；chunk 222aea480737在2.2节将召回遗漏的影响描述为Evidence Insufficient；chunk 2b5bc2c58bf3在幻觉来源中提及检索内容不足以支撑回答。这些证据相互补充，足以回答用户问题。其余两个外部来源（CAP理论和文本分块）与问题无关，但不构成冲突。

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
| E1 | internal/04_RAG失败模式.md | internal/04_RAG失败模式.md@1332-1937#311a87398ac2 | 0.0328 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1411 | E1 | “证据不充分”（Evidence Insufficient）指的是在回答问题时，检索到的内容未能提供足够的信息来支持每个关键声明 |
| 2 | unsupported | 0.0369 | E1 | 这种情况的判断标准包括： 1. 回答中包含了检索内容以外的推断 |
| 3 | unsupported | 0.0357 | E1 | 关键问题需要多跳推理，但仅召回了部分链条 |
| 4 | supported | 1.0000 | E1 | 检索结果覆盖了话题方向，但缺乏具体数据或细节 [E1] |

### 冲突检测（规则型疑似冲突）

- triggered: false
- conflict_count: 0
- trigger_reason: NARROW_FACT 不在规则触发类型中，不执行冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=2；unsupported_claim；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 2,298.850
- model_call_count: 1
- prompt_tokens: 374
- completion_tokens: 57
- total_tokens: 431
- estimated_cost_usd: 0.000090

### 追溯信息

- source_cer_sha256: `68d4ff82171813df6e1d4e9ad734e87429afc6997097a3138c7f19efa06a4142`
- answer_sha256: `5c0533ef861f2f422e7f248e605c6e95717d2775a7b4e67cc2ce0bd1a8b692ca`

## q15 — 检索错但回答对，在 RAG 评估里算成功吗？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: medium
- reason: 问题涉及对 RAG 评估成功标准的整体理解，且没有明显不可验证风险。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/04_RAG失败模式.md@1332-1937#311a87398ac2；internal/04_RAG失败模式.md@0-639#222aea480737
- reason: 证据包中第2条证据（internal/04_RAG失败模式.md@1332-1937）明确回答了用户问题：'检索错但回答对'不算成功，应标记为'Retrieval Failed, Answer Lucky'，不计入正确。第1条证据也提供了相关背景（检索失败与生成失败的区分）。这些证据直接且充分支撑了回答，无冲突或缺失。

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
| E2 | internal/04_RAG失败模式.md | internal/04_RAG失败模式.md@1332-1937#311a87398ac2 | 0.0325 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1671 | E2 | 检索错但回答对在 RAG 评估中不算成功 |
| 2 | partial | 0.1843 | E2 | 虽然最终回答可能正确，但这源于 LLM 的参数记忆，而不是可追溯的检索证据，因此不被视为有效的成功案例 |
| 3 | supported | 0.2762 | E2 | 这种情况应标记为“Retrieval Failed, Answer Lucky”，不计入正确答案 [E2] |

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

- offline_total_ms: 1,139.399
- model_call_count: 1
- prompt_tokens: 380
- completion_tokens: 53
- total_tokens: 433
- estimated_cost_usd: 0.000089

### 追溯信息

- source_cer_sha256: `23f7e97a7ebba3f08569ce7c82956d60de0cd837d19153630c7f3bea372a2930`
- answer_sha256: `522589f738a2af13268bfc56bfed909c105ca89d6dae13eec4f124a3e3999a0d`

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
- supporting_evidence_ids: internal/05_pgvector原理.md@1303-1989#f133a907d82c；external/20-vector-db-datawhale.md@160-666#2f16450f67fa；external/20-vector-db-datawhale.md@1465-1990#6f89ab43d01a；external/21-pgvector补充.md@0-585#45ac5b536066
- reason: 证据包中第一块证据（internal/05_pgvector原理.md@1303-1989）直接包含'pgvector vs 专用向量数据库'对比表格，覆盖架构、集成成本、查询吞吐、过滤检索、事务/ACID、量化压缩、适用规模、运维复杂度等核心差异维度，并给出结论性建议；同时该文档第5节补充了pgvector的主要限制。其他证据块提供了专用向量数据库的功能特性（如高效相似性搜索、过滤查询、分布式扩展等）和pgvector的基础能力（向量类型、距离计算），从侧面支撑对比。证据来源多样（内部文档+外部公开资料），内容互补且无冲突，足以支撑对用户问题的全面回答。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 12
- unsupported_claim_count: 2

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/05_pgvector原理.md | internal/05_pgvector原理.md@1303-1989#f133a907d82c | 0.0472 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.3014 | E1 | pgvector 和专用向量数据库（如 Qdrant 和 Milvus）之间的主要差异如下： 1. **架构**：pgvector 是 PostgreSQL 的扩展，而专用向量数据库是独立的系统 |
| 2 | partial | 0.2182 | E1 | **集成成本**：pgvector 的集成成本较低，因为可以复用现有的 PostgreSQL 栈 |
| 3 | unsupported | 0.0224 | E1 | 而专用向量数据库需要独立部署和维护 |
| 4 | supported | 0.2840 | E1 | **查询吞吐量**：pgvector 的查询吞吐量中等（约百级 QPS），而专用向量数据库如 Qdrant 的吞吐量可超过 4000 RPS |
| 5 | partial | 0.2048 | E1 | **过滤检索**：pgvector 需要额外调优以支持过滤检索，而专用向量数据库原生支持此功能，性能更佳 |
| 6 | supported | 0.2227 | E1 | **事务支持**：pgvector 完整支持 ACID 事务，而专用向量数据库的事务支持有限或不支持 |
| 7 | partial | 0.1953 | E1 | **量化压缩**：pgvector 的量化压缩能力有限，而专用向量数据库支持多种量化方法 |
| 8 | partial | 0.1989 | E1 | **适用规模**：pgvector 适用于小于 1000 万向量的场景，而专用向量数据库可处理亿级向量 |
| 9 | partial | 0.1899 | E1 | **运维复杂度**：pgvector 的运维复杂度较低，因为与业务数据同库 |
| 10 | unsupported | 0.0224 | E1 | 专用向量数据库的运维复杂度中等到高 |
| 11 | supported | 0.2367 | E1 | **结论**：如果已经使用 PostgreSQL 且向量规模小于 500 万，pgvector 是合理选择 |
| 12 | supported | 0.2243 | E1 | 如果向量规模大且对检索性能有严格要求，则应选择专用向量数据库如 Qdrant 或 Milvus [E1] |

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

- offline_total_ms: 1,554.000
- model_call_count: 1
- prompt_tokens: 378
- completion_tokens: 52
- total_tokens: 430
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `301afad5fd572dbf36fcaa01363634a20ff57edc8e0b070a325bd397b1c4b413`
- answer_sha256: `de3ab48322fef5a8f3865892d3af6fd1de8d2394394d9befbc836a7de25b1068`

## q17 — Qdrant 的内存存储和磁盘存储有什么差异？

### 分类与回答边界

- actual_route: DIRECT
- question_type: EXPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: high
- reason: 问题明确要求比较 Qdrant 的内存存储和磁盘存储，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/06_Qdrant架构.md@0-464#aca4cb5fc3d4；internal/06_Qdrant架构.md@965-1773#50531ea08667
- reason: 证据包中包含来自 Qdrant 架构文档的两个相关片段，其中第二个片段（internal/06_Qdrant架构.md@965-1773#50531ea08667）明确列出了 In-Memory、Mmap 和 On-disk 三种存储模式的说明、性能与成本对比，直接回答了内存存储与磁盘存储的差异。第一个片段提供了 Qdrant 核心概念背景，辅助理解。其他证据涉及 Kubernetes 和 Milvus，与问题无关，但不影响充分性。证据足以支撑回答用户问题。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 5
- unsupported_claim_count: 3

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E2 | internal/06_Qdrant架构.md | internal/06_Qdrant架构.md@965-1773#50531ea08667 | 0.0325 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.2065 | E2 | Qdrant 的内存存储和磁盘存储主要有以下差异： 1. **存储位置**： - **内存存储（In-Memory）**：向量完全加载到 RAM 中，提供最快的访问速度 |
| 2 | unsupported | 0.0210 | E2 | - **磁盘存储**：向量存储在磁盘上，使用操作系统的缓存管理，性能较内存存储中等 |
| 3 | unsupported | 0.0176 | E2 | **性能与成本**： - **内存存储**：性能最佳，但内存成本高 |
| 4 | unsupported | 0.0154 | E2 | - **磁盘存储**：性能较慢，但成本最低，适合大规模数据存储 |
| 5 | partial | 0.1998 | E2 | **存储策略**： - Qdrant 支持多种存储策略，包括内存、内存映射（Mmap）和量化+磁盘存储，以在性能与成本之间进行权衡 [E2] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: EXPLICIT_COMPARE 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=3；unsupported_claim；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,026.354
- model_call_count: 1
- prompt_tokens: 380
- completion_tokens: 57
- total_tokens: 437
- estimated_cost_usd: 0.000091

### 追溯信息

- source_cer_sha256: `9a9940bcec6b4f9b44909f9adf4d9e26fe9f664d80c72e57729b880dc1636980`
- answer_sha256: `daa5c2a79e49c582d0cfa62c8cd7b3d7395935cb1ee1199d8f1d75dc9129e315`

## q18 — Recall 和 latency 在向量检索中为什么需要权衡？

### 分类与回答边界

- actual_route: DIRECT
- question_type: IMPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: high
- reason: 问题明确涉及 Recall 和 latency 的关系，且可以提供相关的解释和分析。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/07_向量索引算法HNSW与IVF.md@1558-2289#f09b34881aa0；internal/07_向量索引算法HNSW与IVF.md@0-301#a87f5dd9a27c；external/22-milvus-datawhale.md@5576-6211#1e7ee82d83d9
- reason: 证据包中第一个证据（internal/07...@1558-2289）直接解释了Recall与Latency的权衡机制，包括HNSW的ef_search和IVF的nprobe参数如何影响两者，以及90%到99% recall需要2-5倍查询时间代价的经验法则。第三个证据（internal/07...@0-301）提供了ANN检索的背景，说明近似搜索牺牲少量精度换取亚线性时间复杂度的根本原因。第四个证据（external/22-milvus...@5576-6211）也提到ANN检索是速度和精度之间的平衡策略。这些证据共同充分回答了为什么需要权衡的问题，即ANN通过牺牲精度（recall）来换取速度（低latency），且参数调整会导致两者此消彼长。其余证据不直接相关但无冲突。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 5
- unsupported_claim_count: 1

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/07_向量索引算法HNSW与IVF.md | internal/07_向量索引算法HNSW与IVF.md@1558-2289#f09b34881aa0 | 0.0320 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1899 | E1 | 在向量检索中，Recall（召回率）和Latency（延迟）之间的权衡是因为提高召回率通常会导致查询延迟增加 |
| 2 | partial | 0.1842 | E1 | 具体来说： 1. **HNSW算法**：通过增加`ef_search`参数可以提高召回率，但这会导致延迟增加 |
| 3 | partial | 0.1773 | E1 | **IVF算法**：通过增加`nprobe`参数同样可以提高召回率，但也会增加延迟 |
| 4 | unsupported | 0.0344 | E1 | 经验法则表明，从90%召回率提升到99%召回率，通常需要2到5倍的查询时间代价 |
| 5 | supported | 0.2473 | E1 | 因此，在实际应用中，需要通过调整`ef_search`或`nprobe`来找到Recall和Latency之间的业务平衡点 [E1] |

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

- offline_total_ms: 1,269.495
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 52
- total_tokens: 429
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `11de7555a1f789e21aa08a86bb22b2af6fd1894d097e54e05093ae18bf6a2e30`
- answer_sha256: `f53c4f804ac8953102aa45a9069cb1328a164ef67fe3727f965d2e2003cf4787`

## q19 — kube-scheduler 在 Kubernetes 集群里负责什么？

### 分类与回答边界

- actual_route: DIRECT
- question_type: NARROW_FACT
- answerability: IN_SCOPE
- route_candidate: DIRECT
- confidence: high
- reason: 问题明确询问 kube-scheduler 的职责，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/08_Kubernetes基础架构.md@1115-1993#1114731f27b6
- reason: 证据包中 internal/08_Kubernetes基础架构.md 的 3.3 节明确说明 kube-scheduler 负责将新建的 Pod 分配到合适的 Node，并列出调度依据（资源请求、节点亲和性、Pod 反亲和性、Taints/Tolerations）及调度流程，足以回答用户问题。其他证据与问题无关，但不影响充分性。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 2
- unsupported_claim_count: 0

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E4 | internal/08_Kubernetes基础架构.md | internal/08_Kubernetes基础架构.md@1115-1993#1114731f27b6 | 0.0161 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1366 | E4 | kube-scheduler 在 Kubernetes 集群中负责将新建的 Pod 分配到合适的 Node |
| 2 | partial | 0.2143 | E4 | 它的调度决策依据包括资源请求/限制、节点亲和性、Pod 反亲和性以及 Taints/Tolerations [E4] |

### 冲突检测（规则型疑似冲突）

- triggered: false
- conflict_count: 0
- trigger_reason: NARROW_FACT 不在规则触发类型中，不执行冲突扫描

### 综合不确定性（派生信号）

- level: medium
- level_meaning: 不确定性/风险中等
- reasons: citation_weak
- missing_info: citation_support_label=partial；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,043.770
- model_call_count: 1
- prompt_tokens: 375
- completion_tokens: 50
- total_tokens: 425
- estimated_cost_usd: 0.000086

### 追溯信息

- source_cer_sha256: `04f5241453a882de55cf0228f3cc10cecf4844f5146d3c8f0f1f008c86551193`
- answer_sha256: `2e71ea8283847b45e41b46629a14024c6559d75db4106ffc49c9e0b74ff3d7c8`

## q20 — 连续批处理（Continuous Batching）和传统静态批处理有什么区别？

### 分类与回答边界

- actual_route: DECOMPOSE
- question_type: EXPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: high
- reason: 问题明确要求比较两个已知的批处理方式，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/10_模型服务层vLLM架构.md@773-1705#c76695ac0bf6；internal/10_模型服务层vLLM架构.md@0-773#e9b11b984010
- reason: 证据包中两个内部文档片段直接对比了传统静态批处理（等待整个批次完成，GPU空等）与连续批处理（请求完成即插入新请求，GPU满载），并给出了吞吐量提升数据，足以回答用户问题。其余外部文档（Kubernetes存储、RAG综述）与问题无关，不影响充分性判断。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 7
- unsupported_claim_count: 3

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/10_模型服务层vLLM架构.md | internal/10_模型服务层vLLM架构.md@773-1705#c76695ac0bf6 | 0.0492 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1852 | E1 | 连续批处理（Continuous Batching）与传统静态批处理的主要区别在于请求处理的方式和效率 |
| 2 | unsupported | 0.0484 | E1 | **请求处理方式**： - **传统静态批处理**：所有请求同时开始，必须等待最长的请求完成后才能接受新请求 |
| 3 | partial | 0.1498 | E1 | 这导致短请求完成后GPU空闲，利用率低 |
| 4 | unsupported | 0.0346 | E1 | - **连续批处理**：在处理请求时，一旦某个请求完成，可以立即插入新的请求，而无需等待其他请求完成 |
| 5 | partial | 0.1378 | E1 | 这使得GPU始终保持满载状态 |
| 6 | partial | 0.1579 | E1 | **效率**： - 传统静态批处理的GPU利用率较低，吞吐量受限 |
| 7 | unsupported | 0.0232 | E1 | - 连续批处理显著提升了吞吐量，相比于传统方法，吞吐量提升可达14到24倍 [E1] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: EXPLICIT_COMPARE 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=3；unsupported_claim；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 3,523.186
- model_call_count: 1
- prompt_tokens: 380
- completion_tokens: 52
- total_tokens: 432
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `aa3579787b853db1b69fc512a46300574644083070cb728cfa6e6b4f87fed346`
- answer_sha256: `0f80efab74e7c50dd1a24b8188611211d6427771ce272a07b0cbd60c3b0f3981`

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
- supporting_evidence_ids: external/16-vector-embedding-datawhale.md@804-1403#9a28961b0343；internal/01_RAG基础原理.md@0-871#dfa7ac57160a；internal/01_RAG基础原理.md@871-1622#b2cf54881a08
- reason: 证据充分回答了embedding与retrieval的关系：外部文档明确说明embedding是语义检索的基础，其质量决定检索质量；内部文档详细描述了embedding在索引和检索两个阶段的作用，并强调必须使用同一模型，且检索结果直接影响生成质量。这些证据共同覆盖了问题的核心需求，无冲突。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 7
- unsupported_claim_count: 2

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | external/16-vector-embedding-datawhale.md | external/16-vector-embedding-datawhale.md@804-1403#9a28961b0343 | 0.0315 |
| E4 | internal/01_RAG基础原理.md | internal/01_RAG基础原理.md@871-1622#b2cf54881a08 | 0.0161 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.2220 | E4 | 在RAG（检索增强生成）中，embedding和retrieval之间的关系是密切相关的 |
| 2 | supported | 0.2742 | E1 | 具体来说，embedding在RAG的“检索”环节中起着核心作用 |
| 3 | supported | 0.2665 | E1 | 其流程如下： 1. **离线索引构建**：将文档切分后，使用embedding模型将每个文档块转换为向量，并存入向量数据库 |
| 4 | supported | 0.2439 | E1 | **在线查询检索**：用户提出问题时，使用同一个embedding模型将问题转换为向量 |
| 5 | unsupported | 0.0428 | E1 | **相似度计算**：在向量数据库中计算问题向量与文档块向量的相似度 |
| 6 | unsupported | 0.0600 | E1 | **召回上下文**：选取相似度最高的文档块作为上下文信息，供大语言模型生成最终答案 |
| 7 | supported | 0.2255 | E1 | 因此，embedding的质量直接影响检索的准确性和相关性，进而影响生成的答案质量 [E1][E4] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: IMPLICIT_COMPARE 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=2；unsupported_claim
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,146.237
- model_call_count: 1
- prompt_tokens: 375
- completion_tokens: 47
- total_tokens: 422
- estimated_cost_usd: 0.000084

### 追溯信息

- source_cer_sha256: `3fe9612b621a2fa7daa5f24650d5c6413274d0f770b35a87cdd3c9b1464a909c`
- answer_sha256: `4a53fa6d29e17151a92b3bd1f1c89282eeb9d6f96a4dce0cd0d178c0e227eced`

## q22 — 为什么 chunk 不是越大越好？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: medium
- reason: 问题涉及对 chunk 大小的整体理解，且没有明显不可验证风险。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/02_Chunk策略.md@0-685#1411d3bdb16d；internal/02_Chunk策略.md@1391-1768#5c5d7a6818b5；external/14-text-chunking-datawhale.md@597-1194#e880edf6d91e；external/14-text-chunking-datawhale.md@0-597#15353cefe471
- reason: 证据充分覆盖了chunk过大的多个核心原因：检索精度下降、噪声稀释、embedding信息损失、context窗口占用等，且内部与外部来源一致，足以支撑回答。

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
| E2 | internal/02_Chunk策略.md | internal/02_Chunk策略.md@1391-1768#5c5d7a6818b5 | 0.0313 |
| E3 | external/14-text-chunking-datawhale.md | external/14-text-chunking-datawhale.md@597-1194#e880edf6d91e | 0.0306 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.2238 | E2 | Chunk 不是越大越好的原因主要有以下几点： 1. **检索精度下降**：过大的 chunk 会导致相关内容被噪声稀释，从而降低检索的精度 [E2] |
| 2 | partial | 0.2124 | E2 | **上下文不完整**：如果 chunk 过小，可能会导致上下文丢失，影响信息的完整性 [E2] |
| 3 | partial | 0.1869 | E2 | **信息损失**：在嵌入过程中，较大的 chunk 会导致信息稀释，关键细节可能被模糊化，从而降低检索的效果 [E3] |
| 4 | supported | 0.3149 | E2 | **占用更多资源**：过大的 chunk 会占用更多的 LLM context 窗口，限制可用的上下文信息 [E2] |
| 5 | supported | 0.2542 | E2 | 因此，chunk 的大小需要在128到512 tokens之间进行调整，以适应不同的任务需求 [E2] |

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

- offline_total_ms: 3,083.529
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 50
- total_tokens: 422
- estimated_cost_usd: 0.000086

### 追溯信息

- source_cer_sha256: `8c3cd25c8dc2326d7482e7c65dec89a2d9069e803ba99164d7e26e7c3c6fd510`
- answer_sha256: `ae339c9a433899d4cfdad7764a85940a2b17ff0cc1f712c3bffc43522c781ad0`

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
- supporting_evidence_ids: external/12-检索增强生成 (RAG) 技术综述-syhya.md@1237-1865#09b01ab21d25；external/14-text-chunking-datawhale.md@2550-3384#9b6f0029c9d2；internal/02_Chunk策略.md@0-685#1411d3bdb16d
- reason: 证据包中多个来源直接对比了语义分块与固定分块的优势。internal/02_Chunk策略.md明确列出固定分块缺点为'可能在语义中间切断'、'不考虑语义边界，检索精度较差'，语义分块优点为'保留语义完整性'、'检索时chunk内容自洽，减少歧义'；external/14-text-chunking-datawhale.md指出固定分块'可能会在语义边界处切断文本，影响内容的完整性和连贯性'，语义分块'在语义主题发生显著变化的地方进行切分'使每个分块具有高度内部语义一致性；external/12综述也说明固定分块'可能切断语义单元'，语义分块'识别文本中的语义边界'。这些证据共同且一致地支撑了语义分块相比固定分块的主要优势在于保留语义完整性、避免切断语义单元、提升检索精度和内容自洽性，足以回答用户问题，无冲突或缺失。

### 引用证据支撑（规则）

- citation_support_label: unsupported
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 2
- unsupported_claim_count: 2

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | external/12-检索增强生成 (RAG) 技术综述-syhya.md | external/12-检索增强生成 (RAG) 技术综述-syhya.md@1237-1865#09b01ab21d25 | 0.0481 |
| E5 | internal/02_Chunk策略.md | internal/02_Chunk策略.md@0-685#1411d3bdb16d | 0.0315 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | unsupported | 0.0318 | E5 | 语义分块相比固定分块的主要优势在于它能够保留语义完整性，确保每个分块的内容在语义上自洽，减少歧义 |
| 2 | unsupported | 0.0330 | E5 | 这是因为语义分块是根据文本的语义边界进行切分，而固定分块则可能在语义中间切断，导致信息的丢失和检索精度的降低 [E1][E5] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: EXPLICIT_COMPARE 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=unsupported；unsupported_claim_count=2；unsupported_claim
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,150.438
- model_call_count: 1
- prompt_tokens: 376
- completion_tokens: 56
- total_tokens: 432
- estimated_cost_usd: 0.000090

### 追溯信息

- source_cer_sha256: `44eb90c06bb65480cce1cd31a0b671928b7de6b3aa8bb61bdea3b8e0dbd2f75f`
- answer_sha256: `4641cb9439c981d08e930d0971a6c1ce90cc5d262665e1fa6c75f7fdd8cdc89a`

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
- supporting_evidence_ids: external/16-vector-embedding-datawhale.md@804-1403#9a28961b0343；internal/01_RAG基础原理.md@871-1622#b2cf54881a08；internal/01_RAG基础原理.md@0-871#dfa7ac57160a
- reason: 证据充分覆盖了Embedding在RAG中的核心作用：作为语义检索的基础（将文档块和查询向量化、相似度计算、召回上下文），决定检索质量，以及发生在索引和检索两个阶段且需使用同一模型。这些信息足以回答用户问题，无冲突或明显缺口。

### 引用证据支撑（规则）

- citation_support_label: supported
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 4
- unsupported_claim_count: 0

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | external/16-vector-embedding-datawhale.md | external/16-vector-embedding-datawhale.md@804-1403#9a28961b0343 | 0.0325 |
| E2 | internal/01_RAG基础原理.md | internal/01_RAG基础原理.md@871-1622#b2cf54881a08 | 0.0318 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.3070 | E1 | 在RAG（检索增强生成）系统中，Embedding主要起到以下作用： 1. **语义检索的基础**：Embedding用于将知识库中的文档块和用户查询转换为向量，以便进行相似度计算和检索 |
| 2 | supported | 0.2244 | E1 | 具体流程包括离线索引构建和在线查询检索，确保使用同一Embedding模型以保持向量空间的一致性 [E1][E2] |
| 3 | supported | 0.2276 | E1 | **决定检索质量的关键**：Embedding的质量直接影响检索结果的准确性和相关性 |
| 4 | supported | 0.2472 | E1 | 优秀的Embedding模型能够捕捉问题与文档之间的深层语义联系，从而提高最终生成答案的质量 [E1] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: SUMMARY 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: low
- level_meaning: 不确定性/风险低
- reasons: none

### D-full 后置评测耗时与用量

- offline_total_ms: 1,520.252
- model_call_count: 1
- prompt_tokens: 375
- completion_tokens: 52
- total_tokens: 427
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `7e673fcee7590dc3047acd969b4d2a25ddeb1f2230eed01e3f1169c593eb8d15`
- answer_sha256: `b6da4a29b0d1e08516aa4f5c9a7733f1b4d3be71fdd63dc01910639cec4838a5`

## q25 — RAG 系统中，检索阶段的错误会如何影响最终回答？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: high
- reason: 问题明确，涉及检索阶段错误对最终回答的影响，且可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/04_RAG失败模式.md@0-639#222aea480737；internal/01_RAG基础原理.md@871-1622#b2cf54881a08；external/11_RAG_intro.md@3858-4404#83cbfcf736af
- reason: 证据包中的核心文档（internal/04_RAG失败模式.md）直接且详细地阐述了检索阶段错误（召回不准、召回遗漏）对最终回答的影响，包括导致生成错误或无意义回答、证据不足时应拒答但可能幻觉作答等。其他文档（internal/01_RAG基础原理.md、external/11_RAG_intro.md）从流程和挑战角度补充支持了检索错误影响生成质量的论述。证据之间无冲突，足以支撑回答用户问题。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 4
- unsupported_claim_count: 1

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/04_RAG失败模式.md | internal/04_RAG失败模式.md@0-639#222aea480737 | 0.0328 |
| E5 | internal/01_RAG基础原理.md | internal/01_RAG基础原理.md@871-1622#b2cf54881a08 | 0.0161 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.2443 | E1 | 在 RAG 系统中，检索阶段的错误会对最终回答产生显著影响，主要体现在以下几个方面： 1. **召回不准（低精度）**：如果检索到的文档片段与用户问题不相关，LLM 将获得噪声上下文，从而生成错误或无意义的回答 [E1] |
| 2 | unsupported | 0.0548 | E1 | **召回遗漏（低召回）**：当相关文档未被检索到时，系统可能会面临证据不足的情况，虽然应拒绝回答，但可能会产生幻觉作答 [E1] |
| 3 | partial | 0.1868 | E1 | **检索正确但生成错误**：即使检索到正确的文档，如果生成阶段出现问题，LLM 仍然可能给出错误的答案，这被视为生成层的失败 [E1] |
| 4 | partial | 0.1748 | E5 | 因此，检索阶段的准确性直接影响到生成阶段的质量，检索失败是 RAG 系统最主要的失败来源之一 [E5] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: SUMMARY 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=1；unsupported_claim；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,411.056
- model_call_count: 1
- prompt_tokens: 380
- completion_tokens: 50
- total_tokens: 430
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `378bbe395e9ab6ecd0c5560bd92108d92fc2391025d5996301d19dc10a5fc83b`
- answer_sha256: `5c1cad67b3d152de190e7383fe44443c7f6cf3ead8a8128ebdeb7da6220107b1`

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
- supporting_evidence_ids: internal/07_向量索引算法HNSW与IVF.md@849-1558#5387fc2754ce；internal/07_向量索引算法HNSW与IVF.md@301-849#cca57ff7d9dd；internal/05_pgvector原理.md@682-1303#b9f400273076；external/22-milvus-datawhale.md@4526-5014#fc79b169f6c2；external/26-Milvus-索引解释.md@3003-3627#3603b200df69
- reason: 多个来源（内部文档和外部文档）共同提供了IVF与HNSW在构建方式、查询性能、内存占用、召回率、适用场景等方面的对比信息，足以回答用户问题。证据之间无直接冲突，内容互补。

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 4
- resolved_citation_count: 4
- unresolved_citation_count: 0
- claim_count: 9
- unsupported_claim_count: 0

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E3 | internal/07_向量索引算法HNSW与IVF.md | internal/07_向量索引算法HNSW与IVF.md@849-1558#5387fc2754ce | 0.0323 |
| E5 | internal/07_向量索引算法HNSW与IVF.md | internal/07_向量索引算法HNSW与IVF.md@301-849#cca57ff7d9dd | 0.0164 |
| E2 | external/26-Milvus-索引解释.md | external/26-Milvus-索引解释.md@3003-3627#3603b200df69 | 0.0323 |
| E4 | external/22-milvus-datawhale.md | external/22-milvus-datawhale.md@4526-5014#fc79b169f6c2 | 0.0315 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.2517 | E4 | IVF（倒排文件索引）和HNSW（分层可导航小世界图）在以下几个方面有显著区别： 1. **构建方式**： - IVF需要先进行聚类，生成质心后才能建立索引，构建速度较快，但不支持增量插入 [E3] |
| 2 | partial | 0.1832 | E4 | - HNSW支持边插入边索引，允许动态更新，构建时间较长 [E5] |
| 3 | partial | 0.2066 | E2 | **内存占用**： - IVF及其变体（如IVFPQ）通常占用较少内存，因为它们的向量存储方式更为高效 [E2] |
| 4 | partial | 0.1811 | E4 | - HNSW由于其图结构需要存储边信息，内存占用较高 [E5] |
| 5 | partial | 0.1823 | E3 | **查询性能**： - IVF的查询速度受`nprobe`参数影响，较高的`nprobe`会提高精度但增加延迟 [E3] |
| 6 | partial | 0.2088 | E4 | - HNSW在查询时速度极快，尤其适合低延迟需求的场景，且高召回率 [E4] |
| 7 | partial | 0.2131 | E4 | **适用场景**： - IVF适合通用场景，尤其是大规模数据集的高吞吐量需求 [E4] |
| 8 | partial | 0.2088 | E4 | - HNSW更适合对查询延迟有严格要求的应用，如实时推荐和在线搜索 [E4] |
| 9 | supported | 0.2314 | E4 | 综上所述，IVF和HNSW各有优缺点，选择时需根据具体应用场景的需求进行权衡 |

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

- offline_total_ms: 2,328.459
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 54
- total_tokens: 431
- estimated_cost_usd: 0.000089

### 追溯信息

- source_cer_sha256: `26c79bb11ffbf4e2e3853afd0eb46c9f44f6bb45b926183bbe1a1d51535a8142`
- answer_sha256: `d8e2aa9755dd27bfea40ed5b6da94498f20836bb80390559de7292e90663df8a`

## q27 — 为什么 HNSW 通常具有更高的检索精度？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: high
- reason: 问题明确，涉及 HNSW 的检索精度，且可以提供相关的总结性回答。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT
- confidence: high
- supporting_evidence_ids: internal/07_向量索引算法HNSW与IVF.md@301-849#cca57ff7d9dd；internal/06_Qdrant架构.md@464-965#34d2c3600e13；external/26-Milvus-索引解释.md@1888-2401#e410b1448e85
- reason: 证据包包含多个直接解释HNSW检索精度优势的片段：internal/07文档详细说明HNSW的多层图结构、贪心搜索机制及参数（M、ef_construction、ef_search）对精度的影响，并指出其在高召回率下延迟最低；internal/06文档说明HNSW为Qdrant默认索引，参数增大可提升精度，且可过滤HNSW避免后过滤精度损失；external/26文档指出基于图的索引在QPS上通常优于IVF变体。这些证据共同从算法原理、参数调优和实际对比角度充分回答了'为什么HNSW通常具有更高的检索精度'，足以支撑归纳性回答。

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
| E5 | internal/07_向量索引算法HNSW与IVF.md | internal/07_向量索引算法HNSW与IVF.md@301-849#cca57ff7d9dd | 0.0313 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1649 | E5 | HNSW 通常具有更高的检索精度，主要是因为其采用了分层图结构，能够在多个层次上进行搜索，从而实现更精细的邻近搜索 |
| 2 | partial | 0.1728 | E5 | 具体来说，HNSW 通过从顶层开始逐层向下搜索，最终在稠密层进行精确的最近邻查找，这种方法有效提高了召回率和检索精度 |
| 3 | partial | 0.1941 | E5 | 此外，HNSW 的关键参数如每个节点的最大连接边数和构建时的候选集大小，均可以通过调整来进一步优化精度和性能 [E5] |

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

- offline_total_ms: 2,568.682
- model_call_count: 1
- prompt_tokens: 378
- completion_tokens: 55
- total_tokens: 433
- estimated_cost_usd: 0.000090

### 追溯信息

- source_cer_sha256: `8e6f13c4b5d2f1bf2f84eab66cd4014a35bec1c5104a500bc3c8af63aeaf500e`
- answer_sha256: `ae8f3d87b066bd40931b52c7dd8ad653c1b475be2e185f3a52903cadb4a622e6`

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
- missing_evidence: 没有证据明确说明 etcd 在 Kubernetes 中的作用，如作为集群状态存储、保存所有集群数据、提供一致性保证等。现有证据仅将 etcd 标记为 'KV存储'，未解释其具体功能。；缺少关于 etcd 如何与 API Server 交互、如何存储集群配置和状态、以及其高可用性要求的说明。
- reason: 唯一相关证据（internal/08_Kubernetes基础架构.md）仅在架构图中将 etcd 标注为 'KV存储'，未提供任何关于其作用、功能或重要性的具体描述。其他证据分别涉及 Service、存储类和索引优化，与 etcd 无关。因此，证据不足以回答用户关于 etcd 作用的问题。

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
- missing_info: insufficient_evidence_after_reretrieve；没有证据明确说明 etcd 在 Kubernetes 中的作用，如作为集群状态存储、保存所有集群数据、提供一致性保证等。现有证据仅将 etcd 标记为 'KV存储'，未解释其具体功能。；缺少关于 etcd 如何与 API Server 交互、如何存储集群配置和状态、以及其高可用性要求的说明。；唯一相关证据（internal/08_Kubernetes基础架构.md）仅在架构图中将 etcd 标注为 'KV存储'，未提供任何关于其作用、功能或重要性的具体描述。其他证据分别涉及 Service、存储类和索引优化，与 etcd 无关。因此，证据不足以回答用户关于 etcd 作用的问题。
- safe_answer_boundary: 当前证据不足，回答边界应限制在已检索到的证据范围内，不能补全缺失信息。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,144.594
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 53
- total_tokens: 425
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `38e7969b6867a5f29e69ffd06329fcedf3e776036dd17bd8b3b57b32d6cff9fc`
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
- supporting_evidence_ids: internal/09_MultiAZ高可用设计.md@613-1434#0c95c99cfcbb；internal/09_MultiAZ高可用设计.md@1434-2292#093c8c8d2e8b；internal/09_MultiAZ高可用设计.md@0-613#57a9e750463e；external/32-Amazon-RDS的多可用区数据库实例部署.md@650-1315#3b9185283564
- reason: 证据充分覆盖了跨AZ部署副本的核心原因：故障隔离（AZ独立故障域）、同步复制保证数据不丢（RPO≈0）、负载均衡跨AZ分发、Kubernetes强制跨AZ分布（反亲和性、TopologySpreadConstraints）、有状态服务挑战及解决方案，以及外部RDS文档佐证。这些证据直接回答了'为什么需要跨AZ部署副本'，足以支撑归纳回答。

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
| E1 | internal/09_MultiAZ高可用设计.md | internal/09_MultiAZ高可用设计.md@613-1434#0c95c99cfcbb | 0.0328 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1637 | E1 | 在 Multi-AZ 架构中，跨 AZ 部署副本的主要原因是为了实现故障隔离和高可用性 |
| 2 | partial | 0.1575 | E1 | 当一个可用区（AZ）发生故障时，其他 AZ 中的副本可以继续提供服务，从而降低单点风险 |
| 3 | partial | 0.1966 | E1 | 例如，如果 AZ-1 发生故障，AZ-2 和 AZ-3 上的副本不受影响，可以自动切换，确保服务的持续可用性 [E1] |
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

- offline_total_ms: 2,377.051
- model_call_count: 1
- prompt_tokens: 381
- completion_tokens: 53
- total_tokens: 434
- estimated_cost_usd: 0.000089

### 追溯信息

- source_cer_sha256: `8232b61727ad3321fd02bc9b5317d4c7a95ed40012ba993bbceae8146e919305`
- answer_sha256: `08c31983eeb4960e5c41c2316b9413f4d637ad3b78e5223bf398cab687f4e6fd`

## q30 — 为什么 KV cache 会成为大模型推理的关键优化点？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: medium
- reason: 问题明确，涉及 KV cache 在大模型推理中的作用，但可能需要更具体的上下文来详细回答。

### 证据充分性

- raw_verdict: INSUFFICIENT
- control_verdict: INSUFFICIENT
- confidence: medium
- supporting_evidence_ids: internal/10_模型服务层vLLM架构.md@0-773#e9b11b984010；external/34-vllm_architecture_cn.md@4392-4854#e44bd71a8184
- missing_evidence: 需要更直接、更完整地解释 KV cache 为何成为大模型推理关键优化点的证据，包括其作用机制、显存占用规模、对吞吐量和延迟的影响，以及与传统方法的对比。当前证据仅部分覆盖，且包含大量无关内容。
- reason: 证据包中仅第一条证据（internal/10）直接解释了 KV cache 的定义、作用（避免重复计算）和显存占用问题，第二条证据（external/34 自动前缀缓存部分）补充了 PagedAttention 解决内存碎片的思想，但两者均未完整覆盖问题核心，如 KV cache 为何成为关键优化点的具体原因（如显存占比、内存管理低效对吞吐量的影响）虽有提及但不够系统。其余证据（external/26 的两条和 external/34 的异步引擎参数部分）与问题无关，属于检索噪声。整体证据不足以支撑全面回答，缺少对 KV cache 优化重要性的深入阐述和量化对比。

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
- missing_info: insufficient_evidence_after_reretrieve；需要更直接、更完整地解释 KV cache 为何成为大模型推理关键优化点的证据，包括其作用机制、显存占用规模、对吞吐量和延迟的影响，以及与传统方法的对比。当前证据仅部分覆盖，且包含大量无关内容。；证据包中仅第一条证据（internal/10）直接解释了 KV cache 的定义、作用（避免重复计算）和显存占用问题，第二条证据（external/34 自动前缀缓存部分）补充了 PagedAttention 解决内存碎片的思想，但两者均未完整覆盖问题核心，如 KV cache 为何成为关键优化点的具体原因（如显存占比、内存管理低效对吞吐量的影响）虽有提及但不够系统。其余证据（external/26 的两条和 external/34 的异步引擎参数部分）与问题无关，属于检索噪声。整体证据不足以支撑全面回答，缺少对 KV cache 优化重要性的深入阐述和量化对比。
- safe_answer_boundary: 当前证据不足，回答边界应限制在已检索到的证据范围内，不能补全缺失信息。

### D-full 后置评测耗时与用量

- offline_total_ms: 2,462.198
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 58
- total_tokens: 435
- estimated_cost_usd: 0.000091

### 追溯信息

- source_cer_sha256: `b4327d75c480ef2cdbbd3d9477dd92c21c39e6a8c17274a4968b0286b7a3b0fa`
- answer_sha256: `76bf36d8ac30d8cd4dbfdd22e7e40a5be87f2d4e53ad995d12f1147b903196cf`
