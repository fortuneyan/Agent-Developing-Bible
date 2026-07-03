# 第五章：技能体系——Agent Skills 定义和组织

本章讲解 2026 年 Agent Skills 的核心标准 SKILL.md、渐进式披露机制、Skills 与 Workflow 架构的选择、四种技能组合模式、Skills 生态市场，以及 Auto Skills 自进化能力。

## 5.1 引言：从"提示词工程"到"技能工程"

2026 年，Agent 开发的主旋律不再是"如何写好 Prompt"，而是"如何用标准化的技能模块构建可组合的能力"。中商产业研究院预测，2026 年全球 AI Agent 市场规模将达 175 亿美元。

这个转变的标志性事件是 **SKILL.md 标准的统一**。在 2024-2025 年，每家平台都在自造技能定义格式——JSON Schema、YAML 配置、Python 装饰器，互不兼容。到了 2026 年，Claude Code、Codex CLI、OpenAI Agents SDK、Cursor、OpenClaw 等 27+ 平台都收敛到了同一个标准：一个以 `SKILL.md` 为核心的文件夹结构。

这个收敛意义巨大。过去你在 Claude Code 写的技能没法在 OpenAI SDK 用，现在一个标准走天下。

### Skill 是什么

用一句话讲：**Skill 是 LLM 可延迟加载、按需激活的专业知识包**。

跟 Prompt 有什么区别？Prompt 是一次性指令，每次都全文加载。Skill 是模块化的能力单元，只在需要时才被激活加载。一个 Agent 可以持有一百个 Skill，但每次对话只激活两三个，不浪费上下文。

跟我们在第 04 章讲的 Function 有什么区别？

| 维度 | Function (工具) | Skill (技能) |
|:---|:---|:---|
| **粒度** | 原子操作：`sql_query`, `web_search` | 业务场景：`analyze_sales_report` |
| **内容** | JSON Schema 定义接口 | SKILL.md + scripts/ + references/ + assets/ |
| **知识** | 无，只有参数签名 | 包含操作流程、领域知识、参考文档 |
| **加载时机** | LLM 决策后按需调用 | 按描述匹配后渐进式加载 |
| **生命周期** | 瞬时执行返回结果 | 可能涉及多轮交互、状态管理 |

一个简单的判断标准：如果这个能力可以用一个 JSON Schema 描述清楚，它是个 Function。如果需要文档、代码、模板才能跑起来，它是个 Skill。

## 5.2 SKILL.md 标准

2026 年的 Agent Skill 有且只有一个标准格式：一个包含 `SKILL.md` 的文件夹。

### 5.2.1 目录结构

```
my-skill/
├── SKILL.md           # 技能定义文件（唯一必需文件）
├── scripts/           # 可执行脚本（Python/Bash/Node）
│   ├── main.py
│   └── utils.py
├── references/        # 参考文档（知识注入，按需加载）
│   ├── api_docs.md
│   └── best_practices.md
└── assets/            # 静态资源（模板、图片、配置文件）
    ├── template.html
    └── logo.png
```

**SKILL.md 是唯一必需文件**，其余三个目录都是可选的。这种"一个文件就是最小技能"的设计极大降低了创建门槛。

### 5.2.2 SKILL.md 结构

```markdown
---
name: code-reviewer
description: 代码审查技能，检查代码质量、安全性和最佳实践
version: "1.2.0"
author: dev-tools-team
tags: [code-review, quality, security]
triggers:
  - 审查代码
  - review code
  - 检查代码质量
---

# 代码审查技能

## 核心职责
作为代码审查专家，你需要对提交的代码执行三级审查。

## 审查流程
1. **安全检查**：SQL 注入、XSS、敏感信息泄露
2. **性能检查**：N+1 查询、不必要的循环、内存泄漏
3. **可读性检查**：命名规范、函数长度、注释完整性

## 输出格式
```json
{
  "score": 1-10,
  "issues": [{"severity": "high|medium|low", "file": "...", "line": N, "description": "...", "suggestion": "..."}],
  "summary": "..."
}
```
```

**Frontmatter（元数据层）**：技能的"摘要卡片"，包含名称、描述、触发词、标签。这是渐进式披露的第一层——Agent 先加载元数据再决定是否要展开正文。

**Body（指令层）**：具体的工作流程和规则。只在技能被匹配后加载，通常不超过 5000 Token。

### 5.2.3 渐进式披露：核心设计思想

这是 SKILL.md 标准最巧妙的地方。技能不是一次性全塞进上下文，而是分三层按需加载：

```
第一层：Frontmatter 元数据（~100 Token）
  → Agent 扫描所有已注册技能的元数据
  → 根据用户意图匹配 2-3 个候选技能

第二层：SKILL.md Body（<5000 Token）
  → 仅展开匹配到的技能的完整指令
  → 不需要的技能正文完全不占 Token

第三层：references/ + assets/（按需读取）
  → 只在技能执行中需要时才读取
  → 例如 API 文档只在调用具体接口时加载
```

这解决了什么实际问题？假设你有个 Agent 配了 50 个技能。如果全塞进 System Prompt，光技能描述就要吃掉 10-20 万 Token，每次对话的成本是白白付给模型"读菜单"的钱。渐进式披露让 Agent 持有一整个技能图书馆，但每次只翻开当前任务需要的那几页。

**关键数据**：相比直接全部注入 Prompt，渐进式披露平均节省 **82.6% 的上下文 Token**。

## 5.3 Skills 与 Workflow：架构抉择

这是 2026 年 Agent 架构中最根本的选择：用声明式的 Skill 还是命令式的 Workflow？

### 5.3.1 两种范式

**Workflow 模式（命令式）**：用 DAG（有向无环图）或状态机预定义步骤。

```yaml
# workflow.yaml — 你预设所有路径
steps:
  - name: validate_input
  - name: process_data
  - name: generate_report
  - name: send_email
    if: generated_successfully
  - name: alert_admin
    if: generation_failed
```

**Skills 模式（声明式）**：定义能力清单，让 LLM 自己决定何时、如何、按什么顺序调用。

```markdown
# skills/ 目录 — 你只声明"我有什么能力"
skills/
├── data-validator/SKILL.md
├── data-processor/SKILL.md
├── report-generator/SKILL.md
├── email-sender/SKILL.md
└── admin-alerter/SKILL.md
```

### 5.3.2 什么时候用哪个

| 场景特征 | 推荐方案 |
|:---|:---|
| 流程固定、步骤少（3-5步）、不可出错 | Workflow（审核流程、支付链路） |
| 流程灵活、步骤多变、需要推理判断 | Skills（客户服务、数据分析） |
| 混合场景 | Skills 编排 + Workflow 卡关键节点 |

**真实数据**：在一个涉及 100 个任务的多 Agent 基准测试中，Skills 模式在仅用 **17.4% 的内存** 的约束下达到了 Workflow 模式 **92.3% 完成率**。换句话说，用不到 1/5 的上下文就能覆盖 9 成以上场景。

### 5.3.3 不要掉进的坑

一个常见错误是"用 Workflow 控制不信任的 LLM"——觉得模型不可靠，于是把每一步都写成流程图。但实践证明，过度定义 Workflow 会让 Agent 失去灵活性，反而降低完成质量。

更好的思路：**把确定性交给 Workflow，把灵活性留给 Skill**。支付确认用 DAG 写死，客服对话用 Skills 让 LLM 自由发挥。

## 5.4 技能组合与编排

单个 Skill 解决简单问题，复杂问题需要技能组合。2026 年有四种主流模式。

### 5.4.1 顺序组合（Pipeline）

最直接的组合方式：Skill A 的输出是 Skill B 的输入。

```
数据采集 Skill → 数据清洗 Skill → 数据分析 Skill → 报告生成 Skill
```

适用场景：流程固定、每个环节的输出格式已知。

### 5.4.2 条件组合（Router）

根据中间结果动态选择下一技能。

```
用户请求 → 意图分类 Skill → 
  ├── 技术支持 Skill（匹配到技术类）
  ├── 退款处理 Skill（匹配到投诉类）
  └── 产品推荐 Skill（匹配到咨询类）
```

LLM 在每一步都重新决策"下一步用哪个技能"，不需要预设分支。

### 5.4.3 并行组合（MapReduce）

N 个 Skill 并行执行，结果汇总到一个汇总 Skill。

```
大文件处理 → 
  ├── 分块1 → 分类器 Skill
  ├── 分块2 → 分类器 Skill   （并行）
  ├── 分块3 → 分类器 Skill
  └── 分块4 → 分类器 Skill
      ↓
  汇总 Skill → 最终结果
```

适用场景：批量处理、多维度分析、大规模数据。

### 5.4.4 LLM 驱动自适应规划

这是 2026 年出现的最高级组合模式。你不需要预定义组合流程，Agent 自己规划。

```
用户："帮我分析这个数据集，找出增长瓶颈，给方案，输出 PPT"

Agent 推理：
  1. 需要数据加载 Skill
  2. 需要统计分析 Skill
  3. 需要可视化 Skill
  4. 需要策略生成 Skill
  5. 需要 PPT 生成 Skill
  → 自动规划执行顺序，部分并行，部分串行
```

关键前提是 Skill 的描述要足够精确——LLM 无法规划它不理解的技能。

## 5.5 Skills 生态与市场

2026 年，Skills 已经从"自己造轮子"进入了"社区共享"阶段。

### 5.5.1 三个主流渠道

| 渠道 | 类型 | 特点 |
|:---|:---|:---|
| **ClawHub** | 去中心化市场 | 基于 GitHub 仓库，`npx skills add` 一键安装 |
| **skills.sh** | 中心化发现平台 | 数百个精选 Skill，内置 `find-skills` 自动搜索 |
| **OpenClaw** | 开源生态 | 2026 年标杆级开源项目，技能生态最繁荣 |

### 5.5.2 生态数据（截至 2026 年中）

- 公开可用的 Agent Skills：**85,000+**
- 支持 SKILL.md 标准的平台：**27+** 家
- 覆盖类别：代码审查、数据分析、文档处理、网页自动化、安全合规、跨服务集成（Gmail/Slack/GitHub/Notion 等）

### 5.5.3 安装和分发

```bash
# 从 ClawHub 安装
npx skills add code-reviewer

# Agent 自动搜索安装（find-skills）
# 用户："帮我审查这段代码"
# Agent 自动调用 find-skills 搜索 code-review 类技能
# 自动安装并激活
```

一个值得注意的趋势：**Skill 分发成本接近零**——一个文件夹拖进 skills/ 目录就能用，不需要编译、部署、注册。这跟传统软件分发的 npm install / pip install 是完全不同的心智模型。

## 5.6 Auto Skills：技能自进化

2026 年 Agent 领域最前沿的能力之一是让 Agent **自动创建、存储、改进自己的技能**。

### 5.6.1 技术路线：从 Voyager 到 Claude Code

2023 年，Voyager 项目展示了 Agent 在 Minecraft 中自主编写并存储技能代码的潜力。但那是在封闭的游戏环境里。

到了 2026 年，自进化能力已经进入生产级编码 Agent：

- **发现缺口**：Agent 执行任务时发现自己缺乏某领域的知识或流程
- **自动创建**：Agent 调用 `skill-creator` 自动生成 SKILL.md + scripts/
- **存储记录**：新技能存入 skills/ 目录，下次自动可用
- **迭代改进**：再次执行类似任务时，Agent 基于执行结果修改技能内容

### 5.6.2 核心闭环

```
┌──────────────────────────────────────────┐
│                                          │
│  任务执行 → 发现知识缺口                    │
│      ↓                                   │
│  自动创建 Skill（skill-creator）            │
│      ↓                                   │
│  存储到 skills/ 目录                       │
│      ↓                                   │
│  下次类似任务自动激活                        │
│      ↓                                   │
│  基于执行反馈迭代优化 ──────────────────────┘
```

### 5.6.3 一个真实场景

程序员在 Claude Code 中调试一个 PyTorch 分布式训练的 OOM 问题。场景涉及 NCCL 配置、梯度累积、混合精度训练等多个知识点。

Claude Code 调试完后自动创建了一个 `pytorch-distributed-debugging` Skill，包含诊断流程、常见错误码对照表、NCCL 环境变量参考。

三周后，同一团队的另一个开发者遇到类似问题。Agent 自动匹配到这个 Skill，直接按既定流程走，从诊断到解决用了 15 分钟，而不是上次的 2 小时。

### 5.6.4 注意事项

自进化不是魔法。真实运行中你需要关注三个问题：

1. **技能污染**：错误经验会被固化。需要"审查者 Agent"（Reviewer）定期审计自动创建的技能
2. **技能膨胀**：自动创建过多，元数据层膨胀。需要定期清理低频技能
3. **上下文限制**：第 5.2 节讲的渐进式披露正是解决这个问题——技能再多，每次只加载需要的

## 5.7 编写最佳实践

### 5.7.1 四条原则

**1. 描述决定匹配率**

技能的 Frontmatter 描述和触发词，直接决定了 LLM 在什么场景下激活它。写得太泛——"数据处理技能"——太多场景误匹配。写得太窄——"CSV 第三列求和技能"——几乎不会被匹配。

好的描述是对使用场景的精确画像：

```yaml
triggers:
  - 生成代码审查报告
  - code review
  - PR review
  - 检查代码质量
```

**2. 正文控制在 5000 Token 内**

渐进式披露的设计意图是"正文只加载当前需要的技能"。如果每个技能正文都 20000 Token，匹配两个就吃掉了模型上下文的大半。好的技能用 500-2000 Token 讲清楚流程，详细文档放 references/ 里。

**3. 区分"技能知识"和"领域知识"**

技能知识放 SKILL.md，领域知识放 references/。举个例子：

- SKILL.md 写："执行财务分析时，参考 references/financial_ratios.md 中的公式"
- references/financial_ratios.md 才是完整的公式库

这样 Agent 在非财务场景中不会加载财务公式，在需要时才加载。

**4. 每个 Skill 一个职责边界**

一个 Skill 只解决一类问题。如果 SKILL.md 里有 5 个互不相关的流程，拆成 5 个独立 Skill。匹配更精确，正文更简短，维护更简单。

### 5.7.2 常见陷阱

| 陷阱 | 表现 | 解决 |
|:---|:---|:---|
| **触发词太泛** | 每个请求都匹配到这个 Skill | 加具体的场景关键词 |
| **正文太长** | 匹配两个 Skill 就吃满上下文 | 控制在 5000 Token，细节放 references |
| **把 Function 写成 Skill** | SKILL.md 里只有工具调用，没有知识 | 如果不需要文档/代码/模板，它应该是个 Function |
| **忽略元数据质量** | 描述写"helpful assistant for everything" | 写清楚具体干什么、何时用 |

## 5.8 小结

2026 年，Agent Skills 从各家自造轮子走向了统一标准。这章讲了四个核心要点：

1. **SKILL.md 标准**：一个文件就是一个最小技能，27+ 平台通用
2. **渐进式披露**：三层加载（元数据→正文→资源），平均节省 82.6% Token
3. **Skills vs Workflow**：把确定性交给 Workflow，把灵活性留给 Skill
4. **Auto Skills**：Agent 自己能创建和改进技能，但需要审查机制防止污染

下一章我们转向 Agent 的记忆机制——先从短期记忆（Session Memory）开始，这是实现连贯多轮对话的基础。

---

> **本章参考来源**
>
> - wangjun.dev：SKILL.md 标准规范解读（2026.05）
> - 知乎：2026 年 10 大 AI Agent Skills 深度解析（2026.04）
> - CSDN：Skills 声明式 vs 工作流架构之争（2026.01）
> - daoyuly.cn：Agent Skills Engineering 深度综述（2026.04）
> - AI Insight 研报：Auto Skills 自进化 Agent 路线图（2026.03）
> - skills.sh / ClawHub / OpenClaw：Skills 生态数据
