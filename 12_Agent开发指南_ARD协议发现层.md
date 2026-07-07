# 第十二章补充：ARD 协议——发现层，Agent 的搜索引擎

> 本章是第十二章（生态工具）§12.6 的扩展内容，补充协议栈的"发现层"。阅读前提：已了解 MCP 和 A2A 的基本概念。

---

## 12.6.3 ARD：发现层——"有什么可用？谁提供的？可信吗？"

### 12.6.3.1 问题：Agent 怎么知道"有什么可用"？

你的编排 Agent 接到一个任务：**"帮我做一份 2026 Q2 的销售分析报告"**。

它脑子里有个粗略的计划——先拉数据、再画图表、最后写分析。但它不知道：公司里有没有一个能拉销售数据的 Agent？有没有能画图表的 Agent？它们叫什么、在哪里、怎么调？

2025 年之前，这个问题只有一个答案：手动配置。把每个 Agent 的 URL 硬编码在编排器的配置文件里。Agent 数量涨到 50 个的时候，配置文件已经 800 行——每次新增 Agent 改 5 个地方，每次 Agent 换域名改 8 个地方。

我们第一次搭企业内部 Agent 平台时，Agent 数量从一个季度的 5 个涨到下一个季度的 50 个。不是夸张——财务部、销售部、HR 部门、IT 运维，每个部门都搞了自己的 Agent。管配置文件的那个人离职了，没人知道哪些 Agent 还活着、哪些 URL 已经 404 了。

ARD 就是把"手动配置"变成"自动发现"的协议。

它"坐在调用之前"——帮 Agent 回答三个问题：**有什么可用？怎么找到？可信吗？** 然后退场。实际的执行还是 A2A 或 MCP 的事。

---

### 12.6.3.2 四阶段发现流程

ARD 的完整工作流分四步。把它想象成一个搜索引擎的建立过程，每一步都对应现实搜索引擎的一个阶段：

```
阶段一          阶段二              阶段三              阶段四
  发布    →     索引构建      →     动态搜索      →     调用执行
  │              │                   │                   │
  │       Registry 爬取           编排器发送          编排器用 A2A/MCP
  │       ai-catalog.json         POST /search         调用选中的资源
  │       构建语义向量索引         获取匹配列表
  │                               │
  Well-Known URI                  语义向量匹配         ARD 退场
  静态清单                        + 联邦路由            具体协议接管
```

**阶段一（发布）**：资源提供者在自己的域名下埋一个静态 JSON 文件，声明"我这里有这些资源，它们能干什么"。

**阶段二（索引）**：Registry（发现服务）定期爬取这些清单，把自然语言描述转成向量嵌入，构建语义索引。注意——Registry 不存 Agent 本身，只存"能找到 Agent 的线索"。

**阶段三（搜索）**：编排器把用户任务（"帮我做销售分析报告"）转成自然语言搜索请求，发给 Registry。Registry 做语义匹配，返回按相关性排序的资源列表——不是关键词匹配，是语义理解。

**阶段四（调用）**：编排器拿到资源引用后，用 A2A（如果是 Agent）或 MCP（如果是工具）去调。ARD 的工作到这里就结束了。

在这四步里，阶段二（索引构建）是整个系统的核心——它的质量决定了 ARD 是"能用"还是"好用"。先看 Registry 内部长什么样，再展开阶段一和三的细节。

Registry 本质上是一个**语义搜索引擎 + 联邦路由器**。它的内部有三个核心组件：

1. **爬取调度器**：定期从已知域名拉取 `ai-catalog.json`，维护一个"哪些域名有新内容"的变更日志。不是实时 push——是定期 pull。这意味着新发布的 Agent 不会立即被搜到，存在一个索引延迟（通常 1-5 分钟，取决于 Registry 配置）。
2. **向量索引**：将每个资源的 `description` 和 `representativeQueries` 向量化（embedding），存入向量数据库（如 pgvector、Milvus、Qdrant）。搜索时用自然语言查询做语义匹配，不是关键词匹配——"帮我做销售报告"能匹配到 `description: "Generates quarterly sales analysis"` 即使没有一个词完全一样。

> **向量化是什么？** 如果你不熟悉这个概念，把它想象成"给每段文字找一个坐标"。传统搜索是"对暗号"——你搜"销售报告"，它只匹配出现过"销售"和"报告"这两个词的地方。向量搜索是"找邻居"——它把一段文字变成一串数字（比如 768 个浮点数），然后把这些数字当成它在高维空间里的坐标。两段文字含义越接近，它们的坐标就越靠近。所以"帮我做销售分析"能找到"Generates quarterly revenue breakdown"——虽然中英文不同、用词不同，但含义接近，在向量空间里是邻居。
3. **联邦代理**：当本地索引没找到足够相关的结果时，根据联邦配置（auto/referrals/none）决定是否向上游 Registry 转发查询，合并去重后返回。

这三个组件里，向量索引的质量决定了 ARD 的可用性——如果"找销售数据分析 Agent"返回"天气查询 Agent"，用户不会再用第二次。而索引质量的核心变量不是模型，是 `representativeQueries` 写得好不好。这一点在展开讲阶段一的 AI Catalog 时会看得更清楚。

---

### 12.6.3.3 Well-Known URI：在域名下埋线索

ARD 的发现入口不是一个中心化的注册中心，而是一个**分布式的约定**：每个资源提供者在自己的域名下，把资源清单放在标准路径上。

路径就一条：`https://{domain}/.well-known/ai-catalog.json`

比如 Salesforce 把自己的 CRM Agent 注册在 `https://salesforce.com/.well-known/ai-catalog.json`，Workday 在自己的域名下放一份。Registry 只需要知道域名，就能找到清单。

但这个路径不是唯一入口。ARD 同时定义了四种发现方式，优先级从高到低：

1. **DNS SVCB 记录**：最优雅的方式——在 DNS 里加一条记录，客户端不用猜路径
2. **Well-Known URI**：`/.well-known/ai-catalog.json`——没有 DNS 权限时的首选
3. **robots.txt**：`Agentmap: https://example.com/catalog.json`——对已有网站改动最小
4. **HTML `<link>` 标签**：`<link rel="ai-catalog" href="...">`——适合有 Web 前端的服务

一份简化但真实的 AI Catalog 清单：

```json
{
  "resources": [
    {
      "identifier": "urn:air:salesforce.com:crm:lead-enrichment",
      "type": "application/vnd.a2a.agent-card+json",
      "url": "https://salesforce.com/.well-known/agent-card.json",
      "description": "Enriches sales leads with firmographic data, contact details, and intent signals",
      "representativeQueries": [
        "Find company info for a lead",
        "Enrich lead with social profiles",
        "Check lead's recent funding news"
      ],
      "capabilities": ["lead-enrichment", "data-appending", "company-research"],
      "tags": ["sales", "crm", "lead", "b2b"]
    }
  ]
}
```

字段本身不复杂，但每个都有工程考量。`identifier` 是全局唯一的 URN（下一节细讲）。`representativeQueries` 是整份清单里最巧妙的设计——2 到 5 个自然语言示例查询，Registry 把它们向量化，作为语义搜索的种子。没有这个字段，Registry 只能靠 `description` 和 `tags` 做粗糙的文本匹配，召回质量会差很多。

本质上，`representativeQueries` 就是"你觉得用户会用什么样的自然语言找到你？"。写得好不好，直接决定你的 Agent 能不能被搜到。

---

### 12.6.3.4 URN 标识符：每项资源的"身份证号"

AI Catalog 里的每个资源都有一个 `urn:air:` 开头的标识符。为什么不用 URL？

因为 URL 指向的是**物理位置**——`https://salesforce.com/agents/crm`。如果 Salesforce 把 Agent 迁移到 `https://agents.salesforce.com/`，所有调用方的配置都废了。

URN 是**逻辑身份**——跟物理位置无关。格式：

```
urn:air:<publisher>:<namespace>:<agent-name>
  │    │       │           │            │
  │    │       │           │            └── 资源名称
  │    │       │           └── 可选层级（部门/团队/项目）
  │    │       └── FQDN（组织信任锚点）
  │    └── Agentic AI Resource 命名空间
  └── 固定前缀
```

举个例子：`urn:air:salesforce.com:crm:lead-enrichment`

- `salesforce.com` 是发布者——倒过来写的域名，天然全局唯一
- `crm` 是命名空间——Salesforce 的 CRM 部门
- `lead-enrichment` 是资源名——具体干了什么

FQDN 作为信任锚点是一个很聪明的设计。`salesforce.com` 这个域名是经过 DNS 验证的——你说你是 Salesforce 的资源，你得有 `salesforce.com` 这个域名。不需要额外的 CA 证书体系。

而且不同组织的同名 Agent 天然不会冲突：`urn:air:acme.com:hr:onboarding` 和 `urn:air:globex.com:hr:onboarding` 是两个完全不同的标识符。联邦搜索合并多个 Registry 的结果时，不会有命名碰撞。

---

### 12.6.3.5 联邦搜索：跨 Registry 的联合发现

一个 Registry 不可能索引全世界的所有 Agent。企业内部 Registry 只索引内部 Agent，公共 Registry 索引公开 Agent——但编排器需要同时搜两者。

ARD 的联邦机制让多个 Registry 像一个整体一样工作。三种模式：

| 模式 | Registry 的行为 | 什么时候用 |
|------|----------------|-----------|
| **`auto`** | 自动查询上游 Registry，合并结果统一返回 | 用户不想关心"结果从哪来" |
| **`referrals`** | 返回自身结果 + 其他 Registry 的引用地址 | 客户端要控制搜索范围和优先级 |
| **`none`** | 仅搜索自身索引 | 隔离环境：内部 Registry 不暴露给外部 |

回到开头的销售报告场景，它在实际运作中会这样走：

> 编排 Agent 先搜企业内部 Registry → federation: none，返回两个 Agent：数据查询 Agent（拉销售数据库）+ 文案 Agent（写分析文本）。
>
> 但企业内部没有可视化 Agent。编排器切换 federation: referrals → 企业内部 Registry 返回自身结果，外加一个公共 Registry 的引用（`"federationReferrals": ["https://public-agent-registry.example.com"]`）→ 编排器跟进公共 Registry → 找到三个可视化 Agent。
>
> Trust Manifest 过滤掉两个没有 SOC2 认证的 → 选中最可信的那个 → 调它画图表。

整个过程编排器写了不到 15 行代码——剩下的都是协议的事。

但有一个必须考虑的故障模式：**上游 Registry 不可达**。公共 Registry 挂了、网络断了、或者它正在做索引重建——编排器发过去的搜索请求超时。这种情况下的降级策略有三种：

1. **硬降级**：只用本地结果，标记"部分结果可能不可用"。适合内部 Registry 覆盖率高的场景。
2. **缓存兜底**：编排器维护一个本地 Agent 引用缓存（最近 24 小时内成功调过的 Agent URN + URL），Registry 不可达时直接走缓存。适合关键业务 Agent 固定的场景。
3. **静态配置 fallback**：在编排器的配置文件里维护一份"关键 Agent 清单"——不管 Registry 返回什么，这些 Agent 始终可用。这是最保守也最可靠的策略。

三种策略不互斥——生产环境通常是"Registry 优先 → 缓存兜底 → 静态配置保底"的三层降级链。

---

### 12.6.3.6 Trust Manifest：能搜到 ≠ 能用

搜索结果的 `score` 字段是相关性评分——"这个 Agent 跟你描述的需求多匹配"。但匹配不等于可信。

Trust Manifest 是 ARD 里专门解决"可信性"的部分。它由四块组成：

- **`identity`**：加密身份标识——SPIFFE ID、DID 或 HTTPS URI。不是自报家门，是经过加密验证的身份。如果你不熟悉这两个缩写：SPIFFE 是云原生领域的身份标准（"这个微服务确实是 `payment-service.prod` 而不是冒牌货"），DID 是 W3C 的去中心化身份标准（"我是我自己，不需要靠 Google 或 Facebook 来证明"）。Trust Manifest 不强制用哪个——它接受任何经过加密绑定的身份格式。
- **`attestations`**：合规认证列表——SOC2、HIPAA、GDPR、ISO27001 等。不是自己说"我们很安全"，是审计机构签发的。
- **`provenance`**：来源血缘链——这个资源是从哪里派生/发布出来的。如果它声称是 Salesforce 的 Agent、但实际上来自一个 GitHub Pages 地址——provenance 链会暴露这一点。
- **`signature`**：Detached JWS 签名——防止整个 Manifest 被篡改。"Detached"（分离式）的意思是签名不嵌在 Manifest 的 JSON 里面，而是单独存放——这样 Manifest 本身保持干净的 JSON 结构，验证时把 Manifest 原文和签名拼在一起做校验。好处是不污染数据格式，坏处是你得同时保管两个东西（Manifest + 签名文件）。

这四个维度回答的不是"这个 Agent 厉不厉害"，而是"这个 Agent 能进生产环境吗"。

我们有一个真实的教训：某个数据分析 Agent 声称能访问公司的财务数据库。搜索匹配度很高——90% 相关性。但 Trust Manifest 里它的 `attestations` 是空的。合规团队直接禁止了调用。后来发现那是一个实习生搭的 side project，确实能连财务库——但没有审计日志，没有访问控制。

Trust Manifest 让合规检查从"人工逐一审核"变成了"可编程过滤"。企业内部 Registry 可以配置策略：自动拒绝缺少 SOC2 认证的外部 Agent、标记 HIPAA 认证缺失的 Agent 为"高风险"、只允许来自 `*.company.com` FQDN 的资源进入索引。但这里有一个重要前提：**Trust Manifest 提供的是元数据，不是审计结论**。SOC2 认证字段可以被人填写，JWS 签名只能保证这个 Manifest 在传输中没被篡改——不能保证填写内容是真的。最终的可信性仍然需要 Registry 运营方对发布者做离线验证（比如通过 DNS FQDN 确认身份、交叉比对公开的合规认证数据库）。Trust Manifest 让这个流程可以自动化，但不能替代这个流程。

---

### 12.6.3.7 与现有服务发现的区别

做后端架构的人第一次看到 ARD，通常会问："这不就是又一个服务发现吗？Consul、etcd、Kubernetes Service 不是都能干这个？"（如果你没用过这些：Consul 是 HashiCorp 的服务注册工具，etcd 是 Kubernetes 的配置存储，K8s Service 是 Kubernetes 里让 Pod 之间互相找到对方的机制——它们解决的都是"一个服务怎么找到另一个服务的网络地址"的问题。）

它们解决的问题层不同：

| 维度 | ARD | Consul / K8s Service |
|------|-----|---------------------|
| **发现方式** | 自然语言语义搜索 | 精确名称匹配（`service-name.namespace`） |
| **发现粒度** | 按能力搜索（"能做销售分析的 Agent"） | 按名称查找（"sales-db.ns-prod"） |
| **标识体系** | URN（逻辑身份，与物理位置解耦） | IP:Port（物理位置） |
| **信任模型** | Trust Manifest（身份+合规+血缘+签名） | mTLS / ServiceAccount（网络层身份） |
| **跨组织** | 原生支持——FQDN 做信任锚点 | 需要额外基础设施（Mesh Federation） |

关键区别就一个：Consul 回答的是 **"sales-db 服务在哪个 IP 上？"**，ARD 回答的是 **"有什么 Agent 能帮我分析销售数据？"**。前者是基于名称的查找，后者是基于意图的发现。

两者不是替代关系。一个 A2A Agent 在 Kubernetes 集群里运行时，它既需要 ARD 来发现其他 Agent（按能力搜索），也需要 K8s Service 来做网络路由（按名称解析到 Pod IP）。ARD 坐在服务发现的上面一层——它帮你找到"谁"，但不管"在哪个 IP 上"。

---

### 12.6.3.8 三协议协作全景

让我们用一个完整的场景，把 ARD、A2A、MCP 串起来。还是那个销售报告任务。

```
阶段           协议              发生了什么
────────────────────────────────────────────────
发现           ARD               编排器问企业 Registry："销售数据分析 + 可视化"
                                 Registry 返回 3 个匹配的资源引用

解析           ARD + A2A         编排器通过 Agent Card URL 获取每个 Agent 的详细信息
                                 验证 JWS 签名，确认卡片未被篡改

委托           A2A               编排器向数据 Agent 发 Task："拉取 2026 Q2 销售数据"
                                 数据 Agent 进入 WORKING 状态

工具调用       MCP               数据 Agent 内部通过 MCP 调用数据仓库的 SQL 查询工具
                                 一条 SQL，返回结构化数据

交付           A2A               数据 Agent 返回 Artifact（data Part：结构化销售数据）
                                 任务状态 → COMPLETED

再次委托       A2A               编排器把数据传给可视化 Agent → Task："生成趋势图"
                                 可视化 Agent 返回 Artifact（url Part：图表链接）

再次委托       A2A               编排器把图表链接 + 数据传给文案 Agent → Task："写分析报告"
                                 文案 Agent 返回 Artifact（text Part：Markdown 报告）

聚合           —                 编排器把所有 Artifact 组装成最终报告
```

每一层协议都在自己该出现的时候出现，做自己该做的事，然后退场。

ARD 找到了三个 Agent 之后就不再参与；A2A 管理了每个任务的完整生命周期；MCP 在 Agent 内部安静地调工具。没有哪层越界。

---

### 成熟度评估

ARD v0.9 于 2026 年 6 月发布，Google、Microsoft、Hugging Face、GoDaddy 联合工作组推动。本书截稿时的生态状态：

| 维度 | 状态 |
|------|------|
| **协议稳定性** | v0.9，v1.0 路线图已公布，核心发现流程基本稳定 |
| **公开 Registry** | 建设中，尚无生产级公共 Registry |
| **企业 Registry** | Google/Hugging Face 有内部实现，开源方案（Ardorman）在早期阶段 |
| **Trust Manifest** | 格式已定，合规认证字段的标准化尚在讨论 |
| **框架支持** | Google ADK 原生支持，LangChain/LangGraph 适配器开发中 |

现阶段的生产策略：ARD 搜索做主要发现通道，但对于关键 Agent（财务、合规、核心业务），同步维护静态配置。这是"Registry 优先 → 缓存兜底 → 静态保底"三层降级链（详见 §12.6.3.5 联邦搜索小节）的具体落地。等 v1.0 生态成熟后再切掉静态配置——但从协议设计来看，ARD 工作组吸取了 MCP 早期迭代的教训（MCP 经历了多次不兼容的协议变更），一开始就明确了分层架构和联邦模型，少走了很多弯路。

---

## 后记：开源项目参考

ARD 生态还很年轻（v0.9 于 2026 年 6 月发布），但已经有值得关注的开源项目。

### 官方规范仓库

[ards-project/ard-spec](https://github.com/ards-project/ard-spec)，Apache-2.0 许可。这是 ARD 协议的权威规范仓库，内容包括：

- `spec/ard.md` — 协议规范正文
- `spec/schemas/` — CDDL、JSON Schema、OpenAPI 定义（可以直接用于代码生成）
- `adr/` — 架构决策记录（了解"为什么这么设计"的最佳入口）
- `conformance/` — 一致性测试工具（含 Python 参考 Registry Server 实现）

如果你只想看一个仓库来理解 ARD，看这个就够了。规范本身不到 2000 行 Markdown，比大多数 RFC 好读。

### OpenARD：独立开源实现

[iFurySt/ard](https://github.com/iFurySt/ard)（OpenARD），Go 语言编写，Apache-2.0 许可。这是目前最完整的 ARD 独立实现，面向企业和 Agent 平台的自托管场景。核心能力：

| 模块 | 功能 |
|------|------|
| **Registry Server** | 基于 Gin + GORM/Postgres 的自托管注册中心，支持 Prometheus 指标、W3C traceparent 追踪、OTLP trace 导出 |
| **CLI + Go SDK** | `ardctl` 命令行工具 + `pkg/ard` Go SDK，兼容性策略见 `docs/SDK_COMPATIBILITY.md` |
| **多协议资源接入** | MCP（`application/mcp-server-card+json`）、A2A（`/.well-known/agent-card.json`）、Skills（`SKILL.md`）、OpenAPI（`openapi.json`） |
| **目录爬取** | 自动发现并解析 `/.well-known/ai-catalog.json`，批量导入远端资源 |
| **JWS 签名验证** | 支持 Ed25519、本地/远程 JWKS、`did:web`、OIDC `jwks_uri`、SPIFFE bundle 等多种信任锚 |
| **策略引擎** | `--policy-file` 可施加摄入策略——比如"没有 Trust Manifest 的资源不允许持久化" |
| **联邦搜索** | 支持客户端 referral 模式和有界服务端 auto 模式，跨 Registry 合并去重 |
| **审计链** | 审计事件哈希链式存储，`ardctl admin audit --verify-chain` 验证完整性 |

OpenARD 的核心理念就是 README 里的那句话："MCP、A2A、Skills 和 APIs 定义的是能力**如何被使用**，ARD 定义的是它们**如何被找到**。"

### 与 §12.6.3.5 降级链的配合

如果你按照本章建议的"三层降级链"部署，OpenARD 非常适合做**第一层（Registry 优先）**的自托管注册中心，搭配静态配置做保底。它的 admin API 支持禁用/重新激活资源、审核待审条目——这些治理功能正是企业级 Agent 平台需要的。

---

本节是第十二章（生态工具）§12.6 的扩充内容。A2A 的深度工程解析（Agent Card 结构、Task 生命周期、多轮交互模式）见第十章 §10.5 扩展——`10_Agent开发指南_A2A协议深度解析.md`。
