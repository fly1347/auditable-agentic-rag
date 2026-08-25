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

The two profiles share route, retrieval, ACL, RRF, evidence, prompt, generation, and citation implementation. The incremental logic in `orchestrated` is concentrated in structured evidence judgment, rewrite, second-round retrieval, and a second judgment.

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
      ├─ DIRECT ─────> [ACL-eligible candidates → TopK] ─────────────────┐
      └─ DECOMPOSE ──> [ACL-eligible candidates per query → TopK → RRF] ┤
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

DIRECT retrieves with the original question. DECOMPOSE preserves retrieval events for both the original question and subqueries, then fuses them with RRF. Second-round retrieval does not overwrite first-round evidence; it creates a union while preserving lineage.

The system records these sets separately:

```text
retrieved → merged/reranked → evidence selected
→ prompt visible → cited
```

They are not interchangeable. Citations can only point to evidence the model actually saw in the prompt.

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
