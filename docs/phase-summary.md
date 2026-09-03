# 阶段演进

项目按固定主线推进：

```text
A → A' → B → D-lite → C → C+ → D-full → E → F → G
```

## A：基础 RAG

建立文档加载、文本切分、Embedding、本地向量检索、Prompt 拼接、答案生成和引用的最小闭环。

## A'：最小评估

引入小规模回归题集与行为检查，让主链修改能够被重复验证。

## B：评估闭环

扩展到 B2 30 题同域回归集，形成逐题结果、检索信号、时延和成本报告。项目从“能回答”转向“能定位答案为何成功或失败”。

## D-lite：受控双步检索

加入 DIRECT / DECOMPOSE 路由、子问题检索、证据充分性判断、query rewrite 和第二轮检索。Agentic 行为被限制在可观察、可回归的控制节点中。

## C：服务化与运行入口

补齐 FastAPI、Streamlit UI、Docker、日志、指标和压测入口，将离线脚本收束为可运行服务。

## C+：模型、成本与部署认知

把模型选择从经验判断改成专项工程测试：建立模型信息源与 benchmark 阅读框架、候选决策卡、本地 GPU / llama.cpp 验证、自部署 VRAM / 云 GPU 成本认知，并用固定 C+5 小评测集执行 generator 横评、人工逐题标注和双 evaluator RAGAS 对照。

阶段从 `qwen2.5:7b` 本地 baseline 出发，继续验证 Qwen3.5-9B 本地路线，并比较 GPT-4o-mini、DeepSeek V4 Flash / Pro 和质量上限模型。最终将模型按角色拆分：GPT-4o-mini 作为默认 generator，DeepSeek V4 Flash 作为 sufficiency judge，Qwen3.5-9B 保留本地 fallback 证据；同时确认低频开发场景下 API 的时间与运维成本更合适，自部署在数据不可外发时重新成为必要路线。

完整决策史、历史 benchmark 与时间边界见 [模型选型与推理部署演进](model-selection.md)。

## D-full：完整工作流诊断

形成：

```text
GENERATE_ANSWER
→ CHECK_CITATION_SUPPORT
→ DETECT_CONFLICTS
→ BUILD_UNCERTAINTY
→ BUILD_RESPONSE
```

后续工程收束将 classifier、Citation Support、Conflict 和 Uncertainty 固定为 CER 后置评测层。这样保留完整诊断能力，同时避免离线分析逻辑改变在线答案。

## E：企业工程基线

加入可信身份、source-level ACL、tenant 预留、egress gate、redaction、审计、成本预算、安全负控和发布扫描。权限与外发控制采用 fail-close 合同。

## F：全量 Review、修正与最终评测

Phase F 完成了三类工作。

### 统一运行与事实结构

```text
CLI / API / UI / Eval
→ RagApplicationService
→ baseline | orchestrated
→ shared corrected stages
→ CanonicalExecutionRecord
```

### Splitter 与索引纠偏

历史切分存在超长 fenced block 丢块和 BGE 512 截断问题。最终生产切分改为 structure-first、largest-fit 和 tokenizer hard budget，并冻结 S2 索引：

```text
34 documents
575 chunks
575 vectors
512 dimensions
max content tokens = 510
```

### 双 profile 最终评测

完成 baseline、orchestrated、D-full、RAGAS、三类成本总账和自动配对报告。冻结实现的最终记录为 82/82 tests PASS。

Phase F 的关键结论是：baseline 提供更高覆盖率和较低成本；orchestrated 提供更严格的证据边界，但当前二轮恢复能力不足。

## G：公开发布

Phase G 从空 staging 按白名单组装公开仓库：

- 只保留运行主线、核心评测入口、4 个核心治理与审计 contract tests 和发布脚本；
- 用原创 `sample_data` 替代完整私有语料；
- 为 sample sources 重建 ACL；
- 公开 baseline / orchestrated / comparison 人读报告；
- 排除 `.env`、logs、raw CER、完整 evidence、experiments、缓存和历史过程稿；
- 重写 README、架构、评测、安全、部署与限制文档；
- 通过 clean install、tests、API/UI、Docker 和 release scan 后建立全新 Git 历史。

## 2026-09 维护更新

项目发布后按维护口径完成一次 Retriever 与 sufficiency 合同修正，不新增阶段：

- 公开默认 Retriever 从 Dense-only 固定为 `Dense Top10 + BM25 Top10 → RRF(k=60) → Top5`，baseline / orchestrated / API / eval 共用同一实现；
- `vector_score`、`rrf_score`、`rerank_score` 分离，Hybrid 内部 Dense/BM25 events 与 merge trace 保留到 CER，检索分数不进入 structured sufficiency prompt；
- structured sufficiency malformed JSON 只重试一次，第二次失败显式记录 `SufficiencyJudgeOutputParseError`，不伪装为普通证据不足；
- 增加 Hybrid RRF、score semantics、sufficiency prompt / parse retry 等公开 contract tests；
- 基于同一冻结索引完成 Dense / Hybrid 对照与新一轮双 profile 评测，Hybrid CORE Hit@5 从 14/27 提升到 20/27，并保留 q28 / q30 等已知边界。

该更新属于已发布项目的维护与证据刷新，不改变 `A → … → G` 的历史阶段线。

## 方法沉淀

项目形成了几条可复用原则：

1. 一次运行、一份机器事实、多个确定性投影；
2. `not_observed`、`not_applicable` 和 `error` 保持独立；
3. source hit 与 answer-bearing evidence 分开判断；
4. 答案正确与 RAG grounding 成功分开评价；
5. 对比实验冻结共同输入，优先做 matched cohort；
6. 先测量真实 char/token 分布，再决定切分策略；
7. 报告结构和字段也是工程接口；
8. 每个阶段设停止线，发布阶段不继续修改主链行为。
