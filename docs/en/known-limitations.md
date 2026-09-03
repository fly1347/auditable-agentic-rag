# Known Limitations

## 1. Hybrid RRF Still Has Answer-Bearing Ranking Boundaries

The public default has moved from Dense-only to `Dense Top10 + BM25 Top10 → RRF(k=60) → Top5`. Manually confirmed CORE Hit@5 improves from 14/27 to 20/27, and old Dense gaps including q06 and q19 are recovered. q28, however, remains a genuine retrieval boundary.

For q28, the detailed etcd passage is not highly ranked by either Dense or BM25, while RRF rewards overview chunks that are jointly ranked well by both channels. The actual answer-bearing chunk therefore misses the final EvidencePacket. RRF improves average reachability but has no semantic discriminator and cannot guarantee that one-channel-correct evidence outranks two-channel wrong consensus.

### Possible Improvements

- Keep recording Dense / BM25 / RRF candidate ranks and fusion contributions for cases such as q28.
- Use more constrained query expansion for entity, exact-term, and mechanism questions.
- Compare larger candidate pools and the optional reranker while keeping the strict evidence gate independent.
- Continue treating answer-bearing reachability as its own regression signal instead of relying only on source-level Full@K.

## 2. Second-Round Retrieval Can Recover, but Is Not Yet Stable

Hybrid `orchestrated` behaves as follows on answerable first-round-insufficient cases:

```text
q17 → recovery
q27 → recovery
q28 → refuse
q30 → refuse
```

Second-round recovery is therefore 2/4 on answerable cases. q17 and q27 show that bounded rewrite + R2 can recover real evidence gaps; q28 remains a retrieval problem. q30 already contains direct KV-cache evidence in the first round yet is repeatedly judged insufficient by the structured judge, making it closer to a sufficiency-calibration / provider-variation false negative.

Further optimization should first distinguish genuine evidence absence from over-strict judging rather than simply adding more loops.

## 3. The Two Profiles Still Represent an Explicit Trade-Off

| Dimension | baseline | orchestrated |
| :-- | :-- | :-- |
| Coverage on answerable questions | 29/29 | 27/29 |
| Evidence control | More permissive | Strict and structured |
| Online tokens | 123,627 | 190,941 |
| Estimated online cost | $0.036531 | $0.073633 |

No current profile simultaneously maximizes coverage, evidence strictness, low cost, and stable recovery. They remain scenario choices rather than simple low-end/high-end variants.

## 4. B2 Demonstrates Only In-Domain Regression Stability

B2 contains only 30 questions and is highly in-domain with respect to the frozen private corpus. It can validate:

- behavior stability under frozen corpus and configuration;
- reproducibility of key controls, evidence paths, and cost;
- the Splitter correction, Hybrid Retriever, and differences between the two profiles.

It cannot by itself prove:

- accuracy in unseen domains;
- real-world business effectiveness;
- that `orchestrated` is universally better across all quality dimensions;
- production-grade quality or stability.

Future evaluation needs independent held-out, out-of-domain, multi-hop, conflicting, negation, and realistic attack sets.

## 5. Evaluation Signals Still Have Boundaries

- q06 and q27 still have a mismatch between the machine expected-evidence gate and the manual precise-evidence diagnosis; the focused manual labels were not silently promoted into a new release gate.
- q21 has a single `baseline` citation-validity failure and should remain a citation-layer regression point.
- q30 exposes over-strict / provider-variable structured-sufficiency behavior.
- Human answer-quality grades have not yet been imported into the unified release gate using exact answer SHA values.
- Citation Support is primarily character/lexical matching and has limited semantic entailment capability.
- Conflict lacks an independent gold set; zero final conflicts only means the rule did not trigger.
- RAGAS depends on an LLM judge and is sensitive to model version, randomness, and provider behavior.
- Cost comes from a static price table and is not the actual provider bill.

## 6. The Current Implementation Is Still a Local Reference System

- `LocalVectorStore` uses local files and in-memory O(N) dot products.
- Hybrid BM25 reuses the current chunk set and is built in-process; it is not a production sparse index for large corpora.
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
