# Dense vs Hybrid RRF｜四组批跑对比报告

**日期：** 2026-09-03
**批次：** `dense-hybrid-main-20260903-211042`
**对象：** B2 30 题，Dense / Hybrid RRF × baseline / orchestrated
**结论：** `HYBRID_RRF_SELECTED / PASS_WITH_KNOWN_LIMITATIONS`

## 1. 本报告回答的问题

本报告只回答一个工程决策问题：

> 将公开仓库的检索主链从 Dense-only 改为 `Dense Top10 + BM25 Top10 → RRF(k=60) → Top5`，是否有足够证据支持；改善发生在哪里，代价是什么，哪些问题仍未解决。

因此，本报告以**检索层直接证据**为主，以四组端到端批跑、RAGAS、人工答案质量和成本为辅助。它不替代完整系统终版评估报告。

本次 Dense 批跑与 2026-08-24 历史终版评估相比也出现了模型判断与生成波动，因此历史 Dense 结果不作为本次检索变更的数值对照。检索方案的主要归因依据采用同日固定索引上的 Dense / BM25 / RRF 可复现检索 probe；四组 E2E 用于确认这种检索变化能否传导到真实控制链路。

---

## 2. 冻结条件与变量

四组主链共享：

| 对象 | 冻结值 |
| :-- | :-- |
| 数据集 | B2，30 题 |
| dataset SHA-256 | `2abf448e2ac2fa67a51de370db3fed01597ce64ac5e742faf241e4c51bba2204` |
| corpus SHA-256 | `605858272b2b7fe8eceb931ce363875ee005638a693ffcb40b5e65fa32aa7c4e` |
| config SHA-256 | `d47fc9c017e830a1ed197b8628806fa0a173a6ac9a1d8cb472bb1fa3e2f7a60d` |
| ACL registry SHA-256 | `8e6dfc826ac1d8d7610a0386fdbec18ac9e8a2b282f7d1722a88f58ef0c495b6` |
| index build | `20260821T054541778117Z-60585827-e81a7f97` |
| index | 34 documents / 575 chunks / 575 vectors / 512 dimensions |
| route | 四组均 DIRECT=24、DECOMPOSE=6 |

变量有两层：

1. **Retriever**
   - Dense：cosine dense retrieval；
   - Hybrid RRF：Dense Top10 + BM25 Top10 → RRF `k=60` → final Top5。
2. **Sufficiency profile**
   - baseline：binary sufficiency；
   - orchestrated：structured sufficiency + EvidencePacket。

四组共用同一数据、语料、配置和索引，因此同一批次内可以观察 Retriever 改动对两种 profile 的影响。但 sufficiency / generation 都包含远程模型调用，端到端答案与拒答仍可能受模型波动影响。

---

## 3. 为什么不能只看母文档命中

同日检索对照实验把检索拆为两层：

- **source-level**：期待母文档是否进入 Top5；
- **strict evidence-level**：人工确认的 answer-bearing char range 是否进入 Top5。

### 3.1 Source-level

| Method | Any@5 | Full@5 |
| :-- | --: | --: |
| Dense | **29/29** | **29/29** |
| BM25 | 28/29 | 22/29 |
| RRF | **29/29** | 27/29 |

Dense 在母文档层已经接近饱和，继续只看 source-level 会得到“检索没有问题”的错觉。

### 3.2 Strict evidence-level

已人工确认 12 题、27 条 CORE、2 条 AUX 精确证据。

| Method | CORE Hit@5 | CORE + AUX Hit@5 |
| :-- | --: | --: |
| Dense | 14/27 | 14/29 |
| BM25 | 14/27 | 15/29 |
| RRF | **20/27** | **20/29** |

核心结果：

```text
Dense CORE Hit@5 = 14/27
RRF   CORE Hit@5 = 20/27
```

RRF 在当前已确认 CORE 上净增加 **6 条 Top5 命中**。这是本次 Retriever 变更最直接的技术证据。

---

## 4. Hybrid 实际救回了什么

以下 CORE 在 Dense Top5 外，经 BM25 补召回后由 RRF 推入 Top5：

| qid | Evidence | Dense | BM25 | RRF |
| :-- | :-- | --: | --: | --: |
| q03 | `external/14@1923-3200` | R7 | R2 | **R5** |
| q06 | `internal/04@639-999` | R67 | **R1** | **R1** |
| q19 | `internal/08@1393-1705` | R30 | **R2** | **R3** |
| q26 | `internal/07@849-1934` | R7 | **R1** | **R3** |
| q27 | `internal/07@301-848` | R10 | R6 | **R5** |
| q30 | `internal/10@920-1280` | R51 | **R3** | **R5** |

BM25 单独的 CORE Hit@5 仍是 14/27，与 Dense 相同，因此它的价值是作为**互补召回通道**，不是替代 Dense。RRF 的价值在于融合两路排名，而不要求直接比较 cosine 与 BM25 原始分数。

---

## 5. 四组端到端主链结果

### 5.1 控制结果

| run | ANSWERED / REFUSED | behavior pass | first INSUFFICIENT | 二轮恢复 |
| :-- | :-- | --: | :-- | :-- |
| Dense / baseline | 29 / 1 | 30/30 | q02、q06 | q06 恢复 |
| Dense / orchestrated | 24 / 6 | 25/30 | q02、q06、q19、q23、q27、q28 | 0 |
| Hybrid / baseline | 29 / 1 | **30/30** | q02 | 无应答题进入恢复 |
| Hybrid / orchestrated | 27 / 3 | **28/30** | q02、q17、q27、q28、q30 | **q17、q27 恢复** |

在 orchestrated 下，Hybrid 将异常拒答从 Dense 的 5 道应回答题：

```text
q06, q19, q23, q27, q28
```

降为 2 道：

```text
q28, q30
```

但这个差值不能全部归因于 Retriever，因为 structured judge 本身存在运行间判断波动。可归因程度最高的是 q06、q19、q27：它们同时具备 strict evidence rank 改善与 E2E 行为改善。

### 5.2 人工答案质量分档

本次人工分档只看最终答案质量；q02 正确拒答计 A，应回答却拒答计 D。

| run | A | B | C | D |
| :-- | --: | --: | --: | --: |
| Hybrid / baseline | **27** | 3 | 0 | **0** |
| Hybrid / orchestrated | **25** | 3 | 0 | 2 |
| Dense / baseline | 26 | 3 | 1 | 0 |
| Dense / orchestrated | 24 | 1 | 0 | 5 |

观察：

- **Hybrid / baseline 最稳**：30 题无 C/D，29 道应回答题全部形成有效答案；
- Dense / baseline 的 q06 为 C，说明 Dense 在该题的答案偏离 RAG 典型 failure mode 核心；
- orchestrated 的主要损失来自异常拒答，而不是进入生成阶段后出现大量内容型错误；
- Hybrid orchestrated 的 q28、q30 为 D，分别代表“检索仍有真实缺口”和“structured sufficiency 仍会过严/波动”两种不同问题。

---

## 6. 关键题归因

### q06：最清楚的 lexical rescue

```text
CORE: internal/04_RAG失败模式.md
Dense R67 → BM25 R1 → RRF R1
```

Dense 能找到同主题 RAG 文档，但直接回答“什么情况下容易 hallucination”的核心片段不可达。Hybrid 首轮 EvidencePacket 已包含该片段，structured judge 直接判 `SUFFICIENT`，最终答案由 Dense orchestrated 的异常拒答变为 A。

这是本轮最强的：

```text
Dense candidate reachability failure
→ BM25 lexical rescue
→ RRF 保留收益
→ E2E 恢复
```

### q19：精确组件名的收益

```text
CORE: internal/08 Kubernetes Scheduler 详解
Dense R30 → BM25 R2 → RRF R3
```

Hybrid 的最终 Top5 包含 `internal/08@1115-1993`，其中明确写出 kube-scheduler 将新建 Pod 分配到合适 Node。Dense orchestrated 拒答，Hybrid orchestrated 首轮直接 `SUFFICIENT` 并正常回答。

### q27：RRF + 二轮恢复共同作用

```text
CORE: internal/07 HNSW mechanism
Dense R10 → BM25 R6 → RRF R5
```

Hybrid 首轮已经把核心证据推到 Top5，但 structured judge 仍认为“机制性说明不够”，触发 rewrite。第二轮将相关 internal/07 片段进一步提升并判 `SUFFICIENT`，最终正常回答。

因此 q27 不能简单写成“RRF 单独解决”：Retriever 把证据送入可达范围，**二轮 recovery 完成了控制层恢复**。

### q28：RRF 的真实边界

```text
CORE: internal/08 etcd 作用
Dense R69 → BM25 R5 → RRF R9
```

BM25 已经把正确片段救到 Top5，但 Dense 没有支持；RRF 奖励了两路共同靠前的概览块，把正确片段重新压出 Top5。Hybrid orchestrated 两轮都只拿到架构图中的 `etcd / KV存储` 标签，最终拒答。

它说明：

> RRF 奖励排名共识，但不能判断共识是否真的 answer-bearing。

q28 应保留为 Hybrid 的明确 Known Limitation，而不是为了“证明 Hybrid 更好”而弱化。

### q30：不是检索层失败的典型

检索 probe 中 q30 CORE 已从 Dense R51 提升到 RRF R5；Hybrid baseline 也正常回答 A。Hybrid orchestrated 首轮 Top1 已是 `internal/10_模型服务层vLLM架构.md@0-773`，其中直接包含 KV Cache 的计算作用、显存占用与传统内存管理问题，但 structured judge 仍要求更完整的量化对比，二轮继续拒答。

因此 q30 更适合作为：

```text
structured sufficiency calibration / model-variance case
```

而不是 Hybrid retrieval failure。

### q23：提醒不要把所有 E2E 差异都算给 Retriever

Dense orchestrated 本批次对 q23 异常拒答，而 Hybrid orchestrated 正常回答；但 q23 并不是此前确认的 Dense 深层核心缺口。该题说明远程 judge 的单批输出会波动，进一步支持“Retriever 选型以 strict evidence rank 为主，E2E 结果为辅助”的归因纪律。

---

## 7. RAGAS

### 7.1 各 run 实际均值

| run | 题数 | Context Precision | Faithfulness | Answer Relevancy |
| :-- | --: | --: | --: | --: |
| Dense / baseline | 29 | 0.7999 | 0.8506 | 0.8804 |
| Dense / orchestrated | 24 | 0.8832 | 0.9130 | 0.8722 |
| Hybrid / baseline | 29 | **0.8640** | **0.9452** | 0.8678 |
| Hybrid / orchestrated | 27 | 0.8197 | **0.9562** | 0.8468 |

baseline 两组覆盖同一 29 道应回答题，因此可直接配对观察：

```text
Context Precision  +0.0641
Faithfulness       +0.0945
Answer Relevancy   -0.0126
```

这与检索 probe 的方向一致：Hybrid 更明显改善了证据相关性与 grounding，回答切题度没有同步上升。

orchestrated 两组参与题数不同。只看两组都实际回答的 23 题：

```text
Context Precision  0.8890 → 0.8824
Faithfulness       0.9285 → 0.9666
Answer Relevancy   0.8668 → 0.8438
```

这组结果更适合说明“Faithfulness 仍有改善信号”，不适合据此声称 Hybrid 全面提高所有 RAGAS 指标。RAGAS 本身也包含 LLM evaluator 波动，应与 deterministic retrieval evidence 一起阅读。

### 7.2 典型题

| qid | Dense baseline CP / Faith | Hybrid baseline CP / Faith | 观察 |
| :-- | :-- | :-- | :-- |
| q06 | 0.000 / 0.875 | 0.500 / **1.000** | 直接 core 进入 prompt 后 grounding 改善 |
| q19 | 0.000 / 0.000 | 0.250 / **1.000** | Scheduler 职责从参数知识补全转为有证据支撑 |
| q27 | 0.333 / 0.143 | 0.450 / **0.714** | core 进入 Top5 后 Faithfulness 明显改善 |
| q28 | 1.000 / 0.400 | 1.000 / 0.400 | 母文档相关不等于核心证据到位 |

q28 再次说明 Context Precision / source relevance 单独使用不足以判断真正的 answer-bearing evidence 是否命中。

---

## 8. 性能、Token 与在线成本

| run | service total | median | p95 | model calls | tokens | estimated cost |
| :-- | --: | --: | --: | --: | --: | --: |
| Dense / baseline | 130.295 s | 3.971 s | 8.196 s | 69 | 121,277 | $0.036105 |
| Hybrid / baseline | 137.674 s | 3.891 s | 8.536 s | 67 | 123,627 | $0.036531 |
| Dense / orchestrated | 177.259 s | 5.111 s | 9.691 s | 72 | 183,151 | $0.072752 |
| Hybrid / orchestrated | 194.988 s | 5.864 s | 11.848 s | 73 | 190,941 | $0.073633 |

> p95 沿用各 run 的 `Timing-Usage-Cost` 报告口径。自动生成的 baseline-vs-orchestrated comparison 使用 nearest-rank p95，因此数值会略有不同；底层均来自相同的逐题 `service_total_ms`。

Dense → Hybrid：

- baseline：tokens `+1.9%`，估算费用 `+1.2%`；
- orchestrated：tokens `+4.3%`，估算费用 `+1.2%`。

Hybrid 检索本身没有新增模型推理，只增加一条 BM25 通道和本地 RRF 融合。主链费用变化主要来自本批次 judge / rewrite / generator 实际调用差异，而不是 RRF 计算本身。端到端 latency 同样受到模型供应商波动影响，因此不能把 5%～10% 的 service total 差异直接解释成 Hybrid 检索开销。

从工程取舍看，当前 575 chunks 规模下：

- BM25 增加的是本地倒排索引、少量 CPU / 内存 / 磁盘；
- RRF 是候选排名融合；
- 相比 Cross-Encoder reranker，不新增一轮模型推理成本。

这也是本轮选择 RRF、暂不引入 reranker 的重要原因。

---

## 9. 为什么选 Hybrid RRF，而不是 BM25-only 或 reranker

### BM25-only

不选。CORE Hit@5 与 Dense 同为 14/27，说明它对实体词、组件名、精确术语很强，但语义召回并不稳定。它适合作为 Dense 的补充通道。

### Reranker

实验显示 Cross-Encoder 能救回部分候选，例如 q19、q27 external core；但它受 candidate_k 覆盖约束，候选没进池就无法处理，而且本身也会误排，例如 q27 internal core 被从 RRF R5 压到 R9。

当前项目目标是以低复杂度修复已知 lexical / exact-evidence 召回缺口。RRF 已将 CORE Hit@5 从 14/27 提到 20/27，且不增加模型推理，因此优先级高于 reranker。

---

## 10. 最终工程决策

本轮证据支持公开仓库将默认 Retriever 从 Dense-only 更新为：

```text
Query
 ├─ Dense Top10
 └─ BM25 Top10
        ↓
      RRF(k=60)
        ↓
     final Top5
```

主要理由：

1. strict CORE Hit@5 从 **14/27 → 20/27**；
2. q06、q19 等 Dense 深层 answer-bearing evidence 被明确救回；
3. Hybrid baseline 在本批次达到 **29/29 应回答题全部回答、A=27/B=3/C=0/D=0**；
4. orchestrated 的异常拒答由 Dense 的 5 道应回答题降到 2 道，其中 q06、q19 有强检索归因，q27通过二轮恢复；
5. 在线费用变化很小，RRF 不增加模型推理；
6. q28 仍保留为明确反例，说明方案有边界但没有掩盖失败。

最终判断：

```text
Dense-only：保留为历史实验基线
Hybrid RRF：进入公开正式实现
Reranker：本轮不加入主链
```

---

## 11. Known Limitations

1. **q28 仍是真实检索缺口。** BM25 R5 被 RRF 的错误共识压到 R9。
2. **RRF 不理解语义。** 它融合排名，不判断候选是否真正 answer-bearing。
3. **精确证据清单只覆盖 12 题。** 27 条 CORE 足以证明当前已知问题的净改善，但不是 29 道应回答题的完整 chunk-level gold set。
4. **当前 expected_evidence gate 仍是原有粗粒度标注。** q06、q27 在 Hybrid 中已出现人工确认的直接 answer-bearing evidence，但统一 gate 仍可能因旧 expected-source/full-coverage 语义报 fail；该 gate 本轮不改。
5. **远程 judge / generator 有运行间波动。** q23、q30 说明不能把单次 E2E refusal 差异全部归因给 Retriever。
6. **本批次规模较小。** B2 是冻结回归集，适合工程回归与已知故障验证，不等同于 held-out 泛化评测。

---

## 12. 证据索引

本报告由同一冻结索引上的 Dense / Hybrid 四组评测机器底账、专项检索 probe 与人工答案质量分档汇总而来。公开仓库只保留当前 Hybrid RRF 的精选人读报告，不发布 raw CER、raw evidence、完整私有运行日志或 Dense 历史运行包。

公开可复核入口：

- [`Baseline-vs-Orchestrated-最终评测对比.md`](Baseline-vs-Orchestrated-最终评测对比.md)：当前 Hybrid RRF 下的双 profile 配对比较；
- [`baseline/`](baseline/)：Hybrid baseline 的在线、D-full、RAGAS 与总账报告；
- [`orchestrated/`](orchestrated/)：Hybrid orchestrated 的对应报告；
- [`../../docs/evaluation-report.md`](../../docs/evaluation-report.md)：当前正式实现的终版评估结论与适用边界。

Dense 四组源 bundle 与人工 precise-evidence 工作稿保留在项目私有评测档案中，用于维护期复核，不作为公开运行时资产。
