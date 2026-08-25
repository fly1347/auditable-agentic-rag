# 模型选型与推理部署演进

## 1. 文档定位与时间边界

本文记录项目从“本地模型优先”逐步收束到“本地知识底座 + 受控云端推理”的真实工程决策过程，重点回答：为什么最初选择本地模型，为什么后来没有把“零 API 费用”继续作为默认生成链，generator、sufficiency judge 和 RAGAS evaluator 为什么采用不同模型，以及自部署路线在什么条件下仍然成立。

主要实验发生在 **2026 年 3—5 月**，其中 Phase C+ 的正式模型横评集中在 **2026 年 5 月**。当时使用的是后续已经继续演进的 D-lite / Phase C 旧链路、当时的 Prompt 和证据装配方式，以及 Win11 + WSL2 + Intel Arc 140V 的本地硬件环境。因此，本文中的模型版本、延迟、价格和平台行为都是**历史工程快照**，用于说明选型方法和决策依据，不作为当前通用模型排行榜。

对应的精简实验数字见 [模型选型证据摘要](../artifacts/evaluation/model-selection-evidence.md)。

2026 年 8 月 Phase F 复盘重新检查了 C+ 的模型角色、市场变化和证据链问题，没有重开已经冻结的主链模型决策。公开仓库进一步关闭默认 fallback，以保持模型身份、失败原因、成本和评测结果可解释。

## 2. 起点：为什么一开始坚持本地模型

项目早期 generator 使用 `qwen2.5:7b` via Ollama。这个选择符合最初的“本地优先”目标：

- 语料和 Prompt 尽量不离开本机；
- 不产生按次 API 账单；
- 模型、运行时和版本由本地控制；
- 断网后仍能完成基本问答；
- 能直接理解 GGUF、Ollama、llama.cpp、显存、量化和推理后端这些部署问题。

这一阶段证明了 7B 本地模型可以承担基础生成，也逐步暴露出三个不同层面的约束：**生成速度、判别任务能力、评估框架兼容性**。随着这些边界被量化，本地优先的含义也随之收束：知识资产、本地索引和执行事实优先保留在本机，推理位置则按能力、成本和数据边界选择。

## 3. 第一轮边界：本地 7B 能生成，但不适合承担所有模型角色

### 3.1 RAGAS：结构化评估输出成为能力门槛

Phase A' 尝试使用本地 `qwen2.5:7b` 跑 RAGAS。调试过程先后遇到并发 timeout、Ragas/Ollama wrapper 兼容、长时间运行和结构化输出解析问题。

在 Ragas 0.4.x 路线上，Instructor 风格的结构化输出与当时 Ollama `/v1` 路径无法稳定配合；降级到旧版本并把 timeout 拉长后，问题又落到模型输出格式本身。一次三指标全量运行持续约 **206 分钟**，最终仍出现 `RagasOutputParserException`。其中 faithfulness 只有 3/9 题得到有效值，多题失败于 NLI 结构化输出解析。

这次实验确认了一个独立的工程门槛：**评估模型需要稳定的结构化判别和格式遵循能力。** Generator 能完成问答，只能证明生成角色可用；Evaluator 仍需单独验证。

### 3.2 Sufficiency Judge：生成与判别需要分开验证

D-lite 初次把本地 7B 用作 evidence sufficiency 判别时，30 题回归出现 **8 个 SUFFICIENT → INSUFFICIENT 的假拒答**。继续改 Prompt 在小集上能变好，但全量结果高方差，无法形成稳定解。

项目因此停止继续用 Prompt 搜索弥补本地 7B 判别能力，转而将 DeepSeek 接入 sufficiency judge。后续在修正 Judge 实际可见证据范围后，误伤从 8 题降到 2 题；C+ 再次固定输入对比时，`deepseek-v4-flash non-thinking` 为 30/30，GPT-4o-mini 为 29/30，后者在 q15 出现 false insufficient。

这一步形成了后续一直保留的原则：**模型按角色选，generator、Judge 和离线 evaluator 分别验证。**

## 4. Phase C+：把模型选择从印象判断变成专项工程测试

Phase C 完成服务化后，项目已经不缺“能调用一个模型”的能力，真正缺的是稳定回答以下问题：

```text
这个模型适合生成、判别还是评估？
公开 benchmark 与当前 RAG 任务有什么关系？
本地模型慢在哪里，是 pipeline 慢还是 inference 慢？
GPU backend 对 generation 能带来多大真实收益？
API 的 token 费用和本地 / 云 GPU 的时间成本如何比较？
模型升级、alias 路由和 evaluator 漂移如何进入可观测体系？
```

因此单独增加 Phase C+，建立了以下工作流：

```text
模型情报与 benchmark 阅读
→ 项目任务映射
→ 候选决策卡
→ 本地 GPU / 推理后端验证
→ C+5 固定题集横评
→ 人工答案标注
→ 双 evaluator RAGAS 对照
→ latency / token / cost 拆账
→ D-full 模型角色决策
```

C+ 的决策证据优先级最终收束为：

```text
人工标注
> 项目内真实行为
> 双 evaluator 一致性
> 单 evaluator 分数
> 公开 benchmark
```

公开榜单用于筛候选，项目自己的固定题集和证据链行为负责做最终选择。

## 5. 本地推理专项：零 API 账单下的时间与维护成本

### 5.1 qwen2.5:7b / Ollama 的真实瓶颈

C+ Step 8 在当前服务链上固定运行 5 题，结果为：

| 指标 | 结果 |
| :-- | --: |
| avg generation | 57.14 s |
| avg total | 65.62 s |
| 单题 total 范围 | 43.80–80.89 s |
| avg retrieval | 167.86 ms |
| avg sufficiency judge | 697.58 ms |

瓶颈非常明确：retrieval 是毫秒级，DeepSeek Judge 约 0.6–0.8 秒，主要等待都发生在 Ollama generator。硬件观察中 CPU 高占用，而 Intel Arc 140V 没有形成稳定有效的推理占用。

后续 C+5 正式 12 题 run 中，`qwen2.5:7b` 的平均总耗时仍为 **51.57 s**。它没有 API 账单，但持续消耗开发等待时间和本地计算资源。

### 5.2 Intel Arc 140V + llama.cpp SYCL：从可运行到主链候选仍需性能证据

项目随后直接验证 GPU 后端：完成 oneAPI + llama.cpp SYCL 构建和 smoke test。Arc 140V 能被 runtime 识别，llama.cpp SYCL 可以正常推理。

但在 0.5B Q4 benchmark 中：

```text
SYCL tg128 ≈ 38.45 tokens/s
CPU  tg128 ≈ 71.56 tokens/s
```

SYCL 显著改善 prompt processing，却没有改善 generation。后续 9B 级实验同样没有得到“GPU offload 能稳定提升生成速度”的证据。因此 Arc 140V 被保留为本地能力验证和研究记录，没有进入默认在线链。

### 5.3 本地候选继续筛选

`llama3.1:8b` via Ollama 能运行，但 3 题 smoke 的平均 generation 约 **98.7 s**，比 qwen2.5 更慢，因此退出候选。

后续 `Qwen3.5-9B-Q4_K_M` 通过 llama.cpp server + OpenAI-compatible endpoint 完成正式 12 题横评：

| 指标 | Qwen2.5-7B | Qwen3.5-9B local |
| :-- | --: | --: |
| Prompt-aware 人工分档 | A5 / B4 / C3 / D0 | A7 / B3 / C2 / D0 |
| avg generation | 45.28 s | 25.95 s |
| avg total | 51.57 s | 30.59 s |

Qwen3.5 在本地质量和速度上都优于 qwen2.5，证明本地路线仍有价值；但它的平均总耗时仍约为 GPT-4o-mini 的 **4.25 倍**。因此它被定位为 preferred local fallback / local capability demo，而没有成为默认在线 generator。

## 6. 云端 Generator 横评：为什么最终选择 GPT-4o-mini

C+5 使用固定 12 题小评测集，并固定 retrieval、embedding、sufficiency judge 和最小 Prompt，只切换 generator / query rewrite 模型。2026 年 8 月复盘时进一步核对了 **Prompt 实际可见证据**：早期人工标注没有完整区分“retrieval 已命中”与“最终 Prompt 真正可见”，因此 q10、q19、q22 等题的质量判断需要重标。

新的分档把答案质量和 grounding 一起看：核心证据未进入 Prompt 或基本被截断时，能够识别证据不足并拒答 / 保守回答记为 A；继续依赖参数知识作答则降到 C。q27 则属于“核心证据未进 Prompt、但辅助证据还能支撑部分方向”的边界样本，能答出主方向记为 B。

> 分档顺序统一为 A / B / C / D。

| generator         | Prompt-aware 人工分档 | avg total | 项目角色结论                          |
| :---------------- | :-------------------- | --------: | :------------------------------------ |
| qwen2.5:7b        | 5 / 4 / 3 / 0         | 51.57 s   | legacy local baseline                 |
| Qwen3.5-9B local  | 7 / 3 / 2 / 0         | 30.59 s   | preferred local fallback              |
| DeepSeek V4 Flash | 7 / 3 / 2 / 0         | 9.60 s    | sufficiency judge                     |
| GPT-4o-mini       | 5 / 4 / 3 / 0         | 7.19 s    | default cloud generator               |
| DeepSeek V4 Pro   | 6 / 3 / 3 / 0         | 23.09 s   | 不进入默认生成链                      |
| GPT-5.5           | 3 / 3 / 0 / 0（6题）  | 12.85 s   | quality ceiling / difficult-case reviewer |

这次重判改变了对“模型质量领先”的解释：**GPT-4o-mini 并不是这组 Prompt-aware 分档中的最高分模型。** DeepSeek V4 Flash 和 Qwen3.5-9B 在证据边界上都更稳；GPT-4o-mini 的 q10、q19、q22 则暴露出核心证据不可见时仍继续作答的倾向。

GPT-4o-mini 继续作为默认 cloud generator，依据的是整体工程取舍，而不是单一答案分档：

- 正式横评平均总耗时约 **7.19 s**，是本轮完整 12 题候选中最快的云端 generator；
- 输出较轻、格式稳定，适合反复开发、回归和演示；
- token 与 API 成本可控，OpenAI-compatible 接入成熟；
- 在 q26、q27 这类“有部分证据、仍可回答主方向”的题上，比更保守的 DeepSeek 更愿意完成回答；
- 更严格的证据边界交给 DeepSeek sufficiency judge，而不是要求 generator 同时承担回答生成与证据裁决两个目标。

因此最终方案本质上是**角色拆分**：DeepSeek Flash 负责在生成前把证据不足问题尽量拦住，GPT-4o-mini 负责在已经通过 sufficiency gate 的证据上生成轻量、稳定的用户答案。q10、q19、q22 的复盘也说明这种拆分为什么必要，并进一步推动后续系统把 Prompt-visible evidence、citation support、sufficiency 和 CER 审计纳入统一事实链。

## 7. DeepSeek：为什么适合 Judge / Evaluator，却没有成为默认 Generator

DeepSeek 是项目较早采用的云端候选，主要考虑低成本、接入便利以及判别类任务表现。后续实验把它的角色逐步拆开。

### 7.1 作为 Generator

按 2026 年 8 月 Prompt-aware 重判，DeepSeek V4 Flash 为 A7 / B3 / C2，V4 Pro 为 A6 / B3 / C3。Flash 在 q10、q19、q22 等证据边界题上更能识别 Prompt 内证据不足；Pro 更慢，并带来更高的 reasoning / output token 成本，却没有形成足以覆盖成本的质量优势。

DeepSeek 因此被保留在更适合它的控制角色。当前知识库问答同时关注证据边界、回答覆盖率、交互延迟和开发成本；偏严格的模型在 sufficiency 控制节点上更有价值，用户答案则交给综合表现更均衡的 generator。

### 7.2 作为 Sufficiency Judge

固定 30 题 Judge 替换实验中：

```text
deepseek-v4-flash non-thinking：30/30
GPT-4o-mini：29/30，q15 false insufficient
```

DeepSeek Flash 在这一角色上速度更快、成本更低，并且判别行为更符合当前证据控制需求，所以继续承担在线 sufficiency judge。

### 7.3 作为 RAGAS Evaluator

RAGAS 对照实验进一步发现，同一批答案在 DeepSeek 和 GPT-4o-mini evaluator 下的 faithfulness / answer_relevancy 差异明显。项目因此将 RAGAS 定位为辅助评估，并把人工标注与项目内行为放在更高优先级。

### 7.4 模型 alias 与版本漂移也是工程变量

早期使用 `deepseek-chat` 时，项目观察到 provider 后端模型升级后 sufficiency 行为发生变化；同一时期还遇到过 API availability incident。这个经历直接推动了后续 ModelIdentity / CER 记录：

```text
configured_model
provider_response_model
resolved_model
endpoint
usage / latency / cost
```

模型身份需要按运行事实记录。provider alias、版本升级、thinking / non-thinking 模式和服务状态都可能改变评测结果，因此这些字段进入 CER 与重新选型条件。

## 8. API、自部署与云 GPU：为什么最终没有为了“省 API 钱”强行自托管

C+ 同时整理了 VRAM、量化、KV cache、推理栈、云 GPU 和利用率成本。核心判断是：

```text
API 按 token 付费；
GPU 自部署按时间、容量和运维付费。
```

云 GPU 单题成本需要把 hourly price 与以下因素一起计算：

```text
GPU 时租 × 单题推理时间
+ 空转
+ 并发 / batch 利用率
+ KV cache / 上下文显存
+ 存储与出向流量
+ 部署、监控和升级维护
```

对于个人项目、小团队 PoC 和低频知识库问答，只要数据允许出境，API 通常比长期占用 GPU 更经济，也更容易获得稳定的高质量模型能力。当前机器上的本地 7B/9B 又已经实测出明显延迟差距，所以继续为了“零 API 账单”强行本地化，反而会放大时间成本和维护成本。

自部署仍然有清晰成立条件：**当业务数据必须留在企业边界内时，自部署首先解决合规与数据边界，随后再优化成本。** 此时应重新评估企业 GPU、VPC / 专有云、vLLM / SGLang、量化、并发和利用率，并采用面向生产负载的推理服务方案。

## 9. “本地优先”的最终含义

经过这些实验，本项目的本地优先最终收束为：

```text
本地：语料、ACL、Embedding、索引、CER、日志与评测产物
云端：按角色选择 generator / judge / evaluator
控制：每次外发经过 Principal、egress policy、budget 与模型身份记录
```

最终形成的是一条分层部署路线：数据资产保持本地，需要更强模型能力的节点允许受控外发；受限数据场景启用经过独立评测的本地 / 私有化模型 profile。

Phase C+ 曾保留 Qwen3.5-9B 作为 preferred local fallback；Phase G 公开默认进一步将 `fallback_chain` 设为空，并移除 Ollama 专用公开 Compose。原因是公开 Quickstart 更强调结果可解释和配置收束：一次运行使用哪个模型、为什么失败、花了多少成本都保持明确。本地 provider 兼容能力可以存在，但不再静默进入公开默认链。

## 10. 最终角色分工

Phase C+ / D-full 收口时的模型角色为：

| 角色 | 决策 | 理由 |
| :-- | :-- | :-- |
| 默认 generator | `openai/gpt-4o-mini` | 质量、延迟、成本和可用性最均衡 |
| sufficiency judge | `deepseek-v4-flash` non-thinking | 固定判别集表现更稳，延迟和成本适合在线控制 |
| RAGAS evaluator | DeepSeek Flash 为主，GPT-4o-mini 做过对照 | evaluator 存在方差，不由单一分数决定结论 |
| preferred local fallback | Qwen3.5-9B GGUF / llama.cpp | 本地质量与速度均优于旧 qwen2.5 baseline |
| legacy local baseline | qwen2.5:7b / Ollama | 可运行、零 API 账单，但时间成本高 |
| quality reference | GPT-5.5 | 复杂题质量上限参考，不承担默认在线成本 |

公开 Phase G 当前默认只暴露云端 generator / judge，fallback 关闭。上表用于记录选型历史和重新选型依据。

## 11. 这轮模型工作的可复用经验

1. **先定义角色，再选模型。** Generator、Judge、Evaluator 的目标函数不同。
2. **公开 benchmark 用来初筛，项目内固定题集负责决策。** 最终结论回到真实 Prompt、证据、答案和延迟测试。
3. **“免费本地模型”仍有时间与运维成本。** API 账单为零不代表工程成本为零。
4. **跑通 GPU backend 只是可行性证据。** 是否进入主链还要看真实 generation、稳定性和维护复杂度。
5. **答案正确和 grounding 正确分开评价。** 强模型在证据不足时也可能答对，retrieval / prompt 仍需独立审计。
6. **评估模型同样需要评估。** LLM-as-a-judge 会受版本、提示、同模型偏置和 provider 漂移影响。
7. **模型身份必须进入运行事实。** alias、版本、thinking 模式和 endpoint 都会改变系统行为。
8. **自部署首先由数据边界和利用率决定。** 低频场景 API 常更经济；受限数据场景则必须重新评估私有推理。

## 12. 重新选型条件

出现以下情况时，应重新进行模型 benchmark，2026 年 5 月结果只保留为历史对照：

- generator / judge 已有新一代模型，价格或延迟发生明显变化；
- provider alias、thinking 模式或 API 合同变化；
- Prompt、retrieval、证据数量或工作流发生结构性变化；
- 本地硬件或推理栈升级，能够提供新的吞吐证据；
- 数据必须留在受控边界内，需要启用完全本地或 VPC 私有推理；
- 调用量上升到 GPU 长期高利用率，自部署经济性发生反转；
- 任务从中文知识库 QA 扩展到多模态、工具调用或长时程 Agent；
- RAGAS / Judge 版本升级导致评估口径变化。

重新选型时继续沿用 C+ 的方法：**固定共同输入、区分模型角色、记录模型身份与 usage、做人工逐题检查、把质量/延迟/成本/部署约束放在同一张决策表里。**
