# 系统架构

## 1. 架构目标

系统围绕四项工程目标组织：

1. 多入口共用同一条业务主链；
2. baseline 与 orchestrated 共享正确性实现，只保留必要控制差异；
3. 每次执行形成一份可审计、可回放的事实记录；
4. 在线回答、离线评测、成本核算和公开报告使用同一事实底座。

## 2. 总体结构

```text
[CLI · API · UI · Eval]
            │
            ▼
[可信接入]
 └─ Principal · Profile · Request / Run / QID
            │
            ▼
[RagApplicationService] ←→ [RuntimeContainer]
            │
            ▼
[执行 Profile：baseline / orchestrated]
            │
            ▼
[共享检索 · 证据 · 生成]
            │
            ▼
[CanonicalExecutionRecord]
            │
            ▼
[Response · Audit · Evaluation · Report]

横切能力：[Identity] [ACL] [Egress] [Budget] [Logging] [Metrics]
```

### 接入轴

CLI、FastAPI、Streamlit UI 和评测入口最终进入 `RagApplicationService`。身份由可信适配器产生，普通请求不能自行声明 roles、groups 或 tenant。

### 执行轴

在线执行只有两个 profile：

| profile | sufficiency | 适用场景 |
| :-- | :-- | :-- |
| baseline | binary | 默认交互、演示、批量回归、成本敏感场景 |
| orchestrated | structured | 严格证据、高风险问答、审计和故障归因 |

两个 profile 共用 route、retrieval、ACL、RRF、evidence、prompt、generation、citation，以及证据不足后的 rewrite、一次二轮检索和再次判断。差异集中在 sufficiency 合同：baseline 使用 binary 判断，orchestrated 基于 EvidencePacket 生成结构化 SufficiencyResult。

### 横切轴

身份、来源权限、数据出境、预算、日志、指标和 CER 贯穿完整执行过程。

## 3. 在线问答链

```text
[问题 + Principal]
        │
        ▼
[Query Safety]
  ├─ REJECT ──> [Refusal] ──> [CER / Response]
  └─ PASS
       │
       ▼
    [规则路由]
      ├─ DIRECT ─────> [ACL 可访问候选 → TopK] ─────────────────┐
      └─ DECOMPOSE ──> [各查询 ACL 可访问候选 → TopK → RRF] ──┤
                                                                 ▼
                                                       [可选 Rerank]
                                                                 │
                                                                 ▼
                                                      [ACL 二次校验]
                                                                 │
                                                                 ▼
                                                     [EvidenceSnapshot]
                                                                 │
                                                                 ▼
                                                     [Sufficiency Judge]
                                                       ├─ SUFFICIENT
                                                       │    └─> [ANSWER PATH]
                                                       ├─ JUDGE_FAILED
                                                       │    └─> [Fail-close → CER / Response]
                                                       └─ INSUFFICIENT
                                                            └─> [Rewrite + ACL Retrieve R2]
                                                                   └─> [Round RRF + ACL 二次校验]
                                                                        └─> [Second Sufficiency]
                                                                             ├─ SUFFICIENT
                                                                             │    └─> [ANSWER PATH]
                                                                             ├─ JUDGE_FAILED
                                                                             │    └─> [Fail-close → CER / Response]
                                                                             └─ STILL INSUFFICIENT
                                                                                  └─> [Refusal → CER / Response]

[ANSWER PATH]
  └─> [PromptSnapshot]
         └─> [Egress / Budget Gate]
                └─> [Generate Answer]
                       └─> [Citation Check]
                              └─> [CER / Response]
```

DIRECT 检索原问题；DECOMPOSE 同时保留原问题和子问题的 retrieval event，并使用 RRF 融合。二轮检索不会覆盖一轮证据，而是形成 union 并保留 lineage。

系统分别记录：

```text
retrieved → merged/reranked → evidence selected
→ prompt visible → cited
```

这些集合不能互相代替。引用只能指向模型实际看见的 Prompt 证据。

## 4. 语料与索引

```text
[Source ACL Registry] ───────────────┐
                                     ▼
[Markdown / TXT] ──> [Loader + ACL Attach]
                                     │
                                     ▼
                         [Structure-first Splitter]
                                     │
                                     ▼
                          [Tokenizer ≤ 510 Hard Gate]
                                     │
                                     ▼
                             [BGE Embedding]
                                     │
                                     ▼
                         [Immutable Index Build]
                                     │
                                     ▼
                               [Validation]
                           ├─ FAIL ──> 保留旧 current
                           └─ PASS ──> 原子更新 current.json
```

公开 Quickstart 使用 `sample_data/corpus/`。Loader 以相对路径生成稳定 `source_id`；ACL Registry 对每个 source 执行 deny-by-default 登记。切分采用 Markdown 结构优先、largest-fit 和真实 tokenizer 硬预算，并验证 coverage、offset、determinism 与向量行数。

索引写入新的不可变 build，全部校验通过后才原子更新 `artifacts/index/current.json`。失败不会破坏旧指针。

本地向量库使用 `vectors.npy + chunks.jsonl` 和内存点积，定位为小规模演示与回归实现。

## 5. CanonicalExecutionRecord

CER 是一次执行的完整事实记录，主要包含：

```text
identity · provenance · principal · policy · route
retrieval · rerank · merge · evidence · prompt
sufficiency · model_calls · usage · timing · outcome
evaluation · errors · events
```

它同时服务于：

- API debug 投影；
- 审计、日志与观测；
- 在线统一断言；
- D-full 后置诊断；
- 从 prompt-visible contexts 构造 RAGAS 输入；
- Timing / Usage / Cost 总账；
- baseline 与 orchestrated 自动配对比较。

历史材料缺少的事实保持 `not_observed`，不会从最终结果反推中间过程。

## 6. 在线与离线边界

D-full 的 classifier、Citation Support、Conflict 和 Uncertainty 是后置评测信号。它们读取冻结 CER，用于故障定位和审计，不进入在线答案控制链。

RAGAS 同样消费冻结 CER，不重新执行 retrieval 或 query pipeline。它评价模型当时实际看到的 contexts，避免评测输入与在线事实漂移。

## 7. 关键实现位置

| 职责 | 路径 |
| :-- | :-- |
| 应用服务 | `src/agentic_rag/service/` |
| 两个 profile | `src/agentic_rag/engine/` |
| 在线主链 | `src/agentic_rag/query_pipeline.py` |
| CER 与 snapshots | `src/agentic_rag/execution/` |
| 索引与切分 | `src/agentic_rag/ingest/`、`indexing/` |
| ACL / egress | `src/agentic_rag/policy/` |
| 检索与融合 | `src/agentic_rag/retrieve/` |
| 后置诊断 | `src/agentic_rag/evaluation/`、`evidence/` |
| 报告投影 | `src/agentic_rag/reporting/` |

各层选型依据、有效配置与关键权衡见 [系统设计与技术选型](system-design.md)；系统的规模与部署边界见 [已知限制](known-limitations.md)。
