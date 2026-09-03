# 已知限制

## 1. Hybrid RRF 仍存在 answer-bearing 排名边界

当前公开默认已从 Dense-only 切换为 `Dense Top10 + BM25 Top10 → RRF(k=60) → Top5`。人工精确标注的 CORE Hit@5 从 14/27 提升到 20/27，q06、q19 等旧 Dense 缺口已经修复；但 q28 仍暴露出真实检索边界。

q28 的 etcd 详解片段在 Dense 与 BM25 单路都不够靠前，RRF 又会奖励两路共同靠前的概览块，最终真正 answer-bearing chunk 没进入 EvidencePacket。RRF 因此改善了平均可达性，但不具备语义判别能力，也不能保证单路正确候选一定压过双路错误共识。

### 可能改进

- 为 q28 一类题继续记录 Dense / BM25 / RRF 的 candidate rank 与融合贡献；
- 对 entity / exact-term / mechanism 问题尝试更有约束的 query expansion；
- 比较更大的候选池与可选 reranker，但保持 strict evidence gate 独立；
- 将 answer-bearing reachability 继续作为独立回归信号，而不是只看母文档 Full@K。

## 2. 二轮检索已经能恢复，但稳定性仍不足

Hybrid `orchestrated` 在应回答的一轮不足题中：

```text
q17 → recovery
q27 → recovery
q28 → refuse
q30 → refuse
```

因此当前应回答题的二轮 recovery 为 2/4。q17、q27 证明 bounded rewrite + R2 已能真实恢复部分证据缺口；q28 仍是检索问题。q30 首轮已经有较直接 KV Cache 证据，却仍被 structured judge 连续判为不足，更接近 sufficiency calibration / provider variation 的 false negative。

后续若继续优化，应优先区分“真正缺证据”和“Judge 要求过严”，而不是简单增加循环次数。

## 3. 两个 profile 仍是明确取舍

| 维度 | baseline | orchestrated |
| :-- | :-- | :-- |
| 应回答题覆盖 | 29/29 | 27/29 |
| 证据控制 | 更宽松 | 严格、结构化 |
| 在线 Token | 123,627 | 190,941 |
| 在线估算成本 | $0.036531 | $0.073633 |

当前没有单一 profile 同时实现最高覆盖、最严格证据边界、最低成本和稳定恢复。两者仍是场景选择，而不是简单的低配 / 高配关系。

## 4. B2 只能证明同域回归稳定性

B2 只有 30 题，且与冻结私有语料高度同域。它能够验证：

- 冻结语料与配置下的行为稳定性；
- 关键控制、证据路径和成本可复核；
- Splitter 修正、Hybrid Retriever 与双 profile 差异。

它不能单独证明：

- 未知领域上的准确率；
- 真实业务效果；
- orchestrated 在所有质量维度普遍更优；
- 生产级质量或稳定性。

后续需要独立 held-out、域外、多跳、冲突、否定和真实攻击题集。

## 5. 评测信号仍有边界

- q06、q27 的机器 expected-evidence gate 与人工 precise-evidence 诊断未完全对齐；本轮没有把专项人工标注悄悄升级为正式 gate；
- q21 baseline 出现单题 citation-validity fail，应作为引用层独立回归点保留；
- q30 暴露 structured sufficiency 的过严 / provider 波动风险；
- 回答质量分档尚未按 exact answer SHA 导入统一 release gate；
- Citation Support 主要是字符/词面规则，语义蕴含能力有限；
- Conflict 缺少独立 gold set，最终 0 conflicts 只表示规则未触发；
- RAGAS 依赖 LLM judge，受模型版本、随机性和 provider 波动影响；
- 成本来自静态价格表估算，不等同于实际账单。

## 6. 当前仍是本地参考实现

- `LocalVectorStore` 使用本地文件与内存 O(N) 点积；
- Hybrid BM25 复用当前 chunk 集并在进程内构建，不是面向大规模语料的生产 sparse index；
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
