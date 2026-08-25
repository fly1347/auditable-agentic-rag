# Known Limitations

## 1. Core Answer-Bearing Evidence Is Still Missed

For q06, q19, q27, and q28, the core answer-bearing evidence does not enter Top10 or the final prompt.

- `baseline` produces readable answers using model parametric knowledge.
- `orchestrated` identifies insufficient evidence and refuses.

The main retrieval failure is not that the answer is absent from the corpus, but that the paragraph carrying the answer is not sufficiently reachable. Kubernetes, HNSW, tables, ASCII architecture diagrams, and mechanisms described across multiple paragraphs are more likely to exhibit this problem.

### Main Causes

- Retrieval is currently dense-first. When question phrasing differs from the answer-bearing paragraph, the core evidence can fall in rank.
- If the initial TopK candidate pool does not contain the core evidence, RRF and reranking can only reorder existing candidates; they cannot recover evidence outside the pool.
- Second-round rewrites are mostly semantic paraphrases and provide limited query expansion.

### Possible Improvements

- Test dense + sparse/BM25 hybrid retrieval on the four missed-recall questions.
- Compare different embedding models on TopK ranking of core evidence.
- Expand the initial candidate pool before RRF and reranking.
- Replace paraphrase-style second-round rewriting with keyword-, entity-, and answer-constraint-driven query expansion.
- Add a focused regression suite that records core-evidence reachability at Top10, Top20, and final-prompt stages.

## 2. Second-Round Retrieval Detects Gaps but Recovers Poorly

`orchestrated` triggers five second-round retrievals with a recovery rate of 0/5. Most rewrites are close paraphrases and do not surface new core evidence.

The Agentic path can already detect evidence insufficiency; autonomous recovery of the evidence gap remains the primary weakness.

## 3. The Two Profiles Have an Explicit Trade-Off

| Dimension | baseline | orchestrated |
| :-- | :-- | :-- |
| Coverage on answerable questions | 29/29 | 25/29 |
| Evidence control | More permissive | Strict |
| Online tokens | 119,756 | 188,062 |
| Estimated online cost | $0.035468 | $0.073791 |

No current profile simultaneously achieves high coverage, strong grounding, low cost, and high recovery. The two profiles are scenario choices rather than simple low-end/high-end variants.

## 4. B2 Demonstrates Only In-Domain Regression Stability

B2 contains only 30 questions and is highly in-domain with respect to the frozen private corpus. It can validate:

- behavior stability under frozen corpus and configuration;
- reproducibility of key controls, evidence paths, and cost;
- the Splitter correction and differences between the two profiles.

It cannot by itself prove:

- accuracy in unseen domains;
- real-world business effectiveness;
- that `orchestrated` is universally better across all quality dimensions;
- production-grade quality or stability.

Future evaluation needs independent held-out, out-of-domain, multi-hop, conflicting, negation, and realistic attack sets.

## 5. Evaluation Signals Still Have Boundaries

- The online `baseline` security snapshot was not observed, so `hard_gate_complete=0/30`.
- Human answer-quality grades have not yet been imported into the unified release gate using exact answer SHA values.
- q26 still has a mismatch between the machine evidence gate and the human grade-A conclusion.
- Citation Support is primarily character/lexical matching and has limited semantic entailment capability.
- Conflict lacks an independent gold set; zero final conflicts only means the rule did not trigger.
- RAGAS depends on an LLM judge and is sensitive to model version, randomness, and provider behavior.
- Cost comes from a static price table and is not the actual provider bill.

## 6. The Current Implementation Is Still a Local Reference System

- `LocalVectorStore` uses local files and in-memory O(N) dot products.
- The API is best run with a single worker.
- CER, audit, and service logs use local JSONL.
- Authentication uses static tokens.
- Tenant isolation is primarily validated through synthetic negative controls.
- Ingest mainly supports Markdown/TXT and full rebuilds; PDF / Office / OCR do not yet have parsing-quality, layout-recovery, or page-level citation regression gates.
- Incremental embedding, task queues, production vector databases, and a knowledge-operations backend are not provided.
- The UI focuses on single-turn QA and debugging display.
- HA, autoscaling, disaster recovery, and production SLOs are not provided.

The project is therefore positioned as an enterprise-oriented Agentic RAG reference implementation and evaluable prototype.

## 7. Security Capabilities Are an Engineering Baseline

Query Safety, Prompt Injection checks, redaction, sanitizer logic, and release scans primarily depend on rules and fixed negative controls. Source ACL and the egress gate provide fail-close contracts, but the project does not integrate an enterprise IdP, DLP, SIEM, key rotation, or a complete compliance system.

New schemas, providers, tool calls, or data types require corresponding security-test extensions and manual review.

## 8. Deployment and Public-Release Boundary

Docker Compose targets local reproduction. The public repository excludes raw logs, the complete private corpus, raw CER/evidence, real `.env` files, model caches, experiments, and historical process drafts.

The public B2 human-readable reports demonstrate frozen evaluation facts. The public Quickstart uses a separate sample corpus and sample regression set, so the full B2 metrics cannot be reproduced from the sample data.

## 9. Model-Selection Results Are Time-Bounded

The C+ model comparison was conducted primarily in May 2026 using the then-current D-lite / Phase C pipeline, prompts, provider versions, and local hardware. Its purpose is to show how model roles and engineering trade-offs were selected; it is historical engineering evidence, not a current general-purpose model ranking. When model versions, aliases, prices, network conditions, or inference backends change, benchmarking should be rerun against the current pipeline with a fixed shared input set.
