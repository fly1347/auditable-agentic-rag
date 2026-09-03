# 系统设计与技术选型

## 1. 文档定位

本文是项目的全局认知入口，回答五个问题：

1. 系统要解决什么问题，明确不解决什么问题；
2. 从语料入库到答案生成，主链由哪些基础能力组成；
3. 每一层为什么采用当前方案；
4. 公开默认配置、冻结评测配置和预留配置分别代表什么；
5. 当前取舍在什么条件下需要重新评估。

[系统架构](architecture.md) 侧重组件关系、控制流和实现位置；本文侧重设计逻辑、有效配置与技术取舍。具体可执行值仍以 `config.example.yaml`、`.env.example` 和对应 Docker 配置为准。

## 2. 项目目标与边界

### 2.1 核心目标

本项目是建立一条可控制、可解释、可评测的 RAG 工程链：

- **本地优先**：语料、Embedding、索引、执行记录和评测产物优先保留在本机；
- **证据优先**：答案必须能回到模型实际看见的证据，而不是只记录检索结果；
- **权限优先**：不可见来源不得进入 TopK、融合、重排、Prompt 或生成链；
- **有界 Agentic**：允许分解、证据判断、改写和一次补检索，但不开放无限循环或任意工具自治；
- **统一事实**：在线回答、审计、评测、成本与报告都从同一份执行记录投影；
- **可比较**：baseline 与 orchestrated 共享底层实现，只比较证据控制策略带来的真实差异。

### 2.2 “本地优先”不等于“完全离线”

公开默认运行链使用本地语料、本地 BGE Embedding 和本地索引；生成模型与充分性 Judge 分别通过 OpenRouter 和 DeepSeek 调用云端服务。数据出境必须通过 egress policy，受限内容默认不允许发送到公开云。

因此，本项目展示的是**本地知识底座 + 受控云端推理**，不是默认完全离线部署。

### 2.3 项目边界

当前定位是企业工程型 Agentic RAG 参考实现与可评估原型，适合本地演示、小规模知识库和回归验证。它不声明生产级多租户隔离、企业 IAM、分布式向量库、HA、SLO、合规审计或域外泛化能力。

## 3. 从目标到设计原则

| 目标 | 设计原则 | 在系统中的落点 |
| :-- | :-- | :-- |
| 多入口行为一致 | 单一应用服务入口 | CLI、API、UI、Eval 共用 `RagApplicationService` |
| 知识边界可控 | 先确定身份和可见范围，再形成 TopK | trusted principal、source ACL、TopK 前过滤、生成前 egress gate |
| 长文档可稳定索引 | 文档结构和实际 Embedding tokenizer 共同约束切分 | structure-first splitter、510 token 硬门禁、coverage/offset 校验 |
| Agentic 行为可预测 | 路由、分解和重试均设置明确边界 | DIRECT / DECOMPOSE、固定子问题数、最多一次 R2 |
| 答案可追溯 | 区分检索、证据、Prompt 和引用集合 | EvidenceSnapshot、PromptSnapshot、`[E#]` 引用合同 |
| 评测不漂移 | 离线评测读取冻结在线事实 | CER-native D-full、RAGAS 和成本总账 |
| 失败方式可解释 | provider、fallback 与 fail-close 显式配置 | egress 检查、judge 失败拒答、公开 fallback 关闭 |

## 4. 端到端设计地图

```text
[Markdown / TXT + Source ACL Registry]
                  │
                  ▼
[Loader] → [Structure-first Splitter] → [510-token Gate]
                  │
                  ▼
[Local BGE Embedding] → [Immutable Local Index]
                  │
                  ▼
[Trusted Principal + Query Safety]
                  │
                  ▼
[DIRECT / DECOMPOSE]
       │
       ▼
[ACL-eligible candidates] → [Dense Top10 + BM25 Top10] → [RRF(k=60) → Top5] → [Optional Rerank] → [ACL Recheck]
       │
       ▼
[EvidenceSnapshot] → [Sufficiency Judge]
       │                     │
       │                     └─ insufficient → rewrite + R2（最多一次）
       ▼
[PromptSnapshot] → [Egress / Budget Policy] → [Generator] → [Citation Contract · E#]
       │
       ▼
[CanonicalExecutionRecord]
       ├─ Response / Debug / Audit / Metrics / Cost
       └─ Offline D-full / RAGAS / Comparison / Report
```

这条链同时包含数据面、控制面和事实面：数据面负责语料与证据，控制面负责权限、路由和失败策略，事实面负责记录系统实际做过什么。

## 5. RAG 底座：配置与选型

### 5.1 语料、权限与加载

| 项目 | 当前设计 | 选择原因 | 代价与边界 |
| :-- | :-- | :-- | :-- |
| 公开语料 | `sample_data/corpus/` 中的 Markdown / TXT | 可读、可审查、适合展示结构化切分 | 不覆盖 PDF、Office、OCR 和复杂解析链 |
| 来源身份 | 相对路径生成稳定 `source_id` | 同一仓库布局下结果确定，便于 ACL、引用和评测关联 | 路径调整会改变 ID；大规模知识运营需要独立内容 ID 与版本系统 |
| 权限登记 | 独立 Source ACL Registry | 内容与策略解耦，来源权限可审计 | 新增 source 必须同步登记 |
| 缺失策略 | deny-by-default，索引阶段 fail-close | 防止未登记内容意外进入可查询知识库 | 配置不完整时宁可停止构建 |

ACL 采用**共享索引中的查询时可见性过滤**，而不是为每个身份复制一套索引。检索时本地向量库会计算相似度，但只有满足 principal 权限谓词的 chunk 才能进入 TopK；融合或重排后还会执行二次校验。未经授权的文本不会进入 RRF、reranker、EvidenceSnapshot、Prompt 或 generator。

这种方案更适合权限经常变化、角色组合较多的小规模共享知识库。若业务要求监管级物理隔离、租户密钥隔离或独立数据生命周期，应改用 tenant/安全域分库，并保留查询时 ACL 作为纵深防御。

首版输入主动限定为 Markdown / TXT，是为了先固定可审查、可复现的文档表示，把工程变量集中在切分、索引、召回、证据控制和执行记录。PDF 会额外引入文本抽取、页眉页脚、多栏版面、表格、OCR 与页码引用质量；在没有独立 Loader 合同、解析质量样例和回归门禁之前接入，会把解析误差混入 retrieval 评测。本轮先完成主链与评测闭环，PDF 作为后续输入扩展保留。

### 5.2 结构化切分

Splitter 是先理解 Markdown 结构，再用实际 Embedding tokenizer 执行硬预算：

1. 按标题树寻找不超过预算的最大完整子树；
2. 超限时递归下降到段落、列表、表格和 fenced block 等原子单元；
3. 原子单元仍超限时，分别按句子、列表项、表格行或代码行拆分；
4. 只有上述结果仍过长时，才使用最终 token window；
5. 相邻单元在不超预算的前提下重新装箱，并校验 coverage、offset 和 determinism。

当前内容预算为 **510 tokens**，与 BGE 的 `max_seq_length=512` 对齐并预留特殊 token 空间。表格、ASCII 图和 fenced block 在当前公开与冻结语料中可以完整保留；只有未来单个结构自身超过预算时才会被分层拆分。

这项选择优先保证“送入 Embedding 的文本与验证预算一致”。代价是实现和测试复杂度高于普通字符切分，并且无法保证任意超长结构永不拆分。

### 5.3 Embedding 与索引

| 项目 | 有效设计 |
| :-- | :-- |
| Embedding | 本地 `BAAI/bge-small-zh-v1.5` |
| 向量维度 | 512 |
| 批大小 | 32 |
| 归一化 | L2 normalize |
| 查询缓存 | 进程内 LRU，默认 1000 项 |
| 索引文件 | `vectors.npy + chunks.jsonl` |
| 更新方式 | 新建不可变 build，校验后原子切换 `current.json` |

选择中文 BGE 小模型，是为了在本地资源、中文语义效果和可复现性之间取得平衡。Embedding 与索引留在本机，也减少了原始语料在入库阶段的外发面。

不可变 build 避免在原索引上原地修改：向量行数、chunk 数量、维度和 manifest 校验全部通过后才切换当前指针；失败时旧 build 仍可使用。代价是构建期间需要额外磁盘空间，当前实现也仍是全量重建。

本地向量库采用内存点积和 O(N) 扫描，便于观察、调试和冻结回归，但不是大规模在线检索方案。

### 5.4 路由、检索与融合

公开在线链只保留两条可回答路线：

| 路线 | 行为 | 设计意图 |
| :-- | :-- | :-- |
| DIRECT | 原问题检索一次 | 控制简单问题的时延与成本 |
| DECOMPOSE | 生成 2 个子问题，并保留原问题；三路分别检索后 RRF | 为复合问题补充不同语义视角，同时保留原始意图 |

路由由确定性规则完成，不调用额外 LLM classifier。子问题生成失败时退回原问题检索，避免把一次规划失败扩散为整次请求失败。

单次 query 的公开默认 retrieval 为 `Dense Top10 + BM25 Top10 → RRF(k=60) → Top5`。Dense 与 BM25 都基于当前不可变索引中的同一批 chunk 和同一 source-level ACL 可见集合；RRF 只使用排名，不直接比较两种分数尺度。DECOMPOSE 和二轮检索仍会把多个 query / round 的结果按 `chunk_id` 去重后再做一层 RRF，从而同时保留词面召回、语义召回和不同查询视角。

Dense cosine 原始值保持为 `vector_score`，RRF 融合值单独记录为 `rrf_score`，只有实际启用 reranker 时才写 `rerank_score`；RRF 分数不会伪装成向量相似度。Hybrid 内部 Dense / BM25 retrieval events 和 merge trace 也保留在 CER 中。检索分数用于排序与审计，但不发送给 structured sufficiency judge，避免 Judge 把不可跨口径比较的分数当作证据强度。

CrossEncoder rerank 是可选能力，默认关闭；候选模型为 `BAAI/bge-reranker-base`。reranker 只能重排已经召回的候选，不能修复未进入候选池的核心证据，因此应先验证 recall，再判断是否值得增加模型加载、时延和资源占用。

### 5.5 证据充分性与有界恢复

两个 profile 共用 retrieval、ACL、融合、EvidenceSnapshot、Prompt、generation 和 citation 实现，差异集中在充分性合同：

| profile | Judge 输出 | 主要取向 |
| :-- | :-- | :-- |
| baseline | binary sufficiency | 默认交互、较高覆盖、较低控制复杂度 |
| orchestrated | structured EvidencePacket judgment | 更严格的证据解释、审计和拒答控制 |

当 Judge 判定证据不足时，系统允许 query rewrite 和一次 R2。R2 使用改写后的查询再次执行同一 Hybrid retrieval，再与 R1 结果形成 union、RRF 融合并重新检查 ACL 和充分性。第二次仍不足则拒答；Judge 调用失败同样 fail-close。structured judge 若返回 malformed JSON，只重试一次；第二次仍无法解析时显式抛出 `SufficiencyJudgeOutputParseError`，不会伪装成普通 `INSUFFICIENT`，两次真实 provider attempt 都进入 CER。

“最多一次”是刻意的边界：它让额外成本、时延和状态空间可预测，也防止近义改写无限循环。当前 Hybrid 冻结评测中，q17、q27 已出现二轮成功恢复，q28、q30 仍未恢复；说明 bounded recovery 已真实生效，但稳定性仍不足，后续重点应是候选召回、缺口类型驱动的改写与 sufficiency 校准，而不是简单增加循环次数。

### 5.6 Prompt、生成与引用

| 项目 | 公开有效口径 |
| :-- | :-- |
| Prompt 证据上限 | 最多 5 个 chunk |
| 单 chunk 字符截断 | 关闭，保留完整已选 chunk |
| 最低证据数 | generator 前至少 2 个 chunk |
| 引用格式 | `[E#]`，绑定 Prompt 可见证据 |
| 系统补造引用 | 关闭 |
| generator | OpenRouter `openai/gpt-4o-mini` |
| sufficiency judge | DeepSeek `deepseek-v4-flash` |
| provider fallback | `[]`，公开默认关闭 |

EvidenceSnapshot 表示控制链选中的证据，PromptSnapshot 表示模型实际收到的证据。引用只能绑定 PromptSnapshot 中的 `[E#]`，不能用“曾经检索到”替代“模型确实看见”。引用检查记录合同结果，不会在模型漏引时偷偷补造来源。

配置中声明了 `context_token_budget: 4096`，但当前实现尚未用 generator 的实际 tokenizer 将它落实为最终 Prompt 硬门禁。现阶段真正生效的约束是最多 5 个完整 chunk 和生成前的证据数量检查。这个字段应视为待完成的预算合同，而不是已经兑现的安全保证；接入更长语料或生产流量前需要补齐 tokenizer-aware prompt budgeting。

公开默认关闭 fallback，是为了让模型身份、成本和失败原因保持明确，避免一次执行在不知情时切换 provider。可用性要求高于可比性时，可以显式设计受策略约束的 fallback，但每次 attempt 仍应单独通过 egress 与预算检查并写入 CER。

当前 generator / judge 并非直接指定：项目曾从本地 `qwen2.5:7b` 出发，经历 RAGAS 与 sufficiency 判别边界、本地 GPU/llama.cpp 验证、Qwen3.5 本地补测、六类 generator 固定题集横评和 API / 自部署成本比较后，才收束到现在的角色分工。完整历史实验、时间边界与重新选型方法见 [模型选型与推理部署演进](model-selection.md)。

## 6. 统一事实、评测与观测

### 6.1 为什么需要 CER

如果在线响应、日志、评测输入和成本表各自重建事实，就会出现“报告中的 contexts 不是模型当时看到的 contexts”或“最终答案反推中间流程”的漂移。

因此，每次执行都形成 CanonicalExecutionRecord，记录：

```text
identity · provenance · principal · policy · route
retrieval · rerank · merge · evidence · prompt
sufficiency · model_calls · usage · timing · outcome
evaluation · errors · events
```

CER 是执行事实源，Response、debug、audit、metrics、cost 和 evaluation 都是它的不同投影。未观测到的历史字段保持 `not_observed`，不会根据最终答案臆造。

### 6.2 在线控制与离线诊断分离

在线链只运行回答所需的 safety、retrieval、sufficiency、generation 和 citation 合同。D-full classifier、Citation Support、Conflict、Uncertainty 与 RAGAS 位于离线层，读取冻结 CER，不重新执行 retrieval，也不改变已生成答案。

这种分离避免把评测模型的成本和延迟混入用户请求，同时让离线分析严格针对“当时真实发生的执行”。代价是离线发现的问题不会自动修复线上答案，需要通过下一轮设计、配置或数据改进回到主链。

## 7. 公开默认值与冻结评测快照

两组数据承担不同职责，不能混用：

| 口径 | 公开 Quickstart | 冻结完整评测 |
| :-- | :-- | :-- |
| 目的 | 让读者用原创 sample 语料运行主链 | 展示完整私有语料上的配对工程评测 |
| 语料 | `sample_data/corpus/` | 冻结语料：34 documents |
| 索引 | 由使用者本地新建 | 575 chunks / 575 vectors / 512 dimensions |
| 默认 profile | baseline | baseline 与 orchestrated 配对执行 |
| generator | OpenRouter `openai/gpt-4o-mini` | 以冻结运行记录为准 |
| judge | DeepSeek `deepseek-v4-flash` | 以冻结运行记录为准 |
| fallback | 关闭 | 以冻结运行记录为准 |
| 可复现范围 | sample 行为、接口与控制合同 | 公开人读报告中的冻结事实；不能由 sample 指标复算 |

公开仓库保留完整实现、sample 数据和人读评测报告，但不发布私有语料、raw CER、raw evidence、完整日志和真实凭据。因此 Quickstart 是功能复现入口，不是假装可以复算完整评测数字。

## 8. 关键权衡

| 当前选择 | 获得什么 | 放弃或推迟什么 |
| :-- | :-- | :-- |
| 本地 BGE + 本地索引 | 数据可控、易调试、低依赖 | 大规模 ANN、分布式扩展与在线增量更新 |
| structure-first + token 硬预算 | 当前语料结构完整、Embedding 输入可验证 | 实现复杂度；任意超长结构仍可能拆分 |
| Hybrid RRF（Dense Top10 + BM25 Top10 → Top5）、rerank 默认关闭 | 同时利用语义与词面召回，RRF 不依赖跨检索器分数标定 | BM25 构建/查询增加本地开销；RRF 仍可能奖励双路错误共识，不能替代语义 rerank |
| 规则路由 + 固定 2 个子问题 | 可预测、可测试、额外调用有限 | 面对复杂任务时的规划自由度 |
| 最多一次 R2 | 成本和状态空间有界 | 多轮自主搜索与更强恢复能力 |
| baseline / orchestrated 双 profile | 在同一底座上观察覆盖、grounding 与成本取舍 | 不提供一个声称全面最优的单一模式 |
| 共享索引 + TopK 前 ACL | 权限变更灵活、避免索引复制 | 不等同于监管级物理租户隔离 |
| 云端 generator/judge、无默认 fallback | 模型能力可用，运行身份与成本明确 | 完全离线能力与 provider 故障时的自动可用性 |
| CER 统一事实 | 可审计、可复核、评测不漂移 | schema、存储与隐私治理成本 |
| 离线深评测 | 不增加在线延迟，可冻结复盘 | 诊断结果不会实时改变当前答案 |

## 9. 何时需要重新选型

出现以下条件时，当前参考实现的取舍应被重新评估：

- 语料规模或并发使 O(N) 扫描无法满足延迟目标：迁移到支持 metadata filter 的生产向量库；
- 租户或监管要求物理隔离：按 tenant / 安全域拆分索引、密钥和生命周期；
- 文档类型扩展到 PDF、Office、图片或扫描件：引入解析、OCR、版面恢复和质量门禁；
- 核心证据持续无法进入候选池或 RRF 排名仍不理想：先改进 query expansion、candidate recall 和 fusion 诊断，再评估 rerank；
- 二轮 recovery 经验证仍不足：引入基于缺口类型的 rewrite、multi-query 或受控工具检索，而不是直接放开无限循环；
- Prompt 可能接收更长证据：完成 generator-tokenizer-aware 的硬预算、截断策略和回归测试；
- API 需要多 worker 或高可用：将 JSONL 执行记录、审计和日志迁移到具备并发与持久性保证的存储；
- 接入真实组织身份：用 IdP / IAM 替换静态 token，并将 principal、tenant 与审计策略纳入统一治理；
- 业务要求完全离线或受限数据推理：增加经过评测的本地 generator/judge profile，并保持显式 egress fail-close；
- 需要证明泛化能力：增加独立 held-out、域外、多跳、冲突、否定和真实攻击题集。

## 10. 延伸阅读

- 组件拓扑与在线控制流：[系统架构](architecture.md)
- 运行、配置与 Docker 入口：[部署说明](deployment-notes.md)
- ACL、egress 与发布安全合同：[安全基线](security-baseline.md)
- 冻结评测结果与解释边界：[评测报告](evaluation-report.md)
- 尚未解决的工程问题：[已知限制](known-limitations.md)
