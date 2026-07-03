# 附录B：初级程序员必读

> **使用说明**：本附录整理了本书各章更新时删除的通用编程基础知识。如果你的 Python 基础较弱，或者在阅读正文时遇到"上下文窗口""指数退避""流式处理"等概念感到吃力，可以先过一遍这里。

---

## B.1 开发环境配置

### 环境变量与密钥管理

API Key 不能硬编码在代码里。标准做法：

**步骤1**：项目根目录创建 `.env` 文件，并加入 `.gitignore`：

```bash
# .env
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxx
```

```bash
# .gitignore 中追加
.env
```

**步骤2**：用 `python-dotenv` 或 `pydantic-settings` 读取：

```python
# 方案A：最简单
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")

# 方案B：带类型校验（推荐生产环境）
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str

    class Config:
        env_file = ".env"

settings = Settings()
print(settings.openai_api_key)
```

> **原则**：永远不要让 API Key 出现在 Git 提交历史中。GitHub 会自动扫描并吊销泄露的 Key。

---

## B.2 API 调用与错误处理

### HTTP 请求基础

调用 LLM API 本质是发 HTTP POST 请求。直接看结构：

```
POST https://api.openai.com/v1/chat/completions
Headers:
  Authorization: Bearer sk-xxx
  Content-Type: application/json
Body:
{
  "model": "gpt-4o",
  "messages": [{"role": "user", "content": "Hello"}]
}
```

几乎所有 LLM API 都兼容这个格式。国产模型（DeepSeek、Qwen）也是同一套。

### 常见 HTTP 状态码

| 状态码 | 含义 | 应对 |
|:---|:---|:---|
| 200 | 成功 | 正常处理 |
| 401 | API Key 无效 | 检查 Key 是否正确/过期 |
| 429 | 请求过多/速率限制 | 等待后重试（指数退避） |
| 500 | 服务器内部错误 | 重试，多次失败则降级 |
| 503 | 服务不可用 | 等待后重试 |

### 指数退避重试

遇到 429（限流）时，不能立即重试——这样只会加剧拥堵。

原理：**每次重试等待时间翻倍，并加入随机抖动**，避免多个客户端同时重试（惊群效应）。

```python
import time
import random

def retry_with_backoff(max_retries=3, base_delay=1):
    """指数退避装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        wait = base_delay * (2 ** attempt) + random.uniform(0, 1)
                        print(f"限流。{wait:.1f}秒后重试...")
                        time.sleep(wait)
                    else:
                        raise
        return wrapper
    return decorator

@retry_with_backoff(max_retries=3)
def call_llm(client, messages):
    return client.chat_completion(messages=messages)
```

### 缓存重复请求

`temperature=0` 的请求结果是确定性的——相同输入必然产生相同输出。这类请求可以缓存，把响应时间从秒级降到毫秒级：

```python
import hashlib
import json

def cache_key(model, messages):
    """temperature=0 且同样输入 → 同样 key"""
    content = json.dumps({"model": model, "messages": messages}, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()[:32]
```

---

## B.3 JSON 解析与数据校验

Agent 开发中最常见的 bug：LLM 返回的内容不是纯 JSON，`json.loads()` 直接报错。

### 鲁棒解析：分四步尝试

```python
import re
import json

def robust_json_parse(text):
    """容错 JSON 解析：纯JSON → Markdown代码块 → 外科手术提取"""
    # 第一步：直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 第二步：提取 Markdown 代码块
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 第三步：定位首尾大括号
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        json_str = text[start:end+1]
        # 第四步：修复尾随逗号 {"a": 1,} → {"a": 1}
        cleaned = json_str.replace(",}", "}").replace(",]", "]")
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    raise ValueError("无法解析出有效 JSON")
```

> 2026 年各 LLM 已原生支持结构化输出（`response_format: "json_schema"`），这个解析器只在处理旧模型或 Prompt 约束失效时兜底。

### Pydantic 数据校验

解析出 JSON 后，还必须校验字段类型和必填项：

```python
from pydantic import BaseModel, ValidationError

class AgentAction(BaseModel):
    tool_name: str          # 必填，字符串
    parameters: dict        # 必填，字典

try:
    action = AgentAction(**raw_data)
except ValidationError as e:
    # 根据 e.errors() 重新构建错误回传给 LLM 自我修复
    print(f"校验失败: {e}")
```

---

## B.4 Prompt 编写基本功

### System Message 原则

System Message 是 Agent 的"宪法"——定义角色、能力边界、输出格式、安全规则。不会变的内容放这里。

**好的 System Message 模板**：

```
# 角色定位
你是一名{role}，专注于{expertise}。

# 能力范围
{expertise_list}

# 沟通风格
{communication_style}

# 输出格式要求
{output_format}

# 安全规则
{safety_rules}
```

**关键点**：
- System Message 越长，模型越容易忽略后面的指令（"Lost in the Middle"效应）
- 把最重要的规则放在开头和结尾
- 用 Markdown 标题（`#`、`##`）而非自然语言分段——模型对标题结构的注意力更高

### Few-shot 技巧

当你要模型输出特定格式时，给 2-3 个例子比写 200 字描述有效：

```
将用户输入分类为以下类别之一：技术问题、账单问题、账户问题。

示例1:
输入: "我的服务器报502错误"
输出: 技术问题

示例2:
输入: "这个月扣了两次费"
输出: 账单问题

现在分类以下输入:
输入: "{user_input}"
输出:
```

---

## B.5 常用设计模式速览

正文多处提到了设计模式。不要求记住所有，但知道这几个就够了：

### 适配器模式

**问题**：不同 LLM 供应商的 API 参数名不同（Anthropic 用 `max_tokens`，某些国产模型用 `max_new_tokens`）。

**解法**：定义一个统一接口，为每个供应商写一个"适配器"：

```python
from abc import ABC, abstractmethod

class BaseLLMClient(ABC):
    @abstractmethod
    def chat_completion(self, messages, model, temperature=0.7):
        """所有供应商都实现这个接口"""
        pass

class OpenAIAdapter(BaseLLMClient):
    def chat_completion(self, messages, model, temperature=0.7):
        return self.client.chat.completions.create(
            model=model, messages=messages, temperature=temperature
        )
```

**好处**：换供应商只改配置，不改业务代码。

### 工厂模式

**问题**：不知道运行时要用哪个供应商的适配器。

**解法**：一个"工厂"函数根据配置返回对应的适配器：

```python
def create_llm_client(provider: str, api_key: str):
    if provider == "openai":
        return OpenAIAdapter(api_key=api_key)
    elif provider == "anthropic":
        return AnthropicAdapter(api_key=api_key)
    raise ValueError(f"不支持的供应商: {provider}")
```

**组合使用**：适配器定义"做什么"，工厂决定"用哪个"。这是 Agent 开发中最常见的代码组织方式。

---

## B.6 常见错误排查清单

### API 调用相关

| 现象 | 可能原因 | 优先检查 |
|:---|:---|:---|
| `401 Unauthorized` | API Key 过期/错误/未加载 | `os.getenv()` 是否读到了值，Key 是否以 `sk-` 开头 |
| `429 Rate Limit` | 请求频率超限 | 是否加了重试逻辑，是否有多个客户端共用同一 Key |
| `503 Service Unavailable` | 供应商宕机 | 是否有备用供应商/降级策略 |
| 返回慢（>10秒） | 模型响应慢 | 是否用了推理模型（o3/Claude Opus 4.6），考虑切换到中小模型 |
| 返回内容被截断 | `max_tokens` 设太小 | 检查 `finish_reason == "length"` |

### JSON 解析相关

| 现象 | 可能原因 | 优先检查 |
|:---|:---|:---|
| `json.loads()` 报错 | LLM 输出了非纯 JSON | 使用 `robust_json_parse()` 提取，或启用 `response_format` |
| 字段类型错误 | Prompt 描述不清 | 在 Prompt 中给出字段类型示例，或使用 JSON Schema 约束 |
| JSON 不完整 | `max_tokens` 不够 | 增大 `max_tokens`，或触发自动续写 |
| 尾随逗号导致解析失败 | LLM 输出习惯 | `robust_json_parse()` 里 `replace(",}", "}")` 兜底 |

### 上下文窗口相关

| 现象 | 可能原因 | 优先检查 |
|:---|:---|:---|
| 模型"失忆"——忘记前面的对话 | 上下文窗口满了，早期内容被截断 | 是否在拼接历史时按 Token 数做了限制 |
| 回答越来越差 | 历史对话噪音堆积 | 是否需要对旧对话做摘要压缩 |
| System Message 被忽略 | 过长的用户输入把系统指令"冲走" | System Message 是否太长，核心规则是否放在末尾 |

---

## B.7 Python 异步基础速览

Agent 开发中大量使用异步——同时调多个 API、流式输出等。Python 异步核心只有三个概念：

```python
import asyncio

async def fetch_data(url):
    """async def = 这是个异步函数"""
    # await = 等待一个异步操作完成，但不阻塞其他任务
    result = await some_async_call(url)
    return result

async def main():
    # 并发执行多个任务
    results = await asyncio.gather(
        fetch_data("url1"),
        fetch_data("url2"),
        fetch_data("url3"),
    )
    # results = [result1, result2, result3]

asyncio.run(main())
```

**记住**：
- `async def` 定义的函数需要用 `await` 调用
- `asyncio.gather()` 让多个异步任务并发执行，等全部完成才返回
- 不要混用同步和异步——如果函数里有 `await`，调用它的函数也必须是 `async`

---

## B.8 Token 计数入门

Token 是 LLM 计费和处理的基本单位。中文约 1 Token ≈ 1.5 个汉字，英文约 1 Token ≈ 4 个字符。

当你需要判断"这段对话历史是否超出模型的上下文窗口"时，用 `tiktoken`：

```python
import tiktoken

enc = tiktoken.get_encoding("cl100k_base")  # GPT-3.5/4/o 系列
tokens = enc.encode("你的文本内容")
print(f"Token 数: {len(tokens)}")
```

不需要精确到个位数——估算就行。经验法则：一段 500 字的中文 ≈ 330 Token，一次典型的 10 轮对话 ≈ 3000-5000 Token。

---

**回到正文**：以上内容足够覆盖 Agent 开发中 90% 的基础编程需求。如果在正文中遇到新的概念卡住，首先查附录A术语表。
