# Auditable Agentic RAG

[English](README.en.md)

一个本地优先、可评估、可审计的企业工程型 Agentic RAG 参考实现。

项目围绕知识库问答的工程闭环展开：来源级权限、结构化切分、可控检索、证据充分性、引用追踪、统一执行记录、离线评测、成本核算，以及 API、UI 与 Docker 演示入口。

公开版默认使用：

- 执行 profile：`baseline`
- 生成模型：OpenRouter `openai/gpt-4o-mini`
- 证据充分性 Judge：DeepSeek `deepseek-v4-flash`
- Embedding：本地 `BAAI/bge-small-zh-v1.5`
- 语料：`sample_data/corpus/`
- fallback：关闭

`orchestrated` 作为可选严格证据 profile 保留。它会在证据不足时执行 query rewrite、第二轮检索和再次判断。

## 项目价值

很多 RAG Demo 只展示“检索后调用模型”。本项目重点展示答案之外的工程事实：

- 这个问题走了哪条路线；
- 哪些证据被检索、融合、送入 Prompt 和最终引用；
- ACL 与数据出境策略如何影响结果；
- 证据不足时系统如何拒答或进行第二轮检索；
- 一次执行如何沉淀为可回放、可评测、可核算成本的记录；
- baseline 与严格证据控制之间有哪些质量、覆盖率和成本取舍。

## 架构

### 系统总览

```text
[CLI · API · UI · Eval]
            │
            ▼
[RagApplicationService]
            │
            ▼
[身份与安全] → [路由与检索] → [证据控制] → [生成与引用]
      │             │              │             │
      └─────────────┴──────┬───────┴─────────────┘
                           ▼
             [CER · Audit · Metrics · Cost · Eval]

基础设施：[Corpus / Index]  [Embedding]  [LLM / Judge]
```

所有在线入口共用 `RagApplicationService`。两个 profile 共用检索、ACL、证据、Prompt、生成与引用实现；差异集中在 sufficiency 合同和证据不足后的控制动作。

D-full classifier、Citation Support、Conflict 和 Uncertainty 位于后置评测层，不改变在线答案。

完整说明见 [系统架构](docs/architecture.md)。

## 核心能力

| 能力 | 实现口径 |
| :-- | :-- |
| 结构化切分 | Markdown structure-first、largest-fit、真实 tokenizer 硬预算 |
| 本地索引 | 不可变 build + 原子 `current.json` 指针 |
| 检索 | DIRECT / DECOMPOSE、RRF 融合、可选二轮检索 |
| 权限 | source-level ACL，deny-by-default，TopK 前过滤 |
| 证据 | EvidenceSnapshot / PromptSnapshot / `[E#]` 引用合同 |
| 执行控制 | baseline binary sufficiency；orchestrated structured sufficiency |
| 统一事实 | CanonicalExecutionRecord（CER）记录执行、策略、证据、调用、时延与结果 |
| 评测 | 在线断言、D-full 后置诊断、CER-native RAGAS、成本总账与配对对比 |
| 服务入口 | CLI、FastAPI、Streamlit、Docker Compose |
| 安全基线 | 可信身份适配、query safety、egress gate、redaction、release scan |

## Quickstart

### 1. 安装

Python 支持 3.10–3.12。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[local,ui]'
cp config.example.yaml config.yaml
cp .env.example .env
```

在 `.env` 中填写本次实际使用的 `OPENROUTER_API_KEY`、`DEEPSEEK_API_KEY`，并更换演示 API token。不要提交真实 `.env`。

### 2. 建立 sample index

首次使用需要取得 `BAAI/bge-small-zh-v1.5`。已准备本地缓存时可以启用离线模式。

```bash
PYTHONPATH=src:. python -m agentic_rag.cli \
  --mode index \
  --config config.yaml \
  --corpus-dir sample_data/corpus \
  --rebuild
```

### 3. 运行一次 baseline 问答

```bash
PYTHONPATH=src:. python -m agentic_rag.cli \
  --mode query \
  --config config.yaml \
  --profile baseline \
  --query 'RAG 系统的主要流程是什么？' \
  --debug-record
```

该步骤会调用配置的云端 generator/judge，可能产生费用。provider 调用前仍会执行身份、egress 与预算检查。

### 4. 启动 API 与 UI

```bash
uvicorn agentic_rag.api.app:app \
  --host 127.0.0.1 --port 8000 --workers 1
```

另开终端：

```bash
export AGENTIC_RAG_API_BASE_URL=http://127.0.0.1:8000
streamlit run src/agentic_rag/ui/streamlit_app.py
```

完整启动、验证与停止方式见 [部署说明](docs/deployment-notes.md)。

## 评测摘要

冻结项目专用同域回归评测集包含 30 题。两套 profile 使用相同语料、索引和第一轮 original-query Top5。

| 观察项 | baseline | orchestrated |
| :-- | --: | --: |
| ANSWERED / REFUSED | 29 / 1 | 25 / 5 |
| DIRECT / DECOMPOSE | 24 / 6 | 24 / 6 |
| 在线 Token | 119,756 | 188,062 |
| 在线估算成本 | $0.035468 | $0.073791 |
| 题级服务耗时累计 | 124.334 s | 167.940 s |

orchestrated 额外拦截 q06、q19、q27、q28：四题均缺少核心 answer-bearing evidence。它提高了证据控制强度，同时降低回答覆盖率，并使在线成本增加 108%。本轮二轮检索 recovery 为 0/5。

RAGAS 共同 25 题：

| metric | baseline | orchestrated | delta |
| :-- | --: | --: | --: |
| Context Precision | 0.8734 | 0.9066 | +0.0331 |
| Faithfulness | 0.9691 | 0.9422 | -0.0269 |
| Answer Relevancy | 0.8673 | 0.8303 | -0.0370 |

B2 属于 `derived_in_domain_regression`，用于同域回归、证据链验证与 profile 配对比较，不代表 held-out 泛化能力或真实业务准确率。

完整结论见 [评测报告](docs/evaluation-report.md)，逐题与工作流报告见 [`artifacts/evaluation/`](artifacts/evaluation/README.md)。

## 安全、审计与成本

- 可信身份在接入层解析，roles/groups/tenant 不从请求正文接受；
- 未登记 source 在索引阶段 fail-close；
- ACL 在 TopK 前过滤，避免不可见证据参与排序与 Prompt；
- 每次 provider attempt 独立检查 egress 与预算；
- CER 保存 route、retrieval、evidence、prompt、model calls、timing、usage、policy 与 outcome；
- 成本来自静态价格表估算，用于同批工程比较，不等同于 provider 账单。

详见 [安全基线](docs/security-baseline.md)。

## 仓库结构

```text
src/agentic_rag/       在线实现与统一事实结构
eval/                  核心评测入口与 sample regression
tests/                 4 个核心治理与审计 contract tests
sample_data/           公开原创演示语料
policy/                sample source ACL registry
docker/                API/UI 容器化入口
docs/                  系统设计、架构、评测、安全、部署与限制
artifacts/evaluation/      公开冻结评测报告
scripts/               发布扫描、打包与辅助验证
```

## 文档导航

- [系统设计与技术选型](docs/system-design.md)
- [模型选型与推理部署演进](docs/model-selection.md)
- [系统架构](docs/architecture.md)
- [阶段演进](docs/phase-summary.md)
- [评测报告](docs/evaluation-report.md)
- [安全基线](docs/security-baseline.md)
- [部署说明](docs/deployment-notes.md)
- [已知限制](docs/known-limitations.md)

## 定位边界

本项目是企业工程型 Agentic RAG 参考实现与可评估原型，适合本地演示、工程验证和小规模回归。它不声明生产级多租户、IAM、HA、审计合规、SLO 或域外泛化能力。
