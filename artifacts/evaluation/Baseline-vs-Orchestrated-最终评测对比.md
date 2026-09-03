# Baseline vs Orchestrated 最终评测对比

> 本报告只读取两套冻结评测机器底账，零模型调用。RAGAS 同时给出各 profile 原始统计与共同题集（matched cohort）统计；由于 orchestrated 会把证据不足题挡在 RAGAS 之外，跨 profile 质量结论优先看共同题集。

## 结论先看

| 观察项 | baseline | orchestrated | 变化 |
| :-- | --: | --: | --: |
| 在线主链 estimated cost | $0.036531 | $0.073633 | +101.6% |
| 在线主链 total tokens | 123,627 | 190,941 | +54.4% |
| 在线主链 service time sum | 137.674 s | 194.988 s | +41.6% |
| 最终拒答题 | 1 | 3 | +2 |
| 二轮 sufficiency 题 | 1 | 5 | +4 |
| RAGAS ContextPrecision 共同题均值 | 0.8539 | 0.8197 | -0.0342 |
| RAGAS Faithfulness 共同题均值 | 0.9633 | 0.9562 | -0.0071 |
| RAGAS AnswerRelevancy 共同题均值 | 0.8585 | 0.8468 | -0.0118 |
| 全套 evaluation estimated cost | $0.134604 | $0.153556 | +14.1% |

### 发生控制结果变化的题

- 最终 ANSWERED / REFUSED 状态变化：q28、q30
- actual_route 变化：无
- baseline 最终证据不足：q02
- orchestrated 最终证据不足：q02、q28、q30

## 1. 主链控制结果

| signal | baseline | orchestrated |
| :-- | :-- | :-- |
| cases | 30 | 30 |
| ANSWERED | 29 | 27 |
| REFUSED | 1（q02） | 3（q02、q28、q30） |
| DIRECT | 24 | 24 |
| DECOMPOSE | 6 | 6 |
| second sufficiency / reretrieve | 1（q02） | 5（q02、q17、q27、q28、q30） |
| final insufficiency | 1（q02） | 3（q02、q28、q30） |
| prompt_evidence fail | 2（q06、q27） | 4（q06、q27、q28、q30） |

## 2. 在线主链性能与成本

> service time 为 30 题逐题 `service_total_ms` 的统计；sum 是题级耗时求和，不等同于批任务真实墙钟时长。

| metric | baseline | orchestrated | delta / ratio |
| :-- | --: | --: | --: |
| service time sum | 137.674 s | 194.988 s | +41.6% |
| service time mean | 4.589 s | 6.500 s | +41.6% |
| service time median | 3.891 s | 5.864 s | +50.7% |
| service time p95 | 9.325 s | 12.762 s | +36.9% |
| model calls | 67 | 73 | +9.0% |
| total tokens | 123,627 | 190,941 | +54.4% |
| estimated cost | $0.036531 | $0.073633 | +101.6% |

### 在线模型角色成本分解

| role | baseline calls | orchestrated calls | baseline tokens | orchestrated tokens | baseline cost | orchestrated cost |
| :-- | --: | --: | --: | --: | --: | --: |
| generator | 29 | 27 | 69,226 | 64,413 | $0.012632 | $0.011723 |
| rewrite_query | 1 | 5 | 75 | 401 | $0.000016 | $0.000089 |
| subquery_generator | 6 | 6 | 685 | 678 | $0.000171 | $0.000167 |
| sufficiency_judge | 31 | 35 | 53,641 | 125,449 | $0.023713 | $0.061654 |

## 3. Sufficiency Judge 代价

> 这里只拆主链中 `role=sufficiency_judge` 的真实模型调用；baseline 为 binary，orchestrated 为 structured。

| metric | baseline | orchestrated | delta / ratio |
| :-- | :-- | :-- | :-- |
| mode | binary=30 | structured=30 | — |
| judge calls | 31 | 35 | +12.9% |
| second-round cases | 1（q02） | 5（q02、q17、q27、q28、q30） | — |
| provider latency sum | 17.770 s | 69.203 s | +289.4% |
| prompt tokens | 53,515 | 118,112 | +120.7% |
| completion tokens | 126 | 7,337 | +5723.0% |
| total tokens | 53,641 | 125,449 | +133.9% |
| estimated cost | $0.023713 | $0.061654 | +160.0% |

## 4. D-full 后置诊断

> D-full classifier 是独立 LLM 后置诊断，不作为 baseline / orchestrated 质量胜负项；这里重点比较与最终答案和证据直接相关的 Citation Support、Conflict、Uncertainty。

### Citation Support

| label | baseline | orchestrated |
| :-- | --: | --: |
| no_evidence | 1 | 0 |
| not_applicable | 1 | 3 |
| partial | 25 | 24 |
| supported | 1 | 1 |
| unsupported | 2 | 2 |

- **unsupported_claim_count > 0**：
  - baseline：16 题（q01、q03、q04、q05、q07、q11、q12、q13、q14、q16、q17、q18、q20、q21、q23、q25）
  - orchestrated：15 题（q01、q03、q04、q05、q07、q12、q13、q14、q16、q17、q18、q20、q21、q23、q25）

- **conflict_count > 0**：
  - baseline：0 题（无）
  - orchestrated：0 题（无）

### Uncertainty

> `high` 表示不确定性/风险高；`low` 表示不确定性/风险低。

| level | baseline | orchestrated |
| :-- | --: | --: |
| low | 1 | 1 |
| medium | 12 | 11 |
| high | 17 | 18 |

#### 各等级题号

| level | baseline qids | orchestrated qids |
| :-- | :-- | :-- |
| low | q24 | q24 |
| medium | q06、q08、q09、q10、q15、q19、q22、q26、q27、q28、q29、q30 | q06、q08、q09、q10、q11、q15、q19、q22、q26、q27、q29 |
| high | q01、q02、q03、q04、q05、q07、q11、q12、q13、q14、q16、q17、q18、q20、q21、q23、q25 | q01、q02、q03、q04、q05、q07、q12、q13、q14、q16、q17、q18、q20、q21、q23、q25、q28、q30 |

#### Uncertainty 等级发生变化的题

| qid | baseline | orchestrated | direction |
| :-- | :-: | :-: | :-- |
| q11 | high | medium | 不确定性下降 |
| q28 | medium | high | 不确定性上升 |
| q30 | medium | high | 不确定性上升 |

## 5. RAGAS 质量对比

> orchestrated 对证据不足题先拒答，因此进入 RAGAS 的题数少于 baseline。各 profile 全量均值用于描述各自实际评测集；跨 profile 的质量变化优先看共同题集，避免把“跳过难题”误当成质量提升。A/B/C/D 为本项目工程分档，不是 RAGAS 官方等级。

### 参与范围

- baseline 进入 RAGAS：29 题；跳过：q02。
- orchestrated 进入 RAGAS：27 题；跳过：q02、q28、q30。
- 两套共同可比题：27 题。

### Orchestrated 新增拒答题回看 baseline 质量信号

> 这些题在 baseline 中回答、在 orchestrated 中因最终证据不足被拒答。这里回看 baseline 当时已有的 RAGAS 与 D-full 信号，帮助判断更严格的控制实际挡住了什么。

| qid | CP | Faith | AR | baseline citation | baseline uncertainty |
| :-- | :-- | :-- | :-- | :-- | :-- |
| q28 | 1.0000 / A | 0.4000 / D | 0.9898 / A | partial | medium |
| q30 | 1.0000 / A | 1.0000 / A | 0.9957 / A | partial | medium |

### 各 profile 原始均值

| metric | baseline n | baseline mean | orchestrated n | orchestrated mean |
| :-- | --: | --: | --: | --: |
| ContextPrecision | 29 | 0.8640 | 27 | 0.8197 |
| Faithfulness | 29 | 0.9452 | 27 | 0.9562 |
| AnswerRelevancy | 29 | 0.8678 | 27 | 0.8468 |

### 共同题集均值与分档迁移

| metric | shared n | baseline mean | orchestrated mean | mean delta | 升档 | 同档 | 降档 |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| ContextPrecision | 27 | 0.8539 | 0.8197 | -0.0342 | 1 | 23 | 3 |
| Faithfulness | 27 | 0.9633 | 0.9562 | -0.0071 | 1 | 23 | 3 |
| AnswerRelevancy | 27 | 0.8585 | 0.8468 | -0.0118 | 2 | 23 | 2 |

### 分档发生变化的题

#### ContextPrecision

| qid | baseline | orchestrated | score delta | direction |
| :-- | :-: | :-: | --: | :-- |
| q18 | B | A | +0.1667 | 升档 |
| q01 | A | B | -0.1667 | 降档 |
| q13 | A | B | -0.1944 | 降档 |
| q17 | A | C | -0.5000 | 降档 |

#### Faithfulness

| qid | baseline | orchestrated | score delta | direction |
| :-- | :-: | :-: | --: | :-- |
| q23 | C | A | +0.2208 | 升档 |
| q04 | A | B | -0.0238 | 降档 |
| q11 | A | B | -0.1667 | 降档 |
| q17 | A | C | -0.2569 | 降档 |

#### AnswerRelevancy

| qid | baseline | orchestrated | score delta | direction |
| :-- | :-: | :-: | --: | :-- |
| q04 | C | B | +0.1186 | 升档 |
| q13 | B | A | +0.1181 | 升档 |
| q10 | A | C | -0.3190 | 降档 |
| q16 | A | B | -0.2091 | 降档 |

### 共同题集分数变化 Top 5

- **ContextPrecision 最大提升**：q18 +0.1667；q23 +0.0208
- **ContextPrecision 最大下降**：q17 -0.5000；q27 -0.2500；q13 -0.1944；q01 -0.1667
- **Faithfulness 最大提升**：q23 +0.2208；q15 +0.1429；q27 +0.0130
- **Faithfulness 最大下降**：q17 -0.2569；q11 -0.1667；q22 -0.0833；q01 -0.0385；q04 -0.0238
- **AnswerRelevancy 最大提升**：q04 +0.1186；q13 +0.1181；q26 +0.0847；q27 +0.0486；q05 +0.0138
- **AnswerRelevancy 最大下降**：q10 -0.3190；q16 -0.2091；q18 -0.0721；q09 -0.0662；q24 -0.0264

## 6. Evaluation 三类总账对比

> `time_sum` 是各题 / 各指标任务耗时求和，不等同于整批任务真实墙钟时间。RAGAS 两套参与题数不同，因此 combined 总成本同时受运行策略和 RAGAS 题数变化影响。

| category | baseline calls | orchestrated calls | baseline tokens | orchestrated tokens | baseline cost | orchestrated cost | cost delta |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| 在线主链 | 67 | 73 | 123,627 | 190,941 | $0.036531 | $0.073633 | +101.6% |
| D-full 后置评测 | 30 | 30 | 12,847 | 12,849 | $0.002636 | $0.002637 | +0.0% |
| RAGAS 离线质量评测 | 290 | 270 | 354,033 | 330,350 | $0.095437 | $0.077286 | -19.0% |
| 三类合计 | 387 | 373 | 490,507 | 534,140 | $0.134604 | $0.153556 | +14.1% |

## 7. 多花了什么，换来了什么

| 维度 | 事实变化 |
| :-- | :-- |
| 在线成本 | orchestrated 相比 baseline +101.6%；$0.036531 → $0.073633 |
| 在线 Token | 123,627 → 190,941（+54.4%） |
| 在线题级耗时总和 | 137.674 s → 194.988 s（+41.6%） |
| Sufficiency Judge | 31 → 35 calls；$0.023713 → $0.061654 |
| 控制结果 | 最终拒答 1 → 3；新增/变化题：q28、q30 |
| RAGAS ContextPrecision（共同题） | mean 0.8539 → 0.8197 (-0.0342)；升档 1，降档 3 |
| RAGAS Faithfulness（共同题） | mean 0.9633 → 0.9562 (-0.0071)；升档 1，降档 3 |
| RAGAS AnswerRelevancy（共同题） | mean 0.8585 → 0.8468 (-0.0118)；升档 2，降档 2 |
| 全套评测成本 | $0.134604 → $0.153556（+14.1%）；注意 RAGAS 参与题数 29 → 27 |

> 本报告不合成一个“总质量分”。控制收益、RAGAS 质量信号与资源代价分别保留，便于按工程目标做取舍。

## 机器底账

- baseline: `artifacts/phase_f_review/final-evaluation/dense-hybrid-main-20260903-211042/hybrid_rrf/baseline`
- orchestrated: `artifacts/phase_f_review/final-evaluation/dense-hybrid-main-20260903-211042/hybrid_rrf/orchestrated`
- 逐题对比 CSV：`tables/baseline_vs_orchestrated_per_case.csv`
- 结构化对比 JSON：`baseline_vs_orchestrated_comparison.json`
