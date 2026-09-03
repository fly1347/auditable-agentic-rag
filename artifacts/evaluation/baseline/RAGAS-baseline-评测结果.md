# RAGAS baseline 评测结果

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
| source_profile | baseline |
| 进入评测题数 | 29 |
| metric records | 87 |
| errors | 0 |
| llm_model | deepseek-v4-flash |
| embedding_model | BAAI/bge-small-zh-v1.5 |
| completion_transport | parallel_n1_merge |
| model_calls | 290 |
| total_tokens | 354,033 |
| estimated_cost_usd | 0.095437 |
| metric_duration_sum_s | 960.011 |

### 未进入 RAGAS 的题

| qid | reason |
| :-- | :-- |
| q02 | 该题按配置不启用 RAGAS |

## 指标汇总

| metric | valid | error | mean | median | min | max |
| :-- | --: | --: | --: | --: | --: | --: |
| context_precision | 29 | 0 | 0.8640 | 0.9500 | 0.2500 | 1.0000 |
| faithfulness | 29 | 0 | 0.9452 | 1.0000 | 0.4000 | 1.0000 |
| answer_relevancy | 29 | 0 | 0.8678 | 0.9391 | 0.5364 | 1.0000 |

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
| ContextPrecision | q01、q03、q04、q05、q07、q09、q10、q11、q13、q14、q15、q16、q17、q20、q21、q22、q24、q28、q29、q30 | q12、q18、q23、q25、q26 | q06 | q08、q19、q27 |
| Faithfulness | q01、q03、q04、q05、q06、q07、q08、q09、q10、q11、q12、q13、q14、q15、q16、q17、q18、q19、q20、q21、q22、q24、q25、q26、q29、q30 | q27 | q23 | q28 |
| AnswerRelevancy | q03、q05、q07、q10、q11、q12、q15、q16、q17、q20、q21、q22、q23、q24、q25、q27、q28、q29、q30 | q01、q06、q09、q13、q18 | q04、q08、q14、q19、q26 | — |
| 三指标同档交集 | q03、q05、q07、q10、q11、q15、q16、q17、q20、q21、q22、q24、q29、q30 | — | — | — |
| CP ∩ Faith | q01、q03、q04、q05、q07、q09、q10、q11、q13、q14、q15、q16、q17、q20、q21、q22、q24、q29、q30 | — | — | — |

### 分段题数

| 指标 | A 档 | B 档 | C 档 | D 档 |
| :-- | --: | --: | --: | --: |
| ContextPrecision | 20 | 5 | 1 | 3 |
| Faithfulness | 26 | 1 | 1 | 1 |
| AnswerRelevancy | 19 | 5 | 5 | 0 |
| 三指标同档交集 | 14 | 0 | 0 | 0 |
| CP ∩ Faith | 19 | 0 | 0 | 0 |

## 低分题索引

> 这里只按分数从低到高列出每项最低 5 题，帮助快速定位；未设置人为 PASS / FAIL 阈值。

| metric | lowest 5 |
| :-- | :-- |
| context_precision | q19=0.2500；q08=0.4167；q27=0.4500；q06=0.5000；q25=0.7000 |
| faithfulness | q28=0.4000；q23=0.6364；q27=0.7143；q04=0.8571；q15=0.8571 |
| answer_relevancy | q26=0.5364；q08=0.5806；q04=0.6351；q14=0.6354；q19=0.6788 |

## 逐题三指标

| qid | context_precision | faithfulness | answer_relevancy |
| :-- | --: | --: | --: |
| q01 | 1.0000 | 1.0000 | 0.8003 |
| q03 | 0.9167 | 1.0000 | 0.8553 |
| q04 | 0.9167 | 0.8571 | 0.6351 |
| q05 | 0.9167 | 1.0000 | 0.8469 |
| q06 | 0.5000 | 1.0000 | 0.7772 |
| q07 | 1.0000 | 1.0000 | 1.0000 |
| q08 | 0.4167 | 1.0000 | 0.5806 |
| q09 | 1.0000 | 1.0000 | 0.8226 |
| q10 | 1.0000 | 1.0000 | 0.9424 |
| q11 | 1.0000 | 1.0000 | 0.9939 |
| q12 | 0.7500 | 1.0000 | 1.0000 |
| q13 | 1.0000 | 1.0000 | 0.7392 |
| q14 | 0.9167 | 1.0000 | 0.6354 |
| q15 | 1.0000 | 0.8571 | 0.9461 |
| q16 | 1.0000 | 1.0000 | 0.9417 |
| q17 | 1.0000 | 0.9444 | 0.8805 |
| q18 | 0.8333 | 1.0000 | 0.7832 |
| q19 | 0.2500 | 1.0000 | 0.6788 |
| q20 | 1.0000 | 1.0000 | 0.9354 |
| q21 | 0.9167 | 1.0000 | 0.9884 |
| q22 | 0.9500 | 1.0000 | 1.0000 |
| q23 | 0.8667 | 0.6364 | 1.0000 |
| q24 | 1.0000 | 1.0000 | 0.9832 |
| q25 | 0.7000 | 1.0000 | 0.9884 |
| q26 | 0.8056 | 1.0000 | 0.5364 |
| q27 | 0.4500 | 0.7143 | 0.9504 |
| q28 | 1.0000 | 0.4000 | 0.9898 |
| q29 | 0.9500 | 1.0000 | 0.9391 |
| q30 | 1.0000 | 1.0000 | 0.9957 |

## 各指标评测资源消耗

| metric | records | model_calls | duration_sum_s | total_tokens | estimated_cost_usd |
| :-- | --: | --: | --: | --: | --: |
| context_precision | 29 | 145 | 433.672 | 191,546 | 0.027872 |
| faithfulness | 29 | 58 | 311.342 | 117,677 | 0.057566 |
| answer_relevancy | 29 | 87 | 214.996 | 44,810 | 0.009999 |

## 机器底账

- `ragas_evaluation_records.jsonl`：逐题逐指标事实记录。
- `tables/ragas_results.csv`：逐题逐指标扁平表。
- `tables/model_calls.csv`：每次 evaluator 模型调用。
- `tables/cost_ledger.csv`：逐题逐指标 Token / Cost 分账。
- `tables/ragas_evaluation_segments.json`：A/B/C/D 分段、逐题档位与交集底账。
