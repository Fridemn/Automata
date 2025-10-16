#!/usr/bin/env python3
"""
任务执行上下文
管理任务执行过程中的状态、工具调用历史、中间结果等
参考 OpenAI Agents SDK 的 RunContext 设计
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ToolCall:
    """工具调用记录"""

    call_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str | None = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    duration_ms: float = 0.0

    def complete(self, result: Any = None, error: str | None = None) -> None:
        """标记工具调用完成"""
        self.completed_at = datetime.now(timezone.utc)
        self.result = result
        self.error = error
        if self.completed_at and self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = delta.total_seconds() * 1000

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "call_id": self.call_id,
            "tool_name": self.tool_name,
            "arguments": self.arguments,
            "result": self.result,
            "error": self.error,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "duration_ms": self.duration_ms,
        }


@dataclass
class TaskStep:
    """任务执行步骤"""

    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    step_number: int = 0
    step_type: str = "tool_call"  # tool_call, llm_call, decision, completion
    description: str = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    llm_input: str | None = None
    llm_output: str | None = None
    decision: str | None = None
    intermediate_result: Any = None
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    duration_ms: float = 0.0
    status: str = "running"  # running, completed, failed

    def complete(
        self,
        status: str = "completed",
        intermediate_result: Any = None,
    ) -> None:
        """标记步骤完成"""
        self.completed_at = datetime.now(timezone.utc)
        self.status = status
        if intermediate_result is not None:
            self.intermediate_result = intermediate_result
        if self.completed_at and self.started_at:
            delta = self.completed_at - self.started_at
            self.duration_ms = delta.total_seconds() * 1000

    def add_tool_call(self, tool_call: ToolCall) -> None:
        """添加工具调用记录"""
        self.tool_calls.append(tool_call)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "step_id": self.step_id,
            "step_number": self.step_number,
            "step_type": self.step_type,
            "description": self.description,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
            "llm_input": self.llm_input,
            "llm_output": self.llm_output,
            "decision": self.decision,
            "intermediate_result": self.intermediate_result,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
        }


@dataclass
class TaskContext:
    """
    任务执行上下文
    参考 OpenAI Agents SDK 的 RunContext 设计，但简化为适合我们的场景
    """

    task_id: str
    session_id: str
    steps: list[TaskStep] = field(default_factory=list)
    current_step: TaskStep | None = None
    state: dict[str, Any] = field(default_factory=dict)  # 任务状态数据
    metadata: dict[str, Any] = field(default_factory=dict)  # 元数据
    max_steps: int = 50  # 最大步骤数，防止无限循环
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def step_count(self) -> int:
        """获取已执行的步骤数"""
        return len(self.steps)

    @property
    def total_tool_calls(self) -> int:
        """获取总工具调用次数"""
        return sum(len(step.tool_calls) for step in self.steps)

    @property
    def is_max_steps_reached(self) -> bool:
        """是否达到最大步骤数"""
        return self.step_count >= self.max_steps

    def begin_step(
        self,
        step_type: str = "tool_call",
        description: str = "",
    ) -> TaskStep:
        """开始新的执行步骤"""
        step = TaskStep(
            step_number=self.step_count + 1,
            step_type=step_type,
            description=description,
        )
        self.current_step = step
        self.updated_at = datetime.now(timezone.utc)
        return step

    def complete_step(
        self,
        status: str = "completed",
        intermediate_result: Any = None,
    ) -> None:
        """完成当前步骤"""
        if self.current_step:
            self.current_step.complete(status, intermediate_result)
            self.steps.append(self.current_step)
            self.current_step = None
            self.updated_at = datetime.now(timezone.utc)

    def add_tool_call(
        self,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> ToolCall:
        """添加工具调用"""
        if not self.current_step:
            self.begin_step(step_type="tool_call", description=f"Call {tool_name}")

        tool_call = ToolCall(tool_name=tool_name, arguments=arguments)
        self.current_step.add_tool_call(tool_call)
        return tool_call

    def update_state(self, key: str, value: Any) -> None:
        """更新任务状态"""
        self.state[key] = value
        self.updated_at = datetime.now(timezone.utc)

    def get_state(self, key: str, default: Any = None) -> Any:
        """获取任务状态"""
        return self.state.get(key, default)

    def get_all_tool_calls(self) -> list[ToolCall]:
        """获取所有工具调用记录"""
        all_calls = []
        for step in self.steps:
            all_calls.extend(step.tool_calls)
        if self.current_step:
            all_calls.extend(self.current_step.tool_calls)
        return all_calls

    def get_execution_summary(self) -> dict[str, Any]:
        """获取执行摘要"""
        tool_calls_by_tool: dict[str, int] = {}
        total_duration = 0.0

        for step in self.steps:
            total_duration += step.duration_ms
            for tc in step.tool_calls:
                tool_calls_by_tool[tc.tool_name] = (
                    tool_calls_by_tool.get(tc.tool_name, 0) + 1
                )

        return {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "total_steps": self.step_count,
            "total_tool_calls": self.total_tool_calls,
            "tool_calls_by_tool": tool_calls_by_tool,
            "total_duration_ms": total_duration,
            "started_at": self.started_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    def to_dict(self) -> dict[str, Any]:
        """转换为字典，用于持久化"""
        return {
            "task_id": self.task_id,
            "session_id": self.session_id,
            "steps": [step.to_dict() for step in self.steps],
            "current_step": self.current_step.to_dict() if self.current_step else None,
            "state": self.state,
            "metadata": self.metadata,
            "max_steps": self.max_steps,
            "started_at": self.started_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "summary": self.get_execution_summary(),
        }
