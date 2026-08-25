# 部署说明

## 1. 运行定位

公开版面向本地开发、作品集演示和小规模工程验证。

“本地优先”指语料、Embedding、索引、执行记录和评测产物默认保留在本机。公开默认生成链使用 OpenRouter `openai/gpt-4o-mini`，充分性判断使用 DeepSeek `deepseek-v4-flash`；它不是完全离线方案。

## 2. 环境准备

Python 支持 3.10–3.12。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[local,ui]'
cp config.example.yaml config.yaml
cp .env.example .env
```

`.env` 至少需要：

- 实际使用的 OpenRouter 与 DeepSeek key；
- 已更换的 API demo token 映射；
- 与运行环境一致的缓存和容量配置。

真实 `.env` 不进入 Git、镜像或发布包。

## 3. 建立公开 sample index

```bash
PYTHONPATH=src:. python -m agentic_rag.cli \
  --mode index \
  --config config.yaml \
  --corpus-dir sample_data/corpus \
  --rebuild
```

索引成功后，`artifacts/index/current.json` 指向新的不可变 build。缺少 Embedding 模型、ACL 登记或 token/coverage 校验失败时，命令会停止，旧指针保持不变。

只检查检索：

```bash
PYTHONPATH=src:. python -m agentic_rag.cli \
  --mode retrieve \
  --config config.yaml \
  --query 'RAG 系统的主要流程是什么？' \
  --topk 3
```

## 4. CLI 问答

默认 baseline：

```bash
PYTHONPATH=src:. python -m agentic_rag.cli \
  --mode query --config config.yaml \
  --profile baseline \
  --qid demo-001 --run-id demo-baseline \
  --query 'RAG 系统的主要流程是什么？' \
  --debug-record
```

严格证据 profile：

```bash
PYTHONPATH=src:. python -m agentic_rag.cli \
  --mode query --config config.yaml \
  --profile orchestrated \
  --qid demo-002 --run-id demo-orchestrated \
  --query 'RAG 系统的主要流程是什么？' \
  --debug-record
```

云端调用会联网并可能计费。CER 默认追加到 `artifacts/executions/records.jsonl`。

## 5. API

```bash
uvicorn agentic_rag.api.app:app \
  --host 127.0.0.1 --port 8000 --workers 1
```

验证：

```bash
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/api/version
```

问答：

```bash
curl -fsS \
  -H 'X-API-Key: replace-this-demo-token' \
  -H 'Content-Type: application/json' \
  -d '{"query":"RAG 系统的主要流程是什么？","profile":"baseline"}' \
  http://127.0.0.1:8000/api/chat
```

需要完整 CER 投影时使用 `/api/chat/debug`，对应身份必须拥有 `debug` 或 `admin` 权限。

API 建议保持单 worker：当前 CER、audit 和 service logs 使用本地 JSONL，写入协调面向单进程参考实现。

## 6. Streamlit UI

API 保持运行，另开终端：

```bash
export AGENTIC_RAG_API_BASE_URL=http://127.0.0.1:8000
streamlit run src/agentic_rag/ui/streamlit_app.py
```

UI 只调用 API，不直接加载 provider key、Embedding、索引或运行主链。

## 7. Docker Compose

公开 Docker 拓扑只包含 API 与 UI，使用同一份 `config.docker.yaml` 云端默认口径：

```text
Browser → UI container → API container
                         → local sample index
                         → configured cloud providers
```

准备环境变量：

```bash
cp docker/.env.example docker/.env
```

构建与启动：

```bash
docker compose -f docker/docker-compose.yml build
docker compose -f docker/docker-compose.yml up -d
```

验证 health、version、API chat 与 UI 后停止：

```bash
docker compose -f docker/docker-compose.yml down
```

公开版不提供 Ollama 专用 Compose 或本地 fallback。容器镜像仍需要本地 Embedding 模型缓存或在构建/启动阶段取得模型；具体缓存与 sample index 挂载以 `docker/README.md` 为准。

## 8. 离线门禁

公开版只保留 4 个核心治理与审计 contract test 文件（11 条测试），而不是 Phase F 的完整开发测试集。

```bash
python -m compileall -q src tests eval scripts
PYTHONPATH=src:. python -m unittest discover -s tests -q
PYTHONPATH=src:. python eval/run_security_smoke.py \
  --output-dir artifacts/security-smoke
python scripts/release_scan.py .
```

离线门禁不会主动调用 generator、judge 或 RAGAS evaluator。

## 9. 运行产物

| 产物 | 位置 |
| :-- | :-- |
| 当前索引指针 | `artifacts/index/current.json` |
| 不可变 index build | `artifacts/index/builds/<build-id>/` |
| CER | `artifacts/executions/records.jsonl` |
| 公开评测展示 | `artifacts/evaluation/` |
| 本地日志 | `logs/` |

索引、CER 和日志可能包含内部信息，不应直接提交或公开。

## 10. 部署边界

Docker Compose 用于本地复现，不代表生产云部署。当前版本未提供生产级 IAM、集中日志、向量数据库集群、HA、自动扩缩、灾备、SLO 或长期数据生命周期策略。
