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
| 进入评测题数 | 27 |
| metric records | 81 |
| errors | 0 |
| llm_model | deepseek-v4-flash |
| embedding_model | BAAI/bge-small-zh-v1.5 |
| completion_transport | parallel_n1_merge |
| model_calls | 270 |
| total_tokens | 330,350 |
| estimated_cost_usd | 0.077286 |
| metric_duration_sum_s | 1074.975 |

### 未进入 RAGAS 的题

| qid | reason |
| :-- | :-- |
| q02 | 该题按配置不启用 RAGAS |
| q28 | 主链未产生 ANSWERED 结果 |
| q30 | 主链未产生 ANSWERED 结果 |

## 指标汇总

| metric | valid | error | mean | median | min | max |
| :-- | --: | --: | --: | --: | --: | --: |
| context_precision | 27 | 0 | 0.8197 | 0.9167 | 0.2000 | 1.0000 |
| faithfulness | 27 | 0 | 0.9562 | 1.0000 | 0.6875 | 1.0000 |
| answer_relevancy | 27 | 0 | 0.8468 | 0.8607 | 0.5806 | 1.0000 |

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
| ContextPrecision | q03、q04、q05、q07、q09、q10、q11、q14、q15、q16、q18、q20、q21、q22、q24、q29 | q01、q12、q13、q23、q25、q26 | q06、q17 | q08、q19、q27 |
| Faithfulness | q01、q03、q05、q06、q07、q08、q09、q10、q12、q13、q14、q15、q16、q18、q19、q20、q21、q22、q23、q24、q25、q26、q29 | q04、q11、q27 | q17 | — |
| AnswerRelevancy | q03、q05、q07、q11、q12、q13、q15、q17、q20、q21、q22、q23、q24、q25、q27、q29 | q01、q04、q06、q09、q16、q18 | q08、q10、q14、q19、q26 | — |
| 三指标同档交集 | q03、q05、q07、q15、q20、q21、q22、q24、q29 | — | — | — |
| CP ∩ Faith | q03、q05、q07、q09、q10、q14、q15、q16、q18、q20、q21、q22、q24、q29 | — | q17 | — |

### 分段题数

| 指标 | A 档 | B 档 | C 档 | D 档 |
| :-- | --: | --: | --: | --: |
| ContextPrecision | 16 | 6 | 2 | 3 |
| Faithfulness | 23 | 3 | 1 | 0 |
| AnswerRelevancy | 16 | 6 | 5 | 0 |
| 三指标同档交集 | 9 | 0 | 0 | 0 |
| CP ∩ Faith | 14 | 0 | 1 | 0 |

## 低分题索引

> 这里只按分数从低到高列出每项最低 5 题，帮助快速定位；未设置人为 PASS / FAIL 阈值。

| metric | lowest 5 |
| :-- | :-- |
| context_precision | q27=0.2000；q19=0.2500；q08=0.4167；q06=0.5000；q17=0.5000 |
| faithfulness | q17=0.6875；q27=0.7273；q04=0.8333；q11=0.8333；q23=0.8571 |
| answer_relevancy | q08=0.5806；q26=0.6211；q10=0.6235；q14=0.6343；q19=0.6785 |

## 逐题三指标

| qid | context_precision | faithfulness | answer_relevancy |
| :-- | --: | --: | --: |
| q01 | 0.8333 | 0.9615 | 0.8003 |
| q03 | 0.9167 | 1.0000 | 0.8553 |
| q04 | 0.9167 | 0.8333 | 0.7537 |
| q05 | 0.9167 | 1.0000 | 0.8607 |
| q06 | 0.5000 | 1.0000 | 0.7772 |
| q07 | 1.0000 | 1.0000 | 1.0000 |
| q08 | 0.4167 | 1.0000 | 0.5806 |
| q09 | 1.0000 | 1.0000 | 0.7564 |
| q10 | 1.0000 | 1.0000 | 0.6235 |
| q11 | 1.0000 | 0.8333 | 0.9959 |
| q12 | 0.7500 | 1.0000 | 1.0000 |
| q13 | 0.8056 | 1.0000 | 0.8573 |
| q14 | 0.9167 | 1.0000 | 0.6343 |
| q15 | 1.0000 | 1.0000 | 0.9507 |
| q16 | 1.0000 | 1.0000 | 0.7326 |
| q17 | 0.5000 | 0.6875 | 0.8805 |
| q18 | 1.0000 | 1.0000 | 0.7111 |
| q19 | 0.2500 | 1.0000 | 0.6785 |
| q20 | 1.0000 | 1.0000 | 0.9354 |
| q21 | 0.9167 | 1.0000 | 0.9884 |
| q22 | 0.9500 | 0.9167 | 1.0000 |
| q23 | 0.8875 | 0.8571 | 1.0000 |
| q24 | 1.0000 | 1.0000 | 0.9568 |
| q25 | 0.7000 | 1.0000 | 0.9744 |
| q26 | 0.8056 | 1.0000 | 0.6211 |
| q27 | 0.2000 | 0.7273 | 0.9991 |
| q29 | 0.9500 | 1.0000 | 0.9391 |

## 各指标评测资源消耗

| metric | records | model_calls | duration_sum_s | total_tokens | estimated_cost_usd |
| :-- | --: | --: | --: | --: | --: |
| context_precision | 27 | 135 | 481.622 | 178,620 | 0.018087 |
| faithfulness | 27 | 54 | 333.394 | 110,135 | 0.050434 |
| answer_relevancy | 27 | 81 | 259.958 | 41,595 | 0.008764 |

## 机器底账

- `ragas_evaluation_records.jsonl`：逐题逐指标事实记录。
- `tables/ragas_results.csv`：逐题逐指标扁平表。
- `tables/model_calls.csv`：每次 evaluator 模型调用。
- `tables/cost_ledger.csv`：逐题逐指标 Token / Cost 分账。
- `tables/ragas_evaluation_segments.json`：A/B/C/D 分段、逐题档位与交集底账。
