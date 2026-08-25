# Evaluation baseline Timing-Usage-Cost 三类总账

> 本报告把在线主链、D-full 后置评测、RAGAS 离线质量评测分账展示。三类模型调用互不重复；combined 只是账目求和。
> `time_sum` 是各题/各指标任务观测耗时的求和，不等同于整批任务的墙钟运行时间；RAGAS 的 3 个指标按独立任务累计。
> 费用为静态价格表估算，用于工程成本比较，不作为 provider 账单对账结果。

## 1. 总账摘要

- profile: `baseline`
- 去重模型调用: `0`
- 三类模型调用合计: **387 calls**
- 三类 Token 合计: **483,096**
- 三类估算费用合计: **$0.154081**
- 三类观测任务耗时累计: **1345.800 s（22.43 min）**

| 类别 | 统计对象 | records / tasks | model calls | time_sum | total tokens | estimated cost |
| :-- | :-- | --: | --: | --: | --: | --: |
| 在线主链 | 在线回答生产与主链控制调用 | 30 | 67 | 124.334 s（2.07 min） | 119,756 | $0.035468 |
| D-full 后置评测 | D-full classifier + 本地 citation/conflict/uncertainty 后置诊断 | 30 | 30 | 47.012 s | 12,858 | $0.002642 |
| RAGAS 离线质量评测 | Context Precision / Faithfulness / Answer Relevancy 指标任务 | 87 | 290 | 1174.454 s（19.57 min） | 350,482 | $0.115970 |
| **三类合计** | 以上三类互不重叠账目合计 | 147 | 387 | 1345.800 s（22.43 min） | 483,096 | $0.154081 |

### records / tasks 口径

- `online`：按在线 CER 题目计数。
- `offline_dfull`：按 D-full 后置评测题目计数。
- `ragas`：按“题目 × 指标”任务计数，因此不是参与 RAGAS 的唯一题数。
- `三类合计`：只是三个类别的记录/任务数相加，不代表唯一问题数。

## 2. 资源占比

> 这一节用于快速看成本主要花在哪里；占比均以三类合计为分母。

| 类别 | calls 占比 | Token 占比 | 费用占比 | time_sum 占比 |
| :-- | --: | --: | --: | --: |
| 在线主链 | 17.3% | 24.8% | 23.0% | 9.2% |
| D-full 后置评测 | 7.8% | 2.7% | 1.7% | 3.5% |
| RAGAS 离线质量评测 | 74.9% | 72.5% | 75.3% | 87.3% |

## 3. Token 与费用明细

| 类别 | prompt | completion | reasoning | cached | cache write | total tokens | priced / unpriced | estimated cost |
| :-- | --: | --: | --: | --: | --: | --: | :-- | --: |
| 在线主链 | 114,467 | 5,289 | not_observed | not_observed | not_observed | 119,756 | 67/0 | $0.035468 |
| D-full 后置评测 | 11,272 | 1,586 | 0 | 0 | 0 | 12,858 | 30/0 | $0.002642 |
| RAGAS 离线质量评测 | 311,341 | 39,141 | not_observed | 170,624 | not_observed | 350,482 | 290/0 | $0.115970 |
| **三类合计** | 437,080 | 46,016 | not_observed | not_observed | not_observed | 483,096 | 387/0 | $0.154081 |

## 4. 观测完整性

> Provider 未返回的 token 明细保持 unknown，不用 0 冒充真实值；完整的 `total_tokens` 与费用仍可正常用于总账。

| 类别 | time | reasoning tokens | cached tokens | cache-write tokens | cost |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 在线主链 | 完整 | 部分缺失（31/67 calls 未观测） | 部分缺失（60/67 calls 未观测） | 部分缺失（60/67 calls 未观测） | 完整 |
| D-full 后置评测 | 完整 | 完整 | 完整 | 完整 | 完整 |
| RAGAS 离线质量评测 | 完整 | 部分缺失（290/290 calls 未观测） | 完整 | 部分缺失（290/290 calls 未观测） | 完整 |

## 5. 机器底账

- `evaluation_totals.csv`：三类及 combined 的完整汇总字段。
- `model_calls_combined.csv`：去重后的逐次模型调用明细。
- `manifest.json`：输入文件哈希、去重数量、combined 汇总与输出哈希。
