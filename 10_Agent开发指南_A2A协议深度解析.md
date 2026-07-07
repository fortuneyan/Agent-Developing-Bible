# 第十章补充：A2A 协议深度解析——Agent 间互操作标准

> 本章是第十章（多智能体治理）§10.5 的扩展内容。阅读前提：已读完第十章 §10.1-10.4，对多智能体协调模式有基本了解。

---

## 10.5.0 从一个真实场景切入

假设你让编排 Agent 干一件事：**"帮我规划一趟下周的国际旅行"**。

这事看起来简单，但拆开来看，需要至少四个 Agent 协作——一个查机票、一个订酒店、一个推荐当地景点、一个做汇率换算。它们来自不同公司、可能跑在不同框架上——机票 Agent 是 LangGraph 写的，酒店 Agent 跑在 Google ADK 上，景点 Agent 是 CrewAI 搭的，汇率换算就是个简单的 MCP Tool。

2024 年到 2025 年初的做法是什么？把每个外部 Agent 都封装成工具，硬塞进编排 Agent 的 Function Calling 里。每对接一个新的 Agent，改代码、改配置、重部署。四个 Agent 还好，四十个呢？一个 Agent 升级了 API 格式，你得改所有调用方。

这就是 A2A 要解决的问题。它不是"又一个通信协议"——它是 Agent 之间互操作的**基础标准**：怎么声明自己的能力、怎么委托任务、怎么在多轮交互中保持上下文、怎么把结果安全地交付回来。

读完本节，你会对这套机制有工程级的理解。我们按"发现 → 委托 → 执行 → 交付"的顺序，一层层拆开。

---

## 10.5.1 Agent Card：能力的名片

A2A 的起点不是任务，是一张"名片"。

每个实现 A2A 的 Agent 都在一个公开 URL 上发布自己的 Agent Card——一个 JSON 文档，描述"我是谁、我能做什么、怎么联系我"。编排 Agent 拿到这张卡片，就知道该怎么跟它打交道了。

一份简化但完整的 Agent Card 长这样：

```json
{
  "name": "Flight Booking Agent",
  "description": "Searches and books international flights across 300+ airlines.",
  "url": "https://flights.example.com/agent",
  "provider": { "organization": "TravelCo", "url": "https://travelco.com" },
  "capabilities": {
    "streaming": true,
    "pushNotifications": true,
    "extendedAgentCard": false
  },
  "skills": [
    {
      "id": "flight-search",
      "name": "Flight Search",
      "description": "Search flights by origin, destination, dates, and passenger count",
      "tags": ["travel", "flight", "booking", "international"],
      "examples": [
        "Find the cheapest flight from Beijing to Tokyo on July 15",
        "Search direct flights from Shanghai to Singapore next Monday"
      ]
    },
    {
      "id": "flight-booking",
      "name": "Flight Booking",
      "description": "Book a selected flight and issue tickets",
      "tags": ["travel", "flight", "booking"],
      "examples": [
        "Book the 9:30 AM flight CA123 from Beijing to Tokyo"
      ]
    }
  ],
  "supportedInterfaces": [
    {
      "protocol": "json-rpc",
      "url": "https://flights.example.com/agent/jsonrpc",
      "preferenceOrder": 1
    },
    {
      "protocol": "grpc",
      "url": "https://flights.example.com/agent/grpc",
      "preferenceOrder": 2
    }
  ],
  "defaultInputModes": ["text/plain", "text/markdown"],
  "defaultOutputModes": ["text/plain", "application/json"],
  "securitySchemes": [
    {
      "type": "oauth2",
      "description": "OAuth 2.0 client credentials flow",
      "authorizationUrl": "https://auth.travelco.com/authorize",
      "tokenUrl": "https://auth.travelco.com/token"
    }
  ],
  "signatures": [
    {
      "algorithm": "ES256",
      "publicKey": {
        "type": "jwk",
        "jwk": {
          "kty": "EC",
          "crv": "P-256",
          "x": "base64url-encoded-x-coordinate",
          "y": "base64url-encoded-y-coordinate"
        }
      },
      "value": "base64url-encoded-JWS-signature"
    }
  ],
  "version": "1.0.0",
  "protocolVersion": "1.0"
}
```

别被长度吓到。关键字段就几个：

**`skills`** 不是工具列表——是"我能帮你完成什么任务"的语义声明。注意和 Function Calling 里 `tools` 的区别：`tools` 是原子操作（"调用 SQL 查询"），`skills` 是复合能力（"搜索并预订航班"）。一个 skill 背后可能调用了十个工具，但调用方不需要知道。

**`supportedInterfaces`** 列出支持的协议绑定和优先级。JSON-RPC 排第一，gRPC 排第二——编排 Agent 会按这个顺序尝试连接。这个机制让同一个 Agent 能同时服务轻量客户端和需要高性能的内部服务。

**`capabilities.streaming`** 和 **`capabilities.pushNotifications`** 决定了这个 Agent 支持哪种交付机制。如果两个都是 false，编排 Agent 就只能轮询——后面 10.5.4 节细说。

**`signatures`** 用 JWS（JSON Web Signature）对整张卡片签名。如果你不熟悉签名机制，把它理解成"数字盖章"就够了：机票 Agent 用一把只有自己知道的私钥在卡片上盖了个数字章。编排 Agent 用机票 Agent 公开的公钥验证这个章——章是真的，说明卡片确实来自机票 Agent，而且内容中途没被篡改。JWS 就是这个"数字盖章"的标准格式。没有签名的 Agent Card 相当于一个没有 SSL 证书的网站——格式正确，但没有任何可信度。

我们第一次对接外部 Agent 时，最大的坑就是把 Agent Card 理解成"一个静态配置文件"。不是的。它是**动态的能力声明**——Agent 升级了、换认证方式了、新增技能了，卡片跟着变。

这就引出一个实际的工程问题：**Card 怎么缓存？** 每次调任务都重新拉一遍 Card，高并发场景下会引入不必要的延迟和带宽开销。但缓存太久，Card 过期了你还不知道——编排器拿着旧 Card 去调 Agent，认证方式变了直接 401。

生产环境的务实策略是三层：

1. **Cache-Control / ETag**：Agent Card 的 HTTP 响应应该带标准缓存头。编排器用 `If-None-Match` 做条件请求——Card 没变就 304，省一次完整传输。如果你没用过 ETag：它就像文件的"指纹"——服务端返回 Card 时附带一个指纹（ETag 值），下次编排器请求时带上这个指纹说"我上次看到的是这个版本"，服务端比对发现没变就回 304（Not Modified），连 Card 的 JSON 都不用传。
2. **TTL 兜底**：即使服务器没设缓存头，编排器也应有硬 TTL（建议 300s）。不要无限缓存。
3. **失败触发刷新**：任务返回 401（认证过期）或版本不兼容错误时，立即重新拉 Card。这是兜底中的兜底——宁可慢一轮，不要一直错。

这三条不是协议规范要求的——A2A 只定义了 Card 的格式，没定义缓存行为。但做工程的人如果不考虑，上线后踩的就是实打实的坑。

---

## 10.5.2 Task 生命周期：8 个状态一台戏

拿到 Agent Card 之后，编排 Agent 就发任务。A2A 用 Task 管理整个任务的生命周期。不是一问一答，而是一个有明确状态的**有限状态机**——任务在任何时刻只能处于一种状态，且只能沿着规定的路径转移到另一个状态。就像自动售货机：你只能从"待机"→"投币"→"出货"，不可能直接从"待机"跳到"出货"。

完整的 8 个状态：

```
                    ┌─────────────┐
                    │  SUBMITTED  │  编排 Agent 提交任务
                    └──────┬──────┘
                           │ Agent 接受
                    ┌──────▼──────┐
          ┌─────────│   WORKING   │──────────┬────────────┐
          │         └──────┬──────┘          │            │
          │                │                  │            │
   ┌──────▼──────┐  ┌──────▼──────┐   ┌──────▼──────┐  ┌─▼──────────┐
   │  COMPLETED  │  │   FAILED    │   │  CANCELED   │  │  REJECTED  │
   │  正常完成    │  │  执行错误   │   │  外部取消   │  │ Agent 拒绝  │
   └─────────────┘  └─────────────┘   └─────────────┘  └────────────┘

   此外还有两个"中断态"——也从 WORKING 转入，用户操作后可恢复：

   ┌──────────────────┐     ┌──────────────────┐
   │ INPUT_REQUIRED   │     │  AUTH_REQUIRED   │
   │ 需要用户输入      │     │  需要重新认证     │
   └────────┬─────────┘     └────────┬─────────┘
            │ 用户确认后              │ 认证完成后
            └──────────┬─────────────┘
                       │
                ┌──────▼──────┐
                │   WORKING   │  ← 可恢复
                └─────────────┘
```

四个终态：**COMPLETED**（正常完成，返回 Artifact）、**FAILED**（执行错误，Agent 主动报告）、**CANCELED**（编排方主动取消）、**REJECTED**（Agent 审核后拒绝，比如"这个任务超出我的能力范围"）。

两个中断态才是 A2A 设计里最巧妙的部分。

**INPUT_REQUIRED**：Agent 执行到一半发现信息不够，需要问用户。比如订机票——Agent 查到三个航班，但价格和转机时间差异很大。它不会自己瞎选，而是进入 INPUT_REQUIRED，把三个选项放在 Message 里推给编排 Agent，等待用户决策后再继续。

**AUTH_REQUIRED**：认证过期了。比如 OAuth2 Token 在任务执行到一半时失效，Agent 进入 AUTH_REQUIRED，编排 Agent 拿到新 Token 后继续。

我们第一次做多 Agent 系统时，所有任务都是"要么成功要么失败"——没有中断态。结果是什么？Agent 在信息不足时要么自己瞎猜（输出质量差），要么直接失败（用户体验差）。INPUT_REQUIRED 本质上是在"全自动"和"人工介入"之间架了一座桥——需要人时暂停，不需要时全速跑。

还有两个工程参数值得注意。**`returnImmediately`**：设为 true 时，Agent 收到任务后立即返回，后续通过 polling 或 streaming 获取结果。适合长时间任务。设为 false 时，连接保持打开直到任务结束。适合短任务。**`blocking`**：设为 true 且 `returnImmediately=false` 时，响应里直接包含最终结果——省一轮网络请求。

状态机解决的是"任务有几种状态"的问题，但它没解决"卡住了怎么办"。生产环境里必须回答三个问题：

**超时策略**。如果任务在 WORKING 状态停了 10 分钟没动静——是 Agent 在执行一个慢查询，还是它挂了？A2A 协议本身不定义超时（留给实现方），但编排器必须设。建议三层超时：（1）单次 HTTP 请求超时 30s——连接层面的基础保护；（2）任务总超时——从 SUBMITTED 到终态的最大时间，超过就发 Cancel；（3）"无进度"超时——WORKING 状态中没有新的 StatusUpdate 事件，超过 N 分钟判死。第三层最容易漏，也最重要——一个 Agent 可能 TCP 连接正常、HTTP 响应正常，但内部线程死锁了。死锁就是"A 等 B，B 等 A，谁也动不了"——Agent 的两个内部任务互相等待对方手里的资源，导致整个 Agent 虽然"活着"但完全不干活。这种情况 TCP 探活根本测不出来。

**重试的边界**。COMPLETED、CANCELED、REJECTED——不重试。FAILED——看原因：如果是网络错误或临时不可用，指数退避重试（最多 3 次）；如果是"超出能力范围"的业务错误，不应重试——再试多少次也超出范围。INPUT_REQUIRED 和 AUTH_REQUIRED 超时后转 FAILED，按 FAILED 的策略处理。

> **指数退避是什么？** 不是每隔固定时间重试一次——而是每次等待时间翻倍。第一次失败等 1 秒，第二次等 2 秒，第三次等 4 秒。这样做的目的是给下游恢复的时间，同时避免"重试风暴"把对方彻底打挂。固定间隔重试在高并发下会变成脉冲攻击——几百个调用方同时重试，瞬间压垮服务。

**幂等性**。同一个任务由于网络超时被重发了两次——Agent 应该查重（通过 taskId 或编排方自定义的 idempotency key），而不是订两张票。

> "幂等"这个词听起来很学术，实际上意思很简单：同一个操作执行一次和执行十次，结果应该一样。就像电梯的楼层按钮——你按一次去 5 楼，连按十次，结果都是到 5 楼，不会到 50 楼。在编程里，幂等键（idempotency key）就是你给每次操作贴的唯一标签——Agent 看到同一个标签第二次过来，知道"这事已经做过了"，直接返回之前的结果，不再执行一次。这是 Agent 实现方的责任，但编排方不能假设对方一定做了——关键操作（如支付、预订）必须自己在业务层加幂等键。

这三个问题不是协议规范的内容，但它们决定了一个 A2A 系统是"能跑"还是"能上线"。

---

## 10.5.3 Part 与 Artifact：为什么"消息≠输出"

A2A 里有个设计原则，第一次读到会觉得"有必要分这么清吗"——**Message 和 Artifact 是两回事**。

Message 用于**通信**：澄清问题、报告进度、请求输入。Artifact 用于**交付**：任务的最终产出。

但为什么不能混在一起？

想象你让机票 Agent 订了三张票。它跟你的对话里有一大堆"抱歉，您选的航班已售罄，备选方案是……""请问需要靠窗还是靠过道？""支付成功，正在出票……"——这些是 Message，是对话历史。

最终产出是三张电子客票的 PDF 和一份行程确认 JSON。这些是 Artifact。

如果混在一起，你怎么区分"沟通过程"和"最终结果"？日志审计时怎么确定"这就是 Agent 实际交付的东西"？

Artifact 由多个 Part 组成。Part 有三种类型：

| 类型 | 含义 | 什么时候用 |
|------|------|-----------|
| `text` | Markdown 或纯文本 | 报告摘要、分析结论、自然语言回答 |
| `file` | 文件（`bytes` 内嵌 Base64 或 `uri` 外部引用） | PDF 票证、CSV 导出、图片——小文件内嵌，大文件引用 |
| `data` | 任意结构化 JSON | 结构化结果：订票确认、表单数据、API 响应 |

一个典型的 Artifact 示例：

```json
{
  "name": "flight-booking-result",
  "description": "CA123 Beijing → Tokyo booking confirmation",
  "parts": [
    {
      "type": "text",
      "text": "## Booking Confirmed\n\nFlight CA123, July 15 2026, 09:30-13:00 (JST).\nConfirmation code: **BK7X9N**."
    },
    {
      "type": "data",
      "data": {
        "bookingId": "BK7X9N",
        "flight": "CA123",
        "date": "2026-07-15",
        "passengers": ["Zhang Wei"],
        "totalPrice": { "amount": 3280, "currency": "CNY" }
      }
    },
    {
      "type": "file",
      "file": {
        "name": "e-ticket.pdf",
        "mimeType": "application/pdf",
        "uri": "https://cdn.travelco.com/tickets/BK7X9N.pdf"
      }
    }
  ]
}
```

三个 Part 各有用途：`text` 给人看，`data` 给程序解析（编排 Agent 可以把 bookingId 传给酒店 Agent 做关联），`file` 用 `uri` 指向实体的 PDF 票证——大文件不嵌入 Artifact 体，只提供一个可下载的引用地址。

这个分离还解决了一个实际工程问题：**上下文窗口管理**。Message 历史可以截断（太长的对话只保留最近 N 轮），但 Artifact 必须完整保留。你不会因为对话太长就把电子客票删了——但你可以删掉"请问需要靠窗还是靠过道？"这轮无用的澄清。

---

## 10.5.4 三种交付机制：轮询、流式、推送

任务提交了，结果怎么回来？A2A 给了三种方式。不是"选一种最好的"，而是"不同场景用不同的"。

| 机制 | 怎么工作 | 延迟 | 复杂度 | 适合场景 |
|------|---------|------|--------|---------|
| **轮询** Polling | 客户端定时 `GET /tasks/{id}` | 高（取决于间隔） | 最低 | 调试、简单集成、防火墙严格环境 |
| **流式** Streaming | 服务端通过 SSE 持续推送状态更新 | 低（实时） | 中 | 交互式应用、用户在线等待 |
| **推送** Push Notification | 服务端主动 POST 到客户端注册的 webhook | 低（异步） | 高 | 长时间任务、服务间集成、后台批处理 |

**流式（SSE Streaming）** 是最常用的。Agent 在执行过程中不断推送 `TaskStatusUpdateEvent` 和 `TaskArtifactUpdateEvent`——编排 Agent 能实时看到"正在搜索航班……""找到 12 个结果……""正在比价……"。用户体验最好。

> **SSE 和 WebSocket 有什么区别？** 很多人第一次看到 SSE（Server-Sent Events）会问"为什么不用 WebSocket？"——两者都能做服务端推送，但方向不同。SSE 是**单向**的：服务端推 → 客户端收。WebSocket 是**双向**的。A2A 的流式场景只需要服务端推送任务状态，客户端不需要反向推送数据——SSE 更简单、更轻量、防火墙兼容性更好。而且 SSE 天然支持自动重连，断了就重新连上接着收，不用自己写重连逻辑。

但流式有个前提：**客户端必须在任务执行期间保持连接**。如果任务要跑 30 分钟呢？用户不可能盯着屏幕等半小时。这时候用**推送通知**——Agent 完成后主动 POST 到你注册的回调地址。不需要保持连接，适合后台任务和服务间集成。

我们自己的选择标准很简单：如果用户在等（比如对话场景里的"帮我订张票"），用流式。如果是后台跑的分析任务（"分析 Q2 销售数据"），用推送。调试和写测试的时候用轮询——最笨但最不出错。

注意：Agent Card 里的 `capabilities.streaming` 和 `capabilities.pushNotifications` 声明了 Agent 支持哪些。如果 Agent 不声明 streaming，编排方就别发 `stream: true` 的请求——发了也没用。

---

## 10.5.5 多轮交互：contextId 和任务引用

Agent 交互很少是"提交一次、拿到结果、结束"。

真实的业务场景里，用户会在中间提额外要求："等一下，我不想要中转航班，只看直飞的"，Agent 需要根据新约束重新搜索。这个过程需要多轮对话，而多轮对话需要一个"粘合剂"——`contextId`。

**`contextId`**：一个逻辑分组。同一个 `contextId` 下的所有任务和消息属于同一个"会话"。类比 HTTP 的 Session Cookie——它不决定具体行为，但告诉服务端"这些请求是同一件事"。

**`taskId`**：引用一个具体任务。当编排 Agent 需要在任务进行中追加输入（比如用户回复 INPUT_REQUIRED 的澄清问题），就带着 `taskId` 发消息。

**`referenceTaskIds`**：显式声明任务间的依赖关系。任务 B 的输入用了任务 A 的输出？在创建 B 时标注 `referenceTaskIds: ["task-A-id"]`。这个信息对审计和调试帮助巨大——出问题时能追溯完整的任务依赖链。

来看一个实际的多轮交互流程：

```
编排 Agent                         机票 Agent
    │                                  │
    │── SendMessage("查北京→东京 7.15")──→│  contextId: "trip-001"
    │                                  │
    │←── TaskCreated(taskId: t1) ──────│
    │←── StatusUpdate(WORKING) ────────│
    │←── StatusUpdate(INPUT_REQUIRED) ─│  "三个航班，价格差很大，选哪个？"
    │                                  │
    │── SendMessage("选第二个,直飞")────→│  taskId: t1, contextId: "trip-001"
    │                                  │
    │←── StatusUpdate(WORKING) ────────│
    │←── StatusUpdate(COMPLETED) ──────│
    │←── Artifact(订票确认) ───────────│
```

INPUT_REQUIRED 之后的 `SendMessage` 带着相同的 `contextId` 和 `taskId`——机票 Agent 知道这不是新任务，是之前那个任务的追加输入。没有这两个标识符，Agent 会把它当成全新请求，从头开始搜索。

---

## 10.5.6 安全与认证

协议再好，没有安全就是玩具。A2A 不定义新的认证协议——它声明 Agent 需要什么，然后把认证委托给成熟的现有标准。

Agent Card 的 `securitySchemes` 字段声明支持哪些方式。三种主流选择：

| 方案 | 复杂度 | 适合场景 | 谁在用 |
|------|--------|---------|--------|
| **API Key** | 最低 | 内部 Agent、信任域内、快速原型 | 企业内部 Agent 网 |
| **OAuth 2.0** | 中 | 跨组织协作、第三方集成 | 绝大多数 SaaS Agent |
| **mTLS** | 高 | 金融、医疗、政府等合规场景 | 银行间 Agent 通信 |

**API Key** 最简单——Agent Card 里声明 `"type": "apiKey"`，调用方在请求头里带 `Authorization: Bearer {key}`。缺点是权限粒度粗，一个 Key 能调所有接口。适合内部使用。

**OAuth 2.0** 是跨组织协作的标准答案。支持三种 flow，对应三种场景：（1）**授权码 flow**——用户在场，跳转到授权页面点"同意"，适合 Web 应用，比如你让编排 Agent 调第三方 CRM Agent 时弹出一个授权页；（2）**客户端凭证 flow**——没有用户，服务直接拿自己的凭证换 Token，适合后台服务间调用；（3）**设备码 flow**——输入受限设备（电视、CLI 终端）上显示一个码，用户在手机上输入完成授权。大部分公开 Agent 都用 OAuth——Salesforce 的 CRM Agent 用 OAuth 认证，Workday 的 HR Agent 也是。

**mTLS（双向 TLS）** 最高安全级别。普通 HTTPS（单向 TLS）只有服务端出示证书——就像你进公司大楼，保安只看你的工牌，你不看保安的。mTLS 是双方都看对方的证件——Agent 验证调用方的证书，调用方也验证 Agent 的证书。银行和保险公司之间的 Agent 通信通常要求 mTLS。

还有一个容易被忽略的安全机制：**Agent Card 的 JWS 签名**。它的作用不是认证调用方，而是**防止卡片本身被篡改**。如果编排 Agent 通过不安全的 DNS 拿到了假的 Agent Card——URL 指向冒牌服务——JWS 签名验证会直接失败。没有签名验证的 Agent Card 发现机制，相当于开放了一个中间人攻击的入口。

原则只有一句话：**认证是 Agent 自己的事，A2A 只是声明需求**。Agent Card 说的是"你来找我玩需要带什么证件"，而不是"我来检查你的证件"。

---

## 10.5.7 A2A vs MCP：什么时候用什么

这是每个做 Agent 系统的人都会问的问题。MCP 和 A2A 功能重叠吗？什么时候该用哪个？

它们不重叠。它们解决的不是同一个层次的问题。

| 维度 | MCP | A2A |
|------|-----|-----|
| **通信对象** | 模型 ↔ 工具/资源 | Agent ↔ Agent |
| **调用模式** | 无状态（每次调用独立） | 有状态（Task 贯穿生命周期） |
| **发现机制** | 静态工具列表 | 动态 Agent Card + ARD 联合发现 |
| **中断处理** | 无（失败就失败了） | INPUT_REQUIRED / AUTH_REQUIRED |
| **输出模型** | 单一返回值 | Message（对话）+ Artifact（交付物） |

判断标准就一个：**对方是"工具"还是"Agent"？**

- **工具**：确定性输入输出、不需要多轮协商、不需要自主推理。比如"查询这个数据库""发送这封邮件""计算这个公式"。用 MCP。
- **Agent**：需要多轮协商、有自己的推理能力、可能拒绝或要求澄清。比如"帮我规划旅行""审核这份合同""分析这份财报"。用 A2A。

但这个二分法只解决"选哪个"的问题。更深一层，两个协议的设计哲学有本质区别：

MCP 是**无状态管道**：每次工具调用是一个独立的事务。输入进去，输出出来，连接关闭。好处是简单——MCP Server 不需要记住"上次你问了我什么"。代价是无法承载复杂交互。

A2A 是**有状态会话**：Task 贯穿整个交互生命周期——从提交到完成，中间可能有中断、追加输入、重新认证。代价是复杂度更高——Agent 需要维护 Task 状态，编排方需要处理状态转换。好处是能承载真实业务流程。

这两种设计哲学没有优劣——是场景适配的不同。无状态适合高吞吐的原子操作（每秒上千次工具调用），有状态适合低频但复杂的协作任务（一个任务跑几分钟，中间需要人决策）。

理解了这层区别，就理解了为什么不能把 Agent 包装成 MCP Tool，也不能把简单工具暴露成 A2A Agent——不是协议不兼容，是**范式不兼容**。

我们见过一种反模式：把 Agent 包装成 MCP Tool。表面上看能调了，实际上丢失了所有 A2A 的价值——没有 Task 状态管理、没有中断态、没有 Artifact 分离、没有多轮交互。Agent 被降级成一个"输入输出函数"。

反过来也成立：不需要把简单的工具暴露成 A2A Agent。一个汇率转换 API 不需要 Agent Card、不需要 Task 生命周期、不需要 INPUT_REQUIRED。别过度工程化。

A2A 的 Agent 内部仍然可以通过 MCP 调用工具——两者是互补的。机票 Agent 对外通过 A2A 接收任务，内部通过 MCP 调用航空公司的 API。层次分明。

---

## 10.5.8 拓扑模式：Hub-Spoke 还是 Mesh？

协议定义了"怎么通信"，但没定义"跟谁通信"。当系统里有超过三个 Agent，多智能体的连接拓扑就成为一个必须主动设计的问题。

两种基本模式：

**Hub-Spoke（星型）**：一个编排 Agent 做中心，所有任务通过它路由。A → 编排器 → B、C、D。编排器持有所有 Agent Card，统一管理 Task 生命周期。

| 优点 | 缺点 |
|------|------|
| 集中管控——监控、限流、审计都在一个点 | 编排器是单点，挂了全挂 |
| 拓扑简单，Agent 之间不需要互相发现 | 编排器变成瓶颈——所有流量经过它 |
| 适合团队规模 3-20 个 Agent | 编排器升级会影响所有下游 |

**Mesh（网状）**：Agent 之间直接通信，没有中心节点。A 可以直接委托 B，B 可以直接委托 C。每个 Agent 通过 ARD 独立发现其他 Agent。

| 优点 | 缺点 |
|------|------|
| 无单点——任意 Agent 挂了不影响其他 | 拓扑复杂——N 个 Agent 有 N(N-1)/2 条潜在连接 |
| 延迟更低——不需要经过编排器 | 治理失控——谁调了谁、为什么调，难以追踪 |
| 适合大型生态（50+ Agent） | 协议版本碎片化——每个 Agent 可能跑不同版本的 A2A |

**实践中怎么做**：纯 Mesh 在工程上几乎不可行——不是因为协议不支持（A2A 完全支持），而是因为治理成本太高。大多数生产系统用的是**受控 Hub-Spoke**：编排器做主要路由，但对于高频、低延迟的交互（比如数据 Agent → 可视化 Agent 的流式管道），允许直连。

A2A 协议层面不强制任何拓扑——它只定义了 Agent 之间点对点通信的格式。拓扑选择是架构决策，需要根据你的系统规模、治理需求、延迟要求来定。关键不是选哪个，而是**意识到你需要选**——很多团队上线三个月才发现 Agent 之间形成了意外的网状调用，排查一个问题要翻五个 Agent 的日志。

---

## 10.5.9 版本协商与扩展

A2A 通过 `A2A-Version` 请求头做版本协商，超出核心规范的扩展能力通过 Agent Card 的 `extensions` 字段声明（如 `"extensions": ["x-progress-v1"]`），Message 中用带前缀字段——不认识该扩展的客户端忽略即可。这套机制借鉴自 HTTP 版本协商和 gRPC 扩展模式。核心原则：服务端应兼容最近几个主版本，给生态迁移窗口。

为什么这个原则不能只是"原则"？想象一个场景：你的企业里有 15 个 Agent，8 个跑 A2A v1.0，7 个还在 v0.4。如果 v1.0 服务端不兼容 v0.4 客户端，那 7 个 Agent 在升级窗口期内就全废了——而你不可能一夜之间把所有 Agent 全升级。这就是"迁移窗口"的实际含义：不是协议设计者的洁癖，是生产环境的刚需。

扩展机制同样重要，但容易被滥用。`extensions` 的正确用法是"A2A 没覆盖的通用能力"——比如自定义的进度报告格式。错误用法是把业务逻辑塞进扩展字段：`"x-mycompany-refund-flow-v1"`。这不是扩展，这是把 A2A 当成了你的私有 RPC 协议。扩展是给生态的，不是给单个业务的。

---

## 10.5.10 协议检查清单

选框架和平台时，按以下清单逐项验证：

| 检查项 | 含义 | 为什么不能忽略 |
|--------|------|---------------|
| 支持 MCP 吗？ | 工具生态对接 | Agent 能不能调用现有工具链 |
| 支持 A2A 吗？ | 跨 Agent 协作 | Agent 能不能找别的 Agent 帮忙 |
| A2A 支持哪些认证方式？ | 跨组织安全 | 能不能给外部 Agent 派任务 |
| 支持 Streaming / Push 吗？ | 实时 + 异步 | 短交互和长任务分别走什么路径 |
| Agent Card 可动态更新吗？ | 发现可靠性 | Card 过期后会不会静默失败 |
| A2A 的 Task 超时可配置吗？ | 生产韧性 | 慢 Agent 会不会拖死编排器 |
| 支持哪种拓扑？Hub-Spoke / Mesh？ | 架构灵活性 | 5 个 Agent 和 50 个 Agent 需要不同的拓扑 |

说一个我们自己踩过的坑：**不要假设"支持 A2A"就是"完整支持"**。有些框架宣称支持 A2A，实际上只实现了 `tasks/send` 和 `tasks/get`——没有 streaming、没有 push notification、Agent Card 是写死的模板。这种"支持"在原型阶段能用，进生产的第一天就会出问题。验证方法很简单：看它的 Agent Card 能不能动态修改，看它的 streaming 是不是基于 SSE 而非伪装的 polling。

---

## 后记：开源项目参考

如果你读完这一节后想动手试试，以下是值得关注的开源项目。

### 官方 SDK 生态（a2aproject）

A2A 协议的核心仓库托管在 GitHub 组织 [a2aproject](https://github.com/a2aproject) 下，由 Linux Foundation 治理，Apache-2.0 许可：

| 仓库 | 语言 | Stars | 说明 |
|------|------|-------|------|
| [A2A](https://github.com/a2aproject/A2A) | Shell/Markdown | 24.7k | 核心协议规范和技术文档，含完整的 JSON Schema 定义 |
| [a2a-python](https://github.com/a2aproject/a2a-python) | Python | 2k | 官方 Python SDK，最成熟——支持完整的 Task 状态机、SSE streaming、Push Notification |
| [a2a-js](https://github.com/a2aproject/a2a-js) | TypeScript | 570 | 官方 JavaScript/TypeScript SDK |
| [a2a-java](https://github.com/a2aproject/a2a-java) | Java | 455 | 官方 Java SDK |
| [a2a-go](https://github.com/a2aproject/a2a-go) | Go | 418 | 官方 Go SDK |
| [a2a-dotnet](https://github.com/a2aproject/a2a-dotnet) | C# | 243 | 官方 C#/.NET SDK |
| [a2a-rs](https://github.com/a2aproject/a2a-rs) | Rust | — | 官方 Rust SDK |

除了语言 SDK，还有三个重要的辅助仓库：

- **[a2a-samples](https://github.com/a2aproject/a2a-samples)**：多智能体协作的完整示例集。最值得看的是 `extensions/agp/sim/enterprise-v1`——模拟跨框架（ADK / LangChain / LangGraph）企业委派场景，涵盖财务、工程、市场、HR、合规五个部门的 Agent 协作。还有基于 FastAPI 的交互式 Web GUI，可以直接在浏览器里调试 A2A 通信。
- **[a2a-inspector](https://github.com/a2aproject/a2a-inspector)**：协议符合性验证 UI 工具——把你的 Agent Card URL 贴进去，它会自动检查格式合法性、端点可达性、认证配置是否正确。生产上线前跑一遍能省很多调试时间。
- **[a2a-tck](https://github.com/a2aproject/a2a-tck)**（Technology Compatibility Kit）：自动化协议合规性测试套件，验证你的 Agent 实现是否严格遵循 v1.0 规范。

### Google ADK（Agent Development Kit）

[google/adk-docs](https://github.com/google/adk-docs)，Apache-2.0，Google 官方的"代码优先"Agent 开发框架。它的 A2A 支持是目前所有框架中最成熟的——原生支持 Agent Card 发布、Task 生命周期管理、SSE 流式传输和 Push Notification。如果你用 Gemini 生态，ADK + A2A 是最短路径。Google 还提供了免费的 [Codelab 教程](https://codelabs.developers.google.com/codelabs/currency-agent)（MCP + ADK + A2A 三合一实战）。

### DeepLearning.AI 短课程

[A2A: The Agent2Agent Protocol](https://goo.gle/dlai-a2a)，由 Google Cloud 和 IBM Research 联合制作，约 1 小时。从零搭建一个多 Agent 协作系统（root agent → local sub-agent → remote A2A agent），适合快速建立直觉。免费。

### 一个提醒

开源 SDK 不等于生产就绪。我们在 §10.5.10 检查清单里提过——有些框架宣称"支持 A2A"，实际只实现了 `tasks/send` 和 `tasks/get`。用 a2a-inspector 跑一下你的 Agent 端点，比看 README 里的勾号靠谱得多。

---

本节是第十章（多智能体治理）的深化内容。A2A 的生态位（与 MCP/ARD 的关系、框架支持情况、市场格局）见第十二章 §12.6 的协议栈全景分析。
