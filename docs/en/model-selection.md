# Model Selection and Inference Deployment Evolution

## 1. Purpose and Time Boundary

This document records the project’s actual engineering path from a “local-model-first” starting point toward a “local knowledge foundation + controlled cloud inference” design. It focuses on five questions: why local models were chosen initially, why zero API spend did not remain the default generation strategy, why the generator, sufficiency judge, and RAGAS evaluator use different models, and under what conditions self-hosting still makes sense.

Most experiments took place between **March and May 2026**, with the formal Phase C+ model comparison concentrated in **May 2026**. At that time the project was still running an earlier D-lite / Phase C pipeline, older prompts and evidence assembly, and a local Win11 + WSL2 + Intel Arc 140V environment. Model versions, latency, prices, and platform behavior in this document are therefore **historical engineering snapshots**. They explain the selection method and decision basis rather than serving as a current general model leaderboard.

Condensed experiment figures are included in the comparison tables below.

The August 2026 Phase F review revisited the C+ model roles, market changes, and evidence-chain issues without reopening the frozen mainline model decision. The public repository additionally disables default fallback so that model identity, failure causes, cost, and evaluation results remain explainable.

## 2. Starting Point: Why Local Models Came First

The early generator was `qwen2.5:7b` via Ollama. This matched the original local-first objective:

- keep corpus content and prompts on the machine where possible;
- avoid per-call API charges;
- retain local control of model, runtime, and version;
- support basic QA without network access;
- gain direct experience with GGUF, Ollama, llama.cpp, VRAM, quantization, and inference backends.

This stage showed that a local 7B model can handle baseline answer generation, while also exposing three distinct constraints: **generation speed, discriminative-task capability, and evaluation-framework compatibility**. Once those boundaries were measured, “local-first” became more precise: knowledge assets, the local index, and execution facts stay local by default, while inference location is selected according to capability, cost, and data boundary.

## 3. First Boundary: A Local 7B Model Can Generate, but Should Not Fill Every Model Role

### 3.1 RAGAS: Structured Evaluation Output Became a Capability Gate

Phase A' attempted to run RAGAS with local `qwen2.5:7b`. Debugging encountered concurrency timeouts, Ragas/Ollama wrapper compatibility issues, long runtimes, and structured-output parsing failures.

On the Ragas 0.4.x path, Instructor-style structured output did not work reliably with the then-current Ollama `/v1` path. After downgrading and extending timeouts, the remaining failure moved to the model output format itself. One full three-metric run lasted about **206 minutes** and still ended with `RagasOutputParserException`. Faithfulness produced valid values for only 3 of 9 questions, while several cases failed during parsing of structured NLI output.

This experiment established an independent engineering gate: **an evaluation model must provide stable structured judgment and format compliance.** A model being usable as a generator does not imply that it is suitable as an evaluator.

### 3.2 Sufficiency Judge: Generation and Discrimination Must Be Evaluated Separately

When D-lite first used the local 7B model for evidence-sufficiency judgment, the 30-question regression run produced **eight false SUFFICIENT → INSUFFICIENT rejections**. Prompt tuning improved small subsets, but full-run variance remained too high to produce a stable solution.

The project therefore stopped using prompt search to compensate for the local 7B model’s judgment limitations and switched the sufficiency judge to DeepSeek. After correcting the judge’s actual visible-evidence scope, false rejections fell from eight questions to two. In a later C+ fixed-input comparison, `deepseek-v4-flash non-thinking` reached 30/30, while GPT-4o-mini reached 29/30 and produced a false insufficient result on q15.

This became a durable design principle: **select models by role; validate generator, judge, and offline evaluator independently.**

## 4. Phase C+: Turning Model Selection from Intuition into an Engineering Test

After Phase C service integration, the project no longer lacked the ability to “call a model.” The real need was to answer the following questions consistently:

```text
Is this model better suited to generation, judgment, or evaluation?
How do public benchmarks relate to this RAG workload?
Where is local inference slow: the pipeline or model generation?
How much real generation speedup does a GPU backend provide?
How do API token cost and local/cloud GPU time cost compare?
How should model upgrades, alias routing, and evaluator drift enter observability?
```

Phase C+ was therefore added as a dedicated engineering stage with the following workflow:

```text
Model intelligence and benchmark reading
→ Task mapping for this project
→ Candidate decision cards
→ Local GPU / inference-backend validation
→ Fixed C+5 benchmark set
→ Manual answer annotation
→ Dual-evaluator RAGAS comparison
→ Latency / token / cost breakdown
→ D-full model-role decision
```

The final evidence priority for C+ was:

```text
Manual annotation
> Actual project behavior
> Agreement between two evaluators
> Single-evaluator scores
> Public benchmarks
```

Public leaderboards filter candidates; the project’s own fixed inputs and evidence-chain behavior determine the final decision.

## 5. Local Inference: Time and Maintenance Cost Behind a Zero-API Bill

### 5.1 Real Bottleneck of qwen2.5:7b / Ollama

C+ Step 8 ran five fixed questions through the current service path:

| Metric | Result |
| :-- | --: |
| avg generation | 57.14 s |
| avg total | 65.62 s |
| per-question total range | 43.80–80.89 s |
| avg retrieval | 167.86 ms |
| avg sufficiency judge | 697.58 ms |

The bottleneck was clear: retrieval was millisecond-scale, the DeepSeek judge took roughly 0.6–0.8 seconds, and most waiting occurred in the Ollama generator. Hardware observation showed high CPU use while Intel Arc 140V did not sustain useful inference utilization.

In the later formal 12-question C+5 run, `qwen2.5:7b` still averaged **51.57 s** total. It incurred no API bill, but consumed substantial developer waiting time and local compute resources.

### 5.2 Intel Arc 140V + llama.cpp SYCL: “Runs on GPU” Was Not Enough

The project then validated the GPU backend directly: oneAPI + llama.cpp SYCL was built and smoke-tested. Arc 140V was detected by the runtime and llama.cpp SYCL could generate normally.

However, the 0.5B Q4 benchmark showed:

```text
SYCL tg128 ≈ 38.45 tokens/s
CPU  tg128 ≈ 71.56 tokens/s
```

SYCL materially improved prompt processing but did not improve generation. Later 9B-scale experiments likewise did not provide evidence that GPU offload could consistently improve generation speed. Arc 140V therefore remained a local capability-validation and research path rather than entering the default online pipeline.

### 5.3 Continuing to Filter Local Candidates

`llama3.1:8b` via Ollama ran successfully, but a three-question smoke test averaged about **98.7 s** generation time, slower than qwen2.5, so it was dropped.

Later, `Qwen3.5-9B-Q4_K_M` completed the formal 12-question benchmark through a llama.cpp server with an OpenAI-compatible endpoint:

| Metric | Qwen2.5-7B | Qwen3.5-9B local |
| :-- | --: | --: |
| Prompt-aware manual grades | A5 / B4 / C3 / D0 | A7 / B3 / C2 / D0 |
| avg generation | 45.28 s | 25.95 s |
| avg total | 51.57 s | 30.59 s |

Qwen3.5 improved both local quality and speed over qwen2.5, proving that the local path remained meaningful. Its average total latency was still about **4.25×** GPT-4o-mini, so it was positioned as preferred local fallback / local capability evidence instead of becoming the default online generator.

## 6. Cloud Generator Comparison: Why GPT-4o-mini Became the Default

C+5 used a fixed 12-question mini-evaluation set while holding retrieval, embedding, sufficiency judge, and the minimal prompt constant; only the generator / query-rewrite model changed. The August 2026 review further verified **evidence actually visible in the prompt**. Early human annotation had not fully distinguished “retrieval hit” from “actually visible in the final prompt,” so cases including q10, q19, and q22 required regrading.

The revised grading considers answer quality and grounding together. If the core evidence never enters the prompt or is effectively truncated, detecting insufficiency and refusing / answering conservatively receives an A; continuing from parametric knowledge is downgraded to C. q27 is a boundary case where the core evidence is absent from the prompt but supporting evidence still points in the correct direction, so an answer capturing the main direction receives a B.

> Grade order is consistently A / B / C / D.

| generator | Prompt-aware manual grades | avg total | Project role conclusion |
| :-- | :-- | --: | :-- |
| qwen2.5:7b | 5 / 4 / 3 / 0 | 51.57 s | legacy local baseline |
| Qwen3.5-9B local | 7 / 3 / 2 / 0 | 30.59 s | preferred local fallback |
| DeepSeek V4 Flash | 7 / 3 / 2 / 0 | 9.60 s | sufficiency judge |
| GPT-4o-mini | 5 / 4 / 3 / 0 | 7.19 s | default cloud generator |
| DeepSeek V4 Pro | 6 / 3 / 3 / 0 | 23.09 s | excluded from the default generation path |
| GPT-5.5 | 3 / 3 / 0 / 0 (6 questions) | 12.85 s | quality ceiling / difficult-case reviewer |

The regrading changed the interpretation of “model quality leadership”: **GPT-4o-mini is not the highest-scoring model under this Prompt-aware grading.** DeepSeek V4 Flash and Qwen3.5-9B are more conservative at evidence boundaries, while GPT-4o-mini on q10, q19, and q22 shows a stronger tendency to continue answering when the core evidence is not visible.

GPT-4o-mini remains the default cloud generator because of the overall engineering trade-off rather than a single answer-quality grade:

- formal benchmark average total latency is about **7.19 s**, the fastest cloud generator among candidates that completed the full 12-question run;
- output is relatively lightweight and format-stable, which suits repeated development, regression, and demos;
- token and API cost remain manageable, and OpenAI-compatible integration is mature;
- on q26 and q27, where partial evidence still supports the main direction, it is more willing than conservative DeepSeek variants to complete the answer;
- stricter evidence-boundary decisions are delegated to the DeepSeek sufficiency judge rather than forcing one generator to optimize for both answer generation and evidence adjudication.

The final design is therefore a **role split**: DeepSeek Flash blocks evidence-insufficient cases before generation, while GPT-4o-mini produces lightweight and stable user-facing answers after the sufficiency gate has passed. The q10/q19/q22 review also demonstrates why this split matters and helped drive the later integration of Prompt-visible evidence, citation support, sufficiency, and CER auditing into one factual chain.

## 7. DeepSeek: Why It Fits Judge / Evaluator Roles Better Than the Default Generator Role

DeepSeek was an early cloud candidate because of low cost, convenient integration, and strong behavior on judgment-style tasks. Later experiments separated its roles more clearly.

### 7.1 As Generator

Under the August 2026 Prompt-aware regrading, DeepSeek V4 Flash scores A7 / B3 / C2 and V4 Pro A6 / B3 / C3. Flash is more likely to recognize insufficient in-prompt evidence on boundary cases such as q10, q19, and q22. Pro is slower and incurs higher reasoning/output token cost without producing enough quality improvement to justify that cost.

DeepSeek therefore remains in the control roles that better fit its behavior. This knowledge-base QA workload simultaneously values evidence boundaries, answer coverage, interaction latency, and development cost. A conservative model provides more value at the sufficiency-control node, while user-facing answers are delegated to a more balanced generator.

### 7.2 As Sufficiency Judge

In the fixed 30-question judge replacement experiment:

```text
deepseek-v4-flash non-thinking: 30/30
GPT-4o-mini: 29/30, q15 false insufficient
```

DeepSeek Flash was faster and cheaper in this role and aligned better with the current evidence-control requirement, so it remains the online sufficiency judge.

### 7.3 As RAGAS Evaluator

RAGAS comparison also showed material differences in faithfulness / answer_relevancy when the same answers were evaluated by DeepSeek and GPT-4o-mini. The project therefore treats RAGAS as an auxiliary signal and gives higher priority to manual annotation and actual project behavior.

### 7.4 Model Aliases and Version Drift Are Engineering Variables

During early use of `deepseek-chat`, the project observed sufficiency behavior change after provider-side model upgrades; it also encountered an API availability incident in the same period. That experience directly motivated later ModelIdentity / CER fields:

```text
configured_model
provider_response_model
resolved_model
endpoint
usage / latency / cost
```

Model identity must be captured as runtime fact. Provider aliases, version upgrades, thinking / non-thinking mode, and service state can all change evaluation results, so these fields are recorded in CER and are part of the conditions that trigger re-selection.

## 8. API, Self-Hosting, and Cloud GPU: Why “Saving API Cost” Did Not Justify Forced Self-Hosting

C+ also analyzed VRAM, quantization, KV cache, inference stacks, cloud GPU pricing, and utilization economics. The central distinction is:

```text
API: pay per token;
Self-hosted GPU: pay for time, capacity, and operations.
```

Cloud-GPU per-question cost must combine hourly price with:

```text
GPU hourly rate × per-question inference time
+ idle time
+ concurrency / batch utilization
+ KV cache / context VRAM
+ storage and egress traffic
+ deployment, monitoring, and upgrade maintenance
```

For personal projects, small-team PoCs, and low-frequency knowledge-base QA, APIs are usually more economical than holding GPU capacity whenever data is allowed to leave the local boundary, and they provide stable access to stronger models. Local 7B/9B experiments on the current hardware already showed a clear latency gap, so forcing local inference purely to reach a “zero API bill” would amplify time and maintenance cost.

Self-hosting still has a clear validity condition: **when business data must remain inside the enterprise boundary, self-hosting first solves compliance and data-boundary requirements, then cost is optimized.** At that point the system should reevaluate enterprise GPUs, VPC/private-cloud deployment, vLLM/SGLang, quantization, concurrency, utilization, and production-oriented inference serving.

## 9. Final Meaning of “Local-First”

After these experiments, local-first converged to:

```text
Local: corpus, ACL, embedding, index, CER, logs, and evaluation artifacts
Cloud: role-specific generator / judge / evaluator
Control: every egress passes Principal, egress policy, budget, and model-identity recording
```

The resulting deployment pattern is layered: data assets remain local, while nodes that benefit from stronger model capability may use controlled egress; restricted-data scenarios can activate a separately evaluated local/private model profile.

Phase C+ retained Qwen3.5-9B as preferred local fallback. Phase G further sets the public default `fallback_chain` to empty and removes the Ollama-specific public Compose path. The public Quickstart prioritizes explainable execution and configuration convergence: which model handled a run, why a failure occurred, and what it cost remain explicit. Local-provider compatibility may remain in the codebase, but it no longer enters the public default path silently.

## 10. Final Model Roles

At the Phase C+ / D-full convergence point, model roles were:

| Role | Decision | Rationale |
| :-- | :-- | :-- |
| Default generator | `openai/gpt-4o-mini` | Best balance of quality, latency, cost, and availability |
| Sufficiency judge | `deepseek-v4-flash` non-thinking | More stable on the fixed judgment set; latency and cost suit online control |
| RAGAS evaluator | DeepSeek Flash primary, GPT-4o-mini used for comparison | Evaluators exhibit variance; conclusions do not depend on one score |
| Preferred local fallback | Qwen3.5-9B GGUF / llama.cpp | Better local quality and speed than the old qwen2.5 baseline |
| Legacy local baseline | qwen2.5:7b / Ollama | Runnable and zero API billing, but high time cost |
| Quality reference | GPT-5.5 | Difficult-case quality-ceiling reference, not the default online-cost choice |

The current public Phase G default exposes only the cloud generator / judge and keeps fallback disabled. The table records model-selection history and the basis for future re-selection.

## 11. Reusable Lessons from the Model Work

1. **Define the role before selecting the model.** Generator, Judge, and Evaluator optimize different objectives.
2. **Use public benchmarks for screening; use a fixed project dataset for decisions.** Final conclusions return to actual prompts, evidence, answers, and latency measurements.
3. **A “free local model” still has time and operations cost.** Zero API billing does not mean zero engineering cost.
4. **Running a GPU backend proves feasibility, not production suitability.** Mainline adoption still requires evidence from real generation speed, stability, and maintenance complexity.
5. **Separate answer correctness from grounding correctness.** Strong models may answer correctly with insufficient evidence; retrieval and prompt visibility still require independent audit.
6. **Evaluate the evaluator.** LLM-as-a-judge is sensitive to model version, prompt, same-model bias, and provider drift.
7. **Model identity belongs in runtime facts.** Aliases, versions, thinking mode, and endpoint can change system behavior.
8. **Self-hosting is first determined by data boundary and utilization.** APIs are often more economical for low-frequency workloads; restricted-data workloads require a fresh private-inference evaluation.

## 12. Conditions for Re-Selection

Rerun the model benchmark when any of the following occurs. The May 2026 results should remain historical reference only:

- a new generation of generator/judge models materially changes price or latency;
- provider aliases, thinking modes, or API contracts change;
- prompts, retrieval, evidence count, or workflow structure changes materially;
- local hardware or the inference stack improves enough to provide new throughput evidence;
- data must remain inside a controlled boundary, requiring fully local or VPC-private inference;
- request volume rises enough for sustained high GPU utilization to reverse self-hosting economics;
- the workload expands from Chinese knowledge-base QA to multimodal tasks, tool use, or long-horizon agents;
- RAGAS / Judge versions change the evaluation contract.

Future re-selection should continue to follow the C+ method: **freeze shared inputs, separate model roles, record model identity and usage, perform manual per-question review, and place quality, latency, cost, and deployment constraints in the same decision table.**
