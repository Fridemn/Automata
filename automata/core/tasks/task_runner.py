#!/usr/bin/env python3
"""
任务运行器
参考 OpenAI Agents SDK 的 Runner 实现
支持多步骤执行、工具调用链、Agent 协作等复杂任务场景
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Callable

from automata.core.tasks.task_context import TaskContext, ToolCall

if TYPE_CHECKING:
    from collections.abc import Awaitable

    from agents import Agent, FunctionTool

    from automata.core.tasks.task_manager import TaskManager


@dataclass
class TaskRunResult:
    """任务运行结果"""

    task_id: str
    success: bool
    final_output: Any = None
    error: str | None = None
    context: TaskContext | None = None
    total_steps: int = 0
    total_tool_calls: int = 0
    duration_ms: float = 0.0


class TaskRunner:
    """
    任务运行器
    负责执行复杂的多步骤任务，支持：
    1. Agent 多次调用工具
    2. 工具调用链
    3. 中间结果传递
    4. 执行过程追踪
    """

    def __init__(self, task_manager: TaskManager | None = None):
        self.task_manager = task_manager
        self._running_tasks: dict[str, asyncio.Task] = {}

    async def run_task(
        self,
        task_func: Callable[[TaskContext], Awaitable[Any]],
        session_id: str,
        task_type: str = "complex_task",
        description: str = "",
        parameters: dict[str, Any] | None = None,
        max_steps: int = 50,
        background: bool = False,
    ) -> TaskRunResult | str:
        """
        运行任务

        Args:
            task_func: 任务执行函数，接收 TaskContext 并返回结果
            session_id: 会话 ID
            task_type: 任务类型
            description: 任务描述
            parameters: 任务参数
            max_steps: 最大步骤数
            background: 是否后台运行

        Returns:
            如果 background=False，返回 TaskRunResult
            如果 background=True，返回 task_id 字符串
        """
        task_id = str(uuid.uuid4())

        # 如果有 task_manager，先在数据库中创建记录
        if self.task_manager:
            await self.task_manager.create_task(
                session_id=session_id,
                tool_name="task_runner",
                task_type=task_type,
                description=description,
                parameters=parameters or {},
            )

        # 创建任务上下文
        context = TaskContext(
            task_id=task_id,
            session_id=session_id,
            max_steps=max_steps,
            metadata={
                "task_type": task_type,
                "description": description,
                "parameters": parameters or {},
            },
        )

        if background:
            # 后台运行
            async_task = asyncio.create_task(
                self._execute_task(task_id, task_func, context),
            )
            self._running_tasks[task_id] = async_task
            return task_id
        # 前台运行
        return await self._execute_task(task_id, task_func, context)

    async def _execute_task(
        self,
        task_id: str,
        task_func: Callable[[TaskContext], Awaitable[Any]],
        context: TaskContext,
    ) -> TaskRunResult:
        """执行任务的内部方法"""
        started_at = datetime.now(timezone.utc)

        try:
            # 更新状态为 running
            if self.task_manager:
                await self.task_manager.update_task_status(task_id, "running")

            # 执行任务函数
            result = await task_func(context)

            # 计算执行时长
            completed_at = datetime.now(timezone.utc)
            duration_ms = (completed_at - started_at).total_seconds() * 1000

            # 创建成功结果
            task_result = TaskRunResult(
                task_id=task_id,
                success=True,
                final_output=result,
                context=context,
                total_steps=context.step_count,
                total_tool_calls=context.total_tool_calls,
                duration_ms=duration_ms,
            )

            # 更新数据库
            if self.task_manager:
                await self.task_manager.complete_task(
                    task_id=task_id,
                    result={
                        "output": result,
                        "execution_summary": context.get_execution_summary(),
                        "steps": [step.to_dict() for step in context.steps],
                    },
                )

            return task_result

        except Exception as e:
            # 计算执行时长
            completed_at = datetime.now(timezone.utc)
            duration_ms = (completed_at - started_at).total_seconds() * 1000

            # 创建失败结果
            error_msg = str(e)
            task_result = TaskRunResult(
                task_id=task_id,
                success=False,
                error=error_msg,
                context=context,
                total_steps=context.step_count,
                total_tool_calls=context.total_tool_calls,
                duration_ms=duration_ms,
            )

            # 更新数据库
            if self.task_manager:
                await self.task_manager.fail_task(task_id=task_id, error=error_msg)

            return task_result

        finally:
            # 清理运行中的任务引用
            if task_id in self._running_tasks:
                del self._running_tasks[task_id]

    async def run_agent_task(
        self,
        agent: Agent,
        input_message: str,
        session_id: str,
        tools: list[FunctionTool] | None = None,
        max_turns: int = 10,
        background: bool = False,
    ) -> TaskRunResult | str:
        """
        运行 Agent 任务
        让 Agent 可以多次调用工具直到完成任务

        Args:
            agent: Agent 实例
            input_message: 输入消息
            session_id: 会话 ID
            tools: 可用工具列表
            max_turns: 最大轮次
            background: 是否后台运行
        """

        async def agent_task_func(context: TaskContext) -> Any:
            """Agent 任务执行函数"""
            # 这里需要集成实际的 Agent 运行逻辑
            # 由于依赖具体的 Agent 实现，这里提供框架

            context.update_state("input", input_message)
            context.update_state("max_turns", max_turns)

            # 模拟多轮对话和工具调用
            turn = 0
            current_message = input_message
            conversation_history = []

            while turn < max_turns and not context.is_max_steps_reached:
                # 开始新的步骤
                step = context.begin_step(
                    step_type="agent_turn",
                    description=f"Agent turn {turn + 1}",
                )

                # 记录输入
                step.llm_input = current_message
                conversation_history.append(
                    {"role": "user", "content": current_message},
                )

                # 模拟 Agent 响应
                response = {
                    "content": f"Processing: {current_message}",
                    "tool_calls": [],
                    "is_final": turn >= max_turns - 1,
                }

                step.llm_output = response.get("content", "")
                conversation_history.append(
                    {"role": "assistant", "content": response.get("content", "")},
                )

                # 处理工具调用
                if response.get("tool_calls"):
                    for tool_call_data in response["tool_calls"]:
                        tool_call = context.add_tool_call(
                            tool_name=tool_call_data.get("name", ""),
                            arguments=tool_call_data.get("arguments", {}),
                        )
                        # 这里应该实际执行工具
                        tool_call.complete(
                            result={"status": "simulated"},
                        )

                # 完成步骤
                context.complete_step(
                    status="completed",
                    intermediate_result=response,
                )

                # 检查是否完成
                if response.get("is_final"):
                    break

                turn += 1
                current_message = "Continue with the task"

            # 返回最终结果
            return {
                "conversation": conversation_history,
                "turns": turn + 1,
                "completed": True,
            }

        return await self.run_task(
            task_func=agent_task_func,
            session_id=session_id,
            task_type="agent_task",
            description=f"Agent task: {input_message[:100]}",
            parameters={"input": input_message, "max_turns": max_turns},
            max_steps=max_turns * 5,  # 每轮可能有多个步骤
            background=background,
        )

    async def run_tool_chain(
        self,
        tools: list[tuple[Callable, dict[str, Any]]],
        session_id: str,
        description: str = "Tool chain execution",
        background: bool = False,
    ) -> TaskRunResult | str:
        """
        运行工具链
        按顺序执行多个工具，每个工具的输出可以作为下一个的输入

        Args:
            tools: 工具列表，每个元素是 (tool_func, arguments) 元组
            session_id: 会话 ID
            description: 任务描述
            background: 是否后台运行
        """

        async def tool_chain_func(context: TaskContext) -> Any:
            """工具链执行函数"""
            results = []
            previous_result = None

            for idx, (tool_func, arguments) in enumerate(tools):
                # 开始新步骤
                tool_name = getattr(tool_func, "__name__", f"tool_{idx}")
                context.begin_step(
                    step_type="tool_call",
                    description=f"Execute {tool_name}",
                )

                # 如果参数中有占位符，用上一个结果替换
                processed_args = arguments.copy()
                if previous_result is not None and "_previous_result" in processed_args:
                    processed_args["_previous_result"] = previous_result

                # 记录工具调用
                tool_call = context.add_tool_call(
                    tool_name=tool_name,
                    arguments=processed_args,
                )

                try:
                    # 执行工具
                    if asyncio.iscoroutinefunction(tool_func):
                        result = await tool_func(**processed_args)
                    else:
                        result = tool_func(**processed_args)

                    tool_call.complete(result=result)
                    previous_result = result
                    results.append(result)

                    context.complete_step(
                        status="completed",
                        intermediate_result=result,
                    )

                except Exception as e:
                    tool_call.complete(error=str(e))
                    context.complete_step(status="failed")
                    raise

            return {
                "results": results,
                "final_result": results[-1] if results else None,
            }

        return await self.run_task(
            task_func=tool_chain_func,
            session_id=session_id,
            task_type="tool_chain",
            description=description,
            parameters={"tools_count": len(tools)},
            background=background,
        )

    async def get_task_status(self, task_id: str) -> dict[str, Any] | None:
        """获取任务状态"""
        if self.task_manager:
            task_data = await self.task_manager.get_task_status(task_id)
            if task_data:
                return {
                    "task_id": task_data.task_id,
                    "status": task_data.status,
                    "description": task_data.description,
                    "result": task_data.result,
                    "error_message": task_data.error_message,
                    "created_at": task_data.created_at,
                    "updated_at": task_data.updated_at,
                    "completed_at": task_data.completed_at,
                }
        return None

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        # 取消运行中的任务
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
            del self._running_tasks[task_id]

        # 更新数据库状态
        if self.task_manager:
            return await self.task_manager.cancel_task(task_id)

        return False

    def get_running_tasks(self) -> list[str]:
        """获取所有运行中的任务 ID"""
        return list(self._running_tasks.keys())
