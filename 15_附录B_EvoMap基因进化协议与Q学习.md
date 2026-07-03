# 附录B：EvoMap 基因进化协议与 Q 学习

本文档是"Agent自我进化概述"的专题深度附录，完整收录 EvoMap 基因进化协议的全部内容。

### GEP协议简介

**EvoMap**是一个协作进化网络，其中AI Agent发布和获取经过验证的解决方案（Gene + Capsule bundles）。

**三个核心概念**：

- **Gene（基因）**：经过验证的解决方案片段

- **Capsule（胶囊）**：打包的技能/工具

- **Evolution（进化）**：通过反馈持续改进

### Capability Evolver技能

```markdown
---
name: capability-evolver
description: A self-evolution engine for AI agents. 
  Analyzes runtime history to identify improvements 
  and applies protocol-constrained evolution.
tags: [meta, ai, self-improvement, core]

---

# 🧬 Capability Evolver

The Capability Evolver is a meta-skill that allows agents to:

1. 监控运行时历史

2. 识别失败或低效

3. 自主进化代码和记忆
```

### Self-Evolve插件架构

```python
# Self-Evolve工作流程
flowchart TD
    A[收到用户消息] --> B{反馈轮次?}
    B -- Yes --> C[奖励打分 + 学习门检查]
    C --> D{应该学习?}
    D -- Yes --> E[本地记忆脱敏]
    E --> F[LLM总结 + 二次脱敏]
    F --> G[追加本地记忆triplet]
    G --> H[可选：远程摄入]
    D -- No --> I[跳过学习]
    B -- No --> J[意图识别 + 任务边界]
    J --> K[检索本地+远程候选]
    K --> L[Phase-B排序选择记忆]
    L --> M[注入记忆 + 生成回复]
```

### Q值强化学习

```python
class EpisodicMemory:
    """情景记忆 - 基于Q值的学习"""
    
    def __init__(self):
        self.memories = []  # 记忆列表
        self.q_values = {}  # Q值表
    
    def update_q_value(self, memory_id: str, reward: float) -> None:
        """更新Q值 - 基于强化学习"""
        if memory_id not in self.q_values:
            self.q_values[memory_id] = 0.0
        
        # Q-Learning更新
        learning_rate = 0.1
        discount_factor = 0.9
        
        self.q_values[memory_id] += learning_rate * (
            reward - self.q_values[memory_id]
        )
    
    def retrieve(self, intent: str, top_k: int = 3) -> List[Dict]:
        """检索最相关的记忆"""
        # 计算嵌入相似度
        candidates = []
        intent_embedding = self._embed(intent)
        
        for memory in self.memories:
            similarity = self._cosine_similarity(
                intent_embedding, 
                memory['embedding']
            )
            candidates.append((similarity, memory))
        
        # 按相似度排序
        candidates.sort(reverse=True)
        return [m for _, m in candidates[:top_k]]
```

### 学习门配置

```yaml
# 学习门配置
runtime:
  observeTurns: 0                    # 观察轮数
  minAbsReward: 0.15               # 最小绝对奖励
  minRewardConfidence: 0.55         # 最小奖励置信度
  learnMode: "balanced"            # 学习模式

# 学习模式

# balanced: 优先工具轮；无工具轮需高奖励

# tools_only: 仅学习有工具调用的轮次

# all: 所有通过门的学习
```
