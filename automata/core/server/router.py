"""
Automata Web服务器路由定义
"""

from __future__ import annotations

import asyncio
import json
import os
import time
import traceback

from agents import Runner
from agents.extensions.memory import SQLAlchemySession
from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import FileResponse, JSONResponse
from loguru import logger

from ..config.config import config_manager
from ..tool import get_tool_manager


def _raise_empty_message_error():
    raise HTTPException(status_code=400, detail="Message cannot be empty")


def _raise_conversation_not_found():
    raise HTTPException(status_code=404, detail="Conversation not found")


def _raise_tool_not_found():
    raise HTTPException(status_code=404, detail="Tool not found")


def _raise_task_not_found():
    raise HTTPException(status_code=404, detail="Task not found")


def _raise_task_cancel_failed():
    raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")


def _raise_tool_enable_failed(tool_name: str):
    raise HTTPException(status_code=400, detail=f"Failed to enable tool {tool_name}")


def _raise_tool_disable_failed(tool_name: str):
    raise HTTPException(status_code=400, detail=f"Failed to disable tool {tool_name}")


def setup_routes(app, dashboard):
    """设置所有路由"""

    @app.post("/api/chat")
    async def chat(request: Request):
        """处理聊天请求"""
        if (
            not dashboard.provider
            or not dashboard.run_config
            or not dashboard.context_mgr
        ):
            raise HTTPException(status_code=500, detail="LLM provider not initialized")

        try:
            data = await request.json()
            user_query = data.get("message", "").strip()
            session_id = data.get("session_id", "default_session")

            if not user_query:
                _raise_empty_message_error()

            # 初始化会话上下文
            conversation_id = await dashboard.context_mgr.initialize_session(
                session_id=session_id,
                platform_id="web",
                user_id=session_id,  # 使用session_id作为user_id
            )

            # 获取或创建Agent session
            if conversation_id not in dashboard.agent_sessions:
                # 为这个对话创建一个新的SQLAlchemySession，使用现有的数据库引擎
                agent_session = SQLAlchemySession(
                    f"automata_{conversation_id}",
                    engine=dashboard.context_mgr.db.engine,
                    create_tables=True,
                )
                dashboard.agent_sessions[conversation_id] = agent_session
                dashboard.context_mgr.set_session(conversation_id, agent_session)
            else:
                agent_session = dashboard.agent_sessions[conversation_id]
                dashboard.context_mgr.set_session(conversation_id, agent_session)

            # 获取或创建Agent实例
            agent = dashboard._get_or_create_agent(conversation_id)

            # 定期清理旧session
            dashboard.cleanup_old_sessions()

            # 使用OpenAI Agent SDK的session调用LLM
            time.time()
            result = await Runner.run(
                agent,
                user_query,
                session=agent_session,
                run_config=dashboard.run_config,
            )
            time.time()

            return JSONResponse(
                content={
                    "response": str(result.final_output),
                    "conversation_id": conversation_id,
                    "session_id": session_id,
                    "status": "success",
                },
            )

        except Exception as e:
            logger.exception(f"Chat request failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/ping")
    async def ping():
        """测试API连通性"""
        return JSONResponse(content={"status": "pong"})

    @app.get("/api/conversations")
    async def get_conversations(session_id: str = "default_session"):
        """获取会话的对话列表"""
        logger.info(f"get_conversations called with session_id: {session_id}")
        if not dashboard.context_mgr:
            raise HTTPException(
                status_code=500,
                detail="Context manager not initialized",
            )

        try:
            conversations = await dashboard.context_mgr.get_conversation_list(
                session_id,
            )

            return JSONResponse(
                content=jsonable_encoder(
                    {
                        "conversations": conversations,
                        "status": "success",
                    },
                ),
            )

        except Exception as e:
            logger.exception(f"Failed to get conversations: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/conversations")
    async def create_conversation(request: Request):
        """创建新对话"""
        if not dashboard.context_mgr:
            raise HTTPException(
                status_code=500,
                detail="Context manager not initialized",
            )

        try:
            data = await request.json()
            session_id = data.get("session_id", "default_session")
            title = data.get("title")

            conversation_id = await dashboard.context_mgr.create_new_conversation(
                session_id=session_id,
                platform_id="web",
                user_id=session_id,
                title=title,
            )

            return JSONResponse(
                content={
                    "conversation_id": conversation_id,
                    "status": "success",
                },
            )

        except Exception as e:
            logger.exception(f"Failed to create conversation: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/conversations/{conversation_id}")
    async def delete_conversation(conversation_id: str):
        """删除对话"""
        if not dashboard.context_mgr:
            raise HTTPException(
                status_code=500,
                detail="Context manager not initialized",
            )

        try:
            success = await dashboard.context_mgr.delete_conversation(conversation_id)

            if success:
                return JSONResponse(content={"status": "success"})
            _raise_conversation_not_found()

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Failed to delete conversation {conversation_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/conversations/{conversation_id}/switch")
    async def switch_conversation(conversation_id: str, request: Request):
        """切换到指定对话"""
        if not dashboard.context_mgr:
            raise HTTPException(
                status_code=500,
                detail="Context manager not initialized",
            )

        try:
            data = await request.json()
            session_id = data.get("session_id", "default_session")

            success = await dashboard.context_mgr.switch_conversation(
                session_id,
                conversation_id,
            )

            if success:
                return JSONResponse(content={"status": "success"})
            _raise_conversation_not_found()

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Failed to switch to conversation {conversation_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/conversations/{conversation_id}/history")
    async def get_conversation_history(conversation_id: str):
        """获取对话历史消息"""
        if not dashboard.context_mgr:
            raise HTTPException(
                status_code=500,
                detail="Context manager not initialized",
            )

        try:
            # 获取对话历史
            history = await dashboard.context_mgr.get_conversation_history(
                conversation_id,
            )

            return JSONResponse(
                content=jsonable_encoder(
                    {
                        "conversation_id": conversation_id,
                        "messages": history,
                        "status": "success",
                    },
                ),
            )

        except Exception as e:
            logger.exception(
                f"Failed to get conversation history for {conversation_id}: {e}",
            )
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/config")
    async def get_config():
        """获取配置"""
        try:
            config = config_manager.load_config()
            return JSONResponse(content=jsonable_encoder(config))
        except Exception as e:
            logger.exception(f"Failed to get config: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.put("/api/config")
    async def update_config(request: Request):
        """更新配置并热重载"""
        try:
            data = await request.json()

            # 分离核心配置和工具配置
            core_config = {}
            tool_config = {}

            # 获取配置section列表
            core_sections = config_manager.get_core_sections()
            extension_sections = config_manager.get_extension_sections()

            # 分离数据到对应的配置
            for section in core_sections:
                if section in data:
                    core_config[section] = data[section]

            for section in extension_sections:
                if section in data:
                    tool_config[section] = data[section]

            # 保存核心配置
            if core_config:
                with open(
                    config_manager.core_config_file,
                    "w",
                    encoding="utf-8",
                ) as f:
                    json.dump(core_config, f, indent=4, ensure_ascii=False)

            # 保存工具配置
            if tool_config:
                with open(
                    config_manager.tool_config_file,
                    "w",
                    encoding="utf-8",
                ) as f:
                    json.dump(tool_config, f, indent=4, ensure_ascii=False)

            # 热重载配置管理器
            config_manager.reload_config()
            # 重新初始化LLM provider和agent配置
            dashboard._init_llm_provider()
            return JSONResponse(
                content={"message": "Configuration updated and reloaded successfully"},
            )
        except Exception as e:
            logger.exception(f"Failed to update config: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/tools")
    async def get_tools():
        """获取所有工具状态"""
        try:
            tool_mgr = get_tool_manager()
            tools_status = tool_mgr.get_all_tools_status()
            return JSONResponse(
                content=jsonable_encoder(
                    {
                        "tools": tools_status,
                        "status": "success",
                    },
                ),
            )
        except Exception as e:
            logger.exception(f"Failed to get tools: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/tools/{tool_name}")
    async def get_tool_status(tool_name: str):
        """获取指定工具状态"""
        try:
            tool_mgr = get_tool_manager()
            status = tool_mgr.get_tool_status(tool_name)
            if status:
                return JSONResponse(
                    content=jsonable_encoder(
                        {
                            "tool": status,
                            "status": "success",
                        },
                    ),
                )
            _raise_tool_not_found()
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Failed to get tool status for {tool_name}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/tools/{tool_name}/enable")
    async def enable_tool(tool_name: str):
        """启用工具"""
        try:
            tool_mgr = get_tool_manager()
            if tool_mgr.enable_tool(tool_name):
                return JSONResponse(
                    content={
                        "message": f"Tool {tool_name} enabled successfully",
                        "status": "success",
                    },
                )
            _raise_tool_enable_failed(tool_name)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Failed to enable tool {tool_name}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/tools/{tool_name}/disable")
    async def disable_tool(tool_name: str):
        """禁用工具"""
        try:
            tool_mgr = get_tool_manager()
            if tool_mgr.disable_tool(tool_name):
                return JSONResponse(
                    content={
                        "message": f"Tool {tool_name} disabled successfully",
                        "status": "success",
                    },
                )
            _raise_tool_disable_failed(tool_name)
        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Failed to disable tool {tool_name}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/tools/save-and-reload")
    async def save_and_reload_tools(request: Request):
        """保存工具状态并重新加载"""
        try:
            tool_mgr = get_tool_manager()

            # 获取请求中的待处理更改
            data = await request.json()
            changes = data.get("changes", []) if data else []

            # 应用所有待处理的更改
            for change in changes:
                action, tool_name = change.split(":", 1)
                if action == "enable":
                    tool_mgr.enable_tool(tool_name)
                elif action == "disable":
                    tool_mgr.disable_tool(tool_name)

            # 保存并重载
            await tool_mgr.save_and_reload()

            # 重置全局Agent，以便下次使用新的工具列表
            dashboard.global_agent = None

            return JSONResponse(
                content={
                    "message": "Tools saved and reloaded successfully",
                    "status": "success",
                },
            )
        except Exception as e:
            logger.exception(f"Failed to save and reload tools: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/tasks")
    async def get_tasks(
        session_id: str | None = None,
        status: str | None = None,
        limit: int = 50,
    ):
        """获取任务列表"""
        if not dashboard.task_manager:
            raise HTTPException(status_code=500, detail="Task manager not initialized")

        try:
            tasks = await dashboard.task_manager.list_tasks(
                session_id=session_id,
                status=status,
                limit=limit,
            )

            return JSONResponse(
                content=jsonable_encoder(
                    {
                        "tasks": [task.__dict__ for task in tasks],
                        "status": "success",
                    },
                ),
            )

        except Exception as e:
            logger.exception(f"Failed to get tasks: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/tasks/{task_id}")
    async def get_task_status(task_id: str):
        """获取任务状态"""
        if not dashboard.task_manager:
            raise HTTPException(status_code=500, detail="Task manager not initialized")

        try:
            task = await dashboard.task_manager.get_task_status(task_id)
            if task:
                return JSONResponse(
                    content=jsonable_encoder(
                        {
                            "task": task.__dict__,
                            "status": "success",
                        },
                    ),
                )
            _raise_task_not_found()

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Failed to get task status for {task_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.post("/api/tasks/{task_id}/cancel")
    async def cancel_task(task_id: str):
        """取消任务"""
        if not dashboard.task_manager:
            raise HTTPException(status_code=500, detail="Task manager not initialized")

        try:
            success = await dashboard.task_manager.cancel_task(task_id)
            if success:
                return JSONResponse(
                    content={
                        "message": "Task cancelled successfully",
                        "status": "success",
                    },
                )
            _raise_task_cancel_failed()

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Failed to cancel task {task_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/tasks/{task_id}/steps")
    async def get_task_steps(task_id: str):
        """获取任务的详细步骤"""
        if not dashboard.task_manager:
            raise HTTPException(status_code=500, detail="Task manager not initialized")

        try:
            # 获取任务基本信息
            task = await dashboard.task_manager.get_task_status(task_id)
            if not task:
                _raise_task_not_found()

            # 获取任务步骤（从 result 中提取）
            steps = []
            if task.result and isinstance(task.result, dict):
                steps = task.result.get("steps", [])

            return JSONResponse(
                content=jsonable_encoder(
                    {
                        "task_id": task_id,
                        "steps": steps,
                        "total_steps": len(steps),
                        "status": "success",
                    },
                ),
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Failed to get task steps for {task_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/tasks/stats")
    async def get_tasks_stats():
        """获取任务统计信息"""
        if not dashboard.task_manager:
            raise HTTPException(status_code=500, detail="Task manager not initialized")

        try:
            # 获取各状态的任务数量
            all_tasks = await dashboard.task_manager.list_tasks(limit=1000)

            stats = {
                "total": len(all_tasks),
                "pending": sum(1 for t in all_tasks if t.status == "pending"),
                "running": sum(1 for t in all_tasks if t.status == "running"),
                "completed": sum(1 for t in all_tasks if t.status == "completed"),
                "failed": sum(1 for t in all_tasks if t.status == "failed"),
            }

            # 按任务类型统计
            task_types = {}
            for task in all_tasks:
                task_types[task.task_type] = task_types.get(task.task_type, 0) + 1

            return JSONResponse(
                content=jsonable_encoder(
                    {
                        "stats": stats,
                        "task_types": task_types,
                        "status": "success",
                    },
                ),
            )

        except Exception as e:
            logger.exception(f"Failed to get task stats: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/tasks/{task_id}/delete")
    async def delete_task(task_id: str):
        """删除任务"""
        if not dashboard.task_manager:
            raise HTTPException(status_code=500, detail="Task manager not initialized")

        try:
            success = await dashboard.task_manager.delete_task(task_id)
            if success:
                return JSONResponse(
                    content={
                        "message": "Task deleted successfully",
                        "status": "success",
                    },
                )
            _raise_task_not_found()

        except HTTPException:
            raise
        except Exception as e:
            logger.exception(f"Failed to delete task {task_id}: {e}")
            raise HTTPException(status_code=500, detail=str(e))
