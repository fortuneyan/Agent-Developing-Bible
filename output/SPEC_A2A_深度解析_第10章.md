# SPEC: A2A 协议深度解析 — 第 10 章 §10.5 扩展

> 版本: v1.0 | 日期: 2026-07-07 | 状态: Draft

---

## 一、定位与动机

### 1.1 现有问题

当前 10.5 节 "MCP + A2A 协议生态" 对 A2A 的覆盖仅约 15 行，内容包括：
- 一句分层图（A2A 水平协调 + MCP 垂直集成）
- 一句话描述（6 个任务状态 + SSE + 跨框架互操作）
- 一条检查清单提示

**缺失了所有工程落地需要的细节。** 如果一个读者要做多智能体系统，看完当前 10.5 节仍然不知道：
- Agent Card 长什么样，怎么用它做发现
- Task 的 8 个状态分别意味着什么，什么时候会卡在 INPUT_REQUIRED
- Part 和 Artifact 怎么区分，为什么"消息≠输出"
- 流式、推送通知、轮询三种交付方式怎么选
- 安全认证怎么配（OAuth2 vs mTLS vs API Key）
- 多轮交互的 contextId / taskId / referenceTaskIds 怎么用

### 1.2 为什么放在第 10 章

第 10 章是"多智能体治理"——A2A 天然属于这个主题。它不是一个独立的生态工具（那是第 12 章的范畴），而是多智能体协作的**基础设施协议**。理解了 A2A 的设计，才能理解 10.2-10.4 节中那些协调模式（Orchestrator-Subagent、Agent Teams、Message Bus）在跨组织、跨框架的场景下如何落地。

第 12 章 §12.6 已有 A2A 的生态级概述，那里的内容保持不变——它回答的是"选框架时看什么协议"。本章节回答的是"你要用 A2A 做多 Agent 系统时，需要知道什么"。

---

## 二、学习目标

读完本节后，读者应能：

1. 解释 A2A 的三层协议架构（数据模型 / 抽象操作 / 协议绑定）及其设计意图
2. 阅读和理解一份 Agent Card JSON，知道各字段的含义和用途
3. 描述 Task 的完整 8 状态生命周期，以及每种终态/中断态的触发条件
4. 区分 Part 的四种内容类型（text / raw / url / data）并说明"消息≠输出"的设计原则
5. 对比三种任务更新交付机制（轮询 / 流式 / 推送通知）的适用场景
6. 理解 contextId、taskId、referenceTaskIds 在多轮交互中的作用
7. 了解 A2A 的安全认证体系（API Key / OAuth2 / mTLS）及其选择依据
8. 掌握 A2A vs MCP 的分工边界：什么时候应该用 A2A 暴露 Agent，什么时候应该用 MCP 暴露工具

---

## 三、前置依赖

- 第 04 章：Function Calling（理解 Agent 如何调用工具）
- 第 10 章 §10.1-10.4：多智能体协调模式与编排架构
- 第 12 章 §12.6 中对 MCP 的基本了解（A2A 与 MCP 的对比是本节的暗线）

---

## 四、内容大纲

### 10.5 A2A 协议深度解析——Agent 间互操作标准

#### 10.5.0 从一个真实场景切入

用一个具体的多 Agent 场景开场——"帮我规划一趟国际旅行"：
- 机票 Agent、酒店 Agent、当地导游 Agent、汇率换算 Agent 来自不同公司、不同框架
- 没有 A2A：每个 Agent 被包装成 Tool，失去自主性；每对接一个新 Agent 都是一次新集成
- 有 A2A：编排 Agent 通过 Agent Card 发现能力，通过 Task 管理生命周期，通过 Artifact 接收结果

这四段场景描述替代传统的"本节将介绍……"式开头。

#### 10.5.1 Agent Card：能力的名片

- Agent Card 的完整 JSON 结构展示（一个完整示例）
- 关键字段详解：
  - `name` / `description`：身份声明
  - `capabilities`：streaming、pushNotifications、extendedAgentCard
  - `skills`：Agent 的能力列表（不是工具列表，是"我能做什么"）
  - `supportedInterfaces`：端点 URL + 协议绑定（JSON-RPC / gRPC / HTTP+JSON），优先级排序
  - `defaultInputModes` / `defaultOutputModes`：支持的媒体类型
  - `securitySchemes`：认证方式声明
  - `signatures`：JWS 签名（验证卡片完整性）
- 发现流程：Client → GET Agent Card → 解析 → 建立连接
- Extended Agent Card（认证后可获取更详细的能力声明）
- 与 Function Calling 的对比：工具声明 vs Agent 声明——为什么 Agent 不应该被包装成 Tool

#### 10.5.2 Task 生命周期：8 个状态一台戏

- 完整状态机图（用文本 ASCII 艺术或代码块展示）
  ```
  SUBMITTED → WORKING → COMPLETED
                    ├→ FAILED
                    ├→ CANCELED
                    ├→ REJECTED
                    ├→ INPUT_REQUIRED (可恢复: 用户输入 → WORKING)
                    └→ AUTH_REQUIRED (可恢复: 认证完成 → WORKING)
  ```
- 四个终态：COMPLETED（正常完成）、FAILED（执行错误）、CANCELED（外部取消）、REJECTED（Agent 主动拒绝）
- 两个中断态：INPUT_REQUIRED（需要用户输入）、AUTH_REQUIRED（需要认证）——这两个状态的工程意义：在"全自动"和"人工介入"之间架桥
- 阻塞模式 vs 非阻塞模式（`returnImmediately` 字段的工程选择）
- 实际案例：订机票时航班已售罄 → Agent 进入 INPUT_REQUIRED → 用户在对话中确认备选方案 → 任务继续

#### 10.5.3 Part 与 Artifact：为什么"消息≠输出"

- Part 的四种类型：
  - `text`：纯文本（最常用）
  - `raw`：文件的原始字节（base64 编码）
  - `url`：指向文件内容的 URL（大文件场景）
  - `data`：任意结构化 JSON（表单、结构化结果）
- Artifact：Task 的输出容器——由多个 Part 组成
- 关键设计原则：**Message 用于通信（多轮对话、澄清、状态更新），Artifact 用于交付结果**
- 为什么这个分离很重要：
  - 通信历史可能很长、需要截断
  - Artifact 是最终产出，需要完整保留和引用
  - 生产环境中日志审计需要区分"沟通过程"和"最终结果"
- 代码片段：一个包含 text + data Part 的 Artifact 示例

#### 10.5.4 三种交付机制：轮询、流式、推送

- 轮询（Get Task）：最简单，防火墙友好，适合简单集成
- 流式（SSE Streaming）：低延迟、实时更新，适合交互式应用
- 推送通知（Push Notification）：异步、无需保持长连接，适合长时间运行任务和服务间集成
- 对比表格：延迟、复杂度、适用场景、基础设施要求
- `capabilities.streaming` 和 `capabilities.pushNotifications` 的声明机制
- 选型建议：大多数场景从流式开始；后台批处理用推送；调试阶段用轮询

#### 10.5.5 多轮交互：contextId 和任务引用

- `contextId`：逻辑分组，维持会话连续性（类比 HTTP Session）
- `taskId`：引用特定任务，支持追加输入
- `referenceTaskIds`：显式声明任务间的依赖关系
- INPUT_REQUIRED 状态下的交互模式：Agent 发澄清消息 → 用户回复 → 任务继续
- 实际场景：采购审批流程——采购 Agent 生成订单草稿 → INPUT_REQUIRED → 用户确认/修改 → 继续执行

#### 10.5.6 安全与认证

- Agent Card 中的 `securitySchemes` 字段声明支持哪些认证方式
- 三种主流方案对比：
  - API Key：最轻量，适合内部 Agent 或信任域内
  - OAuth 2.0（含授权码 / 客户端凭证 / 设备码）：适合跨组织协作
  - mTLS（双向 TLS）：最高安全级别，适合金融/医疗等合规场景
- JWS 签名：Agent Card 的完整性验证——防止卡片被中间人篡改
- 原则：认证委托给 Agent 自身（A2A 不定义认证协议，只声明需求）

#### 10.5.7 A2A vs MCP：什么时候用什么

- 核心区别表格：
  - MCP：模型 ↔ 工具/资源，无状态调用，工具声明
  - A2A：Agent ↔ Agent，有状态任务，Agent Card 发现
- 判断标准：对方是"工具"还是"Agent"？
  - 工具：确定性输入输出、不需要多次交互、不需要自主推理 → MCP
  - Agent：需要多轮协商、有自己的推理能力、可能拒绝或要求澄清 → A2A
- 反模式：把 Agent 包装成 MCP Tool——失去自主性、无法处理中断态、无法多轮交互
- 互补关系：A2A 的 Agent 内部仍然可以通过 MCP 调用工具

#### 10.5.8 版本协商与扩展机制

- A2A-Version 请求头的协商逻辑
- 兼容性规则：客户端必须发送版本号，服务端按请求版本处理
- Extension 机制：超出核心规范的扩展能力——Agent Card 中声明，消息中携带
- 选框架时的协议版本检查清单

#### 10.5.9 协议检查清单（更新版）

- 将现有的一句话检查清单扩展为实用表格：
  - 支持 MCP 吗？→ 工具生态对接能力
  - 支持 A2A 吗？→ 跨 Agent 协作能力
  - A2A 支持哪些认证方式？→ 跨组织协作安全性
  - 支持流式吗？→ 实时交互体验
  - 支持推送通知吗？→ 异步长任务支持
  - Agent Card 是否可定制？→ 发现机制灵活性

---

## 五、写作策略

### 5.1 叙事弧设计

参考 humanize.md 的"问题 → 尝试 → 解决"模式：

1. **场景引入**（10.5.0）：用一个谁都看得懂的"规划国际旅行"场景讲清楚"没有 A2A 有多痛苦"
2. **核心机制展开**（10.5.1-10.5.6）：逐一拆解 A2A 的设计要素，每个要素配一个实际场景
3. **对比与选择**（10.5.7-10.5.8）：MCP vs A2A、轮询 vs 流式 vs 推送——帮读者做决策
4. **落地指南**（10.5.9）：回到工程视角，检查清单加个人经验

### 5.2 Humanize 策略

| humanize.md 要求 | 本节的执行方式 |
|---|---|
| 有"人设" | 以"做过跨 Agent 系统集成的人"的视角，讲述选择协议时遇到的真实困惑 |
| 有叙事弧 | "规划国际旅行"场景贯穿全文，多次回扣 |
| 减少"大词" | 不用"非常重要""核心""关键"，改用"它解决的是一个很具体的问题……" |
| 长短句交替 | 每个 subsection 至少有一句不超过 8 个字的短句收尾 |
| 有个人视角 | "我们第一次对接外部 Agent 时，最头疼的不是协议本身，而是……" |
| 有具体数据 | Agent Card JSON 示例、Task 状态机、Part 类型示例——都用真实格式 |
| 打破"工整" | 10.5.7（A2A vs MCP）用问答体，10.5.9（检查清单）用表格——形式不统一 |

### 5.3 个人经验注入点

1. "我们第一次用 A2A 做多 Agent 协作时，最大的坑是把 Agent 当 Tool 调——结果状态丢失、上下文断裂"
2. "INPUT_REQUIRED 状态在实际项目中比想象的更常见——用户确认、审批流程、异常分支都需要它"
3. "选推送通知还是流式？我们的经验是：用户在线用流式，后台任务用推送，别混用"

---

## 六、与现有章节的集成点

| 章节 | 集成方式 |
|---|---|
| 第 00 章（前言） | 已有 A2A 提及，无需修改 |
| 第 04 章（Function Calling） | 在 10.5.7 中对比 FC 工具声明 vs Agent Card 声明 |
| 第 10 章 §10.1 | 回扣"多智能体的成本"——A2A 通信本身也有 Token 开销 |
| 第 10 章 §10.2 | 五种协调模式在 A2A 体系下如何映射（Orchestrator 对应 A2A Client，Worker 对应 A2A Server） |
| 第 12 章 §12.6 | 保持高层概述不变，不重复本节内容。在 12.6 末尾加一句"详见第 10 章 10.5 节" |

---

## 七、度量预估

| 指标 | 预估值 |
|---|---|
| 新增行数 | ~250 行（替换原 10.5 的 ~25 行，净增 ~225 行） |
| subsection 数量 | 10 个（10.5.0 到 10.5.9） |
| 代码/JSON 示例 | 3 个（Agent Card / Artifact / 请求示例） |
| 对比表格 | 4 个（交付机制 / 认证方案 / MCP vs A2A / 协议检查清单） |
| 场景案例 | 2 个（国际旅行 / 采购审批） |
| 个人经验 | 3 处 |
