# -*- coding: utf-8 -*-
"""
验证第07/08/09/12/13章新增代码块（不依赖外部库的纯 Python 部分）
"""
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import json
import os
import re
import time
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import List, Optional, Dict
from collections import Counter


# ============================================================
# 第07章：记忆数据备份 & 生命周期管理（无向量库依赖部分）
# ============================================================

print("=" * 60)
print("第07章：记忆生命周期管理")
print("=" * 60)


class MemoryLifecycleManager:
    """记忆生命周期管理：价值评分 + 自动淘汰（不含向量库调用）"""

    RETENTION_POLICY = {
        "user_preference": -1,
        "constraint_rule": -1,
        "project_state": 180,
        "conversation_log": 30,
        "temp_context": 7,
    }

    def score_memory_value(self, content: str, metadata: dict) -> float:
        score = 0.0

        if len(content) > 20:
            score += 0.3
        if len(content) > 100:
            score += 0.2

        memory_type = metadata.get("type", "conversation_log")
        type_weights = {
            "user_preference": 1.0,
            "constraint_rule": 1.0,
            "project_state": 0.7,
            "conversation_log": 0.3,
            "temp_context": 0.1,
        }
        score += type_weights.get(memory_type, 0.3)

        access_count = metadata.get("access_count", 0)
        score += min(access_count * 0.05, 0.5)

        return min(score, 1.0)


mgr = MemoryLifecycleManager()
score1 = mgr.score_memory_value(
    "用户偏好：不喜欢超过3步的操作流程",
    {"type": "user_preference", "access_count": 10}
)
score2 = mgr.score_memory_value("嗯", {"type": "conversation_log", "access_count": 0})
print(f"长期偏好记忆评分: {score1:.2f}")   # 应接近 1.0
print(f"无意义对话评分:   {score2:.2f}")   # 应较低
assert score1 > score2, "价值评分逻辑有误"
print("[PASS] 07章记忆评分逻辑正确")


# ============================================================
# 第08章：RAG 评估器 & 文档质量检查器（无 LLM 依赖部分）
# ============================================================

print("\n" + "=" * 60)
print("第08章：RAG 评估与文档质量")
print("=" * 60)


class RAGEvaluatorBasic:
    """RAG 检索层评估（不依赖 LLM）"""

    def evaluate_retrieval_recall(
        self,
        query: str,
        retrieved_docs: List[str],
        ground_truth_docs: List[str],
    ) -> Dict:
        retrieved_set = set(retrieved_docs)
        truth_set = set(ground_truth_docs)

        hits = len(retrieved_set & truth_set)
        recall = hits / len(truth_set) if truth_set else 0
        precision = hits / len(retrieved_set) if retrieved_set else 0
        f1 = 2 * recall * precision / (recall + precision + 1e-9)

        return {
            "recall": round(recall, 3),
            "precision": round(precision, 3),
            "f1": round(f1, 3),
            "hits": hits,
        }


evaluator = RAGEvaluatorBasic()
result = evaluator.evaluate_retrieval_recall(
    query="什么是向量数据库",
    retrieved_docs=["doc_A", "doc_B", "doc_C"],
    ground_truth_docs=["doc_A", "doc_C", "doc_D"],
)
print(f"检索评估结果: {result}")
assert result["hits"] == 2
assert abs(result["recall"] - 0.667) < 0.01
print("[PASS] 08章 RAG 检索评估逻辑正确")


class DocumentQualityChecker:
    """文档解析质量检查器"""

    def check_parsing_quality(self, file_size_kb: float, parsed_text: str) -> Dict:
        issues = []
        score = 1.0

        expected_min_chars = file_size_kb * 50
        if len(parsed_text) < expected_min_chars * 0.3:
            issues.append(f"文本过短（{len(parsed_text)} 字符），可能解析失败")
            score -= 0.4

        garbled_pattern = r'[□■▪▫●○◆◇]{3,}'
        garbled_count = len(re.findall(garbled_pattern, parsed_text))
        if garbled_count > 5:
            issues.append(f"发现 {garbled_count} 处可能的乱码区域")
            score -= 0.2

        table_refs = re.findall(r'表\s*\d+', parsed_text)
        table_contents = re.findall(r'\|.+\|', parsed_text)
        if len(table_refs) > 0 and len(table_contents) == 0:
            issues.append(f"文档引用了 {len(table_refs)} 处表格，但未检测到解析后的表格内容")
            score -= 0.3

        return {
            "quality_score": max(0, round(score, 2)),
            "char_count": len(parsed_text),
            "issues": issues,
            "recommendation": "建议人工复查" if score < 0.6 else "质量良好",
        }


checker = DocumentQualityChecker()
# 正常文档
good = checker.check_parsing_quality(10.0, "a" * 600)
assert good["quality_score"] == 1.0
# 过短文档（10KB 预期 500 字符，这里只给 50）
bad = checker.check_parsing_quality(10.0, "a" * 50)
assert bad["quality_score"] < 1.0
# 含乱码：用空格分隔确保产生多个独立匹配
garbled_text = "正常文本" + " □■▪" * 8 + "a" * 600
garbled = checker.check_parsing_quality(10.0, garbled_text)
assert garbled["quality_score"] < 1.0, f"乱码检测应触发，当前分数: {garbled['quality_score']}"
print("[PASS] 08章文档质量检查逻辑正确")


# ============================================================
# 第09章：规划保护器 & 规划缓存 & 执行计划（不含 Redis 调用）
# ============================================================

print("\n" + "=" * 60)
print("第09章：规划与推理")
print("=" * 60)


@dataclass
class PlanningMetricsV2:
    task_id: str
    start_time: float = field(default_factory=time.time)
    iterations: int = 0
    total_tokens: int = 0
    tool_calls: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    status: str = "running"

    def record_iteration(self, thought: str, action: str, tokens_used: int):
        self.iterations += 1
        self.total_tokens += tokens_used
        if action:
            self.tool_calls.append(action)

    def detect_loop(self, window: int = 5) -> bool:
        if len(self.tool_calls) < window:
            return False
        recent = self.tool_calls[-window:]
        return len(set(recent)) == 1

    def get_summary(self) -> Dict:
        elapsed = time.time() - self.start_time
        tool_counter = Counter(self.tool_calls)
        return {
            "task_id": self.task_id,
            "status": self.status,
            "iterations": self.iterations,
            "total_tokens": self.total_tokens,
            "elapsed_seconds": round(elapsed, 2),
            "most_called_tool": tool_counter.most_common(1)[0] if self.tool_calls else None,
            "errors": self.errors,
        }


class PlanningGuardV2:
    def __init__(
        self,
        max_iterations: int = 20,
        max_tokens: int = 50000,
        max_seconds: int = 120,
        loop_window: int = 5,
    ):
        self.max_iterations = max_iterations
        self.max_tokens = max_tokens
        self.max_seconds = max_seconds
        self.loop_window = loop_window

    def check(self, metrics: PlanningMetricsV2) -> Optional[str]:
        if metrics.iterations >= self.max_iterations:
            return f"超过最大迭代次数 {self.max_iterations}"
        if metrics.total_tokens >= self.max_tokens:
            return f"Token 消耗超过上限 {self.max_tokens}"
        elapsed = time.time() - metrics.start_time
        if elapsed >= self.max_seconds:
            return f"执行时间超过 {self.max_seconds} 秒"
        if metrics.detect_loop(self.loop_window):
            return f"检测到死循环：工具 '{metrics.tool_calls[-1]}' 连续调用 {self.loop_window} 次"
        return None


metrics = PlanningMetricsV2(task_id="test_task")
guard = PlanningGuardV2(max_iterations=5)

for i in range(6):
    metrics.record_iteration("thinking", "search_tool", 100)

stop_reason = guard.check(metrics)
assert stop_reason is not None, "应该检测到超过最大迭代次数"
print(f"规划保护触发: {stop_reason}")

# 测试死循环检测
metrics2 = PlanningMetricsV2(task_id="loop_test")
for _ in range(5):
    metrics2.record_iteration("thinking", "same_tool", 50)
assert metrics2.detect_loop(5), "应该检测到死循环"
print("[PASS] 09章规划保护和死循环检测逻辑正确")


# ============================================================
# 第09章：ExecutionPlan 断点续执（文件系统部分）
# ============================================================

class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PlanStep:
    step_id: str
    description: str
    tool_name: str
    tool_params: dict
    status: StepStatus = StepStatus.PENDING
    result: Optional[dict] = None
    error: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    plan_id: str
    task: str
    steps: List[PlanStep]
    checkpoint_path: str

    def save_checkpoint(self):
        checkpoint = {
            "plan_id": self.plan_id,
            "task": self.task,
            "steps": [
                {
                    "step_id": s.step_id,
                    "description": s.description,
                    "tool_name": s.tool_name,
                    "tool_params": s.tool_params,
                    "status": s.status.value,
                    "result": s.result,
                    "error": s.error,
                }
                for s in self.steps
            ],
        }
        with open(self.checkpoint_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint, f, ensure_ascii=False, indent=2)

    @classmethod
    def load_checkpoint(cls, checkpoint_path: str) -> "ExecutionPlan":
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        steps = [
            PlanStep(
                step_id=s["step_id"],
                description=s["description"],
                tool_name=s["tool_name"],
                tool_params=s["tool_params"],
                status=StepStatus(s["status"]),
                result=s.get("result"),
                error=s.get("error"),
            )
            for s in data["steps"]
        ]
        return cls(
            plan_id=data["plan_id"],
            task=data["task"],
            steps=steps,
            checkpoint_path=checkpoint_path,
        )

    def get_next_step(self) -> Optional[PlanStep]:
        completed_ids = {s.step_id for s in self.steps if s.status == StepStatus.SUCCESS}
        for step in self.steps:
            if step.status != StepStatus.PENDING:
                continue
            if all(dep in completed_ids for dep in step.dependencies):
                return step
        return None


# 测试 ExecutionPlan 保存和恢复
tmp_path = "c:\\Users\\jike\\Desktop\\agent 开发指南\\_test_checkpoint.json"
plan = ExecutionPlan(
    plan_id="plan_001",
    task="测试任务",
    steps=[
        PlanStep("s1", "搜索", "search", {"query": "test"}),
        PlanStep("s2", "分析", "analyze", {"data": "..."}, dependencies=["s1"]),
    ],
    checkpoint_path=tmp_path,
)
plan.save_checkpoint()

# 把第一步标为完成
plan.steps[0].status = StepStatus.SUCCESS
plan.steps[0].result = {"found": True}
plan.save_checkpoint()

# 重新加载
restored = ExecutionPlan.load_checkpoint(tmp_path)
assert restored.steps[0].status == StepStatus.SUCCESS
assert restored.steps[1].status == StepStatus.PENDING

next_step = restored.get_next_step()
assert next_step is not None and next_step.step_id == "s2"
print("[PASS] 09章 ExecutionPlan 断点续执逻辑正确")

# 清理临时文件
os.remove(tmp_path)


# ============================================================
# 第12章：LLMAdapter 框架隔离 & 加权路由（无 LangChain 依赖）
# ============================================================

print("\n" + "=" * 60)
print("第12章：框架选型实践")
print("=" * 60)

import random


def weighted_router(state: dict) -> str:
    """带权重的路由函数（无框架依赖版本，测试逻辑正确性）"""
    weights = state.get("route_weights", {"route_a": 0.7, "route_b": 0.3})
    routes = list(weights.keys())
    probs = list(weights.values())
    return random.choices(routes, weights=probs, k=1)[0]


# 统计分布是否大致符合权重
random.seed(42)
results = [weighted_router({"route_weights": {"route_a": 0.7, "route_b": 0.3}}) for _ in range(1000)]
a_ratio = results.count("route_a") / 1000
assert 0.6 <= a_ratio <= 0.8, f"加权路由分布异常: {a_ratio}"
print(f"[PASS] 12章加权路由逻辑正确，route_a 实际比例: {a_ratio:.2f}")


# ============================================================
# 第13章：多级兜底处理器 & 反馈收集器（无数据库依赖）
# ============================================================

print("\n" + "=" * 60)
print("第13章：用户体验设计")
print("=" * 60)


class AgentFallbackHandler:
    def handle(self, query: str, rag_result: dict) -> str:
        confidence = rag_result.get("confidence", 0)

        if confidence >= 0.8:
            return rag_result["answer"]

        elif confidence >= 0.5:
            return f"{rag_result['answer']}\n\n*注意：以上内容仅供参考，如涉及重要决策，建议以官方文件为准。*"

        elif confidence >= 0.2:
            related = rag_result.get("related_content", [])
            if related:
                suggestions = "\n".join([f"- {r}" for r in related[:3]])
                return f"我没有找到完全匹配的内容，但找到了一些相关信息：\n\n{suggestions}"

        return "抱歉，这个问题超出了我目前的知识范围。"


handler = AgentFallbackHandler()

r1 = handler.handle("test", {"confidence": 0.9, "answer": "高置信度回答"})
assert "高置信度回答" in r1
assert "注意" not in r1  # 高置信度不加免责声明

r2 = handler.handle("test", {"confidence": 0.6, "answer": "中置信度回答"})
assert "注意" in r2  # 中置信度要加免责声明

r3 = handler.handle("test", {"confidence": 0.3, "related_content": ["相关A", "相关B"]})
assert "相关A" in r3

r4 = handler.handle("test", {"confidence": 0.0})
assert "超出" in r4
print("[PASS] 13章多级兜底处理器逻辑正确")


# 验证安全过滤器（源自13章的错误信息人话化）
ERROR_MESSAGES = {
    "rate_limit_exceeded": "当前咨询量较大，请稍等 30 秒后重试。",
    "context_length_exceeded": "您的问题包含的内容太长了，请简化一下或分几次提问。",
    "model_timeout": "响应超时，可能是网络波动，请刷新后重试。",
    "knowledge_not_found": "我在知识库里没有找到相关内容。",
}

def user_friendly_error(error_code: str) -> str:
    return ERROR_MESSAGES.get(error_code, "遇到了一点小问题，请稍后重试。")

assert "30 秒" in user_friendly_error("rate_limit_exceeded")
assert "小问题" in user_friendly_error("unknown_error_xyz")
print("[PASS] 13章错误信息人话化逻辑正确")


print("\n" + "=" * 60)
print("全部验证通过！")
print("=" * 60)
