# 第十二章 生态工具——主流框架与产品

2026 年的 Agent 框架格局跟两年前完全不同。LangChain 一家独大的时代结束了，取而代之的是四条赛道同步竞争：实验室官方 SDK、独立编排框架、多 Agent 协作框架、低代码平台。本章不讲"怎么用"（那是文档的事），而是帮你理清每条赛道的玩家、边界和选择逻辑。

## 12.1 2026 框架全景

先把玩家认全。按赛道分类：

| 赛道 | 框架 | 定位 |
|------|------|------|
| **实验室 SDK** | OpenAI Agents SDK | 行动优先，并行原生 |
| | Anthropic Claude Agent SDK | 安全门控，原生 MCP |
| | Google ADK | 图原生，多语言企业级 |
| | Microsoft Agent Framework | .NET 生态，企业中间件 |
| **独立编排** | LangGraph | 图驱动状态机，0% 云锁定 |
| | LangChain | 生态最大，700+ 集成 |
| **多 Agent 协作** | CrewAI | 角色化团队，上手最快 |
| | AutoGen (v0.4+) | 对话驱动，微软出品 |
| **低代码平台** | Dify | 开源 Web UI，内置 RAG |
| | Coze (扣子) | 字节跳动，200+ 插件 |

两个数字帮你感受生态规模：MCP 协议月下载量 9700 万次，公开 MCP Server 17,468 个——Agent 的工具生态已经不是"有几个 HTTP API 能调"，而是"是否有标准的协议栈"。

## 12.2 四大实验室 SDK

2025 年底到 2026 年初，OpenAI、Anthropic、Google、Microsoft 在六个月内先后发布了生产级 Agent SDK。它们不再是"玩具"，而是各自云生态的战略锚点。

**设计哲学差异**：

| 维度 | OpenAI | Anthropic | Google ADK | Microsoft |
|------|--------|-----------|------------|-----------|
| 设计哲学 | 行动优先 | 安全门控 | 图原生 | 企业中间件 |
| 工具定义 | `@function_tool` 装饰器（最简洁） | 需理解 MCP Server | 四种语言（Python/TS/Java/Go） | 编译时类型安全 |
| 多 Agent 交接 | 显式一等模型（最不易出错） | 会话级编排 | 有向图 + 条件边（最强但复杂） | ChatAgent 统一抽象 |
| MCP 集成 | 适配器层 | **原生**（创建者） | 适配器层 | 适配器层 |
| A2A 协议 | 成员 | 成员 | **联合作者/领导者** | 成员（文档少） |
| 语言支持 | Python/JS | Python | Python/TS/Java/Go | .NET/Python |

**企业市场格局**（2026 Q1 数据）：Anthropic ~40% 企业部署份额（领先），OpenAI ~27%（从 2023 年的 50% 下滑），Google ~21%。LangGraph 出现在 34% 的千人以上企业架构文档中——作为独立编排框架，它跨云的优势正在侵蚀实验室 SDK 的份额。

**选 SDK 的核心问题不是"今天哪个 API 更好用"**，而是"你的组织能承受哪种基础设施依赖 24-36 个月"。四大 SDK 都深度绑定各自的云平台——选 OpenAI 等于选 OpenAI 基础设施，选 Google 等于选 GCP。只有 LangGraph 提供 0% 云锁定的图编排能力。

## 12.3 独立编排框架：LangGraph + LangChain

LangChain 依然是生态最大的集成框架（700+ 工具集成），但它的核心价值已经转移：**LangChain 负责"对接"，LangGraph 负责"编排"**。

**LangChain**：LCEL（LangChain Expression Language）提供统一的 Runnable 协议——`invoke`/`stream`/`batch`/`map`。管道操作符 `|` 将组件串联为 DAG，适合线性流程。但一旦涉及循环和条件分支，LCEL 就力不从心。

**LangGraph**：将 Agent 执行建模为状态机——State（共享状态字典）在 Node（执行单元）之间通过 Edge（流转条件）传递。核心能力是**循环图**而非 DAG，这意味着 Agent 可以"思考 → 行动 → 观察 → 再思考"，形成真正的 Agent Loop。内置 Checkpointer 实现断点续传，支持 Human-in-the-Loop 的暂停-审批-恢复流程。

**两者的关系**：LangGraph 的 Node 里可以直接用 LangChain 的组件（Prompt 模板、LLM 封装、输出解析器）。不是"二选一"，而是"LangChain 做零件，LangGraph 做装配线"。

## 12.4 多 Agent 协作：CrewAI vs AutoGen

多 Agent 框架解决同一个问题：单个 Agent 的 Prompt 和上下文承载不了太复杂的任务，需要"分而治之"。

**CrewAI**：角色化设计。三个核心概念——Agent（定义角色 + 目标 + 背景故事）、Task（定义任务 + 期望输出）、Crew（组装 Agent 和 Task）。框架自动处理任务分配、结果聚合、依赖管理。学习曲线最平——半小时能从零写成"研究员→撰稿人→审校"三步流水线。2026 年多 Agent 协作能力被评价为最成熟。

**AutoGen (v0.4+)**：对话驱动。Agent 之间通过消息进行交互，像几个人开会讨论一样逐步逼近解决方案。灵活度高——支持 RoundRobin、SelectorGroup 等多种对话模式，但需要精心设计终止条件，容易陷入无限循环。微软出品，与 Azure、Semantic Kernel 无缝集成。

**什么时候用哪个**：如果你需要明确的角色分工和流水线任务（"先 X 再 Y 再 Z"），用 CrewAI。如果你需要 Agent 之间通过多轮对话动态协作（"你们讨论一下这个问题"），用 AutoGen。如果第 10 章的决策框架判断你**不需要**多 Agent，那这两个都别用。

## 12.5 低代码平台：Dify + Coze

2026 年国内开发者最常用的两个 Agent 平台，都不需要写代码。

**Dify**：开源，Web UI 拖拽构建工作流。核心优势是内置 RAG——不需要额外搭向量数据库和 Embedding 管道，上传文档就能做知识库问答。支持 Docker 一键部署，可直接对接 DeepSeek、通义千问等国产模型。适合需要快速验证 PMF 或让非技术人员参与 Agent 构建的团队。

**Coze（扣子）**：字节跳动出品，闭源。最大卖点是 200+ 插件市场——飞书/钉钉/企微消息推送、抖音数据、微信生态全覆盖。配置触发条件和动作就能发布 Bot。缺点是 Agent 逻辑不能完全自定义，数据不落地，安全合规严格场景受限。

**Dify vs Coze**：开源自托管 vs 闭源云服务。需要数据控制和深度定制选 Dify，需要国内生态无缝集成和零运维选 Coze。

## 12.6 MCP + A2A + ARD：协议栈三剑客

2026 年 Agent 生态最重要的基础设施不是任何框架，而是三层协议——它们已经形成了清晰的分工：

```
┌─────────────────────────────────────┐
│           ARD（发现层）               │
│  Well-Known URI · AI Catalog · URN  │
│  Registry · 联邦搜索 · Trust Manifest │
│  "有什么可用？谁提供的？可信吗？"       │
├─────────────────────────────────────┤
│           A2A（协作层）               │
│  Agent Card · Task · Artifact · SSE │
│  "Agent 之间怎么委托任务？"           │
├─────────────────────────────────────┤
│           MCP（执行层）               │
│  Tools · Resources · Prompts        │
│  "怎么调用具体工具和资源？"           │
└─────────────────────────────────────┘
```

### 12.6.1 MCP（执行层）

Anthropic 创建，2025 年 12 月移交 Linux Foundation 旗下 Agentic AI Foundation。核心概念：MCP Server 暴露工具（Resources/Tools/Prompts），MCP Client（Agent）通过标准协议调用。2026 年 4 月数据：月下载 9700 万次，17,468 个公开 Server。

### 12.6.2 A2A（协作层）

Google 主导，v1.0 于 2026.03 发布。解决 Agent 间的能力发现和任务委托。150+ 组织采用，预置合作伙伴包括 Salesforce、Workday、ServiceNow。A2A 的深度工程解析（Agent Card 结构、Task 生命周期、多轮交互模式）见第十章补充文件 `10_Agent开发指南_A2A协议深度解析.md`。

### 12.6.3 ARD（发现层）

Google + Microsoft + Hugging Face + GoDaddy 联合推动，v0.9 于 2026.06 发布——本书截稿时最新鲜的 Agent 协议。解决的是"编排 Agent 怎么自动发现有哪些资源可用"。核心机制：Well-Known URI 静态发布资源清单、Registry 语义搜索、URN 全局标识、Trust Manifest 信任评估。完整解析见本章补充文件 `12_Agent开发指南_ARD协议发现层.md`。

**对你的影响**：2026 年选框架 = 选协议生态。核心原则不变：**围绕协议构建，而非围绕框架构建**——协议的生命周期远长于框架。只是现在你要检查的不是两个协议，是三个。

## 12.7 选型决策

别再一个一个试了。按场景速查：

| 你的场景 | 推荐 | 原因 |
|----------|------|------|
| 快速原型验证、非技术人员参与 | **Dify** | 可视化拖拽，内置 RAG |
| 国内生态无缝集成（企微/飞书/抖音） | **Coze** | 200+ 国内插件，零运维 |
| 多 Agent 角色化协作 | **CrewAI** | 角色化设计最成熟，0.5 小时上手 |
| 需要深度定制、0% 云锁定 | **LangGraph** | 图驱动编排，跨所有 LLM 供应商 |
| 最大工具集（700+ 集成） | **LangChain** | 生态最大，什么都能接 |
| 微软/.NET 生态 | **Microsoft Agent Framework** | Azure + Semantic Kernel 集成 |
| 原生 MCP 深度投入 | **Anthropic Claude SDK** | MCP 创建者，集成摩擦最低 |
| 多语言企业级（Java/Go） | **Google ADK** | 唯一四语言企业 SDK |
| 学术实验、对话式任务分解 | **AutoGen** | 多轮对话模式灵活 |

**三个决策原则**：

1. **优先选协议，其次选框架**。确保你的工具链通过 MCP 暴露，Agent 通过 A2A 协作——这样换框架时不伤筋动骨。
2. **从最简单的开始**。Dify 或 CrewAI 先跑通 PMF，再根据瓶颈决定是否迁移到 LangGraph 或实验室 SDK——而不是反过来。
3. **不要 All in 一个框架**。2026 年的格局还在快速演变。掌握一个主力框架的同时，保持对其他框架的了解。

## 12.8 小结

2026 年的 Agent 框架生态有三条主线：

1. **框架在分化，协议在收敛**。四大实验室 SDK 各有哲学，但都在向 MCP + A2A 协议栈靠拢。
2. **编排能力从"手写"变成"内置"**。LangGraph 的 Checkpointer、CrewAI 的任务依赖管理、Dify 的可视化工作流——你不再需要自己实现断点续传、任务排队、HITL。
3. **国内生态独立成线**。Dify 和 Coze 在国内开发者中的使用率已经超过 LangChain，国产模型的原生对接是核心优势。

选框架最怕的是什么？花三个月深度集成一个框架，结果它被收购了或者不维护了。选协议不存在这个问题——MCP 有 9700 万月下载，A2A 有 150+ 组织背书，它们持续的时间会比任何一个框架都长。

---

下一章，我们将从"用框架"走向"建平台"——看看那些让 Agent 从开发者工具变成企业产品的平台层能力。
