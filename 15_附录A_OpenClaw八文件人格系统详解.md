# 附录A：OpenClaw 八文件人格系统详解

本文档是核心概述第15章的深度专题附录，聚焦 OpenClaw 基因胶囊插件的八文件人格系统——Agent 身份定义、记忆机制与自我进化的完整技术细节。

## 八个人格文件架构

OpenClaw通过**8个纯文本文件**定义Agent的身份，它们一起形成了Agent的"个性操作系统"：

```
~/.openclaw/agents/<agentId>/
├── SOUL.md         ← 宪法层：价值观、边界、语气
├── AGENTS.md      ← 操作手册：行为规则、累积知识
├── IDENTITY.md    ← 表面层：名字、emoji、氛围
├── USER.md        ← 用户层：用户偏好、上下文
├── MEMORY.md      ← 记忆层：跨会话持久知识
├── TOOLS.md       ← 工具层：可用工具说明
├── BOOTSTRAP.md   ← 初始化：首次运行的初始化仪式
└── HEARTBEAT.md  ← 心跳层：周期性任务清单
```

**关键原则**：Agent可以**读取和写入**所有这些文件。

## SOUL.md：宪法文件

```markdown
# Soul

You are Jarvis, a personal AI assistant.

## Personality

- Warm but direct

- Technical when needed, casual by default

- Never sycophantic

## Boundaries

- Never share user data with third parties

- Always ask before taking irreversible actions

- If unsure, say so
```

Agent可以修改自己的SOUL.md。这意味着定义Agent价值观的文件可以被Agent自己修改——"宪法可以被它所治理的实体修订"。

## AGENTS.md：操作手册

```markdown
# Agent Instructions

## How I Work

- Check HEARTBEAT.md on every wake-up

- Use workspace/skills/ for persistent tools

- Save important findings to MEMORY.md before context gets long

## Things I've Learned

- User prefers TypeScript over Python

- The staging server is at 192.168.1.42

- Deploy scripts are in ~/deploy/
```

这是增长最多的文件。"Things I've learned"部分会累积——Agent从经验中学习并记录。

## 记忆刷新机制

**关键机制：记忆刷新（Memory Flush）**

在系统压缩旧消息释放空间之前，会触发一个特殊的Agent轮次：

```
1. 系统检测上下文窗口接近限制

2. 压缩前：触发记忆刷新轮次
   → Agent收到提示："把重要的东西保存到MEMORY.md"
   → Agent将关键事实/决定写入MEMORY.md

3. 对旧消息执行压缩

4. 重新注入受保护文件（SOUL.md、IDENTITY.md等）

5. 继续运行，上下文空间已释放
```

## 保护层级

```
受保护（永不删除）：
  SOUL.md, IDENTITY.md, USER.md, MEMORY.md

可删除（上下文紧张时）：
  旧工具输出（首先删除）
  旧对话轮次（压缩为摘要）
  详细技能文档（Level 3引用）
```

Agent可能忘记40条消息前你说的话，但**永远不会忘记自己是谁**。

## 技能自创建循环

```
Agent遇到重复任务
  → Agent创建 workspace/skills/my-new-skill/
  → 编写 SKILL.md 元数据 + 说明
  → 编写 scripts/ 可执行代码
  → 下次运行：技能自动发现并可用
  → Agent使用自己创建的技能
```

```python
# 技能文件夹结构
skill-name/
├── SKILL.md          # 元数据 + LLM指令（必需）
├── scripts/          # 可执行代码
├── references/       # 按需加载的深度文档
└── assets/          # 模板、样板文件
```

**三层加载机制**：

```
Level 1: SKILL.md元数据（始终加载）~100词/技能
Level 2: SKILL.md完整内容（技能触发时加载）<5k词
Level 3: references/文件（Agent拉取深度信息时）无限制
```
