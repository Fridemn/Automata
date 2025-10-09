"""
Automata Web服务器路由定义
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

from quart import jsonify, request


def setup_routes(app, dashboard):
    """设置所有路由"""

    @app.route("/")
    async def index():
        """服务index.html"""
        index_path = os.path.join(dashboard.static_folder, "index.html")
        if os.path.exists(index_path):
            return await app.send_static_file("index.html")
        return "Dashboard not found. Please build the frontend first."

    @app.route("/<path:path>")
    async def static_files(path):
        """服务其他静态文件"""
        return await app.send_static_file(path)

    @app.route("/api/chat", methods=["POST"])
    async def chat():
        """处理聊天请求"""
        if (
            not dashboard.provider
            or not dashboard.run_config
            or not dashboard.context_mgr
        ):
            return jsonify({"error": "LLM provider not initialized"}), 500

        try:
            data = await request.get_json()
            user_query = data.get("message", "").strip()
            session_id = data.get("session_id", "default_session")

            if not user_query:
                return jsonify({"error": "Message cannot be empty"}), 400

            # 初始化会话上下文
            conversation_id = await dashboard.context_mgr.initialize_session(
                session_id=session_id,
                platform_id="web",
                user_id=session_id,  # 使用session_id作为user_id
            )

            # 获取或创建Agent session
            from agents.extensions.memory import SQLAlchemySession

            if conversation_id not in dashboard.agent_sessions:
                # 为这个对话创建一个新的SQLAlchemySession，使用现有的数据库引擎
                agent_session = await asyncio.to_thread(
                    SQLAlchemySession,
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
            import time

            from agents import Runner

            time.time()
            result = await Runner.run(
                agent,
                user_query,
                session=agent_session,
                run_config=dashboard.run_config,
            )
            time.time()

            return jsonify(
                {
                    "response": str(result.final_output),
                    "conversation_id": conversation_id,
                    "session_id": session_id,
                    "status": "success",
                },
            )

        except Exception as e:
            import traceback

            traceback.print_exc()
            return jsonify({"error": str(e)}), 500

    @app.route("/api/conversations", methods=["GET"])
    async def get_conversations():
        """获取会话的对话列表"""
        if not dashboard.context_mgr:
            return jsonify({"error": "Context manager not initialized"}), 500

        try:
            session_id = request.args.get("session_id", "default_session")
            conversations = await dashboard.context_mgr.get_conversation_list(
                session_id,
            )

            return jsonify(
                {
                    "conversations": conversations,
                    "status": "success",
                },
            )

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/conversations", methods=["POST"])
    async def create_conversation():
        """创建新对话"""
        if not dashboard.context_mgr:
            return jsonify({"error": "Context manager not initialized"}), 500

        try:
            data = await request.get_json()
            session_id = data.get("session_id", "default_session")
            title = data.get("title")

            conversation_id = await dashboard.context_mgr.create_new_conversation(
                session_id=session_id,
                platform_id="web",
                user_id=session_id,
                title=title,
            )

            return jsonify(
                {
                    "conversation_id": conversation_id,
                    "status": "success",
                },
            )

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/conversations/<conversation_id>", methods=["DELETE"])
    async def delete_conversation(conversation_id):
        """删除对话"""
        if not dashboard.context_mgr:
            return jsonify({"error": "Context manager not initialized"}), 500

        try:
            success = await dashboard.context_mgr.delete_conversation(conversation_id)

            if success:
                return jsonify({"status": "success"})
            return jsonify({"error": "Conversation not found"}), 404

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/conversations/<conversation_id>/switch", methods=["POST"])
    async def switch_conversation(conversation_id):
        """切换到指定对话"""
        if not dashboard.context_mgr:
            return jsonify({"error": "Context manager not initialized"}), 500

        try:
            data = await request.get_json()
            session_id = data.get("session_id", "default_session")

            success = await dashboard.context_mgr.switch_conversation(
                session_id,
                conversation_id,
            )

            if success:
                return jsonify({"status": "success"})
            return jsonify({"error": "Conversation not found"}), 404

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/conversations/<conversation_id>/history", methods=["GET"])
    async def get_conversation_history(conversation_id):
        """获取对话历史消息"""
        if not dashboard.context_mgr:
            return jsonify({"error": "Context manager not initialized"}), 500

        try:
            # 获取对话历史
            history = await dashboard.context_mgr.get_conversation_history(
                conversation_id,
            )

            return jsonify(
                {
                    "conversation_id": conversation_id,
                    "messages": history,
                    "status": "success",
                },
            )

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/config", methods=["GET"])
    async def get_config():
        """获取配置"""
        from ..config.config import config_manager

        try:
            config = config_manager.load_config()
            return jsonify(config)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/config", methods=["PUT"])
    async def update_config():
        """更新配置并热重载"""
        from ..config.config import config_manager

        try:
            data = await request.get_json()

            # 分离核心配置和扩展配置
            core_config = {}
            extension_config = {}

            # 获取配置section列表
            core_sections = config_manager.get_core_sections()
            extension_sections = config_manager.get_extension_sections()

            # 分离数据到对应的配置
            for section in core_sections:
                if section in data:
                    core_config[section] = data[section]

            for section in extension_sections:
                if section in data:
                    extension_config[section] = data[section]

            # 保存核心配置
            if core_config:
                with open(
                    config_manager.core_config_file,
                    "w",
                    encoding="utf-8",
                ) as f:
                    json.dump(core_config, f, indent=4, ensure_ascii=False)

            # 保存扩展配置
            if extension_config:
                with open(
                    config_manager.extension_config_file,
                    "w",
                    encoding="utf-8",
                ) as f:
                    json.dump(extension_config, f, indent=4, ensure_ascii=False)

            # 热重载配置管理器
            config_manager.reload_config()
            # 重新初始化LLM provider和agent配置
            dashboard._init_llm_provider()
            return jsonify(
                {"message": "Configuration updated and reloaded successfully"},
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/tools", methods=["GET"])
    async def get_tools():
        """获取所有工具状态"""
        from ..tool import get_tool_manager

        try:
            tool_mgr = get_tool_manager()
            tools_status = tool_mgr.get_all_tools_status()
            return jsonify(
                {
                    "tools": tools_status,
                    "status": "success",
                },
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/tools/<tool_name>", methods=["GET"])
    async def get_tool_status(tool_name):
        """获取指定工具状态"""
        from ..tool import get_tool_manager

        try:
            tool_mgr = get_tool_manager()
            status = tool_mgr.get_tool_status(tool_name)
            if status:
                return jsonify(
                    {
                        "tool": status,
                        "status": "success",
                    },
                )
            return jsonify({"error": "Tool not found"}), 404
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/tools/<tool_name>/enable", methods=["POST"])
    async def enable_tool(tool_name):
        """启用工具"""
        from ..tool import get_tool_manager

        try:
            tool_mgr = get_tool_manager()
            if tool_mgr.enable_tool(tool_name):
                return jsonify(
                    {
                        "message": f"Tool {tool_name} enabled successfully",
                        "status": "success",
                    },
                )
            return jsonify({"error": f"Failed to enable tool {tool_name}"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/tools/<tool_name>/disable", methods=["POST"])
    async def disable_tool(tool_name):
        """禁用工具"""
        from ..tool import get_tool_manager

        try:
            tool_mgr = get_tool_manager()
            if tool_mgr.disable_tool(tool_name):
                return jsonify(
                    {
                        "message": f"Tool {tool_name} disabled successfully",
                        "status": "success",
                    },
                )
            return jsonify({"error": f"Failed to disable tool {tool_name}"}), 400
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/tools/builtin/<sub_tool>/enable", methods=["POST"])
    async def enable_builtin_tool(sub_tool):
        """启用内置子工具"""
        from ..tool import get_tool_manager

        try:
            tool_mgr = get_tool_manager()
            if tool_mgr.enable_builtin_tool(sub_tool):
                return jsonify(
                    {
                        "message": f"Builtin tool {sub_tool} enabled successfully",
                        "status": "success",
                    },
                )
            return (
                jsonify(
                    {"error": f"Failed to enable builtin tool {sub_tool}"},
                ),
                400,
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/tools/builtin/<sub_tool>/disable", methods=["POST"])
    async def disable_builtin_tool(sub_tool):
        """禁用内置子工具"""
        from ..tool import get_tool_manager

        try:
            tool_mgr = get_tool_manager()
            if tool_mgr.disable_builtin_tool(sub_tool):
                return jsonify(
                    {
                        "message": f"Builtin tool {sub_tool} disabled successfully",
                        "status": "success",
                    },
                )
            return (
                jsonify(
                    {"error": f"Failed to disable builtin tool {sub_tool}"},
                ),
                400,
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/tools/builtin", methods=["GET"])
    async def get_builtin_tools():
        """获取内置工具状态"""
        from ..tool import get_tool_manager

        try:
            tool_mgr = get_tool_manager()
            enabled_tools = tool_mgr.get_builtin_tools_status()
            return jsonify(
                {
                    "enabled_tools": enabled_tools,
                    "status": "success",
                },
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/tools/save-and-reload", methods=["POST"])
    async def save_and_reload_tools():
        """保存工具状态并重新加载"""
        from ..tool import get_tool_manager

        try:
            tool_mgr = get_tool_manager()

            # 获取请求中的待处理更改
            data = await request.get_json()
            changes = data.get("changes", []) if data else []

            # 应用所有待处理的更改
            for change in changes:
                action, tool_name = change.split(":", 1)
                if action == "enable":
                    tool_mgr.enable_tool(tool_name)
                elif action == "disable":
                    tool_mgr.disable_tool(tool_name)
                elif action == "enable_builtin":
                    tool_mgr.enable_builtin_tool(tool_name)
                elif action == "disable_builtin":
                    tool_mgr.disable_builtin_tool(tool_name)

            # 保存并重载
            await tool_mgr.save_and_reload()

            # 重置全局Agent，以便下次使用新的工具列表
            dashboard.global_agent = None

            return jsonify(
                {
                    "message": "Tools saved and reloaded successfully",
                    "status": "success",
                },
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/tasks", methods=["GET"])
    async def get_tasks():
        """获取任务列表"""
        if not dashboard.task_manager:
            return jsonify({"error": "Task manager not initialized"}), 500

        try:
            session_id = request.args.get("session_id")
            status = request.args.get("status")
            limit = int(request.args.get("limit", 50))

            tasks = await dashboard.task_manager.list_tasks(
                session_id=session_id,
                status=status,
                limit=limit,
            )

            return jsonify(
                {
                    "tasks": [task.__dict__ for task in tasks],
                    "status": "success",
                },
            )

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/tasks/<task_id>", methods=["GET"])
    async def get_task_status(task_id):
        """获取任务状态"""
        if not dashboard.task_manager:
            return jsonify({"error": "Task manager not initialized"}), 500

        try:
            task = await dashboard.task_manager.get_task_status(task_id)
            if task:
                return jsonify(
                    {
                        "task": task.__dict__,
                        "status": "success",
                    },
                )
            return jsonify({"error": "Task not found"}), 404

        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/tasks/<task_id>/cancel", methods=["POST"])
    async def cancel_task(task_id):
        """取消任务"""
        if not dashboard.task_manager:
            return jsonify({"error": "Task manager not initialized"}), 500

        try:
            success = await dashboard.task_manager.cancel_task(task_id)
            if success:
                return jsonify(
                    {
                        "message": "Task cancelled successfully",
                        "status": "success",
                    },
                )
            return jsonify({"error": "Task not found or cannot be cancelled"}), 404

        except Exception as e:
            return jsonify({"error": str(e)}), 500
