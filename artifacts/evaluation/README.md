# Evaluation Artifacts

这里保存公开仓库中精选的人读评测证据。

运行时生成的 raw CER、raw evidence、完整日志和私有语料不进入这里。当前正式 Retriever 为 `Dense Top10 + BM25 Top10 → RRF(k=60) → Top5`；`baseline` 与 `orchestrated` 共用同一 Hybrid RRF 检索实现。

## 目录

- `baseline/`：Hybrid RRF baseline 冻结运行的在线、D-full、RAGAS 与总账报告；
- `orchestrated/`：Hybrid RRF orchestrated 对应报告；
- `Baseline-vs-Orchestrated-最终评测对比.md`：当前 Hybrid RRF 下的双 profile 配对对比；
- `Dense-vs-Hybrid-RRF-四组批跑对比报告.md`：Dense-only → Hybrid RRF 的检索变更依据。

## baseline

1. [B2-baseline-01-逐题运行报告-20260903-211834.md](baseline/B2-baseline-01-逐题运行报告-20260903-211834.md)
2. [B2-baseline-02-检索信号摘要-20260903-211834.md](baseline/B2-baseline-02-检索信号摘要-20260903-211834.md)
3. [B2-baseline-03-运行检索来源分布-20260903-211834.md](baseline/B2-baseline-03-运行检索来源分布-20260903-211834.md)
4. [B2-baseline-04-检索工作流明细-20260903-211834.md](baseline/B2-baseline-04-检索工作流明细-20260903-211834.md)
5. [B2-baseline-05-Timing-Usage-Cost明细-20260903-211834.md](baseline/B2-baseline-05-Timing-Usage-Cost明细-20260903-211834.md)
6. [D-full-baseline-离线评测总览.md](baseline/D-full-baseline-离线评测总览.md)
7. [D-full-baseline-逐题评测报告.md](baseline/D-full-baseline-逐题评测报告.md)
8. [D-full-baseline-Timing-Usage-Cost明细.md](baseline/D-full-baseline-Timing-Usage-Cost明细.md)
9. [RAGAS-baseline-评测结果.md](baseline/RAGAS-baseline-评测结果.md)
10. [RAGAS-baseline-Timing-Usage-Cost明细.md](baseline/RAGAS-baseline-Timing-Usage-Cost明细.md)
11. [Evaluation-baseline-Timing-Usage-Cost总账.md](baseline/Evaluation-baseline-Timing-Usage-Cost总账.md)

## orchestrated

1. [B2-orchestrated-01-逐题运行报告-20260903-212201.md](orchestrated/B2-orchestrated-01-逐题运行报告-20260903-212201.md)
2. [B2-orchestrated-02-检索信号摘要-20260903-212201.md](orchestrated/B2-orchestrated-02-检索信号摘要-20260903-212201.md)
3. [B2-orchestrated-03-运行检索来源分布-20260903-212201.md](orchestrated/B2-orchestrated-03-运行检索来源分布-20260903-212201.md)
4. [B2-orchestrated-04-检索工作流明细-20260903-212201.md](orchestrated/B2-orchestrated-04-检索工作流明细-20260903-212201.md)
5. [B2-orchestrated-05-Timing-Usage-Cost明细-20260903-212201.md](orchestrated/B2-orchestrated-05-Timing-Usage-Cost明细-20260903-212201.md)
6. [D-full-orchestrated-离线评测总览.md](orchestrated/D-full-orchestrated-离线评测总览.md)
7. [D-full-orchestrated-逐题评测报告.md](orchestrated/D-full-orchestrated-逐题评测报告.md)
8. [D-full-orchestrated-Timing-Usage-Cost明细.md](orchestrated/D-full-orchestrated-Timing-Usage-Cost明细.md)
9. [RAGAS-orchestrated-评测结果.md](orchestrated/RAGAS-orchestrated-评测结果.md)
10. [RAGAS-orchestrated-Timing-Usage-Cost明细.md](orchestrated/RAGAS-orchestrated-Timing-Usage-Cost明细.md)
11. [Evaluation-orchestrated-Timing-Usage-Cost总账.md](orchestrated/Evaluation-orchestrated-Timing-Usage-Cost总账.md)

## Cross-profile / Retriever change

- [Baseline-vs-Orchestrated-最终评测对比.md](Baseline-vs-Orchestrated-最终评测对比.md)
- [Dense-vs-Hybrid-RRF-四组批跑对比报告.md](Dense-vs-Hybrid-RRF-四组批跑对比报告.md)
