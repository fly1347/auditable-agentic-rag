# 已知限制

## 1. 核心证据仍有漏召回

q06、q19、q27、q28 的核心 answer-bearing evidence 未进入 Top10 和最终 Prompt。

- baseline 依赖模型参数知识给出可读答案；
- orchestrated 识别证据不足并拒答。

当前主要检索问题是：答案存在于语料中，但真正承载答案的段落可达性不足。Kubernetes、HNSW、表格、ASCII 架构图和跨段机制说明更容易出现该问题。

### 主要归因

- 当前以 dense retrieval 为主，问题措辞与答案段落表达不一致时，核心证据排名容易下降；
- TopK 候选池未包含核心证据时，RRF 和 rerank 只能重排已有候选，无法恢复池外证据；
- 二轮 rewrite 多为近义复述，查询扩展能力有限。

### 可选改进方向

- 对四道漏召回题测试 dense + sparse/BM25 混合检索；
- 比较不同 Embedding 模型对核心证据的 TopK 排名；
- 扩大初始候选池，再执行 RRF 与 rerank；
- 将二轮 rewrite 改为关键词、实体和答案约束驱动的查询扩展；
- 建立专项回归，分别记录核心证据的 Top10、Top20 与最终 Prompt 可达性。

## 2. 二轮检索能发现问题，恢复能力较弱

orchestrated 触发 5 次二轮检索，recovery 为 0/5。rewrite 多数属于近义复述，没有带来新的核心证据。

当前 Agentic 链路已经具备发现证据不足的能力；自主修复证据缺口仍是主要短板。

## 3. 两套 profile 存在明确取舍

| 维度 | baseline | orchestrated |
| :-- | :-- | :-- |
| 应回答题覆盖 | 29/29 | 25/29 |
| 证据控制 | 较宽松 | 严格 |
| 在线 Token | 119,756 | 188,062 |
| 在线估算成本 | $0.035468 | $0.073791 |

当前没有一个 profile 同时获得高覆盖、强 grounding、低成本和高恢复率。两套 profile 是场景选择，不是简单的高低配关系。

## 4. B2 只能证明同域回归稳定

B2 只有 30 题，且题目与冻结私有语料高度同域。它能够验证：

- 冻结语料与配置下的行为稳定性；
- 关键控制、证据路径和成本可复核；
- Splitter 修正与双 profile 差异。

它不能单独证明：

- 未知领域上的准确率；
- 真实业务效果；
- orchestrated 在所有质量维度普遍更优；
- 生产级质量或稳定性。

后续需要独立 held-out、域外、多跳、冲突、否定和真实攻击题集。

## 5. 评测信号仍有边界

- baseline 在线 security snapshot 未观测，`hard_gate_complete=0/30`；
- 回答质量分档尚未按 exact answer SHA 导入统一 release gate；
- q26 的机器 evidence gate 与人工答案 A 结论未完全对齐；
- Citation Support 主要是字符/词面规则，语义蕴含能力有限；
- Conflict 缺少独立 gold set，最终 0 conflicts 只表示规则未触发；
- RAGAS 依赖 LLM judge，受模型版本、随机性和 provider 波动影响；
- 成本来自静态价格表估算，不等同于实际账单。

## 6. 当前仍是本地参考实现

- `LocalVectorStore` 使用本地文件与内存 O(N) 点积；
- API 建议单 worker；
- CER、audit 和 service logs 使用本地 JSONL；
- 认证使用静态 token；
- tenant isolation 主要通过合成负控验证；
- ingest 主要支持 Markdown/TXT 和全量重建；PDF / Office / OCR 尚未建立解析质量、版面恢复与页码引用回归门禁；
- 未提供增量 Embedding、任务队列、生产向量数据库和知识库运营后台；
- UI 以单轮问答和调试展示为主；
- 未提供 HA、自动扩缩、灾备和生产 SLO。

因此项目定位是企业工程型 Agentic RAG 参考实现与可评估原型。

## 7. 安全能力属于工程基线

Query Safety、Prompt Injection、redaction、sanitizer 和 release scan 主要依赖规则与固定负控。source ACL 与 egress gate 提供 fail-close 合同，但没有接入企业 IdP、DLP、SIEM、密钥轮换与完整合规体系。

新增 schema、provider、工具调用或数据类型后，需要同步扩展安全测试并进行人工抽查。

## 8. 部署与公开边界

Docker Compose 面向本地复现。公开仓库排除 raw logs、完整私有语料、raw CER/evidence、真实 `.env`、模型缓存、experiments 和历史过程稿。

公开的 B2 人读报告用于展示冻结评测事实；公开 Quickstart 使用独立 sample corpus 和 sample regression set，不能从 sample data 复现完整 B2 指标。

## 9. 模型选型结果具有时间边界

C+ 模型横评主要发生在 2026 年 5 月，使用当时的 D-lite / Phase C 链路、Prompt、provider 版本和本地硬件。它用于证明项目如何进行模型角色划分和工程取舍，定位为历史工程证据，不承担当前通用模型排名。模型版本、alias、价格、网络和推理后端变化后，应使用当前链路和固定共同输入重新 benchmark。
