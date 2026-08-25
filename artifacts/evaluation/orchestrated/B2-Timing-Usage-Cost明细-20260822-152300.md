# B2 Timing-Usage-Cost 明细

> 来源：当前 live CanonicalExecutionRecord（CER）确定性投影。
> `engine_ms` 已包含 `engine_init_ms`；两者分别展示，不相加作为总耗时。
> `service_unaccounted_ms = service_total_ms - queue_wait_ms - engine_ms`；`engine_observed_components_ms` 仅用于观察已记录的 engine 内部组件。
> 当前 CER 未记录独立 `merge_ms` / `build_response_ms` 时保留 `not_observed`；rerank 关闭时记为 `not_applicable`。

## 0. 运行信息

- profile: orchestrated
- cases: 30
- run_id: eval_1ffb699473ab
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
| final_status | ANSWERED: 25；REFUSED: 5 |
| model_role | generator: 25；rewrite_query: 5；subquery_generator: 6；sufficiency_judge: 35 |
| provider | deepseek: 35；openrouter: 36 |
| model | deepseek-v4-flash: 35；openai/gpt-4o-mini: 36 |
| upstream_provider | Azure: 16；OpenAI: 20 |
| usage ledger | full=30/30 |

## 2. Timing 总体逐题表

| qid | route | status | service_total_ms | engine_ms | pipeline_total_ms | engine_init_ms | queue_wait_ms | observed_model_ms | retrieval_ms | engine_observed_components_ms | service_unaccounted_ms | tokens | cost_usd |
| :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| q01 | DIRECT | ANSWERED | 12075 | 12067 | 6029 | 6024 | 0 | 5799 | 225 | 12048 | 8 | 6020 | 0.002241 |
| q02 | DIRECT | REFUSED | 4642 | 4633 | 4633 | 0 | 0 | 4589 | 40 | 4629 | 9 | 7527 | 0.003526 |
| q03 | DECOMPOSE | ANSWERED | 6099 | 6090 | 6089 | 0 | 0 | 5888 | 194 | 6081 | 8 | 6163 | 0.002243 |
| q04 | DIRECT | ANSWERED | 2966 | 2958 | 2957 | 0 | 0 | 2940 | 14 | 2954 | 8 | 5824 | 0.002115 |
| q05 | DIRECT | ANSWERED | 5615 | 5608 | 5607 | 0 | 0 | 5585 | 20 | 5604 | 8 | 5291 | 0.002028 |
| q06 | DIRECT | REFUSED | 4864 | 4855 | 4854 | 0 | 0 | 4816 | 33 | 4849 | 9 | 6757 | 0.003184 |
| q07 | DIRECT | ANSWERED | 5545 | 5538 | 5537 | 0 | 0 | 5521 | 14 | 5535 | 8 | 6418 | 0.002473 |
| q08 | DECOMPOSE | ANSWERED | 9265 | 9258 | 9257 | 0 | 0 | 9032 | 220 | 9252 | 7 | 5572 | 0.002150 |
| q09 | DIRECT | ANSWERED | 3025 | 3018 | 3017 | 0 | 0 | 2999 | 14 | 3013 | 7 | 6619 | 0.002323 |
| q10 | DIRECT | ANSWERED | 4693 | 4685 | 4684 | 0 | 0 | 4664 | 17 | 4681 | 8 | 6012 | 0.002262 |
| q11 | DIRECT | ANSWERED | 5156 | 5149 | 5148 | 0 | 0 | 5130 | 15 | 5144 | 7 | 6118 | 0.002243 |
| q12 | DIRECT | ANSWERED | 4117 | 4109 | 4108 | 0 | 0 | 4089 | 17 | 4105 | 8 | 6130 | 0.002195 |
| q13 | DIRECT | ANSWERED | 4938 | 4931 | 4930 | 0 | 0 | 4912 | 14 | 4926 | 8 | 6100 | 0.002258 |
| q14 | DIRECT | ANSWERED | 4701 | 4693 | 4692 | 0 | 0 | 4671 | 18 | 4689 | 8 | 5863 | 0.002149 |
| q15 | DIRECT | ANSWERED | 3914 | 3906 | 3905 | 0 | 0 | 3882 | 18 | 3901 | 8 | 6067 | 0.002196 |
| q16 | DECOMPOSE | ANSWERED | 8769 | 8762 | 8761 | 0 | 0 | 8484 | 272 | 8756 | 7 | 5411 | 0.002092 |
| q17 | DIRECT | ANSWERED | 4510 | 4502 | 4501 | 0 | 0 | 4472 | 26 | 4498 | 8 | 6085 | 0.002236 |
| q18 | DIRECT | ANSWERED | 6939 | 6931 | 6930 | 0 | 0 | 6908 | 19 | 6927 | 8 | 6028 | 0.002335 |
| q19 | DIRECT | REFUSED | 4563 | 4556 | 4555 | 0 | 0 | 4513 | 37 | 4550 | 8 | 7483 | 0.003509 |
| q20 | DECOMPOSE | ANSWERED | 5864 | 5856 | 5854 | 0 | 0 | 5646 | 200 | 5846 | 9 | 6670 | 0.002428 |
| q21 | DIRECT | ANSWERED | 5565 | 5557 | 5556 | 0 | 0 | 5539 | 15 | 5553 | 8 | 6451 | 0.002431 |
| q22 | DIRECT | ANSWERED | 5130 | 5121 | 5120 | 0 | 0 | 5102 | 15 | 5117 | 8 | 5750 | 0.002140 |
| q23 | DECOMPOSE | ANSWERED | 5982 | 5974 | 5973 | 0 | 0 | 5730 | 237 | 5967 | 8 | 6538 | 0.002425 |
| q24 | DIRECT | ANSWERED | 5189 | 5181 | 5180 | 0 | 0 | 5162 | 15 | 5177 | 8 | 5641 | 0.002115 |
| q25 | DIRECT | ANSWERED | 5293 | 5286 | 5285 | 0 | 0 | 5266 | 16 | 5282 | 8 | 5959 | 0.002254 |
| q26 | DECOMPOSE | ANSWERED | 9093 | 9085 | 9617 | 0 | 0 | 9420 | 191 | 9611 | 8 | 6181 | 0.002340 |
| q27 | DIRECT | REFUSED | 5824 | 5816 | 5815 | 0 | 0 | 5770 | 37 | 5808 | 8 | 6996 | 0.003497 |
| q28 | DIRECT | REFUSED | 5269 | 5262 | 5261 | 0 | 0 | 5218 | 39 | 5257 | 7 | 7607 | 0.003614 |
| q29 | DIRECT | ANSWERED | 4078 | 4071 | 4070 | 0 | 0 | 4034 | 31 | 4065 | 7 | 6290 | 0.002376 |
| q30 | DIRECT | ANSWERED | 4255 | 4247 | 4247 | 0 | 0 | 4231 | 12 | 4243 | 8 | 6491 | 0.002413 |

## 3. Timing 阶段明细表

| qid | engine_init_ms | decompose_ms | rewrite_ms | retrieve_total_ms | first_retrieve_ms | second_retrieve_ms | merge_ms | rerank_ms | first_suff_ms | second_suff_ms | generate_ms | generator_llm_ms | build_response_ms |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| q01 | 6024 | not_applicable | 0 | 225 | 225 | 0 | not_observed | not_applicable | 1869 | 0 | 3933 | 3931 | not_observed |
| q02 | 0 | not_applicable | 1612 | 40 | 22 | 18 | not_observed | not_applicable | 1560 | 1419 | 0 | 0 | not_observed |
| q03 | 0 | 1687 | 0 | 194 | 194 | 0 | not_observed | not_applicable | 1613 | 0 | 2590 | 2588 | not_observed |
| q04 | 0 | not_applicable | 0 | 14 | 14 | 0 | not_observed | not_applicable | 1574 | 0 | 1368 | 1366 | not_observed |
| q05 | 0 | not_applicable | 0 | 20 | 20 | 0 | not_observed | not_applicable | 2289 | 0 | 3297 | 3296 | not_observed |
| q06 | 0 | not_applicable | 786 | 33 | 21 | 12 | not_observed | not_applicable | 1932 | 2100 | 0 | 0 | not_observed |
| q07 | 0 | not_applicable | 0 | 14 | 14 | 0 | not_observed | not_applicable | 2756 | 0 | 2767 | 2766 | not_observed |
| q08 | 0 | 1887 | 0 | 220 | 220 | 0 | not_observed | not_applicable | 2331 | 0 | 4815 | 4814 | not_observed |
| q09 | 0 | not_applicable | 0 | 14 | 14 | 0 | not_observed | not_applicable | 1340 | 0 | 1662 | 1660 | not_observed |
| q10 | 0 | not_applicable | 0 | 17 | 17 | 0 | not_observed | not_applicable | 2142 | 0 | 2524 | 2522 | not_observed |
| q11 | 0 | not_applicable | 0 | 15 | 15 | 0 | not_observed | not_applicable | 1962 | 0 | 3170 | 3168 | not_observed |
| q12 | 0 | not_applicable | 0 | 17 | 17 | 0 | not_observed | not_applicable | 1827 | 0 | 2263 | 2262 | not_observed |
| q13 | 0 | not_applicable | 0 | 14 | 14 | 0 | not_observed | not_applicable | 2358 | 0 | 2556 | 2554 | not_observed |
| q14 | 0 | not_applicable | 0 | 18 | 18 | 0 | not_observed | not_applicable | 1829 | 0 | 2844 | 2842 | not_observed |
| q15 | 0 | not_applicable | 0 | 18 | 18 | 0 | not_observed | not_applicable | 2176 | 0 | 1708 | 1707 | not_observed |
| q16 | 0 | 919 | 0 | 272 | 272 | 0 | not_observed | not_applicable | 1880 | 0 | 5688 | 5686 | not_observed |
| q17 | 0 | not_applicable | 0 | 26 | 26 | 0 | not_observed | not_applicable | 1792 | 0 | 2682 | 2680 | not_observed |
| q18 | 0 | not_applicable | 0 | 19 | 19 | 0 | not_observed | not_applicable | 2299 | 0 | 4612 | 4610 | not_observed |
| q19 | 0 | not_applicable | 832 | 37 | 20 | 18 | not_observed | not_applicable | 1963 | 1720 | 0 | 0 | not_observed |
| q20 | 0 | 979 | 0 | 200 | 200 | 0 | not_observed | not_applicable | 2169 | 0 | 2500 | 2498 | not_observed |
| q21 | 0 | not_applicable | 0 | 15 | 15 | 0 | not_observed | not_applicable | 2062 | 0 | 3479 | 3477 | not_observed |
| q22 | 0 | not_applicable | 0 | 15 | 15 | 0 | not_observed | not_applicable | 1908 | 0 | 3197 | 3195 | not_observed |
| q23 | 0 | 1605 | 0 | 237 | 237 | 0 | not_observed | not_applicable | 2556 | 0 | 1571 | 1569 | not_observed |
| q24 | 0 | not_applicable | 0 | 15 | 15 | 0 | not_observed | not_applicable | 1666 | 0 | 3498 | 3496 | not_observed |
| q25 | 0 | not_applicable | 0 | 16 | 16 | 0 | not_observed | not_applicable | 2617 | 0 | 2651 | 2649 | not_observed |
| q26 | 0 | 2507 | 0 | 191 | 191 | 0 | not_observed | not_applicable | 2041 | 0 | 4875 | 4873 | not_observed |
| q27 | 0 | not_applicable | 943 | 37 | 24 | 14 | not_observed | not_applicable | 2642 | 2188 | 0 | 0 | not_observed |
| q28 | 0 | not_applicable | 1503 | 39 | 23 | 15 | not_observed | not_applicable | 1459 | 2259 | 0 | 0 | not_observed |
| q29 | 0 | not_applicable | 0 | 31 | 31 | 0 | not_observed | not_applicable | 2201 | 0 | 1836 | 1834 | not_observed |
| q30 | 0 | not_applicable | 0 | 12 | 12 | 0 | not_observed | not_applicable | 2204 | 0 | 2029 | 2027 | not_observed |

## 4. Token / Usage 汇总表

| qid | route | status | full_ledger | expected_roles | observed_roles | missing_roles | calls | prompt_tokens | completion_tokens | reasoning_tokens | cached_tokens | cache_write_tokens | total_tokens | observed_model_ms | generator_llm_ms | cost_usd |
| :-- | :-- | :-- | :--: | :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| q01 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5594 | 426 | not_observed | not_observed | not_observed | 6020 | 5799 | 3931 | 0.002241 |
| q02 | DIRECT | REFUSED | true | sufficiency_judge；rewrite_query | rewrite_query；sufficiency_judge | not_applicable | 3 | 7253 | 274 | not_observed | not_observed | not_observed | 7527 | 4589 | 0 | 0.003526 |
| q03 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 5837 | 326 | not_observed | not_observed | not_observed | 6163 | 5888 | 2588 | 0.002243 |
| q04 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5576 | 248 | not_observed | not_observed | not_observed | 5824 | 2940 | 1366 | 0.002115 |
| q05 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4927 | 364 | not_observed | not_observed | not_observed | 5291 | 5585 | 3296 | 0.002028 |
| q06 | DIRECT | REFUSED | true | sufficiency_judge；rewrite_query | rewrite_query；sufficiency_judge | not_applicable | 3 | 6483 | 274 | not_observed | not_observed | not_observed | 6757 | 4816 | 0 | 0.003184 |
| q07 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5882 | 536 | not_observed | not_observed | not_observed | 6418 | 5521 | 2766 | 0.002473 |
| q08 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 5036 | 536 | not_observed | not_observed | not_observed | 5572 | 9032 | 4814 | 0.002150 |
| q09 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 6358 | 261 | not_observed | not_observed | not_observed | 6619 | 2999 | 1660 | 0.002323 |
| q10 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5652 | 360 | not_observed | not_observed | not_observed | 6012 | 4664 | 2522 | 0.002262 |
| q11 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5764 | 354 | not_observed | not_observed | not_observed | 6118 | 5130 | 3168 | 0.002243 |
| q12 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5835 | 295 | not_observed | not_observed | not_observed | 6130 | 4089 | 2262 | 0.002195 |
| q13 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5747 | 353 | not_observed | not_observed | not_observed | 6100 | 4912 | 2554 | 0.002258 |
| q14 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5585 | 278 | not_observed | not_observed | not_observed | 5863 | 4671 | 2842 | 0.002149 |
| q15 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5803 | 264 | not_observed | not_observed | not_observed | 6067 | 3882 | 1707 | 0.002196 |
| q16 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 4869 | 542 | not_observed | not_observed | not_observed | 5411 | 8484 | 5686 | 0.002092 |
| q17 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5701 | 384 | not_observed | not_observed | not_observed | 6085 | 4472 | 2680 | 0.002236 |
| q18 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5521 | 507 | not_observed | not_observed | not_observed | 6028 | 6908 | 4610 | 0.002335 |
| q19 | DIRECT | REFUSED | true | sufficiency_judge；rewrite_query | rewrite_query；sufficiency_judge | not_applicable | 3 | 7205 | 278 | not_observed | not_observed | not_observed | 7483 | 4513 | 0 | 0.003509 |
| q20 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 6303 | 367 | not_observed | not_observed | not_observed | 6670 | 5646 | 2498 | 0.002428 |
| q21 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5903 | 548 | not_observed | not_observed | not_observed | 6451 | 5539 | 3477 | 0.002431 |
| q22 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5397 | 353 | not_observed | not_observed | not_observed | 5750 | 5102 | 3195 | 0.002140 |
| q23 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 6131 | 407 | not_observed | not_observed | not_observed | 6538 | 5730 | 1569 | 0.002425 |
| q24 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5270 | 371 | not_observed | not_observed | not_observed | 5641 | 5162 | 3496 | 0.002115 |
| q25 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5502 | 457 | not_observed | not_observed | not_observed | 5959 | 5266 | 2649 | 0.002254 |
| q26 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 5579 | 602 | not_observed | not_observed | not_observed | 6181 | 9420 | 4873 | 0.002340 |
| q27 | DIRECT | REFUSED | true | sufficiency_judge；rewrite_query | rewrite_query；sufficiency_judge | not_applicable | 3 | 6488 | 508 | not_observed | not_observed | not_observed | 6996 | 5770 | 0 | 0.003497 |
| q28 | DIRECT | REFUSED | true | sufficiency_judge；rewrite_query | rewrite_query；sufficiency_judge | not_applicable | 3 | 7275 | 332 | not_observed | not_observed | not_observed | 7607 | 5218 | 0 | 0.003614 |
| q29 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 5895 | 395 | not_observed | not_observed | not_observed | 6290 | 4034 | 1834 | 0.002376 |
| q30 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 6106 | 385 | not_observed | not_observed | not_observed | 6491 | 4231 | 2027 | 0.002413 |

## 5. Model-call 明细

| qid | idx | role | stage | provider | model | upstream | latency_ms | prompt_tokens | completion_tokens | reasoning_tokens | cached_tokens | total_tokens | cost_usd | timeout | api_error | error_type |
| :-- | --: | :-- | :-- | :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | --: | :--: | :--: | :-- |
| q01 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1868 | 3460 | 198 | not_observed | not_observed | 3658 | 0.001784 | false | false | not_applicable |
| q01 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 3931 | 2134 | 228 | 0 | not_observed | 2362 | 0.000457 | false | false | not_applicable |
| q02 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1560 | 3537 | 121 | not_observed | not_observed | 3658 | 0.001716 | false | false | not_applicable |
| q02 | 2 | sufficiency_judge | legacy_second_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1419 | 3651 | 142 | not_observed | not_observed | 3793 | 0.001794 | false | false | not_applicable |
| q02 | 3 | rewrite_query | rewrite_query | openrouter | openai/gpt-4o-mini | Azure | 1610 | 65 | 11 | 0 | 0 | 76 | 0.000016 | false | false | not_applicable |
| q03 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1613 | 3625 | 167 | not_observed | not_observed | 3792 | 0.001815 | false | false | not_applicable |
| q03 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | Azure | 1687 | 86 | 24 | 0 | 0 | 110 | 0.000027 | false | false | not_applicable |
| q03 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 2588 | 2126 | 135 | 0 | not_observed | 2261 | 0.000400 | false | false | not_applicable |
| q04 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1574 | 3492 | 163 | not_observed | not_observed | 3655 | 0.001752 | false | false | not_applicable |
| q04 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1366 | 2084 | 85 | 0 | not_observed | 2169 | 0.000364 | false | false | not_applicable |
| q05 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2289 | 3154 | 216 | not_observed | not_observed | 3370 | 0.001673 | false | false | not_applicable |
| q05 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 3296 | 1773 | 148 | 0 | not_observed | 1921 | 0.000355 | false | false | not_applicable |
| q06 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1932 | 3237 | 128 | not_observed | not_observed | 3365 | 0.001593 | false | false | not_applicable |
| q06 | 2 | sufficiency_judge | legacy_second_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2099 | 3178 | 132 | not_observed | not_observed | 3310 | 0.001573 | false | false | not_applicable |
| q06 | 3 | rewrite_query | rewrite_query | openrouter | openai/gpt-4o-mini | OpenAI | 785 | 68 | 14 | 0 | 0 | 82 | 0.000019 | false | false | not_applicable |
| q07 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2755 | 3648 | 293 | not_observed | not_observed | 3941 | 0.001992 | false | false | not_applicable |
| q07 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2766 | 2234 | 243 | 0 | not_observed | 2477 | 0.000481 | false | false | not_applicable |
| q08 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2331 | 3152 | 221 | not_observed | not_observed | 3373 | 0.001679 | false | false | not_applicable |
| q08 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | Azure | 1887 | 89 | 31 | 0 | 0 | 120 | 0.000032 | false | false | not_applicable |
| q08 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 4814 | 1795 | 284 | 0 | not_observed | 2079 | 0.000440 | false | false | not_applicable |
| q09 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1339 | 3843 | 137 | not_observed | not_observed | 3980 | 0.001872 | false | false | not_applicable |
| q09 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1660 | 2515 | 124 | 0 | not_observed | 2639 | 0.000452 | false | false | not_applicable |
| q10 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2142 | 3498 | 255 | not_observed | not_observed | 3753 | 0.001876 | false | false | not_applicable |
| q10 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 2522 | 2154 | 105 | 0 | not_observed | 2259 | 0.000386 | false | false | not_applicable |
| q11 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1962 | 3528 | 198 | not_observed | not_observed | 3726 | 0.001814 | false | false | not_applicable |
| q11 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 3168 | 2236 | 156 | 0 | not_observed | 2392 | 0.000429 | false | false | not_applicable |
| q12 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1827 | 3562 | 153 | not_observed | not_observed | 3715 | 0.001769 | false | false | not_applicable |
| q12 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2262 | 2273 | 142 | 0 | not_observed | 2415 | 0.000426 | false | false | not_applicable |
| q13 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2358 | 3475 | 245 | not_observed | not_observed | 3720 | 0.001852 | false | false | not_applicable |
| q13 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 2554 | 2272 | 108 | 0 | not_observed | 2380 | 0.000406 | false | false | not_applicable |
| q14 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1829 | 3515 | 174 | not_observed | not_observed | 3689 | 0.001776 | false | false | not_applicable |
| q14 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 2842 | 2070 | 104 | 0 | not_observed | 2174 | 0.000373 | false | false | not_applicable |
| q15 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2175 | 3550 | 191 | not_observed | not_observed | 3741 | 0.001814 | false | false | not_applicable |
| q15 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1707 | 2253 | 73 | 0 | not_observed | 2326 | 0.000382 | false | false | not_applicable |
| q16 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1879 | 3098 | 192 | not_observed | not_observed | 3290 | 0.001617 | false | false | not_applicable |
| q16 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | OpenAI | 919 | 90 | 23 | 0 | 0 | 113 | 0.000027 | false | false | not_applicable |
| q16 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 5686 | 1681 | 327 | 0 | not_observed | 2008 | 0.000448 | false | false | not_applicable |
| q17 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1792 | 3513 | 183 | not_observed | not_observed | 3696 | 0.001787 | false | false | not_applicable |
| q17 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2680 | 2188 | 201 | 0 | not_observed | 2389 | 0.000449 | false | false | not_applicable |
| q18 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2298 | 3458 | 278 | not_observed | not_observed | 3736 | 0.001888 | false | false | not_applicable |
| q18 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 4610 | 2063 | 229 | 0 | not_observed | 2292 | 0.000447 | false | false | not_applicable |
| q19 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1962 | 3569 | 124 | not_observed | not_observed | 3693 | 0.001734 | false | false | not_applicable |
| q19 | 2 | sufficiency_judge | legacy_second_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1720 | 3570 | 142 | not_observed | not_observed | 3712 | 0.001758 | false | false | not_applicable |
| q19 | 3 | rewrite_query | rewrite_query | openrouter | openai/gpt-4o-mini | OpenAI | 831 | 66 | 12 | 0 | 0 | 78 | 0.000017 | false | false | not_applicable |
| q20 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2169 | 3816 | 216 | not_observed | not_observed | 4032 | 0.001964 | false | false | not_applicable |
| q20 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | OpenAI | 979 | 92 | 28 | 0 | 0 | 120 | 0.000031 | false | false | not_applicable |
| q20 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2498 | 2395 | 123 | 0 | not_observed | 2518 | 0.000433 | false | false | not_applicable |
| q21 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2062 | 3640 | 224 | not_observed | not_observed | 3864 | 0.001897 | false | false | not_applicable |
| q21 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 3477 | 2263 | 324 | 0 | not_observed | 2587 | 0.000534 | false | false | not_applicable |
| q22 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1907 | 3406 | 182 | not_observed | not_observed | 3588 | 0.001739 | false | false | not_applicable |
| q22 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 3195 | 1991 | 171 | 0 | not_observed | 2162 | 0.000401 | false | false | not_applicable |
| q23 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2556 | 3669 | 274 | not_observed | not_observed | 3943 | 0.001976 | false | false | not_applicable |
| q23 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | Azure | 1605 | 88 | 28 | 0 | 0 | 116 | 0.000030 | false | false | not_applicable |
| q23 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1569 | 2374 | 105 | 0 | not_observed | 2479 | 0.000419 | false | false | not_applicable |
| q24 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1666 | 3331 | 189 | not_observed | not_observed | 3520 | 0.001715 | false | false | not_applicable |
| q24 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 3496 | 1939 | 182 | 0 | not_observed | 2121 | 0.000400 | false | false | not_applicable |
| q25 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2617 | 3355 | 252 | not_observed | not_observed | 3607 | 0.001809 | false | false | not_applicable |
| q25 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2649 | 2147 | 205 | 0 | not_observed | 2352 | 0.000445 | false | false | not_applicable |
| q26 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2040 | 3398 | 217 | not_observed | not_observed | 3615 | 0.001782 | false | false | not_applicable |
| q26 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | OpenAI | 2507 | 89 | 22 | 0 | 0 | 111 | 0.000027 | false | false | not_applicable |
| q26 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 4873 | 2092 | 363 | 0 | not_observed | 2455 | 0.000532 | false | false | not_applicable |
| q27 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2642 | 3209 | 250 | not_observed | not_observed | 3459 | 0.001742 | false | false | not_applicable |
| q27 | 2 | sufficiency_judge | legacy_second_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2188 | 3210 | 246 | not_observed | not_observed | 3456 | 0.001737 | false | false | not_applicable |
| q27 | 3 | rewrite_query | rewrite_query | openrouter | openai/gpt-4o-mini | OpenAI | 941 | 69 | 12 | 0 | 0 | 81 | 0.000018 | false | false | not_applicable |
| q28 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1459 | 3606 | 160 | not_observed | not_observed | 3766 | 0.001798 | false | false | not_applicable |
| q28 | 2 | sufficiency_judge | legacy_second_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2258 | 3606 | 162 | not_observed | not_observed | 3768 | 0.001800 | false | false | not_applicable |
| q28 | 3 | rewrite_query | rewrite_query | openrouter | openai/gpt-4o-mini | Azure | 1501 | 63 | 10 | 0 | 0 | 73 | 0.000015 | false | false | not_applicable |
| q29 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2200 | 3682 | 259 | not_observed | not_observed | 3941 | 0.001962 | false | false | not_applicable |
| q29 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1834 | 2213 | 136 | 0 | not_observed | 2349 | 0.000414 | false | false | not_applicable |
| q30 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 2204 | 3719 | 260 | not_observed | not_observed | 3979 | 0.001980 | false | false | not_applicable |
| q30 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2027 | 2387 | 125 | 0 | not_observed | 2512 | 0.000433 | false | false | not_applicable |

## 6. Model role 汇总

| role | calls | total_ms | median_ms | total_tokens | token observed/unknown | cost_usd | cost observed/unknown |
| :-- | --: | --: | --: | --: | :-- | --: | :-- |
| sufficiency_judge | 35 | 70690 | 2040 | 128904 | 128904/0 | 0.062828 | 0.062828/0 |
| generator | 25 | 74070 | 2680 | 58078 | 58078/0 | 0.010703 | 0.010703/0 |
| subquery_generator | 6 | 9584 | 1646 | 690 | 690/0 | 0.000174 | 0.000174/0 |
| rewrite_query | 5 | 5668 | 941 | 390 | 390/0 | 0.000085 | 0.000085/0 |

## 7. 批次分析

- service latency min / median / p95 / max / total ms: 2966 / 5173 / 9188 / 12075 / 167940
- model_call_count: 71
- total_tokens: 188062
- total_tokens observed subtotal / unknown records: 188062 / 0
- total_estimated_cost_usd: 0.073791
- estimated cost observed subtotal / unknown records: 0.073791 / 0
- slowest_cases: q01=12075ms, q08=9265ms, q26=9093ms, q16=8769ms, q18=6939ms
- highest_token_cases: q28=7607, q02=7527, q19=7483, q27=6996, q06=6757
- highest_cost_cases: q28=$0.003614, q02=$0.003526, q19=$0.003509, q27=$0.003497, q06=$0.003184
- engine_init_outliers (>=100ms): q01=6024ms
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
