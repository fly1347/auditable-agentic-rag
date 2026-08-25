# Deployment Notes

## 1. Runtime Positioning

The public release targets local development, portfolio demos, and small-scale engineering validation.

“Local-first” means the corpus, embeddings, index, execution records, and evaluation artifacts remain local by default. The public default generation path uses OpenRouter `openai/gpt-4o-mini`, while evidence sufficiency is judged by DeepSeek `deepseek-v4-flash`; this is not a fully offline deployment.

## 2. Environment Setup

Python 3.10–3.12 is supported.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[local,ui]'
cp config.example.yaml config.yaml
cp .env.example .env
```

At minimum, `.env` needs:

- the OpenRouter and DeepSeek keys actually used by the runtime;
- replacement values for the demo API token mapping;
- cache and capacity settings that match the local environment.

A real `.env` must not enter Git, container images, or release packages.

## 3. Build the Public Sample Index

```bash
PYTHONPATH=src:. python -m agentic_rag.cli \
  --mode index \
  --config config.yaml \
  --corpus-dir sample_data/corpus \
  --rebuild
```

After a successful build, `artifacts/index/current.json` points to the new immutable build. If the embedding model is unavailable, a source lacks ACL registration, or token/coverage validation fails, the command stops and the previous pointer remains unchanged.

To inspect retrieval only:

```bash
PYTHONPATH=src:. python -m agentic_rag.cli \
  --mode retrieve \
  --config config.yaml \
  --query 'RAG 系统的主要流程是什么？' \
  --topk 3
```

## 4. CLI QA

Default baseline profile:

```bash
PYTHONPATH=src:. python -m agentic_rag.cli \
  --mode query --config config.yaml \
  --profile baseline \
  --qid demo-001 --run-id demo-baseline \
  --query 'RAG 系统的主要流程是什么？' \
  --debug-record
```

Strict-evidence profile:

```bash
PYTHONPATH=src:. python -m agentic_rag.cli \
  --mode query --config config.yaml \
  --profile orchestrated \
  --qid demo-002 --run-id demo-orchestrated \
  --query 'RAG 系统的主要流程是什么？' \
  --debug-record
```

Cloud calls require network access and may incur charges. CERs are appended to `artifacts/executions/records.jsonl` by default.

## 5. API

```bash
uvicorn agentic_rag.api.app:app \
  --host 127.0.0.1 --port 8000 --workers 1
```

Validate:

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/api/version
```

Query:

```bash
curl -fsS \
  -H 'X-API-Key: replace-this-demo-token' \
  -H 'Content-Type: application/json' \
  -d '{"query":"RAG 系统的主要流程是什么？","profile":"baseline"}' \
  http://127.0.0.1:8000/api/chat
```

Use `/api/chat/debug` when a complete CER projection is required. The corresponding principal must have `debug` or `admin` permission.

The API is best run with a single worker in the current reference implementation because CER, audit, and service logs use local JSONL files whose write coordination assumes a single process.

## 6. Streamlit UI

Keep the API running and open another terminal:

```bash
export AGENTIC_RAG_API_BASE_URL=http://127.0.0.1:8000
streamlit run src/agentic_rag/ui/streamlit_app.py
```

The UI only calls the API. It does not load provider keys, embeddings, the index, or the execution pipeline directly.

## 7. Docker Compose

The public Docker topology contains only the API and UI and uses the same cloud-default semantics from `config.docker.yaml`:

```text
Browser → UI container → API container
                         → local sample index
                         → configured cloud providers
```

Prepare environment variables:

```bash
cp docker/.env.example docker/.env
```

Build and start:

```bash
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml up -d
```

After validating health, version, API chat, and the UI, stop the stack:

```bash
docker compose -f docker/docker-compose.yml down
```

The public release does not provide an Ollama-specific Compose setup or local fallback. Container images still require a local embedding-model cache or access to obtain the model during build/startup. See [`docker/README.en.md`](../../docker/README.en.md) for cache and sample-index mounts.

## 8. Offline Gates

```bash
python -m compileall -q src tests eval scripts
PYTHONPATH=src:. python -m unittest discover -s tests -q
PYTHONPATH=src:. python eval/run_security_smoke.py \
  --output-dir artifacts/security-smoke
python scripts/release_scan.py .
```

These offline gates do not proactively call the generator, judge, or RAGAS evaluator.

## 9. Runtime Artifacts

| Artifact | Location |
| :-- | :-- |
| Current index pointer | `artifacts/index/current.json` |
| Immutable index build | `artifacts/index/builds/<build-id>/` |
| CER | `artifacts/executions/records.jsonl` |
| Public evaluation showcase | `artifacts/evaluation/` |
| Local logs | `logs/` |

Indexes, CERs, and logs may contain internal information and should not be committed or published directly.

## 10. Deployment Boundary

Docker Compose is intended for local reproduction, not production cloud deployment. The current version does not provide production-grade IAM, centralized logging, clustered vector databases, HA, autoscaling, disaster recovery, SLOs, or long-term data lifecycle policies.
