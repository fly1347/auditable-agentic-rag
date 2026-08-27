# 评测报告

## 1. 评测目标

最终评测关注四个工程问题：

1. 当前结构化切分与冻结索引能否稳定完成 30 题同域回归评测；
2. baseline 与 orchestrated 在共同输入下分别得到什么控制结果；
3. structured sufficiency 增加多少时延、Token 和费用；
4. 当前证据能够支撑哪些结论，还保留哪些缺口。

评测信号保持分层，不合成单一总分。

## 2. 冻结条件

| 对象 | 冻结值 |
| :-- | :-- |
| 数据集 | 项目专用同域回归评测集，30 题，`derived_in_domain_regression` |
| dataset SHA-256 | `ad607fd6372ba3b694cab57fa78802ea7a789d4ecc2b9cc8fc0b8454325301fd` |
| corpus SHA-256 | `605858272b2b7fe8eceb931ce363875ee005638a693ffcb40b5e65fa32aa7c4e` |
| config SHA-256 | `d47fc9c017e830a1ed197b8628806fa0a173a6ac9a1d8cb472bb1fa3e2f7a60d` |
| ACL SHA-256 | `8e6dfc826ac1d8d7610a0386fdbec18ac9e8a2b282f7d1722a88f58ef0c495b6` |
| index build | `20260821T054541778117Z-60585827-e81a7f97` |
| index | 34 docs / 575 chunks / 575 vectors / 512 dimensions |
| embedding | `BAAI/bge-small-zh-v1.5`，normalized，content cap=510 |
| baseline run | `eval_b4d7474e4c62` |
| orchestrated run | `eval_1ffb699473ab` |
| RAGAS | 0.4.3 |

两套 profile 的 30/30 第一轮 original-query Top5 chunk 与 score 一致。主要变量是 binary 与 structured sufficiency 合同；rewrite 与二轮检索机制本身共享，但不同 sufficiency 判断会触发不同数量的二轮执行。

## 3. 评测结构

| 层 | 输入 | 主要信号 |
| :-- | :-- | :-- |
| 在线主链 | 冻结回归集 + 冻结配置/索引 | route、retrieval、sufficiency、answer、citation、timing、usage |
| 统一断言 | CER + dataset | behavior、evidence、prompt、citation、route、security、errors、budget |
| D-full | 冻结 CER | classifier、sufficiency、citation support、conflict、uncertainty |
| RAGAS | CER prompt-visible contexts | Context Precision、Faithfulness、Answer Relevancy |
| 总账 | 三层 model calls | time、calls、tokens、estimated cost |
| 配对对比 | 双 profile 底账 | 控制变化、共同题质量迁移、成本增量 |

## 4. 切分与索引质量

| 检查项 | 冻结结果 |
| :-- | :-- |
| 语料规模 | 34 docs |
| chunk / vector | 575 / 575 |
| embedding dimensions | 512 |
| content token cap | 510 |
| coverage / offset / determinism / vector-row parity | PASS |
| baseline behavior contract | 30/30 |
| baseline 人读答案质量 | A=29，B=1（q27） |

冻结索引采用结构优先切分和真实 tokenizer 硬预算，并完成 coverage、offset、determinism 与向量行数一致性校验。两个 profile 共用这一索引，配对结果建立在一致的检索底座上。

## 5. 在线主链结果

| 观察项 | baseline | orchestrated | 变化 |
| :-- | --: | --: | --: |
| ANSWERED | 29 | 25 | -4 |
| REFUSED | 1（q02） | 5（q02、q06、q19、q27、q28） | +4 |
| DIRECT / DECOMPOSE | 24 / 6 | 24 / 6 | 0 |
| 二轮 sufficiency | 1 | 5 | +4 |
| prompt-evidence fail | 1（q26） | 5（q06、q19、q26、q27、q28） | +4 |

q02 是预期拒答。q06、q19、q27、q28 位于语料范围内，但最终 Prompt 缺少核心 answer-bearing evidence。baseline 依赖模型参数知识给出可读答案；orchestrated 将其识别为证据不足并拒答。

### 答案质量分档

| 档位 | baseline | orchestrated |
| :-- | :-- | :-- |
| A | 29 | 26 |
| B | 1（q27） | 0 |
| C | 0 | 0 |
| D | 0 | 4（q06、q19、q27、q28） |

orchestrated 实际生成的 25 道答案均为 A，q02 正确拒答。总体下降来自四道应回答题被拦截。共同完成回答的题目未显示 structured orchestration 对答案文本质量带来额外提升。

q26 保留双重事实：机器 `prompt_evidence_status=fail`，人工答案质量为 A，引用的 `external/22` 能支撑核心答案。

## 6. 性能、Token 与成本

| metric | baseline | orchestrated | 变化 |
| :-- | --: | --: | --: |
| service time sum | 124.334 s | 167.940 s | +35.1% |
| median | 3.555 s | 5.173 s | +45.5% |
| p95 | 7.843 s | 9.265 s | +18.1% |
| model calls | 67 | 71 | +6.0% |
| total tokens | 119,756 | 188,062 | +57.0% |
| estimated cost | $0.035468 | $0.073791 | +108.0% |

Sufficiency Judge 分账：

| metric | baseline binary | orchestrated structured |
| :-- | --: | --: |
| calls | 31 | 35 |
| total tokens | 51,968 | 128,904 |
| estimated cost | $0.022977 | $0.062828 |

五道二轮题全部再次判为 INSUFFICIENT，本批 recovery 为 0/5。增量主要来自更长的 EvidencePacket、结构化输出、rewrite 与第二次 judge。

## 7. D-full 后置诊断

| signal | baseline | orchestrated |
| :-- | :-- | :-- |
| sufficiency | 29 sufficient / 1 insufficient | 25 sufficient / 5 insufficient |
| citation support | 1 supported / 26 partial / 2 unsupported / 1 N/A | 23 partial / 2 unsupported / 5 N/A |
| unsupported claim 题数 | 12 | 13 |
| conflict_count > 0 | 0 | 0 |
| uncertainty high | 13 | 18 |

Citation Support 是本地字符/词面规则，适合提供确定性审计线索，不等同于语义蕴含判断。Conflict 最终未触发，只说明当前规则在这两批数据上没有给出疑似冲突。

## 8. RAGAS

各 profile 实际题集不同：baseline 评 29 题，orchestrated 评 25 题。跨 profile 结论使用共同 25 题。

| metric | baseline | orchestrated | delta |
| :-- | --: | --: | --: |
| Context Precision | 0.8734 | 0.9066 | +0.0331 |
| Faithfulness | 0.9691 | 0.9422 | -0.0269 |
| Answer Relevancy | 0.8673 | 0.8303 | -0.0370 |

orchestrated 改善了 Context Precision，Faithfulness 与 Answer Relevancy 没有同步提升。严格证据控制、回答质量和回答覆盖率需要分别阅读。

四道新增拒答题的 baseline Faithfulness 为 0.3750、0.2000、0.2857、0.4000，支持“答案可读，但 grounding 不足”的判断。

## 9. 三类总账

| category | baseline calls / tokens / cost | orchestrated calls / tokens / cost |
| :-- | :-- | :-- |
| 在线主链 | 67 / 119,756 / $0.035468 | 71 / 188,062 / $0.073791 |
| D-full | 30 / 12,858 / $0.002642 | 30 / 12,866 / $0.002647 |
| RAGAS | 290 / 350,482 / $0.115970 | 250 / 303,979 / $0.072610 |
| 合计 | 387 / 483,096 / $0.154081 | 351 / 504,907 / $0.149048 |

orchestrated 全套评测费用略低，原因是四道新增拒答题未进入 RAGAS。在线主链实际更贵。费用均为静态价格表估算，不作为账单对账结果。

## 10. 结论与范围

- baseline：高覆盖、低成本，适合一般交互、演示和批量回归；
- orchestrated：证据控制更严格，适合高风险问答与审计；
- 当前瓶颈：核心证据可达性与二轮 recovery；
- 评测范围：该回归集适用于同域工程回归和故障诊断，不代表域外泛化能力

完整逐题、检索工作流、D-full、RAGAS 与成本报告位于 [`artifacts/evaluation/`](../artifacts/evaluation/README.md)。
