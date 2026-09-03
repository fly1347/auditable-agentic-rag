# Auditable Agentic RAG

[中文](README.md)

An evaluation-driven and auditable Agentic RAG reference implementation for enterprise-oriented engineering scenarios.

The project is organized around the full engineering lifecycle of knowledge-base question answering: source-level authorization, structure-aware chunking, controlled retrieval, evidence sufficiency, citation tracing, canonical execution records, offline evaluation, cost accounting, and runnable API, UI, and Docker entry points.

The public release defaults to:

- execution profile: `baseline`
- generator: OpenRouter `openai/gpt-4o-mini`
- evidence sufficiency judge: DeepSeek `deepseek-v4-flash`
- embedding: local `BAAI/bge-small-zh-v1.5`
- retrieval: `Dense Top10 + BM25 Top10 → RRF(k=60) → Top5`
- corpus: `sample_data/corpus/`
- fallback: disabled

`orchestrated` remains available as an optional stricter-evidence profile. Both profiles share query rewriting and at most one second retrieval round after insufficient evidence; the main difference is the sufficiency contract: `baseline` uses a binary judgment, while `orchestrated` produces a structured SufficiencyResult over an EvidencePacket for stronger evidence explanation, auditability, and refusal control.

## Why This Project

Many RAG demos stop at “retrieve context, then call a model.” This project focuses on the engineering facts around the answer:

- which execution path a request followed;
- which evidence was retrieved, fused, exposed to the prompt, and ultimately cited;
- how ACL and data-egress policy change the result;
- how the system refuses or performs a second retrieval round when evidence is insufficient;
- how one execution becomes a replayable, evaluable, and cost-accountable record;
- what quality, coverage, and cost trade-offs exist between the baseline and stricter evidence control.

## Architecture

### System Overview

```text
[CLI · API · UI · Eval]
            │
            ▼
[RagApplicationService]
            │
            ▼
[Identity & Safety] → [Routing & Retrieval] → [Evidence Control] → [Generation & Citation]
      │                     │                       │                       │
      └─────────────────────┴───────────┬───────────┴───────────────────────┘
                                        ▼
                         [CER · Audit · Metrics · Cost · Eval]

Infrastructure: [Corpus / Index]  [Embedding]  [LLM / Judge]
```

All online entry points share `RagApplicationService`. The two profiles reuse the same retrieval, ACL, evidence, prompt, generation, citation, and bounded recovery flow after insufficient evidence; their differences are concentrated in the sufficiency contract and judgment granularity.

The D-full classifier, Citation Support, Conflict, and Uncertainty signals live in the post-hoc evaluation layer and do not modify online answers.

See [System Architecture](docs/en/architecture.md) for the full design.

## Core Capabilities

| Capability | Implementation |
| :-- | :-- |
| Structure-aware chunking | Markdown structure-first splitting, largest-fit packing, hard budgeting with the actual tokenizer |
| Local index | Immutable builds + atomic `current.json` pointer |
| Retrieval | Hybrid RRF: Dense Top10 + BM25 Top10 → RRF(k=60) → Top5; DIRECT / DECOMPOSE; optional second retrieval round |
| Authorization | Source-level ACL, deny-by-default, filtering before TopK |
| Evidence | EvidenceSnapshot / PromptSnapshot / `[E#]` citation contract |
| Execution control | baseline binary sufficiency; orchestrated structured sufficiency |
| Canonical facts | CanonicalExecutionRecord (CER) captures execution, policy, evidence, calls, latency, and outcome |
| Evaluation | Online assertions, post-hoc D-full diagnostics, CER-native RAGAS, cost ledger, paired comparison |
| Service entry points | CLI, FastAPI, Streamlit, Docker Compose |
| Security baseline | Trusted identity adapter, query safety, egress gate, redaction, release scan |

## System Design

The project is not only a composition of RAG components; key choices are placed behind verifiable engineering constraints. Corpus data and indexing remain local-first; ACL filtering happens before TopK; Agentic behavior is bounded to DIRECT / DECOMPOSE plus at most one second retrieval round; and EvidenceSnapshot, PromptSnapshot, and CER separately record what was retrieved, what the model actually saw, and what happened during one execution. Evaluation, audit, and cost reports derive from frozen execution facts instead of reconstructing context later.

See [System Design and Technology Choices](docs/en/system-design.md) for the full design rationale, alternatives, and re-evaluation conditions.

## Model Selection and Deployment

Models are selected by role rather than by a single leaderboard. The project started with local Qwen / Ollama, then compared local inference, fixed evaluation sets, judge replacements, RAGAS compatibility, latency, and cost before converging on the current split: local BGE for embeddings, GPT-4o-mini as the default answer generator, and DeepSeek Flash for online sufficiency judgment. Public fallback is disabled so model identity, failure causes, and cost remain explicit.

See [Model Selection and Inference Deployment Evolution](docs/en/model-selection.md) for the full experiments, model comparisons, API-versus-local deployment trade-offs, and re-selection criteria.

## Quickstart

### 1. Install

Python 3.10–3.12 is supported.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[local,ui]'
cp config.example.yaml config.yaml
cp .env.example .env
```

Set the `OPENROUTER_API_KEY` and `DEEPSEEK_API_KEY` values actually used for the run in `.env`, and replace the demo API token. Never commit a real `.env` file.

### 2. Build the sample index

The first run requires `BAAI/bge-small-zh-v1.5`. If the model is already cached locally, offline mode can be enabled.

```bash
PYTHONPATH=src:. python -m agentic_rag.cli \
  --mode index \
  --config config.yaml \
  --corpus-dir sample_data/corpus \
  --rebuild
```

### 3. Run one baseline query

```bash
PYTHONPATH=src:. python -m agentic_rag.cli \
  --mode query \
  --config config.yaml \
  --profile baseline \
  --query 'RAG 系统的主要流程是什么？' \
  --debug-record
```

This step calls the configured cloud generator and judge and may incur provider charges. Identity, egress, and budget checks still run before each provider call.

### 4. Start the API and UI

```bash
uvicorn agentic_rag.api.app:app \
  --host 127.0.0.1 --port 8000 --workers 1
```

In another terminal:

```bash
export AGENTIC_RAG_API_BASE_URL=http://127.0.0.1:8000
streamlit run src/agentic_rag/ui/streamlit_app.py
```

See [Deployment Notes](docs/en/deployment-notes.md) for complete startup, validation, and shutdown instructions.

## Evaluation Summary

The frozen project-specific in-domain regression set contains 30 questions. Both profiles use the same corpus, index, and Hybrid RRF retrieval configuration.

| Observation | baseline | orchestrated |
| :-- | --: | --: |
| ANSWERED / REFUSED | 29 / 1 | 27 / 3 |
| DIRECT / DECOMPOSE | 24 / 6 | 24 / 6 |
| Online tokens | 123,627 | 190,941 |
| Estimated online cost | $0.036531 | $0.073633 |
| Sum of per-question service time | 137.674 s | 194.988 s |

Hybrid `baseline` produces valid answers for all 29 answerable questions. `orchestrated` recovers q17 and q27 on the second retrieval round, then ultimately refuses q28 and q30. q28 remains an answer-bearing retrieval gap; q30 is better explained as an over-strict / provider-variable structured-sufficiency judgment. The online cost of `orchestrated` is about 2.02× `baseline`.

RAGAS on the 27 questions shared by both profiles:

| metric | baseline | orchestrated | delta |
| :-- | --: | --: | --: |
| Context Precision | 0.8539 | 0.8197 | -0.0342 |
| Faithfulness | 0.9633 | 0.9562 | -0.0071 |
| Answer Relevancy | 0.8585 | 0.8468 | -0.0118 |

In the direct Dense-only → Hybrid RRF retrieval probe, manually confirmed CORE Hit@5 improves from 14/27 to 20/27. This is the primary evidence supporting the public default Retriever change. B2 is a `derived_in_domain_regression` set intended for in-domain regression, evidence-chain validation, and paired profile comparison. It does not represent held-out generalization or real-world business accuracy.

See the [Evaluation Report](docs/en/evaluation-report.md) for the full conclusions and [`artifacts/evaluation/`](artifacts/evaluation/README.md) for per-question and workflow reports.

## Security, Audit, and Cost

- Trusted identity is resolved at the access layer; roles, groups, and tenant cannot be supplied in the request body.
- Unregistered sources fail closed during indexing.
- ACL filtering occurs before TopK so invisible evidence cannot participate in ranking or enter the prompt.
- Every provider attempt independently checks egress policy and budget.
- CER records route, retrieval, evidence, prompt, model calls, timing, usage, policy, and outcome.
- Cost is estimated from a static price table for within-batch engineering comparison and is not a provider billing reconciliation.

See [Security Baseline](docs/en/security-baseline.md).

## Repository Layout

```text
src/agentic_rag/       Online implementation and canonical execution structures
eval/                  Core evaluation entry points and sample regression data
tests/                 Core governance, Hybrid retrieval, and sufficiency contract tests
sample_data/           Public original demo corpus
policy/                Sample source ACL registry
docker/                Containerized API/UI entry points
docs/                  System design, architecture, evaluation, security, deployment, and limits
artifacts/evaluation/  Public frozen evaluation reports
scripts/               Release scan, packaging, and helper validation scripts
```

## Documentation

- [System Design and Technology Choices](docs/en/system-design.md)
- [Model Selection and Inference Deployment Evolution](docs/en/model-selection.md)
- [System Architecture](docs/en/architecture.md)
- [Project Evolution](docs/en/phase-summary.md)
- [Evaluation Report](docs/en/evaluation-report.md)
- [Security Baseline](docs/en/security-baseline.md)
- [Deployment Notes](docs/en/deployment-notes.md)
- [Known Limitations](docs/en/known-limitations.md)

## Scope

This project is an enterprise-oriented Agentic RAG reference implementation and evaluable prototype for local demos, engineering validation, and small-scale regression testing. It does not claim production-grade multi-tenancy, IAM, HA, compliance auditing, SLOs, or out-of-domain generalization.
