# Docker 本地复现

公开 Docker 拓扑只包含 API 与 UI：

```text
Browser → Streamlit UI → FastAPI
                       → local sample index
                       → OpenRouter / DeepSeek
```

UI 只通过 HTTP 调用 API，不接收 provider key。公开默认执行 profile 为
`baseline`；`orchestrated` 作为严格证据 profile 保留。Docker 拓扑不包含
Ollama、llama.cpp 服务或自动 provider fallback。

## 1. 准备环境变量

```bash
cp docker/.env.example docker/.env
```

编辑 `docker/.env`：

- 更换演示 API token；
- 填写 `OPENROUTER_API_KEY`；
- 填写 `DEEPSEEK_API_KEY`；
- 可按需修改预算与并发限制。

不要提交真实 `docker/.env`。

## 2. 准备 Embedding 缓存

容器默认：

```text
HF_HUB_OFFLINE=1
TRANSFORMERS_OFFLINE=1
```

因此启动前需要在宿主机准备 `BAAI/bge-small-zh-v1.5` 缓存。默认挂载：

```text
../.cache/huggingface → /root/.cache/huggingface
../.cache/torch       → /root/.cache/torch
```

没有可用缓存时，索引构建应显式失败，不会切换到其它 Embedding。

## 3. 构建镜像

```bash
docker compose -f docker/docker-compose.yml build
```

## 4. 建立 sample index

首次运行或 sample corpus 变化后：

```bash
docker compose -f docker/docker-compose.yml run --rm api   python -m agentic_rag.cli   --mode index   --config /app/config.docker.yaml   --corpus-dir /app/sample_data/corpus   --rebuild
```

生成的 index 与 vector store 通过宿主机 bind mount 保留。

## 5. 启动

```bash
docker compose -f docker/docker-compose.yml up -d
```

验证：

```bash
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/api/version

curl -fsS   -H 'X-API-Key: demo-public-token'   -H 'Content-Type: application/json'   -d '{"query":"RAG 系统的主要流程是什么？","profile":"baseline"}'   http://localhost:8000/api/chat
```

UI：

```text
http://localhost:8501
```

## 6. 停止

```bash
docker compose -f docker/docker-compose.yml down
```

运行时 index、CER 与 logs 保留在宿主机。该 Compose 用于本地复现和作品集
演示，不代表生产级云部署。
