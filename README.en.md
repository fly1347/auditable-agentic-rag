# Auditable Agentic RAG

[中文](README.md)

An evaluation-driven and auditable Agentic RAG reference implementation for enterprise-oriented engineering scenarios.

The project is organized around the full engineering lifecycle of knowledge-base question answering: source-level authorization, structure-aware chunking, controlled retrieval, evidence sufficiency, citation tracing, canonical execution records, offline evaluation, cost accounting, and runnable API, UI, and Docker entry points.

The public release defaults to:

- execution profile: `baseline`
- generator: OpenRouter `openai/gpt-4o-mini`
- evidence sufficiency judge: DeepSeek `deepseek-v4-flash`
- embedding: local `BAAI/bge-small-zh-v1.5`
- corpus: `sample_data/corpus/`
- fallback: disabled

`orchestrated` remains available as an optional stricter-evidence profile. When evidence is insufficient, it performs query rewriting, a second retrieval round, and a second sufficiency check.

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

All online entry points share `RagApplicationService`. The two profiles reuse the same retrieval, ACL, evidence, prompt, generation, and citation implementation; their differences are concentrated in the sufficiency contract and the control actions taken after evidence is judged insufficient.

The D-full classifier, Citation Support, Conflict, and Uncertainty signals live in the post-hoc evaluation layer and do not modify online answers.

See [System Architecture](docs/en/architecture.md) for the full design.

## Core Capabilities

| Capability | Implementation |
| :-- | :-- |
| Structure-aware chunking | Markdown structure-first splitting, largest-fit packing, hard budgeting with the actual tokenizer |
| Local index | Immutable builds + atomic `current.json` pointer |
| Retrieval | DIRECT / DECOMPOSE, RRF fusion, optional second retrieval round |
| Authorization | Source-level ACL, deny-by-default, filtering before TopK |
| Evidence | EvidenceSnapshot / PromptSnapshot / `[E#]` citation contract |
| Execution control | baseline binary sufficiency; orchestrated structured sufficiency |
| Canonical facts | CanonicalExecutionRecord (CER) captures execution, policy, evidence, calls, latency, and outcome |
| Evaluation | Online assertions, post-hoc D-full diagnostics, CER-native RAGAS, cost ledger, paired comparison |
| Service entry points | CLI, FastAPI, Streamlit, Docker Compose |
| Security baseline | Trusted identity adapter, query safety, egress gate, redaction, release scan |

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

The frozen project-specific in-domain regression set contains 30 questions. Both profiles use the same corpus, index, and first-round original-query Top5 results.

| Observation | baseline | orchestrated |
| :-- | --: | --: |
| ANSWERED / REFUSED | 29 / 1 | 25 / 5 |
| DIRECT / DECOMPOSE | 24 / 6 | 24 / 6 |
| Online tokens | 119,756 | 188,062 |
| Estimated online cost | $0.035468 | $0.073791 |
| Sum of per-question service time | 124.334 s | 167.940 s |

`orchestrated` additionally blocks q06, q19, q27, and q28 because the final prompt lacks the core answer-bearing evidence for those questions. It strengthens evidence control while reducing answer coverage and increasing online cost by 108%. Second-round retrieval recovered 0/5 cases in this run.

RAGAS on the 25 questions shared by both profiles:

| metric | baseline | orchestrated | delta |
| :-- | --: | --: | --: |
| Context Precision | 0.8734 | 0.9066 | +0.0331 |
| Faithfulness | 0.9691 | 0.9422 | -0.0269 |
| Answer Relevancy | 0.8673 | 0.8303 | -0.0370 |

B2 is a `derived_in_domain_regression` set intended for in-domain regression, evidence-chain validation, and paired profile comparison. It does not represent held-out generalization or real-world business accuracy.

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
sample_data/           Public original demo corpus
policy/                Sample source ACL registry
docker/                Containerized API/UI entry points
docs/                  System design, architecture, evaluation, security, deployment, and limits
artifacts/evaluation/  Public evaluation reports and model-selection evidence
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
