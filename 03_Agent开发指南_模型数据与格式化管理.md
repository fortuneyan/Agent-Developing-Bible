# 第三章：结构化输出——从"祈祷"到"保证"

## 3.1 问题已经变了

2023 年，LLM 的结构化输出是件让人血压飙升的事。你需要写一个 `robust_json_parse()`，先用正则找大括号，清理尾随逗号，再手动补缺失的闭合括号——最后还要祈祷模型别把 `"false"` 写成 `False`。

2026 年，这个问题在 API 模型层面已经解决。核心范式转移：**从"手动解析免责"到"选对工具即可"。**

这章的叙事也因此变了——不再教你写正则抢救残破 JSON，而是带你理解三种保证层级的差异、三个现代化工具怎么用，以及在哪些时候你仍然需要手动降级。

### 三个保证层级

| 层级 | 技术 | 可靠性 | 适用场景 |
|------|------|--------|---------|
| L1: 文本约束 | JSON Mode (`response_format`) | ~95% | 简单 JSON、内部工具调用 |
| L2: Schema 约束 | Structured Outputs (`json_schema`) | ~99.9% | 生产 API、精确字段控制 |
| L3: 约束解码 | FSM + Token 掩码 | 100% Schema | 严格 Schema、合规场景 |

L3 的 100% 是通过 FSM（有限状态机）在输出 Token 时就做掩码——能做 `{` 的地方绝不可能生成 `[`。OpenAI 的 Structured Outputs 和 Anthropic 的 Structured Outputs 本质都是这个机制。

> **提示**：Schema 合规 ≠ 内容正确。模型可以输出 `"age": 999` 且完全符合 Schema。不要混淆"格式保证"和"语义正确"。

---

## 3.2 如果只需要简单 JSON

并非所有场景都需要重量级方案。下面这个就够了：

```python
response = client.chat.completions.create(
    model="gpt-5.4-mini",
    messages=[...],
    response_format={"type": "json_object"},  # L1 层级
)
data = json.loads(response.choices[0].message.content)
```

当你的需求是"给我一个 JSON 对象"而非"字段必须长成这个 Schema"，L1 足够了。成本几乎为零。

如果需要精确 Schema：

```python
response = client.chat.completions.create(
    model="gpt-5.4-mini",
    messages=[...],
    response_format={
        "type": "json_schema",               # L2 层级
        "json_schema": {
            "name": "weather_query",
            "strict": True,                   # 开启约束解码
            "schema": {
                "type": "object",
                "properties": {
                    "city": {"type": "string"},
                    "date": {"type": "string", "format": "date"}
                },
                "required": ["city", "date"],
                "additionalProperties": False
            }
        }
    }
)
```

当 `strict: True` 时，OpenAI 在 Token 级别保证输出 100% 符合 `json_schema`。你不会再看到字段缺失或类型错误。

### 一个常见陷阱

`additionalProperties: False` 在某些供应商（DeepSeek、Ollama 等）的兼容实现中可能不生效或行为不一致。如果你跨供应商使用，建议在 Schema 级别接受额外字段，用 Pydantic 做解析侧裁剪：

```python
from pydantic import BaseModel

class WeatherQuery(BaseModel):
    city: str
    date: str | None = None

    class Config:
        extra = "ignore"  # 解析时丢弃未定义字段
```

---

## 3.3 方案一：Instructor（API 模型首选）

[Instructor](https://github.com/instructor-ai/instructor) 是目前 Python 生态中 Structured Outputs 的事实标准。月度下载 60 万+，支持 OpenAI/Anthropic/Gemini 等所有主流供应商。

核心思想：把 Pydantic 模型作为"输出契约"直接传给 API，Instructor 负责模型调用、重试和类型强制。

```python
import instructor
from openai import OpenAI
from pydantic import BaseModel

client = instructor.from_openai(OpenAI())

class UserInfo(BaseModel):
    name: str
    age: int
    email: str | None = None

# 一次调用，返回已验证的 Pydantic 对象
user = client.chat.completions.create(
    model="gpt-5.4-mini",
    messages=[
        {"role": "user", "content": "张伟, 28岁, zhangwei@example.com"}
    ],
    response_model=UserInfo,  # 这就是输出契约
    max_retries=3,            # 自动重试，每次带上校验错误
)

print(user.name)   # "张伟"
print(user.age)    # 28
print(type(user))  # <class '__main__.UserInfo'>
```

三层内置保障：
1. **API 端约束**：自动设置 `response_format` 和 `json_schema`
2. **Pydantic 校验**：收到响应后执行 `UserInfo.model_validate()`
3. **自动重试**：校验失败时把 Pydantic 错误信息传给模型，让它自我修正（最多 `max_retries` 次）

这意味着你可以删掉之前手写的所有"自我修复循环"代码——Instructor 已经做了。

### 多模型支持

```python
# Anthropic Claude
client = instructor.from_anthropic(anthropic.Anthropic())

# Google Gemini
client = instructor.from_gemini(genai.GenerativeModel("gemini-3.1-flash"))

# Litellm（代理任意供应商）
client = instructor.from_litellm(litellm.completion)
```

对于没有原生 Structured Outputs 的模型（如旧版 Ollama），Instructor 退回到 JSON Mode + 重试策略，最大化兼容性。

---

## 3.4 方案二：BAML（跨模型 + 多语言 + 类型安全）

BAML（Boundary AI Markup Language）是 2025 年底由 Glean 开源的方案，把结构化输出提升到了编译期类型安全的高度。

和 Instructor 的区别：

| | Instructor | BAML |
|---|---|---|
| 核心理念 | Python 运行时校验 | 编译期类型检查 + DSL |
| 多语言 | Python/TS 分别实现 | 同一 `.baml` 定义，自动生成 Python/TS/Ruby 代码 |
| 解析引擎 | 依赖 API 层 | 自带 SAP（语法-分析-解析）引擎，不依赖模型 |
| 错误修复 | API 重试 | SAP 引擎自动修复词法/语法/语义错误 |
| 使用场景 | 快速原型、Python 占主导 | 多语言团队、生产级别可靠性 |

### BAML 的核心武器：SAP 解析引擎

三个修复层级，依次尝试：

1. **词法修复**：清理非法 Unicode、匹配未闭合引号
2. **语法修复**：自动补全缺失的括号、去除尾随逗号
3. **语义修复**：对比目标 Schema，补充缺失字段的默认值

生产数据对照：某 SaaS 公司从 Instructor 迁移到 BAML 后，月成本从 $18,400 降至 $6,200，JSON 解析错误率从 12.7% 降到 0.3%。

### 一个 BAML 示例

```baml
// weather.baml
class WeatherQuery {
  city: string     @description("城市名称")
  date: string?    @description("查询日期，可选")
}

class WeatherResponse {
  temperature: float
  condition: string    @description("如: 晴, 多云, 雨")
  humidity: int
}

function GetWeather(query: WeatherQuery) -> WeatherResponse
```

编译后自动生成 Python 代码：

```python
from baml_client import b

# 类型安全的调用
result = b.GetWeather("今天北京天气怎么样")
# result 是强类型 WeatherResponse，IDE 有完整补全
print(f"{result.temperature}°C, {result.condition}")
```

BAML 的最佳场景是：多语言协作、需要编译期类型保证、对解析可靠性有极致要求。

---

## 3.5 方案三：Outlines（开源/自托管模型）

如果你用的是开源模型（Llama、Qwen、Mistral 等），以上 API 方案都不适用。这时需要 [Outlines](https://github.com/dottxt-ai/outlines)。

Outlines 在自托管模型的推理层直接注入 FSM 约束——生成每个 Token 时，只允许符合 Schema 的候选。

```python
import outlines

model = outlines.models.transformers("meta-llama/Llama-3.2-70B-Instruct")

from pydantic import BaseModel

class WeatherReport(BaseModel):
    city: str
    temperature_c: float

generator = outlines.generate.json(model, WeatherReport)

result = generator("北京今天的天气怎么样？")
# result 保证是 WeatherReport 类型，绝无违规字段
print(result.model_dump())  # {"city": "北京", "temperature_c": 26.5}
```

这是数学层面的保证——FSM 状态机在推理过程中始终维护 Schema 约束。不依赖模型配合，不需要重试。

代价：复杂 Schema 下推理速度下降 20-40%（每个 Token 都需要做掩码运算），且只适用于支持自定义采样的推理框架（vLLM/llama.cpp/transformers）。

---

## 3.6 生产级分层降级策略

生产环境中，不赌单一方案。按以下优先级依次降级：

```python
from enum import Enum

class ParseStrategy(Enum):
    STRUCTURED_OUTPUTS = 1  # 最优：原生 json_schema + strict
    INSTRUCTOR_RETRY = 2    # 次优：Instructor 自动重试
    JSON_MODE = 3           # 兜底：JSON Mode + Pydantic 手动校验
    BAML_SAP = 4            # 最后：BAML SAP 引擎暴力修复
    FREE_TEXT = 5           # 降级：自由文本 + 正则关键词
```

实现骨架：

```python
async def safe_extract(prompt: str, schema: type[BaseModel]) -> BaseModel:
    strategies = [
        # L1: 原生 Structured Outputs
        lambda: extract_via_native_structured_outputs(prompt, schema),
        # L2: Instructor 兜底（处理供应商不支持的 Schema 变体）
        lambda: extract_via_instructor(prompt, schema),
        # L3: JSON Mode + 宽松 Pydantic
        lambda: extract_via_json_mode(prompt, schema),
    ]
    last_error = None
    for strategy in strategies:
        try:
            return await strategy()
        except Exception as e:
            last_error = e
            # 记录降级日志，包含降级原因和部分输出
            logger.warning(f"策略降级: {strategy.__name__} 失败: {e}")
            continue
    # 全部失败：返回含原始输出和错误信息的结果
    raise ParseError(f"所有策略均失败: {last_error}")
```

真实经验：**绝大多数场景只需 L1**。L2 和 L3 是"安全网"——它们在 99.9% 的请求中不会被触发，但缺少它们会让那次 0.1% 的异常从"记录日志→下一条请求继续跑"变成"用户看到 500 错误"。

---

## 3.7 选型决策

| 场景 | 推荐方案 | 原因 |
|------|---------|------|
| GPT / Claude / Gemini API | Instructor | 最简，一行 `response_model` |
| 跨供应商 + 多语言团队 | BAML | 编译期类型安全、单一定义多处生成 |
| 开源模型自托管 | Outlines | FSM 数学保证、无 API 依赖 |
| 快速原型、内部工具 | JSON Mode + Pydantic | 零依赖、即开即用 |
| 高可靠性要求（金融/医疗） | Structured Outputs + BAML 双保险 | SAP 引擎兜底任何残留错误 |

### 另一个容易忽视的现实

流式输出 + 结构化输出是两个天然矛盾的需求。Structured Outputs 需要模型输出完整后才做 Schema 校验——这意味着流式场景下你只能在"实时展示文本"和"保证结构"之间二选一。

工程上的常见拆解：文本部分流式输出（打字机效果），工具调用部分等完整后再解析。别试图在流式文本中做实时 JSON Schema 校验。

---

## 3.8 小结

这一章的核心只有一句话：**2026 年不要再手写 `robust_json_parse()` 了**。

这条路上已经有人替你把坑踩完了。选对工具，结构化输出从"工程噩梦"变成"一行 `response_model`"。剩下的精力，应该花在 Schema 设计、降级策略和语义校验上——那些才是真正区分好 Agent 和凑合能跑的 Agent 的地方。

下一章进入 Agent 真正开始"做事"的核心能力——Function Calling（函数调用）。
