# 附录A：术语解释

> **使用说明**：按字母顺序排列，每条术语包含中文对照和简要定义。正文中首次出现的术语均有脚注指向本附录。

---

## A.1 核心术语表

### A2A（Agent-to-Agent Protocol）

**中文**：Agent 间通信协议

Google 主导的开放协议，标准化不同 Agent 之间的能力发现、任务委托和结果传递。核心技术组件是 Agent Card——类似 `.well-known/agent.json`，让 Agent 通过网络声明自己的能力和接口。与 MCP 的分工：MCP 解决"模型↔工具"，A2A 解决"Agent↔Agent"。

**相关术语**：MCP、ACP、ARD、Agent Card

**首次定义章节**：第12章 生态工具

---

### ACP（Agent Communication Protocol）

**中文**：Agent 通信协议（IBM）

IBM 推出的企业级 Agent 通信标准，采用经典 REST + Webhook 架构。特色在于命名空间和会话 ID 体系，适合传统企业 IT 架构的运维和审计要求。2026 年 5 月迭代至 v0.3。

**相关术语**：A2A、MCP

**首次定义章节**：第12章 生态工具

---

### ARD（Agentic Resource Discovery）

**中文**：Agent 资源发现协议

Google + Microsoft + Hugging Face + GoDaddy 联合推动的开放协议，解决 Agent 如何自动发现可用资源的问题。核心机制：Well-Known URI 静态发布 AI Catalog 清单 → Registry 构建语义向量索引 → 编排 Agent 通过自然语言搜索发现资源 → 联邦搜索跨 Registry 联合查询。v0.9 于 2026 年 6 月发布。三层协议栈分工：ARD（发现层，回答"有什么可用"）→ A2A（协作层，回答"怎么委托任务"）→ MCP（执行层，回答"怎么调工具"）。

**相关术语**：A2A、MCP、AI Catalog、Well-Known URI、URN

**首次定义章节**：第12章 生态工具

---

### Agent（智能代理）

**中文**：智能代理 / 智能体

自主感知环境、做出决策并执行行动以达成目标的软件系统。与 Chatbot 的关键区别：目标驱动而非对话驱动。工程视角的简洁定义——"Agent 在循环中运行工具以实现目标"（Simon Willison）。

**核心特征**：自主性、工具调用、状态管理、目标导向

**相关术语**：LLM、Function Calling、Skill、Agentic Loop

**首次定义章节**：第00章 前言

---

### Agentic Loop（Agent 循环）

**中文**：Agent 循环

Agent 运行的核心模式：收集上下文 → 规划行动 → 执行工具 → 观察结果 → 判断是否完成（未完成则继续循环）。这是区分 Agent 和普通 LLM 调用的关键——Agent 不是单轮问答，而是多轮迭代直到完成任务。

**相关术语**：Agent、ReAct、Harness

**首次定义章节**：第13章 Harness 与 Loop 工程化

---

### AI Catalog（AI 资源目录）

**中文**：AI 资源目录

ARD 协议定义的标准资源清单格式。每个提供者在自己的域名下通过 Well-Known URI（`/.well-known/ai-catalog.json`）发布，列出该域下所有可被 Agent 发现的资源。条目包含：URN 标识符、资源类型、访问 URL、能力描述、代表性查询示例（用于语义搜索的种子向量）。支持四种发现入口：DNS SVCB 记录、Well-Known URI、robots.txt Agentmap 指令、HTML `<link>` 标签。

**相关术语**：ARD、Well-Known URI、URN、A2A

**首次定义章节**：第12章 生态工具

---

### API（Application Programming Interface）

**中文**：应用程序编程接口

在 Agent 开发语境下，通常指 LLM 供应商的调用接口（OpenAI API、Claude API 等）。核心概念：API Key（身份凭证）、Rate Limit（频率限制）、Endpoint（服务地址）。API Key 禁止硬编码，需通过环境变量或密钥管理服务加载。

**相关术语**：LLM、Token、Prompt Caching

**首次定义章节**：第01章 AI 平台管理

---

### Chain-of-Thought（CoT，思维链）

**中文**：思维链

通过提示（如"Let's think step by step"）引导模型输出中间推理步骤的技术。2026 年，推理模型已内置 CoT，无需手动写提示词——设置 `reasoning_effort` 参数即可控制推理深度。CoT 仍适用于非推理模型（如 GPT-4o、Claude Sonnet）。

**相关术语**：Reasoning Model、ReAct、Tree of Thoughts

**首次定义章节**：第09章 规划与推理

---

### Chunk（文本分块）

**中文**：文本分块 / 文本切片

将长文档切分为小段的过程，是 RAG 系统的核心预处理步骤。切分策略：固定长度（最简单但破坏语义）、语义边界（按段落/句子）、Parent-Child（小块检索、大块返回上下文）、AST（代码按函数/类切分）。核心参数：`chunk_size` 和 `chunk_overlap`。

**相关术语**：RAG、Embedding、Vector

**首次定义章节**：第08章 RAG

---

### Context Engineering（上下文工程）

**中文**：上下文工程

Prompt Engineering 的继任者——不是只设计一段提示词，而是系统化设计整个上下文窗口的全部内容：系统指令、检索片段、工具定义、记忆、对话历史。2026 年行业共识：Context Engineering > Prompt Engineering。

**相关术语**：Context、Prompt、RAG、Memory

**首次定义章节**：第02章 Context 和 Prompt 管理

---

### Context（上下文）

**中文**：上下文

LLM 在一次调用中接收的全部输入信息。四大要素分层：System Message（宪法层，定义角色）、RAG Context（知识层，外部检索）、History Message（记忆层，对话连贯性）、User Message（触发层，当前输入）。上下文窗口是硬限制——2026 年主流 200K tokens，但窗口大不等于有效注意力大。

**相关术语**：Context Window、Context Engineering、Prompt Caching

**首次定义章节**：第02章 Context 和 Prompt 管理

---

### Durable Execution（持久执行）

**中文**：持久执行

运行时模式——工作流每执行一步就建立检查点（checkpoint），使系统能承受崩溃、重启和长时间暂停后在中断点恢复。Temporal 是这一模式的工业标准实现。与传统无状态调用的区别：类似数据库事务的耐久性保证。

**相关术语**：Agentic Loop、Pipeline

**首次定义章节**：第11章 流程编排

---

### Embedding（嵌入向量）

**中文**：嵌入向量 / 向量嵌入

将文本、图像等非结构化数据转换为高维稠密向量的过程。Embedding 的核心价值：语义相近的文本在向量空间中距离近。2026 年主流模型：OpenAI text-embedding-3-large（1536维）、BAAI/bge-m3（开源，中英文）。

**相关术语**：Vector、RAG、Chunk、Semantic Search

**首次定义章节**：第08章 RAG

---

### Function Calling（函数调用 / Tool Use）

**中文**：函数调用 / 工具调用

LLM 生成结构化 JSON（而非自然语言）以调用外部工具的能力。这是 Agent 从"说"到"做"的桥梁。核心原理：决策与执行分离——LLM 只生成调用意图，宿主程序负责实际执行。2026 年，各主要模型的结构化 Function Calling 已经很可靠，不再需要手写 JSON 修复逻辑。

**相关术语**：Agent、Skill、MCP、Structured Output

**首次定义章节**：第04章 Function Calling

---

### Harness / Scaffolding（编排层 / 脚手架）

**中文**：编排层 / 脚手架

包裹在 LLM 外层的提示策略、工具连接、控制流和记忆管理。Agent = Model + Harness。Harness 负责循环控制、状态管理、错误处理和资源调度——模型只管"思考"，Harness 管"怎么做"。

**相关术语**：Agent、Agentic Loop、Pipeline

**首次定义章节**：第13章 Harness 与 Loop 工程化

---

### LLM（Large Language Model，大语言模型）

**中文**：大语言模型

基于 Transformer 架构训练的超大规模神经网络，是 Agent 的"大脑"。2026 年市场格局：OpenAI GPT-5.4、Anthropic Claude Sonnet 4.6、Google Gemini 2.5 Pro、DeepSeek V4 作为主流选项。推理模型（o3/o4-mini、Claude Opus 4.6）是新增类别——在回答前进行深度推理，不适用于实时交互。

**核心概念**：Token、Context Window、Temperature、流式输出

**相关术语**：Agent、Reasoning Model、Prompt Caching

**首次定义章节**：第00章 前言

---

### MCP（Model Context Protocol，模型上下文协议）

**中文**：模型上下文协议

Anthropic 开源的 JSON-RPC 2.0 协议，标准化 LLM 与外部工具和数据源的连接方式。截至 2026 年 7 月，MCP 生态达 9700 万月下载量、17,468 个 Server。传输层：Streamable HTTP（2025年3月取代 HTTP+SSE）。与 A2A 的分工：MCP = 模型↔工具，A2A = Agent↔Agent。

**相关术语**：A2A、ACP、Function Calling、Tool Use

**首次定义章节**：第12章 生态工具

---

### Memory（记忆）

**中文**：记忆

Agent 存储和召回历史信息的能力。按生命周期分：Short-term Memory（会话级，维持对话连贯性，通常存 Redis/内存）、Long-term Memory（跨会话持久化，存向量数据库/关系数据库）、Working Memory（上下文窗口内的即时信息）。2026 年工具链：Mem0、Letta、LangMem、Memobase 提供开箱即用的记忆管理。

**相关术语**：Context、RAG、Vector、Embedding

**首次定义章节**：第06章 短期记忆 / 第07章 长期记忆

---

### Pipeline（流程编排）

**中文**：流程编排 / 管道

将多个处理节点按逻辑组合成完整工作流的技术。三种基础模式：顺序链（依次执行）、条件分支（根据结果选择路径）、循环迭代（重复直到满足条件）。2026 年主推方案：LangGraph + Temporal（Durable Agent 双栈架构），替代手写 Pipeline 引擎。

**相关术语**：Agent、Durable Execution、ReAct

**首次定义章节**：第11章 流程编排

---

### Planner（规划器）

**中文**：规划器

负责将复杂目标拆解为可执行子任务的组件。Planner 不执行操作，只输出任务列表。2026 年，推理模型极大地提升了规划能力——模型内部在进行某种形式的隐式规划，不再需要手动写"Plan-and-Execute"提示模板。

**相关术语**：ReAct、Reasoning Model、SubAgent

**首次定义章节**：第09章 规划与推理

---

### Prompt Caching（提示缓存）

**中文**：提示缓存

重用已处理的提示前缀来降低成本和延迟的机制。长期静态内容（系统指令、工具定义、知识库上下文）放在 Prompt 前部，会被自动缓存；动态对话放在后部。缓存命中成本约为标准输入的 10%。Anthropic Claude 和 OpenAI 均支持，实现方式有差异。

**相关术语**：Context、LLM、Prompt

**首次定义章节**：第01章 AI 平台管理 / 第02章 Context 管理

---

### Prompt（提示词）

**中文**：提示词

发送给 LLM 的指令文本。核心类型：System Prompt（定义角色和能力边界）、Task Prompt（描述具体任务）、Few-shot Prompt（通过示例引导输出）。工程化要求：版本控制（像管理代码一样管理 Prompt）、A/B 测试、模板变量注入。2026 年趋势：从"写 Prompt"到"设计 Context"。

**相关术语**：Context Engineering、LLM、Context

**首次定义章节**：第02章 Context 和 Prompt 管理

---

### RAG（Retrieval-Augmented Generation，检索增强生成）

**中文**：检索增强生成

结合外部知识库检索和 LLM 生成的技术架构。核心流程：用户问题 → Embedding 向量化 → 向量检索相似文档 → 注入 Context → LLM 生成回答。四代演进：朴素 RAG → 高级 RAG → Agentic RAG → 多模态 RAG。2026 年，Adaptive RAG 和 Self-RAG 已成熟，Agent 根据问题复杂度动态选择检索策略。

**相关术语**：Embedding、Vector、Chunk、Context

**首次定义章节**：第08章 RAG

---

### ReAct（Reason + Act，推理-行动）

**中文**：推理-行动循环

经典的 Agent 推理架构：Thought（分析当前状态）→ Action（选择工具并执行）→ Observation（观察结果）→ 循环直到完成。2026 年实践中，推理模型正在淡化显式 ReAct——模型内部的推理步骤隐式包含了 ReAct 的"思考-行动"逻辑。

**相关术语**：Agent、Planner、Reasoning Model、Agentic Loop

**首次定义章节**：第09章 规划与推理

---

### Reasoning Model（推理模型）

**中文**：推理模型

在回答前进行深度链式推理的 LLM 子类别。代表模型：OpenAI o3/o4-mini、DeepSeek R1-0528、Claude Opus 4.6（extended thinking）。通过 `reasoning_effort` 或 `thinking budget` 参数控制推理深度。核心权衡：推理质量 vs 延迟和成本。不适用于实时交互场景。

**相关术语**：LLM、Chain-of-Thought、Planner

**首次定义章节**：第09章 规划与推理

---

### Reflexion（自我反思）

**中文**：自我反思 / 反省

Agent 在执行动作后，通过"批评家"角色审查自己的输出并修正的机制。不同于 Self-Reflection 的一次性审视，Reflexion 强调"试错-反思-重试"的完整循环。核心流程：Draft（初稿）→ Critic（评估）→ Refine（修正）。需要设置最大反思次数防止死循环。

**相关术语**：ReAct、Self-Reflection、Planner

**首次定义章节**：第09章 规划与推理

---

### SKILL.md（技能文件）

**中文**：技能文件

2026 年行业标准的 Agent 技能定义格式。自包含的 Markdown 文件，包含技能的触发条件、执行步骤、工具需求和知识库引用。Agent 框架（如 Claude Code、WorkBuddy）按需加载 Skill，而非在 System Prompt 中塞入全部定义。核心优势：渐进式披露——Agent 只在需要时看到相关指令。

**相关术语**：Skill、Agent、Context Engineering

**首次定义章节**：第05章 技能体系

---

### Structured Output（结构化输出）

**中文**：结构化输出

LLM 直接输出符合预定义 JSON Schema 的结果，而非自然语言后解析。2026 年，各主要模型均已原生支持（OpenAI `response_format`、Anthropic `tool_choice`、Google Gemini `response_schema`）。不再需要手写 JSON 解析器或修复逻辑。

**相关术语**：Function Calling、LLM

**首次定义章节**：第03章 模型数据与格式化管理

---

### SubAgent（子代理）

**中文**：子代理 / 子智能体

在多 Agent 系统中，由父 Agent 生成的、拥有独立上下文窗口和工具预算的子进程。典型场景：父 Agent 规划任务后，生成专业化 SubAgent 分别执行搜索、编码、测试等子任务。调度模式：顺序、并行、层级调用。与 Skill 的区别：Skill 是加载到父上下文的文件（共享 token 预算），SubAgent 是独立进程（独立预算）。

**相关术语**：Agent、Planner、Skill

**首次定义章节**：第10章 多智能体治理

---

### Token（词元）

**中文**：词元

LLM 处理文本的最小单位。直接影响 API 调用成本和上下文窗口占用。中文约 1 Token ≈ 1.5 汉字，英文约 1 Token ≈ 4 字符。成本控制策略：Prompt Caching（缓存命中降成本 90%）、选择合适的模型、用摘要压缩旧对话。

**相关术语**：Context、Context Window、LLM

**首次定义章节**：第02章 Context 和 Prompt 管理

---

### URN（Uniform Resource Name）

**中文**：统一资源名称

ARD 协议定义的 Agent 资源全局唯一标识符。格式：`urn:air:<publisher>:<namespace>:<agent-name>`。核心设计意图：逻辑身份与物理位置解耦——Agent 迁移域名不影响 URN 标识；FQDN 作为组织信任锚点——域名所有权天然验证归属；联邦合并无碰撞——不同组织的同名 Agent 自动区分。示例：`urn:air:salesforce.com:crm:lead-enrichment`。

**相关术语**：ARD、AI Catalog、Well-Known URI

**首次定义章节**：第12章 生态工具

---

### Vector（向量）

**中文**：向量 / 嵌入向量

文本语义的数值数组表示。向量间的余弦相似度反映语义相似性。2026 年主流向量数据库：Milvus（开源高性能）、Pinecone（托管服务）、Qdrant（Rust 实现）、Chroma（轻量级）。混合检索（向量 + BM25 关键词）加 Rerank 是生产环境的标配方案。

**相关术语**：Embedding、RAG、Chunk、Semantic Search

**首次定义章节**：第08章 RAG

---

### Well-Known URI（公认统一资源标识符）

**中文**：公认 URI / 知名 URI

Web 基础设施标准（RFC 8615），在域名的 `/.well-known/` 路径下发布站点级元数据的约定。ARD 协议利用此机制——每个 Agent 提供者在 `https://{domain}/.well-known/ai-catalog.json` 发布资源清单，使 Registry 能通过域名自动发现资源。不需要中心化注册中心，分布式的域名体系本身就是发现基础设施。

**相关术语**：ARD、AI Catalog、URN

**首次定义章节**：第12章 生态工具

---

## A.2 术语中英文使用规范

| 英文 | 首次出现 | 后续使用 |
|:---|:---|:---|
| Agent | Agent（智能代理） | Agent |
| MCP | MCP（模型上下文协议） | MCP |
| A2A | A2A（Agent 间通信协议） | A2A |
| ARD | ARD（Agent 资源发现协议） | ARD |
| AI Catalog | AI Catalog（AI 资源目录） | AI Catalog |
| URN | URN（统一资源名称） | URN |
| RAG | RAG（检索增强生成） | RAG |
| ReAct | ReAct（推理-行动） | ReAct |
| Embedding | Embedding（嵌入向量） | Embedding |
| Token | Token（词元） | Token |
| Prompt | Prompt（提示词） | Prompt |

原则：首次出现标注中英文，后续直接用英文简称。不强行翻译已约定俗成的术语。

---

## A.3 快速索引

### 按字母

A: Agent, Agentic Loop, A2A, ACP, AI Catalog, API, ARD
C: Chain-of-Thought, Chunk, Context, Context Engineering
D: Durable Execution
E: Embedding
F: Function Calling
H: Harness / Scaffolding
L: LLM
M: MCP, Memory
P: Pipeline, Planner, Prompt, Prompt Caching
R: RAG, ReAct, Reasoning Model, Reflexion
S: SKILL.md, Structured Output, SubAgent
T: Token
U: URN
V: Vector
W: Well-Known URI

### 按章节

| 章节 | 首次定义的术语 |
|:---|:---|
| 00 前言 | Agent, LLM |
| 01 AI 平台管理 | API, Prompt Caching |
| 02 Context 与 Prompt | Context, Context Engineering, Prompt, Token |
| 03 模型数据与格式化 | Structured Output |
| 04 Function Calling | Function Calling |
| 05 技能体系 | SKILL.md |
| 06-07 记忆 | Memory |
| 08 RAG | Chunk, Embedding, RAG, Vector |
| 09 规划与推理 | Chain-of-Thought, Planner, ReAct, Reasoning Model, Reflexion |
| 10 多智能体治理 | SubAgent |
| 11 流程编排 | Durable Execution, Pipeline |
| 12 生态工具 | A2A, ACP, ARD, AI Catalog, URN, Well-Known URI, MCP |
| 16 Harness 与 Loop | Agentic Loop, Harness / Scaffolding |
