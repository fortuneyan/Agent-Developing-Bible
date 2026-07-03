# 第十一章 流程编排——Pipeline 编排

本章不讲怎么从零手写编排引擎。2026 年，编排已经从"拼积木"变成了"选预构件"——问题不再是"怎么搭 Pipeline"，而是"该选哪种 Pipeline"。我们会对比三种编排范式的适用场景，讲解 LangGraph + Temporal 双栈架构（2026 年金标准），并给你一个从单次调用到持久编排的六阶梯选型决策树。

## 11.1 引言：编排的民主化

如果你在 2024 年写 Agent，编排是你的全部工作——定义 Node 类、写 Pipeline 引擎、手动管理状态流转。今天再看那些代码会有点恍惚，就像看到有人用汇编写 Web 服务。

2026 年，编排已不是你要解决的问题，而是你要做的**选择**。LangGraph 的 `StateGraph` 内建了图编译、检查点持久化、条件路由、人机协作暂停——你不需要手写 Pipeline 类，只需要定义节点和边。Temporal 提供了基础设施级的持久执行保证——工作流可以在崩溃后从第 7 步恢复，不需要你自己实现恢复逻辑。

但这带来了一个新问题：**框架太多，选型反而更难了**。本章帮你理清这个问题。

## 11.2 三种编排范式速览

Agent 编排不是只有 DAG 一种方式。2026 年有三种主流范式，它们的适用场景差异很大。

### DAG：确定性的流水线

**核心理念**：预定义执行计划。节点是任务，边是依赖关系。调度器自动并行化独立分支。

- **优势**：确定性（相同输入 = 相同执行顺序）、成熟的工具链（Airflow/Dagster/Prefect 数十年的积累）、强可观测性（DAG UI 直观展示失败节点）
- **局限**：无法原生表达循环和回溯（这是 Agent 推理的核心模式）

**适用**：批处理管道、ML 训练、带 AI 的 ETL。

### 事件驱动：响应的生态系统

**核心理念**：Agent 是事件的消费者。每个 Agent 动作产生事件，事件触发更多动作。工作流从事件拓扑中**涌现**，而非预先声明。

- **优势**：天然解耦（生产者和消费者互不知晓）、实时处理、事件日志提供完整审计
- **局限**：理解系统行为需要理解整个事件拓扑（任何单个组件看不到全局）、延迟开销、静默消费者崩溃

**适用**：欺诈检测、实时威胁分析、安全事件响应系统。Elastic Security 使用 Kafka + 事件驱动，每个安全事件触发并行专家 Agent，事件日志提供完整审计轨迹。

### Actor 模型：隔离的有状态实体

**核心理念**：每个 Actor 拥有私有状态、邮箱和行为函数。通过消息传递通信，通过监督树实现故障恢复。起源于 Erlang/OTP。

- **优势**：故障隔离（一个 Actor 崩溃不影响其他）、位置透明（跨进程/跨机器消息传递 API 一致）、自然并发（无共享状态竞争）
- **局限**：认知模型转变（习惯同步调用会觉得陌生）、简单管线有额外开销

**适用**：需要复杂生命周期管理的长存活 Agent、需要极端容错的分布式系统。

### 决策指南

| 问题 | 答案 → 范式 |
|------|----|
| 拓扑预先已知且固定？ | → DAG |
| Agent 需要对实时事件做出反应？ | → 事件驱动 + Kafka |
| Agent 需要隔离的复杂私有状态？ | → Actor 模型（MAF/Akka） |
| LLM 动态生成执行计划？ | → LangGraph（动态拓扑） |

> **关键洞察**：三种范式不是互斥的。生产系统经常混用——LinkedIn AI 招聘用 LangGraph（DAG 层）+ Kafka（事件通知）+ Temporal（持久化）。

## 11.3 Durable Agent：LangGraph + Temporal 双栈

这是 2026 年最重要的编排模式。核心思想很简单：**LangGraph 负责"Agent 怎么思考"，Temporal 负责"执行怎么活下来"**。

### 为什么需要持久执行？

假设你的 Agent 做以下操作：
1. 调用 LLM 分析需求（30s）
2. 调用三个外部 API 获取数据（2min）
3. 再调用 LLM 综合分析（1min）
4. 把结果写入数据库（5s）

如果 Agent 进程在第 3 步崩溃了——步骤 1-2 的工作全部丢失。普通的 `try/except` 无法解决这个问题（进程没了，try/except 也没了）。这就是 **Durable Execution** 的核心场景。

### 双栈分工

| 层次 | 职责 | 技术 |
|------|------|------|
| **内层推理** | 图式 Agent 逻辑、条件路由、LLM 调用编排 | **LangGraph** |
| **外层持久** | 崩溃恢复、超时重试、Saga 补偿、分布式协调 | **Temporal** |

直观比喻：Temporal 确保火车不脱轨、一定到达目的地；LangGraph 处理每节车厢内部乘客怎么上下车。

### 代码骨架

**内层（LangGraph）**：定义 Agent 的推理图。

```python
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

class AgentState(TypedDict):
    input: str
    analysis: str
    decision: str

builder = StateGraph(AgentState)
builder.add_node("analyze", analyze_node)
builder.add_node("decide", decide_node)
builder.add_edge(START, "analyze")
builder.add_conditional_edges("analyze", route_function,
    {"approved": "decide", "rejected": END})
builder.add_edge("decide", END)

graph = builder.compile(checkpointer=PostgresSaver.from_conn_string(DB_URL))
```

**外层（Temporal）**：把 LangGraph Agent 包装为 Temporal Activity，获得崩溃恢复和超时重试。

```python
@activity.defn
async def run_agent(input: str) -> dict:
    return graph.invoke({"input": input},
        config={"configurable": {"thread_id": task_id}})

@workflow.defn
class AgentWorkflow:
    @workflow.run
    async def run(self, input: str) -> str:
        result = await workflow.execute_activity(
            run_agent, input,
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=RetryPolicy(maximum_attempts=3),
        )
        return result["decision"]
```

### 什么时候加 Temporal？

cordum.io 给出了四个硬指标：

| 条件 | 是否加 Temporal |
|------|:--:|
| 单步执行 < 30s，只读 | LangGraph 够用 |
| 3 个以上外部调用 | 加 Temporal |
| 需要暂停等待数小时/天的人工审核 | 必须加 Temporal |
| 涉及副作用（支付/删除/部署/发消息） | 必须加 Temporal + 安全门控 |

## 11.4 LangGraph 核心概念速览

即使不引入 Temporal，LangGraph 本身的四个概念也值得掌握。

### StateGraph：图即流程

定义节点（函数）和边（流转关系）。`StateGraph` 替代了你手写的 `Pipeline + Node + Router` 三件套。

- `add_node("name", function)`：注册节点
- `add_edge(A, B)`：A 完成后必然走 B
- `add_conditional_edges(A, router, mapping)`：A 完成后根据 router 返回值走不同路径

### Checkpointer：状态持久化

每次节点执行后自动保存状态快照。进程崩溃后，用相同的 `thread_id` 调用即可从断点恢复。

生产环境唯一推荐 `PostgresSaver`（不用 `InMemorySaver`，重启就没了）。单次任务 TTL 设 24-48 小时，对话式设基于 session 过期时间。

### 条件路由：Agent 的选择权

条件路由是编排与代码的区别所在——不是 `if/else`，而是让 LLM 判断该走哪条路。

```python
def route_after_analysis(state: AgentState) -> str:
    # LLM 判断走哪条路径
    return "needs_research" if state["confidence"] < 0.7 else "generate_report"
```

### Human-in-the-Loop：在关键节点插入人类判断

不是代码里设一个 `asyncio.Event` 等着（这只能单进程用），而是通过 LangGraph 的 `interrupt` API：

```python
# 在任何节点前设置断点
graph = builder.compile(
    checkpointer=PostgresSaver.from_conn_string(DB_URL),
    interrupt_before=["approval_node"],  # 在此节点前暂停
)

# 人工审核后，通过相同 thread_id 恢复执行
graph.invoke(None, config={"configurable": {"thread_id": task_id}})
```

流程暂停 → 状态持久化到 Postgres → 发送通知 → 人工决策 → API 恢复执行。即使 Agent 服务重启，审核也不会丢失。

## 11.5 编排选型决策树

这是本章最实用的一节。问自己两个问题：

### 问题一：单任务的执行时间？

| 执行时间 | 编排方案 |
|------|------|
| < 30s | 简单 ReAct 循环即可，不需要编排框架 |
| 30s – 10min | LangGraph + PostgresSaver |
| 10min – 数小时 | LangGraph + Temporal |
| 数小时 – 数天 | Temporal（持久执行是必需品） |

### 问题二：拓扑是预先已知的吗？

| 拓扑特征 | 编排方案 |
|------|------|
| 已知且固定 | DAG（Dagster/Prefect/Airflow） |
| 已知但需迭代 | LangGraph 状态机 |
| LLM 动态生成 | Temporal + 动态拓扑 |

**实际生产的典型选择**：
- **简单 Agent**（单步问答/单工具调用）：不需要编排框架
- **中等复杂 Agent**（多步推理/多工具调用，分钟级）：LangGraph
- **复杂 Agent**（跨服务/小时级/有人工审核）：LangGraph + Temporal
- **Microservice Agent 网格**（实时响应/多服务协调）：Kafka + 事件驱动

## 11.6 生产核心模式速览

### 幂等性：最重要的一个模式

LLM 调用是非确定性的，重试意味着重复计费。用输入哈希做幂等键：

```python
import hashlib

cache_key = hashlib.sha256(prompt.encode()).hexdigest()
if cached := cache.get(cache_key):
    return cached
result = llm.generate(prompt)
cache.set(cache_key, result, ttl=3600)
```

### Checkpoint 配置

- 后端：`PostgresSaver`
- TTL：单次任务 24-48h，对话式按 session 过期时间
- 状态压缩：大文件存 S3，状态中只放引用 URI

### Saga 补偿

不是"要么全成要么全无"的 ACID 事务，而是"失败了按逆序撤销"。

```
步骤1: 创建数据库记录 → 注册补偿: 删除记录
步骤2: 发送通知      → 注册补偿: 撤回通知
步骤3: 触发部署      → 注册补偿: 回滚部署
步骤3 失败 → 逆序执行: 撤回通知 → 删除记录
```

### Human-in-the-Loop 分级

| 风险等级 | 审批策略 |
|------|------|
| 低（内部读取） | 无需审批 |
| 中（修改内部数据） | 自动执行 + 事后审计 |
| 高（外部通知/部署） | 人工审批 |
| 极高（支付/删除资源） | 多人审批 + 安全门控 |

## 11.7 核心反模式

### 反模式 1：过度编排

**症状**：一个"查询天气"的 Agent 通过了 7 个 LangGraph 节点。

**正确做法**：如果任务在 30 秒内完成且逻辑线性，一个 ReAct 循环就够了。编排框架的存在是为了解决崩溃恢复、人机协作、复杂路由——不是为了让你把简单问题变复杂。

### 反模式 2：过早引入 Temporal

**症状**：团队花了两周配置 Temporal 集群，然后发现 Agent 只是调用一个 API 返回结果。

**正确做法**：先用 LangGraph + PostgresSaver。只有当执行路径超过 30 秒或涉及 3 个以上外部系统时，再加 Temporal。cordum.io 的数据显示，低于这些阈值时第二个运行时的运维成本不值得。

### 反模式 3：所有节点都走 LLM

**症状**：格式化输出、拼接字段、简单判断——全部通过 LLM 节点。

**正确做法**：LLM 只用于推理和决策。数据转换、格式检查、确定性路由用纯代码。

### 反模式 4：忽略编排税

编排框架本身有开销：LangGraph 每次节点执行写 Checkpoint（50-200ms），Temporal 每次活动调用通过 RPC。如果你有 20 个节点每个 200ms，编排税就是 4 秒。

**缓解**：合并小操作为一个节点，减少 Checkpoint 频率。

## 11.8 小结

2026 年的 Pipeline 编排已经从"怎么写"变成了"怎么选"。三条原则：

1. **从最简单的开始**。不是所有任务都需要编排框架——很多场景下一个 ReAct 循环就够了。
2. **按需升级**。当任务开始跨越 30 秒、3 个外部系统、或涉及人工审批时，依次引入 LangGraph → Temporal。
3. **LLM 只用在该用的地方**。编排的核心价值在于确定性逻辑（崩溃恢复、补偿、审批门控），不是让 LLM 决定每一个步骤。

更深的编排知识——特别是 Sub-Agent 的 Loop Engineering——见第 16 章。
