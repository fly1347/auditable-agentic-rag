# D-full baseline 离线评测总览

> 输入为冻结 CER。Classifier 为本轮 D-full 的 LLM 分类；Sufficiency 读取主链既有判断；Citation Support、Conflict 与 Uncertainty 为后置规则诊断。

## 五类信号怎么读

| 模块 | 主要职责 | 方法 | 关键结果 |
| :-- | :-- | :-- | :-- |
| Classifier | 判断问题类型、可答性状态与候选路线 | LLM | question_type / answerability / route_candidate / confidence / reason |
| Sufficiency Judge | 判断当前证据是否足够回答 | 主链 LLM 结果投影 | binary=30；verdict / confidence / missing_evidence 等 |
| Citation Support | 检查答案 claims 是否被**最终实际引用证据**支撑 | 本地规则 | supported / partial / unsupported；claim-level best_score |
| Conflict | 对多来源 EvidencePacket 做规则型疑似冲突扫描 | 本地规则 | conflict_count / conflict_type |
| Uncertainty | 汇总 sufficiency、citation、conflict 等信号形成回答风险等级 | 本地规则聚合 | high / medium / low；**high 表示不确定性/风险高** |

## 批次摘要

| field | value |
| :-- | :-- |
| source_profile | baseline |
| 评测题数 | 30 |
| classifier.mode | llm=30 |
| sufficiency.mode | binary=30 |
| sufficiency_raw_verdict | INSUFFICIENT=1；SUFFICIENT=29 |
| citation_support_label | not_applicable=1；partial=26；supported=1；unsupported=2 |
| uncertainty_level | high=13；low=1；medium=16 |
| offline_total_ms | 47,012.303 |
| model_call_count | 30 |
| total_tokens | 12,858 |
| estimated_cost_usd | 0.002642 |

## 重点题索引

| 观察维度 | 题数 | qids |
| :-- | --: | :-- |
| answerability 非 IN_SCOPE | 2 | q02、q13 |
| classifier confidence 为 medium / low | 6 | q02、q13、q15、q21、q22、q30 |
| route_candidate 与 actual_route 明确不一致（仅 DIRECT / DECOMPOSE） | 3 | q17、q18、q21 |
| sufficiency 非 SUFFICIENT | 1 | q02 |
| citation_support 为 unsupported / no_evidence | 2 | q05、q23 |
| unsupported_claim_count > 0 | 12 | q01、q03、q05、q06、q12、q13、q14、q16、q17、q21、q23、q25 |
| conflict_count > 0 | 0 | 无 |
| uncertainty_level = high | 13 | q01、q02、q03、q05、q06、q12、q13、q14、q16、q17、q21、q23、q25 |

## Classifier 分类汇总

### question_type

| question_type | 含义 | count | qids |
| :-- | :-- | --: | :-- |
| EXPLICIT_COMPARE | 明确比较两个或多个对象，通常倾向拆解 | 7 | q03、q08、q16、q17、q20、q23、q26 |
| IMPLICIT_COMPARE | 问题隐含对照关系，通常倾向拆解 | 2 | q18、q21 |
| NARROW_FACT | 单一事实点，通常适合直接回答 | 7 | q02、q05、q06、q13、q14、q19、q28 |
| OPEN_MULTI | 需要多个要点、原因、风险或场景 | 4 | q01、q04、q09、q12 |
| PROCEDURE | 操作、排查、配置或流程型问题 | 1 | q07 |
| SUMMARY | 总结或整体说明 | 9 | q10、q11、q15、q22、q24、q25、q27、q29、q30 |

### answerability

| answerability | 含义 | count | qids |
| :-- | :-- | --: | :-- |
| IN_SCOPE | 问题范围明确，可在当前知识范围内回答 | 28 | q01、q03、q04、q05、q06、q07、q08、q09、q10、q11、q12、q14、q15、q16、q17、q18、q19、q20、q21、q22、q23、q24、q25、q26、q27、q28、q29、q30 |
| NEEDS_CLARIFICATION | 问题缺少必要定义、对象或约束，需要澄清 | 1 | q13 |
| OOD_CANDIDATE | 可能超出当前知识范围或涉及未公开信息 | 1 | q02 |

### route_candidate

> route_candidate 是 classifier 派生的候选处理方式，不等同于主链实际 `actual_route`。

| route_candidate | 含义 | count | qids |
| :-- | :-- | --: | :-- |
| DECOMPOSE | 候选为拆解问题后处理 | 9 | q03、q08、q16、q17、q18、q20、q21、q23、q26 |
| DIRECT | 候选为直接处理 | 6 | q05、q06、q07、q14、q19、q28 |
| NEEDS_CLARIFICATION | 建议先澄清问题 | 1 | q13 |
| OPEN_MULTI | 开放多点回答候选；不是实际执行 path | 13 | q01、q04、q09、q10、q11、q12、q15、q22、q24、q25、q27、q29、q30 |
| REJECT_CANDIDATE | 存在拒答候选；最终仍由后续证据与控制逻辑决定 | 1 | q02 |

### confidence

> classifier confidence 是模型自报分类置信等级，不是校准后的概率。

| confidence | 含义 | count | qids |
| :-- | :-- | --: | :-- |
| high | 分类器自报高置信；不是概率值 | 24 | q01、q03、q04、q05、q06、q07、q08、q09、q10、q11、q12、q14、q16、q17、q18、q19、q20、q23、q24、q25、q26、q27、q28、q29 |
| medium | 分类器自报中等置信；建议结合 reason 查看 | 6 | q02、q13、q15、q21、q22、q30 |

## D-full 判断结果分类

| signal | value | count | qids |
| :-- | :-- | --: | :-- |
| sufficiency_raw_verdict | INSUFFICIENT | 1 | q02 |
| sufficiency_raw_verdict | SUFFICIENT | 29 | q01、q03、q04、q05、q06、q07、q08、q09、q10、q11、q12、q13、q14、q15、q16、q17、q18、q19、q20、q21、q22、q23、q24、q25、q26、q27、q28、q29、q30 |
| citation_support_label | not_applicable | 1 | q02 |
| citation_support_label | partial | 26 | q01、q03、q04、q06、q07、q08、q09、q10、q11、q12、q13、q14、q15、q16、q17、q18、q19、q20、q21、q22、q25、q26、q27、q28、q29、q30 |
| citation_support_label | supported | 1 | q24 |
| citation_support_label | unsupported | 2 | q05、q23 |
| uncertainty_level | high | 13 | q01、q02、q03、q05、q06、q12、q13、q14、q16、q17、q21、q23、q25 |
| uncertainty_level | low | 1 | q24 |
| uncertainty_level | medium | 16 | q04、q07、q08、q09、q10、q11、q15、q18、q19、q20、q22、q26、q27、q28、q29、q30 |
| conflict_count | 0 | 30 | q01、q02、q03、q04、q05、q06、q07、q08、q09、q10、q11、q12、q13、q14、q15、q16、q17、q18、q19、q20、q21、q22、q23、q24、q25、q26、q27、q28、q29、q30 |
| conflict_count | >0 | 0 | 无 |

## 分类器逐题摘要

| qid | actual_route | question_type | answerability | route_candidate | confidence |
| :-- | :-- | :-- | :-- | :-- | :--: |
| q01 | DIRECT | OPEN_MULTI | IN_SCOPE | OPEN_MULTI | high |
| q02 | DIRECT | NARROW_FACT | OOD_CANDIDATE | REJECT_CANDIDATE | medium |
| q03 | DECOMPOSE | EXPLICIT_COMPARE | IN_SCOPE | DECOMPOSE | high |
| q04 | DIRECT | OPEN_MULTI | IN_SCOPE | OPEN_MULTI | high |
| q05 | DIRECT | NARROW_FACT | IN_SCOPE | DIRECT | high |
| q06 | DIRECT | NARROW_FACT | IN_SCOPE | DIRECT | high |
| q07 | DIRECT | PROCEDURE | IN_SCOPE | DIRECT | high |
| q08 | DECOMPOSE | EXPLICIT_COMPARE | IN_SCOPE | DECOMPOSE | high |
| q09 | DIRECT | OPEN_MULTI | IN_SCOPE | OPEN_MULTI | high |
| q10 | DIRECT | SUMMARY | IN_SCOPE | OPEN_MULTI | high |
| q11 | DIRECT | SUMMARY | IN_SCOPE | OPEN_MULTI | high |
| q12 | DIRECT | OPEN_MULTI | IN_SCOPE | OPEN_MULTI | high |
| q13 | DIRECT | NARROW_FACT | NEEDS_CLARIFICATION | NEEDS_CLARIFICATION | medium |
| q14 | DIRECT | NARROW_FACT | IN_SCOPE | DIRECT | high |
| q15 | DIRECT | SUMMARY | IN_SCOPE | OPEN_MULTI | medium |
| q16 | DECOMPOSE | EXPLICIT_COMPARE | IN_SCOPE | DECOMPOSE | high |
| q17 | DIRECT | EXPLICIT_COMPARE | IN_SCOPE | DECOMPOSE | high |
| q18 | DIRECT | IMPLICIT_COMPARE | IN_SCOPE | DECOMPOSE | high |
| q19 | DIRECT | NARROW_FACT | IN_SCOPE | DIRECT | high |
| q20 | DECOMPOSE | EXPLICIT_COMPARE | IN_SCOPE | DECOMPOSE | high |
| q21 | DIRECT | IMPLICIT_COMPARE | IN_SCOPE | DECOMPOSE | medium |
| q22 | DIRECT | SUMMARY | IN_SCOPE | OPEN_MULTI | medium |
| q23 | DECOMPOSE | EXPLICIT_COMPARE | IN_SCOPE | DECOMPOSE | high |
| q24 | DIRECT | SUMMARY | IN_SCOPE | OPEN_MULTI | high |
| q25 | DIRECT | SUMMARY | IN_SCOPE | OPEN_MULTI | high |
| q26 | DECOMPOSE | EXPLICIT_COMPARE | IN_SCOPE | DECOMPOSE | high |
| q27 | DIRECT | SUMMARY | IN_SCOPE | OPEN_MULTI | high |
| q28 | DIRECT | NARROW_FACT | IN_SCOPE | DIRECT | high |
| q29 | DIRECT | SUMMARY | IN_SCOPE | OPEN_MULTI | high |
| q30 | DIRECT | SUMMARY | IN_SCOPE | OPEN_MULTI | medium |

## D-full 逐题判断信号

| qid | raw_verdict | control_verdict | citation_support_label | unsupported_claim_count | conflict_count | uncertainty_level |
| :-- | :-- | :-- | :-- | --: | --: | :-- |
| q01 | SUFFICIENT | SUFFICIENT | partial | 6 | 0 | high |
| q02 | INSUFFICIENT | INSUFFICIENT | not_applicable | 0 | 0 | high |
| q03 | SUFFICIENT | SUFFICIENT | partial | 1 | 0 | high |
| q04 | SUFFICIENT | SUFFICIENT | partial | 0 | 0 | medium |
| q05 | SUFFICIENT | SUFFICIENT | unsupported | 3 | 0 | high |
| q06 | SUFFICIENT | SUFFICIENT | partial | 2 | 0 | high |
| q07 | SUFFICIENT | SUFFICIENT | partial | 0 | 0 | medium |
| q08 | SUFFICIENT | SUFFICIENT | partial | 0 | 0 | medium |
| q09 | SUFFICIENT | SUFFICIENT | partial | 0 | 0 | medium |
| q10 | SUFFICIENT | SUFFICIENT | partial | 0 | 0 | medium |
| q11 | SUFFICIENT | SUFFICIENT | partial | 0 | 0 | medium |
| q12 | SUFFICIENT | SUFFICIENT | partial | 2 | 0 | high |
| q13 | SUFFICIENT | SUFFICIENT | partial | 1 | 0 | high |
| q14 | SUFFICIENT | SUFFICIENT | partial | 2 | 0 | high |
| q15 | SUFFICIENT | SUFFICIENT | partial | 0 | 0 | medium |
| q16 | SUFFICIENT | SUFFICIENT | partial | 3 | 0 | high |
| q17 | SUFFICIENT | SUFFICIENT | partial | 2 | 0 | high |
| q18 | SUFFICIENT | SUFFICIENT | partial | 0 | 0 | medium |
| q19 | SUFFICIENT | SUFFICIENT | partial | 0 | 0 | medium |
| q20 | SUFFICIENT | SUFFICIENT | partial | 0 | 0 | medium |
| q21 | SUFFICIENT | SUFFICIENT | partial | 3 | 0 | high |
| q22 | SUFFICIENT | SUFFICIENT | partial | 0 | 0 | medium |
| q23 | SUFFICIENT | SUFFICIENT | unsupported | 3 | 0 | high |
| q24 | SUFFICIENT | SUFFICIENT | supported | 0 | 0 | low |
| q25 | SUFFICIENT | SUFFICIENT | partial | 2 | 0 | high |
| q26 | SUFFICIENT | SUFFICIENT | partial | 0 | 0 | medium |
| q27 | SUFFICIENT | SUFFICIENT | partial | 0 | 0 | medium |
| q28 | SUFFICIENT | SUFFICIENT | partial | 0 | 0 | medium |
| q29 | SUFFICIENT | SUFFICIENT | partial | 0 | 0 | medium |
| q30 | SUFFICIENT | SUFFICIENT | partial | 0 | 0 | medium |
