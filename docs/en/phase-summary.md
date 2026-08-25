# Project Evolution

The project followed a fixed mainline:

```text
A → A' → B → D-lite → C → C+ → D-full → E → F → G
```

## A: Baseline RAG

Built the minimum closed loop for document loading, text splitting, embeddings, local vector retrieval, prompt assembly, answer generation, and citation.

## A': Minimal Evaluation

Introduced a small regression set and behavior checks so changes to the main pipeline could be validated repeatedly.

## B: Evaluation Loop

Expanded to the 30-question B2 in-domain regression set and produced per-question results, retrieval signals, latency, and cost reports. The project moved from “can answer” to “can explain why an answer succeeded or failed.”

## D-lite: Controlled Two-Step Retrieval

Added DIRECT / DECOMPOSE routing, subquery retrieval, evidence sufficiency, query rewriting, and a second retrieval round. Agentic behavior was constrained to observable and regression-testable control nodes.

## C: Service Layer and Runtime Entry Points

Added FastAPI, Streamlit UI, Docker, logging, metrics, and load-test entry points, turning offline scripts into a runnable service.

## C+: Model, Cost, and Deployment Understanding

Moved model selection from intuition to focused engineering tests: established a framework for model intelligence and benchmark interpretation, candidate decision cards, local GPU / llama.cpp validation, self-hosting VRAM and cloud-GPU cost analysis, and a fixed C+5 mini-evaluation for generator comparison, manual per-question grading, and dual-evaluator RAGAS comparison.

The phase started from a local `qwen2.5:7b` baseline, continued with a local Qwen3.5-9B path, and compared GPT-4o-mini, DeepSeek V4 Flash / Pro, and a quality-ceiling model. Model roles were ultimately split: GPT-4o-mini as the default generator, DeepSeek V4 Flash as the sufficiency judge, and Qwen3.5-9B retained as local-fallback evidence. The project also concluded that API usage is more appropriate for low-frequency development scenarios in terms of time and operations cost, while self-hosting becomes necessary again when data cannot leave the controlled boundary.

See [Model Selection and Inference Deployment Evolution](model-selection.md) for the full decision history, historical benchmarks, and time boundaries.

## D-full: Full Workflow Diagnostics

The diagnostic chain became:

```text
GENERATE_ANSWER
→ CHECK_CITATION_SUPPORT
→ DETECT_CONFLICTS
→ BUILD_UNCERTAINTY
→ BUILD_RESPONSE
```

Later engineering consolidation fixed the classifier, Citation Support, Conflict, and Uncertainty as post-hoc CER evaluation signals. This retains full diagnostic capability without allowing offline analysis logic to alter online answers.

## E: Enterprise Engineering Baseline

Added trusted identity, source-level ACL, tenant placeholders, egress gates, redaction, audit, cost budgets, security negative controls, and release scanning. Authorization and data-egress controls follow fail-close contracts.

## F: Full Review, Corrections, and Final Evaluation

Phase F completed three categories of work.

### Unified Runtime and Fact Structure

```text
CLI / API / UI / Eval
→ RagApplicationService
→ baseline | orchestrated
→ shared corrected stages
→ CanonicalExecutionRecord
```

### Splitter and Index Corrections

Historical chunking had two major problems: dropped oversized fenced blocks and truncation against the BGE 512-token limit. The final production splitter became structure-first with largest-fit packing and a tokenizer hard budget, and the S2 index was frozen as:

```text
34 documents
575 chunks
575 vectors
512 dimensions
max content tokens = 510
```

### Final Dual-Profile Evaluation

Completed `baseline`, `orchestrated`, D-full, RAGAS, three-layer cost ledgers, and automated paired reports. The final frozen implementation recorded 82/82 tests PASS.

The key Phase F conclusion is that `baseline` provides higher coverage and lower cost, while `orchestrated` provides stricter evidence boundaries but currently has weak second-round recovery.

## G: Public Release

Phase G assembled the public repository from an empty staging area using a whitelist:

- retained only the runtime mainline, core evaluation entry points, tests, and release scripts;
- replaced the complete private corpus with original `sample_data`;
- rebuilt ACLs for sample sources;
- published human-readable `baseline`, `orchestrated`, and comparison reports;
- excluded `.env`, logs, raw CER, complete evidence, experiments, caches, and historical process drafts;
- rewrote README, architecture, evaluation, security, deployment, and limitation documentation;
- established a clean Git history after clean-install, tests, API/UI, Docker, and release-scan validation.

## Reusable Methods

The project produced several reusable engineering principles:

1. One execution, one machine fact record, multiple deterministic projections.
2. Keep `not_observed`, `not_applicable`, and `error` distinct.
3. Separate source hit from answer-bearing evidence.
4. Evaluate answer correctness separately from RAG grounding success.
5. Freeze shared inputs for comparisons and prefer matched cohorts.
6. Measure real character/token distributions before choosing a chunking strategy.
7. Report structures and fields are engineering interfaces too.
8. Define stop conditions for each phase; the release phase should not continue changing mainline behavior.
