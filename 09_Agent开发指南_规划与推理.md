# 第九章：规划与推理——Planning & Reasoning

本章探讨 2026 年 Agent 的规划与推理能力——从 Prompt 工程时代的 CoT/ToT，到推理模型内置的思考能力，再到自适应重规划的生产实践。

## 9.1 引言：从 Prompt 技巧到模型能力

2022-2024 年，让 LLM"思考"靠的是一句咒语：*"Let's think step by step"*。CoT（思维链）、ToT（思维树）、ReAct——这些范式的本质都是**通过 Prompt 工程在外部引导模型的推理路径**。

2026 年，事情变了。o3、o4-mini、Claude Extended Thinking、DeepSeek-R1 将推理过程**内化为模型本身的计算步骤**。你不再需要在 Prompt 里教模型怎么思考——你只需要设置 `reasoning_effort="high"` 和 `max_completion_tokens=16000`，模型自己会分配"思考时间"。

但这不意味着 Prompt 工程范式就过时了。GPT-4o、Gemini Flash、Claude Haiku 仍然是成本最优的选择，它们的推理仍然依赖外部引导。**2026 年的工程实践不是"选一个"，而是"知道什么时候该上哪个"。**

## 9.2 推理的两条路径

### 9.2.1 Prompt 工程范式（CoT / ToT）

**CoT（思维链）**的本质是强制模型在输出答案前产生中间推理步骤。2022 年需要 few-shot 示例，2023 年零样本 `"Let's think step by step"` 即可生效。

核心原理：将"输入→输出"的直接映射拆解为"输入→步骤1→步骤2→...→输出"的序列，激活模型内部的逻辑通路。局限是线性的——一步错了，后面全错。

**ToT（思维树）**将推理建模为树搜索：每一步生成多个候选，评估后选择最优路径，不通则回溯。适用于规划、谜题等需要多路径探索的任务。代价是 Token 消耗极高（BFS 每层都要评估多个候选）。

> 在 2026 年，CoT/ToT 主要用于**非推理模型**（GPT-4o、Gemini Flash、Claude Haiku）上的复杂任务。

### 9.2.2 推理模型范式（o3 / o4-mini）

推理模型在输出答案前进行**内部 CoT**——这些 thinking tokens 对用户可见（取决于模型），消耗额外的计算和 Token，但显著提升准确性。

```python
# 推理模型的正确用法：不写 CoT Prompt，只设置推理预算
from openai import OpenAI
client = OpenAI()

# 轻量推理：日常工程任务
response = client.chat.completions.create(
    model="o4-mini",
    messages=[{"role": "user", "content": "写一个带过期策略的 LRU 缓存"}],
    reasoning_effort="medium"  # low / medium / high
)

# 深度推理：算法设计、数学证明
response = client.chat.completions.create(
    model="o3",
    messages=[{"role": "user", "content": "设计一个支持事务的分布式 KV 存储方案"}],
    reasoning_effort="high",
    max_completion_tokens=32000  # 始终设置上限，防止账单爆炸
)
```

**预算控制**是推理模型的关键工程实践。`max_completion_tokens` 同时限制 thinking tokens 和输出 tokens——不设这个值等于给了一张空白支票。

**Prompt 缓存**在推理模型上的行为不同：thinking tokens 是动态生成的，不会被缓存命中。但 system prompt 中的固定指令依然可以被缓存。

### 9.2.3 何时用哪条路径

| 场景 | 推荐 | 原因 |
|------|------|------|
| 单步复杂推理（算法设计、数学证明） | o3, reasoning_effort=high | 质量是唯一约束 |
| 日常 Agent 规划（拆解任务、编排步骤） | o4-mini, reasoning_effort=medium | 比 o3 快 10x，成本 1/10 |
| Agent 运行时决策（每步选工具） | GPT-4o / Claude Haiku | 延迟敏感，不需要深度推理 |
| 批量简单任务 | GPT-4o-mini / Gemini Flash | 成本优先 |
| 开源/自托管场景 | DeepSeek-R1 / Qwen | 数据隐私 + 成本可控 |

## 9.3 规划架构全景

### 9.3.1 ReAct：边想边做

```
Thought → Action → Observation → Thought → ...
```

每步先推理"现状是什么、下一步该做什么"，然后执行工具调用，根据结果调整。优势是灵活——能根据工具返回动态调整。局限是缺乏全局视野，容易在长链任务中偏离目标，且每步都需要额外的 LLM 调用。

**适用**：5 步以内的交互式任务，查询-检索-回答类场景。

### 9.3.2 Plan-and-Execute：先谋后动

```
Planner（生成完整计划）→ Executor（逐步执行）→ 可选 Replanner（调整后续）
```

将规划与执行解耦。Planner 输出步骤列表和依赖关系，Executor 按列表执行。优势是结构清晰、可并行执行独立步骤。劣势是如果初始规划有误，后续执行全白费——需要重规划能力兜底。

**适用**：步骤明确、可预测的多步骤任务（报告生成、数据处理流水线）。

### 9.3.3 Reflexion：从失败中学习

```
尝试 → 失败 → 生成反思（自然语言分析原因）→ 存入记忆 → 重试（带反思上下文）
```

在 ReAct 基础上增加"口头强化学习"——每次失败后生成一段反思，分析哪里做错了、下次怎么改进。这些反思存入长期记忆，后续任务可检索参考。HumanEval 基准上让 GPT-4 从 80% 提升到 91%，不需要微调。

**适用**：有明确成败信号、允许多次尝试的任务（代码调试、策略搜索）。

### 9.3.4 ReWOO：先规划再并行

```
Planner（生成计划+参数）→ Worker（并行执行所有工具）→ Solver（合成最终答案）
```

ReWOO（Reasoning WithOut Observation）是 Plan-and-Execute 的激进版本——Planner 一次性生成所有步骤的完整参数（不等待任何工具返回），Worker 并行执行所有工具调用，Solver 汇总输出。**比 ReAct 节省 5 倍 Token**，因为不需要每步都重新喂入上下文。

**适用**：工具调用可预测的任务（已知 API 的批量查询、模板化数据流水线）。

### 9.3.5 架构对比速览

| 范式 | 核心思路 | Token 成本 | 全局视野 | 灵活性 | 最佳场景 |
|------|----------|------------|----------|--------|----------|
| ReAct | 边想边做 | 中等 | 弱 | 高 | 交互式任务（<5 步） |
| Plan-Execute | 先谋后动 | 较高 | 强 | 中 | 结构化多步任务 |
| Reflexion | 失败中学习 | 高（重试） | 中 | 高 | 试错迭代型任务 |
| ReWOO | 并行执行 | 低（5x 节省） | 强 | 低 | 可预测的批量任务 |

> **不是选一个，是组合使用。** 生产系统常见模式：全局用 Plan-Execute，局部用 ReAct，失败时用 Reflexion 反思。

## 9.4 2026 核心能力：自适应重规划

### 9.4.1 静态规划为何失败

2025-2026 年的研究（Plan-and-Act、ALAS、SagaLLM）明确了静态规划的四种失败模式：

1. **工具失败**：需要的工具不可用或返回错误——一步失败，后续全阻塞
2. **状态漂移**：环境在规划生成和执行之间发生了变化——计划的前置条件已失效
3. **依赖违反**：前一步的实际输出和预期不符，导致后续步骤的前提不成立
4. **上下文侵蚀**：长链任务中累积的输出溢出上下文窗口——Agent 丢失了对整体计划的感知

Plan-and-Act 的实验数据直接说明了问题：**初始规划在步骤 3-4 时经常已经错误**——动态重规划让 WebArena-Lite 成功率从基线 ReAct 提升了 34 个百分点。

### 9.4.2 范围重规划 vs 全量重规划

全量重规划（从头生成新计划）昂贵且不稳定——可能抛弃已完成的正确步骤。2026 年的共识是**范围重规划（scoped replanning）**：

- Planner 生成计划时同时输出**依赖图**（哪些步骤依赖哪些前序步骤的输出）
- 某步失败时，仅重规划**受影响子树**，保留其余部分
- 只有范围重规划失败（如全局目标已不可达）才升级为全量重规划

成本差异：如果 10 步计划在第 8 步失败，范围重规划只重新生成 2 步，全量重规划重新生成 10 步。

### 9.4.3 四级升级策略

SagaLLM 和 MACI 论文共同指向了一个生产级的升级链：

```
L1: 本地回退（重试 + 替换参数）
  ↓ 失败
L2: 范围重规划（依赖图中的受影响子树）
  ↓ 失败
L3: 全量重规划（从当前状态生成新计划）
  ↓ 失败
L4: 人工介入（通知用户 + 保存检查点）
```

大多数失败在 L1-L2 即可解决。L4 是底线——永远不要无声失败。

### 9.4.4 实施模式

生产环境中最小的自适应重规划骨架：

```python
class AdaptiveExecutor:
    def __init__(self, planner, executor, validator):
        self.planner = planner      # o4-mini，reasoning_effort=medium
        self.executor = executor    # GPT-4o 或 Claude Haiku
        self.validator = validator  # 独立验证器，非 Executor 自检

    def execute_plan(self, plan, goal):
        completed = []
        remaining = plan.steps[:]
        dependency_graph = plan.dependency_graph  # Planner 必须输出依赖图

        while remaining:
            step = remaining.pop(0)
            try:
                result = self.executor.run(step)
                if not self.validator.check(step, result):
                    # L1: 本地回退
                    result = self.executor.run(step.with_retry())
                completed.append((step, result))
            except Exception as e:
                # L2: 范围重规划
                affected = dependency_graph.get_affected_subtree(step.id)
                revised = self.planner.replan_subtree(
                    goal=goal, completed=completed,
                    failed_step=step, error=str(e),
                    affected_steps=affected
                )
                remaining = revised + [s for s in remaining if s not in affected]

        return completed
```

核心要点：
- **依赖图是重规划的基础**——没有它就只能全量重规划
- **验证器独立于执行器**——防止 Executor "自我说服"步骤成功了
- **检查点保存已完成步骤**——重规划时不要丢弃已完成的工作

## 9.5 生产实践

### 9.5.1 混合架构：推理模型做规划，快速模型做执行

这是 2026 年最成熟的生产模式：

```
o3/o4-mini（推理模型）
    ↓ 一次性生成结构化的执行计划 + 依赖图
GPT-4o / Claude Haiku（快速模型）
    ↓ 按步骤执行工具调用
o4-mini（推理模型）
    ↓ 只在执行异常时触发，做范围重规划
```

一次 o3 规划 + N 次快速模型执行 的成本远低于 N 次 o3 调用。

### 9.5.2 三个常见陷阱

**陷阱一：在循环中使用高 thinking_budget**

```python
# ❌ 10步Agent循环，每步都调用 o3 reasoning_effort="high"
# 每步可能需要30秒思考，10步 = 5分钟 + 巨额Token

# ✅ 规划用 o3 一次，执行用 GPT-4o
plan = o3_plan(goal, reasoning_effort="high")     # 一次深度规划
for step in plan.steps:
    result = gpt4o_execute(step)                   # 快速执行
```

**陷阱二：不设 max_completion_tokens**

推理模型的 thinking tokens 可以暴涨。不设上限等于签空白支票。生产环境始终设置——通常轻量任务 4000-8000，复杂任务 16000-32000。

**陷阱三：只用一种模式**

没有银弹。ReAct 适合动态交互，Plan-Execute 适合结构化任务，Reflexion 适合需要改进的场景。生产系统往往组合使用。

## 9.6 决策框架

按优先级依次判断你的任务该用什么模式：

1. **工具调用完全可预测？** → **ReWOO**（5x Token 节省，并行执行）
2. **步骤 < 5，需要自适应？** → **ReAct**（灵活，低开销）
3. **步骤 ≥ 5，结构明确？** → **Plan-Execute + 自适应重规划**
4. **质量是唯一约束，成本不敏感？** → **o3 全程深度推理**
5. **需要多轮改进？** → **Reflexion**（失败后生成反思并重试）

## 9.7 小结

2026 年规划与推理的核心变化：**推理从 Prompt 技巧变成了模型能力**。

- **推理模型**（o3/o4-mini）内化了 CoT，`reasoning_effort` 替代了 `"Let's think step by step"`。但非推理模型（GPT-4o、Claude Haiku）在成本敏感场景中依然依赖 Prompt 工程引导推理。
- **四种规划架构**各有适用场景：ReAct 灵活但缺乏全局视野，Plan-Execute 结构清晰但初始规划质量决定成败，Reflexion 能从失败中学习，ReWOO 以 5x Token 节省换取了灵活性。
- **自适应重规划**是 2026 年最重要的工程能力：范围重规划优于全量重规划，依赖图是基础，四级升级（回退→范围→全量→人工）是生产底线。
- **混合架构是生产金标准**：推理模型做规划，快速模型做执行——一次 OA 规划 + N 次快速执行的成本远低于 N 次推理模型调用。

下一章，我们将进入多智能体治理，探讨 Sub-Agent 的监控、编排与协作。

---

## 参考资料

01. ReAct (Yao et al., ICLR 2023) — https://arxiv.org/abs/2210.03629
02. Reflexion (Shinn et al., 2023) — https://arxiv.org/abs/2303.11366
03. Plan-and-Act (UC Berkeley, ICML 2025) — https://arxiv.org/abs/2503.09572
04. ALAS: Disruption-Aware Multi-Agent Planning — https://arxiv.org/abs/2505.12501
05. SagaLLM: Transactional Multi-Agent Planning (VLDB 2025) — https://arxiv.org/abs/2503.11951
06. OpenAI o3/o4-mini Reasoning Guide (2026) — https://platform.openai.com/docs/guides/reasoning
07. Zylos Research: Adaptive Replanning Strategies (2026.03) — https://zylos.ai/zh/research/2026-03-20-adaptive-replanning-ai-agents/
08. Cowork.ink: AI Agent Reasoning Patterns (2026) — https://cowork.ink/blog/ai-agent-reasoning/
