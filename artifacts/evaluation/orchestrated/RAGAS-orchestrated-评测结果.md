# RAGAS orchestrated 评测结果

> 本报告只整理既有 `ragas_evaluation_records.jsonl`，不重新执行 RAGAS。分数越高通常越好；RAGAS 是辅助质量评估，不单独作为最终 PASS / FAIL 门禁。

## 三项指标怎么读

| metric | 主要看什么 | 读取重点 |
| :-- | :-- | :-- |
| `context_precision` | 检索上下文中与 reference 相关的证据是否更靠前 | 低分优先检查检索排序、无关 context 占位 |
| `faithfulness` | 回答中的陈述能否由 RAGAS 实际使用的 contexts 支撑 | 低分表示回答更可能脱离已给证据；最接近‘基于证据的幻觉’检查 |
| `answer_relevancy` | 回答是否切中用户问题 | 低分表示答非所问或回答重点偏移；不等同于事实正确性 |

## 批次信息

| field | value |
| :-- | :-- |
| source_profile | orchestrated |
| 进入评测题数 | 25 |
| metric records | 75 |
| errors | 0 |
| llm_model | deepseek-v4-flash |
| embedding_model | BAAI/bge-small-zh-v1.5 |
| completion_transport | parallel_n1_merge |
| model_calls | 250 |
| total_tokens | 303,979 |
| estimated_cost_usd | 0.072610 |
| metric_duration_sum_s | 1033.441 |

### 未进入 RAGAS 的题

| qid | reason |
| :-- | :-- |
| q02 | 该题按配置不启用 RAGAS |
| q06 | 主链未产生 ANSWERED 结果 |
| q19 | 主链未产生 ANSWERED 结果 |
| q27 | 主链未产生 ANSWERED 结果 |
| q28 | 主链未产生 ANSWERED 结果 |

## 指标汇总

| metric | valid | error | mean | median | min | max |
| :-- | --: | --: | --: | --: | --: | --: |
| context_precision | 25 | 0 | 0.9066 | 1.0000 | 0.2500 | 1.0000 |
| faithfulness | 25 | 0 | 0.9422 | 1.0000 | 0.5000 | 1.0000 |
| answer_relevancy | 25 | 0 | 0.8303 | 0.8760 | 0.4989 | 1.0000 |

## RAGAS 分段评估

> A/B/C/D 是本项目用于结果分层与问题定位的工程判档规则，不是 RAGAS 官方等级。实际判档前先将原始分数四舍五入到两位小数。

### 分段标准

| 档位 | 简称 | ContextPrecision | Faithfulness | AnswerRelevancy |
| :-: | :--: | :--: | :--: | :--: |
| A | 优 | ≥ 0.90 | ≥ 0.85 | ≥ 0.85 |
| B | 可用 | 0.70–<0.90 | 0.70–<0.85 | 0.70–<0.85 |
| C | 风险观察 | 0.50–<0.70 | 0.50–<0.70 | 0.50–<0.70 |
| D | 重点诊断 | < 0.50 | < 0.50 | < 0.50 |

### 分段详情

| 指标 | A 档 | B 档 | C 档 | D 档 |
| :-- | :-- | :-- | :-- | :-- |
| ContextPrecision | q01、q03、q04、q05、q07、q09、q10、q12、q13、q15、q16、q17、q20、q21、q22、q24、q25、q26、q29 | q14、q18、q23、q30 | — | q08、q11 |
| Faithfulness | q01、q03、q04、q07、q08、q09、q10、q11、q12、q13、q14、q15、q16、q17、q18、q20、q21、q22、q24、q26、q29、q30 | — | q05、q23、q25 | — |
| AnswerRelevancy | q01、q03、q05、q07、q11、q12、q13、q15、q18、q21、q22、q23、q24、q25、q29、q30 | — | q04、q08、q09、q10、q14、q16、q17、q20、q26 | — |
| 三指标同档交集 | q01、q03、q07、q12、q13、q15、q21、q22、q24、q29 | — | — | — |
| CP ∩ Faith | q01、q03、q04、q07、q09、q10、q12、q13、q15、q16、q17、q20、q21、q22、q24、q26、q29 | — | — | — |

### 分段题数

| 指标 | A 档 | B 档 | C 档 | D 档 |
| :-- | --: | --: | --: | --: |
| ContextPrecision | 19 | 4 | 0 | 2 |
| Faithfulness | 22 | 0 | 3 | 0 |
| AnswerRelevancy | 16 | 0 | 9 | 0 |
| 三指标同档交集 | 10 | 0 | 0 | 0 |
| CP ∩ Faith | 17 | 0 | 0 | 0 |

## 低分题索引

> 这里只按分数从低到高列出每项最低 5 题，帮助快速定位；未设置人为 PASS / FAIL 阈值。

| metric | lowest 5 |
| :-- | :-- |
| context_precision | q08=0.2500；q11=0.3250；q14=0.7500；q30=0.7500；q18=0.8056 |
| faithfulness | q23=0.5000；q05=0.6923；q25=0.6923；q04=0.8571；q15=0.8571 |
| answer_relevancy | q26=0.4989；q08=0.5503；q10=0.6043；q16=0.6291；q04=0.6325 |

## 逐题三指标

| qid | context_precision | faithfulness | answer_relevancy |
| :-- | --: | --: | --: |
| q01 | 1.0000 | 0.9565 | 0.8455 |
| q03 | 1.0000 | 1.0000 | 0.8553 |
| q04 | 1.0000 | 0.8571 | 0.6325 |
| q05 | 1.0000 | 0.6923 | 0.8592 |
| q07 | 1.0000 | 1.0000 | 1.0000 |
| q08 | 0.2500 | 1.0000 | 0.5503 |
| q09 | 1.0000 | 1.0000 | 0.6903 |
| q10 | 1.0000 | 1.0000 | 0.6043 |
| q11 | 0.3250 | 1.0000 | 0.9939 |
| q12 | 1.0000 | 1.0000 | 1.0000 |
| q13 | 1.0000 | 1.0000 | 0.9304 |
| q14 | 0.7500 | 1.0000 | 0.6331 |
| q15 | 1.0000 | 0.8571 | 0.9507 |
| q16 | 1.0000 | 1.0000 | 0.6291 |
| q17 | 1.0000 | 1.0000 | 0.6650 |
| q18 | 0.8056 | 1.0000 | 0.8760 |
| q20 | 1.0000 | 1.0000 | 0.6647 |
| q21 | 1.0000 | 1.0000 | 0.9884 |
| q22 | 1.0000 | 1.0000 | 0.9859 |
| q23 | 0.8333 | 0.5000 | 1.0000 |
| q24 | 1.0000 | 1.0000 | 0.9898 |
| q25 | 1.0000 | 0.6923 | 0.9791 |
| q26 | 1.0000 | 1.0000 | 0.4989 |
| q29 | 0.9500 | 1.0000 | 0.9391 |
| q30 | 0.7500 | 1.0000 | 0.9957 |

## 各指标评测资源消耗

| metric | records | model_calls | duration_sum_s | total_tokens | estimated_cost_usd |
| :-- | --: | --: | --: | --: | --: |
| context_precision | 25 | 125 | 464.876 | 163,636 | 0.016761 |
| faithfulness | 25 | 50 | 326.039 | 101,330 | 0.047183 |
| answer_relevancy | 25 | 75 | 242.527 | 39,013 | 0.008666 |

## 机器底账

- `ragas_evaluation_records.jsonl`：逐题逐指标事实记录。
- `tables/ragas_results.csv`：逐题逐指标扁平表。
- `tables/model_calls.csv`：每次 evaluator 模型调用。
- `tables/cost_ledger.csv`：逐题逐指标 Token / Cost 分账。
- `tables/ragas_evaluation_segments.json`：A/B/C/D 分段、逐题档位与交集底账。
