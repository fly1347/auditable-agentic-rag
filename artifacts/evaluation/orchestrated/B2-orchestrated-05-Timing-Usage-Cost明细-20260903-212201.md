# B2-orchestrated Timing-Usage-Cost 明细

> 来源：当前 live CanonicalExecutionRecord（CER）确定性投影。
> `engine_ms` 已包含 `engine_init_ms`；两者分别展示，不相加作为总耗时。
> `service_unaccounted_ms = service_total_ms - queue_wait_ms - engine_ms`；`engine_observed_components_ms` 仅用于观察已记录的 engine 内部组件。
> 当前 CER 未记录独立 `merge_ms` / `build_response_ms` 时保留 `not_observed`；rerank 关闭时记为 `not_applicable`。

## 0. 运行信息

- profile: orchestrated
- cases: 30
- run_id: eval_e78ef09a941d
- index_build_id: 20260821T054541778117Z-60585827-e81a7f97
- generator: openai/gpt-4o-mini
- sufficiency_judge: deepseek-v4-flash
- cost_estimation_coverage: full=30
- price_table_version: phase_f_official_reference_2026-08-18
- provider_billing_reconciled: False
- resource_budget: not_configured

## 1. 分布摘要

| 类型 | 分布 |
| :-- | :-- |
| route | DECOMPOSE: 6；DIRECT: 24 |
| final_status | ANSWERED: 27；REFUSED: 3 |
| model_role | generator: 27；rewrite_query: 5；subquery_generator: 6；sufficiency_judge: 35 |
| provider | deepseek: 35；openrouter: 38 |
| model | deepseek-v4-flash: 35；openai/gpt-4o-mini: 38 |
| upstream_provider | Azure: 23；OpenAI: 15 |
| usage ledger | full=30/30 |

## 2. Timing 总体逐题表

| qid | route | status | service_total_ms | engine_ms | pipeline_total_ms | engine_init_ms | queue_wait_ms | observed_model_ms | retrieval_ms | engine_observed_components_ms | service_unaccounted_ms | tokens | cost_usd |
| :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| q01 | DIRECT | ANSWERED | 9596 | 9585 | 7917 | 3094 | 0 | 7778 | 134 | 11006 | 11 | 6473 | 0.002403 |
| q02 | DIRECT | REFUSED | 3549 | 3542 | 3540 | 0 | 0 | 3507 | 30 | 3536 | 8 | 7158 | 0.003343 |
| q03 | DECOMPOSE | ANSWERED | 8526 | 8518 | 8516 | 0 | 0 | 8256 | 252 | 8508 | 8 | 6075 | 0.002202 |
| q04 | DIRECT | ANSWERED | 3504 | 3496 | 3495 | 0 | 0 | 3475 | 16 | 3491 | 8 | 5578 | 0.002055 |
| q05 | DIRECT | ANSWERED | 6191 | 6183 | 6182 | 0 | 0 | 6166 | 13 | 6179 | 8 | 4944 | 0.001865 |
| q06 | DIRECT | ANSWERED | 4868 | 4861 | 6328 | 0 | 0 | 6308 | 16 | 6324 | 7 | 5468 | 0.001975 |
| q07 | DIRECT | ANSWERED | 7232 | 7224 | 7223 | 0 | 0 | 7206 | 13 | 7220 | 8 | 6100 | 0.002314 |
| q08 | DECOMPOSE | ANSWERED | 9305 | 9297 | 9296 | 0 | 0 | 9101 | 190 | 9291 | 8 | 6147 | 0.002222 |
| q09 | DIRECT | ANSWERED | 5018 | 5011 | 5010 | 0 | 0 | 4990 | 16 | 5006 | 7 | 6478 | 0.002282 |
| q10 | DIRECT | ANSWERED | 4044 | 4037 | 4036 | 0 | 0 | 4017 | 15 | 4033 | 7 | 6192 | 0.002292 |
| q11 | DIRECT | ANSWERED | 4331 | 4322 | 4321 | 0 | 0 | 4297 | 22 | 4319 | 8 | 6171 | 0.002244 |
| q12 | DIRECT | ANSWERED | 4006 | 3998 | 5878 | 0 | 0 | 5860 | 15 | 5875 | 9 | 5606 | 0.002081 |
| q13 | DIRECT | ANSWERED | 3638 | 3630 | 3629 | 0 | 0 | 3606 | 15 | 3621 | 8 | 5615 | 0.002053 |
| q14 | DIRECT | ANSWERED | 4556 | 4547 | 4546 | 0 | 0 | 4525 | 18 | 4543 | 8 | 6127 | 0.002236 |
| q15 | DIRECT | ANSWERED | 5152 | 5143 | 5142 | 0 | 0 | 5122 | 15 | 5138 | 9 | 5792 | 0.002056 |
| q16 | DECOMPOSE | ANSWERED | 10732 | 10724 | 10723 | 0 | 0 | 10530 | 186 | 10716 | 8 | 6178 | 0.002395 |
| q17 | DIRECT | ANSWERED | 12762 | 12755 | 14323 | 0 | 0 | 14277 | 38 | 14315 | 7 | 9512 | 0.003918 |
| q18 | DIRECT | ANSWERED | 5864 | 5856 | 5855 | 0 | 0 | 5822 | 31 | 5852 | 8 | 5722 | 0.002219 |
| q19 | DIRECT | ANSWERED | 2440 | 2433 | 2432 | 0 | 0 | 2412 | 16 | 2428 | 8 | 6043 | 0.002119 |
| q20 | DECOMPOSE | ANSWERED | 4968 | 4961 | 4960 | 0 | 0 | 4766 | 187 | 4953 | 7 | 6759 | 0.002391 |
| q21 | DIRECT | ANSWERED | 6684 | 6676 | 6675 | 0 | 0 | 6657 | 14 | 6671 | 8 | 6189 | 0.002247 |
| q22 | DIRECT | ANSWERED | 3491 | 3483 | 3482 | 0 | 0 | 3459 | 19 | 3478 | 8 | 5862 | 0.002124 |
| q23 | DECOMPOSE | ANSWERED | 5621 | 5614 | 7515 | 0 | 0 | 5417 | 2090 | 7507 | 8 | 6452 | 0.002447 |
| q24 | DIRECT | ANSWERED | 5864 | 5855 | 5854 | 0 | 0 | 5833 | 17 | 5850 | 9 | 5963 | 0.002143 |
| q25 | DIRECT | ANSWERED | 14147 | 14140 | 14138 | 0 | 0 | 14118 | 15 | 14133 | 7 | 6621 | 0.002422 |
| q26 | DECOMPOSE | ANSWERED | 9446 | 9439 | 11375 | 0 | 0 | 10900 | 462 | 11362 | 8 | 6510 | 0.002424 |
| q27 | DIRECT | ANSWERED | 10224 | 10216 | 10214 | 0 | 0 | 10155 | 52 | 10208 | 8 | 8514 | 0.003705 |
| q28 | DIRECT | REFUSED | 5895 | 5886 | 5885 | 0 | 0 | 5825 | 55 | 5880 | 9 | 7437 | 0.003594 |
| q29 | DIRECT | ANSWERED | 6705 | 6697 | 6695 | 0 | 0 | 6572 | 119 | 6692 | 8 | 6077 | 0.002256 |
| q30 | DIRECT | REFUSED | 6629 | 6621 | 6619 | 0 | 0 | 6550 | 63 | 6613 | 8 | 7178 | 0.003609 |

## 3. Timing 阶段明细表

| qid | engine_init_ms | decompose_ms | rewrite_ms | retrieve_total_ms | first_retrieve_ms | second_retrieve_ms | merge_ms | rerank_ms | first_suff_ms | second_suff_ms | generate_ms | generator_llm_ms | build_response_ms |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| q01 | 3094 | not_applicable | 0 | 134 | 134 | 0 | not_observed | not_applicable | 3315 | 0 | 4467 | 4466 | not_observed |
| q02 | 0 | not_applicable | 775 | 30 | 16 | 14 | not_observed | not_applicable | 1419 | 1314 | 0 | 0 | not_observed |
| q03 | 0 | 1532 | 0 | 252 | 252 | 0 | not_observed | not_applicable | 1547 | 0 | 5180 | 5177 | not_observed |
| q04 | 0 | not_applicable | 0 | 16 | 16 | 0 | not_observed | not_applicable | 1687 | 0 | 1790 | 1789 | not_observed |
| q05 | 0 | not_applicable | 0 | 13 | 13 | 0 | not_observed | not_applicable | 1777 | 0 | 4391 | 4389 | not_observed |
| q06 | 0 | not_applicable | 0 | 16 | 16 | 0 | not_observed | not_applicable | 1761 | 0 | 4549 | 4547 | not_observed |
| q07 | 0 | not_applicable | 0 | 13 | 13 | 0 | not_observed | not_applicable | 1804 | 0 | 5405 | 5403 | not_observed |
| q08 | 0 | 2161 | 0 | 190 | 190 | 0 | not_observed | not_applicable | 1462 | 0 | 5480 | 5478 | not_observed |
| q09 | 0 | not_applicable | 0 | 16 | 16 | 0 | not_observed | not_applicable | 1342 | 0 | 3650 | 3648 | not_observed |
| q10 | 0 | not_applicable | 0 | 15 | 15 | 0 | not_observed | not_applicable | 1821 | 0 | 2199 | 2197 | not_observed |
| q11 | 0 | not_applicable | 0 | 22 | 22 | 0 | not_observed | not_applicable | 1736 | 0 | 2562 | 2561 | not_observed |
| q12 | 0 | not_applicable | 0 | 15 | 15 | 0 | not_observed | not_applicable | 3783 | 0 | 2079 | 2077 | not_observed |
| q13 | 0 | not_applicable | 0 | 15 | 15 | 0 | not_observed | not_applicable | 1865 | 0 | 1746 | 1744 | not_observed |
| q14 | 0 | not_applicable | 0 | 18 | 18 | 0 | not_observed | not_applicable | 2815 | 0 | 1712 | 1711 | not_observed |
| q15 | 0 | not_applicable | 0 | 15 | 15 | 0 | not_observed | not_applicable | 1630 | 0 | 3495 | 3493 | not_observed |
| q16 | 0 | 1197 | 0 | 186 | 186 | 0 | not_observed | not_applicable | 2373 | 0 | 6963 | 6961 | not_observed |
| q17 | 0 | not_applicable | 2305 | 38 | 20 | 18 | not_observed | not_applicable | 1796 | 3496 | 6684 | 6682 | not_observed |
| q18 | 0 | not_applicable | 0 | 31 | 31 | 0 | not_observed | not_applicable | 2572 | 0 | 3252 | 3250 | not_observed |
| q19 | 0 | not_applicable | 0 | 16 | 16 | 0 | not_observed | not_applicable | 1327 | 0 | 1088 | 1086 | not_observed |
| q20 | 0 | 1313 | 0 | 187 | 187 | 0 | not_observed | not_applicable | 1589 | 0 | 1867 | 1865 | not_observed |
| q21 | 0 | not_applicable | 0 | 14 | 14 | 0 | not_observed | not_applicable | 1855 | 0 | 4804 | 4802 | not_observed |
| q22 | 0 | not_applicable | 0 | 19 | 19 | 0 | not_observed | not_applicable | 1310 | 0 | 2151 | 2150 | not_observed |
| q23 | 0 | 1400 | 0 | 2090 | 2090 | 0 | not_observed | not_applicable | 2430 | 0 | 1590 | 1588 | not_observed |
| q24 | 0 | not_applicable | 0 | 17 | 17 | 0 | not_observed | not_applicable | 1506 | 0 | 4329 | 4327 | not_observed |
| q25 | 0 | not_applicable | 0 | 15 | 15 | 0 | not_observed | not_applicable | 1524 | 0 | 12596 | 12594 | not_observed |
| q26 | 0 | 1264 | 0 | 462 | 462 | 0 | not_observed | not_applicable | 1614 | 0 | 8026 | 8023 | not_observed |
| q27 | 0 | not_applicable | 1995 | 52 | 38 | 15 | not_observed | not_applicable | 2485 | 2041 | 3639 | 3637 | not_observed |
| q28 | 0 | not_applicable | 2470 | 55 | 43 | 12 | not_observed | not_applicable | 1228 | 2129 | 0 | 0 | not_observed |
| q29 | 0 | not_applicable | 0 | 119 | 119 | 0 | not_observed | not_applicable | 1918 | 0 | 4657 | 4655 | not_observed |
| q30 | 0 | not_applicable | 1602 | 63 | 27 | 36 | not_observed | not_applicable | 2116 | 2835 | 0 | 0 | not_observed |

## 4. Token / Usage 汇总表

| qid | route | status | full_ledger | expected_roles | observed_roles | missing_roles | calls | prompt_tokens | completion_tokens | reasoning_tokens | cached_tokens | cache_write_tokens | total_tokens | observed_model_ms | generator_llm_ms | cost_usd |
| :-- | :-- | :-- | :--: | :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| q01 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5998 | 475 | not_observed | not_observed | not_observed | 6473 | 7778 | 4466 | 0.002403 |
| q02 | DIRECT | REFUSED | true | sufficiency_judge；rewrite_query | rewrite_query；sufficiency_judge | not_applicable | 3 | 6908 | 250 | not_observed | not_observed | not_observed | 7158 | 3507 | 0 | 0.003343 |
| q03 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 5697 | 378 | not_observed | not_observed | not_observed | 6075 | 8256 | 5177 | 0.002202 |
| q04 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5262 | 316 | not_observed | not_observed | not_observed | 5578 | 3475 | 1789 | 0.002055 |
| q05 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4626 | 318 | not_observed | not_observed | not_observed | 4944 | 6166 | 4389 | 0.001865 |
| q06 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5222 | 246 | not_observed | not_observed | not_observed | 5468 | 6308 | 4547 | 0.001975 |
| q07 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5571 | 529 | not_observed | not_observed | not_observed | 6100 | 7206 | 5403 | 0.002314 |
| q08 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 5654 | 493 | not_observed | not_observed | not_observed | 6147 | 9101 | 5478 | 0.002222 |
| q09 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 6205 | 273 | not_observed | not_observed | not_observed | 6478 | 4990 | 3648 | 0.002282 |
| q10 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5786 | 406 | not_observed | not_observed | not_observed | 6192 | 4017 | 2197 | 0.002292 |
| q11 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5861 | 310 | not_observed | not_observed | not_observed | 6171 | 4297 | 2561 | 0.002244 |
| q12 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5241 | 365 | not_observed | not_observed | not_observed | 5606 | 5860 | 2077 | 0.002081 |
| q13 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5301 | 314 | not_observed | not_observed | not_observed | 5615 | 3606 | 1744 | 0.002053 |
| q14 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5804 | 323 | not_observed | not_observed | not_observed | 6127 | 4525 | 1711 | 0.002236 |
| q15 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5551 | 241 | not_observed | not_observed | not_observed | 5792 | 5122 | 3493 | 0.002056 |
| q16 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 5493 | 685 | not_observed | not_observed | not_observed | 6178 | 10530 | 6961 | 0.002395 |
| q17 | DIRECT | ANSWERED | true | sufficiency_judge；rewrite_query；generator | generator；rewrite_query；sufficiency_judge | not_applicable | 4 | 8899 | 613 | not_observed | not_observed | not_observed | 9512 | 14277 | 6682 | 0.003918 |
| q18 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5258 | 464 | not_observed | not_observed | not_observed | 5722 | 5822 | 3250 | 0.002219 |
| q19 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5837 | 206 | not_observed | not_observed | not_observed | 6043 | 2412 | 1086 | 0.002119 |
| q20 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 6400 | 359 | not_observed | not_observed | not_observed | 6759 | 4766 | 1865 | 0.002391 |
| q21 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5802 | 387 | not_observed | not_observed | not_observed | 6189 | 6657 | 4802 | 0.002247 |
| q22 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5495 | 367 | not_observed | not_observed | not_observed | 5862 | 3459 | 2150 | 0.002124 |
| q23 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 5989 | 463 | not_observed | not_observed | not_observed | 6452 | 5417 | 1588 | 0.002447 |
| q24 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5640 | 323 | not_observed | not_observed | not_observed | 5963 | 5833 | 4327 | 0.002143 |
| q25 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 6180 | 441 | not_observed | not_observed | not_observed | 6621 | 14118 | 12594 | 0.002422 |
| q26 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 5919 | 591 | not_observed | not_observed | not_observed | 6510 | 10900 | 8023 | 0.002424 |
| q27 | DIRECT | ANSWERED | true | sufficiency_judge；rewrite_query；generator | generator；rewrite_query；sufficiency_judge | not_applicable | 4 | 7837 | 677 | not_observed | not_observed | not_observed | 8514 | 10155 | 3637 | 0.003705 |
| q28 | DIRECT | REFUSED | true | sufficiency_judge；rewrite_query | rewrite_query；sufficiency_judge | not_applicable | 3 | 7043 | 394 | not_observed | not_observed | not_observed | 7437 | 5825 | 0 | 0.003594 |
| q29 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5704 | 373 | not_observed | not_observed | not_observed | 6077 | 6572 | 4655 | 0.002256 |
| q30 | DIRECT | REFUSED | true | sufficiency_judge；rewrite_query | rewrite_query；sufficiency_judge | not_applicable | 3 | 6632 | 546 | not_observed | not_observed | not_observed | 7178 | 6550 | 0 | 0.003609 |

## 5. Model-call 明细

| qid | idx | role | stage | provider | model | upstream | latency_ms | prompt_tokens | completion_tokens | reasoning_tokens | cached_tokens | total_tokens | cost_usd | timeout | api_error | error_type |
| :-- | --: | :-- | :-- | :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | --: | :--: | :--: | :-- |
| q01 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 3312 | 3577 | 251 | not_observed | not_observed | 3828 | 0.001905 | false | false | not_applicable |
| q01 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 4466 | 2421 | 224 | 0 | not_observed | 2645 | 0.000498 | false | false | not_applicable |
| q02 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1419 | 3410 | 136 | not_observed | not_observed | 3546 | 0.001680 | false | false | not_applicable |
| q02 | 2 | sufficiency_judge | legacy_second_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1314 | 3433 | 104 | not_observed | not_observed | 3537 | 0.001648 | false | false | not_applicable |
| q02 | 3 | rewrite_query | rewrite_query | openrouter | openai/gpt-4o-mini | OpenAI | 774 | 65 | 10 | 0 | 0 | 75 | 0.000016 | false | false | not_applicable |
| q03 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1547 | 3411 | 182 | not_observed | not_observed | 3593 | 0.001741 | false | false | not_applicable |
| q03 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | OpenAI | 1532 | 86 | 23 | 0 | 0 | 109 | 0.000027 | false | false | not_applicable |
| q03 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 5177 | 2200 | 173 | 0 | not_observed | 2373 | 0.000434 | false | false | not_applicable |
| q04 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1686 | 3266 | 179 | not_observed | not_observed | 3445 | 0.001673 | false | false | not_applicable |
| q04 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1789 | 1996 | 137 | 0 | not_observed | 2133 | 0.000382 | false | false | not_applicable |
| q05 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1777 | 2960 | 170 | not_observed | not_observed | 3130 | 0.001527 | false | false | not_applicable |
| q05 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 4389 | 1666 | 148 | 0 | not_observed | 1814 | 0.000339 | false | false | not_applicable |
| q06 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1761 | 3192 | 164 | not_observed | not_observed | 3356 | 0.001621 | false | false | not_applicable |
| q06 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 4547 | 2030 | 82 | 0 | not_observed | 2112 | 0.000354 | false | false | not_applicable |
| q07 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1803 | 3391 | 246 | not_observed | not_observed | 3637 | 0.001817 | false | false | not_applicable |
| q07 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 5403 | 2180 | 283 | 0 | not_observed | 2463 | 0.000497 | false | false | not_applicable |
| q08 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1462 | 3338 | 153 | not_observed | not_observed | 3491 | 0.001671 | false | false | not_applicable |
| q08 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | Azure | 2161 | 89 | 31 | 0 | 0 | 120 | 0.000032 | false | false | not_applicable |
| q08 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 5478 | 2227 | 309 | 0 | not_observed | 2536 | 0.000519 | false | false | not_applicable |
| q09 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1342 | 3718 | 152 | not_observed | not_observed | 3870 | 0.001837 | false | false | not_applicable |
| q09 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 3648 | 2487 | 121 | 0 | not_observed | 2608 | 0.000446 | false | false | not_applicable |
| q10 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1820 | 3408 | 267 | not_observed | not_observed | 3675 | 0.001852 | false | false | not_applicable |
| q10 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2197 | 2378 | 139 | 0 | not_observed | 2517 | 0.000440 | false | false | not_applicable |
| q11 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1736 | 3498 | 228 | not_observed | not_observed | 3726 | 0.001840 | false | false | not_applicable |
| q11 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2561 | 2363 | 82 | 0 | not_observed | 2445 | 0.000404 | false | false | not_applicable |
| q12 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 3783 | 3157 | 222 | not_observed | not_observed | 3379 | 0.001682 | false | false | not_applicable |
| q12 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2077 | 2084 | 143 | 0 | not_observed | 2227 | 0.000398 | false | false | not_applicable |
| q13 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1862 | 3175 | 207 | not_observed | not_observed | 3382 | 0.001670 | false | false | not_applicable |
| q13 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1744 | 2126 | 107 | 0 | not_observed | 2233 | 0.000383 | false | false | not_applicable |
| q14 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2814 | 3492 | 221 | not_observed | not_observed | 3713 | 0.001828 | false | false | not_applicable |
| q14 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1711 | 2312 | 102 | 0 | not_observed | 2414 | 0.000408 | false | false | not_applicable |
| q15 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1629 | 3315 | 163 | not_observed | not_observed | 3478 | 0.001674 | false | false | not_applicable |
| q15 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 3493 | 2236 | 78 | 0 | not_observed | 2314 | 0.000382 | false | false | not_applicable |
| q16 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2372 | 3281 | 290 | not_observed | not_observed | 3571 | 0.001826 | false | false | not_applicable |
| q16 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | OpenAI | 1197 | 90 | 20 | 0 | 0 | 110 | 0.000025 | false | false | not_applicable |
| q16 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 6961 | 2122 | 375 | 0 | not_observed | 2497 | 0.000543 | false | false | not_applicable |
| q17 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1796 | 3320 | 204 | not_observed | not_observed | 3524 | 0.001730 | false | false | not_applicable |
| q17 | 2 | sufficiency_judge | legacy_second_sufficiency | deepseek | deepseek-v4-flash | not_observed | 3496 | 3320 | 198 | not_observed | not_observed | 3518 | 0.001722 | false | false | not_applicable |
| q17 | 3 | rewrite_query | rewrite_query | openrouter | openai/gpt-4o-mini | Azure | 2304 | 71 | 18 | 0 | 0 | 89 | 0.000021 | false | false | not_applicable |
| q17 | 4 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 6682 | 2188 | 193 | 0 | not_observed | 2381 | 0.000444 | false | false | not_applicable |
| q18 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2572 | 3222 | 302 | not_observed | not_observed | 3524 | 0.001816 | false | false | not_applicable |
| q18 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 3250 | 2036 | 162 | 0 | not_observed | 2198 | 0.000403 | false | false | not_applicable |
| q19 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1326 | 3493 | 148 | not_observed | not_observed | 3641 | 0.001732 | false | false | not_applicable |
| q19 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1086 | 2344 | 58 | 0 | not_observed | 2402 | 0.000386 | false | false | not_applicable |
| q20 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1588 | 3790 | 162 | not_observed | not_observed | 3952 | 0.001881 | false | false | not_applicable |
| q20 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | Azure | 1313 | 92 | 21 | 0 | 0 | 113 | 0.000026 | false | false | not_applicable |
| q20 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1865 | 2518 | 176 | 0 | not_observed | 2694 | 0.000483 | false | false | not_applicable |
| q21 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1855 | 3494 | 182 | not_observed | not_observed | 3676 | 0.001778 | false | false | not_applicable |
| q21 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 4802 | 2308 | 205 | 0 | not_observed | 2513 | 0.000469 | false | false | not_applicable |
| q22 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1309 | 3289 | 174 | not_observed | not_observed | 3463 | 0.001677 | false | false | not_applicable |
| q22 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2150 | 2206 | 193 | 0 | not_observed | 2399 | 0.000447 | false | false | not_applicable |
| q23 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2429 | 3532 | 342 | not_observed | not_observed | 3874 | 0.002006 | false | false | not_applicable |
| q23 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | OpenAI | 1400 | 88 | 27 | 0 | 0 | 115 | 0.000029 | false | false | not_applicable |
| q23 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1588 | 2369 | 94 | 0 | not_observed | 2463 | 0.000412 | false | false | not_applicable |
| q24 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1506 | 3381 | 170 | not_observed | not_observed | 3551 | 0.001712 | false | false | not_applicable |
| q24 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 4327 | 2259 | 153 | 0 | not_observed | 2412 | 0.000431 | false | false | not_applicable |
| q25 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1524 | 3692 | 222 | not_observed | not_observed | 3914 | 0.001918 | false | false | not_applicable |
| q25 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 12594 | 2488 | 219 | 0 | not_observed | 2707 | 0.000505 | false | false | not_applicable |
| q26 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1613 | 3518 | 224 | not_observed | not_observed | 3742 | 0.001844 | false | false | not_applicable |
| q26 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | OpenAI | 1264 | 89 | 22 | 0 | 0 | 111 | 0.000027 | false | false | not_applicable |
| q26 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 8023 | 2312 | 345 | 0 | not_observed | 2657 | 0.000554 | false | false | not_applicable |
| q27 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2484 | 3002 | 272 | not_observed | not_observed | 3274 | 0.001680 | false | false | not_applicable |
| q27 | 2 | sufficiency_judge | legacy_second_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2041 | 3002 | 258 | not_observed | not_observed | 3260 | 0.001661 | false | false | not_applicable |
| q27 | 3 | rewrite_query | rewrite_query | openrouter | openai/gpt-4o-mini | Azure | 1993 | 69 | 13 | 0 | 0 | 82 | 0.000018 | false | false | not_applicable |
| q27 | 4 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 3637 | 1764 | 134 | 0 | not_observed | 1898 | 0.000345 | false | false | not_applicable |
| q28 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1228 | 3526 | 165 | not_observed | not_observed | 3691 | 0.001769 | false | false | not_applicable |
| q28 | 2 | sufficiency_judge | legacy_second_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2129 | 3454 | 219 | not_observed | not_observed | 3673 | 0.001809 | false | false | not_applicable |
| q28 | 3 | rewrite_query | rewrite_query | openrouter | openai/gpt-4o-mini | Azure | 2468 | 63 | 10 | 0 | 0 | 73 | 0.000015 | false | false | not_applicable |
| q29 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1917 | 3491 | 228 | not_observed | not_observed | 3719 | 0.001837 | false | false | not_applicable |
| q29 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 4655 | 2213 | 145 | 0 | not_observed | 2358 | 0.000419 | false | false | not_applicable |
| q30 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2115 | 3282 | 238 | not_observed | not_observed | 3520 | 0.001758 | false | false | not_applicable |
| q30 | 2 | sufficiency_judge | legacy_second_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2835 | 3282 | 294 | not_observed | not_observed | 3576 | 0.001832 | false | false | not_applicable |
| q30 | 3 | rewrite_query | rewrite_query | openrouter | openai/gpt-4o-mini | Azure | 1600 | 68 | 14 | 0 | 0 | 82 | 0.000019 | false | false | not_applicable |

## 6. Model role 汇总

| role | calls | total_ms | median_ms | total_tokens | token observed/unknown | cost_usd | cost observed/unknown |
| :-- | --: | --: | --: | --: | :-- | --: | :-- |
| sufficiency_judge | 35 | 69203 | 1796 | 125449 | 125449/0 | 0.061654 | 0.061654/0 |
| generator | 27 | 110300 | 3648 | 64413 | 64413/0 | 0.011723 | 0.011723/0 |
| subquery_generator | 6 | 8867 | 1356 | 678 | 678/0 | 0.000167 | 0.000167/0 |
| rewrite_query | 5 | 9139 | 1993 | 401 | 401/0 | 0.000089 | 0.000089/0 |

## 7. 批次分析

- service latency min / median / p95 / max / total ms: 2440 / 5864 / 11848 / 14147 / 194988
- model_call_count: 73
- total_tokens: 190941
- total_tokens observed subtotal / unknown records: 190941 / 0
- total_estimated_cost_usd: 0.073633
- estimated cost observed subtotal / unknown records: 0.073633 / 0
- slowest_cases: q25=14147ms, q17=12762ms, q16=10732ms, q27=10224ms, q01=9596ms
- highest_token_cases: q17=9512, q27=8514, q28=7437, q30=7178, q02=7158
- highest_cost_cases: q17=$0.003918, q27=$0.003705, q30=$0.003609, q28=$0.003594, q02=$0.003343
- engine_init_outliers (>=100ms): q01=3094ms
- unaccounted_outliers (>=100ms): none

### 口径说明

- `service_total_ms`：应用服务本题总耗时。
- `engine_ms`：engine 执行总耗时，已包含 `engine_init_ms`；`pipeline_total_ms`：pipeline 内部总耗时。
- `observed_model_ms`：所有已记录 model call latency 的合计；它是调用观测总量，不代表 provider 并发情况下的关键路径耗时。
- `engine_observed_components_ms = engine_init_ms + retrieval_ms + observed_model_ms`，仅用于组件覆盖观察。
- `service_unaccounted_ms = service_total_ms - queue_wait_ms - engine_ms`，用于观察 service 层剩余开销。
- `decompose_ms`：当前 CER 没有独立 decompose stage timer，直接使用已观测 `subquery_generator` model-call latency；未发生 DECOMPOSE 时为 `not_applicable`。
- `merge_ms` / `build_response_ms`：当前 CER 未独立记录时保留 `not_observed`，不从总耗时反推。
- `rerank_ms`：本轮 rerank 全局关闭，因此为 `not_applicable`。
- cost 为静态价格表估算值；`provider_billing_reconciled=false` 时不等同于供应商账单实扣。
