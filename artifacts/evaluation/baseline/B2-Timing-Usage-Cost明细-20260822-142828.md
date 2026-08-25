# B2 Timing-Usage-Cost 明细

> 来源：当前 live CanonicalExecutionRecord（CER）确定性投影。
> `engine_ms` 已包含 `engine_init_ms`；两者分别展示，不相加作为总耗时。
> `service_unaccounted_ms = service_total_ms - queue_wait_ms - engine_ms`；`engine_observed_components_ms` 仅用于观察已记录的 engine 内部组件。
> 当前 CER 未记录独立 `merge_ms` / `build_response_ms` 时保留 `not_observed`；rerank 关闭时记为 `not_applicable`。

## 0. 运行信息

- profile: baseline
- cases: 30
- run_id: eval_b4d7474e4c62
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
| upstream_provider | Azure: 16；OpenAI: 20 |
| usage ledger | full=30/30 |

## 2. Timing 总体逐题表

| qid | route | status | service_total_ms | engine_ms | pipeline_total_ms | engine_init_ms | queue_wait_ms | observed_model_ms | retrieval_ms | engine_observed_components_ms | service_unaccounted_ms | tokens | cost_usd |
| :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| q01 | DIRECT | ANSWERED | 9215 | 9207 | 6482 | 2697 | 0 | 6441 | 35 | 9173 | 8 | 4010 | 0.001186 |
| q02 | DIRECT | REFUSED | 4520 | 4513 | 4512 | 0 | 0 | 4248 | 255 | 4503 | 8 | 3706 | 0.001622 |
| q03 | DECOMPOSE | ANSWERED | 4756 | 4748 | 4747 | 0 | 0 | 4621 | 116 | 4737 | 8 | 4065 | 0.001176 |
| q04 | DIRECT | ANSWERED | 2923 | 2915 | 2914 | 0 | 0 | 2801 | 109 | 2911 | 8 | 3863 | 0.001114 |
| q05 | DIRECT | ANSWERED | 2848 | 2840 | 2840 | 0 | 0 | 2794 | 43 | 2837 | 8 | 3195 | 0.000919 |
| q06 | DIRECT | ANSWERED | 2780 | 2770 | 2770 | 0 | 0 | 2678 | 88 | 2766 | 9 | 3400 | 0.000981 |
| q07 | DIRECT | ANSWERED | 3325 | 3317 | 3316 | 0 | 0 | 3297 | 16 | 3314 | 8 | 4307 | 0.001287 |
| q08 | DECOMPOSE | ANSWERED | 5200 | 5191 | 5190 | 0 | 0 | 4974 | 212 | 5186 | 9 | 3529 | 0.001064 |
| q09 | DIRECT | ANSWERED | 3471 | 3464 | 3463 | 0 | 0 | 3436 | 22 | 3457 | 8 | 4728 | 0.001376 |
| q10 | DIRECT | ANSWERED | 4161 | 4152 | 4152 | 0 | 0 | 4122 | 26 | 4149 | 9 | 3982 | 0.001151 |
| q11 | DIRECT | ANSWERED | 5156 | 5147 | 5146 | 0 | 0 | 5127 | 17 | 5143 | 9 | 4152 | 0.001208 |
| q12 | DIRECT | ANSWERED | 2852 | 2843 | 2842 | 0 | 0 | 2817 | 22 | 2839 | 9 | 4185 | 0.001208 |
| q13 | DIRECT | ANSWERED | 3331 | 3322 | 3322 | 0 | 0 | 3301 | 17 | 3318 | 9 | 4114 | 0.001172 |
| q14 | DIRECT | ANSWERED | 2477 | 2469 | 2468 | 0 | 0 | 2434 | 31 | 2466 | 9 | 3831 | 0.001105 |
| q15 | DIRECT | ANSWERED | 3639 | 3631 | 3630 | 0 | 0 | 3613 | 13 | 3626 | 8 | 4034 | 0.001138 |
| q16 | DECOMPOSE | ANSWERED | 6059 | 6051 | 6050 | 0 | 0 | 5531 | 514 | 6046 | 8 | 3466 | 0.001079 |
| q17 | DIRECT | ANSWERED | 4957 | 4949 | 4948 | 0 | 0 | 4874 | 66 | 4941 | 8 | 4105 | 0.001208 |
| q18 | DIRECT | ANSWERED | 2640 | 2632 | 2631 | 0 | 0 | 2606 | 23 | 2628 | 8 | 3778 | 0.001095 |
| q19 | DIRECT | ANSWERED | 3181 | 3173 | 3172 | 0 | 0 | 3140 | 29 | 3169 | 8 | 4330 | 0.001242 |
| q20 | DECOMPOSE | ANSWERED | 5650 | 5642 | 5641 | 0 | 0 | 5403 | 233 | 5636 | 9 | 4701 | 0.001369 |
| q21 | DIRECT | ANSWERED | 5914 | 5904 | 5903 | 0 | 0 | 5848 | 52 | 5900 | 10 | 4335 | 0.001307 |
| q22 | DIRECT | ANSWERED | 3824 | 3814 | 3814 | 0 | 0 | 3789 | 21 | 3811 | 10 | 3760 | 0.001109 |
| q23 | DECOMPOSE | ANSWERED | 3687 | 3678 | 3677 | 0 | 0 | 3462 | 210 | 3672 | 9 | 4460 | 0.001277 |
| q24 | DIRECT | ANSWERED | 3304 | 3295 | 3294 | 0 | 0 | 3278 | 13 | 3291 | 9 | 3620 | 0.001068 |
| q25 | DIRECT | ANSWERED | 3090 | 3081 | 3080 | 0 | 0 | 3062 | 14 | 3076 | 9 | 3920 | 0.001138 |
| q26 | DECOMPOSE | ANSWERED | 7843 | 7834 | 7832 | 0 | 0 | 7620 | 204 | 7824 | 10 | 4040 | 0.001201 |
| q27 | DIRECT | ANSWERED | 3023 | 3013 | 3012 | 0 | 0 | 2982 | 26 | 3008 | 10 | 3174 | 0.000915 |
| q28 | DIRECT | ANSWERED | 3045 | 3037 | 3037 | 0 | 0 | 3021 | 13 | 3033 | 8 | 4348 | 0.001241 |
| q29 | DIRECT | ANSWERED | 4763 | 4754 | 4753 | 0 | 0 | 4729 | 21 | 4750 | 9 | 4173 | 0.001222 |
| q30 | DIRECT | ANSWERED | 2697 | 2689 | 2688 | 0 | 0 | 2659 | 23 | 2683 | 8 | 4445 | 0.001291 |

## 3. Timing 阶段明细表

| qid | engine_init_ms | decompose_ms | rewrite_ms | retrieve_total_ms | first_retrieve_ms | second_retrieve_ms | merge_ms | rerank_ms | first_suff_ms | second_suff_ms | generate_ms | generator_llm_ms | build_response_ms |
| :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| q01 | 2697 | not_applicable | 0 | 35 | 35 | 0 | not_observed | not_applicable | 996 | 0 | 5448 | 5446 | not_observed |
| q02 | 0 | not_applicable | 2121 | 255 | 186 | 70 | not_observed | not_applicable | 1009 | 1119 | 0 | 0 | not_observed |
| q03 | 0 | 1754 | 0 | 116 | 116 | 0 | not_observed | not_applicable | 885 | 0 | 1984 | 1982 | not_observed |
| q04 | 0 | not_applicable | 0 | 109 | 109 | 0 | not_observed | not_applicable | 932 | 0 | 1872 | 1870 | not_observed |
| q05 | 0 | not_applicable | 0 | 43 | 43 | 0 | not_observed | not_applicable | 786 | 0 | 2009 | 2008 | not_observed |
| q06 | 0 | not_applicable | 0 | 88 | 88 | 0 | not_observed | not_applicable | 582 | 0 | 2098 | 2097 | not_observed |
| q07 | 0 | not_applicable | 0 | 16 | 16 | 0 | not_observed | not_applicable | 611 | 0 | 2687 | 2686 | not_observed |
| q08 | 0 | 877 | 0 | 212 | 212 | 0 | not_observed | not_applicable | 569 | 0 | 3530 | 3529 | not_observed |
| q09 | 0 | not_applicable | 0 | 22 | 22 | 0 | not_observed | not_applicable | 712 | 0 | 2726 | 2724 | not_observed |
| q10 | 0 | not_applicable | 0 | 26 | 26 | 0 | not_observed | not_applicable | 999 | 0 | 3125 | 3124 | not_observed |
| q11 | 0 | not_applicable | 0 | 17 | 17 | 0 | not_observed | not_applicable | 995 | 0 | 4133 | 4132 | not_observed |
| q12 | 0 | not_applicable | 0 | 22 | 22 | 0 | not_observed | not_applicable | 789 | 0 | 2030 | 2028 | not_observed |
| q13 | 0 | not_applicable | 0 | 17 | 17 | 0 | not_observed | not_applicable | 687 | 0 | 2617 | 2615 | not_observed |
| q14 | 0 | not_applicable | 0 | 31 | 31 | 0 | not_observed | not_applicable | 879 | 0 | 1557 | 1556 | not_observed |
| q15 | 0 | not_applicable | 0 | 13 | 13 | 0 | not_observed | not_applicable | 918 | 0 | 2698 | 2696 | not_observed |
| q16 | 0 | 962 | 0 | 514 | 514 | 0 | not_observed | not_applicable | 619 | 0 | 3952 | 3951 | not_observed |
| q17 | 0 | not_applicable | 0 | 66 | 66 | 0 | not_observed | not_applicable | 782 | 0 | 4094 | 4093 | not_observed |
| q18 | 0 | not_applicable | 0 | 23 | 23 | 0 | not_observed | not_applicable | 555 | 0 | 2052 | 2051 | not_observed |
| q19 | 0 | not_applicable | 0 | 29 | 29 | 0 | not_observed | not_applicable | 585 | 0 | 2558 | 2556 | not_observed |
| q20 | 0 | 1005 | 0 | 233 | 233 | 0 | not_observed | not_applicable | 683 | 0 | 3717 | 3715 | not_observed |
| q21 | 0 | not_applicable | 0 | 52 | 52 | 0 | not_observed | not_applicable | 479 | 0 | 5372 | 5370 | not_observed |
| q22 | 0 | not_applicable | 0 | 21 | 21 | 0 | not_observed | not_applicable | 611 | 0 | 3180 | 3179 | not_observed |
| q23 | 0 | 1018 | 0 | 210 | 210 | 0 | not_observed | not_applicable | 615 | 0 | 1832 | 1830 | not_observed |
| q24 | 0 | not_applicable | 0 | 13 | 13 | 0 | not_observed | not_applicable | 563 | 0 | 2718 | 2716 | not_observed |
| q25 | 0 | not_applicable | 0 | 14 | 14 | 0 | not_observed | not_applicable | 693 | 0 | 2372 | 2370 | not_observed |
| q26 | 0 | 1951 | 0 | 204 | 204 | 0 | not_observed | not_applicable | 553 | 0 | 5118 | 5116 | not_observed |
| q27 | 0 | not_applicable | 0 | 26 | 26 | 0 | not_observed | not_applicable | 816 | 0 | 2168 | 2166 | not_observed |
| q28 | 0 | not_applicable | 0 | 13 | 13 | 0 | not_observed | not_applicable | 669 | 0 | 2354 | 2352 | not_observed |
| q29 | 0 | not_applicable | 0 | 21 | 21 | 0 | not_observed | not_applicable | 687 | 0 | 4045 | 4043 | not_observed |
| q30 | 0 | not_applicable | 0 | 23 | 23 | 0 | not_observed | not_applicable | 571 | 0 | 2092 | 2090 | not_observed |

## 4. Token / Usage 汇总表

| qid | route | status | full_ledger | expected_roles | observed_roles | missing_roles | calls | prompt_tokens | completion_tokens | reasoning_tokens | cached_tokens | cache_write_tokens | total_tokens | observed_model_ms | generator_llm_ms | cost_usd |
| :-- | :-- | :-- | :--: | :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | --: | --: | --: | --: |
| q01 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3775 | 235 | not_observed | not_observed | not_observed | 4010 | 6441 | 5446 | 0.001186 |
| q02 | DIRECT | REFUSED | true | sufficiency_judge；rewrite_query | rewrite_query；sufficiency_judge | not_applicable | 3 | 3685 | 21 | not_observed | not_observed | not_observed | 3706 | 4248 | 0 | 0.001622 |
| q03 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 3903 | 162 | not_observed | not_observed | not_observed | 4065 | 4621 | 1982 | 0.001176 |
| q04 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3766 | 97 | not_observed | not_observed | not_observed | 3863 | 2801 | 1870 | 0.001114 |
| q05 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3044 | 151 | not_observed | not_observed | not_observed | 3195 | 2794 | 2008 | 0.000919 |
| q06 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3266 | 134 | not_observed | not_observed | not_observed | 3400 | 2678 | 2097 | 0.000981 |
| q07 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4074 | 233 | not_observed | not_observed | not_observed | 4307 | 3297 | 2686 | 0.001287 |
| q08 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 3189 | 340 | not_observed | not_observed | not_observed | 3529 | 4974 | 3529 | 0.001064 |
| q09 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4587 | 141 | not_observed | not_observed | not_observed | 4728 | 3436 | 2724 | 0.001376 |
| q10 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3855 | 127 | not_observed | not_observed | not_observed | 3982 | 4122 | 3124 | 0.001151 |
| q11 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3988 | 164 | not_observed | not_observed | not_observed | 4152 | 5127 | 4132 | 0.001208 |
| q12 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4039 | 146 | not_observed | not_observed | not_observed | 4185 | 2817 | 2028 | 0.001208 |
| q13 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4002 | 112 | not_observed | not_observed | not_observed | 4114 | 3301 | 2615 | 0.001172 |
| q14 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3726 | 105 | not_observed | not_observed | not_observed | 3831 | 2434 | 1556 | 0.001105 |
| q15 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3951 | 83 | not_observed | not_observed | not_observed | 4034 | 3613 | 2696 | 0.001138 |
| q16 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 3060 | 406 | not_observed | not_observed | not_observed | 3466 | 5531 | 3951 | 0.001079 |
| q17 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3899 | 206 | not_observed | not_observed | not_observed | 4105 | 4874 | 4093 | 0.001208 |
| q18 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3600 | 178 | not_observed | not_observed | not_observed | 3778 | 2606 | 2051 | 0.001095 |
| q19 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4238 | 92 | not_observed | not_observed | not_observed | 4330 | 3140 | 2556 | 0.001242 |
| q20 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 4509 | 192 | not_observed | not_observed | not_observed | 4701 | 5403 | 3715 | 0.001369 |
| q21 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4005 | 330 | not_observed | not_observed | not_observed | 4335 | 5848 | 5370 | 0.001307 |
| q22 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3579 | 181 | not_observed | not_observed | not_observed | 3760 | 3789 | 3179 | 0.001109 |
| q23 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 4302 | 158 | not_observed | not_observed | not_observed | 4460 | 3462 | 1830 | 0.001277 |
| q24 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3402 | 218 | not_observed | not_observed | not_observed | 3620 | 3278 | 2716 | 0.001068 |
| q25 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3711 | 209 | not_observed | not_observed | not_observed | 3920 | 3062 | 2370 | 0.001138 |
| q26 | DECOMPOSE | ANSWERED | true | sufficiency_judge；subquery_generator；generator | generator；subquery_generator；sufficiency_judge | not_applicable | 3 | 3711 | 329 | not_observed | not_observed | not_observed | 4040 | 7620 | 5116 | 0.001201 |
| q27 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 3017 | 157 | not_observed | not_observed | not_observed | 3174 | 2982 | 2166 | 0.000915 |
| q28 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4274 | 74 | not_observed | not_observed | not_observed | 4348 | 3021 | 2352 | 0.001241 |
| q29 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4020 | 153 | not_observed | not_observed | not_observed | 4173 | 4729 | 4043 | 0.001222 |
| q30 | DIRECT | ANSWERED | true | sufficiency_judge；generator | generator；sufficiency_judge | not_applicable | 2 | 4290 | 155 | not_observed | not_observed | not_observed | 4445 | 2659 | 2090 | 0.001291 |

## 5. Model-call 明细

| qid | idx | role | stage | provider | model | upstream | latency_ms | prompt_tokens | completion_tokens | reasoning_tokens | cached_tokens | total_tokens | cost_usd | timeout | api_error | error_type |
| :-- | --: | :-- | :-- | :-- | :-- | :-- | --: | --: | --: | --: | --: | --: | --: | :--: | :--: | :-- |
| q01 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 995 | 1641 | 4 | not_observed | not_observed | 1645 | 0.000727 | false | false | not_applicable |
| q01 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 5446 | 2134 | 231 | 0 | not_observed | 2365 | 0.000459 | false | false | not_applicable |
| q02 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1009 | 1780 | 5 | not_observed | not_observed | 1785 | 0.000790 | false | false | not_applicable |
| q02 | 2 | sufficiency_judge | legacy_second_sufficiency | deepseek | deepseek-v4-flash | not_observed | 1119 | 1840 | 5 | not_observed | not_observed | 1845 | 0.000816 | false | false | not_applicable |
| q02 | 3 | rewrite_query | rewrite_query | openrouter | openai/gpt-4o-mini | Azure | 2120 | 65 | 11 | 0 | 0 | 76 | 0.000016 | false | false | not_applicable |
| q03 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 885 | 1691 | 4 | not_observed | not_observed | 1695 | 0.000749 | false | false | not_applicable |
| q03 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | Azure | 1754 | 86 | 24 | 0 | 0 | 110 | 0.000027 | false | false | not_applicable |
| q03 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1982 | 2126 | 134 | 0 | not_observed | 2260 | 0.000399 | false | false | not_applicable |
| q04 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 931 | 1682 | 4 | not_observed | not_observed | 1686 | 0.000745 | false | false | not_applicable |
| q04 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1870 | 2084 | 93 | 0 | not_observed | 2177 | 0.000368 | false | false | not_applicable |
| q05 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 786 | 1271 | 4 | not_observed | not_observed | 1275 | 0.000565 | false | false | not_applicable |
| q05 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2008 | 1773 | 147 | 0 | not_observed | 1920 | 0.000354 | false | false | not_applicable |
| q06 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 581 | 1408 | 4 | not_observed | not_observed | 1412 | 0.000625 | false | false | not_applicable |
| q06 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2097 | 1858 | 130 | 0 | not_observed | 1988 | 0.000357 | false | false | not_applicable |
| q07 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 611 | 1840 | 4 | not_observed | not_observed | 1844 | 0.000815 | false | false | not_applicable |
| q07 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2686 | 2234 | 229 | 0 | not_observed | 2463 | 0.000472 | false | false | not_applicable |
| q08 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 568 | 1305 | 4 | not_observed | not_observed | 1309 | 0.000579 | false | false | not_applicable |
| q08 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | OpenAI | 877 | 89 | 30 | 0 | 0 | 119 | 0.000031 | false | false | not_applicable |
| q08 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 3529 | 1795 | 306 | 0 | not_observed | 2101 | 0.000453 | false | false | not_applicable |
| q09 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 712 | 2072 | 4 | not_observed | not_observed | 2076 | 0.000917 | false | false | not_applicable |
| q09 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 2724 | 2515 | 137 | 0 | not_observed | 2652 | 0.000459 | false | false | not_applicable |
| q10 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 998 | 1701 | 4 | not_observed | not_observed | 1705 | 0.000754 | false | false | not_applicable |
| q10 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 3124 | 2154 | 123 | 0 | not_observed | 2277 | 0.000397 | false | false | not_applicable |
| q11 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 995 | 1752 | 4 | not_observed | not_observed | 1756 | 0.000776 | false | false | not_applicable |
| q11 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 4132 | 2236 | 160 | 0 | not_observed | 2396 | 0.000431 | false | false | not_applicable |
| q12 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 789 | 1766 | 4 | not_observed | not_observed | 1770 | 0.000782 | false | false | not_applicable |
| q12 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2028 | 2273 | 142 | 0 | not_observed | 2415 | 0.000426 | false | false | not_applicable |
| q13 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 686 | 1730 | 4 | not_observed | not_observed | 1734 | 0.000766 | false | false | not_applicable |
| q13 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 2615 | 2272 | 108 | 0 | not_observed | 2380 | 0.000406 | false | false | not_applicable |
| q14 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 878 | 1656 | 4 | not_observed | not_observed | 1660 | 0.000734 | false | false | not_applicable |
| q14 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1556 | 2070 | 101 | 0 | not_observed | 2171 | 0.000371 | false | false | not_applicable |
| q15 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 917 | 1698 | 4 | not_observed | not_observed | 1702 | 0.000752 | false | false | not_applicable |
| q15 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 2696 | 2253 | 79 | 0 | not_observed | 2332 | 0.000385 | false | false | not_applicable |
| q16 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 618 | 1289 | 4 | not_observed | not_observed | 1293 | 0.000572 | false | false | not_applicable |
| q16 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | OpenAI | 962 | 90 | 20 | 0 | 0 | 110 | 0.000025 | false | false | not_applicable |
| q16 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 3951 | 1681 | 382 | 0 | not_observed | 2063 | 0.000481 | false | false | not_applicable |
| q17 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 781 | 1711 | 4 | not_observed | not_observed | 1715 | 0.000758 | false | false | not_applicable |
| q17 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 4093 | 2188 | 202 | 0 | not_observed | 2390 | 0.000449 | false | false | not_applicable |
| q18 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 555 | 1537 | 4 | not_observed | not_observed | 1541 | 0.000682 | false | false | not_applicable |
| q18 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2051 | 2063 | 174 | 0 | not_observed | 2237 | 0.000414 | false | false | not_applicable |
| q19 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 584 | 1890 | 4 | not_observed | not_observed | 1894 | 0.000837 | false | false | not_applicable |
| q19 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 2556 | 2348 | 88 | 0 | not_observed | 2436 | 0.000405 | false | false | not_applicable |
| q20 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 683 | 1980 | 4 | not_observed | not_observed | 1984 | 0.000876 | false | false | not_applicable |
| q20 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | OpenAI | 1005 | 92 | 20 | 0 | 0 | 112 | 0.000026 | false | false | not_applicable |
| q20 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 3715 | 2437 | 168 | 0 | not_observed | 2605 | 0.000466 | false | false | not_applicable |
| q21 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 478 | 1742 | 4 | not_observed | not_observed | 1746 | 0.000772 | false | false | not_applicable |
| q21 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 5370 | 2263 | 326 | 0 | not_observed | 2589 | 0.000535 | false | false | not_applicable |
| q22 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 610 | 1588 | 4 | not_observed | not_observed | 1592 | 0.000704 | false | false | not_applicable |
| q22 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 3179 | 1991 | 177 | 0 | not_observed | 2168 | 0.000405 | false | false | not_applicable |
| q23 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 614 | 1840 | 4 | not_observed | not_observed | 1844 | 0.000815 | false | false | not_applicable |
| q23 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | OpenAI | 1018 | 88 | 27 | 0 | 0 | 115 | 0.000029 | false | false | not_applicable |
| q23 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 1830 | 2374 | 127 | 0 | not_observed | 2501 | 0.000432 | false | false | not_applicable |
| q24 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 562 | 1463 | 4 | not_observed | not_observed | 1467 | 0.000649 | false | false | not_applicable |
| q24 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2716 | 1939 | 214 | 0 | not_observed | 2153 | 0.000419 | false | false | not_applicable |
| q25 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 692 | 1564 | 4 | not_observed | not_observed | 1568 | 0.000693 | false | false | not_applicable |
| q25 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2370 | 2147 | 205 | 0 | not_observed | 2352 | 0.000445 | false | false | not_applicable |
| q26 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 553 | 1530 | 4 | not_observed | not_observed | 1534 | 0.000678 | false | false | not_applicable |
| q26 | 2 | subquery_generator | first_decompose | openrouter | openai/gpt-4o-mini | Azure | 1951 | 89 | 23 | 0 | 0 | 112 | 0.000027 | false | false | not_applicable |
| q26 | 3 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 5116 | 2092 | 302 | 0 | not_observed | 2394 | 0.000495 | false | false | not_applicable |
| q27 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 816 | 1261 | 4 | not_observed | not_observed | 1265 | 0.000560 | false | false | not_applicable |
| q27 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2166 | 1756 | 153 | 0 | not_observed | 1909 | 0.000355 | false | false | not_applicable |
| q28 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 669 | 1904 | 4 | not_observed | not_observed | 1908 | 0.000843 | false | false | not_applicable |
| q28 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2352 | 2370 | 70 | 0 | not_observed | 2440 | 0.000398 | false | false | not_applicable |
| q29 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 686 | 1807 | 4 | not_observed | not_observed | 1811 | 0.000800 | false | false | not_applicable |
| q29 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | Azure | 4043 | 2213 | 149 | 0 | not_observed | 2362 | 0.000421 | false | false | not_applicable |
| q30 | 1 | sufficiency_judge | legacy_first_sufficiency | deepseek | deepseek-v4-flash | not_observed | 569 | 1903 | 4 | not_observed | not_observed | 1907 | 0.000843 | false | false | not_applicable |
| q30 | 2 | generator | generator | openrouter | openai/gpt-4o-mini | OpenAI | 2090 | 2387 | 151 | 0 | not_observed | 2538 | 0.000449 | false | false | not_applicable |

## 6. Model role 汇总

| role | calls | total_ms | median_ms | total_tokens | token observed/unknown | cost_usd | cost observed/unknown |
| :-- | --: | --: | --: | --: | :-- | --: | :-- |
| sufficiency_judge | 31 | 22933 | 686 | 51968 | 51968/0 | 0.022977 | 0.022977/0 |
| generator | 29 | 86091 | 2686 | 67034 | 67034/0 | 0.012309 | 0.012309/0 |
| subquery_generator | 6 | 7567 | 1012 | 678 | 678/0 | 0.000167 | 0.000167/0 |
| rewrite_query | 1 | 2120 | 2120 | 76 | 76/0 | 0.000016 | 0.000016/0 |

## 7. 批次分析

- service latency min / median / p95 / max / total ms: 2477 / 3555 / 7041 / 9215 / 124334
- model_call_count: 67
- total_tokens: 119756
- total_tokens observed subtotal / unknown records: 119756 / 0
- total_estimated_cost_usd: 0.035468
- estimated cost observed subtotal / unknown records: 0.035468 / 0
- slowest_cases: q01=9215ms, q26=7843ms, q16=6059ms, q21=5914ms, q20=5650ms
- highest_token_cases: q09=4728, q20=4701, q23=4460, q30=4445, q28=4348
- highest_cost_cases: q02=$0.001622, q09=$0.001376, q20=$0.001369, q21=$0.001307, q30=$0.001291
- engine_init_outliers (>=100ms): q01=2697ms
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
