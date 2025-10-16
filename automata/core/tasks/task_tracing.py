#!/usr/bin/env python3
"""
任务追踪系统
参考 OpenAI Agents SDK 的 Tracing 机制
提供任务执行过程的详细追踪和可视化
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from automata.core.db.database import DatabaseManager
    from automata.core.tasks.task_context import TaskContext


@dataclass
class TraceSpan:
    """追踪跨度 - 表示一个可追踪的操作"""

    span_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    trace_id: str = ""
    parent_span_id: str | None = None
    name: str = ""
    span_type: str = "generic"  # task, step, tool_call, llm_call
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    duration_ms: float = 0.0
    attributes: dict[str, Any] = field(default_factory=dict)
    status: str = "running"  # running, completed, failed
    error: str | None = None

    def end(self, status: str = "completed", error: str | None = None) -> None:
        """结束跨度"""
        self.ended_at = datetime.now(timezone.utc)
        self.status = status
        self.error = error
        if self.ended_at and self.started_at:
            delta = self.ended_at - self.started_at
            self.duration_ms = delta.total_seconds() * 1000

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "span_id": self.span_id,
            "trace_id": self.trace_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "span_type": self.span_type,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "duration_ms": self.duration_ms,
            "attributes": self.attributes,
            "status": self.status,
            "error": self.error,
        }


@dataclass
class Trace:
    """追踪 - 表示完整的任务执行追踪"""

    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_id: str = ""
    session_id: str = ""
    name: str = ""
    spans: list[TraceSpan] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: datetime | None = None
    status: str = "running"

    def create_span(
        self,
        name: str,
        span_type: str = "generic",
        parent_span_id: str | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> TraceSpan:
        """创建新的跨度"""
        span = TraceSpan(
            trace_id=self.trace_id,
            parent_span_id=parent_span_id,
            name=name,
            span_type=span_type,
            attributes=attributes or {},
        )
        self.spans.append(span)
        return span

    def end(self, status: str = "completed") -> None:
        """结束追踪"""
        self.ended_at = datetime.now(timezone.utc)
        self.status = status

    def get_span_tree(self) -> dict[str, Any]:
        """获取跨度树结构"""
        # 构建父子关系
        roots = []

        def build_tree(span: TraceSpan) -> dict[str, Any]:
            children = [
                build_tree(s) for s in self.spans if s.parent_span_id == span.span_id
            ]
            return {
                "span": span.to_dict(),
                "children": children,
            }

        # 找到所有根节点
        for span in self.spans:
            if span.parent_span_id is None:
                roots.append(build_tree(span))

        return {
            "trace_id": self.trace_id,
            "task_id": self.task_id,
            "name": self.name,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "status": self.status,
            "metadata": self.metadata,
            "spans": roots,
        }

    def get_statistics(self) -> dict[str, Any]:
        """获取统计信息"""
        total_spans = len(self.spans)
        spans_by_type: dict[str, int] = {}
        total_duration = 0.0
        failed_spans = 0

        for span in self.spans:
            spans_by_type[span.span_type] = spans_by_type.get(span.span_type, 0) + 1
            total_duration += span.duration_ms
            if span.status == "failed":
                failed_spans += 1

        return {
            "total_spans": total_spans,
            "spans_by_type": spans_by_type,
            "total_duration_ms": total_duration,
            "failed_spans": failed_spans,
            "success_rate": (total_spans - failed_spans) / total_spans
            if total_spans > 0
            else 0,
        }

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "trace_id": self.trace_id,
            "task_id": self.task_id,
            "session_id": self.session_id,
            "name": self.name,
            "spans": [span.to_dict() for span in self.spans],
            "metadata": self.metadata,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "status": self.status,
            "statistics": self.get_statistics(),
        }


class TaskTracer:
    """
    任务追踪器
    负责追踪任务执行的详细过程
    """

    def __init__(self, db_manager: DatabaseManager | None = None):
        self.db = db_manager
        self._active_traces: dict[str, Trace] = {}

    def start_trace(
        self,
        task_id: str,
        session_id: str,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> Trace:
        """开始新的追踪"""
        trace = Trace(
            task_id=task_id,
            session_id=session_id,
            name=name,
            metadata=metadata or {},
        )
        self._active_traces[trace.trace_id] = trace
        return trace

    def get_trace(self, trace_id: str) -> Trace | None:
        """获取追踪"""
        return self._active_traces.get(trace_id)

    def get_trace_by_task(self, task_id: str) -> Trace | None:
        """根据任务 ID 获取追踪"""
        for trace in self._active_traces.values():
            if trace.task_id == task_id:
                return trace
        return None

    def end_trace(self, trace_id: str, status: str = "completed") -> Trace | None:
        """结束追踪"""
        trace = self._active_traces.get(trace_id)
        if trace:
            trace.end(status)
        return trace

    def create_trace_from_context(self, context: TaskContext) -> Trace:
        """从任务上下文创建追踪"""
        trace = Trace(
            task_id=context.task_id,
            session_id=context.session_id,
            name=f"Task: {context.metadata.get('description', context.task_id)}",
            metadata=context.metadata,
            started_at=context.started_at,
        )

        # 为每个步骤创建跨度
        for step in context.steps:
            step_span = trace.create_span(
                name=step.description or f"Step {step.step_number}",
                span_type=step.step_type,
                attributes={
                    "step_number": step.step_number,
                    "step_id": step.step_id,
                },
            )
            step_span.started_at = step.started_at
            step_span.ended_at = step.completed_at
            step_span.duration_ms = step.duration_ms
            step_span.status = step.status

            # 为每个工具调用创建子跨度
            for tool_call in step.tool_calls:
                tool_span = trace.create_span(
                    name=f"Tool: {tool_call.tool_name}",
                    span_type="tool_call",
                    parent_span_id=step_span.span_id,
                    attributes={
                        "tool_name": tool_call.tool_name,
                        "arguments": tool_call.arguments,
                        "result": tool_call.result,
                        "call_id": tool_call.call_id,
                    },
                )
                tool_span.started_at = tool_call.started_at
                tool_span.ended_at = tool_call.completed_at
                tool_span.duration_ms = tool_call.duration_ms
                tool_span.status = "completed" if tool_call.error is None else "failed"
                tool_span.error = tool_call.error

        return trace

    def export_trace(self, trace_id: str) -> dict[str, Any] | None:
        """导出追踪数据"""
        trace = self.get_trace(trace_id)
        if trace:
            return trace.to_dict()
        return None

    def export_trace_tree(self, trace_id: str) -> dict[str, Any] | None:
        """导出追踪树"""
        trace = self.get_trace(trace_id)
        if trace:
            return trace.get_span_tree()
        return None

    def clear_completed_traces(self, keep_count: int = 100) -> int:
        """清理已完成的追踪，只保留最近的指定数量"""
        completed = [
            (tid, t)
            for tid, t in self._active_traces.items()
            if t.status in ["completed", "failed"]
        ]

        # 按结束时间排序
        completed.sort(
            key=lambda x: x[1].ended_at or datetime.now(timezone.utc),
            reverse=True,
        )

        # 删除超出保留数量的追踪
        to_remove = completed[keep_count:]
        for trace_id, _ in to_remove:
            del self._active_traces[trace_id]

        return len(to_remove)
