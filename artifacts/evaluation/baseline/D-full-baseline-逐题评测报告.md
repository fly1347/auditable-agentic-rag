# D-full baseline 逐题评测报告

> source_profile: `baseline`；classifier.mode: `llm=30`；sufficiency.mode: `binary=30`。批次共同配置不再逐题重复。

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
- reason: 问题明确询问 RAG 流程的主要步骤，信息可验证且范围清晰。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT

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
| 2 | unsupported | 0.0200 | E2 | **离线索引阶段**： - 文档加载：从不同的数据源加载原始数据 |
| 3 | unsupported | 0.0093 | E2 | - 文本分块：将加载的文档分割成较小的文本块 |
| 4 | partial | 0.1631 | E2 | - Embedding 计算：将文本映射到高维向量空间 |
| 5 | unsupported | 0.0140 | E2 | - 向量存储：将向量写入数据库以建立索引 |
| 6 | unsupported | 0.0185 | E2 | **在线检索-生成阶段**： - 用户查询：接收用户的查询请求 |
| 7 | partial | 0.1618 | E2 | - Query Embedding：将查询转化为向量 |
| 8 | unsupported | 0.0235 | E2 | - 向量相似度检索：从索引中检索最相关的文档片段 |
| 9 | partial | 0.1502 | E2 | - 构建 Prompt：将查询和检索到的文档片段结合 |
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

- offline_total_ms: 2,130.585
- model_call_count: 1
- prompt_tokens: 373
- completion_tokens: 54
- total_tokens: 427
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `1ce19a11bb975f1feb768104dcace5fbf61fc99f5a25eb646e1182583d95f4ae`
- answer_sha256: `4134c414c74629ef1b8cbf586d92ce927a68dcc5ca779f6fcf7cdc23157aa14e`

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
- missing_info: insufficient_evidence_after_reretrieve
- safe_answer_boundary: 当前证据不足，回答边界应限制在已检索到的证据范围内，不能补全缺失信息。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,649.584
- model_call_count: 1
- prompt_tokens: 374
- completion_tokens: 52
- total_tokens: 426
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `c8f91feaf9cd0f2fd11a0392bc994c3aa049b19de31f89a2964e8bd05ac630e5`
- answer_sha256: `76bf36d8ac30d8cd4dbfdd22e7e40a5be87f2d4e53ad995d12f1147b903196cf`

## q03 — 固定长度 chunk 和语义分块有什么区别？

### 分类与回答边界

- actual_route: DECOMPOSE
- question_type: EXPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: high
- reason: 问题明确要求比较两种分块方式，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT

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

- offline_total_ms: 2,273.879
- model_call_count: 1
- prompt_tokens: 374
- completion_tokens: 50
- total_tokens: 424
- estimated_cost_usd: 0.000086

### 追溯信息

- source_cer_sha256: `54b11ec3c931cad9485dafc8cab70a597076f760ba5edd22516688b84e6b9f08`
- answer_sha256: `9b32557fc03962a066dc31b4cc430876f9c6565fed87c446f60a07430fc20776`

## q04 — chunk size 过大会带来什么问题？

### 分类与回答边界

- actual_route: DIRECT
- question_type: OPEN_MULTI
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: high
- reason: 问题明确，涉及多个可能的影响，且可验证

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT

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
| 1 | partial | 0.1436 | E1 | chunk size 过大会带来以下问题： 1. 检索精度下降，相关内容可能被噪声稀释 |
| 2 | supported | 0.2512 | E1 | 占用更多的 LLM context 窗口，导致处理效率降低 |
| 3 | partial | 0.2107 | E1 | embedding 向量的语义混杂，信息表达变得笼统，关键细节模糊化，从而降低检索的精度 [E1][E2] |

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

- offline_total_ms: 1,045.961
- model_call_count: 1
- prompt_tokens: 373
- completion_tokens: 45
- total_tokens: 418
- estimated_cost_usd: 0.000083

### 追溯信息

- source_cer_sha256: `4fb84d37da55eeb78ef59d5402092e074cd0440e8499ec824d9ba92daf20d268`
- answer_sha256: `38aa19f6439f55b1969eb62063c58c6e3f6f98065aa251d41478b7b2992581b5`

## q05 — 为什么 embedding 相似度常用余弦相似度？

### 分类与回答边界

- actual_route: DIRECT
- question_type: NARROW_FACT
- answerability: IN_SCOPE
- route_candidate: DIRECT
- confidence: high
- reason: 问题明确，询问的是余弦相似度在 embedding 相似度中的常用原因，答案可以提供具体的解释。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT

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

- offline_total_ms: 2,254.178
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 65
- total_tokens: 442
- estimated_cost_usd: 0.000096

### 追溯信息

- source_cer_sha256: `ddd8cb2f17c19b583d06ecbedf64aee044bd93b1b7eb41954b94d4965f0159cc`
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

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 3
- unsupported_claim_count: 2

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | external/12-检索增强生成 (RAG) 技术综述-syhya.md | external/12-检索增强生成 (RAG) 技术综述-syhya.md@518-1237#59ad08ea7df5 | 0.6060 |
| E3 | external/12-检索增强生成 (RAG) 技术综述-syhya.md | external/12-检索增强生成 (RAG) 技术综述-syhya.md@20859-21506#4ce255e17806 | 0.5993 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1314 | E1 | 在 RAG 系统中，容易产生 hallucination 的情况主要与以下因素有关： 1. **上下文窗口限制**：由于 LLM 的上下文窗口长度有限，过长的上下文可能导致中间遗忘问题，从而影响生成的准确性 [E1] |
| 2 | unsupported | 0.0341 | E3 | **噪声管理**：在训练中注入不相关结果或噪声可能会影响模型的鲁棒性，导致生成不准确的信息 [E3] |
| 3 | unsupported | 0.0888 | E3 | 因此，RAG 系统在处理信息时，若未能有效管理上下文和噪声，容易产生 hallucination |

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

- offline_total_ms: 2,035.135
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 57
- total_tokens: 434
- estimated_cost_usd: 0.000091

### 追溯信息

- source_cer_sha256: `5073aa8631f7fbed4ebef0710eec5279a7a0ed495ea318cafa0044920b442cac`
- answer_sha256: `82622d91d3f1da90c19239828b626f17807f37697b76128c387bc2b9adb79bd5`

## q07 — Multi-AZ 部署如何降低系统单点故障风险？

### 分类与回答边界

- actual_route: DIRECT
- question_type: PROCEDURE
- answerability: IN_SCOPE
- route_candidate: DIRECT
- confidence: high
- reason: 问题明确询问 Multi-AZ 部署的具体操作和效果，且没有不可验证的风险。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT

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
| 1 | partial | 0.2028 | E1 | Multi-AZ 部署通过以下方式降低系统单点故障风险： 1. **故障隔离**：每个可用区（AZ）是独立的故障域，某个 AZ 发生故障时，其他 AZ 的服务不受影响，能够实现自动故障转移 |
| 2 | partial | 0.1693 | E1 | 例如，当 AZ-1 发生故障时，AZ-2 可以自动提升为主节点，确保服务持续可用 [E1] |
| 3 | partial | 0.1911 | E1 | **同步复制**：数据库在写入时会同步复制到多个 AZ 的副本，确保在故障切换时数据不会丢失，达到接近零的数据丢失目标（RPO ≈ 0） [E1] |
| 4 | partial | 0.1898 | E1 | **负载均衡**：负载均衡器将请求分发到多个 AZ 中的健康实例，单个 AZ 故障时流量会自动切换，用户不会感知到服务中断 [E1] |
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

- offline_total_ms: 1,141.619
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 56
- total_tokens: 433
- estimated_cost_usd: 0.000090

### 追溯信息

- source_cer_sha256: `178caf15c6031dd5177bfb445a1765c58654347fc02648c0be3991d3ab0cb566`
- answer_sha256: `e58fb77010470b02f6e174c97d57cceea4878c5c7694d58556e99251abbba437`

## q08 — HNSW 和 IVF 向量索引有什么主要区别？

### 分类与回答边界

- actual_route: DECOMPOSE
- question_type: EXPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: high
- reason: 问题明确要求比较两个已知的向量索引方法，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT

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
| E4 | external/22-milvus-datawhale.md | external/22-milvus-datawhale.md@4526-5014#fc79b169f6c2 | 0.0313 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1584 | E4 | HNSW（Hierarchical Navigable Small World）和IVF（Inverted File）是两种主要的向量索引算法，它们的主要区别在于数据结构和检索方式： 1. **数据结构**： - HNSW使用基于图的结构，通过构建多层邻近图来进行检索，适合处理高维数据和低延迟查询 [E4] |
| 2 | supported | 0.2389 | E4 | - IVF则将向量分成多个“桶”，查询时先找到最相似的几个桶，然后在这些桶内进行精确搜索 [E4] |
| 3 | partial | 0.2029 | E4 | **检索速度与召回率**： - HNSW提供较高的检索速度和召回率，尤其在高维数据中表现优异，但内存占用较大 [E4] |
| 4 | supported | 0.2450 | E4 | - IVF通过缩小搜索范围来提升检索速度，但召回率不是100%，因为相关向量可能被分到未搜索的桶中 [E4] |
| 5 | supported | 0.2283 | E4 | **适用场景**： - HNSW适合对查询延迟有严格要求的场景，如实时推荐和在线搜索 [E4] |
| 6 | partial | 0.2075 | E4 | - IVF适合需要高吞吐量的大规模数据集的通用场景 [E4] |
| 7 | supported | 0.2336 | E4 | 综上所述，HNSW和IVF在数据结构、检索效率和适用场景上存在显著差异 |

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

- offline_total_ms: 2,091.669
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 54
- total_tokens: 431
- estimated_cost_usd: 0.000089

### 追溯信息

- source_cer_sha256: `eabce41cd4be0aae89063d2526f0b7c4b3774c9b66937ca91c24cf274b066f27`
- answer_sha256: `99d91adf0778fc036dcd84954f13dd4e06af964769723e264d5c891866892889`

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
| 4 | supported | 0.2603 | E2 | **Controller Manager（kube-controller-manager）**：多个控制器的集合，负责使实际状态趋向期望状态，如管理 Pod 副本数、滚动更新等 [E1][E2] |

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

- offline_total_ms: 1,100.457
- model_call_count: 1
- prompt_tokens: 373
- completion_tokens: 52
- total_tokens: 425
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `81b67e7e4238b5674b7ac4412a640518b40aac0c5ed1dd1f22ecc80f99938b99`
- answer_sha256: `89cb8c02066d5be72159dd814c5d5bca290c736fa2d7cb0607f110d1d5547eec`

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
| E1 | internal/10_模型服务层vLLM架构.md | internal/10_模型服务层vLLM架构.md@0-773#e9b11b984010 | 0.7072 |
| E2 | external/34-vllm_architecture_cn.md | external/34-vllm_architecture_cn.md@5634-6214#2c8ba4fa9cdf | 0.6185 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.2534 | E1 | KV Cache 在大模型推理中的作用是缓存历史 token 的 Key 和 Value 矩阵，以避免在每次生成新 token 时重复计算，从而降低计算复杂度 |
| 2 | partial | 0.1721 | E1 | 具体来说，使用 KV Cache 可以将复杂度从 O(n²) 降低到 O(n)，显著提高推理效率 [E1] |
| 3 | partial | 0.1988 | E1 | 此外，KV Cache 还面临内存管理的挑战，传统方法导致内存利用率低下，而 vLLM 通过灵活的缓存策略和哈希表管理来优化 KV Cache 的使用 [E2] |

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

- offline_total_ms: 1,454.465
- model_call_count: 1
- prompt_tokens: 374
- completion_tokens: 54
- total_tokens: 428
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `db6ddaf9c4e9b622896917673f66382c7f8decd6905497d686b29a6e48d5b8af`
- answer_sha256: `96ef6976ec2209997a97cef2388167599d866fe3196f2956aabdb7f58cc4ee95`

## q11 — Overlap 在文本分块中有什么作用？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: high
- reason: 问题明确，涉及文本分块的作用，答案可以概括性地回答。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT

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
| 1 | supported | 0.2232 | E4 | Overlap 在文本分块中的作用主要有两个： 1. **防止信息丢失**：Overlap 通过在相邻的文本块之间共享一定数量的 token，防止跨越边界的关键信息被切断而丢失，从而保持信息的完整性 |
| 2 | partial | 0.1849 | E4 | **提升上下文连贯性**：Overlap 有助于保留上下文的连贯性，提升边界附近的检索召回率，使得模型在处理相邻块时能够更好地理解上下文关系 |
| 3 | partial | 0.2134 | E4 | 然而，Overlap 也有副作用，如增加存储量和可能导致信息冗余，因此通常建议将重叠设置为 chunk_size 的 10%~20% [E4] |

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

- offline_total_ms: 1,989.105
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 51
- total_tokens: 423
- estimated_cost_usd: 0.000086

### 追溯信息

- source_cer_sha256: `ddbc9ac3086349a48964e324d662444de1385b3135f1da3d6f801b5fae8b7cee`
- answer_sha256: `c936190f6a482e9450714f78c0f1f68350222dd105bf94bc621bf0d0f9ba47d1`

## q12 — Embedding 维度会影响哪些方面？

### 分类与回答边界

- actual_route: DIRECT
- question_type: OPEN_MULTI
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: high
- reason: 问题明确，涉及多个方面的影响，且可验证

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT

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

- offline_total_ms: 2,092.399
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 46
- total_tokens: 418
- estimated_cost_usd: 0.000083

### 追溯信息

- source_cer_sha256: `384fe433235e275b4e0f339fc2be416d357d1f12de8bde0703e84d07799e59e6`
- answer_sha256: `99cfc7f6ab9a34a2236d0057e769b85c5ff458eefc9c3e17eb59386f2a95807e`

## q13 — Embedding 是否真正“理解”语义？

### 分类与回答边界

- actual_route: DIRECT
- question_type: NARROW_FACT
- answerability: NEEDS_CLARIFICATION
- route_candidate: NEEDS_CLARIFICATION
- confidence: medium
- reason: 问题中缺少对“理解”具体含义的定义，导致无法给出明确回答。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT

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

- triggered: false
- conflict_count: 0
- trigger_reason: NARROW_FACT 不在规则触发类型中，不执行冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=1；unsupported_claim；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,117.989
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 59
- total_tokens: 431
- estimated_cost_usd: 0.000091

### 追溯信息

- source_cer_sha256: `96ac34f8b077c8f2b6b1f40397c8e5db1eec853323ebf53770f57b7df7c76222`
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
| E1 | internal/04_RAG失败模式.md | internal/04_RAG失败模式.md@1332-1937#311a87398ac2 | 0.6815 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1456 | E1 | “证据不充分”（Evidence Insufficient）指的是在回答中，检索到的内容未能提供足够的信息来支撑每个关键声明 |
| 2 | unsupported | 0.0390 | E1 | 这种情况的判断标准包括： 1. 回答中包含检索内容以外的推断 |
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

- offline_total_ms: 1,088.207
- model_call_count: 1
- prompt_tokens: 374
- completion_tokens: 57
- total_tokens: 431
- estimated_cost_usd: 0.000090

### 追溯信息

- source_cer_sha256: `8fc2796db9c1a007c0e3dd483fa6d4bde4c0b5ebbe53692dc3e45390aee46544`
- answer_sha256: `5433011c0e63b53a8e1a98d5bb64f993cc75ac106eeb4caf1f1b7be33a7950ee`

## q15 — 检索错但回答对，在 RAG 评估里算成功吗？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: medium
- reason: 问题涉及 RAG 评估的成功标准，范围明确但可能存在不同解读。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT

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
| 1 | partial | 0.1671 | E2 | 检索错但回答对在 RAG 评估中不算成功 |
| 2 | partial | 0.1805 | E2 | 尽管最终回答可能正确，但这源于 LLM 的参数记忆，而非可追溯的检索证据，因此不被视为有效的成功案例 |
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

- offline_total_ms: 2,444.419
- model_call_count: 1
- prompt_tokens: 380
- completion_tokens: 53
- total_tokens: 433
- estimated_cost_usd: 0.000089

### 追溯信息

- source_cer_sha256: `c00dd223705c5167b50545d24f97d97e7538e0940e47add49bde9598146370f4`
- answer_sha256: `d53631b4340850c9f18221a93a0b626542d93397e70c8558375d60fd62c992b2`

## q16 — pgvector 和专用向量数据库相比，有什么主要差异？

### 分类与回答边界

- actual_route: DECOMPOSE
- question_type: EXPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: high
- reason: 问题明确比较了两个对象，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 13
- unsupported_claim_count: 3

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/05_pgvector原理.md | internal/05_pgvector原理.md@1303-1989#f133a907d82c | 0.0320 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.3012 | E1 | pgvector 和专用向量数据库（如 Qdrant 和 Milvus）之间的主要差异如下： 1. **架构**：pgvector 是 PostgreSQL 的扩展，而专用向量数据库是独立的数据库系统 |
| 2 | supported | 0.2204 | E1 | **集成成本**：pgvector 的集成成本较低，因为可以复用已有的 PostgreSQL 栈 |
| 3 | unsupported | 0.0224 | E1 | 而专用向量数据库需要独立部署和维护 |
| 4 | supported | 0.2840 | E1 | **查询吞吐量**：pgvector 的查询吞吐量中等（约百级 QPS），而专用向量数据库如 Qdrant 的吞吐量可超过 4000 RPS |
| 5 | partial | 0.1899 | E1 | **过滤检索**：pgvector 需要额外调优以支持过滤检索，性能较差 |
| 6 | unsupported | 0.0285 | E1 | 专用向量数据库原生支持过滤检索，性能更好 |
| 7 | supported | 0.2265 | E1 | **事务/ACID 支持**：pgvector 完整支持事务和 ACID，而专用向量数据库的支持有限或不支持 |
| 8 | partial | 0.1953 | E1 | **量化压缩**：pgvector 的量化压缩能力有限，而专用向量数据库支持多种压缩方式 |
| 9 | partial | 0.1990 | E1 | **适用规模**：pgvector 适用于小于 1000 万向量的场景，而专用向量数据库适合亿级向量 |
| 10 | partial | 0.1899 | E1 | **运维复杂度**：pgvector 的运维复杂度较低，因为与业务数据同库 |
| 11 | unsupported | 0.0224 | E1 | 专用向量数据库的运维复杂度中等到高 |
| 12 | supported | 0.2367 | E1 | **结论**：如果已经使用 PostgreSQL 且向量规模小于 500 万，pgvector 是合理选择 |
| 13 | supported | 0.2243 | E1 | 如果向量规模大且对检索性能有严格要求，则应选择专用向量数据库如 Qdrant 或 Milvus [E1] |

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

- offline_total_ms: 2,191.925
- model_call_count: 1
- prompt_tokens: 378
- completion_tokens: 47
- total_tokens: 425
- estimated_cost_usd: 0.000085

### 追溯信息

- source_cer_sha256: `145641b00374b21ec2e0cfe27063d4fa86288c3a9dda5001a3e2f99e4b1ccd42`
- answer_sha256: `bf32a24a251f6d2cc4a144c6d876f953cffcdc0dde3acc158bee4915ef766012`

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
| 2 | partial | 0.1998 | E1 | - **磁盘存储**： - **Mmap（Memory-mapped）**：向量存储在磁盘上，由操作系统进行缓存管理，性能中等，内存友好 |
| 3 | partial | 0.1907 | E1 | - **On-disk（量化+磁盘）**：量化向量存储在磁盘上，原始向量用于重新排序，性能较慢，但成本最低 [E1] |
| 4 | unsupported | 0.0156 | E1 | **性能与成本**： - 内存存储提供最佳性能，但成本较高 |
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

- offline_total_ms: 1,469.003
- model_call_count: 1
- prompt_tokens: 380
- completion_tokens: 57
- total_tokens: 437
- estimated_cost_usd: 0.000091

### 追溯信息

- source_cer_sha256: `a166967a1cc7a84a2b40797a372d086402486c998a482205f2a793bd3549e19b`
- answer_sha256: `c030439532332677979b7b461cb1776f48de5dd4b8d64f6da3f7eb492af0bff2`

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
| E4 | internal/07_向量索引算法HNSW与IVF.md | internal/07_向量索引算法HNSW与IVF.md@1558-2289#f09b34881aa0 | 0.6188 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1896 | E4 | 在向量检索中，Recall（召回率）和Latency（延迟）之间需要权衡的原因在于，提升Recall通常会导致Latency的增加 |
| 2 | supported | 0.2542 | E4 | 具体来说： 1. **Recall的提升**：为了提高Recall，可能需要增加查询参数（如HNSW中的ef_search或IVF中的nprobe），这会使得检索过程需要处理更多的数据，从而增加延迟 |
| 3 | partial | 0.1898 | E4 | **Latency的影响**：当查询参数增大时，虽然可以获得更高的Recall，但相应的查询时间也会显著增加 |
| 4 | partial | 0.1749 | E4 | 例如，从90%提升到99%的Recall，可能需要2到5倍的查询时间代价 |
| 5 | partial | 0.1901 | E4 | 因此，在实际应用中，系统需要在Recall和Latency之间找到一个合适的平衡点，以满足业务需求 [E4] |

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

- offline_total_ms: 1,119.594
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 52
- total_tokens: 429
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `3b6759e69e940093455093e4caf5ead4a95f301da44bfafd290234f70d82d03c`
- answer_sha256: `31a77e963a3ae8c03efdae21807d99c0a101611f4d8fb578ac093a0208edeeb9`

## q19 — kube-scheduler 在 Kubernetes 集群里负责什么？

### 分类与回答边界

- actual_route: DIRECT
- question_type: NARROW_FACT
- answerability: IN_SCOPE
- route_candidate: DIRECT
- confidence: high
- reason: 问题明确询问 kube-scheduler 的职责，且该信息是公开可验证的。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT

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
| E1 | internal/08_Kubernetes基础架构.md | internal/08_Kubernetes基础架构.md@0-1115#f0413c5d9c86 | 0.6031 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1255 | E1 | kube-scheduler 在 Kubernetes 集群中负责将待调度的 Pod 分配到合适的工作节点上 |
| 2 | partial | 0.1399 | E1 | 它根据资源需求、调度策略和其他约束条件，选择最合适的节点来运行这些 Pod，从而实现负载均衡和资源优化 |
| 3 | partial | 0.1611 | E1 | 这个过程是 Kubernetes 控制平面的一部分，确保集群中的资源得到有效利用和管理 [E1] |

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

- offline_total_ms: 2,119.292
- model_call_count: 1
- prompt_tokens: 375
- completion_tokens: 55
- total_tokens: 430
- estimated_cost_usd: 0.000089

### 追溯信息

- source_cer_sha256: `e2bf9a53517c9eaa664d41027e5b32445d520453c1ee4bf56e3587343cd61d3e`
- answer_sha256: `56830edac1a103a39ab2919853e85cdd4343cbc75cee39708bae3754dfb589b8`

## q20 — 连续批处理（Continuous Batching）和传统静态批处理有什么区别？

### 分类与回答边界

- actual_route: DECOMPOSE
- question_type: EXPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: high
- reason: 问题明确要求比较两个具体的处理方式，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT

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
| E1 | internal/10_模型服务层vLLM架构.md | internal/10_模型服务层vLLM架构.md@773-1705#c76695ac0bf6 | 0.0492 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1852 | E1 | 连续批处理（Continuous Batching）与传统静态批处理的主要区别在于请求处理的方式和效率 |
| 2 | partial | 0.1860 | E1 | **请求处理方式**： - **传统静态批处理**：所有请求同时开始，必须等到最长的请求完成后才能接受新请求，这导致短请求完成后GPU处于空闲状态，利用率低 |
| 3 | partial | 0.1681 | E1 | - **连续批处理**：在处理请求时，一旦某个请求完成，可以立即插入新的请求，而无需等待其他请求完成，从而保持GPU的持续满载 |
| 4 | partial | 0.1630 | E1 | **效率**： - 连续批处理显著提升了吞吐量，相比传统方法，吞吐量提升可达14到24倍，确保GPU始终处于高效工作状态 [E1] |

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

- offline_total_ms: 991.731
- model_call_count: 1
- prompt_tokens: 380
- completion_tokens: 49
- total_tokens: 429
- estimated_cost_usd: 0.000086

### 追溯信息

- source_cer_sha256: `5f79ab2d4ed7680f35620005b9574908ad3595b9292511c974392b865a8e646b`
- answer_sha256: `83aeb5442cfcfc8828d9eb7a49c166bbbb3c9da9f5bb93288ddfd9d57ec6a609`

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
| 6 | supported | 0.2838 | E1 | **语义检索的基础**：RAG 的检索环节通常依赖于基于 embedding 的语义搜索 |
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

- offline_total_ms: 945.578
- model_call_count: 1
- prompt_tokens: 375
- completion_tokens: 47
- total_tokens: 422
- estimated_cost_usd: 0.000084

### 追溯信息

- source_cer_sha256: `abf38bb4174c0b6b3cc2939cac2eb899e9ed3cf77ab4c06e8cfa2e65cabb8e02`
- answer_sha256: `67c6331e16006e46418a3f26bf701cf83e0c59513cedd84c0640ffce483a743f`

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
| 4 | supported | 0.2843 | E1 | **embedding 向量语义混杂**：过大的 chunk 可能导致 embedding 向量的语义混合，影响后续的检索和生成质量 [E1] |
| 5 | partial | 0.1865 | E1 | 因此，选择合适的 chunk 大小是确保系统性能的关键 |

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

- offline_total_ms: 1,056.054
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 49
- total_tokens: 421
- estimated_cost_usd: 0.000085

### 追溯信息

- source_cer_sha256: `9b62fb7fd9104d9a1ac36f93b1d0deb66c44fdb6ef168a41276ccb2b40f419e7`
- answer_sha256: `2a038722afcad718262544ee357b8229f9992c4726b0bb20c3ee214791c0d751`

## q23 — 语义分块相比固定分块的主要优势是什么？

### 分类与回答边界

- actual_route: DECOMPOSE
- question_type: EXPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: high
- reason: 问题明确比较了语义分块和固定分块，且可以提供清晰的优势对比。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT

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
| 1 | unsupported | 0.0218 | E1 | 语义分块相比固定分块的主要优势在于其能够根据文本的语义内涵进行切分，从而保持每个分块的内部语义一致性 |
| 2 | unsupported | 0.0304 | E1 | 这种方法在语义主题发生显著变化的地方进行切分，避免了固定大小分块可能导致的语义单元被切断的问题 |
| 3 | unsupported | 0.0356 | E4 | 固定大小分块在处理超长段落时只能发出警告并保留，而语义分块则能够更灵活地调整分块策略，以确保信息的完整性和上下文的准确性 [E1][E4] |

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

- offline_total_ms: 1,252.789
- model_call_count: 1
- prompt_tokens: 376
- completion_tokens: 57
- total_tokens: 433
- estimated_cost_usd: 0.000091

### 追溯信息

- source_cer_sha256: `c218940763fc588d2d7398c466bfbf4da5d96a06a7cd1da81f1c9384f26e2e78`
- answer_sha256: `3c7fc5d8397f56ab74f95b47a3388857be9db8a8d2ef1bb815265780b099bfd1`

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
| E1 | external/16-vector-embedding-datawhale.md | external/16-vector-embedding-datawhale.md@804-1403#9a28961b0343 | 0.7542 |
| E2 | internal/01_RAG基础原理.md | internal/01_RAG基础原理.md@871-1622#b2cf54881a08 | 0.6469 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.3213 | E1 | 在 RAG（检索增强生成）系统中，Embedding 主要起到以下作用： 1. **语义检索的基础**：Embedding 是 RAG 流程中“检索”环节的核心，负责将知识库中的文档块和用户查询转换为向量，以便进行相似度计算和检索相关文档块 [E1] |
| 2 | supported | 0.2237 | E1 | **检索质量的关键**：Embedding 的质量直接影响检索结果的准确性和相关性 |
| 3 | supported | 0.2446 | E1 | 高质量的 Embedding 模型能够更好地捕捉问题与文档之间的深层语义联系，从而提高最终生成答案的质量 [E1] |
| 4 | supported | 0.2866 | E1 | **发生在两个阶段**：Embedding 在 RAG 中发生在索引阶段（对文档块计算向量并存入向量库）和检索阶段（对用户查询计算向量以进行相似度匹配），且两个阶段必须使用同一个 Embedding 模型 [E2] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: SUMMARY 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: low
- level_meaning: 不确定性/风险低
- reasons: none

### D-full 后置评测耗时与用量

- offline_total_ms: 1,235.280
- model_call_count: 1
- prompt_tokens: 375
- completion_tokens: 52
- total_tokens: 427
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `e1e350847b89ed0453c904dbff6c527d4a4d678080c54524f90a0a0673e35170`
- answer_sha256: `aa80cb32f6eca47dc67cb71e1234828ed0df83a57e91731ade1d72e8ef1e5aca`

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
| 4 | unsupported | 0.0162 | E1 | 因此，检索阶段的错误直接影响到生成阶段的质量和准确性，可能导致错误回答或幻觉现象的出现 |

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

- offline_total_ms: 1,395.354
- model_call_count: 1
- prompt_tokens: 380
- completion_tokens: 49
- total_tokens: 429
- estimated_cost_usd: 0.000086

### 追溯信息

- source_cer_sha256: `fd871f4389d74896bf870e06e00c288634ae2e07e1bd4e0fb08f67853e06a2b9`
- answer_sha256: `b2f25f95abe0325df058104e174791587a35b49911b51000b49735aec26da2fa`

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
| E1 | external/22-milvus-datawhale.md | external/22-milvus-datawhale.md@4526-5014#fc79b169f6c2 | 0.0328 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.3238 | E1 | IVF（倒排文件索引）和HNSW（基于图的索引）在原理、优缺点和适用场景上有显著差异： 1. **原理**： - IVF通过聚类将向量分成多个“桶”，查询时先找到最相似的几个桶，再在这些桶内进行精确搜索 |
| 2 | supported | 0.2588 | E1 | [E1] - HNSW构建一个多层的邻近图，查询时从稀疏图开始，快速定位到目标区域，然后在密集图中进行精确搜索 |
| 3 | supported | 0.2333 | E1 | [E1] 2. **优缺点**： - IVF的优点是提升检索速度，适合高吞吐量的大规模数据集，但召回率不是100% |
| 4 | supported | 0.2331 | E1 | [E1] - HNSW的优点是检索速度极快且召回率高，尤其适合高维数据和低延迟查询，但内存占用大且构建时间较长 |
| 5 | partial | 0.2067 | E1 | [E1] 3. **适用场景**： - IVF适用于通用场景，尤其是需要高吞吐量的情况 |
| 6 | partial | 0.2155 | E1 | [E1] - HNSW适用于对查询延迟有严格要求的场景，如实时推荐和在线搜索 |
| 7 | supported | 0.2255 | E1 | [E1] 综上所述，IVF和HNSW各有特点，选择时需根据具体需求进行权衡 |

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

- offline_total_ms: 1,110.261
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 53
- total_tokens: 430
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `32bb71fa76a06dba5ed4b7af375e3fcd7e8de4013ab810228d983515f6d2cdf5`
- answer_sha256: `d801ab673db6d0d7bc87cbaaf778cfd20b67fc1ce777159a4bf96c6053c2dc78`

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
| E4 | internal/07_向量索引算法HNSW与IVF.md | internal/07_向量索引算法HNSW与IVF.md@0-301#a87f5dd9a27c | 0.6008 |
| E5 | internal/06_Qdrant架构.md | internal/06_Qdrant架构.md@464-965#34d2c3600e13 | 0.5888 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.2442 | E5 | HNSW（Hierarchical Navigable Small World）通常具有更高的检索精度，主要是因为其在构建索引时采用了更复杂的图结构和参数配置，这使得它能够在近似最近邻（ANN）搜索中提供更好的结果 |
| 2 | supported | 0.2441 | E5 | 具体来说，HNSW通过设置较大的参数（如每层最大边数`m`和构建时扩展因子`ef_construct`）来提高索引质量，从而在检索时能够更准确地找到最相似的向量 |
| 3 | partial | 0.1687 | E4 | 此外，HNSW的设计允许在搜索过程中进行更有效的路径导航，进一步提升了检索的精度和效率 [E4][E5] |

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

- offline_total_ms: 1,070.381
- model_call_count: 1
- prompt_tokens: 378
- completion_tokens: 54
- total_tokens: 432
- estimated_cost_usd: 0.000089

### 追溯信息

- source_cer_sha256: `2b5fbee09bc6293aec3726b0d046886935ab7576a477b50904cfd6668cbda87d`
- answer_sha256: `f651688c97db8281405f0cd1ec43254a704c93e77f7a69c15448b7fb527859c4`

## q28 — Kubernetes 中 etcd 的作用是什么？

### 分类与回答边界

- actual_route: DIRECT
- question_type: NARROW_FACT
- answerability: IN_SCOPE
- route_candidate: DIRECT
- confidence: high
- reason: 问题明确询问 etcd 的作用，且该信息是公开可验证的。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT

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
| E1 | internal/08_Kubernetes基础架构.md | internal/08_Kubernetes基础架构.md@0-1115#f0413c5d9c86 | 0.6459 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1921 | E1 | Kubernetes 中 etcd 的作用是作为一个键值存储（KV存储），用于保存集群的所有配置数据和状态信息 |
| 2 | partial | 0.1672 | E1 | 它是 Kubernetes 控制平面的一个重要组件，负责存储和管理集群的元数据，确保集群的状态一致性和高可用性 [E1] |

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

- offline_total_ms: 1,905.395
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 54
- total_tokens: 426
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `e4f43d68be42b4ff1109e27ac304be5c30d067b7272db77a61d42cbf8b0f6867`
- answer_sha256: `56c2b44336506be1b0c7dded9f1f07cf0afce3ed6c8343e42363f6d6770d2d81`

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
| 3 | partial | 0.2038 | E1 | 例如，如果 AZ-1 发生故障，AZ-2 和 AZ-3 上的副本不受影响，服务可以自动切换到健康的副本，确保业务连续性 [E1] |
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

- offline_total_ms: 1,111.197
- model_call_count: 1
- prompt_tokens: 381
- completion_tokens: 52
- total_tokens: 433
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `eba9aea6984ae739c4bdee88920797f23817f5241d379adcc0c5e737efdd6721`
- answer_sha256: `a4036f9de2ab97581ac96e5db274dc9047ec6dae8038b9d9e0e8517b54846223`

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
| E1 | internal/10_模型服务层vLLM架构.md | internal/10_模型服务层vLLM架构.md@0-773#e9b11b984010 | 0.7106 |
| E4 | external/34-vllm_architecture_cn.md | external/34-vllm_architecture_cn.md@5634-6214#2c8ba4fa9cdf | 0.6013 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1689 | E1 | KV cache 成为大模型推理的关键优化点，主要是因为它显著降低了计算复杂度 |
| 2 | supported | 0.2431 | E1 | 在没有 KV cache 的情况下，每生成一个新 token 都需要对所有历史 token 进行 attention 计算，复杂度为 O(n²) |
| 3 | supported | 0.2493 | E1 | 而使用 KV cache 后，可以缓存历史 token 的 Key 和 Value 矩阵，每次只需计算新 token，复杂度降低为 O(n) [E1] |
| 4 | partial | 0.1825 | E1 | 此外，传统的 KV cache 存在内存管理低效的问题，导致内存利用率低于 40% |
| 5 | partial | 0.1886 | E1 | vLLM 通过改进的 KV cache 管理策略，能够更有效地利用内存，提升推理性能 [E1][E4] |

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

- offline_total_ms: 2,128.816
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 54
- total_tokens: 431
- estimated_cost_usd: 0.000089

### 追溯信息

- source_cer_sha256: `c05cbc499f56d221bfddde6e6893d4227bd0a78ec144cf153a6825a82aacc84d`
- answer_sha256: `10f106379895a3408a321962e33138be30f52e65fc9f2f5219058cdce08d754e`
