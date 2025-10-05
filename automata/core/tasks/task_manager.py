#!/usr/bin/env python3
"""
任务管理器
管理异步任务的创建、执行和跟踪
参考OpenAI Agents SDK的Tracing机制
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable, Awaitable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db.database import DatabaseManager
from ..db.models import Task, TaskData


@dataclass
class TaskResult:
    """任务结果"""
    success: bool
    result: Any = None
    error: Optional[str] = None


class TaskManager:
    """任务管理器"""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)

    async def create_task(
        self,
        session_id: str,
        tool_name: str,
        task_type: str,
        description: str = "",
        parameters: Optional[Dict[str, Any]] = None,
        priority: int = 4
    ) -> str:
        """创建异步任务"""
        task_id = str(uuid.uuid4())

        task = Task(
            task_id=task_id,
            session_id=session_id,
            tool_name=tool_name,
            task_type=task_type,
            status="pending",
            description=description,
            parameters=parameters or {},
            priority=priority,
        )

        async with AsyncSession(self.db.engine) as session:
            session.add(task)
            await session.commit()

        return task_id

    async def start_task(
        self,
        task_id: str,
        task_func: Callable[[], Awaitable[TaskResult]]
    ) -> None:
        """启动任务"""
        # 更新状态为running
        async with AsyncSession(self.db.engine) as session:
            result = await session.execute(select(Task).where(Task.task_id == task_id))
            task = result.scalar_one_or_none()
            if task:
                task.status = "running"
                task.updated_at = datetime.now(timezone.utc)
                await session.commit()

        # 创建异步任务
        async def _run_task():
            try:
                result = await task_func()
                await self._complete_task(task_id, result)
            except Exception as e:
                await self._fail_task(task_id, str(e))

        task = asyncio.create_task(_run_task())
        self._running_tasks[task_id] = task

    async def get_task_status(self, task_id: str) -> Optional[TaskData]:
        """获取任务状态"""
        async with AsyncSession(self.db.engine) as session:
            result = await session.execute(select(Task).where(Task.task_id == task_id))
            task = result.scalar_one_or_none()
            if task:
                return TaskData(
                    task_id=task.task_id,
                    session_id=task.session_id,
                    tool_name=task.tool_name,
                    task_type=task.task_type,
                    status=task.status,
                    priority=task.priority,
                    description=task.description,
                    parameters=task.parameters,
                    result=task.result,
                    error_message=task.error_message,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                    completed_at=task.completed_at,
                )
        return None

    async def list_tasks(
        self,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[TaskData]:
        """列出任务"""
        async with AsyncSession(self.db.engine) as session:
            query = select(Task)
            if session_id:
                query = query.where(Task.session_id == session_id)
            if status:
                query = query.where(Task.status == status)

            query = query.order_by(Task.priority.asc(), Task.created_at.desc()).limit(limit)
            tasks = await session.execute(query)
            task_list = tasks.scalars().all()

            return [
                TaskData(
                    task_id=task.task_id,
                    session_id=task.session_id,
                    tool_name=task.tool_name,
                    task_type=task.task_type,
                    status=task.status,
                    priority=task.priority,
                    description=task.description,
                    parameters=task.parameters,
                    result=task.result,
                    error_message=task.error_message,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                    completed_at=task.completed_at,
                )
                for task in task_list
            ]

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self._running_tasks:
            task = self._running_tasks[task_id]
            task.cancel()
            del self._running_tasks[task_id]

            # 更新数据库状态
            async with AsyncSession(self.db.engine) as session:
                result = await session.execute(select(Task).where(Task.task_id == task_id))
                db_task = result.scalar_one_or_none()
                if db_task:
                    db_task.status = "failed"
                    db_task.error_message = "Task cancelled"
                    db_task.completed_at = datetime.now(timezone.utc)
                    db_task.updated_at = datetime.now(timezone.utc)
                    await session.commit()

            return True
        return False

    async def _complete_task(self, task_id: str, result: TaskResult) -> None:
        """完成任务"""
        async with AsyncSession(self.db.engine) as session:
            result_query = await session.execute(select(Task).where(Task.task_id == task_id))
            task = result_query.scalar_one_or_none()
            if task:
                task.status = "completed" if result.success else "failed"
                task.result = result.result
                task.error_message = result.error
                task.completed_at = datetime.now(timezone.utc)
                task.updated_at = datetime.now(timezone.utc)
                await session.commit()

        # 清理运行中的任务
        if task_id in self._running_tasks:
            del self._running_tasks[task_id]

    async def _fail_task(self, task_id: str, error: str) -> None:
        """标记任务失败"""
        async with AsyncSession(self.db.engine) as session:
            result = await session.execute(select(Task).where(Task.task_id == task_id))
            task = result.scalar_one_or_none()
            if task:
                task.status = "failed"
                task.error_message = error
                task.completed_at = datetime.now(timezone.utc)
                task.updated_at = datetime.now(timezone.utc)
                await session.commit()

        # 清理运行中的任务
        if task_id in self._running_tasks:
            del self._running_tasks[task_id]

    async def cleanup_completed_tasks(self, days: int = 7) -> int:
        """清理完成的旧任务"""
        cutoff_date = datetime.now(timezone.utc)
        # 简化计算，假设30天为一个月
        cutoff_date = cutoff_date.replace(day=cutoff_date.day - days)

        async with AsyncSession(self.db.engine) as session:
            result = await session.execute(
                select(Task)
                .where(Task.status.in_(["completed", "failed"]))
                .where(Task.completed_at < cutoff_date)
            )
            old_tasks = result.scalars().all()

            count = len(old_tasks)
            for task in old_tasks:
                await session.delete(task)

            await session.commit()
            return count

    async def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        async with AsyncSession(self.db.engine) as session:
            result = await session.execute(select(Task).where(Task.task_id == task_id))
            task = result.scalar_one_or_none()
            if task:
                await session.delete(task)
                await session.commit()
                return True
        return False

    async def shutdown(self) -> None:
        """关闭任务管理器"""
        # 取消所有运行中的任务
        for task in self._running_tasks.values():
            task.cancel()

        self._running_tasks.clear()
        self._executor.shutdown(wait=True)