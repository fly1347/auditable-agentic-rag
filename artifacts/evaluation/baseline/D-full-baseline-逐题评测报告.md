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
- reason: 问题明确询问 RAG 流程的主要步骤，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 1
- resolved_citation_count: 1
- unresolved_citation_count: 0
- claim_count: 12
- unsupported_claim_count: 4

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/01_RAG基础原理.md | internal/01_RAG基础原理.md@0-871#dfa7ac57160a | 0.0325 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1866 | E1 | RAG（检索增强生成）的完整流程主要分为两个阶段：**离线索引阶段**和**在线检索-生成阶段** |
| 2 | unsupported | 0.0345 | E1 | **离线索引阶段**： - 文档加载：支持多种格式，提取纯文本 |
| 3 | partial | 0.1518 | E1 | - 文本分块：将文档切分为较小的文本块（chunk） |
| 4 | partial | 0.1631 | E1 | - Embedding 计算：将文本映射到高维向量空间 |
| 5 | unsupported | 0.0188 | E1 | - 向量存储：将向量写入向量数据库，建立索引 |
| 6 | partial | 0.1564 | E1 | **在线检索-生成阶段**： - 用户 Query：用户输入查询 |
| 7 | partial | 0.1634 | E1 | - Query Embedding：将查询进行向量化 |
| 8 | unsupported | 0.0235 | E1 | - 向量相似度检索：从数据库中检索最相关的文本块 |
| 9 | partial | 0.1470 | E1 | - 构建 Prompt：将查询和检索到的文本块结合 |
| 10 | partial | 0.1487 | E1 | - LLM 生成回答：使用大语言模型生成最终答案 |
| 11 | unsupported | 0.0124 | E1 | - 返回结果：将结果返回给用户，并包含来源引用 |
| 12 | partial | 0.1409 | E1 | 以上步骤构成了 RAG 的标准工作流程 [E1] |

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

- offline_total_ms: 3,103.046
- model_call_count: 1
- prompt_tokens: 373
- completion_tokens: 52
- total_tokens: 425
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `8dbfe44ae573f05c255a74b23dffa6707e818168fb0917197a4e72f177f52f11`
- answer_sha256: `894355ca977caf421c6f22509d122473583afd8a4b5161ce322836bd53525bc1`

## q02 — OpenAI GPT-6 的内部架构是什么？

### 分类与回答边界

- actual_route: DIRECT
- question_type: NARROW_FACT
- answerability: OOD_CANDIDATE
- route_candidate: REJECT_CANDIDATE
- confidence: high
- reason: 该信息属于未公开的内部细节，无法验证

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

- offline_total_ms: 1,531.134
- model_call_count: 1
- prompt_tokens: 374
- completion_tokens: 50
- total_tokens: 424
- estimated_cost_usd: 0.000086

### 追溯信息

- source_cer_sha256: `8b018c8a5b60554954499c90d84b88e5a5a69684607fe17a4cf70c1b7cb6315c`
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
| E2 | internal/02_Chunk策略.md | internal/02_Chunk策略.md@0-685#1411d3bdb16d | 0.0482 |
| E1 | external/12-检索增强生成 (RAG) 技术综述-syhya.md | external/12-检索增强生成 (RAG) 技术综述-syhya.md@1237-1865#09b01ab21d25 | 0.0484 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1943 | E2 | 固定长度分块和语义分块的主要区别在于分块的依据和效果： 1. **固定长度分块**是根据固定的字符数或token数进行切分，简单易实现，但可能在语义上切断句子或段落，导致检索精度较差 [E2] |
| 2 | unsupported | 0.0359 | E2 | **语义分块**则是利用自然语言处理技术，根据文本的语义边界进行切分，能够保留语义完整性，减少歧义，适用于需要高语义一致性的场景 [E1][E2] |

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

- offline_total_ms: 1,374.558
- model_call_count: 1
- prompt_tokens: 374
- completion_tokens: 49
- total_tokens: 423
- estimated_cost_usd: 0.000086

### 追溯信息

- source_cer_sha256: `8f5136998a06647b48dc986f74c559ec0299d9777523754ae2112e7a7292e724`
- answer_sha256: `e45907d6576164b3ff9b498fe1fcc85ea4c81bb5154607d67db2064e5bd32699`

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
| 4 | unsupported | 0.0808 | E4 | 在嵌入过程中，信息损失不可避免，长文本块的语义点过多，导致单一向量的表示变得笼统，关键细节被模糊化，从而降低检索精度 [E1][E4] |

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

- offline_total_ms: 1,455.942
- model_call_count: 1
- prompt_tokens: 373
- completion_tokens: 45
- total_tokens: 418
- estimated_cost_usd: 0.000083

### 追溯信息

- source_cer_sha256: `7c19bf6fca3b9ed5c77dd035969be27defe41dc014edb19924a21e8c10ce854a`
- answer_sha256: `06b04017f744e360b97a6be6f48dd1c534191cf3b8fa6e565ae7635361f9949a`

## q05 — 为什么 embedding 相似度常用余弦相似度？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: IN_SCOPE
- route_candidate: OPEN_MULTI
- confidence: high
- reason: 问题明确，涉及 embedding 相似度的常用方法，且可以提供清晰的解释。

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
| E1 | internal/03_Embedding原理与向量空间.md | internal/03_Embedding原理与向量空间.md@685-1106#3f0be53594bb | 0.0328 |
| E2 | external/16-vector-embedding-datawhale.md | external/16-vector-embedding-datawhale.md@398-804#13940eb805c6 | 0.0320 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | unsupported | 0.0652 | E1 | 余弦相似度常用的原因包括： 1. **归一化处理**：余弦相似度消除了向量长度的影响，专注于向量的方向，这对于文本长度不一的情况尤为重要 |
| 2 | unsupported | 0.0579 | E1 | **值域直观**：其值域为[-1, 1]，便于理解，1表示完全相同方向，0表示正交，-1表示完全相反 |
| 3 | unsupported | 0.0498 | E1 | **适用性**：余弦相似度适合高维稀疏或密集的语义向量，能够有效反映语义相似性 [E1][E2] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: SUMMARY 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=unsupported；unsupported_claim_count=3；unsupported_claim
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,246.133
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 53
- total_tokens: 430
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `a30aa1fbc4d13024f568f10098711b308136f2663d274c428b0b93115dd79d88`
- answer_sha256: `26abdb709e92067a1cafe5439b39f0609348b16a2081d9488c8165591d3cdc6c`

## q06 — 在 RAG 系统中，什么情况下容易产生 hallucination？

### 分类与回答边界

- actual_route: DIRECT
- question_type: NARROW_FACT
- answerability: IN_SCOPE
- route_candidate: DIRECT
- confidence: high
- reason: 问题明确询问 RAG 系统中 hallucination 产生的情况，且没有不可验证的风险。

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

- offline_total_ms: 3,133.656
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 59
- total_tokens: 436
- estimated_cost_usd: 0.000092

### 追溯信息

- source_cer_sha256: `7fb75f1cdea957e707179cec0bc52ad4feaa9532db5929f306308c50e2ad0109`
- answer_sha256: `91d81c9415ce419f7d7fd0fb5e1e7becdd8718b873f9335c2cfacdafcdf8a766`

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
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 5
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
| 1 | partial | 0.2100 | E1 | Multi-AZ 部署通过以下方式降低系统单点故障风险： 1. **故障隔离**：每个可用区（AZ）是独立的故障域，若一个 AZ 发生故障，其他 AZ 的副本不受影响，服务可以自动切换到健康的副本，从而保持系统的可用性 [E1] |
| 2 | partial | 0.1952 | E1 | **同步复制**：数据库在写入时会同步复制到多个 AZ 的副本，确保在故障切换时数据不会丢失，恢复点目标（RPO）接近于零 [E1] |
| 3 | partial | 0.1935 | E1 | **负载均衡**：负载均衡器将请求分发到多个 AZ 中的健康实例，确保在单个 AZ 故障时流量能够自动切换，用户体验不受影响 [E1] |
| 4 | partial | 0.1993 | E2 | **Pod 反亲和性和均匀分布**：通过强制 Pods 跨 AZ 分布，确保任一 AZ 故障只影响该 AZ 的 Pods，避免单点故障 [E2] |
| 5 | unsupported | 0.0073 | E2 | 这些机制共同作用，显著提高了系统的高可用性和容错能力 |

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

- offline_total_ms: 2,951.114
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 57
- total_tokens: 434
- estimated_cost_usd: 0.000091

### 追溯信息

- source_cer_sha256: `44fb97666804ef2560ff5684f3273e6ea45b3073769d82c906ea89b14756b428`
- answer_sha256: `6540772a309e783bfaa7bdecb443f1f580368c53b4a1c2b1241df918a9eb909b`

## q08 — HNSW 和 IVF 向量索引有什么主要区别？

### 分类与回答边界

- actual_route: DECOMPOSE
- question_type: EXPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: high
- reason: 问题明确要求比较 HNSW 和 IVF 两种向量索引的主要区别，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 3
- resolved_citation_count: 3
- unresolved_citation_count: 0
- claim_count: 8
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
| 1 | supported | 0.2838 | E3 | HNSW 和 IVF 向量索引的主要区别在于它们的结构和工作原理： 1. **数据结构**： - HNSW 使用基于图的结构，通过构建多层邻近图来进行搜索，适合高维数据和低延迟查询 [E3] |
| 2 | supported | 0.2275 | E3 | - IVF 则通过聚类将向量空间划分为多个“桶”，查询时只在最相似的几个桶内进行精确搜索 [E3][E5] |
| 3 | partial | 0.1952 | E3 | **检索速度与精度**： - HNSW 提供极快的检索速度和较高的召回率，但内存占用较大 [E3] |
| 4 | supported | 0.2258 | E3 | - IVF 通过缩小搜索范围来提升检索速度，适合大规模数据集，但召回率不是100% [E3][E5] |
| 5 | partial | 0.1892 | E3 | **内存占用**： - HNSW 通常占用更多内存，因为其图结构需要更多的空间 [E4] |
| 6 | partial | 0.1971 | E4 | - IVF 及其变体（如 IVFPQ）在内存使用上更为高效 [E4] |
| 7 | supported | 0.2322 | E3 | **构建速度**： - IVF 的构建速度通常比 HNSW 快 [E5] |
| 8 | supported | 0.2605 | E3 | 综上所述，HNSW 更适合对查询延迟有严格要求的场景，而 IVF 则在处理大规模数据时表现更佳 |

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

- offline_total_ms: 2,402.941
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 58
- total_tokens: 435
- estimated_cost_usd: 0.000091

### 追溯信息

- source_cer_sha256: `149119e51a169c40c1ee93ff44f41d5235c23ff1f520360a963cb90ddf1ec7e9`
- answer_sha256: `a6ad73781c6ff593fe9c47235323c784986a7107af80b7e0433a34a245ac283a`

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

- offline_total_ms: 3,171.159
- model_call_count: 1
- prompt_tokens: 373
- completion_tokens: 53
- total_tokens: 426
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `e4d67e1c156472d03259871b5462d39e84d48952cfc69d6df13afec7de5802c8`
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
| 1 | supported | 0.2471 | E1 | KV Cache 在大模型推理中的作用主要是缓存历史 token 的 Key 和 Value 矩阵，从而避免重复计算，显著降低计算复杂度 |
| 2 | partial | 0.2030 | E1 | 具体来说，使用 KV Cache 可以将每步生成新 token 的复杂度从 O(n²) 降低到 O(n)，提高推理效率 [E1] |
| 3 | partial | 0.1774 | E1 | 此外，KV Cache 还面临传统内存管理低效的问题，如内存碎片和利用率低等 |
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

- offline_total_ms: 2,310.814
- model_call_count: 1
- prompt_tokens: 374
- completion_tokens: 55
- total_tokens: 429
- estimated_cost_usd: 0.000089

### 追溯信息

- source_cer_sha256: `35347ce1977fa139bf0a30cdbe59e75d4b87f0371fa1609b2c96be1c2d7266b6`
- answer_sha256: `e4998b1a0927d5e7988b78c240ac2ce1e048d65bd1f5f142b961bd4230d94460`

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
- claim_count: 4
- unsupported_claim_count: 1

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/02_Chunk策略.md | internal/02_Chunk策略.md@685-1391#5484310af4bf | 0.0320 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1966 | E1 | Overlap 在文本分块中的作用主要是防止关键信息在分块边界被切断，从而保留上下文的连贯性，提升边界附近的检索召回率 |
| 2 | supported | 0.2541 | E1 | 具体来说，Overlap 是指相邻 chunk 之间共享一定数量的 token，例如，设置 chunk_size 为 400，重叠为 50，则前一个 chunk 的最后 50 个 token 会与下一个 chunk 重叠 |
| 3 | unsupported | 0.0306 | E1 | 这种策略有助于确保信息的完整性和上下文的连贯性，但也会增加存储量，并可能导致检索时的冗余信息干扰生成 |
| 4 | partial | 0.1981 | E1 | 通常，Overlap 的大小建议为 chunk_size 的 10%~20% [E1] |

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

- offline_total_ms: 2,955.248
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 51
- total_tokens: 423
- estimated_cost_usd: 0.000086

### 追溯信息

- source_cer_sha256: `0765467ac5aac63231f06729ac138e5b43822b6d939f8c66fa45e84fb5f3f3a3`
- answer_sha256: `5f4254270075ccde9bea6e545221564e61f9ab3f23283aa5f6ac6e4f30895f82`

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

- offline_total_ms: 1,712.807
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 45
- total_tokens: 417
- estimated_cost_usd: 0.000083

### 追溯信息

- source_cer_sha256: `7213808b0f635710986fa0b0338bfba3be882f6fcd4df3d6e7272343936c36e3`
- answer_sha256: `6bf597c1ce3f3118a6ba5374c2060c4e141f7324c83a6f0c215954e6a913f3e2`

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
| E1 | internal/03_Embedding原理与向量空间.md | internal/03_Embedding原理与向量空间.md@1106-1746#7cc4b717d45c | 0.0328 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1932 | E1 | Embedding 模型并不真正“理解”语义，而是捕捉语义的统计规律 |
| 2 | unsupported | 0.0852 | E1 | 它通过大量文本训练，将经常出现在相似上下文中的文本映射到相近的向量位置，能够处理语义相似性，但对逻辑推理和因果关系等高阶理解能力有限 |
| 3 | partial | 0.1916 | E1 | 此外，Embedding 对否定词和精确数字的敏感性较差，这表明其在某些情况下可能无法准确反映语义的真实含义 [E1] |

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

- offline_total_ms: 1,289.913
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 59
- total_tokens: 431
- estimated_cost_usd: 0.000091

### 追溯信息

- source_cer_sha256: `601eaa152c7165cfbe6b6f7bd2ac2f39046af6bdfd72da59f5d3fdf87f7bd788`
- answer_sha256: `c90d36d2ec6e176113f9b08012f7d8e3a55c0de161039434744a2dda4ab21ae3`

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

- offline_total_ms: 2,444.824
- model_call_count: 1
- prompt_tokens: 374
- completion_tokens: 58
- total_tokens: 432
- estimated_cost_usd: 0.000091

### 追溯信息

- source_cer_sha256: `69aa34c6c0c06d9e81e42353fb62177493a8a6ca064a88d667048444ed89631d`
- answer_sha256: `5c0533ef861f2f422e7f248e605c6e95717d2775a7b4e67cc2ce0bd1a8b692ca`

## q15 — 检索错但回答对，在 RAG 评估里算成功吗？

### 分类与回答边界

- actual_route: DIRECT
- question_type: SUMMARY
- answerability: NEEDS_CLARIFICATION
- route_candidate: NEEDS_CLARIFICATION
- confidence: medium
- reason: 问题缺少对成功标准的具体定义和评估范围

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
| E2 | internal/04_RAG失败模式.md | internal/04_RAG失败模式.md@1332-1937#311a87398ac2 | 0.0325 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1671 | E2 | 检索错但回答对在 RAG 评估中不算成功 |
| 2 | partial | 0.1982 | E2 | 尽管最终回答可能正确，但这通常是由于 LLM 的参数记忆（即幻觉的一种形式），而不是基于可追溯的检索证据 |
| 3 | supported | 0.2756 | E2 | 因此，这种情况应标记为“Retrieval Failed, Answer Lucky”，不计入正确答案 [E2] |

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

- offline_total_ms: 1,174.563
- model_call_count: 1
- prompt_tokens: 380
- completion_tokens: 48
- total_tokens: 428
- estimated_cost_usd: 0.000086

### 追溯信息

- source_cer_sha256: `126230623d9b4f484dbc47696af249789615bcf07f8542c803890c37f01a72e3`
- answer_sha256: `f2d2346765f88e2f5aa5ebc35bc4ac916a1276a8103327b2d439a85dd37af63d`

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
| 1 | supported | 0.3014 | E1 | pgvector 和专用向量数据库（如 Qdrant 和 Milvus）之间的主要差异包括： 1. **架构**：pgvector 是 PostgreSQL 的扩展，而专用向量数据库是独立的系统 |
| 2 | partial | 0.2182 | E1 | **集成成本**：pgvector 的集成成本较低，因为可以复用现有的 PostgreSQL 栈 |
| 3 | unsupported | 0.0224 | E1 | 而专用向量数据库需要独立部署和维护 |
| 4 | supported | 0.2838 | E1 | **查询吞吐量**：pgvector 的查询吞吐量中等（约百级 QPS），而专用向量数据库如 Qdrant 可以达到高于 4000 RPS |
| 5 | partial | 0.2048 | E1 | **过滤检索**：pgvector 需要额外调优以支持过滤检索，而专用向量数据库原生支持此功能，性能更佳 |
| 6 | supported | 0.2227 | E1 | **事务支持**：pgvector 完整支持 ACID 事务，而专用向量数据库的事务支持有限或不支持 |
| 7 | partial | 0.1953 | E1 | **量化压缩**：pgvector 的量化压缩能力有限，而专用向量数据库支持多种量化方法 |
| 8 | partial | 0.1987 | E1 | **适用规模**：pgvector 适用于小于 1000 万向量的场景，而专用向量数据库可以处理亿级向量 |
| 9 | partial | 0.1899 | E1 | **运维复杂度**：pgvector 的运维复杂度较低，因为与业务数据同库 |
| 10 | unsupported | 0.0281 | E1 | 专用向量数据库的运维复杂度中等到高，因为是独立组件 |
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

- offline_total_ms: 1,287.017
- model_call_count: 1
- prompt_tokens: 378
- completion_tokens: 52
- total_tokens: 430
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `511938c661e22e4681de3ce8c5d7233d3c3409525f2ed77a3a91b474899ad2c0`
- answer_sha256: `89a91b481266fefee6608985c3096d359cb001407511ced5f641835f668c4bc8`

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
| E1 | internal/06_Qdrant架构.md | internal/06_Qdrant架构.md@965-1773#50531ea08667 | 0.0328 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.2157 | E1 | Qdrant 的内存存储和磁盘存储主要有以下差异： 1. **存储模式**： - **内存存储（In-Memory）**：向量完全加载到 RAM 中，提供最快的性能，但内存成本较高 |
| 2 | partial | 0.1974 | E1 | - **磁盘存储**： - **Mmap（Memory-mapped）**：向量存储在磁盘上，由操作系统进行缓存管理，性能中等，成本相对友好 |
| 3 | partial | 0.1907 | E1 | - **On-disk（量化+磁盘）**：量化向量存储在磁盘上，原始向量用于重新排序，性能较慢，但成本最低 |
| 4 | unsupported | 0.0177 | E1 | **性能与成本**： - 内存存储提供最佳性能，但成本高 |
| 5 | unsupported | 0.0173 | E1 | 而磁盘存储则在性能和成本之间提供不同的平衡选择，适合不同的使用场景 [E1] |

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

- offline_total_ms: 1,203.059
- model_call_count: 1
- prompt_tokens: 380
- completion_tokens: 57
- total_tokens: 437
- estimated_cost_usd: 0.000091

### 追溯信息

- source_cer_sha256: `4ff4461e11b87b442c29d956eb83eebd9a5e740d2aa2a61470296a714083fb7b`
- answer_sha256: `9f0078d8cc0d8dcb72358e6df70d7b91c75146ccbd9c0011af440c7fcb81c353`

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
- unsupported_claim_count: 1

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/07_向量索引算法HNSW与IVF.md | internal/07_向量索引算法HNSW与IVF.md@1558-2289#f09b34881aa0 | 0.0320 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1917 | E1 | 在向量检索中，Recall（召回率）和Latency（延迟）之间的权衡主要体现在查询性能与检索精度的平衡上 |
| 2 | supported | 0.2320 | E1 | 具体来说： 1. **高召回率通常伴随高延迟**：在使用HNSW或IVF算法时，增加ef_search或nprobe的值可以提高召回率，但这也会导致查询的延迟增加 |
| 3 | unsupported | 0.0268 | E1 | 例如，从90%召回率提升到99%可能需要2到5倍的查询时间代价 [E1] |
| 4 | supported | 0.2588 | E1 | **实际应用中的平衡**：在实际部署中，系统需要通过调整ef_search或nprobe的参数来找到适合业务需求的Recall和Latency之间的平衡点，以满足不同场景下的性能要求 [E1] |
| 5 | partial | 0.1841 | E1 | 因此，Recall和Latency的权衡是向量检索系统设计中的一个重要考量，影响着系统的响应速度和检索效果 |

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

- offline_total_ms: 2,516.072
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 53
- total_tokens: 430
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `6b89f838d541dffb4f068f427dc18405fd903e8bab76f087a9d4104c5bb19d5a`
- answer_sha256: `81804a2e303740731a34387f51b6767994a6df88564a46a8a837c9fc8a848644`

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
| E4 | internal/08_Kubernetes基础架构.md | internal/08_Kubernetes基础架构.md@1115-1993#1114731f27b6 | 0.0161 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1366 | E4 | kube-scheduler 在 Kubernetes 集群中负责将新建的 Pod 分配到合适的 Node |
| 2 | partial | 0.2143 | E4 | 它的调度决策依据包括资源请求/限制、节点亲和性、Pod 反亲和性以及 Taints/Tolerations |
| 3 | supported | 0.2720 | E4 | 具体流程为：新 Pod 创建后，API Server 将其写入 etcd，kube-scheduler 监听并选择最优 Node，然后将 Pod 绑定到该 Node，最后目标 Node 的 kubelet 启动容器 [E4] |

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

- offline_total_ms: 2,887.517
- model_call_count: 1
- prompt_tokens: 375
- completion_tokens: 51
- total_tokens: 426
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `3b25be7a0934e02e083782421adde7f699be1c557a59a2e1e042347da288be11`
- answer_sha256: `582518a2fe33a447b0253c9744f5512aec22bba1dd51abae3b11809932803864`

## q20 — 连续批处理（Continuous Batching）和传统静态批处理有什么区别？

### 分类与回答边界

- actual_route: DECOMPOSE
- question_type: EXPLICIT_COMPARE
- answerability: IN_SCOPE
- route_candidate: DECOMPOSE
- confidence: high
- reason: 问题明确要求比较两个批处理方式，且信息可验证。

### 证据充分性

- raw_verdict: SUFFICIENT
- control_verdict: SUFFICIENT

### 引用证据支撑（规则）

- citation_support_label: partial
- citation_count: 2
- resolved_citation_count: 2
- unresolved_citation_count: 0
- claim_count: 8
- unsupported_claim_count: 4

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/10_模型服务层vLLM架构.md | internal/10_模型服务层vLLM架构.md@773-1705#c76695ac0bf6 | 0.0492 |
| E2 | internal/10_模型服务层vLLM架构.md | internal/10_模型服务层vLLM架构.md@0-773#e9b11b984010 | 0.0474 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1852 | E1 | 连续批处理（Continuous Batching）与传统静态批处理的主要区别在于请求处理的方式和效率 |
| 2 | unsupported | 0.0467 | E1 | **请求处理方式**： - **传统静态批处理**：所有请求同时开始，必须等到最长的请求完成后才能接受新请求 |
| 3 | partial | 0.1498 | E2 | 这导致短请求完成后GPU空闲，利用率低 [E1] |
| 4 | unsupported | 0.0346 | E1 | - **连续批处理**：在处理请求时，一旦某个请求完成，可以立即插入新的请求，而无需等待其他请求完成 |
| 5 | partial | 0.1428 | E1 | 这使得GPU始终保持满载，提高了吞吐量 [E1] |
| 6 | partial | 0.1595 | E2 | **效率**： - 传统静态批处理的GPU利用率较低，导致吞吐量不足 |
| 7 | unsupported | 0.0232 | E1 | - 连续批处理显著提升了吞吐量，相比传统方法，吞吐量提升可达14到24倍 [E2] |
| 8 | unsupported | 0.0150 | E1 | 因此，连续批处理在处理效率和资源利用上优于传统静态批处理 |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: EXPLICIT_COMPARE 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=4；unsupported_claim；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,066.657
- model_call_count: 1
- prompt_tokens: 380
- completion_tokens: 48
- total_tokens: 428
- estimated_cost_usd: 0.000086

### 追溯信息

- source_cer_sha256: `1c574c1303622ca473f5bf21ac18c1ff345e494de956386a323d0f1fc11db53f`
- answer_sha256: `d9c4ec6a84cfbb1fff09f0d9d800dcd10429dcc7ee8c6866ca60e383eb7808c1`

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

- citation_support_label: no_evidence
- citation_count: 0
- resolved_citation_count: 0
- unresolved_citation_count: 0
- claim_count: 6
- unsupported_claim_count: 6

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | no_evidence | 0.0000 | not_observed | 在RAG（检索增强生成）中，embedding和retrieval之间的关系是密切相关的 |
| 2 | no_evidence | 0.0000 | not_observed | 具体来说，embedding在RAG流程中主要用于将文档和用户查询转换为向量，以便进行语义检索 |
| 3 | no_evidence | 0.0000 | not_observed | 其流程如下： 1. **离线索引构建**：在索引阶段，文档被切分并通过embedding模型转换为向量，存入向量数据库中 |
| 4 | no_evidence | 0.0000 | not_observed | **在线查询检索**：当用户提出问题时，使用同样的embedding模型将用户的问题转换为向量 |
| 5 | no_evidence | 0.0000 | not_observed | **相似度计算**：在向量数据库中，计算用户问题向量与文档块向量的相似度，以检索相关文档 |
| 6 | no_evidence | 0.0000 | not_observed | 因此，embedding的质量直接影响retrieval的效果，优秀的embedding模型能够更准确地捕捉问题与文档之间的语义关系，从而提高检索的准确性和相关性【E1】【E4】 |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: IMPLICIT_COMPARE 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=no_evidence；unsupported_claim_count=6；no_evidence
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,422.970
- model_call_count: 1
- prompt_tokens: 375
- completion_tokens: 47
- total_tokens: 422
- estimated_cost_usd: 0.000084

### 追溯信息

- source_cer_sha256: `cc25f0886b322b9424329d04cdfb945fe0e13a887437d4754c61ee8f7a98857a`
- answer_sha256: `a5e1a01d000638612e699f8f409cd052881b5057492092a581921a201192a66a`

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
| E2 | internal/02_Chunk策略.md | internal/02_Chunk策略.md@1391-1768#5c5d7a6818b5 | 0.0313 |
| E3 | external/14-text-chunking-datawhale.md | external/14-text-chunking-datawhale.md@597-1194#e880edf6d91e | 0.0306 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.2238 | E2 | Chunk 不是越大越好的原因主要有以下几点： 1. **检索精度下降**：过大的 chunk 会导致相关内容被噪声稀释，从而降低检索的精度 [E2] |
| 2 | partial | 0.2091 | E2 | **上下文不完整**：如果 chunk 过小，可能会导致上下文信息丢失，影响理解 [E2] |
| 3 | partial | 0.1900 | E2 | **信息损失**：在嵌入过程中，较大的 chunk 会导致信息稀释，关键细节可能被模糊化，降低语义表示的质量 [E3] |
| 4 | supported | 0.3149 | E2 | **占用更多资源**：过大的 chunk 会占用更多的 LLM context 窗口，限制可用的上下文信息 [E2] |
| 5 | supported | 0.2619 | E2 | 因此，合理的 chunk 大小应在128到512 tokens之间，根据任务类型进行调整 [E2] |

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

- offline_total_ms: 2,572.405
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 50
- total_tokens: 422
- estimated_cost_usd: 0.000086

### 追溯信息

- source_cer_sha256: `172beb1dd17de723913a06a694b35bdd61a844e63083530f93e841661daad025`
- answer_sha256: `36ee8b6d9e24d64d4156ae50f01b41426a627761f4a20faaf3c7bd60da618380`

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
| E5 | internal/02_Chunk策略.md | internal/02_Chunk策略.md@0-685#1411d3bdb16d | 0.0315 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | unsupported | 0.0321 | E5 | 语义分块相比固定分块的主要优势在于它能够保留语义完整性，确保每个分块的内容自洽，减少歧义 |
| 2 | unsupported | 0.0330 | E5 | 这是因为语义分块是根据文本的语义边界进行切分，而固定分块则可能在语义中间切断，导致信息的丢失和检索精度的降低 |
| 3 | unsupported | 0.0243 | E5 | 此外，语义分块能够更好地适应不同类型的文本，尤其适用于学术文档和法律合同等需要高语义一致性的场景 [E1][E5] |

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

- offline_total_ms: 1,596.158
- model_call_count: 1
- prompt_tokens: 376
- completion_tokens: 56
- total_tokens: 432
- estimated_cost_usd: 0.000090

### 追溯信息

- source_cer_sha256: `8f9944c2b717677768da4008c51d78390fa33637c10e0e57185c5f62717e1aa3`
- answer_sha256: `a94305d0356f6a3f97e7cb91d06feb1c44ef453690ace1fa8a83a743cfa72cf4`

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

- offline_total_ms: 2,649.676
- model_call_count: 1
- prompt_tokens: 375
- completion_tokens: 53
- total_tokens: 428
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `3a4b021c01af14f9ceb10510bba73c0ab856bea639022903265bb615989de0fc`
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
| E1 | internal/04_RAG失败模式.md | internal/04_RAG失败模式.md@0-639#222aea480737 | 0.0328 |
| E5 | internal/01_RAG基础原理.md | internal/01_RAG基础原理.md@871-1622#b2cf54881a08 | 0.0161 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1603 | E1 | 在 RAG 系统中，检索阶段的错误会对最终回答产生显著影响 |
| 2 | partial | 0.2185 | E1 | 具体来说，检索失败可以分为两种情况： 1. **召回不准（低精度）**：如果检索到的文档片段与用户问题不相关，LLM 将获得噪声上下文，从而生成错误或无意义的回答 [E1] |
| 3 | unsupported | 0.0550 | E1 | **召回遗漏（低召回）**：当相关文档未被检索到时，系统可能会面临证据不足的情况，理应拒绝回答，但可能会产生幻觉作答 [E1] |
| 4 | unsupported | 0.0183 | E5 | 因此，检索阶段的准确性直接影响生成阶段的质量，检索错误无法通过生成阶段弥补 [E5] |

### 冲突检测（规则型疑似冲突）

- triggered: true
- conflict_count: 0
- trigger_reason: SUMMARY 多来源问题，触发规则冲突扫描

### 综合不确定性（派生信号）

- level: high
- level_meaning: 不确定性/风险高
- reasons: citation_weak
- missing_info: citation_support_label=partial；unsupported_claim_count=2；unsupported_claim；partial_support
- safe_answer_boundary: 部分回答内容未被实际引用证据充分支撑，应作为待核验内容处理。

### D-full 后置评测耗时与用量

- offline_total_ms: 1,242.931
- model_call_count: 1
- prompt_tokens: 380
- completion_tokens: 50
- total_tokens: 430
- estimated_cost_usd: 0.000087

### 追溯信息

- source_cer_sha256: `c5a3c55c0c11b424b8cd59b1e181b82e4a8e5d6068ef512651808859cd4d304a`
- answer_sha256: `59de0a4da5e1d1b4f96f6f6615a62711bc4475e9695a52349920da33fa6c8b16`

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
- citation_count: 5
- resolved_citation_count: 5
- unresolved_citation_count: 0
- claim_count: 8
- unsupported_claim_count: 0

#### 最终实际 Citations

| evidence_id | source_id | chunk_id | retrieval_score |
| :-- | :-- | :-- | --: |
| E1 | internal/05_pgvector原理.md | internal/05_pgvector原理.md@682-1303#b9f400273076 | 0.0469 |
| E3 | internal/07_向量索引算法HNSW与IVF.md | internal/07_向量索引算法HNSW与IVF.md@849-1558#5387fc2754ce | 0.0323 |
| E5 | internal/07_向量索引算法HNSW与IVF.md | internal/07_向量索引算法HNSW与IVF.md@301-849#cca57ff7d9dd | 0.0164 |
| E2 | external/26-Milvus-索引解释.md | external/26-Milvus-索引解释.md@3003-3627#3603b200df69 | 0.0323 |
| E4 | external/22-milvus-datawhale.md | external/22-milvus-datawhale.md@4526-5014#fc79b169f6c2 | 0.0315 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.2517 | E4 | IVF（倒排文件索引）和HNSW（分层可导航小世界图）在以下几个方面有显著区别： 1. **构建方式**： - IVF需要先进行聚类，生成质心后才能建立索引，构建速度较快，但不支持增量插入 [E1][E3] |
| 2 | partial | 0.1832 | E4 | - HNSW支持边插入边索引，允许动态更新，构建时间较长 [E1][E5] |
| 3 | partial | 0.1827 | E3 | **内存占用**： - IVF及其变体（如IVFFlat）通常占用较少内存，适合大规模数据集 [E2][E4] |
| 4 | partial | 0.1793 | E4 | - HNSW由于其图结构，内存占用较高 [E2][E4] |
| 5 | partial | 0.1808 | E3 | **查询性能**： - IVF的查询速度受`nprobe`参数影响，较高的`nprobe`会增加延迟 [E3][E4] |
| 6 | partial | 0.2089 | E5 | - HNSW在高召回率下具有较低的查询延迟，查询复杂度为O(log n) [E5] |
| 7 | supported | 0.2222 | E4 | **适用场景**： - IVF适合通用场景，尤其是需要高吞吐量的大规模数据集 [E4] |
| 8 | partial | 0.2155 | E4 | - HNSW更适合对查询延迟有严格要求的场景，如实时推荐和在线搜索 [E4] |

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

- offline_total_ms: 1,673.321
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 53
- total_tokens: 430
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `79c304e16c2b1d187c431a4e4b472a2495550bef36d1e38e3b86c4bddb9d549e`
- answer_sha256: `6fca7df7ab07bcb8dbe5c9e85a0de44ef7c0a39a94547addad78eb4465323f42`

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
| E5 | internal/07_向量索引算法HNSW与IVF.md | internal/07_向量索引算法HNSW与IVF.md@301-849#cca57ff7d9dd | 0.0294 |
| E4 | internal/06_Qdrant架构.md | internal/06_Qdrant架构.md@464-965#34d2c3600e13 | 0.0299 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | supported | 0.3199 | E4 | HNSW（Hierarchical Navigable Small World）通常具有更高的检索精度，主要是因为其采用了分层图结构，能够在多个层次上进行搜索，从而实现更精细的邻近搜索 |
| 2 | partial | 0.1727 | E5 | 具体来说，HNSW通过从顶层开始逐层向下搜索，最终在稠密层中进行精确的最近邻查找，这种方法有效提高了召回率和检索精度 [E5] |
| 3 | partial | 0.1931 | E5 | 此外，HNSW的设计允许通过调整参数（如每个节点的最大连接边数和构建时的候选集大小）来优化索引质量和精度，这使得在保持较高检索速度的同时，能够实现更高的精度 [E4] |

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

- offline_total_ms: 2,565.020
- model_call_count: 1
- prompt_tokens: 378
- completion_tokens: 55
- total_tokens: 433
- estimated_cost_usd: 0.000090

### 追溯信息

- source_cer_sha256: `dbd86e924433da3dbefc8e6207f090e75c4926c1a5c9bc90a7578edd123cdbbe`
- answer_sha256: `8b3a28459d346ede9538048ad002c8ff308a3f283b620c2fe641d85ed19560a2`

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
| E1 | internal/08_Kubernetes基础架构.md | internal/08_Kubernetes基础架构.md@0-1115#f0413c5d9c86 | 0.0328 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1918 | E1 | 在 Kubernetes 中，etcd 的作用是作为一个键值存储（KV存储），用于保存集群的所有配置数据和状态信息 |
| 2 | partial | 0.1672 | E1 | 它是 Kubernetes 控制平面的一个重要组件，负责存储和管理集群的状态数据，以确保集群的高可用性和一致性 [E1] |

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

- offline_total_ms: 2,056.311
- model_call_count: 1
- prompt_tokens: 372
- completion_tokens: 53
- total_tokens: 425
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `3621b0115a4e250ff2ab3e9b65b2e4fd39f4711b381addb46030c23d48642691`
- answer_sha256: `1b2f75de6977774f9903ca0155cda6fb67a44a7bb6edaa4cc83281189e1b669e`

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
| E1 | internal/09_MultiAZ高可用设计.md | internal/09_MultiAZ高可用设计.md@613-1434#0c95c99cfcbb | 0.0328 |

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

- offline_total_ms: 1,986.644
- model_call_count: 1
- prompt_tokens: 381
- completion_tokens: 52
- total_tokens: 433
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `eb042b95155c75c0549300e8a3a9d439afec47baf61a0a6046410a5e03a2ba1b`
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
| E1 | internal/10_模型服务层vLLM架构.md | internal/10_模型服务层vLLM架构.md@0-773#e9b11b984010 | 0.0328 |
| E2 | external/34-vllm_architecture_cn.md | external/34-vllm_architecture_cn.md@4392-4854#e44bd71a8184 | 0.0299 |

#### 引用 claim 明细

> `label` 已直接表达 best_score 对应的支撑等级；`best_evidence_id` 只会从最终实际引用证据中选择。

| # | label（支撑判定） | best_score | best_evidence_id | claim |
| --: | :-- | --: | :-- | :-- |
| 1 | partial | 0.1718 | E1 | KV cache 成为大模型推理的关键优化点，主要是因为它能够显著提高自回归生成过程中的计算效率 |
| 2 | supported | 0.2646 | E1 | 具体来说，KV cache 通过缓存历史 token 的 Key 和 Value 矩阵，避免了在每次生成新 token 时重复计算所有历史 token，从而将复杂度从 O(n²) 降低到 O(n) [E1] |
| 3 | partial | 0.2019 | E1 | 然而，传统的 KV cache 管理存在内存利用率低和碎片严重的问题，导致 GPU 显存的浪费 [E1] |
| 4 | supported | 0.2332 | E1 | vLLM 通过引入 PagedAttention 机制，优化了 KV cache 的内存管理，允许不连续的内存分配，从而提高了内存利用率并减少了碎片 [E2] |
| 5 | partial | 0.1689 | E1 | 因此，KV cache 的高效管理直接影响到推理性能，是大模型推理中的关键优化点 |

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

- offline_total_ms: 1,146.598
- model_call_count: 1
- prompt_tokens: 377
- completion_tokens: 53
- total_tokens: 430
- estimated_cost_usd: 0.000088

### 追溯信息

- source_cer_sha256: `ffa4122ee8b8ddb9fc59e6ad3e5340ad4273bc85c98d028e8652325757d86402`
- answer_sha256: `b1e80047778fec63b8ba048b8db58059cfe18f19ed31adc41fbe8894c71e8502`
