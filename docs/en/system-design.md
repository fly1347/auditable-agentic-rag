# System Design and Technology Choices

## 1. Purpose

This document is the project’s global design entry point. It answers five questions:

1. What problem does the system solve, and what does it explicitly not solve?
2. From corpus ingestion to answer generation, which capabilities form the main pipeline?
3. Why was the current option selected at each layer?
4. What is the difference between public defaults, frozen evaluation configuration, and reserved configuration?
5. Under what conditions should the current trade-offs be reevaluated?

[System Architecture](architecture.md) focuses on component relationships, control flow, and implementation locations. This document focuses on design logic, effective configuration, and technical trade-offs. Executable values are still defined by `config.example.yaml`, `.env.example`, and the corresponding Docker configuration.

## 2. Project Goals and Boundaries

### 2.1 Core Goals

The project builds a controllable, explainable, and evaluable RAG engineering pipeline:

- **Local-first**: corpus, embeddings, index, execution records, and evaluation artifacts remain local by default.
- **Evidence-first**: answers must trace back to evidence actually visible to the model, not merely to retrieved candidates.
- **Authorization-first**: invisible sources must not enter TopK, fusion, reranking, prompts, or generation.
- **Bounded Agentic behavior**: decomposition, evidence judgment, rewriting, and one recovery retrieval are allowed; unbounded loops and arbitrary autonomous tool use are not.
- **Canonical facts**: online answers, audit, evaluation, cost, and reporting are projections of the same execution record.
- **Comparability**: `baseline` and `orchestrated` share the underlying implementation so that measured differences reflect evidence-control policy rather than unrelated code paths.

### 2.2 “Local-First” Does Not Mean “Fully Offline”

The public default path uses local corpus data, local BGE embeddings, and a local index. The generator and sufficiency judge call cloud services through OpenRouter and DeepSeek respectively. Data egress must pass egress policy, and restricted content is denied from public-cloud transmission by default.

The project therefore demonstrates a **local knowledge foundation + controlled cloud inference**, not a fully offline default deployment.

### 2.3 Scope

The current system is an enterprise-oriented Agentic RAG reference implementation and evaluable prototype for local demos, small knowledge bases, and regression validation. It does not claim production-grade multi-tenant isolation, enterprise IAM, distributed vector storage, HA, SLOs, compliance auditing, or out-of-domain generalization.

## 3. From Goals to Design Principles

| Goal | Design principle | System implementation |
| :-- | :-- | :-- |
| Consistent behavior across entry points | One application-service entry point | CLI, API, UI, and Eval all use `RagApplicationService` |
| Controlled knowledge boundary | Resolve identity and visibility before forming TopK | trusted principal, source ACL, pre-TopK filtering, pre-generation egress gate |
| Stable indexing of long documents | Constrain splitting by both document structure and the actual embedding tokenizer | structure-first splitter, 510-token hard gate, coverage/offset validation |
| Predictable Agentic behavior | Explicit bounds on routing, decomposition, and retry | DIRECT / DECOMPOSE, fixed number of subqueries, at most one R2 |
| Traceable answers | Keep retrieval, evidence, prompt, and citation sets distinct | EvidenceSnapshot, PromptSnapshot, `[E#]` citation contract |
| Stable evaluation facts | Offline evaluation reads frozen online execution facts | CER-native D-full, RAGAS, and cost ledgers |
| Explainable failure modes | Explicit provider, fallback, and fail-close configuration | egress checks, judge-failure refusal, public fallback disabled |

## 4. End-to-End Design Map

```text
[Markdown / TXT + Source ACL Registry]
                  │
                  ▼
[Loader] → [Structure-first Splitter] → [510-token Gate]
                  │
                  ▼
[Local BGE Embedding] → [Immutable Local Index]
                  │
                  ▼
[Trusted Principal + Query Safety]
                  │
                  ▼
[DIRECT / DECOMPOSE]
       │
       ▼
[ACL-eligible candidates] → [Dense Top10 + BM25 Top10] → [RRF(k=60) → Top5] → [Optional Rerank] → [ACL Recheck]
       │
       ▼
[EvidenceSnapshot] → [Sufficiency Judge]
       │                     │
       │                     └─ insufficient → rewrite + R2 (at most once)
       ▼
[PromptSnapshot] → [Egress / Budget Policy] → [Generator] → [Citation Contract · E#]
       │
       ▼
[CanonicalExecutionRecord]
       ├─ Response / Debug / Audit / Metrics / Cost
       └─ Offline D-full / RAGAS / Comparison / Report
```

This pipeline contains a data plane, a control plane, and a fact plane. The data plane handles corpus and evidence; the control plane handles authorization, routing, and failure policy; the fact plane records what the system actually did.

## 5. RAG Foundation: Configuration and Technology Choices

### 5.1 Corpus, Authorization, and Loading

| Area | Current design | Why | Cost / boundary |
| :-- | :-- | :-- | :-- |
| Public corpus | Markdown / TXT under `sample_data/corpus/` | Human-readable, reviewable, well suited to structure-aware splitting | Does not cover PDF, Office, OCR, or complex parsing pipelines |
| Source identity | Stable `source_id` derived from relative path | Deterministic within one repository layout; easy to connect ACL, citation, and evaluation | Path changes alter IDs; large-scale content operations need independent content IDs and versioning |
| Authorization registry | Separate Source ACL Registry | Decouples content from policy; source authorization becomes auditable | New sources must be registered |
| Missing-source policy | deny-by-default; fail-close during indexing | Prevents unregistered content from entering the queryable knowledge base | Incomplete configuration stops the build |

ACL uses **query-time visibility filtering over a shared index** rather than duplicating an index per identity. The local vector store computes similarities, but only chunks satisfying the principal authorization predicate can enter TopK. Fusion or reranking is followed by a second check. Unauthorized text never enters RRF, the reranker, EvidenceSnapshot, the prompt, or the generator.

This design fits small shared knowledge bases where authorization changes frequently and roles combine in multiple ways. If the business requires regulatory-grade physical separation, tenant-specific key isolation, or independent data lifecycles, split storage by tenant/security domain and retain query-time ACL as defense in depth.

The first release intentionally limits input to Markdown / TXT to stabilize a reviewable and reproducible document representation and keep engineering variables concentrated on splitting, indexing, recall, evidence control, and execution records. PDF adds text extraction, headers/footers, multi-column layout, tables, OCR, and page-citation quality. Without an independent Loader contract, parsing-quality samples, and regression gates, PDF errors would contaminate retrieval evaluation. The current release completes the main pipeline and evaluation loop first; PDF remains a later input extension.

### 5.2 Structure-Aware Chunking

The splitter first understands Markdown structure and then applies a hard budget using the actual embedding tokenizer:

1. Find the largest complete subtree under the budget along the heading tree.
2. If it exceeds the budget, recursively descend into atomic units such as paragraphs, lists, tables, and fenced blocks.
3. If an atomic unit still exceeds the budget, split it by sentence, list item, table row, or code line as appropriate.
4. Only if those results still exceed the limit, apply a final token window.
5. Repack adjacent units while remaining within budget, then validate coverage, offsets, and determinism.

The current content budget is **510 tokens**, aligned with the BGE `max_seq_length=512` while reserving room for special tokens. Tables, ASCII diagrams, and fenced blocks remain intact in the current public and frozen corpora; only a future individual structure that itself exceeds the budget will be hierarchically split.

This design prioritizes consistency between the text sent to the embedding model and the budget actually validated. The cost is higher implementation and testing complexity than character-based splitting, and no guarantee that arbitrarily long structures can remain indivisible.

### 5.3 Embedding and Index

| Area | Effective design |
| :-- | :-- |
| Embedding | local `BAAI/bge-small-zh-v1.5` |
| Vector dimension | 512 |
| Batch size | 32 |
| Normalization | L2 normalize |
| Query cache | in-process LRU, default 1000 entries |
| Index files | `vectors.npy + chunks.jsonl` |
| Update method | create a new immutable build, validate, then atomically switch `current.json` |

The small Chinese BGE model was selected to balance local resources, Chinese semantic performance, and reproducibility. Keeping embeddings and indexing local also reduces the egress surface for raw corpus content during ingestion.

Immutable builds avoid in-place mutation of the active index. Vector row count, chunk count, dimensions, and manifest must all validate before the current pointer switches; on failure the previous build remains usable. The cost is temporary extra disk use during builds, and the current implementation still performs full rebuilds.

The local vector store uses in-memory dot products and O(N) scanning. It is easy to inspect, debug, and freeze for regression, but it is not a large-scale online retrieval architecture.

### 5.4 Routing, Retrieval, and Fusion

The public online path keeps only two answerable routes:

| Route | Behavior | Design intent |
| :-- | :-- | :-- |
| DIRECT | Retrieve once with the original question | Control latency and cost for simple questions |
| DECOMPOSE | Generate two subqueries while retaining the original question; retrieve all three and fuse with RRF | Add different semantic views for compound questions while preserving original intent |

Routing uses deterministic rules rather than an additional LLM classifier. If subquery generation fails, execution falls back to retrieval with the original question so that one planning failure does not fail the entire request.

For each query, the public default retrieval path is `Dense Top10 + BM25 Top10 → RRF(k=60) → Top5`. Dense and BM25 operate over the same chunks from the current immutable index and the same source-level ACL-visible set; RRF uses ranks rather than directly comparing incompatible score scales. DECOMPOSE and second-round retrieval then apply another RRF layer across query / round results after `chunk_id` deduplication, preserving lexical recall, semantic recall, and different query perspectives.

Dense cosine values remain `vector_score`; RRF fusion values are recorded separately as `rrf_score`; `rerank_score` is written only when a reranker actually runs. RRF scores are never presented as vector similarity. Hybrid-internal Dense/BM25 retrieval events and the merge trace remain visible in CER. Retrieval scores are used for ranking and audit but are not sent to the structured sufficiency judge, so the judge does not treat incomparable retrieval scores as evidence strength.

CrossEncoder reranking is optional and disabled by default; the candidate model is `BAAI/bge-reranker-base`. A reranker can only reorder retrieved candidates and cannot recover core evidence that never entered the candidate pool. Recall should therefore be validated before deciding whether additional model loading, latency, and resource cost are justified.

### 5.5 Evidence Sufficiency and Bounded Recovery

The two profiles share retrieval, ACL, fusion, EvidenceSnapshot, prompt, generation, and citation implementation. Their differences are concentrated in the sufficiency contract:

| profile | Judge output | Primary intent |
| :-- | :-- | :-- |
| baseline | binary sufficiency | Default interaction, higher coverage, lower control complexity |
| orchestrated | structured EvidencePacket judgment | Stricter evidence explanation, audit, and refusal control |

When the Judge classifies evidence as insufficient, the system allows a query rewrite and one R2. R2 runs the same Hybrid retrieval with the rewritten query, unions it with R1 results, applies RRF fusion, rechecks ACL, and judges sufficiency again. If the second result is still insufficient, the system refuses. Judge failures also fail closed. If the structured judge returns malformed JSON, the parser retries exactly once; a second parse failure raises `SufficiencyJudgeOutputParseError` instead of being disguised as ordinary `INSUFFICIENT`, and both real provider attempts are recorded in CER.

“At most once” is intentional. It keeps incremental cost, latency, and state space predictable and prevents endless paraphrase loops. In the current Hybrid frozen evaluation, q17 and q27 recover successfully on R2, while q28 and q30 do not. Bounded recovery is therefore observably effective but still unstable; the next targets are candidate recall, gap-type-driven rewriting, and sufficiency calibration rather than simply adding more loops.

### 5.6 Prompt, Generation, and Citation

| Area | Public effective behavior |
| :-- | :-- |
| Prompt evidence limit | Up to 5 chunks |
| Per-chunk character truncation | Disabled; selected chunks remain complete |
| Minimum evidence | At least 2 chunks before generation |
| Citation format | `[E#]`, bound to prompt-visible evidence |
| System-fabricated citations | Disabled |
| generator | OpenRouter `openai/gpt-4o-mini` |
| sufficiency judge | DeepSeek `deepseek-v4-flash` |
| provider fallback | `[]`, disabled by default in the public release |

EvidenceSnapshot represents evidence selected by the control path. PromptSnapshot represents evidence the model actually receives. Citations can bind only to `[E#]` entries in PromptSnapshot; “retrieved at some point” cannot substitute for “actually visible to the model.” Citation checking records contract outcomes and does not silently fabricate missing sources.

Configuration declares `context_token_budget: 4096`, but the current implementation does not yet enforce it as a final prompt hard gate using the generator’s actual tokenizer. The constraints currently enforced are a maximum of five complete chunks and the minimum evidence count before generation. The field should be treated as an unfinished budgeting contract rather than a fulfilled safety guarantee; longer corpora or production traffic require tokenizer-aware prompt budgeting first.

Public fallback is disabled so that model identity, cost, and failure cause remain explicit rather than switching provider without the user’s knowledge. If availability later becomes more important than strict comparability, a policy-bound fallback can be designed explicitly, but every attempt should still pass independent egress and budget checks and be recorded in CER.

The current generator/judge pair was not chosen directly. The project began with local `qwen2.5:7b`, then went through RAGAS and sufficiency limitations, local GPU/llama.cpp validation, Qwen3.5 local follow-up tests, fixed-set comparison across six generator candidates, and API-versus-self-hosting cost analysis before converging on the current role split. See [Model Selection and Inference Deployment Evolution](model-selection.md) for the full historical evidence, time boundary, and re-selection method.

## 6. Canonical Facts, Evaluation, and Observability

### 6.1 Why CER Exists

If online responses, logs, evaluation inputs, and cost tables reconstruct facts independently, drift appears: “the contexts in the report are not the contexts the model actually saw” or “the final answer is used to infer intermediate process.”

Every execution therefore produces a CanonicalExecutionRecord containing:

```text
identity · provenance · principal · policy · route
retrieval · rerank · merge · evidence · prompt
sufficiency · model_calls · usage · timing · outcome
evaluation · errors · events
```

CER is the execution fact source. Response, debug, audit, metrics, cost, and evaluation are different projections of it. Historical fields that were not observed remain `not_observed`; they are not invented from final answers.

### 6.2 Separating Online Control from Offline Diagnostics

The online path runs only the safety, retrieval, sufficiency, generation, and citation contracts required to answer the request. The D-full classifier, Citation Support, Conflict, Uncertainty, and RAGAS live offline. They read frozen CERs, do not rerun retrieval, and do not modify already generated answers.

This separation prevents evaluation-model cost and latency from entering user requests while keeping offline analysis tied to what actually happened during execution. The trade-off is that offline findings do not automatically repair the current answer; they must feed into the next design, configuration, or data change.

## 7. Public Defaults vs. Frozen Evaluation Snapshot

These two sets of facts have different responsibilities and should not be mixed:

| Scope | Public Quickstart | Frozen full evaluation |
| :-- | :-- | :-- |
| Purpose | Let readers run the main pipeline on original sample data | Show paired engineering evaluation on the complete private corpus |
| Corpus | `sample_data/corpus/` | Frozen corpus: 34 documents |
| Index | Rebuilt locally by the user | 575 chunks / 575 vectors / 512 dimensions |
| Default profile | baseline | Paired baseline and orchestrated runs |
| generator | OpenRouter `openai/gpt-4o-mini` | Defined by frozen execution records |
| judge | DeepSeek `deepseek-v4-flash` | Defined by frozen execution records |
| fallback | disabled | Defined by frozen execution records |
| Reproducible scope | Sample behavior, interfaces, and control contracts | Frozen facts in public human-readable reports; sample data cannot recompute the full metrics |

The public repository includes the complete implementation, sample data, and human-readable evaluation reports, but not the private corpus, raw CER, raw evidence, complete logs, or real credentials. Quickstart is a functional reproduction path, not a claim that the full evaluation numbers can be recomputed from the sample corpus.

## 8. Key Trade-Offs

| Current choice | What it provides | What it gives up or postpones |
| :-- | :-- | :-- |
| Local BGE + local index | Data control, easy debugging, low external dependency | Large-scale ANN, distributed expansion, online incremental updates |
| structure-first + token hard budget | Structural integrity for current corpus, verifiable embedding inputs | More implementation complexity; arbitrarily long structures may still split |
| Hybrid RRF (Dense Top10 + BM25 Top10 → Top5), rerank disabled by default | Combines semantic and lexical recall without cross-retriever score calibration | Adds local BM25 work; RRF can still reward shared wrong consensus and does not replace semantic reranking |
| Rule routing + fixed two subqueries | Predictable, testable, bounded extra calls | Less planning freedom for complex tasks |
| At most one R2 | Bounded cost and state space | Multi-round autonomous search and stronger recovery |
| baseline / orchestrated dual profiles | Observe coverage, grounding, and cost trade-offs over one shared foundation | No claim that one single mode is globally optimal |
| Shared index + pre-TopK ACL | Flexible permission changes without index duplication | Not equivalent to regulatory-grade physical tenant isolation |
| Cloud generator/judge, no default fallback | Strong model capability with explicit identity and cost | Fully offline operation and automatic resilience to provider outages |
| CER canonical facts | Auditability, reproducibility, stable evaluation | Schema, storage, and privacy-governance cost |
| Deep offline evaluation | No extra online latency; frozen retrospective analysis | Diagnostics do not alter the answer in real time |

## 9. When to Reevaluate Technology Choices

Reevaluate the current reference implementation when any of the following becomes true:

- Corpus size or concurrency makes O(N) scanning incompatible with latency targets: migrate to a production vector database with metadata filtering.
- Tenant or regulatory requirements demand physical isolation: separate indexes, keys, and lifecycles by tenant/security domain.
- Document types expand to PDF, Office, images, or scans: add parsing, OCR, layout reconstruction, and quality gates.
- Core evidence repeatedly fails to enter the candidate pool or remains poorly ranked after RRF: improve query expansion, candidate recall, and fusion diagnostics before evaluating reranking.
- Second-round recovery remains insufficient under measurement: introduce gap-type-aware rewrite, multi-query retrieval, or bounded tool retrieval instead of unbounded loops.
- Prompts may receive substantially more evidence: implement generator-tokenizer-aware hard budgeting, truncation policy, and regression tests.
- API must support multiple workers or HA: move JSONL execution records, audit, and logs to storage with concurrency and durability guarantees.
- Real organizational identity is integrated: replace static tokens with IdP / IAM and unify principal, tenant, and audit governance.
- The business requires fully offline or restricted-data inference: add separately evaluated local generator/judge profiles while preserving explicit egress fail-close behavior.
- Generalization must be demonstrated: add independent held-out, out-of-domain, multi-hop, conflict, negation, and realistic attack sets.

## 10. Further Reading

- Component topology and online control flow: [System Architecture](architecture.md)
- Runtime, configuration, and Docker entry points: [Deployment Notes](deployment-notes.md)
- ACL, egress, and release-security contracts: [Security Baseline](security-baseline.md)
- Frozen evaluation results and interpretation boundary: [Evaluation Report](evaluation-report.md)
- Unresolved engineering issues: [Known Limitations](known-limitations.md)
