# 第六章：短期记忆——Session Memory

本章讲解 2026 年的 Session Memory 工程实践。核心范式已从"上下文窗口太小怎么办"迁移到"1M 窗口 ≠ 1M 有效注意力"——关键不是存多少，而是模型实际能注意到多少。

## 6.1 引言：LLM 天生没有记忆

大语言模型每一次 API 调用都是一次全新的开始。它没有内置的"海马体"来留存上一秒的信息。Agent 要具备智能，首先必须能记住对话。

但 2026 年的 Session Memory 已经不是 2024 年的那个问题了。当时的核心矛盾是"上下文窗口太小"——GPT-4 只有 128K，长对话很快就爆掉。2026 年 GPT-5.4 有 256K，Gemini 3.1 Pro 有 1M，窗口不再是瓶颈。

**新问题来了**：1M 上下文窗口不等于 1M 有效注意力。信息在窗口中的位置、结构、缓存命中率——这些决定了 Agent 实际能"记住"多少。本节要讲的就是怎么做。

## 6.2 消息结构：Tool Call 配对是底线

先解决最基本的——消息怎么存。主流 LLM 的对话历史都遵循基于角色的消息结构：

```json
[
  {"role": "system", "content": "你是一个天气助手..."},
  {"role": "user", "content": "北京今天天气怎么样？"},
  {"role": "assistant", "content": null, "tool_calls": [{"id": "call_123", "name": "get_weather", "args": "Beijing"}]},
  {"role": "tool", "tool_call_id": "call_123", "content": "{'temp': 25, 'condition': 'sunny'}"},
  {"role": "assistant", "content": "北京今天天气晴朗，气温25度。"}
]
```

**一个关键规则**：`assistant(tool_call)` 和 `tool(result)` 必须成对存在。如果修剪时破坏了这种配对——比如保留 tool_call 但删了 result——Agent 会以为工具调用还没返回，然后重新发起调用。这是生产环境最常见的死循环原因。

```python
class SessionManager:
    def __init__(self, max_tokens: int = 100000):
        self.messages = []
        self.max_tokens = max_tokens

    def add_message(self, role: str, content: str = None, **kwargs):
        msg = {"role": role}
        if content is not None:
            msg["content"] = content
        msg.update(kwargs)
        self.messages.append(msg)
        self._prune()

    def _prune(self):
        """保留 system + 最近 N 轮，但确保不拆散 tool_call 配对"""
        tool_call_ids = set()
        for m in self.messages:
            if m.get("tool_call_id"):
                tool_call_ids.add(m["tool_call_id"])

        while self._estimate_tokens() > self.max_tokens and len(self.messages) > 1:
            candidate = self.messages[1]  # 跳过 system
            role = candidate.get("role", "")

            # tool 消息有配对 assistant → 一起删
            if role == "tool" and candidate.get("tool_call_id") in tool_call_ids:
                # 向前找配对的 assistant(tool_call)
                for j in range(1, len(self.messages)):
                    if (self.messages[j].get("tool_calls") and
                        any(tc["id"] == candidate["tool_call_id"]
                            for tc in self.messages[j].get("tool_calls", []))):
                        del self.messages[j]
                        break

            del self.messages[1]

    def _estimate_tokens(self) -> int:
        return sum(len(str(m)) for m in self.messages) // 3
```

**会话隔离**：生产环境在 Key 中带 Session ID：`session:{user_id}:{session_id}`。A 用户的对话绝不能出现在 B 用户的上下文中。

## 6.3 核心问题：1M 窗口 ≠ 1M 有效注意力

有了 1M 的上下文窗口，为什么还需要管理策略？两个原因：

### Lost in the Middle 效应

LLM 对上下文窗口中的信息不是均匀注意的。开头和结尾的内容记得清楚，中间的信息容易被忽略——这叫 U 型性能曲线。

数据来自 zylos.ai 2026 年研究：在一个 4K Token 的上下文中，中间位置的信息准确率从 75% 显著下降。窗口越大，这个效应越明显。**1M 窗口的最中间 300K 部分，模型的有效注意力可能只有窗口边缘的 30-40%。**

### 成本增长

每轮对话都带上完整历史，Token 消耗线性增长。假设每轮 500 Token，10 轮对话后每次请求要带 5000 Token。用 GPT-5.4 ($3/1M output)，100 轮对话的后几轮实际成本远高于早期。

**核心洞察**：2026 年的 Session Memory 重心不再是"怎么在有限空间里塞更多东西"，而是"怎么让模型在现有空间里注意到最关键的东西"。

## 6.4 缓存感知的会话设计

这是 2026 年 Session Memory 最重要的工程优化——但大多数开发者还忽略了它。

### 为什么缓存决定了你的架构

2026 年所有主流供应商都提供了 Prompt Caching：

| 供应商 | 缓存成本 | vs 标准 Input |
|--------|---------|---------------|
| Anthropic Sonnet/Opus | $0.30/1M tokens | **节省 90%** |
| OpenAI GPT-5 系列 | $2.50/1M tokens | **节省 50%** |
| Gemini 3.1 系列 | $0.075/1M tokens | **节省 75%** |
| DeepSeek V4 | 自动缓存 | 无需开发者干预 |

关键点：**缓存的命中条件是前缀必须完全一致**。这意味着你的消息列表的前缀结构，直接决定你花了多少钱。

### 三种前缀策略

```
策略 A：固定前缀（缓存友好，命中率最高）
[system_msg, summary_msg, msg1, msg2, msg3]  ← 前两条不变，始终命中缓存

策略 B：增量追加（每轮都在尾部加新消息，前缀不变）
[system_msg, msg1]
[system_msg, msg1, msg2]        ← 缓存命中（前缀 [system_msg, msg1] 不变）
[system_msg, msg1, msg2, msg3]  ← 缓存命中

策略 C：缓存断点（中段插入新内容，打破前缀）
[system_msg, summary, msg1, msg2]
[system_msg, new_summary, msg1, msg2]  ← 缓存 MISS（summary 变了）
```

**正确的做法**：当你需要更新摘要时，不要插入到前缀中。把它放在独立的占位消息里，或者在消息列表末尾追加，保持前缀稳定。

```python
class CacheAwareSession(SessionManager):
    """缓存感知的会话管理器：永远保持前缀稳定"""

    def get_context(self) -> List[Dict]:
        """返回优化后的上下文，保证缓存命中率"""
        # 固定前缀：system + 历史摘要（不变的部分）
        prefix = [m for m in self.messages if m["role"] == "system"]
        if self._summary:
            prefix.append({"role": "system", "content": f"[历史摘要] {self._summary}"})

        # 尾部：最近 N 轮原始对话
        non_system = [m for m in self.messages if m["role"] != "system"]
        recent = non_system[-10:]

        return prefix + recent

    def update_summary(self, new_summary: str):
        """更新摘要——但保持前缀结构不变，缓存不失效"""
        self._summary = new_summary
        # 注意：摘要内容是字符串，存储为 self._summary，
        # get_context() 中始终复用同一个前缀结构，缓存命中
```

**一个关键反模式**：有人在每轮对话后都重新生成摘要并 insert 到 system 消息之后。每次摘要变了，整个前缀就不一样了，缓存命中率直接归零。正确做法是：只有对话积累到一定阈值（比如 30 轮以上）才更新一次摘要，保持前缀稳定。

## 6.5 四级优先级框架

不是所有消息都值得保留到上下文用完。zylos.ai 提出的优先级框架比传统的"三段式"（System + 摘要 + 最近几轮）更精细：

| 优先级 | 内容 | 保留策略 | 代表 |
|--------|------|---------|------|
| **关键** | 当前任务相关的决策、约束、用户明确指令 | 始终保留 | system message、最新用户指令 |
| **高** | 最近的完整对话轮次（含 tool call） | 保留最近 5-8 轮 | 刚完成的工具调用、确认信息 |
| **中** | 早期对话的摘要 | 定期更新，保持 300-500 Token | 已完成步骤的背景 |
| **低** | 寒暄、确认性回复、"好的""收到" | 直接丢弃 | 无信息量的消息 |

核心代码：

```python
class PrioritySessionManager(SessionManager):
    def get_context(self) -> List[Dict]:
        critical = [m for m in self.messages if m["role"] == "system"]
        # 高优先级：最近 N 轮完整对话（含 tool call 配对）
        high = self._get_recent_complete_rounds(n=6)
        # 中优先级：摘要
        mid = [{"role": "system", "content": f"[历史摘要] {self.summary}"}] if self.summary else []
        return critical + mid + high
```

## 6.6 压缩策略速览

压缩在 2026 年仍然需要，但不是因为窗口不够大——而是为了减少 Token 成本和提升注意力聚焦。

| 策略 | 何时用 | 效果 |
|------|--------|------|
| **滑动窗口**（只保留最近 N 轮） | 简单问答、对话轮次 < 30 | 实现简单，但会丢失早期上下文 |
| **LLM 摘要** | 长任务、跨多轮的复杂推理 | 保留决策脉络，额外 LLM 调用成本 ~500 Token |
| **缓存感知混合**（前缀不变 + 摘要 + 最近几轮） | **生产级 Agent 首选** | 同时优化成本和注意力 |

**何时不需要压缩**：如果对话轮次 < 20 且没有成本压力，直接全部保留即可。1M 窗口下，20 轮对话通常不到 50K Token，压缩带来的收益还不如它引入的复杂度和摘要不准确的风险。

## 6.7 Agent Loop 中的记忆陷阱

当 Agent 进入循环（多步推理、自主任务执行），Session Memory 面临特殊挑战：

**陷阱一：中间的推理链不能被简单丢弃。** 如果 Agent 在 20 轮推理后形成了一个结论，你把推理过程删了只保留结论——下一轮 Agent 可能"忘记"为什么得出这个结论，然后重新推理一遍。

**陷阱二：工具链的原子性比想象中脆弱。** 一个任务可能涉及 `search → filter → analyze → summarize` 四步工具调用。如果你按时间窗口裁剪恰好裁掉了 `filter` 的结果但保留了后续步骤，Agent 看到的上下文是断裂的。

**解决方案**：把工具调用按"任务块"分组。一个完整的任务块（从用户指令到最终回复）作为一个原子单元。修剪时要么全删，要么全留。

```python
def get_task_blocks(self, messages: List[Dict]) -> List[List[Dict]]:
    """将消息列表按任务拆分为原子块"""
    blocks = []
    current = []
    for msg in messages:
        current.append(msg)
        # assistant 的非 tool_call 回复 = 任务结束标志
        if msg["role"] == "assistant" and not msg.get("tool_calls") and msg.get("content"):
            blocks.append(current)
            current = []
    if current:
        blocks.append(current)
    return blocks
```

## 6.8 存储方案速览

| 方案 | 适用场景 | 取舍 |
|------|---------|------|
| **进程内存**（Python dict） | 单机脚本、原型验证 | 重启即丢失 |
| **Redis** | 生产级 Web 服务 | TTL 自动过期，分布式共享 |
| **MongoDB/PostgreSQL** | 需要长期冷归档 | 查询灵活，但不如 Redis 快 |

生产级推荐：**Redis 热数据 + 数据库冷归档**。Redis 存活跃会话（TTL 30 分钟），超时后自动过期或归档到 MongoDB 作长期存储。

## 6.9 记忆框架生态

如果你不想从零搭建，2026 年已有成熟的记忆框架：

| 框架 | 定位 | 特色 |
|------|------|------|
| **mem0** | 通用记忆层 | 自动提取实体和偏好，生成结构化记忆 |
| **MemGPT/Letta** | 操作系统式记忆 | 虚拟上下文管理，自动将长记忆分页交换 |
| **Memobase** | 用户画像记忆 | 长期用户档案的渐进式更新 |
| **Zep** | 企业级记忆平台 | 时序记忆图 + 用户事实 + 消息搜索 |

选型建议：如果你在做一个聊天机器人，先别急着上框架。从 `Dict[str, List[Dict]]` 开始，等真正遇到问题（多服务实例共享、TTL 管理、记忆查询）再引入合适的方案。

## 6.10 反模式清单

| # | 反模式 | 后果 | 正确做法 |
|---|--------|------|---------|
| 1 | 修剪时拆散 tool_call 配对 | Agent 死循环重试工具调用 | 原子性检查，成对删除 |
| 2 | 每轮都更新摘要并 insert 到前缀 | Prompt Caching 命中率归零 | 前缀结构保持稳定，摘要变化频率降到最低 |
| 3 | 把中间推理丢弃只留结论 | Agent "失忆"，重新推理 | 按任务块分组，原子保留 |
| 4 | 无限制堆叠对话历史 | 成本线性增长 + Lost in the Middle | 超过 20 轮启动压缩策略 |
| 5 | 把 system message 和其他消息混在一起管理 | system 被意外裁剪 | 单独存储，get_context() 始终位列第一 |

## 6.11 小结

Session Memory 在 2026 年的重心变了：

1. 上下文窗口够大了，但模型对窗口中间信息的注意力严重下降——**位置决定一切**。
2. **缓存感知的会话设计**是最大的成本优化杠杆——前缀结构直接影响 50-90% 的输入成本。
3. 四级优先级框架替代传统"三段式"，更精细地管理信息保留策略。
4. Agent Loop 场景下的记忆陷阱需要特别注意——按任务块分组、原子性保留。
5. 不要过早引入记忆框架。从最简单的 dict 开始，遇到真实瓶颈再加方案。

下一章将探讨长期记忆——如何让 Agent 记住几天甚至几个月前的事。
