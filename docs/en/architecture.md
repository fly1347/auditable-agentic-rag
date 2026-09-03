# System Architecture

## 1. Architecture Goals

The system is organized around four engineering goals:

1. All entry points share the same business execution path.
2. `baseline` and `orchestrated` reuse the same correctness-critical implementation and differ only where control behavior must differ.
3. Every execution produces an auditable and replayable factual record.
4. Online answers, offline evaluation, cost accounting, and public reports all derive from the same fact base.

## 2. Overall Structure

```text
[CLI · API · UI · Eval]
            │
            ▼
[Trusted Access]
 └─ Principal · Profile · Request / Run / QID
            │
            ▼
[RagApplicationService] ←→ [RuntimeContainer]
            │
            ▼
[Execution Profile: baseline / orchestrated]
            │
            ▼
[Shared Retrieval · Evidence · Generation]
            │
            ▼
[CanonicalExecutionRecord]
            │
            ▼
[Response · Audit · Evaluation · Report]

Cross-cutting: [Identity] [ACL] [Egress] [Budget] [Logging] [Metrics]
```

### Access Axis

CLI, FastAPI, Streamlit UI, and evaluation entry points ultimately enter `RagApplicationService`. Identity is produced by trusted adapters; ordinary requests cannot self-declare roles, groups, or tenant.

### Execution Axis

There are only two online execution profiles:

| profile | sufficiency | Intended use |
| :-- | :-- | :-- |
| baseline | binary | Default interaction, demos, batch regression, cost-sensitive scenarios |
| orchestrated | structured | Strict evidence control, high-risk QA, audit, and failure diagnosis |

The two profiles share route, Hybrid retrieval, ACL, RRF, evidence, prompt, generation, citation, and the bounded recovery path of rewrite, one second retrieval round, and a second judgment after insufficient evidence. The default Retriever for one query is `Dense Top10 + BM25 Top10 → RRF(k=60) → Top5`. Their difference is concentrated in the sufficiency contract: `baseline` uses a binary judgment, while `orchestrated` produces a structured SufficiencyResult over an EvidencePacket.

### Cross-Cutting Axis

Identity, source authorization, data egress, budget, logging, metrics, and CER span the full execution lifecycle.

## 3. Online QA Flow

```text
[Question + Principal]
        │
        ▼
[Query Safety]
  ├─ REJECT ──> [Refusal] ──> [CER / Response]
  └─ PASS
       │
       ▼
    [Rule-based Routing]
      ├─ DIRECT ─────> [Per-query Hybrid: Dense Top10 + BM25 Top10 → RRF Top5] ──┐
      └─ DECOMPOSE ──> [Original + subqueries each Hybrid → query-level RRF] ─────┤
                                                                                        ▼
                                                                             [Optional Rerank]
                                                                       │
                                                                       ▼
                                                               [ACL Recheck]
                                                                       │
                                                                       ▼
                                                           [EvidenceSnapshot]
                                                                       │
                                                                       ▼
                                                           [Sufficiency Judge]
                                                             ├─ SUFFICIENT
                                                             │    └─> [ANSWER PATH]
                                                             ├─ JUDGE_FAILED
                                                             │    └─> [Fail-close → CER / Response]
                                                             └─ INSUFFICIENT
                                                                  └─> [Rewrite + ACL Retrieve R2]
                                                                         └─> [Round RRF + ACL Recheck]
                                                                              └─> [Second Sufficiency]
                                                                                   ├─ SUFFICIENT
                                                                                   │    └─> [ANSWER PATH]
                                                                                   ├─ JUDGE_FAILED
                                                                                   │    └─> [Fail-close → CER / Response]
                                                                                   └─ STILL INSUFFICIENT
                                                                                        └─> [Refusal → CER / Response]

[ANSWER PATH]
  └─> [PromptSnapshot]
         └─> [Egress / Budget Gate]
                └─> [Generate Answer]
                       └─> [Citation Check]
                              └─> [CER / Response]
```

DIRECT runs one Hybrid retrieval for the original question. DECOMPOSE runs Hybrid retrieval independently for the original question and subqueries, then applies query-level RRF while preserving every retrieval event. Dense/BM25 events and the internal Hybrid RRF merge trace remain visible; second-round retrieval uses the same Hybrid path and forms a union without overwriting first-round lineage.

The system records these sets separately:

```text
retrieved → merged/reranked → evidence selected
→ prompt visible → cited
```

They are not interchangeable. Dense cosine, RRF, and rerank scores are recorded separately as `vector_score`, `rrf_score`, and `rerank_score`; one score type is never presented as another. Retrieval scores / `score_summary` remain available for ranking and audit but are not sent to the structured sufficiency judge. Citations can only point to evidence the model actually saw in the prompt.

If structured sufficiency returns malformed JSON, the system allows exactly one real retry. A second parse failure is recorded explicitly as `SufficiencyJudgeOutputParseError` and fails closed; both provider attempts remain in CER.

## 4. Corpus and Index

```text
[Source ACL Registry] ───────────────┐
                                     ▼
[Markdown / TXT] ──> [Loader + ACL Attach]
                                     │
                                     ▼
                         [Structure-first Splitter]
                                     │
                                     ▼
                          [Tokenizer ≤ 510 Hard Gate]
                                     │
                                     ▼
                             [BGE Embedding]
                                     │
                                     ▼
                         [Immutable Index Build]
                                     │
                                     ▼
                               [Validation]
                           ├─ FAIL ──> Keep previous current
                           └─ PASS ──> Atomically update current.json
```

The public Quickstart uses `sample_data/corpus/`. The loader derives stable `source_id` values from relative paths; the ACL Registry applies deny-by-default registration to every source. Chunking is Markdown structure-first, uses largest-fit packing and a hard budget from the actual tokenizer, and validates coverage, offsets, determinism, and vector-row parity.

Each index is written as a new immutable build. `artifacts/index/current.json` is updated atomically only after all validations pass. A failed build does not corrupt the previous pointer.

The local vector store uses `vectors.npy + chunks.jsonl` and in-memory dot products. It is intended for small-scale demos and regression testing.

## 5. CanonicalExecutionRecord

CER is the complete factual record of one execution. It primarily contains:

```text
identity · provenance · principal · policy · route
retrieval · rerank · merge · evidence · prompt
sufficiency · model_calls · usage · timing · outcome
evaluation · errors · events
```

It supports:

- API debug projections;
- audit, logging, and observability;
- unified online assertions;
- post-hoc D-full diagnostics;
- RAGAS inputs constructed from prompt-visible contexts;
- Timing / Usage / Cost ledgers;
- automatic paired comparison of `baseline` and `orchestrated`.

Facts absent from historical material remain `not_observed`; the system does not infer intermediate steps backward from final outcomes.

## 6. Online / Offline Boundary

The D-full classifier, Citation Support, Conflict, and Uncertainty are post-hoc evaluation signals. They read frozen CERs for diagnosis and audit and do not enter the online answer-control path.

RAGAS also consumes frozen CERs and does not rerun retrieval or the query pipeline. It evaluates the contexts that were actually visible to the model at execution time, preventing evaluation input from drifting away from online facts.

## 7. Key Implementation Locations

| Responsibility | Path |
| :-- | :-- |
| Application service | `src/agentic_rag/service/` |
| Two execution profiles | `src/agentic_rag/engine/` |
| Online pipeline | `src/agentic_rag/query_pipeline.py` |
| CER and snapshots | `src/agentic_rag/execution/` |
| Indexing and splitting | `src/agentic_rag/ingest/`, `indexing/` |
| ACL / egress | `src/agentic_rag/policy/` |
| Retrieval and fusion | `src/agentic_rag/retrieve/` |
| Post-hoc diagnostics | `src/agentic_rag/evaluation/`, `evidence/` |
| Report projections | `src/agentic_rag/reporting/` |

See [System Design and Technology Choices](system-design.md) for selection rationale, effective configuration, and key trade-offs; see [Known Limitations](known-limitations.md) for scale and deployment boundaries.
