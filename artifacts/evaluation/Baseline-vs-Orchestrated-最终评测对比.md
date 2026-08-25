# Baseline vs Orchestrated 最终评测对比

> 本报告只读取两套冻结评测机器底账，零模型调用。RAGAS 同时给出各 profile 原始统计与共同题集（matched cohort）统计；由于 orchestrated 会把证据不足题挡在 RAGAS 之外，跨 profile 质量结论优先看共同题集。

## 结论先看

| 观察项 | baseline | orchestrated | 变化 |
| :-- | --: | --: | --: |
| 在线主链 estimated cost | $0.035468 | $0.073791 | +108.0% |
| 在线主链 total tokens | 119,756 | 188,062 | +57.0% |
| 在线主链 service time sum | 124.334 s | 167.940 s | +35.1% |
| 最终拒答题 | 1 | 5 | +4 |
| 二轮 sufficiency 题 | 1 | 5 | +4 |
| RAGAS ContextPrecision 共同题均值 | 0.8734 | 0.9066 | +0.0331 |
| RAGAS Faithfulness 共同题均值 | 0.9691 | 0.9422 | -0.0269 |
| RAGAS AnswerRelevancy 共同题均值 | 0.8673 | 0.8303 | -0.0370 |
| 全套 evaluation estimated cost | $0.154081 | $0.149048 | -3.3% |

### 发生控制结果变化的题

- 最终 ANSWERED / REFUSED 状态变化：q06、q19、q27、q28
- actual_route 变化：无
- baseline 最终证据不足：q02
- orchestrated 最终证据不足：q02、q06、q19、q27、q28

## 1. 主链控制结果

| signal | baseline | orchestrated |
| :-- | :-- | :-- |
| cases | 30 | 30 |
| ANSWERED | 29 | 25 |
| REFUSED | 1（q02） | 5（q02、q06、q19、q27、q28） |
| DIRECT | 24 | 24 |
| DECOMPOSE | 6 | 6 |
| second sufficiency / reretrieve | 1（q02） | 5（q02、q06、q19、q27、q28） |
| final insufficiency | 1（q02） | 5（q02、q06、q19、q27、q28） |
| prompt_evidence fail | 1（q26） | 5（q06、q19、q26、q27、q28） |

## 2. 在线主链性能与成本

> service time 为 30 题逐题 `service_total_ms` 的统计；sum 是题级耗时求和，不等同于批任务真实墙钟时长。

| metric | baseline | orchestrated | delta / ratio |
| :-- | --: | --: | --: |
| service time sum | 124.334 s | 167.940 s | +35.1% |
| service time mean | 4.144 s | 5.598 s | +35.1% |
| service time median | 3.555 s | 5.173 s | +45.5% |
| service time p95 | 7.843 s | 9.265 s | +18.1% |
| model calls | 67 | 71 | +6.0% |
| total tokens | 119,756 | 188,062 | +57.0% |
| estimated cost | $0.035468 | $0.073791 | +108.0% |

### 在线模型角色成本分解

| role | baseline calls | orchestrated calls | baseline tokens | orchestrated tokens | baseline cost | orchestrated cost |
| :-- | --: | --: | --: | --: | --: | --: |
| generator | 29 | 25 | 67,034 | 58,078 | $0.012309 | $0.010703 |
| rewrite_query | 1 | 5 | 76 | 390 | $0.000016 | $0.000085 |
| subquery_generator | 6 | 6 | 678 | 690 | $0.000167 | $0.000174 |
| sufficiency_judge | 31 | 35 | 51,968 | 128,904 | $0.022977 | $0.062828 |

## 3. Sufficiency Judge 代价

> 这里只拆主链中 `role=sufficiency_judge` 的真实模型调用；baseline 为 binary，orchestrated 为 structured。

| metric | baseline | orchestrated | delta / ratio |
| :-- | :-- | :-- | :-- |
| mode | binary=30 | structured=30 | — |
| judge calls | 31 | 35 | +12.9% |
| second-round cases | 1（q02） | 5（q02、q06、q19、q27、q28） | — |
| provider latency sum | 22.933 s | 70.690 s | +208.2% |
| prompt tokens | 51,842 | 121,960 | +135.3% |
| completion tokens | 126 | 6,944 | +5411.1% |
| total tokens | 51,968 | 128,904 | +148.0% |
| estimated cost | $0.022977 | $0.062828 | +173.4% |

## 4. D-full 后置诊断

> D-full classifier 是独立 LLM 后置诊断，不作为 baseline / orchestrated 质量胜负项；这里重点比较与最终答案和证据直接相关的 Citation Support、Conflict、Uncertainty。

### Citation Support

| label | baseline | orchestrated |
| :-- | --: | --: |
| not_applicable | 1 | 5 |
| partial | 26 | 23 |
| supported | 1 | 0 |
| unsupported | 2 | 2 |

- **unsupported_claim_count > 0**：
  - baseline：12 题（q01、q03、q05、q06、q12、q13、q14、q16、q17、q21、q23、q25）
  - orchestrated：13 题（q01、q03、q05、q12、q13、q14、q16、q17、q20、q21、q23、q25、q26）

- **conflict_count > 0**：
  - baseline：0 题（无）
  - orchestrated：0 题（无）

### Uncertainty

> `high` 表示不确定性/风险高；`low` 表示不确定性/风险低。

| level | baseline | orchestrated |
| :-- | --: | --: |
| low | 1 | 0 |
| medium | 16 | 12 |
| high | 13 | 18 |

#### 各等级题号

| level | baseline qids | orchestrated qids |
| :-- | :-- | :-- |
| low | q24 | 无 |
| medium | q04、q07、q08、q09、q10、q11、q15、q18、q19、q20、q22、q26、q27、q28、q29、q30 | q04、q07、q08、q09、q10、q11、q15、q18、q22、q24、q29、q30 |
| high | q01、q02、q03、q05、q06、q12、q13、q14、q16、q17、q21、q23、q25 | q01、q02、q03、q05、q06、q12、q13、q14、q16、q17、q19、q20、q21、q23、q25、q26、q27、q28 |

#### Uncertainty 等级发生变化的题

| qid | baseline | orchestrated | direction |
| :-- | :-: | :-: | :-- |
| q19 | medium | high | 不确定性上升 |
| q20 | medium | high | 不确定性上升 |
| q24 | low | medium | 不确定性上升 |
| q26 | medium | high | 不确定性上升 |
| q27 | medium | high | 不确定性上升 |
| q28 | medium | high | 不确定性上升 |

## 5. RAGAS 质量对比

> orchestrated 对证据不足题先拒答，因此进入 RAGAS 的题数少于 baseline。各 profile 全量均值用于描述各自实际评测集；跨 profile 的质量变化优先看共同题集，避免把“跳过难题”误当成质量提升。A/B/C/D 为本项目工程分档，不是 RAGAS 官方等级。

### 参与范围

- baseline 进入 RAGAS：29 题；跳过：q02。
- orchestrated 进入 RAGAS：25 题；跳过：q02、q06、q19、q27、q28。
- 两套共同可比题：25 题。

### Orchestrated 新增拒答题回看 baseline 质量信号

> 这些题在 baseline 中回答、在 orchestrated 中因最终证据不足被拒答。这里回看 baseline 当时已有的 RAGAS 与 D-full 信号，帮助判断更严格的控制实际挡住了什么。

| qid | CP | Faith | AR | baseline citation | baseline uncertainty |
| :-- | :-- | :-- | :-- | :-- | :-- |
| q06 | 0.0000 / D | 0.3750 / D | 0.7712 / B | partial | high |
| q19 | 0.0000 / D | 0.2000 / D | 0.7129 / B | partial | medium |
| q27 | 0.3333 / D | 0.2857 / D | 0.9005 / A | partial | medium |
| q28 | 1.0000 / A | 0.4000 / D | 0.9180 / A | partial | medium |

### 各 profile 原始均值

| metric | baseline n | baseline mean | orchestrated n | orchestrated mean |
| :-- | --: | --: | --: | --: |
| ContextPrecision | 29 | 0.7989 | 25 | 0.9066 |
| Faithfulness | 29 | 0.8789 | 25 | 0.9422 |
| AnswerRelevancy | 29 | 0.8615 | 25 | 0.8303 |

### 共同题集均值与分档迁移

| metric | shared n | baseline mean | orchestrated mean | mean delta | 升档 | 同档 | 降档 |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| ContextPrecision | 25 | 0.8734 | 0.9066 | +0.0331 | 3 | 22 | 0 |
| Faithfulness | 25 | 0.9691 | 0.9422 | -0.0269 | 0 | 22 | 3 |
| AnswerRelevancy | 25 | 0.8673 | 0.8303 | -0.0370 | 1 | 20 | 4 |

### 分档发生变化的题

#### ContextPrecision

| qid | baseline | orchestrated | score delta | direction |
| :-- | :-: | :-: | --: | :-- |
| q01 | C | A | +0.4167 | 升档 |
| q12 | B | A | +0.1667 | 升档 |
| q13 | B | A | +0.2444 | 升档 |

#### Faithfulness

| qid | baseline | orchestrated | score delta | direction |
| :-- | :-: | :-: | --: | :-- |
| q05 | A | C | -0.3077 | 降档 |
| q23 | A | C | -0.3571 | 降档 |
| q25 | A | C | -0.3077 | 降档 |

#### AnswerRelevancy

| qid | baseline | orchestrated | score delta | direction |
| :-- | :-: | :-: | --: | :-- |
| q13 | B | A | +0.1057 | 升档 |
| q10 | B | C | -0.1303 | 降档 |
| q16 | B | C | -0.2095 | 降档 |
| q17 | B | C | -0.1053 | 降档 |
| q20 | A | C | -0.2707 | 降档 |

### 共同题集分数变化 Top 5

- **ContextPrecision 最大提升**：q01 +0.4167；q13 +0.2444；q12 +0.1667
- **ContextPrecision 最大下降**：无负向变化
- **Faithfulness 最大提升**：q11 +0.1000；q13 +0.1000；q21 +0.0625；q17 +0.0556
- **Faithfulness 最大下降**：q23 -0.3571；q05 -0.3077；q25 -0.3077；q04 -0.0179
- **AnswerRelevancy 最大提升**：q13 +0.1057；q25 +0.0046；q21 +0.0028；q24 +0.0022
- **AnswerRelevancy 最大下降**：q20 -0.2707；q16 -0.2095；q26 -0.1805；q10 -0.1303；q17 -0.1053

## 6. Evaluation 三类总账对比

> `time_sum` 是各题 / 各指标任务耗时求和，不等同于整批任务真实墙钟时间。RAGAS 两套参与题数不同，因此 combined 总成本同时受运行策略和 RAGAS 题数变化影响。

| category | baseline calls | orchestrated calls | baseline tokens | orchestrated tokens | baseline cost | orchestrated cost | cost delta |
| :-- | --: | --: | --: | --: | --: | --: | --: |
| 在线主链 | 67 | 71 | 119,756 | 188,062 | $0.035468 | $0.073791 | +108.0% |
| D-full 后置评测 | 30 | 30 | 12,858 | 12,866 | $0.002642 | $0.002647 | +0.2% |
| RAGAS 离线质量评测 | 290 | 250 | 350,482 | 303,979 | $0.115970 | $0.072610 | -37.4% |
| 三类合计 | 387 | 351 | 483,096 | 504,907 | $0.154081 | $0.149048 | -3.3% |

## 7. 多花了什么，换来了什么

| 维度 | 事实变化 |
| :-- | :-- |
| 在线成本 | orchestrated 相比 baseline +108.0%；$0.035468 → $0.073791 |
| 在线 Token | 119,756 → 188,062（+57.0%） |
| 在线题级耗时总和 | 124.334 s → 167.940 s（+35.1%） |
| Sufficiency Judge | 31 → 35 calls；$0.022977 → $0.062828 |
| 控制结果 | 最终拒答 1 → 5；新增/变化题：q06、q19、q27、q28 |
| RAGAS ContextPrecision（共同题） | mean 0.8734 → 0.9066 (+0.0331)；升档 3，降档 0 |
| RAGAS Faithfulness（共同题） | mean 0.9691 → 0.9422 (-0.0269)；升档 0，降档 3 |
| RAGAS AnswerRelevancy（共同题） | mean 0.8673 → 0.8303 (-0.0370)；升档 1，降档 4 |
| 全套评测成本 | $0.154081 → $0.149048（-3.3%）；注意 RAGAS 参与题数 29 → 25 |

> 本报告不合成一个“总质量分”。控制收益、RAGAS 质量信号与资源代价分别保留，便于按工程目标做取舍。

## 机器底账

- baseline: `artifacts/phase_f_review/final-evaluation/baseline-rerun-20260822`
- orchestrated: `artifacts/phase_f_review/final-evaluation/orchestrated-full-rerun-20260822-01`
- 逐题对比 CSV：`tables/baseline_vs_orchestrated_per_case.csv`
- 结构化对比 JSON：`baseline_vs_orchestrated_comparison.json`
