# Evaluation orchestrated Timing-Usage-Cost 三类总账

> 本报告把在线主链、D-full 后置评测、RAGAS 离线质量评测分账展示。三类模型调用互不重复；combined 只是账目求和。
> `time_sum` 是各题/各指标任务观测耗时的求和，不等同于整批任务的墙钟运行时间；RAGAS 的 3 个指标按独立任务累计。
> 费用为静态价格表估算，用于工程成本比较，不作为 provider 账单对账结果。

## 1. 总账摘要

- profile: `orchestrated`
- 去重模型调用: `0`
- 三类模型调用合计: **373 calls**
- 三类 Token 合计: **534,140**
- 三类估算费用合计: **$0.153556**
- 三类观测任务耗时累计: **1328.897 s（22.15 min）**

| 类别 | 统计对象 | records / tasks | model calls | time_sum | total tokens | estimated cost |
| :-- | :-- | --: | --: | --: | --: | --: |
| 在线主链 | 在线回答生产与主链控制调用 | 30 | 73 | 194.988 s（3.25 min） | 190,941 | $0.073633 |
| D-full 后置评测 | D-full classifier + 本地 citation/conflict/uncertainty 后置诊断 | 30 | 30 | 58.934 s | 12,849 | $0.002637 |
| RAGAS 离线质量评测 | Context Precision / Faithfulness / Answer Relevancy 指标任务 | 81 | 270 | 1074.975 s（17.92 min） | 330,350 | $0.077286 |
| **三类合计** | 以上三类互不重叠账目合计 | 141 | 373 | 1328.897 s（22.15 min） | 534,140 | $0.153556 |

### records / tasks 口径

- `online`：按在线 CER 题目计数。
- `offline_dfull`：按 D-full 后置评测题目计数。
- `ragas`：按“题目 × 指标”任务计数，因此不是参与 RAGAS 的唯一题数。
- `三类合计`：只是三个类别的记录/任务数相加，不代表唯一问题数。

## 2. 资源占比

> 这一节用于快速看成本主要花在哪里；占比均以三类合计为分母。

| 类别 | calls 占比 | Token 占比 | 费用占比 | time_sum 占比 |
| :-- | --: | --: | --: | --: |
| 在线主链 | 19.6% | 35.7% | 48.0% | 14.7% |
| D-full 后置评测 | 8.0% | 2.4% | 1.7% | 4.4% |
| RAGAS 离线质量评测 | 72.4% | 61.8% | 50.3% | 80.9% |

## 3. Token 与费用明细

| 类别 | prompt | completion | reasoning | cached | cache write | total tokens | priced / unpriced | estimated cost |
| :-- | --: | --: | --: | --: | --: | --: | :-- | --: |
| 在线主链 | 178,815 | 12,126 | not_observed | not_observed | not_observed | 190,941 | 73/0 | $0.073633 |
| D-full 后置评测 | 11,272 | 1,577 | 0 | 0 | 0 | 12,849 | 30/0 | $0.002637 |
| RAGAS 离线质量评测 | 294,369 | 35,981 | not_observed | 234,112 | not_observed | 330,350 | 270/0 | $0.077286 |
| **三类合计** | 484,456 | 49,684 | not_observed | not_observed | not_observed | 534,140 | 373/0 | $0.153556 |

## 4. 观测完整性

> Provider 未返回的 token 明细保持 unknown，不用 0 冒充真实值；完整的 `total_tokens` 与费用仍可正常用于总账。

| 类别 | time | reasoning tokens | cached tokens | cache-write tokens | cost |
| :-- | :-- | :-- | :-- | :-- | :-- |
| 在线主链 | 完整 | 部分缺失（35/73 calls 未观测） | 部分缺失（62/73 calls 未观测） | 部分缺失（62/73 calls 未观测） | 完整 |
| D-full 后置评测 | 完整 | 完整 | 完整 | 完整 | 完整 |
| RAGAS 离线质量评测 | 完整 | 部分缺失（270/270 calls 未观测） | 完整 | 部分缺失（270/270 calls 未观测） | 完整 |

## 5. 机器底账

- `evaluation_totals.csv`：三类及 combined 的完整汇总字段。
- `model_calls_combined.csv`：去重后的逐次模型调用明细。
- `manifest.json`：输入文件哈希、去重数量、combined 汇总与输出哈希。
