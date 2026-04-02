# 附录A：术语解释

> **使用说明**：本附录收录全书核心术语,按字母顺序排列。每个术语包含中文对照、定义、首次定义章节和典型使用场景,方便读者快速查阅。

---

## A.1 核心术语表

### Agent（智能代理）

**中文对照**：智能代理 / 智能体

**定义**：一种能够自主感知环境、做出决策并执行行动以达成目标的软件系统。与传统的Chatbot(聊天机器人)不同,Agent是**目标驱动式**的:给它一个目标,它会自主规划步骤、调用工具、处理中间结果和失败,直到达成目标或判断无法完成。

业界也有一个更简洁的工程视角定义（来自 Simon Willison，`datasette` 作者）：

> **"智能体在循环中运行工具以实现目标。"**（Agents run tools in a loop to achieve a goal.）

这个定义抓住了三个核心要素：**循环**（反复迭代直到完成）、**工具**（具备与外部世界交互的能力）、**目标**（不是单轮问答，而是面向结果）。

**首次定义章节**：第00章 前言

**核心特征**：

- 自主性：无需人工干预即可执行任务

- 目标驱动：围绕明确目标展开行动

- 工具调用：具备与外部世界交互的能力

- 状态管理：跨多轮对话和工具调用维护上下文

**典型使用场景**：

- 自动化客户服务系统

- 数据分析与报告生成

- 代码辅助开发

- 复杂业务流程自动化

**相关术语**：Chatbot、LLM、Function Calling、Skill

---

### API（Application Programming Interface，应用程序编程接口）

**中文对照**：应用程序编程接口

**定义**：软件系统之间进行通信的约定和接口。在Agent开发中,API主要指LLM供应商提供的调用接口(如OpenAI API、Claude API等),用于发送Prompt并接收模型响应。

**首次定义章节**：第01章 AI平台和api-key管理

**核心概念**：

- **API Key**：身份认证凭证,用于标识调用者身份和计费

- **Rate Limit**：调用频率限制,防止滥用

- **Endpoint**：API的服务地址

**典型使用场景**：

- 调用OpenAI GPT-4进行对话

- 调用Embedding API生成向量表示

- 调用Whisper API进行语音识别

**注意事项**：

- API Key需安全存储,禁止硬编码在代码中

- 需要处理Rate Limit导致的调用失败

- 建议实现熔断机制防止雪崩效应

**相关术语**：LLM、Context、Token

---

### Chunk（文本分块）

**中文对照**：文本分块 / 文本切片

**定义**：将长文档切分为较小片段的过程,是RAG系统的核心预处理步骤。Chunk的质量直接影响检索效果和生成质量。

**首次定义章节**：第08章 RAG检索增强生成

**核心策略**：

- **固定长度切分**：按字符数或Token数切分,简单但可能破坏语义

- **语义边界切分**：按段落、句子边界切分,保留语义完整性

- **Parent-Child切分**：小块用于检索,大块用于返回上下文

- **AST切分**：针对代码按语法结构(函数、类)切分

**典型参数**：

- `chunk_size`：分块大小(如256、512、1024 tokens)

- `chunk_overlap`：分块重叠区域,避免信息丢失

**使用场景**：

- 构建知识库索引

- 文档问答系统

- 代码仓库分析

**相关术语**：RAG、Embedding、Vector、Token

---

### Context（上下文）

**中文对照**：上下文

**定义**：LLM在一次调用中接收的所有输入信息,包括系统指令、对话历史、检索到的知识库内容和当前用户问题。Context是Agent的"工作记忆",决定了模型对当前任务的理解深度。

**首次定义章节**：第02章 核心交互_Context和Prompt管理

**四大核心要素**：

| 要素 | 层级 | 作用 | 变化频率 |
|------|------|------|----------|
| System Message | 宪法层 | 定义角色、能力边界、输出格式 | 极低 |
| RAG Context | 知识层 | 提供外部知识库检索结果 | 高 |
| History Message | 记忆层 | 维持对话连贯性 | 中 |
| User Message | 触发层 | 用户当前输入 | 极高 |

**上下文窗口**：LLM对Context的最大Token限制(如GPT-4 Turbo为128k tokens)。超出限制需要采用压缩或截断策略。

**管理策略**：

- **滑动窗口**：只保留最近N轮对话

- **摘要压缩**：用LLM总结旧对话

- **动态回溯**：根据相关性动态召回历史信息

**相关术语**：Prompt、Token、Session Memory、RAG

---

### Embedding（嵌入向量）

**中文对照**：嵌入向量 / 向量嵌入

**定义**：将文本、图像等非结构化数据转换为高维稠密向量表示的过程。Embedding向量能捕获语义相似性,使计算机能够理解"苹果"和"水果"在语义上相近。

**首次定义章节**：第08章 RAG检索增强生成

**核心特性**：

- **维度**：向量的长度(如768、1536、3072维)

- **语义距离**：向量间的余弦相似度反映语义相似性

- **多语言支持**：优秀模型支持中英文跨语言检索

**典型模型**：

- OpenAI text-embedding-3-large

- BAAI/bge-m3(开源,支持中英文)

- Cohere embed-v3

**使用场景**：

- RAG检索：将问题和文档转为向量进行相似度匹配

- 聚类分析：将相似文本聚集在一起

- 推荐系统：基于向量相似度推荐相关内容

**代码示例**：

```python
from openai import OpenAI
client = OpenAI()

response = client.embeddings.create(
    model="text-embedding-3-large",
    input="苹果是一种水果"
)
vector = response.data[0].embedding  # 输出: [0.123, -0.456, ...]
```

**相关术语**：Vector、RAG、Chunk、Token

---

### Function Calling（函数调用）

**中文对照**：函数调用 / 工具调用

**定义**：LLM生成结构化JSON以调用外部工具的能力。Function Calling是Agent从"说"到"做"的桥梁,使AI能够查询实时数据、操作数据库、发送邮件等。

**首次定义章节**：第04章 能力扩展_FunctionCalling

**核心原理**：

- **决策与执行分离**：LLM只生成"调用意图",不执行代码

- **标准化定义**：通过JSON Schema描述工具的名称、参数和用途

- **闭环反馈**：执行结果返回给LLM,用于生成最终回复

**生命周期流程**：

```text
用户提问 → LLM决策 → 生成Tool Call JSON →
本地执行 → 返回结果 → LLM生成最终回复
```

**工具定义示例**：

```json
{
  "name": "get_weather",
  "description": "查询指定城市的实时天气",
  "parameters": {
    "type": "object",
    "properties": {
      "city": {
        "type": "string",
        "description": "城市名称,如'北京'"
      }
    },
    "required": ["city"]
  }
}

```

**安全注意事项**：

- 禁止执行任何数据删除操作

- 需要实现参数校验防止幻觉

- 敏感操作需要人工审核

**相关术语**：Agent、Skill、Tool Executor、Context

---

### LLM（Large Language Model，大语言模型）

**中文对照**：大语言模型

**定义**：基于Transformer架构训练的超大规模神经网络,能够理解和生成自然语言文本。LLM是Agent的"大脑",负责推理、规划和生成。

**首次定义章节**：第00章 前言

**核心能力**：

- **自然语言理解**：理解用户意图和上下文

- **文本生成**：生成流畅、连贯的回复

- **推理能力**：进行逻辑推理和问题求解

- **工具调用**：生成结构化的Function Call

**主流模型**：

- OpenAI GPT-4 / GPT-4 Turbo

- Anthropic Claude 3.5 Sonnet

- Google Gemini Pro

- Meta Llama 3

**关键概念**：

- **Token**：文本的最小处理单位

- **Context Window**：单次调用的最大Token数

- **Temperature**：控制输出随机性(0-2)

**使用场景**：

- 对话系统

- 文本生成与摘要

- 代码生成与解释

- 知识问答

**相关术语**：Agent、Token、Context、API

---

### Memory（记忆）

**中文对照**：记忆

**定义**：Agent存储和召回历史信息的能力。根据生命周期和作用范围,分为短期记忆(Session Memory)和长期记忆(Long-term Memory)。

**首次定义章节**：第06章 短期记忆_SessionMemory

**分类**：

| 类型 | 生命周期 | 作用 | 实现方式 |
|------|----------|------|----------|
| **Session Memory** | 会话级 | 维持对话连贯性 | Redis、内存数据库 |
| **Long-term Memory** | 永久 | 跨会话知识保留 | 向量数据库、关系数据库 |

**Session Memory核心设计**：

- 基于角色的消息结构(user/assistant/tool)

- Tool Call配对完整性

- 上下文窗口管理策略

**长期记忆核心设计**：

- 用户隔离

- 数据生命周期管理

- 权限控制

**相关术语**：Context、Token、Session、RAG、Vector

---

### Pipeline（流程编排）

**中文对照**：流程编排 / 管道

**定义**：将多个Agent处理节点按特定逻辑组合成完整工作流的技术。Pipeline是Agent系统的"神经系统",协调各组件有序工作。

**首次定义章节**：第11章 流程编排_Pipeline

**三大基础模式**：

| 模式 | 说明 | 生活类比 |
|------|------|----------|
| **顺序链** | 节点依次执行 | 餐厅后厨:洗菜→切菜→烹饪→装盘 |
| **条件分支** | 根据条件选择路径 | 医院分诊:判断病情→分流科室 |
| **循环迭代** | 重复执行直到满足条件 | 写作:初稿→审阅→修改→定稿 |

**高级架构**：

- **DAG(有向无环图)**：处理复杂依赖关系

- **并行执行**：无依赖节点同时执行

- **人机协作节点**：关键环节插入人工审核

**核心价值**：

- 可观测性：清晰追踪执行链路

- 可控性：在关键节点插入审核

- 鲁棒性：重试和降级机制

**代码示例**：

```python
from langchain.schema.runnable import RunnableParallel

# 并行执行两个独立任务
pipeline = RunnableParallel({
    "news": fetch_news_chain,
    "stocks": fetch_stock_chain
})
result = pipeline.invoke({"topic": "AI"})
```

**相关术语**：Agent、State、ReAct、Plan-and-Execute

---

### Planner（规划器）

**中文对照**：规划器

**定义**：负责将复杂目标拆解为可执行子任务的组件。Planner不执行具体操作,只输出任务列表。

**首次定义章节**：第09章 规划与推理

**核心职责**：

- 任务分解：将大目标拆解为原子任务

- 依赖识别：识别任务间的前置依赖关系

- 顺序安排：确定任务的执行顺序

**工作流程**：

```
用户目标 → Planner分析 → 输出任务列表 → 
Executor执行 → 监控进度 → 动态重规划(可选)

```

**规划粒度控制**：

- **过粗**："赚钱"(无法执行)

- **适中**："收集数据→分析数据→生成报告"

- **过细**："打开浏览器→点击按钮→输入文字"(脆弱)

**最佳实践**：

- 采用分层规划:高层规划宏观步骤,底层Worker执行细节

- 设置重规划触发条件:执行失败或环境变化

- 引入Self-Reflection机制审查规划质量

**相关术语**：ReAct、Executor、Sub-Agent、Self-Reflection

---

### Prompt（提示词）

**中文对照**：提示词

**定义**：发送给LLM的指令文本,用于引导模型生成符合预期的输出。Prompt是人与AI沟通的主要方式,其设计质量直接影响输出质量。

**首次定义章节**：第02章 核心交互_Context和Prompt管理

**核心类型**：

| 类型 | 作用 | 示例 |
|------|------|------|
| **System Prompt** | 定义角色、能力边界 | "你是一名专业的Python开发工程师" |
| **Task Prompt** | 描述具体任务 | "请为以下函数编写单元测试" |
| **Few-shot Prompt** | 提供示例引导输出 | "示例1:输入→输出\n示例2:..." |

**工程化实践**：

- **版本控制**：像管理代码一样管理Prompt

- **A/B测试**：对比不同Prompt效果

- **变量注入**：使用模板引擎动态填充

**代码示例**：

```python
from jinja2 import Template

template = Template("""
你是一名{{role}},专注于{{domain}}。

当前任务:{{task}}
输出格式:{{format}}
""")

prompt = template.render(
    role="数据分析师",
    domain="用户行为分析",
    task="分析用户留存率下降原因",
    format="JSON格式报告"
)

```

**相关术语**：Context、LLM、Token、System Message

---

### RAG（Retrieval-Augmented Generation，检索增强生成）

**中文对照**：检索增强生成

**定义**：结合外部知识库检索和LLM生成的技术架构。RAG通过"先检索相关文档,再让LLM基于文档回答"的方式,解决LLM知识滞后和幻觉问题。

**首次定义章节**：第08章 RAG检索增强生成

**核心流程**：

```text
用户问题 → Embedding向量化 → 向量检索相似文档 →
文档作为Context注入Prompt → LLM基于文档生成回答
```

**四大应用场景**：

| 场景 | 难度 | 核心挑战 |
|------|------|----------|
| 智能客服/FAQ | ⭐ | 口语化匹配 |
| 企业知识库 | ⭐⭐ | 表格切片、权限隔离 |
| 法律合同审查 | ⭐⭐⭐ | 零幻觉、精准引用 |
| 代码仓库分析 | ⭐⭐⭐⭐ | 跨文件依赖、AST解析 |

**进阶技术**：

- **Parent-Child切片**：小块检索、大块返回

- **混合检索+Rerank**：向量+关键词融合

- **AST切片**：按代码语法结构切分

**评估指标**：

- **召回率**：检索到的相关文档占所有相关文档的比例

- **准确率**：检索到的文档中真正相关的比例

- **答案准确性**：生成的答案是否正确

**相关术语**：Embedding、Vector、Chunk、Context、LLM

---

### ReAct（Reason + Act）

**中文对照**：推理-行动循环框架

**定义**：一种经典的Agent规划架构,将"推理"(Reason)和"行动"(Act)交织形成闭环。ReAct通过Thought→Action→Observation三步循环,逐步推进任务完成。

**首次定义章节**：第09章 规划与推理

**核心循环**：

```
Thought(思考): 分析当前状态,规划下一步
↓
Action(行动): 选择工具并生成调用参数
↓
Observation(观察): 获取工具执行结果
↓
(判断是否完成) → 未完成则继续循环

```

**实战案例**：

```
用户: 苹果公司最新股价是多少?买入100股需要多少钱?

[第1轮]
Thought: 需要查询苹果股价,我还没有这个信息
Action: search_stock_ticker(symbol="AAPL")

[第2轮]
Observation: 当前股价178.50美元
Thought: 已获取股价,现在计算总成本
Action: calculator(expression="178.50 * 100")

[第3轮]
Observation: 17850.0
Thought: 已获取所有信息,可以回答了
Final Answer: 苹果公司最新股价是178.50美元,买入100股需要17,850美元

```

**优势**：

- 灵活性强,适合动态场景

- 可解释性好,推理过程透明

**局限**：

- 缺乏全局观,容易在中途偏离目标

- Token消耗大,每次循环都需重新加载历史

- 容易陷入死循环

**相关术语**：Planner、Pipeline、Self-Reflection、Function Calling

---

### Self-Reflection（自我反思）

**中文对照**：自我反思

**定义**：Agent在执行动作后,通过"批评家"角色审查自己的输出,并根据反馈进行修正的能力。Self-Reflection是Agent实现自我进化的关键机制。

**首次定义章节**：第09章 规划与推理

**核心流程**：

```
Draft(初稿) → Critic(批评审查) → Refine(修改完善)

```

**应用场景**：

- **代码生成**：生成代码→检查语法→修正Bug→再次验证

- **SQL生成**：生成SQL→检查语法和性能→优化查询→执行

- **报告写作**：生成初稿→审阅结构和逻辑→修改润色→定稿

**Prompt示例**：

```
[Draft]
生成一段Python代码读取CSV文件并计算平均值

[Critic Prompt]
请以第三视角审查上述代码:

1. 是否处理了文件不存在的异常?

2. 是否处理了数据类型转换异常?

3. 性能是否有优化空间?

[Refine Prompt]
根据批评意见修改代码,确保健壮性和性能

```

**注意事项**：

- 设置最大反思次数,避免无限循环

- 批评Prompt需要明确审查维度

- 需要有明确的"通过标准"

**相关术语**：ReAct、Planner、Self-Evolution

---

### Session Memory（短期记忆）

**中文对照**：短期记忆 / 会话记忆

**定义**：Agent在单次会话期间的临时记忆存储,用于维持对话连贯性。Session Memory类似于计算机的RAM,会话结束后自动清空。

**首次定义章节**：第06章 短期记忆_SessionMemory

**核心特性**：

- **生命周期**：会话级,关闭窗口或超时后清空

- **作用**：解决"前言不搭后语"问题

- **隔离性**：不同用户的Session互不干扰

**消息结构设计**：

```json
{
  "role": "user|assistant|tool|system",
  "content": "消息内容",
  "tool_calls": [{"id": "call_123", "name": "get_weather", "args": {...}}],
  "tool_call_id": "call_123"
}

```

**上下文窗口管理策略**：

- **滑动窗口**：只保留最近N轮

- **摘要压缩**：用LLM总结旧对话

- **混合策略**：System Message + 摘要 + 最近对话

**存储方案**：

- **Redis**：高性能,适合大规模并发

- **内存字典**：简单,适合小规模应用

**代码示例**：

```python
import redis

class SessionMemory:
    def __init__(self, redis_client):
        self.redis = redis_client
    
    def get_messages(self, session_id: str):
        return self.redis.get(f"session:{session_id}")
    
    def add_message(self, session_id: str, message: dict):
        messages = self.get_messages(session_id) or []
        messages.append(message)
        self.redis.set(f"session:{session_id}", messages)

```

**相关术语**：Memory、Context、Token、Session

---

### Skill（技能）

**中文对照**：技能

**定义**：比Function更高维度的抽象,是Agent的业务解决方案。一个Skill可能包含特定的Prompt策略、一系列有序的工具调用、专用知识库资源和状态管理。

**首次定义章节**：第05章 技能体系_AgentSkills定义和组织

**Skill vs Function**：

| 维度 | Function(工具) | Skill(技能) |
|------|----------------|-------------|
| **层级** | 底层原子操作 | 上层业务封装 |
| **示例** | read_file、http_get | analyze_sales_report |
| **复用性** | 通用性强 | 领域性强 |
| **逻辑** | 无状态执行 | 包含推理和流程控制 |
| **生命周期** | 瞬时执行 | 可能包含多轮交互 |

**结构化定义**：

```json
{
  "metadata": {
    "name": "financial_report_generator",
    "display_name": "财务报表生成器",
    "tags": ["finance", "report"],
    "category": "financial-analysis"
  },
  "input_schema": {...},
  "output_schema": {...},
  "tools_required": ["sql_query", "excel_generator"],
  "knowledge_bases": ["kb_financial_regulations"],
  "system_prompt_template": "..."
}

```

**技能管理**：

- **集中式注册表**：统一管理所有技能定义

- **动态发现**：运行时扫描加载新技能

- **语义匹配**：根据任务描述自动匹配最相关技能

**相关术语**：Function Calling、Agent、Prompt、Knowledge Base

---

### SubAgent（子代理）

**中文对照**：子代理 / 子智能体

**定义**：在多智能体系统中,负责执行特定子任务的独立Agent实例。SubAgent通常由主Agent调度和管理,完成特定领域或特定步骤的工作。

**首次定义章节**：第09章 规划与推理

**核心特性**：

- **独立性**：拥有自己的Prompt、工具和记忆

- **专业性**：专注于特定任务领域

- **协作性**：通过消息传递与主Agent或其他SubAgent通信

**应用场景**：

- **代码审查Agent**：专门负责代码质量检查

- **数据分析Agent**：专门负责数据处理和可视化

- **测试Agent**：专门负责生成和执行测试用例

**调度模式**：

- **顺序执行**：SubAgent A完成后,SubAgent B开始

- **并行执行**：多个SubAgent同时工作

- **层级调用**：主Agent调度SubAgent,SubAgent再调度Worker Agent

**注意事项**：

- 需要监控SubAgent执行状态

- 设置超时机制防止阻塞

- 实现结果聚合和错误处理

**相关术语**：Agent、Planner、Multi-Agent、Pipeline

---

### Token（词元）

**中文对照**：词元 / 标记

**定义**：LLM处理文本的最小单位。一个Token可以是一个单词、一个汉字或一个字符片段。Token数量直接影响API调用成本和上下文窗口占用。

**首次定义章节**：第02章 核心交互_Context和Prompt管理

**核心概念**：

- **Tokenization**：将文本切分为Token的过程

- **Token计费**：LLM API按Token数量收费

- **Context Window**：LLM单次调用的最大Token数

**Token vs 字符数估算**：

- **英文**：1 Token ≈ 4个字符 ≈ 0.75个单词

- **中文**：1 Token ≈ 1.5个汉字

- **代码**：1 Token ≈ 2-3个字符

**Token计数工具**：

```python
import tiktoken

encoder = tiktoken.encoding_for_model("gpt-4")
text = "你好,世界!"
token_count = len(encoder.encode(text))  # 输出: 约4-5个Token

```

**成本控制策略**：

- 压缩Prompt,去除冗余信息

- 使用摘要压缩旧对话

- 选择合适模型(大模型贵,小模型便宜)

**相关术语**：Context、LLM、API、Session Memory

---

### Vector（向量）

**中文对照**：向量

**定义**：在LLM语境中,Vector通常指Embedding生成的数值数组,用于表示文本的语义特征。向量间的距离反映文本间的语义相似性。

**首次定义章节**：第02章 核心交互_Context和Prompt管理

**核心概念**：

- **维度**：向量的长度,如768维、1536维

- **余弦相似度**：衡量两个向量方向相似性的指标

- **向量数据库**：专门存储和检索向量的数据库

**相似度计算**：

```python
import numpy as np

def cosine_similarity(vec1, vec2):
    """计算两个向量的余弦相似度"""
    dot_product = np.dot(vec1, vec2)
    norm = np.linalg.norm(vec1) * np.linalg.norm(vec2)
    return dot_product / norm

# 相似度范围: [-1, 1]

# 1表示完全相同, 0表示正交, -1表示完全相反

```

**典型向量数据库**：

- **Milvus**：开源,高性能,适合生产环境

- **Pinecone**：托管服务,易上手

- **Weaviate**：支持混合检索

- **Chroma**：轻量级,适合小规模应用

**使用场景**：

- RAG检索：计算问题向量与文档向量的相似度

- 语义搜索：找到语义相近的文档

- 聚类分析：将相似文本归为一类

**相关术语**：Embedding、RAG、Chunk、Vector Database

---

### MCP (Model Context Protocol，模型上下文协议)

**中文对照**：模型上下文协议

**定义**：由 Anthropic 于 2024 年底发起的开放协议，定义了 AI Agent 如何标准化地连接外部工具、数据源和软件服务。MCP 的核心理念是"工具定义一次，到处可用"——Agent 通过统一接口发现和调用工具，而不需要为每个工具写适配代码。

**首次定义章节**：第04章 能力扩展_FunctionCalling（4.9节）

**核心概念**：

- **MCP Host**：AI Agent 应用，负责决策何时调用工具
- **MCP Client**：协议客户端，管理与 Server 的连接
- **MCP Server**：工具提供者，暴露 Tools、Resources、Prompts
- **Transport**：传输层，支持 stdio（本地）、SSE、Streamable HTTP（远程）

**生态规模**：截至 2026 年初，MCP 累计下载量超过 9700 万次，成为 Agent-to-Tool 领域的事实标准。

**典型使用场景**：

- 让 Claude Desktop 访问本地文件系统、数据库、Git 仓库
- 企业 Agent 通过 MCP Server 连接内部 API
- 开源社区贡献了数百个 MCP Server（GitHub、Slack、Jira 等）

**代码示例**：

```python
# 使用 MCP Python SDK 创建 Server
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("MyServer")

@mcp.tool()
def search_docs(query: str) -> str:
    """搜索内部文档库"""
    return search_internal_db(query)

@mcp.resource("config://app")
def get_config() -> str:
    """读取应用配置"""
    return load_config()
```

**与 Function Calling 的关系**：MCP 不是替代 Function Calling，而是它的"上层标准化"。Function Calling 解决的是"LLM 如何调用工具"，MCP 解决的是"工具如何被标准化发现和接入"。

**相关术语**：Function Calling、A2A、ACP、Tool

---

### A2A (Agent-to-Agent Protocol，智能体间通信协议)

**中文对照**：智能体间通信协议

**定义**：由 Google 于 2025 年 4 月发布的开放协议，定义了不同 AI Agent 之间如何通信、协作和委托任务。如果说 MCP 解决的是"Agent 如何调用工具"，A2A 解决的就是"Agent 如何跟另一个 Agent 说话"。

**首次定义章节**：第10章 多智能体治理（补充内容）

**核心概念**：

- **Agent Card**：Agent 的"名片"，声明自己的能力、接口和可用状态
- **Task**：Agent 之间传递的工作单元
- **Message**：Agent 之间的通信消息格式
- **Artifact**：Agent 产出的结果（文档、代码、数据等）

**典型使用场景**：

- 一个"旅行规划 Agent"调用"酒店预订 Agent"完成住宿安排
- 企业内"客服 Agent"将复杂问题转交给"技术专家 Agent"
- 跨组织的 Agent 协作（如供应商 Agent 与采购 Agent 对接）

**A2A vs MCP 一句话区分**：

> MCP 是 Agent 和工具之间的"USB-C"；A2A 是 Agent 和 Agent 之间的"HTTP"。

**代码示例**：

```json
// Agent Card 示例
{
  "name": "travel-booking-agent",
  "description": "可以查询航班、酒店和租车信息",
  "capabilities": ["search_flights", "book_hotels", "compare_prices"],
  "endpoint": "https://api.example.com/a2a/travel-agent",
  "authentication": "bearer_token"
}
```

**相关术语**：MCP、ACP、Multi-Agent、SubAgent

---

### ACP (Agent Communication Protocol，智能体通信协议)

**中文对照**：智能体通信协议

**定义**：2025-2026 年间涌现的又一 Agent 通信标准，由阿里云等中国科技企业推动。ACP 的目标是提供一个更通用的 Agent 互操作框架，兼容 MCP 和 A2A 的设计理念，同时更强调企业级场景（如权限管理、审计日志、多租户隔离）。

**首次定义章节**：第04章 能力扩展_FunctionCalling（补充内容）

**与 MCP/A2A 的关系**：

| 维度 | MCP | A2A | ACP |
|------|-----|-----|-----|
| **发起方** | Anthropic | Google | 阿里云等中国企业 |
| **核心场景** | Agent-to-Tool | Agent-to-Agent | 企业级 Agent 互操作 |
| **传输方式** | stdio/SSE/HTTP | HTTP | HTTP/gRPC |
| **成熟度** | 最成熟（97M下载） | 快速发展中 | 早期阶段 |

**选型建议**：

- 如果你的 Agent 主要需要调用外部工具 → MCP
- 如果你的 Agent 需要和其他 Agent 协作 → A2A
- 如果你在企业环境，需要权限管理和审计 → 关注 ACP

**相关术语**：MCP、A2A、Multi-Agent

---

### Agentic RAG（智能体化检索增强生成）

**中文对照**：智能体化检索增强生成

**定义**：传统 RAG 是"检索→生成"的线性流程。Agentic RAG 让 Agent 自主决定"需要检索什么""检索结果够不够好""是否需要换关键词再检索"。检索不再是被动的一步操作，而是 Agent 主动规划和迭代的过程。

**首次定义章节**：第08章 RAG检索增强生成（补充内容）

**与传统 RAG 的对比**：

| 维度 | 传统 RAG | Agentic RAG |
|------|---------|-------------|
| **检索策略** | 固定：一次检索 | 动态：Agent 自主决定检索次数和策略 |
| **失败处理** | 检索不到就返回空 | Agent 会换关键词、换检索方式 |
| **复杂度** | 低 | 高（需要 Agent 规划能力） |
| **适用场景** | 简单问答 | 复杂多步查询 |

**一个具体例子**：

用户问："对比一下 2024 年和 2025 年我们公司在 AI 领域的专利数量变化。"

- **传统 RAG**：检索一次，可能找不到"对比"维度的信息
- **Agentic RAG**：Agent 会先检索 2024 年数据，再检索 2025 年数据，然后自己做对比分析。如果某一年数据缺失，Agent 会尝试换关键词再搜。

**相关术语**：RAG、GraphRAG、Corrective RAG、Self-RAG

---

### GraphRAG（图谱检索增强生成）

**中文对照**：图谱检索增强生成

**定义**：由微软在 2024 年提出的 RAG 改进方案。传统 RAG 用向量相似度检索文档片段，GraphRAG 在此基础上增加了知识图谱——先构建文档中的实体关系图，检索时同时利用向量相似度和图谱结构来定位信息。

**首次定义章节**：第08章 RAG检索增强生成（补充内容）

**核心流程**：

```
文档 → 提取实体和关系 → 构建知识图谱
                              ↓
用户问题 → 向量检索 + 图谱遍历 → 更精准的相关片段 → LLM 生成
```

**为什么需要 GraphRAG**：

举个例子。你有一份 200 页的技术文档，里面提到了"张三负责模块 A，李四负责模块 B，模块 A 依赖模块 B"。

- **传统向量 RAG**：搜"张三负责什么"可能找到相关段落，但搜"模块 A 的依赖链"就很难——因为"依赖链"这个词可能根本没出现在文档里
- **GraphRAG**：通过知识图谱可以直接回答"模块 A → 依赖 → 模块 B → 负责人 → 李四"

**适用场景**：

- 需要理解实体间关系的场景（组织架构、技术依赖、供应链）
- 需要回答"全局性问题"（"文档中提到了哪些项目？它们之间有什么关系？"）
- 文档量大且结构复杂的场景

**局限性**：构建知识图谱的成本较高，不适合小型知识库。

**相关术语**：RAG、Agentic RAG、Embedding、Vector

---

### Reason-Plan-ReAct（推理-规划-行动循环）

**中文对照**：推理-规划-行动循环框架

**定义**：2025-2026 年提出的最新 Agent 规划范式，将 ReAct 的"边想边做"和 Plan-and-Execute 的"谋定后动"结合起来。架构分为三层：Reasoner（推理器，理解问题本质）、Planner（规划器，制定执行计划）、ReAct Executor（执行器，按计划执行并反馈）。

**首次定义章节**：第09章 规划与推理（补充内容）

**三层架构**：

```
用户问题 → Reasoner（这是什么类型的问题？）
              ↓
         Planner（需要几步？每步做什么？依赖关系？）
              ↓
         ReAct Executor（逐步执行，遇到问题反馈给 Planner）
              ↓
              ↻ 如果执行失败 → Planner 重新规划 → Executor 再执行
```

**与 ReAct 的对比**：

| 维度 | ReAct | Reason-Plan-ReAct |
|------|-------|-------------------|
| **规划** | 无显式规划，每步临时决定 | 先做全局规划，再逐步执行 |
| **容错** | 失败后可能原地打转 | 失败后触发重新规划 |
| **长程任务** | 容易偏离目标 | 有全局计划约束，不易偏离 |
| **Token 消耗** | 中等 | 较高（多了规划层） |

**一句话理解**：

> ReAct 像"边走边看"，Plan-and-Execute 像"谋定后动"，Reason-Plan-ReAct 则是"先想清楚再边走边调整"。

**相关术语**：ReAct、Plan-and-Execute、Planner、Self-Reflection

---

### Plan-and-Act（规划-执行框架）

**中文对照**：规划-执行框架

**定义**：2025 年提出的长程任务规划改进方案。与 Plan-and-Execute 不同，Plan-and-Act 强调"计划不是一次性的"——执行器在每一步都会反馈环境变化，规划器据此动态调整后续计划。

**首次定义章节**：第09章 规划与推理（补充内容）

**核心改进**：

- **动态重规划**：执行过程中发现新信息时，Planner 会更新计划而不是硬着头皮执行完
- **执行反馈环**：Executor 不只是"照做"，还会告诉 Planner"这一步的实际结果和预期有偏差"
- **子目标分解**：将大目标分解为可验证的子目标，每完成一个就评估是否需要调整方向

**相关术语**：Plan-and-Execute、ReAct、Reason-Plan-ReAct

---

### Extended Context（扩展上下文窗口）

**中文对照**：扩展上下文窗口

**定义**：2025-2026 年间，主流 LLM 供应商大幅扩展了模型的上下文窗口。Claude 3 支持 200K tokens（约 15 万汉字），Gemini 1.5 Pro 支持 1M tokens（约 70 万汉字）。这意味着 Agent 可以一次性"记住"更长的对话历史和更多的参考资料。

**首次定义章节**：第02章 核心交互_Context和Prompt管理（补充内容）

**实际使用建议**：

- **不是越大越好**：大上下文窗口的推理质量在"中间区域"会下降（Lost in the Middle 现象）
- **关键信息放两头**：System Prompt 放最前面，当前问题放最后面，中间放参考资料
- **成本考量**：200K 上下文的调用费用是 4K 的 50 倍，需要评估是否真的需要

**相关术语**：Context、Token、Prompt Caching

---

### Prompt Caching（提示词缓存）

**中文对照**：提示词缓存

**定义**：OpenAI 和 Anthropic 在 2024-2025 年推出的缓存优化技术。当多次调用使用相同或高度相似的 Prompt 前缀时，API 会缓存这部分的计算结果，只对新增内容重新计算。这可以显著降低延迟和成本。

**首次定义章节**：第02章 核心交互_Context和Prompt管理（补充内容）

**实际效果**：

- **成本节省**：缓存命中部分的 token 费用可降低 50%-90%
- **延迟降低**：缓存命中时首 token 延迟从秒级降到毫秒级
- **适用场景**：System Prompt 固定的 Agent（每次调用前缀相同）、批量处理相似文档

**一个真实数据**：

我们有一个客服 Agent，System Prompt 约 3000 tokens，每次用户提问约 100 tokens。开启 Prompt Caching 后，System Prompt 部分几乎每次都命中缓存，整体 API 费用降了约 70%。

**注意事项**：缓存有有效期（通常几分钟到几小时），且不同供应商的缓存策略不同。

**相关术语**：Context、Token、Extended Context

---

### Structured Outputs（结构化输出）

**中文对照**：结构化输出

**定义**：OpenAI 在 2024 年推出的功能，允许开发者通过 JSON Schema 严格约束 LLM 的输出格式。与早期的 JSON Mode 不同，Structured Outputs 保证输出不仅"是 JSON"，而且"完全符合你定义的 Schema"——字段齐全、类型正确、枚举值合法。

**首次定义章节**：第03章 模型数据与格式化管理（补充内容）

**与 JSON Mode 的对比**：

| 维度 | JSON Mode | Structured Outputs |
|------|-----------|-------------------|
| **保证** | 输出是合法 JSON | 输出符合指定 JSON Schema |
| **字段** | 可能缺失字段 | 保证所有必填字段存在 |
| **类型** | 可能类型错误 | 类型严格校验 |
| **适用模型** | 所有支持 JSON Mode 的模型 | 仅 GPT-4o 及更新模型 |

**相关术语**：Function Calling、JSON Mode、Pydantic

---

## A.2 术语使用规范

### 中英文混用标准

为保持全书术语一致性,建议遵循以下规范:

| 英文术语 | 中文对照 | 推荐用法 |
|---------|---------|---------|
| Agent | 智能代理 | 首次出现用"Agent(智能代理)",后续直接用Agent |
| Context | 上下文 | 首次出现用"Context(上下文)",后续视上下文选择 |
| Prompt | 提示词 | 直接使用Prompt |
| Token | 词元 | 首次出现用"Token(词元)",后续直接用Token |
| Embedding | 嵌入向量 | 直接使用Embedding |
| Vector | 向量 | 技术描述用Vector,通俗解释用向量 |
| Function Calling | 函数调用 | 首次出现用英文+中文,后续用Function Calling |
| RAG | 检索增强生成 | 首次出现用"RAG(检索增强生成)",后续用RAG |

### 术语分类索引

**核心概念类**：

- Agent, LLM, API, Token

**交互与记忆类**：

- Context, Prompt, Memory, Session Memory

**能力扩展类**：

- Function Calling, Skill, SubAgent

**知识管理类**：

- RAG, Embedding, Vector, Chunk

**规划与编排类**：

- ReAct, Planner, Pipeline, Self-Reflection

---

## A.3 快速查找表

### 按字母顺序索引

| 字母 | 术语 |
|------|------|
| **A** | Agent, API |
| **C** | Chunk, Context |
| **E** | Embedding |
| **F** | Function Calling |
| **L** | LLM |
| **M** | Memory |
| **P** | Pipeline, Planner, Prompt |
| **R** | RAG, ReAct |
| **S** | Self-Reflection, Session Memory, Skill, SubAgent |
| **T** | Token |
| **V** | Vector |

### 按章节索引

| 章节 | 核心术语 |
|------|----------|
| 第00章 前言 | Agent, LLM |
| 第01章 AI平台管理 | API, Token |
| 第02章 Context与Prompt | Context, Prompt, Token |
| 第04章 Function Calling | Function Calling, Agent, LLM |
| 第05章 技能体系 | Skill, Function Calling |
| 第06章 短期记忆 | Session Memory, Token, Context |
| 第08章 RAG | RAG, Embedding, Vector, Chunk |
| 第09章 规划与推理 | ReAct, Planner, Self-Reflection, SubAgent |
| 第11章 流程编排 | Pipeline, Agent, State |

---

## A.4 参考资源

### 官方文档

- [OpenAI API Documentation](https://platform.openai.com/docs)

- [Anthropic Claude Documentation](https://docs.anthropic.com)

- [LangChain Documentation](https://python.langchain.com/docs)

### 学术论文

- **ReAct**: "ReAct: Synergizing Reasoning and Acting in Language Models" (Yao et al., 2022)

- **RAG**: "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks" (Lewis et al., 2020)

- **Chain-of-Thought**: "Chain-of-Thought Prompting Elicits Reasoning in Large Language Models" (Wei et al., 2022)

### 开源项目

- **LangChain**: Agent开发框架

- **LlamaIndex**: RAG专用框架

- **AutoGPT**: 自主Agent实验项目

- **Milvus**: 开源向量数据库

---

**版本信息**：

- 附录版本：v1.0

- 最后更新：2026-03-20

- 收录术语：17个核心术语

**使用建议**：

1. 初次阅读时浏览A.1节了解核心概念

2. 阅读正文时遇到陌生术语可快速查阅

3. 通过A.3快速查找表定位术语定义章节
