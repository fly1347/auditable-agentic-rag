# 评测报告

## 1. 评测目标

最终评测关注四个工程问题：

1. 当前结构化切分、冻结索引与 Hybrid RRF 能否稳定完成 30 题同域回归评测；
2. baseline 与 orchestrated 在共同 Hybrid Retriever 下分别得到什么控制结果；
3. structured sufficiency 增加多少时延、Token 和费用；
4. 当前证据能够支撑哪些结论，还保留哪些缺口。

评测信号保持分层，不合成单一总分。Dense-only → Hybrid RRF 的检索变更另保留专项对照报告，本报告以当前正式 Hybrid 实现为主语。

## 2. 冻结条件

| 对象 | 冻结值 |
| :-- | :-- |
| 数据集 | 项目专用同域回归评测集，30 题，`derived_in_domain_regression` |
| dataset SHA-256 | `2abf448e2ac2fa67a51de370db3fed01597ce64ac5e742faf241e4c51bba2204` |
| corpus SHA-256 | `605858272b2b7fe8eceb931ce363875ee005638a693ffcb40b5e65fa32aa7c4e` |
| config SHA-256 | `d47fc9c017e830a1ed197b8628806fa0a173a6ac9a1d8cb472bb1fa3e2f7a60d` |
| ACL SHA-256 | `8e6dfc826ac1d8d7610a0386fdbec18ac9e8a2b282f7d1722a88f58ef0c495b6` |
| index build | `20260821T054541778117Z-60585827-e81a7f97` |
| index | 34 docs / 575 chunks / 575 vectors / 512 dimensions |
| embedding | `BAAI/bge-small-zh-v1.5`，normalized，content cap=510 |
| Retriever | Dense candidate=10；BM25 candidate=10；RRF k=60；final Top5 |
| baseline run | `eval_413526d23766` |
| orchestrated run | `eval_e78ef09a941d` |
| RAGAS | 0.4.3 |

两套 profile 共用相同数据、语料、索引和 Hybrid Retriever；主要控制变量仍是 binary 与 structured sufficiency 合同。rewrite 与二轮检索机制本身共享，但不同 sufficiency 判断会触发不同数量的二轮执行。

## 3. 评测结构

| 层 | 输入 | 主要信号 |
| :-- | :-- | :-- |
| 在线主链 | 冻结回归集 + 冻结配置/索引 | route、retrieval、sufficiency、answer、citation、timing、usage |
| 统一断言 | CER + dataset | behavior、evidence、prompt、citation、route、security、errors、budget |
| 精确检索 probe | 同一冻结索引 + 人工 answer-bearing 标注 | Dense / BM25 / RRF rank、CORE Hit@5 |
| D-full | 冻结 CER | classifier、sufficiency、citation support、conflict、uncertainty |
| RAGAS | CER prompt-visible contexts | Context Precision、Faithfulness、Answer Relevancy |
| 总账 | 三层 model calls | time、calls、tokens、estimated cost |
| 配对对比 | 双 profile 底账 | 控制变化、共同题质量迁移、成本增量 |

## 4. 切分、索引与 Retriever 质量

| 检查项 | 冻结结果 |
| :-- | :-- |
| 语料规模 | 34 docs |
| chunk / vector | 575 / 575 |
| embedding dimensions | 512 |
| content token cap | 510 |
| coverage / offset / determinism / vector-row parity | PASS |
| baseline behavior contract | 30/30 |
| baseline 人读答案质量 | A=27，B=3，C=0，D=0 |

冻结索引继续采用结构优先切分和真实 tokenizer 硬预算。当前 Retriever 在同一批 chunk 上执行 Dense Top10 与 BM25 Top10，再用 RRF(k=60) 融合为最终 Top5。

source-level Full@5 已不足以区分检索质量：Dense 为 29/29，RRF 为 27/29；但在人工确认的 answer-bearing evidence 上，CORE Hit@5 从 Dense 14/27 提升到 RRF 20/27。q03、q06、q19、q26、q27、q30 是典型新增命中。公开默认从 Dense-only 切换到 Hybrid RRF 的依据是这一 strict-evidence 改善，而不是母文档命中率。

## 5. 在线主链结果

| 观察项 | baseline | orchestrated | 变化 |
| :-- | --: | --: | --: |
| ANSWERED | 29 | 27 | -2 |
| REFUSED | 1（q02） | 3（q02、q28、q30） | +2 |
| DIRECT / DECOMPOSE | 24 / 6 | 24 / 6 | 0 |
| behavior contract | 30/30 | 28/30 | -2 |
| 二轮 sufficiency | 1（q02） | 5（q02、q17、q27、q28、q30） | +4 |
| prompt-evidence fail | 2（q06、q27） | 4（q06、q27、q28、q30） | +2 |

q02 是预期拒答。orchestrated 的四道应回答首轮不足题中，q17、q27 在二轮恢复并生成答案；q28、q30 最终拒答，因此对应回答题的 agentic recovery 为 2/4。

q28 当前仍是实际 answer-bearing retrieval gap：etcd 详解在 RRF 中未进入最终 EvidencePacket。q30 则不同，首轮已有较直接 KV Cache 证据，baseline 正常回答且 Faithfulness=1.0；orchestrated 仍连续判为 INSUFFICIENT，更接近 structured sufficiency calibration / provider variation 的 false negative。

q06、q27 还存在机器 expected-evidence gate 与人工 precise-evidence 口径不完全一致；q21 baseline 出现单题 citation-validity fail。这些都保留为独立审计信号，不用一个 gate 反向覆盖其他证据。

### 答案质量分档

| 档位 | baseline | orchestrated |
| :-- | :-- | :-- |
| A | 27 | 25 |
| B | 3（q16、q26、q27） | 3（q16、q26、q27） |
| C | 0 | 0 |
| D | 0 | 2（q28、q30） |

Hybrid baseline 对 29/29 道应回答题全部形成有效答案，无异常拒答。orchestrated 的下降集中在 q28、q30 两个异常拒答；进入生成阶段的答案整体仍稳定。

## 6. 性能、Token 与成本

| metric | baseline | orchestrated | 变化 |
| :-- | --: | --: | --: |
| service time sum | 137.674 s | 194.988 s | +41.6% |
| median | 3.891 s | 5.864 s | +50.7% |
| p95 | 8.536 s | 11.848 s | +38.8% |
| model calls | 67 | 73 | +9.0% |
| total tokens | 123,627 | 190,941 | +54.4% |
| estimated cost | $0.036531 | $0.073633 | +101.6% |

> 本节 p95 沿用各 B2 `Timing-Usage-Cost` 报告的 percentile 口径。机器生成的配对 comparison 使用 nearest-rank p95，因此其中会显示 9.325 s / 12.762 s；两者来自同一 30 题 `service_total_ms`，只是 percentile 定义不同。

Sufficiency Judge 分账：

| metric | baseline binary | orchestrated structured |
| :-- | --: | --: |
| calls | 31 | 35 |
| provider latency sum | 17.770 s | 69.203 s |
| total tokens | 53,641 | 125,449 |
| estimated cost | $0.023713 | $0.061654 |

structured judge 仍是 orchestrated 的主要成本增量：EvidencePacket 输入更长，输出为结构化合同，并且更多 INSUFFICIENT 会触发 rewrite + second judge。当前公开默认继续保持 baseline。

## 7. D-full 后置诊断

| signal | baseline | orchestrated |
| :-- | :-- | :-- |
| sufficiency | 29 sufficient / 1 insufficient | 27 sufficient / 3 insufficient |
| citation support | 1 supported / 25 partial / 2 unsupported / 1 no_evidence / 1 N/A | 1 supported / 24 partial / 2 unsupported / 3 N/A |
| unsupported claim 题数 | 16 | 15 |
| conflict_count > 0 | 0 | 0 |
| uncertainty | low=1 / medium=12 / high=17 | low=1 / medium=11 / high=18 |

Citation Support 是本地字符/词面规则，适合提供确定性审计线索，不等同于语义蕴含判断。Conflict 最终未触发，只说明当前规则在本批冻结 EvidencePacket 上没有给出疑似冲突。

## 8. RAGAS

各 profile 实际题集不同：baseline 评 29 题，orchestrated 评 27 题。跨 profile 结论使用共同 27 题。

| metric | baseline | orchestrated | delta |
| :-- | --: | --: | --: |
| Context Precision | 0.8539 | 0.8197 | -0.0342 |
| Faithfulness | 0.9633 | 0.9562 | -0.0071 |
| Answer Relevancy | 0.8585 | 0.8468 | -0.0118 |

RAGAS 不显示 structured profile 在共同题上普遍提升；严格证据控制、回答质量和回答覆盖率仍需分别阅读。

对本轮历史关注题，Hybrid baseline 的 Faithfulness 为：q06=1.000、q19=1.000、q27=0.714、q28=0.400。q06/q19 体现 core evidence 进入 Prompt 后 grounding 明显改善；q28 则说明高 Context Precision 仍可能掩盖真正 answer-bearing chunk 缺失。

## 9. 三类总账

| category | baseline calls / tokens / cost | orchestrated calls / tokens / cost |
| :-- | :-- | :-- |
| 在线主链 | 67 / 123,627 / $0.036531 | 73 / 190,941 / $0.073633 |
| D-full | 30 / 12,847 / $0.002636 | 30 / 12,849 / $0.002637 |
| RAGAS | 290 / 354,033 / $0.095437 | 270 / 330,350 / $0.077286 |
| 合计 | 387 / 490,507 / $0.134604 | 373 / 534,140 / $0.153556 |

orchestrated RAGAS 费用较低，是因为 q28、q30 不生成答案、未进入 RAGAS；这不能说明 orchestrated 主链更便宜。在线主链实际费用约为 baseline 的 2.02 倍。费用均为静态价格表估算，不作为账单对账结果。

## 10. 结论与范围

- 当前正式 Retriever：`Dense Top10 + BM25 Top10 → RRF(k=60) → Top5`；
- Hybrid baseline：30/30 behavior，29/29 应回答题全部回答，人工答案 A=27 / B=3 / C=0 / D=0；
- Hybrid orchestrated：q17、q27 二轮恢复，q28、q30 最终异常拒答；严格证据控制仍存在覆盖损失与 false-negative 风险；
- Retriever 变更依据：CORE Hit@5 14/27 → 20/27，q06/q19 等 Dense 缺口获得实际修复；
- 当前主要边界：q28 的 RRF 排名融合反例、q30 的 structured sufficiency 校准风险，以及评测 gate / precise evidence 的口径差异；
- 评测范围：该回归集适用于同域工程回归和故障诊断，不代表域外泛化能力。

完整逐题、检索工作流、D-full、RAGAS 和成本报告见 [`artifacts/evaluation/`](../artifacts/evaluation/README.md)；Retriever 变更依据见 [`Dense-vs-Hybrid-RRF-四组批跑对比报告.md`](../artifacts/evaluation/Dense-vs-Hybrid-RRF-四组批跑对比报告.md)。
