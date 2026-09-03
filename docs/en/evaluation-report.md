# Evaluation Report

## 1. Evaluation Goals

The final evaluation focuses on four engineering questions:

1. Can the current structure-aware splitter, frozen index, and Hybrid RRF complete the 30-question in-domain regression run reliably?
2. What control outcomes do `baseline` and `orchestrated` produce over the same Hybrid Retriever?
3. How much latency, token usage, and cost does structured sufficiency add?
4. What conclusions are supported by the current evidence, and what gaps remain?

Signals remain layered rather than collapsed into one score. The Dense-only → Hybrid RRF change is documented in a separate retrieval comparison; this report treats the current Hybrid implementation as the release state.

## 2. Frozen Conditions

| Item | Frozen value |
| :-- | :-- |
| Dataset | Project-specific 30-question in-domain regression set, `derived_in_domain_regression` |
| dataset SHA-256 | `2abf448e2ac2fa67a51de370db3fed01597ce64ac5e742faf241e4c51bba2204` |
| corpus SHA-256 | `605858272b2b7fe8eceb931ce363875ee005638a693ffcb40b5e65fa32aa7c4e` |
| config SHA-256 | `d47fc9c017e830a1ed197b8628806fa0a173a6ac9a1d8cb472bb1fa3e2f7a60d` |
| ACL SHA-256 | `8e6dfc826ac1d8d7610a0386fdbec18ac9e8a2b282f7d1722a88f58ef0c495b6` |
| index build | `20260821T054541778117Z-60585827-e81a7f97` |
| index | 34 docs / 575 chunks / 575 vectors / 512 dimensions |
| embedding | `BAAI/bge-small-zh-v1.5`, normalized, content cap=510 |
| Retriever | Dense candidate=10; BM25 candidate=10; RRF k=60; final Top5 |
| baseline run | `eval_413526d23766` |
| orchestrated run | `eval_e78ef09a941d` |
| RAGAS | 0.4.3 |

Both profiles share the same data, corpus, index, and Hybrid Retriever. The main control variable remains the binary versus structured sufficiency contract. Query rewrite and the second retrieval mechanism are shared, although different sufficiency judgments trigger different numbers of R2 executions.

## 3. Evaluation Structure

| Layer | Input | Main signals |
| :-- | :-- | :-- |
| Online pipeline | Frozen regression set + frozen config/index | route, retrieval, sufficiency, answer, citation, timing, usage |
| Unified assertions | CER + dataset | behavior, evidence, prompt, citation, route, security, errors, budget |
| Precise retrieval probe | Same frozen index + manual answer-bearing labels | Dense / BM25 / RRF ranks, CORE Hit@5 |
| D-full | Frozen CER | classifier, sufficiency, citation support, conflict, uncertainty |
| RAGAS | CER prompt-visible contexts | Context Precision, Faithfulness, Answer Relevancy |
| Ledger | Three layers of model calls | time, calls, tokens, estimated cost |
| Paired comparison | Two profile ledgers | control changes, shared-question quality migrations, cost deltas |

## 4. Splitter, Index, and Retriever Quality

| Check | Frozen result |
| :-- | :-- |
| Corpus size | 34 docs |
| chunk / vector | 575 / 575 |
| embedding dimensions | 512 |
| content token cap | 510 |
| coverage / offset / determinism / vector-row parity | PASS |
| baseline behavior contract | 30/30 |
| baseline human answer quality | A=27, B=3, C=0, D=0 |

The frozen index continues to use structure-first splitting and a hard budget from the actual tokenizer. The current Retriever runs Dense Top10 and BM25 Top10 over the same chunks and fuses them with RRF(k=60) into the final Top5.

Source-level Full@5 no longer separates retrieval quality well: Dense is 29/29 while RRF is 27/29. On manually confirmed answer-bearing evidence, however, CORE Hit@5 improves from Dense 14/27 to RRF 20/27. q03, q06, q19, q26, q27, and q30 are typical newly recovered cases. The public default moved from Dense-only to Hybrid RRF because of this strict-evidence gain, not because of source-level document hit rate.

## 5. Online Pipeline Results

| Observation | baseline | orchestrated | Change |
| :-- | --: | --: | --: |
| ANSWERED | 29 | 27 | -2 |
| REFUSED | 1 (q02) | 3 (q02, q28, q30) | +2 |
| DIRECT / DECOMPOSE | 24 / 6 | 24 / 6 | 0 |
| behavior contract | 30/30 | 28/30 | -2 |
| second-round sufficiency | 1 (q02) | 5 (q02, q17, q27, q28, q30) | +4 |
| prompt-evidence fail | 2 (q06, q27) | 4 (q06, q27, q28, q30) | +2 |

q02 is the expected refusal. Among the four answerable questions that are insufficient after the first `orchestrated` judgment, q17 and q27 recover on R2 and generate answers, while q28 and q30 remain refused. Agentic recovery on answerable R2 cases is therefore 2/4.

q28 remains a genuine answer-bearing retrieval gap: the detailed etcd passage does not enter the final EvidencePacket after RRF. q30 is different. The first round already contains direct KV-cache evidence, `baseline` answers normally, and Faithfulness is 1.0; repeated `orchestrated` INSUFFICIENT judgments are better treated as structured-sufficiency calibration / provider-variation false negatives.

q06 and q27 still expose a mismatch between the machine expected-evidence gate and the manual precise-evidence labels. q21 has a single `baseline` citation-validity failure. These remain separate audit signals rather than allowing one gate to overwrite the other evidence.

### Human Answer-Quality Grades

| Grade | baseline | orchestrated |
| :-- | :-- | :-- |
| A | 27 | 25 |
| B | 3 (q16, q26, q27) | 3 (q16, q26, q27) |
| C | 0 | 0 |
| D | 0 | 2 (q28, q30) |

Hybrid `baseline` produces valid answers for all 29 answerable questions with no abnormal refusal. The `orchestrated` decline is concentrated in q28 and q30; answers that do reach generation remain broadly stable.

## 6. Performance, Tokens, and Cost

| metric | baseline | orchestrated | Change |
| :-- | --: | --: | --: |
| service time sum | 137.674 s | 194.988 s | +41.6% |
| median | 3.891 s | 5.864 s | +50.7% |
| p95 | 8.536 s | 11.848 s | +38.8% |
| model calls | 67 | 73 | +9.0% |
| total tokens | 123,627 | 190,941 | +54.4% |
| estimated cost | $0.036531 | $0.073633 | +101.6% |

> This section keeps the percentile definition used by the per-profile B2 `Timing-Usage-Cost` reports. The machine-generated paired comparison uses nearest-rank p95 and therefore shows 9.325 s / 12.762 s. Both are derived from the same 30 `service_total_ms` values; only the percentile definition differs.

Sufficiency Judge breakdown:

| metric | baseline binary | orchestrated structured |
| :-- | --: | --: |
| calls | 31 | 35 |
| provider latency sum | 17.770 s | 69.203 s |
| total tokens | 53,641 | 125,449 |
| estimated cost | $0.023713 | $0.061654 |

The structured judge remains the main source of incremental `orchestrated` cost: EvidencePackets are longer, outputs follow a structured contract, and more INSUFFICIENT judgments trigger rewrite plus a second judge call. The public default therefore remains `baseline`.

## 7. Post-Hoc D-full Diagnostics

| signal | baseline | orchestrated |
| :-- | :-- | :-- |
| sufficiency | 29 sufficient / 1 insufficient | 27 sufficient / 3 insufficient |
| citation support | 1 supported / 25 partial / 2 unsupported / 1 no_evidence / 1 N/A | 1 supported / 24 partial / 2 unsupported / 3 N/A |
| questions with unsupported claims | 16 | 15 |
| conflict_count > 0 | 0 | 0 |
| uncertainty | low=1 / medium=12 / high=17 | low=1 / medium=11 / high=18 |

Citation Support is a local character/lexical rule for deterministic audit signals, not a semantic-entailment judge. Zero conflicts only means the current rule did not flag conflict in this frozen EvidencePacket batch.

## 8. RAGAS

The evaluated question sets differ by profile: `baseline` evaluates 29 questions and `orchestrated` evaluates 27. Cross-profile conclusions use the 27 shared questions.

| metric | baseline | orchestrated | delta |
| :-- | --: | --: | --: |
| Context Precision | 0.8539 | 0.8197 | -0.0342 |
| Faithfulness | 0.9633 | 0.9562 | -0.0071 |
| Answer Relevancy | 0.8585 | 0.8468 | -0.0118 |

RAGAS does not show a universal quality gain for the structured profile on shared questions; strict evidence control, answer quality, and answer coverage still need to be interpreted separately.

For historical focus cases, Hybrid `baseline` Faithfulness is q06=1.000, q19=1.000, q27=0.714, and q28=0.400. q06/q19 show the grounding improvement after direct core evidence enters the prompt, while q28 shows why high Context Precision can still coexist with missing answer-bearing evidence.

## 9. Three-Layer Cost Ledger

| category | baseline calls / tokens / cost | orchestrated calls / tokens / cost |
| :-- | :-- | :-- |
| Online pipeline | 67 / 123,627 / $0.036531 | 73 / 190,941 / $0.073633 |
| D-full | 30 / 12,847 / $0.002636 | 30 / 12,849 / $0.002637 |
| RAGAS | 290 / 354,033 / $0.095437 | 270 / 330,350 / $0.077286 |
| Total | 387 / 490,507 / $0.134604 | 373 / 534,140 / $0.153556 |

`orchestrated` RAGAS cost is lower because q28 and q30 do not generate answers and therefore do not enter RAGAS. This does not make the online `orchestrated` path cheaper; its online cost is about 2.02× `baseline`. All costs are static-price estimates rather than billing reconciliation.

## 10. Conclusions and Scope

- Current release Retriever: `Dense Top10 + BM25 Top10 → RRF(k=60) → Top5`.
- Hybrid `baseline`: 30/30 behavior, answers all 29 answerable questions, human grades A=27 / B=3 / C=0 / D=0.
- Hybrid `orchestrated`: q17 and q27 recover on R2; q28 and q30 are ultimately abnormal refusals. Strict evidence control still trades coverage for auditability and remains exposed to false-negative sufficiency judgments.
- Retriever-change evidence: CORE Hit@5 improves from 14/27 to 20/27, with actual recovery of Dense gaps including q06 and q19.
- Main remaining boundaries: q28 as an RRF ranking counterexample, q30 as a structured-sufficiency calibration risk, and mismatch between the existing evaluation gate and precise-evidence diagnostics.
- Scope: the regression set supports in-domain engineering regression and failure diagnosis, not claims of out-of-domain generalization.

Full per-question, retrieval-workflow, D-full, RAGAS, and cost reports are available under [`artifacts/evaluation/`](../../artifacts/evaluation/README.md). The retrieval-change evidence is in [`Dense-vs-Hybrid-RRF-四组批跑对比报告.md`](../../artifacts/evaluation/Dense-vs-Hybrid-RRF-四组批跑对比报告.md).
