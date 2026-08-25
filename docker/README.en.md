# Reproducing the System with Docker

The public Docker topology contains only the API and UI:

```text
Browser → Streamlit UI → FastAPI
                       → local sample index
                       → OpenRouter / DeepSeek
```

The UI talks to the API over HTTP and does not receive provider keys. The public default execution profile is `baseline`; `orchestrated` remains available as a stricter-evidence profile. The Docker topology does not include Ollama, llama.cpp services, or automatic provider fallback.

## 1. Prepare Environment Variables

```bash
cp docker/.env.example docker/.env
```

Edit `docker/.env`:

- replace the demo API token;
- set `OPENROUTER_API_KEY`;
- set `DEEPSEEK_API_KEY`;
- adjust budget and concurrency limits if needed.

Never commit a real `docker/.env` file.

## 2. Prepare the Embedding Cache

The containers default to:

```text
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

Therefore the host must already contain a cache for `BAAI/bge-small-zh-v1.5` before startup. The default mounts are:

```text
../.cache/huggingface → /root/.cache/huggingface
../.cache/torch       → /root/.cache/torch
```

If no usable cache is available, index construction fails explicitly rather than switching to another embedding model.

## 3. Build the Images

```bash
docker compose -f docker/docker-compose.yml build
```

## 4. Build the Sample Index

Run this on first use or after changing the sample corpus:

```bash
docker compose -f docker/docker-compose.yml run --rm api   python -m agentic_rag.cli   --mode index   --config /app/config.docker.yaml   --corpus-dir /app/sample_data/corpus   --rebuild
```

The generated index and vector store are persisted through host bind mounts.

## 5. Start the Services

```bash
docker compose -f docker/docker-compose.yml up -d
```

Validate the deployment:

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/api/version

curl -fsS   -H 'X-API-Key: demo-public-token'   -H 'Content-Type: application/json'   -d '{"query":"RAG 系统的主要流程是什么？","profile":"baseline"}'   http://localhost:8000/api/chat
```

UI:

```text
http://localhost:8501
```

## 6. Stop the Services

```bash
docker compose -f docker/docker-compose.yml down
```

Runtime indexes, CERs, and logs remain on the host. This Compose setup is intended for local reproduction and portfolio demos; it is not a production cloud deployment.
