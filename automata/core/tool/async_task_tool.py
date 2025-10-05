#!/usr/bin/env python3
"""
异步任务工具
演示如何创建和管理异步任务
"""

import asyncio
from typing import Dict, Any, List
from agents import function_tool, FunctionTool
from .base import BaseTool, ToolConfig
from ..task_manager import TaskResult


class AsyncTaskTool(BaseTool):
    """异步任务工具"""

    def __init__(self, config: ToolConfig, task_manager=None):
        super().__init__(config, task_manager)
        self._session_id = "default_session"  # 默认会话ID

    def initialize(self) -> None:
        """初始化异步任务工具"""
        # 创建带上下文的函数工具
        self._function_tools.append(self._create_long_running_task_tool())
        self._function_tools.append(self._get_task_status_tool())
        self._function_tools.append(self._list_tasks_tool())
        self._function_tools.append(self._delete_task_tool())

    def _create_long_running_task_tool(self) -> FunctionTool:
        """创建长时间运行任务的函数工具"""
        async def create_long_running_task_impl(duration: int, task_name: str = "Long Task", session_id: str = None) -> str:
            """创建长时间运行的异步任务"""
            if not self.task_manager:
                return "Task manager not available"

            # 使用提供的session_id或默认值
            current_session_id = session_id or self._session_id

            try:
                # 创建任务
                task_id = await self.task_manager.create_task(
                    session_id=current_session_id,
                    tool_name=self.name,
                    task_type="long_running",
                    description=f"Long running task: {task_name}",
                    parameters={"duration": duration, "task_name": task_name}
                )

                # 定义任务函数
                async def task_func():
                    return await self._simulate_long_task(duration, task_name)

                # 启动任务
                await self.task_manager.start_task(task_id, task_func)

                return f"Task '{task_name}' started with ID: {task_id}. Duration: {duration} seconds."

            except Exception as e:
                return f"Failed to create task: {str(e)}"

        # 创建函数工具
        from agents import function_tool
        return function_tool("Create a long-running asynchronous task")(create_long_running_task_impl)

    def _get_task_status_tool(self) -> FunctionTool:
        """创建获取任务状态的函数工具"""
        async def get_task_status_impl(task_id: str) -> str:
            """获取异步任务的状态"""
            if not self.task_manager:
                return "Task manager not available"

            try:
                task_data = await self.task_manager.get_task_status(task_id)
                if task_data:
                    return f"Task {task_id}: Status={task_data.status}, Description={task_data.description}, Result={task_data.result}, Error={task_data.error_message}"
                else:
                    return f"Task {task_id} not found"
            except Exception as e:
                return f"Failed to get task status: {str(e)}"

        # 创建函数工具
        from agents import function_tool
        return function_tool("Get the status of an asynchronous task")(get_task_status_impl)

    def _list_tasks_tool(self) -> FunctionTool:
        """创建列出任务的函数工具"""
        async def list_tasks_impl(session_id: str = "default_session", status: str = None, limit: int = 10) -> str:
            """列出异步任务"""
            if not self.task_manager:
                return "Task manager not available"

            try:
                tasks = await self.task_manager.list_tasks(
                    session_id=session_id,
                    status=status,
                    limit=limit
                )
                
                if not tasks:
                    return "No tasks found"
                
                result = "Current tasks:\n"
                for task in tasks:
                    result += f"- ID: {task.task_id}, Status: {task.status}, Description: {task.description}\n"
                
                return result
            except Exception as e:
                return f"Failed to list tasks: {str(e)}"

        # 创建函数工具
        from agents import function_tool
        return function_tool("List asynchronous tasks")(list_tasks_impl)

    def _delete_task_tool(self) -> FunctionTool:
        """创建删除任务的函数工具"""
        async def delete_task_impl(task_id: str) -> str:
            """删除异步任务"""
            if not self.task_manager:
                return "Task manager not available"

            try:
                success = await self.task_manager.delete_task(task_id)
                if success:
                    return f"Task {task_id} deleted successfully"
                else:
                    return f"Task {task_id} not found"
            except Exception as e:
                return f"Failed to delete task: {str(e)}"

        # 创建函数工具
        from agents import function_tool
        return function_tool("Delete an asynchronous task")(delete_task_impl)

    def get_function_tools(self) -> List[FunctionTool]:
        """获取函数工具列表"""
        return self._function_tools

    async def _simulate_long_task(self, duration: int, task_name: str) -> TaskResult:
        """模拟长时间运行的任务"""
        try:
            print(f"Starting task: {task_name} for {duration} seconds")
            await asyncio.sleep(duration)
            result = f"Task '{task_name}' completed successfully after {duration} seconds"
            print(result)
            return TaskResult(success=True, result=result)
        except Exception as e:
            error_msg = f"Task '{task_name}' failed: {str(e)}"
            print(error_msg)
            return TaskResult(success=False, error=error_msg)


def create_async_task_tool(name: str = "async_task", task_manager=None) -> AsyncTaskTool:
    """创建异步任务工具"""
    config = ToolConfig(
        name=name,
        description="Asynchronous task management tool",
        config={}
    )

    tool = AsyncTaskTool(config, task_manager)
    tool.initialize()
    return tool