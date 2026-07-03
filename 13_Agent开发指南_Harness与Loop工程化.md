# 第13章：Agent Harness 与 Loop 工程化

> "If you're not the model, you're the harness."
>
> —— Vivek Trivedy, LangChain, 2026年3月

2026年，AI Agent 开发领域发生了两次安静但深刻的概念迁移。

第一次：开发者们意识到，**模型本身不是 Agent**。把 LLM 的"智力"转化为"生产力"，需要一整套包裹在模型外面的运行环境——这就是 **Harness**。

第二次：开发者们进一步意识到，**写 prompt 不是工作，设计让 Agent 自己运行的系统才是**。人从循环的执行者变成循环的设计者——这就是 **Loop Engineering**。

两次迁移合在一起，完成了一个完整的范式转换：Prompt Engineering → Harness Engineering → Loop Engineering。本章从这两个概念讲起，然后看它们怎么在实际工程中配合。

---

## 13.1 Harness Engineering：模型之外的一切

### 13.1.1 起源：一个公式的诞生

2026年3月，LangChain 的 Vivek Trivedy 写了一篇博客，标题是《The Anatomy of an Agent Harness》。文中提出了一个后来被 OpenAI、Anthropic、Martin Fowler 广泛引用的公式：

```
Agent = Model + Harness
```

这个公式简单到像一句废话，但它的真正力量在于**划清了边界**：

- **Model**：模型权重 + 推理引擎。只负责"理解"和"生成"，不负责"做"。
- **Harness**：系统提示词、工具定义、编排逻辑、文件系统、沙箱、网络层、权限控制——所有将模型的"理解"转化为"行动"的东西。

ThoughtWorks 的 Birgitta Böckeler 后来给了一个更精炼的定义：**Harness = Guides（前馈控制）+ Sensors（反馈控制）**。

如果你做过 Agent 开发，这个公式会让你想起很多踩过的坑——你花 80% 的时间不是调 prompt，而是在搭工具管理、做权限控制、写重试逻辑、防止无限循环。那些东西以前没有一个统一的名字，现在有了：**Harness**。

### 13.1.2 六组件框架：H = (E, T, C, S, L, V)

综合多个工业级 Harness 实现，一个生产级 Agent Harness 可以模型化为六个组件：

```
H = (E, T, C, S, L, V)
```

| 组件 | 含义 | 关键设计原则 |
|------|------|-------------|
| **E** (Environment) | 运行环境与沙箱 | 网络隔离、文件系统隔离、命令白名单 |
| **T** (Tool Registry) | 工具注册表 | 原子性、正交性、完备性、可组合性 |
| **C** (Context Manager) | 上下文管理 | 自动压缩、Subagent 委托、窗口裁剪 |
| **S** (Safety Layer) | 安全层 | Token 预算、内容过滤、权限模式 |
| **L** (Lifecycle Hooks) | 生命周期钩子 | PreToolUse、PostToolUse、Stop |
| **V** (Evaluation) | 评估接口 | 轨迹捕捉、LLM-as-Judge、A/B 对比 |

这些组件不是你每个项目都要从头实现的。实际上，Claude Agent SDK、OpenAI Agents SDK、LangGraph 等框架已经内置了其中大部分。但**理解这个框架的价值在于，它让你知道什么该自己控制，什么可以放心交给框架**。

#### Environment：沙箱不是可选项

一个教训深刻的案例：Anthropic 在内部实践中发现，仅给 Claude 提供 `bash` 和文本编辑器两个通用工具，它就能取得惊人的表现。但前提是——它在一个**隔离环境**中运行。

生产级 Harness 的沙箱至少需要五层防御：

1. **网络隔离**：Agent 网络访问白名单，禁止访问内部服务
2. **文件系统隔离**：每个 Agent 独立的工作目录，物理上不可能互相覆盖
3. **命令沙箱**：危险命令（`rm -rf`、`sudo`）拦截 + 审计日志
4. **Token 预算**：单任务最大消耗上限，防止成本失控
5. **内容过滤**：输出安全检测，拦截敏感信息泄露

请注意这个顺序：**前两层解决"Agent 会不会搞破坏"，后三层解决"Agent 会不会失控"**。先确保破坏不扩散，再考虑控制行为。

#### Tool Registry：Bash is all you need——但这不代表工具不重要

Anthropic 的实践总结了一条颇具争议的原则：**Bash is all you need**。Claude 在只有 bash 和文本编辑器两个工具时，就能完成绝大多数编程任务。

但这不意味着你可以忽视工具注册表的设计。工具定义的四个原则：

- **原子性**：一个工具只做一件事。`search_and_replace` 不是一个好名字，因为它在做两件事。
- **正交性**：工具之间不重叠。如果 `read_file` 和 `grep` 都能查文件内容，Agent 会在两个工具之间纠结。
- **完备性**：覆盖所有需要的操作。缺了某个基础操作，Agent 会绕远路。
- **可组合性**：工具的输出可以作为另一个工具的输入。

一个真实的生产教训：某团队把编辑工具从 `str_replace` 格式替换为自主设计的 `hashline` 格式（用行哈希而非行号定位），在完全不改变底层模型的情况下，任务成功率从 **6.7% 跃升至 68.3%**。

这就是 Harness 优化不是"锦上添花"而是"核心杠杆"的最好证据。**工具的接口设计，比工具的功能本身更影响 Agent 的表现。**

### 13.1.3 评估：从"看结果"到"看轨迹"

传统软件测试验证的是"输入 → 输出"，确定性逻辑，pass/fail 一目了然。Agent 测试完全不同——同样的输入，模型可能给出不同的推理路径，最终结果是对的但路径是错的。

所以 Agent Harness 的评估不是"看结果"，是"看轨迹"。

**三层评估体系**：

| 层次 | 方法 | 适用场景 | 成本 |
|------|------|---------|------|
| **Task Layer** | 基准测试（SWE-bench、GAIA、WebArena） | 横向对比模型/Agent 能力 | 低（标准化数据） |
| **Decision Layer** | 轨迹分析（Trajectory Analysis） | 验证推理路径是否合理 | 中（需要人工标注或 LLM-as-Judge） |
| **Production Layer** | 持续评测（CI 集成 + A/B 测试） | 确保每次变更不退化 | 高（需要持续运行） |

**关键词匹配已死，LLM-as-Judge 当立。** 简单的关键词匹配（"答案是否包含'晴'字"）在 Agent 评估中几乎毫无价值——Agent 的输出太复杂、太多样。用一个更强的模型来评判 Agent 的输出质量，已经是 2026 年的标准做法。

但要小心：LLM-as-Judge 也有系统性偏见——它倾向于给"看起来像正确答案"的答案打高分，而不是真正正确的答案。目前的最佳实践是：**用 LLM-as-Judge 做初筛，用人工抽样做校准**。

一个小建议：如果你的 Agent 任务比较简单（比如客服 FAQ 匹配），可以先用关键词匹配做第一轮过滤，把明显错的筛掉，再用 LLM-as-Judge 做精判。这样成本可控，又不丢准确性。

### 13.1.4 一个真实的 Harness 案例

一家金融科技公司部署了自动化 Agent 评测框架后，拿出的数据相当震撼：

| 指标 | 优化前 | 优化后 |
|------|--------|--------|
| 测试周期 | 3 天（人工） | 4 小时（自动化） |
| 测试用例覆盖 | ~60 条 | ~327 条（边界用例） |
| 单轮人力成本 | ¥12,000 | ¥100 |
| 缺陷拦截率 | 基准值 | 提升 63% |

这个案例说明了一个核心事实：**Harness 不是让你少写 prompt，是让你少调 Agent。** 花在测试框架上的时间，会在调试时间上十倍赚回来。

---

## 13.2 Loop Engineering：让 Harness 自己跑起来

### 13.2.1 定义：Loop = Cron + 决策器

如果说 Harness 是 Agent 的"身体"——运行环境、工具、安全控制，那 Loop 就是 Agent 的"心跳"——什么时候跑、跑什么、什么时候停。

**Loop Engineering 最简单的定义：Loop = Cron + 决策器。**

传统模式：人 → 写 prompt → Agent 输出 → 人读结果 → 人写新 prompt → ...

Loop 模式：人 → 设计 loop → loop 自动 prompt Agent → loop 读输出 → loop 判断是否完成 → loop 自动重 prompt 或终止

这个范式迁移被 Boris Cherny（Claude Code 负责人）用一句话道破：**"我不再 prompt Claude 了。我写 loop 让它们运行，loop 去 prompt Claude 并决定下一步做什么。我的工作是写 loop。"**

一个令很多人震撼的数据点：Boris 最近 30 天，100% 对 Claude Code 的代码贡献（259 个 PR）都是由 Claude Code 自己写的。他的工作不再是写代码，而是设计让 Claude Code 写代码的 loop。

### 13.2.2 演进史：从 ReAct 到多 Agent 编排

Loop 不是 2026 年突然冒出来的概念。它的演进路径清晰地记录了过去四年 Agent 的核心发展轨迹：

| 阶段 | 时间 | 核心思想 | 教训 |
|------|------|---------|------|
| **ReAct** | 2022 | 推理（Thought）与行动（Action）交替 | 单步推理，没有自主循环 |
| **AutoGPT** | 2023 | 全自主 Agent，设定目标后自动执行 | 没有终止条件的自主循环 = 灾难 |
| **Ralph Loop** | 2025 | 引入结构化循环验证 | 仍需人工介入验证 |
| **/goal & /loop** | 2026 | 声明式目标 + 自动循环 | 需要精心设计目标描述和终止条件 |
| **多 Agent 编排** | 2026 | 多个 Agent 协同完成复杂任务 | 编排复杂度指数级增长 |

注意这个演进的核心趋势：**每一步都在把"人"从循环内部往外推。**

AutoGPT 是第一个"让 Agent 自主循环"的尝试。它失败了——或者说，它的失败恰好定义了 Loop Engineering 必须解决的第一个问题：**没有终止条件的自主循环就是灾难。**

今天的 /goal 指令之所以能工作，正是因为从这个失败中学到了：**判断是否完成的不能是干活的模型，必须是另一个独立的模型（或规则）**。制造者不批改自己的作业。

### 13.2.3 六个原语：Loop 的通用结构

Addy Osmani 在 2026 年 6 月发表的《Loop Engineering》一文中，总结了 Loop 的六个原语——这个框架同时映射到 Claude Code 和 Codex App 两大产品，说明它不是工具特定的，而是 loop 本身的通用结构。

| 原语 | Loop 中的角色 | 一句话理解 |
|------|-------------|-----------|
| **Automations** | 定时发现与分诊 | Loop 的心跳——不是跑一次就结束 |
| **Worktrees** | 并行隔离 | 两个 Agent 同时写同一个文件 = 灾难（git worktree 解决） |
| **Skills** | 固化项目知识 | 把隐性知识写到磁盘上，agent 每次运行都读 |
| **Connectors** | 连接外部工具 | MCP 让 Loop 能读 issue tracker、开 PR、发 Slack |
| **Sub-agents** | 制造者与审查者分离 | 一个写代码，另一个（不同模型/指令）审查 |
| **State** | 跨会话记忆 | 模型在两次运行之间忘记一切——记忆必须在磁盘上 |

这六个原语中，最容易被忽视但最关键的是 **State**。

听起来太简单以至于不像一个重要设计：一个 markdown 文件、一个 Linear board、一个存在于单次对话之外的数据。但 Addy Osmani 反复强调：**This is the same trick every long-running agent depends on. 模型在两次运行之间忘记一切，所以记忆必须在磁盘上，不在上下文里。**

### 13.2.4 一个真实 Loop 的形状

综合多个信息源，一个典型的 Loop 长这样：

```
1. Automation 每天早上在 repo 上运行
   → 调用 triage skill，扫描新 issue 和 CI 失败
   → 结果写入 progress.md（State 原语）

2. Loop 读取 progress.md，找到最高优先级任务
   → 派出 sub-agent A（实现者，用 fast model）
   → 在独立 worktree 中工作（Worktrees 原语）
   → 完成后派 sub-agent B（审查者，用 strong model）
   → 审查通过 → 开 PR + 关联 Linear ticket（Connectors 原语）
   → 审查不通过 → 反馈写回 progress.md，A 重新尝试

3. /goal 判断："所有 P0 issue 已关闭且 CI green"
   → 满足 → loop 终止，通知人
   → 超过迭代上限 → 终止，升级给人

4. 预算控制：max 15 iterations / $5 / 300s
```

人介入的时机只有三个：**loop 卡住了、方向需要调整、最终结果需要确认。**

### 13.2.5 Anthropic 的内部数据

Anthropic 在 2026 年 6 月发布的《When AI builds itself》报告中，公开了一组 Loop Engineering 的生产力数据：

| 指标 | 数值 |
|------|------|
| Claude 写的代码占合并总量 | >80%（2026年5月） |
| 工程师日均代码合并量 | 较 2024 年增长 8x |
| 开放式任务成功率 | 76%（半年前 26%） |
| Claude 自主优化训练代码加速 | 3x（2025.5）→ 52x（2026.4） |

两个拐点值得注意：

- **2025 年初**：Claude 从"建议代码"变成"自己跑代码"——代码量开始攀升
- **2026 年初**：模型开始长时间自主工作——斜率再次陡增

这些数据印证了 Loop Engineering 的核心假设：**当 Agent 可以在 loop 中自主运行时，人的产出不取决于写代码的速度，而取决于设计 loop 的质量。**

### 13.2.6 三个高度的阶梯

Boris Cherny 提出了一个"阶梯"模型来描述 AI 辅助工作的三个高度：

**高度 1：带自动补全的手写代码。** 人写代码，模型建议补全。最快写简单代码的方式，但人仍在 loop 内。

**高度 2：并行运行多个 Agent 会话。** 启动多个 Agent 探索不同方案，人决定推进哪个。人仍在做决策和指挥。

**高度 3：编写 Loop 来替你 Prompt Agent。** 人写决策器，loop 和模型自主运行。人只在 loop 卡住或需要优化时介入。

每上升一个高度，人的角色就从**执行者**变成**设计者**。这不是"人被替代"——是问题的尺度变了。你不再考虑"这段代码怎么写"，你考虑的是"这个系统怎么设计"。

---

## 13.3 Harness + Loop：它们怎么配合？

把前面两节串起来：**Harness 是静态的基础设施，Loop 是动态的编排层。**

Harness 解决"Agent 能不能跑"：
- 沙箱让它安全地跑
- 工具注册表让它知道自己能干什么
- 评估接口让你知道它跑得怎么样

Loop 解决"Agent 跑不跑、怎么跑、跑到什么时候停"：
- Automations 决定什么时候跑
- /goal 决定跑到什么程度停
- Sub-agents 让多个 Agent 协同跑
- State 让下次跑的时候知道上次发生了什么

一个比喻：Harness 是汽车的底盘、引擎、刹车、安全气囊。Loop 是导航系统、巡航控制、自动驾驶逻辑。没有底盘，车根本动不了；没有导航，你只能一直握着方向盘。

**两个常见误区：**

1. **"有了 Harness 就不需要 Loop。"** 错。Harness 让一个 Agent 在单次调用中表现良好，但生产环境需要的是持续运行、自主决策的系统。Harness 保证质量，Loop 保证持续性。

2. **"Loop 就是多轮对话。"** 错。多轮对话是用户在场的情况下的交互式循环，Loop 是用户不在场的情况下的自主循环。多轮对话不需要 /goal 终止条件，不需要预算控制，不需要自动化触发——Loop 全需要。

---

## 13.4 工程实践：从 Demo 到生产

### 13.4.1 成本控制：预算不是可选项

一个设计不当的 Loop 可以在几小时内烧掉数十美元。这不是比喻——Ben's Bites 在讨论 Loop Engineering 时特别警告过：**usage patterns can vary wildly if you are token rich or poor。**

三层成本控制：

```python
class LoopBudget:
    max_iterations: int = 15          # 第一层：硬性迭代上限
    max_cost_usd: float = 5.0         # 第二层：费用上限
    max_duration_seconds: int = 300   # 第三层：时间上限

    def is_exceeded(self, iterations, cost, elapsed):
        return (iterations >= self.max_iterations or
                cost >= self.max_cost_usd or
                elapsed >= self.max_duration_seconds)
```

注意这个设计：**三层中任何一层触达上限，Loop 都应该终止**——不是"三选一"的安全网，而是三道独立的防线。

另外，对于非实时任务（比如夜间批量处理），OpenAI 的 Batch API 提供 50% 折扣。搭配 Prompt Caching（见第 1 章），你的实际花费可以再砍一半。Production Loop 的 Token 经济学不是"能省则省"，而是"不省的都会变成你的账单"。

### 13.4.2 质量保证：制造者不批改自己的作业

Loop 运行时你不在旁边看着。所以**你信任的验证器，是唯一让你敢走开的东西。**

最有效的结构：一个 Agent 写代码，一个不同指令（甚至不同模型）的 Agent 审查。原因很直接：写代码的模型对自己太客气了，第二双眼睛能抓住第一个说服自己的东西。

但这里有一个坑：**审查 Agent 同样会出错，而且它错的方式和写代码的 Agent 不一定不同。** 如果你用同一个模型做审查（比如两个 Agent 都跑 Claude Sonnet），它们有相似的盲区。更好的做法是：

- 实现用 fast model（DeepSeek V4 Flash、Gemini 3.1 Flash）
- 审查用 strong model（Claude Opus 4.1、GPT-5.4 Pro）
- 关键决策用不同供应商的模型交叉验证

另外，Mikhail Parakhin（前微软）有一个值得反思的观察："模型写更好的代码，但我们用它们写更多代码——不是更好的代码。" **生成的代码越多，审查负担越重，维护成本越高。** Loop 的目的不是让 Agent 写最多代码，而是写最少的、最正确的代码。

### 13.4.3 编排税：Review 带宽是新瓶颈

Addy Osmani 提了一个概念叫 **编排税（Orchestration Tax）**：5 个并行 Agent 听起来很酷，但如果你每小时只能认真审查 1 个 PR，其他 4 个就是在浪费 Token。

**你的 Review 带宽才是并行度的真正上限。** 不是工具决定你能跑多少并行 Agent，而是你能审核多少。

这意味着 Loop 设计的一个核心约束：**Agent 产出的速度不能超过你审查的速度。** 当 Anthropic 的内部数据显示代码产出增长 8x，真正的挑战不是"怎么让 Agent 写更多代码"，而是"怎么让人审得过来"。

现实中实用的策略：

1. **分级审查**：高风险 PR（涉及认证、支付、数据库 Schema 变更）需要人工审查。低风险 PR（文档更新、测试补充、代码格式）可以信任 Agent。
2. **审查循环**：让审查 Agent 先审，通过后再交给人。人的审查不再是逐行看代码，而是看 Agent 的审查报告 + 抽查关键逻辑。
3. **批量审查**：不要每来一个 PR 就审，而是每天固定时间审查一批。Agent 不会不耐烦。

### 13.4.4 可调试性：当 Loop 做错了，你怎么知道为什么？

Loop 最大的工程挑战是**可调试性**。当 loop 出错了，"为什么做了这个决策"是最难回答的问题。

最少需要三个层面的追踪：

| 追踪层 | 内容 | 格式 |
|--------|------|------|
| **迭代日志** | 每一次迭代的输入、模型输出、工具调用、结果 | JSON Lines |
| **决策树** | LLM 选择工具 A 而非工具 B 的原因 | 自然语言摘要 |
| **状态变更** | State（progress.md 等）的每次写入记录 | Git diff |

另外，在 Loop 中加入 **"为什么要做 X"的显式日志**——不是在最终结果中，而是在每次关键决策前让 Agent 输出一段 short reasoning。这增加的 Token 成本不高，但出错时的调试价值极高。

---

## 13.5 从 Prompt 到 Loop：四个阶段

如果你正在考虑把现有的 Prompt-based workflow 升级到 Loop 体系，下面是一个渐进路线：

**阶段一：从 Prompt 到 Harness（1-2 周）**

把你手写的工具调用和重试逻辑，抽象成一个最小 Harness——沙箱、工具注册表、Token 预算控制。这个阶段不改变 Agent 的一次性执行模式，只是把基础设施规范化。

**阶段二：从 Harness 到简单 Loop（2-4 周）**

加入 `/goal` 终止条件：Agent 重复执行直到条件满足或预算耗尽。从最简单的场景开始——比如自动修复 lint 错误。这个阶段的目标不是"Agent 能自主完成复杂任务"，而是"你信任 loop 在简单任务上的判断"。

**阶段三：加入验证与审查（4-8 周）**

引入 Sub-agent 审查模式：一个 Agent 做，另一个审查。审查结果写回 State，形成反馈闭环。加入自动化触发（每天运行、代码 push 触发等）。

**阶段四：多 Agent 编排（持续迭代）**

多个 Loop 协同工作：一个 Loop 负责 triage，一个负责实现，一个负责测试，一个负责部署。每个 Loop 有独立的 State、独立的工作树、独立的预算。

---

## 13.6 最后一个提醒

Anthropic 在《Building Effective Agents》中有一句话，值得刻在每个 Loop Engineer 的屏幕上：**"大多数场景下，简单的 workflow 比复杂的 agentic loop 更合适。"**

Loop Engineering 很酷。Harness Engineering 很强大。但它们解决的是一个特定问题：**那些无法预先定义完整执行路径的任务。** 对于可以明确步骤的流程——数据管道、固定审批流、模板化内容生成——确定性 workflow 更稳定、更可预测、更便宜。

怎么判断该不该用 Loop？一个简单的测试：**如果这个任务交给人，人需要"边做边想"吗？** 如果需要，上 Loop。如果不需要（比如"每天 9 点拉取报表数据"），用 cron + 简单脚本就够了。

Loop Engineering 的最大危险不是技术不成熟，而是**过早优化**——在一个简单 workflow 就够用的场景里，引入了一套复杂的自主循环系统。你增加的工程复杂度，远超过你释放的生产力。

---

## 本章小结

Harness Engineering 和 Loop Engineering 是 2026 年 Agent 开发领域最重要的两个概念迁移：

1. **Agent = Model + Harness**。模型之外的一切——沙箱、工具、安全、评估——都属于 Harness 的范畴。Harness 的质量决定了 Agent 能不能稳定地跑，而不仅仅是能跑。
2. **Loop Engineering 是"让人从循环的执行者变成循环的设计者"**。六个原语——Automations、Worktrees、Skills、Connectors、Sub-agents、State——定义了一个生产级 Loop 的完整结构。
3. **Harness 是基础，Loop 是编排**。Harness 让 Agent 能跑，Loop 让 Agent 持续自主地跑。
4. **成本控制、质量保证、编排税、可调试性**是 Loop 从 Demo 到生产的四大工程挑战。
5. **不是所有场景都需要 Loop。** 简单的 workflow 仍然是最佳选择——只有当任务需要"边做边想"时，Loop 才真正发挥价值。

---

*参考来源：*

- *Vivek Trivedy, "The Anatomy of an Agent Harness", LangChain Blog, 2026.3*
- *Addy Osmani, "Loop Engineering", addyosmani.com, 2026.6*
- *Anthropic Institute, "When AI builds itself", anthropic.com, 2026.6*
- *Boris Cherny, Twitter/X thread on Loop Engineering, 2026.6*
- *Ben's Bites, "Hey Siri, meet AI", bensbites.com, 2026.6*
- *知乎技术分析报告, "2026 Agent Harness 框架深度分析", 2026.5*
- *QubitTool, "AI Agent 评估与 Harness Engineering 实战指南", 2026.4*
- *iTech, "深入理解 Agent Loop", cnblogs.com, 2026.6*
- *道玉 AI 工作坊, "Loop Engineering 深度综述", daoyuly.cn, 2026.6*
