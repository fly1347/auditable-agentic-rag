# B2-baseline Timing-Usage-Cost 明细

> 来源：当前 live CanonicalExecutionRecord（CER）确定性投影。
> `engine_ms` 已包含 `engine_init_ms`；两者分别展示，不相加作为总耗时。
> `service_unaccounted_ms = service_total_ms - queue_wait_ms - engine_ms`；`engine_observed_components_ms` 仅用于观察已记录的 engine 内部组件。
> 当前 CER 未记录独立 `merge_ms` / `build_response_ms` 时保留 `not_observed`；rerank 关闭时记为 `not_applicable`。

## 0. 运行信息

- profile: baseline
- cases: 30
- run_id: eval_413526d23766
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
| final_status | ANSWERED: 29；REFUSED: 1 |
| model_role | generator: 29；rewrite_query: 1；subquery_generator: 6；sufficiency_judge: 31 |
| provider | deepseek: 31；openrouter: 36 |
| model | deepseek-v4-flash: 31；openai/gpt-4o-mini: 36 |
| upstream_provider | Azure: 19；OpenAI: 17 |
| usage ledger | full=30/30 |

## 2. Timing 总体逐题表

| qid | route | status | service_total_ms | engine_ms | pipeline_total_ms | engine_init_ms | queue_wait_ms | observed_model_ms | retrieval_ms | engine_observed_components_ms | service_unaccounted_ms | tokens | cost_usd |
| :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| q01 | DIRECT | ANSWERED | 9325 | 9313 | 6094 | 3209 | 0 | 5972 | 117 | 9297 | 12 | 4518 | 0.001328 |
| q02 | DIRECT | REFUSED | 1886 | 1877 | 1876 | 0 | 0 | 1827 | 41 | 1868 | 9 | 3630 | 0.001589 |
| q03 | DECOMPOSE | ANSWERED | 6083 | 6074 | 6073 | 0 | 0 | 5936 | 132 | 6067 | 8 | 4157 | 0.001194 |
| q04 | DIRECT | ANSWERED | 2236 | 2229 | 2227 | 0 | 0 | 2206 | 17 | 2223 | 7 | 3725 | 0.001086 |
| q05 | DIRECT | ANSWERED | 4551 | 4544 | 4542 | 0 | 0 | 4520 | 19 | 4539 | 8 | 3017 | 0.000871 |
| q06 | DIRECT | ANSWERED | 3324 | 3317 | 3315 | 0 | 0 | 3295 | 17 | 3311 | 7 | 3635 | 0.001027 |
| q07 | DIRECT | ANSWERED | 5581 | 5574 | 6977 | 0 | 0 | 6951 | 23 | 6974 | 7 | 4170 | 0.001247 |
| q08 | DECOMPOSE | ANSWERED | 7108 | 7100 | 7099 | 0 | 0 | 6905 | 187 | 7092 | 8 | 4316 | 0.001286 |
| q09 | DIRECT | ANSWERED | 4105 | 4097 | 4096 | 0 | 0 | 4067 | 26 | 4092 | 7 | 4720 | 0.001378 |
| q10 | DIRECT | ANSWERED | 2365 | 2357 | 2356 | 0 | 0 | 2335 | 16 | 2351 | 8 | 4366 | 0.001257 |
| q11 | DIRECT | ANSWERED | 2608 | 2601 | 2600 | 0 | 0 | 2580 | 16 | 2596 | 7 | 4349 | 0.001257 |
| q12 | DIRECT | ANSWERED | 3438 | 3430 | 3429 | 0 | 0 | 3411 | 15 | 3426 | 8 | 3795 | 0.001092 |
| q13 | DIRECT | ANSWERED | 2458 | 2450 | 2449 | 0 | 0 | 2430 | 16 | 2446 | 8 | 3851 | 0.001099 |
| q14 | DIRECT | ANSWERED | 2665 | 2657 | 2656 | 0 | 0 | 2636 | 17 | 2653 | 7 | 4256 | 0.001222 |
| q15 | DIRECT | ANSWERED | 3011 | 3004 | 3003 | 0 | 0 | 2980 | 19 | 2999 | 7 | 3987 | 0.001122 |
| q16 | DECOMPOSE | ANSWERED | 12266 | 12259 | 12257 | 0 | 0 | 12068 | 184 | 12252 | 8 | 4267 | 0.001303 |
| q17 | DIRECT | ANSWERED | 4760 | 4752 | 4751 | 0 | 0 | 4691 | 56 | 4747 | 8 | 4102 | 0.001206 |
| q18 | DIRECT | ANSWERED | 2862 | 2854 | 5028 | 0 | 0 | 4994 | 29 | 5023 | 8 | 3770 | 0.001105 |
| q19 | DIRECT | ANSWERED | 3868 | 3861 | 3859 | 0 | 0 | 3841 | 15 | 3856 | 7 | 4366 | 0.001262 |
| q20 | DECOMPOSE | ANSWERED | 7263 | 7255 | 7254 | 0 | 0 | 7062 | 187 | 7248 | 8 | 4555 | 0.001346 |
| q21 | DIRECT | ANSWERED | 3481 | 3474 | 3472 | 0 | 0 | 3448 | 19 | 3468 | 7 | 4287 | 0.001254 |
| q22 | DIRECT | ANSWERED | 4220 | 4212 | 4211 | 0 | 0 | 4185 | 22 | 4207 | 8 | 4113 | 0.001204 |
| q23 | DECOMPOSE | ANSWERED | 3914 | 3906 | 3905 | 0 | 0 | 3722 | 176 | 3899 | 7 | 4467 | 0.001281 |
| q24 | DIRECT | ANSWERED | 5473 | 5465 | 5464 | 0 | 0 | 5443 | 17 | 5460 | 8 | 4191 | 0.001217 |
| q25 | DIRECT | ANSWERED | 5414 | 5407 | 6816 | 0 | 0 | 6794 | 18 | 6812 | 8 | 4623 | 0.001343 |
| q26 | DECOMPOSE | ANSWERED | 7571 | 7563 | 7562 | 0 | 0 | 7409 | 147 | 7557 | 8 | 4521 | 0.001350 |
| q27 | DIRECT | ANSWERED | 5016 | 5007 | 5006 | 0 | 0 | 4982 | 20 | 5003 | 8 | 3222 | 0.000936 |
| q28 | DIRECT | ANSWERED | 3719 | 3711 | 3710 | 0 | 0 | 3690 | 16 | 3706 | 8 | 4417 | 0.001261 |
| q29 | DIRECT | ANSWERED | 3834 | 3826 | 3824 | 0 | 0 | 3802 | 18 | 3820 | 8 | 4173 | 0.001222 |
| q30 | DIRECT | ANSWERED | 3270 | 3263 | 3261 | 0 | 0 | 3241 | 18 | 3258 | 8 | 4061 | 0.001185 |

## 3. Timing 阶段明细表

| qid | engine_init_ms | decompose_ms | rewrite_ms | retrieve_total_ms | first_retrieve_ms | second_retrieve_ms | merge_ms | rerank_ms | first_suff_ms | second_suff_ms | generate_ms | generator_llm_ms | build_response_ms |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| q01 | 3209 | not_applicable | 0 | 117 | 117 | 0 | not_observed | not_applicable | 706 | 0 | 5269 | 5267 | not_observed |
| q02 | 0 | not_applicable | 826 | 41 | 28 | 13 | not_observed | not_applicable | 443 | 561 | 0 | 0 | not_observed |
| q03 | 0 | 1266 | 0 | 132 | 132 | 0 | not_observed | not_applicable | 633 | 0 | 4039 | 4037 | not_observed |
| q04 | 0 | not_applicable | 0 | 17 | 17 | 0 | not_observed | not_applicable | 468 | 0 | 1740 | 1738 | not_observed |
| q05 | 0 | not_applicable | 0 | 19 | 19 | 0 | not_observed | not_applicable | 505 | 0 | 4017 | 4015 | not_observed |
| q06 | 0 | not_applicable | 0 | 17 | 17 | 0 | not_observed | not_applicable | 541 | 0 | 2756 | 2754 | not_observed |
| q07 | 0 | not_applicable | 0 | 23 | 23 | 0 | not_observed | not_applicable | 773 | 0 | 6179 | 6178 | not_observed |
| q08 | 0 | 1014 | 0 | 187 | 187 | 0 | not_observed | not_applicable | 857 | 0 | 5036 | 5035 | not_observed |
| q09 | 0 | not_applicable | 0 | 26 | 26 | 0 | not_observed | not_applicable | 572 | 0 | 3497 | 3495 | not_observed |
| q10 | 0 | not_applicable | 0 | 16 | 16 | 0 | not_observed | not_applicable | 483 | 0 | 1855 | 1853 | not_observed |
| q11 | 0 | not_applicable | 0 | 16 | 16 | 0 | not_observed | not_applicable | 366 | 0 | 2217 | 2215 | not_observed |
| q12 | 0 | not_applicable | 0 | 15 | 15 | 0 | not_observed | not_applicable | 1588 | 0 | 1825 | 1824 | not_observed |
| q13 | 0 | not_applicable | 0 | 16 | 16 | 0 | not_observed | not_applicable | 722 | 0 | 1711 | 1709 | not_observed |
| q14 | 0 | not_applicable | 0 | 17 | 17 | 0 | not_observed | not_applicable | 435 | 0 | 2203 | 2201 | not_observed |
| q15 | 0 | not_applicable | 0 | 19 | 19 | 0 | not_observed | not_applicable | 722 | 0 | 2261 | 2259 | not_observed |
| q16 | 0 | 5022 | 0 | 184 | 184 | 0 | not_observed | not_applicable | 369 | 0 | 6678 | 6677 | not_observed |
| q17 | 0 | not_applicable | 0 | 56 | 56 | 0 | not_observed | not_applicable | 536 | 0 | 4158 | 4156 | not_observed |
| q18 | 0 | not_applicable | 0 | 29 | 29 | 0 | not_observed | not_applicable | 463 | 0 | 4534 | 4532 | not_observed |
| q19 | 0 | not_applicable | 0 | 15 | 15 | 0 | not_observed | not_applicable | 333 | 0 | 3511 | 3509 | not_observed |
| q20 | 0 | 1055 | 0 | 187 | 187 | 0 | not_observed | not_applicable | 637 | 0 | 5372 | 5370 | not_observed |
| q21 | 0 | not_applicable | 0 | 19 | 19 | 0 | not_observed | not_applicable | 693 | 0 | 2759 | 2756 | not_observed |
| q22 | 0 | not_applicable | 0 | 22 | 22 | 0 | not_observed | not_applicable | 567 | 0 | 3620 | 3619 | not_observed |
| q23 | 0 | 954 | 0 | 176 | 176 | 0 | not_observed | not_applicable | 335 | 0 | 2436 | 2434 | not_observed |
| q24 | 0 | not_applicable | 0 | 17 | 17 | 0 | not_observed | not_applicable | 585 | 0 | 4861 | 4858 | not_observed |
| q25 | 0 | not_applicable | 0 | 18 | 18 | 0 | not_observed | not_applicable | 340 | 0 | 6456 | 6454 | not_observed |
| q26 | 0 | 1072 | 0 | 147 | 147 | 0 | not_observed | not_applicable | 532 | 0 | 5807 | 5806 | not_observed |
| q27 | 0 | not_applicable | 0 | 20 | 20 | 0 | not_observed | not_applicable | 478 | 0 | 4506 | 4505 | not_observed |
| q28 | 0 | not_applicable | 0 | 16 | 16 | 0 | not_observed | not_applicable | 801 | 0 | 2891 | 2889 | not_observed |
| q29 | 0 | not_applicable | 0 | 18 | 18 | 0 | not_observed | not_applicable | 411 | 0 | 3394 | 3391 | not_observed |
| q30 | 0 | not_applicable | 0 | 18 | 18 | 0 | not_observed | not_applicable | 328 | 0 | 2914 | 2913 | not_observed |

## 4. Token / Usage 汇总表

| qid | route | status | full_ledger | expected_roles | observed_roles | missing_roles | calls | prompt_tokens | completion_tokens | reasoning_tokens | cached_tokens | cache_write_tokens | total_tokens | observed_model_ms | generator_llm_ms | cost_usd |
| :-- | :-- | :-- | :--: | :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| q01 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4274 | 244 | not_observed | not_observed | not_observed | 4518 | 5972 | 5267 | 0.001328 |
| q02 | DIRECT | REFUSED | true | sufficiency_judge；rewrite_query | rewrite_query；sufficiency_judge | not_applicable | 3 | 3610 | 20 | not_observed | not_observed | not_observed | 3630 | 1827 | 0 | 0.001589 |
| q03 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 4001 | 156 | not_observed | not_observed | not_observed | 4157 | 5936 | 4037 | 0.001194 |
| q04 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3584 | 141 | not_observed | not_observed | not_observed | 3725 | 2206 | 1738 | 0.001086 |
| q05 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 2867 | 150 | not_observed | not_observed | not_observed | 3017 | 4520 | 4015 | 0.000871 |
| q06 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3549 | 86 | not_observed | not_observed | not_observed | 3635 | 3295 | 2754 | 0.001027 |
| q07 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3910 | 260 | not_observed | not_observed | not_observed | 4170 | 6951 | 6178 | 0.001247 |
| q08 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 3968 | 348 | not_observed | not_observed | not_observed | 4316 | 6905 | 5035 | 0.001286 |
| q09 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4595 | 125 | not_observed | not_observed | not_observed | 4720 | 4067 | 3495 | 0.001378 |
| q10 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4223 | 143 | not_observed | not_observed | not_observed | 4366 | 2335 | 1853 | 0.001257 |
| q11 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4190 | 159 | not_observed | not_observed | not_observed | 4349 | 2580 | 2215 | 0.001257 |
| q12 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3648 | 147 | not_observed | not_observed | not_observed | 3795 | 3411 | 1824 | 0.001092 |
| q13 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3735 | 116 | not_observed | not_observed | not_observed | 3851 | 2430 | 1709 | 0.001099 |
| q14 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4150 | 106 | not_observed | not_observed | not_observed | 4256 | 2636 | 2201 | 0.001222 |
| q15 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3901 | 86 | not_observed | not_observed | not_observed | 3987 | 2980 | 2259 | 0.001122 |
| q16 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 3864 | 403 | not_observed | not_observed | not_observed | 4267 | 12068 | 6677 | 0.001303 |
| q17 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3899 | 203 | not_observed | not_observed | not_observed | 4102 | 4691 | 4156 | 0.001206 |
| q18 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3562 | 208 | not_observed | not_observed | not_observed | 3770 | 4994 | 4532 | 0.001105 |
| q19 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4253 | 113 | not_observed | not_observed | not_observed | 4366 | 3841 | 3509 | 0.001262 |
| q20 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 4314 | 241 | not_observed | not_observed | not_observed | 4555 | 7062 | 5370 | 0.001346 |
| q21 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4072 | 215 | not_observed | not_observed | not_observed | 4287 | 3448 | 2756 | 0.001254 |
| q22 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3919 | 194 | not_observed | not_observed | not_observed | 4113 | 4185 | 3619 | 0.001204 |
| q23 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 4310 | 157 | not_observed | not_observed | not_observed | 4467 | 3722 | 2434 | 0.001281 |
| q24 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4034 | 157 | not_observed | not_observed | not_observed | 4191 | 5443 | 4858 | 0.001217 |
| q25 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4449 | 174 | not_observed | not_observed | not_observed | 4623 | 6794 | 6454 | 0.001343 |
| q26 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 4183 | 338 | not_observed | not_observed | not_observed | 4521 | 7409 | 5806 | 0.001350 |
| q27 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3051 | 171 | not_observed | not_observed | not_observed | 3222 | 4982 | 4505 | 0.000936 |
| q28 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4342 | 75 | not_observed | not_observed | not_observed | 4417 | 3690 | 2889 | 0.001261 |
| q29 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4020 | 153 | not_observed | not_observed | not_observed | 4173 | 3802 | 3391 | 0.001222 |
| q30 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3867 | 194 | not_observed | not_observed | not_observed | 4061 | 3241 | 2913 | 0.001185 |

## 5. Model-call 明细

| qid | idx | role | stage | provider | model | upstream | latency_ms | prompt_tokens | completion_tokens | reasoning_tokens | cached_tokens | total_tokens | cost_usd | timeout | api_error | error_type |
| :-- | --: | :-- | :-- | :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | --: | :--: | :--: | :-- |
| q01 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 705 | 1853 | 4 | not_observed | not_observed | 1857 | 0.000821 | false | false | not_applicable |
| q01 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 5267 | 2421 | 240 | 0 | not_observed | 2661 | 0.000507 | false | false | not_applicable |
| q02 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 442 | 1760 | 5 | not_observed | not_observed | 1765 | 0.000781 | false | false | not_applicable |
| q02 | 2 | sufficiency_judge | legacy_second_sufficiency | deepseek | deepseek-v4-flash | not_observed | 561 | 1785 | 5 | not_observed | not_observed | 1790 | 0.000792 | false | false | not_applicable |
| q02 | 3 | rewrite_query | rewrite_query | openrouter | openai/gpt-4o-mini | OpenAI | 824 | 65 | 10 | 0 | 0 | 75 | 0.000016 | false | false | not_applicable |
| q03 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 633 | 1715 | 4 | not_observed | not_observed | 1719 | 0.000760 | false | false | not_applicable |
| q03 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | OpenAI | 1266 | 86 | 23 | 0 | 0 | 109 | 0.000027 | false | false | not_applicable |
| q03 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 4037 | 2200 | 129 | 0 | not_observed | 2329 | 0.000407 | false | false | not_applicable |
| q04 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 468 | 1588 | 4 | not_observed | not_observed | 1592 | 0.000704 | false | false | not_applicable |
| q04 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1738 | 1996 | 137 | 0 | not_observed | 2133 | 0.000382 | false | false | not_applicable |
| q05 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 505 | 1201 | 4 | not_observed | not_observed | 1205 | 0.000534 | false | false | not_applicable |
| q05 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 4015 | 1666 | 146 | 0 | not_observed | 1812 | 0.000338 | false | false | not_applicable |
| q06 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 541 | 1519 | 4 | not_observed | not_observed | 1523 | 0.000674 | false | false | not_applicable |
| q06 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 2754 | 2030 | 82 | 0 | not_observed | 2112 | 0.000354 | false | false | not_applicable |
| q07 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 773 | 1730 | 4 | not_observed | not_observed | 1734 | 0.000766 | false | false | not_applicable |
| q07 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 6178 | 2180 | 256 | 0 | not_observed | 2436 | 0.000481 | false | false | not_applicable |
| q08 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 856 | 1652 | 4 | not_observed | not_observed | 1656 | 0.000732 | false | false | not_applicable |
| q08 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | OpenAI | 1014 | 89 | 30 | 0 | 0 | 119 | 0.000031 | false | false | not_applicable |
| q08 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 5035 | 2227 | 314 | 0 | not_observed | 2541 | 0.000522 | false | false | not_applicable |
| q09 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 572 | 2108 | 4 | not_observed | not_observed | 2112 | 0.000933 | false | false | not_applicable |
| q09 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 3495 | 2487 | 121 | 0 | not_observed | 2608 | 0.000446 | false | false | not_applicable |
| q10 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 482 | 1845 | 4 | not_observed | not_observed | 1849 | 0.000817 | false | false | not_applicable |
| q10 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1853 | 2378 | 139 | 0 | not_observed | 2517 | 0.000440 | false | false | not_applicable |
| q11 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 365 | 1827 | 4 | not_observed | not_observed | 1831 | 0.000809 | false | false | not_applicable |
| q11 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2215 | 2363 | 155 | 0 | not_observed | 2518 | 0.000447 | false | false | not_applicable |
| q12 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1587 | 1564 | 4 | not_observed | not_observed | 1568 | 0.000693 | false | false | not_applicable |
| q12 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1824 | 2084 | 143 | 0 | not_observed | 2227 | 0.000398 | false | false | not_applicable |
| q13 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 721 | 1609 | 4 | not_observed | not_observed | 1613 | 0.000713 | false | false | not_applicable |
| q13 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1709 | 2126 | 112 | 0 | not_observed | 2238 | 0.000386 | false | false | not_applicable |
| q14 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 435 | 1838 | 4 | not_observed | not_observed | 1842 | 0.000814 | false | false | not_applicable |
| q14 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2201 | 2312 | 102 | 0 | not_observed | 2414 | 0.000408 | false | false | not_applicable |
| q15 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 721 | 1665 | 4 | not_observed | not_observed | 1669 | 0.000738 | false | false | not_applicable |
| q15 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 2259 | 2236 | 82 | 0 | not_observed | 2318 | 0.000385 | false | false | not_applicable |
| q16 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 369 | 1652 | 4 | not_observed | not_observed | 1656 | 0.000732 | false | false | not_applicable |
| q16 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | OpenAI | 5022 | 90 | 21 | 0 | 0 | 111 | 0.000026 | false | false | not_applicable |
| q16 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 6677 | 2122 | 378 | 0 | not_observed | 2500 | 0.000545 | false | false | not_applicable |
| q17 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 535 | 1711 | 4 | not_observed | not_observed | 1715 | 0.000758 | false | false | not_applicable |
| q17 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 4156 | 2188 | 199 | 0 | not_observed | 2387 | 0.000448 | false | false | not_applicable |
| q18 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 462 | 1526 | 4 | not_observed | not_observed | 1530 | 0.000677 | false | false | not_applicable |
| q18 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 4532 | 2036 | 204 | 0 | not_observed | 2240 | 0.000428 | false | false | not_applicable |
| q19 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 332 | 1909 | 4 | not_observed | not_observed | 1913 | 0.000845 | false | false | not_applicable |
| q19 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 3509 | 2344 | 109 | 0 | not_observed | 2453 | 0.000417 | false | false | not_applicable |
| q20 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 637 | 1901 | 4 | not_observed | not_observed | 1905 | 0.000842 | false | false | not_applicable |
| q20 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | OpenAI | 1055 | 92 | 28 | 0 | 0 | 120 | 0.000031 | false | false | not_applicable |
| q20 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 5370 | 2321 | 209 | 0 | not_observed | 2530 | 0.000474 | false | false | not_applicable |
| q21 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 692 | 1764 | 4 | not_observed | not_observed | 1768 | 0.000781 | false | false | not_applicable |
| q21 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2756 | 2308 | 211 | 0 | not_observed | 2519 | 0.000473 | false | false | not_applicable |
| q22 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 566 | 1713 | 4 | not_observed | not_observed | 1717 | 0.000759 | false | false | not_applicable |
| q22 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 3619 | 2206 | 190 | 0 | not_observed | 2396 | 0.000445 | false | false | not_applicable |
| q23 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 334 | 1853 | 4 | not_observed | not_observed | 1857 | 0.000821 | false | false | not_applicable |
| q23 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | OpenAI | 954 | 88 | 27 | 0 | 0 | 115 | 0.000029 | false | false | not_applicable |
| q23 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2434 | 2369 | 126 | 0 | not_observed | 2495 | 0.000431 | false | false | not_applicable |
| q24 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 585 | 1775 | 4 | not_observed | not_observed | 1779 | 0.000786 | false | false | not_applicable |
| q24 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 4858 | 2259 | 153 | 0 | not_observed | 2412 | 0.000431 | false | false | not_applicable |
| q25 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 340 | 1961 | 4 | not_observed | not_observed | 1965 | 0.000868 | false | false | not_applicable |
| q25 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 6454 | 2488 | 170 | 0 | not_observed | 2658 | 0.000475 | false | false | not_applicable |
| q26 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 531 | 1782 | 4 | not_observed | not_observed | 1786 | 0.000789 | false | false | not_applicable |
| q26 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | OpenAI | 1072 | 89 | 22 | 0 | 0 | 111 | 0.000027 | false | false | not_applicable |
| q26 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 5806 | 2312 | 312 | 0 | not_observed | 2624 | 0.000534 | false | false | not_applicable |
| q27 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 477 | 1287 | 4 | not_observed | not_observed | 1291 | 0.000572 | false | false | not_applicable |
| q27 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 4505 | 1764 | 167 | 0 | not_observed | 1931 | 0.000365 | false | false | not_applicable |
| q28 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 801 | 1939 | 4 | not_observed | not_observed | 1943 | 0.000858 | false | false | not_applicable |
| q28 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 2889 | 2403 | 71 | 0 | not_observed | 2474 | 0.000403 | false | false | not_applicable |
| q29 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 411 | 1807 | 4 | not_observed | not_observed | 1811 | 0.000800 | false | false | not_applicable |
| q29 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 3391 | 2213 | 149 | 0 | not_observed | 2362 | 0.000421 | false | false | not_applicable |
| q30 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 328 | 1676 | 4 | not_observed | not_observed | 1680 | 0.000743 | false | false | not_applicable |
| q30 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2913 | 2191 | 190 | 0 | not_observed | 2381 | 0.000443 | false | false | not_applicable |

## 6. Model role 汇总

| role | calls | total_ms | median_ms | total_tokens | token observed/unknown | cost_usd | cost observed/unknown |
| :-- | --: | --: | --: | --: | :-- | --: | :-- |
| sufficiency_judge | 31 | 17770 | 535 | 53641 | 53641/0 | 0.023713 | 0.023713/0 |
| generator | 29 | 108449 | 3509 | 69226 | 69226/0 | 0.012632 | 0.012632/0 |
| subquery_generator | 6 | 10383 | 1064 | 685 | 685/0 | 0.000171 | 0.000171/0 |
| rewrite_query | 1 | 824 | 824 | 75 | 75/0 | 0.000016 | 0.000016/0 |

## 7. 批次分析

- service latency min / median / p95 / max / total ms: 1886 / 3891 / 8536 / 12266 / 137674
- model_call_count: 67
- total_tokens: 123627
- total_tokens observed subtotal / unknown records: 123627 / 0
- total_estimated_cost_usd: 0.036531
- estimated cost observed subtotal / unknown records: 0.036531 / 0
- slowest_cases: q16=12266ms, q01=9325ms, q26=7571ms, q20=7263ms, q08=7108ms
- highest_token_cases: q09=4720, q25=4623, q20=4555, q26=4521, q01=4518
- highest_cost_cases: q02=$0.001589, q09=$0.001378, q26=$0.001350, q20=$0.001346, q25=$0.001343
- engine_init_outliers (>=100ms): q01=3209ms
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
