# 第四章：能力扩展——Function Calling

## 4.1 引言：FC 的本质

Function Calling（FC）是 Agent 从"聊天"到"做事"的桥梁。但理解它首先要破除一个常见误解：**LLM 不执行函数，它只生成"调用意图"**。

```
# LLM 的输出不是天气数据，而是这个 JSON：
{
  "tool_calls": [{
    "function": {"name": "get_weather", "arguments": "{\"city\": \"Beijing\"}"}
  }]
}
# 你的应用层负责：解析 → 执行 get_weather("Beijing") → 把结果还给 LLM
```

这个"理解任务 → 选择工具 → 构造参数 → 消化结果 → 决定下一步"的循环，就是 FC 的全部工作。它的设计好坏，直接决定 Agent 的可靠性和成本。

## 4.2 2026 年 FC 生态全景

FC 在过去两年经历了三个阶段：

| 阶段 | 时间 | 特征 |
|------|------|------|
| API 原生 FC | 2023-2024 | 各供应商独立实现，格式不互通 |
| 并行 + Strict 模式 | 2025 | 并行调用成为标配，Strict 模式消灭参数错误 |
| FC + MCP 混合 | 2026 | MCP 成为工具标准化协议，内外部分治 |

### BFCL V4 基准数据（2026）

Berkeley Function Calling Leaderboard V4 是最权威的 FC 基准，权重侧重 Agent 行为（40%）和多轮交互（30%）：

| 模型 | BFCL V4 总分 |
|------|-------------|
| Claude Opus 4.1 | 70.36% |
| Claude Sonnet 4 | 70.29% |
| GPT-5 | 59.22% |

即便顶级模型，在长对话记忆和"知道何时不调用工具"上仍有显著差距。70% 看起来不高——但在真实 Agent 场景中，这已经是最高记录了。

### 供应商 FC 能力速览

| 能力 | OpenAI GPT-5.4 | Claude Sonnet 4.6 | Gemini 3.1 | DeepSeek V4 |
|------|:--:|:--:|:--:|:--:|
| 并行 FC | ✅ 默认开启 | ✅ | ✅ | ✅ |
| Strict 模式 | ✅ | ✅ | ✅ | ⚠️ 部分 |
| 嵌套调用 | ✅ | ✅ | ✅ | ❌ |
| Streaming FC | ✅ | ✅ | ✅ | ❌ |
| 最大工具数 | 128 | 128 | 128 | 128 |

---

## 4.3 Schema 设计：投入产出比最高的环节

Schema 设计的每一分钟，在生产中都能省下十倍的调试时间。这不是夸张——有数据支持：

| Schema 优化 | 准确率提升 |
|------------|----------|
| 基础描述（有 function name + 一句话 description） | 基准线 |
| + 详细 description（何时用、返回什么） | **+16%** |
| + 参数示例与约束（enum, format） | **+7%** |
| + enum 约束可选值 | **+3%** |
| **完全优化** | **可达 93%** |

### 五条铁律

```
1. 函数名用动词+名词：query_sales, create_order, delete_user
2. description 要说"何时使用"，不只说"做什么"
3. 参数用 enum 约束可选值——别让模型猜
4. required 只包含真正必要的参数——可选参数放外面
5. 每个参数都有 description——不写 description 的参数=坑
```

### 好与坏的对比

```python
# ❌ 模型不知道该何时调用、参数范围是什么
{"name": "process", "description": "处理数据",
 "parameters": {"input": {"type": "string"}}}

# ✅ 清晰、具体、有约束
{"name": "query_sales_data",
 "description": "查询指定时间范围和区域的销售数据。当用户询问销售额、业绩、营收时使用。",
 "parameters": {
     "start_date": {"type": "string", "format": "date", "description": "起始日期 YYYY-MM-DD"},
     "end_date":   {"type": "string", "format": "date", "description": "结束日期 YYYY-MM-DD"},
     "region":     {"type": "string", "enum": ["north","south","east","west","all"],
                    "description": "区域筛选，默认 all"},
 },
 "required": ["start_date", "end_date"]}
```

> **一个常见陷阱**：不要把"能做所有事"的万能函数暴露给模型。函数职责越窄、边界越清晰，模型的选择准确率越高。拆成 5 个小函数比 1 个大函数好十倍。

---

## 4.4 并行调用：2026 年的默认模式

2024 年你可能需要手写循环来依次调用工具。2026 年，并行 FC 已是所有供应商的默认行为。

**原理**：模型在一次推理中判断出多个独立调用（如"对比北京、上海、广州天气"），同时返回 3 个 tool_call。应用层并行执行它们，将结果一并返回。

性能数据：arXiv:2602.07359 论文在 Agent 搜索任务中测得 **4 倍加速**。

```python
response = client.chat.completions.create(
    model="gpt-5.4-mini",
    messages=[{"role": "user", "content": "北京、上海、深圳的天气分别怎么样？"}],
    tools=tools,
    parallel_tool_calls=True  # OpenAI 默认开启，可显式声明
)

# response.choices[0].message.tool_calls 包含 3 个调用
# 并行执行它们
import asyncio

async def execute_all(tool_calls):
    async def execute_one(tc):
        fn = tool_registry[tc.function.name]
        args = json.loads(tc.function.arguments)
        result = await fn(**args) if asyncio.iscoroutinefunction(fn) else fn(**args)
        return {"tool_call_id": tc.id, "content": str(result)}
    return await asyncio.gather(*[execute_one(tc) for tc in tool_calls])
```

**何时不该并行**：如果两个调用有依赖关系（先查用户 ID，再查该用户的订单），让模型分两步走——第一次返回 query_user，拿到结果后再返回 query_orders。并行仅适用于彼此独立的调用。

---

## 4.5 错误处理：FC 最常见的四类失败

| 错误类型 | 占比 | 根因 | 修复 |
|---------|------|------|------|
| 参数错误 | 30% | description 不清晰、缺 enum 约束 | 优化 Schema description |
| 选错函数 | 25% | 函数职责重叠、描述太像 | 差异化 description |
| 缺少参数 | 15% | required 不符合实际 | 重新审视 required 字段 |
| 幻觉函数 | 12% | 模型编造不存在的函数名 | 开启 Strict 模式 |

**核心防御策略**：

```python
class SafeExecutor:
    def __init__(self, tool_registry: dict, max_retries=2):
        self.registry = tool_registry
        self.max_retries = max_retries

    async def execute(self, tool_call):
        fn_name = tool_call.function.name

        # 1. 存在性检查——阻止幻觉函数
        if fn_name not in self.registry:
            return json.dumps({"error": f"函数 '{fn_name}' 不存在",
                               "available": list(self.registry.keys())})

        # 2. 参数解析
        try:
            args = json.loads(tool_call.function.arguments)
        except json.JSONDecodeError as e:
            return json.dumps({"error": f"参数 JSON 非法: {e}"})

        # 3. 执行 + 重试
        for attempt in range(self.max_retries + 1):
            try:
                result = await asyncio.wait_for(
                    self.registry[fn_name](**args),
                    timeout=30
                )
                return self._sanitize(str(result))
            except Exception as e:
                if attempt == self.max_retries:
                    return json.dumps({"error": str(e)})
                await asyncio.sleep(1 * (attempt + 1))

    def _sanitize(self, result: str, max_chars=5000) -> str:
        return result[:max_chars] + "..." if len(result) > max_chars else result
```

错误信息返回给 LLM 时，要让它"看得懂为什么失败，知道怎么修"。`{"error": True, "message": "..."}` 格式比裸 Exception 字符串有效得多。

### Strict 模式

2026 年所有主流供应商都已支持 Strict 模式——模型在 Token 级别保证参数 100% 符合 JSON Schema：

```python
{"type": "function", "function": {
    "name": "create_user",
    "strict": True,  # 开启
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "email": {"type": "string", "format": "email"},
            "role": {"type": "string", "enum": ["user", "admin"]}
        },
        "required": ["name", "email", "role"],
        "additionalProperties": False  # Strict 模式要求
    }
}}
```

Strict 模式要求 `additionalProperties: False` 且所有字段有明确的 `type`。额外代价是 Schema 编写更严格，但换来零参数错误——在生产环境中这个交易太划算了。

---

## 4.6 FC 与 MCP 的选型

Function Calling 和 MCP 不是二选一的关系。2026 年最务实的模式是**混合使用**：

| | Function Calling | MCP |
|---|---|---|
| 适用场景 | 应用内部工具、低延迟 | 外部工具生态、跨应用共享 |
| 工具定义 | 代码内 JSON Schema | MCP Server 运行时发现 |
| 移植性 | 绑定 LLM 供应商 | 跨模型、跨平台 |
| 延迟 | 极低 | 有协议开销（stdio/HTTP） |
| 典型用途 | 查数据库、发邮件、内部 API | 文件系统操作、第三方服务、开源工具 |

```
决策树：
├── 工具只在本应用用，追求最低延迟 → 原生 FC
├── 工具需要跨应用共享，或来自开源生态 → MCP
├── 企业级部署，需审计+权限+标准化 → MCP 优先
└── 两者都需要（绝大多数情况）→ 内部 FC，外部 MCP
```

MCP 的完整工程化实践（含 Server 实现、Client 管理、权限控制）详见第 16 章《Agent Harness 与 Loop 工程化》。

---

## 4.7 成本优化

FC 的隐藏成本不在 Token 消耗——而在"调了不该调的函数"。

**模型分层路由**：简单 FC 任务不需要 GPT-5.4。

```python
COST_ROUTES = {
    "simple":   ("groq/llama-3.1-8b", 0.27),   # 3 个工具以内
    "medium":   ("gpt-5.4-nano",      0.50),   # 10 个工具以内
    "complex":  ("gpt-5.4-mini",      1.10),   # 复杂推理
}
```

**大规模工具场景**：不要把所有 100+ 工具一次性塞进 Context。用 Tool Search Tool 模式——给模型一个"搜索工具"的元工具，按需查找相关工具定义。Spring AI 的实现在保持准确率的同时减少了 **34-64% Token 消耗**。

**结果截断**：FC 执行结果默认截断到 5000 字符。一个 `SELECT *` 返回的 20MB 数据对 LLM 推理没帮助，只会撑爆 Context Window。

---

## 4.8 小结

Function Calling 在 2026 年已经是一个成熟的基础能力，不再是需要手动构建"鲁棒执行框架"的领域。

三个核心原则：

1. **Schema 设计是最大的杠杆**——优化的 Schema 能带来 +26% 准确率，比换模型更划算
2. **并行是默认、Strict 是标配**——不要在串行循环和手动参数校验上浪费时间
3. **内部 FC + 外部 MCP**——不是选边站，而是各取所长

下一章进入 Agent 能力的组织层面——如何将零散的 Function 封装为可复用的 Skills（技能体系）。
