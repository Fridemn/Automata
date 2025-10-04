#!/usr/bin/env python3
"""
Automata Web服务器，用于服务前端静态文件
"""

import os
import asyncio
import logging
import json
from quart import Quart, request, jsonify
from quart.logging import default_handler

# 配置日志
logging.getLogger('quart.app').setLevel(logging.INFO)
logging.getLogger('quart.serving').setLevel(logging.WARNING)

class AutomataDashboard:
    def __init__(self, webui_dir: str | None = None):
        # 设置静态文件目录
        if webui_dir and os.path.exists(webui_dir):
            self.static_folder = os.path.abspath(webui_dir)
        else:
            # 默认使用dashboard/dist目录
            # 从automata/core/server/web_server.py向上三级到项目根目录，然后到dashboard/dist
            current_dir = os.path.dirname(os.path.abspath(__file__))  # automata/core
            print(f"current_dir: {current_dir}")
            parent_dir = os.path.dirname(current_dir)  # automata/core
            print(f"parent_dir: {parent_dir}")
            grandparent_dir = os.path.dirname(parent_dir)  # automata
            print(f"grandparent_dir: {grandparent_dir}")
            project_root = os.path.dirname(grandparent_dir)  # 项目根目录
            print(f"project_root: {project_root}")
            self.static_folder = os.path.join(project_root, "dashboard", "dist")
            print(f"static_folder: {self.static_folder}")

        self.app = Quart("automata-dashboard", static_folder=self.static_folder, static_url_path="/")
        self.app.config["MAX_CONTENT_LENGTH"] = 128 * 1024 * 1024  # 128MB

        # 初始化LLM provider
        self._init_llm_provider()

        # 设置路由
        self._setup_routes()
        print(f"Static folder set to: {self.static_folder}")

    def _init_llm_provider(self):
        """初始化LLM provider和上下文管理器"""
        try:
            from ..provider.simple_provider import create_simple_provider_from_config
            from ..config.config import get_agent_config
            from ..managers.context_mgr import ContextManager
            from agents import Agent, SQLiteSession
            from agents.extensions.memory import SQLAlchemySession

            self.provider = create_simple_provider_from_config()
            self.run_config = self.provider.create_run_config()

            # 初始化上下文管理器
            self.context_mgr = ContextManager()

            # 初始化Agent配置
            agent_config = get_agent_config()
            self.agent_config = agent_config

            # 会话缓存：conversation_id -> SQLiteSession
            self.agent_sessions = {}

            # Agent缓存：conversation_id -> Agent
            self.agent_cache = {}

            # 全局Agent实例（复用同一个Agent）
            self.global_agent = None

            print("✅ LLM provider and context manager initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize LLM provider: {e}")
            self.provider = None
            self.agent = None
            self.run_config = None
            self.context_mgr = None
            self.agent_sessions = {}
            self.agent_cache = {}
            self.global_agent = None

    def _get_or_create_agent(self, conversation_id: str):
        """获取或创建Agent实例 - 现在使用全局Agent"""
        if self.global_agent is None:
            from agents import Agent
            from ..tool import get_tool_manager
            from ..config.config import get_agent_config

            agent_config = get_agent_config()
            tool_mgr = get_tool_manager()

            # 获取所有函数工具和 MCP 服务器
            tools = tool_mgr.get_all_function_tools()
            mcp_servers = tool_mgr.get_mcp_servers()

            self.global_agent = Agent(
                name=self.agent_config["name"],
                instructions=self.agent_config["instructions"],
                model=self.provider.provider_config["model"],
                tools=tools,
                mcp_servers=mcp_servers
            )
            print("Created global agent instance with tools")
        return self.global_agent

    def cleanup_old_sessions(self, max_sessions: int = 100):
        """清理旧的session缓存，避免内存泄漏"""
        if len(self.agent_sessions) > max_sessions:
            # 简单的LRU清理：移除最早的session
            sessions_to_remove = list(self.agent_sessions.keys())[:-max_sessions//2]
            for conv_id in sessions_to_remove:
                if conv_id in self.agent_sessions:
                    del self.agent_sessions[conv_id]
            print(f"Cleaned up {len(sessions_to_remove)} old sessions")

    def _setup_routes(self):
        @self.app.route('/')
        async def index():
            """服务index.html"""
            index_path = os.path.join(self.static_folder, "index.html")
            if os.path.exists(index_path):
                return await self.app.send_static_file("index.html")
            return "Dashboard not found. Please build the frontend first."

        @self.app.route('/<path:path>')
        async def static_files(path):
            """服务其他静态文件"""
            return await self.app.send_static_file(path)

        @self.app.route('/api/chat', methods=['POST'])
        async def chat():
            """处理聊天请求"""
            if not self.provider or not self.run_config or not self.context_mgr:
                return jsonify({"error": "LLM provider not initialized"}), 500

            try:
                data = await request.get_json()
                user_query = data.get('message', '').strip()
                session_id = data.get('session_id', 'default_session')

                if not user_query:
                    return jsonify({"error": "Message cannot be empty"}), 400

                # 初始化会话上下文
                conversation_id = await self.context_mgr.initialize_session(
                    session_id=session_id,
                    platform_id="web",
                    user_id=session_id,  # 使用session_id作为user_id
                )

                # 获取或创建Agent session
                from agents.extensions.memory import SQLAlchemySession
                if conversation_id not in self.agent_sessions:
                    # 为这个对话创建一个新的SQLAlchemySession，使用现有的数据库引擎
                    agent_session = SQLAlchemySession(
                        f"automata_{conversation_id}",
                        engine=self.context_mgr.db.engine,
                        create_tables=True
                    )
                    self.agent_sessions[conversation_id] = agent_session
                    self.context_mgr.set_session(conversation_id, agent_session)
                    print(f"Created new session for conversation {conversation_id}")
                else:
                    agent_session = self.agent_sessions[conversation_id]
                    self.context_mgr.set_session(conversation_id, agent_session)
                    print(f"Reusing existing session for conversation {conversation_id}")

                # 获取或创建Agent实例
                agent = self._get_or_create_agent(conversation_id)

                # 定期清理旧session
                self.cleanup_old_sessions()

                # 使用OpenAI Agent SDK的session调用LLM
                import time
                from agents import Runner
                print(f"Calling Runner.run with session: {agent_session.session_id}")
                start_time = time.time()
                result = await Runner.run(
                    agent,
                    user_query,
                    session=agent_session,
                    run_config=self.run_config
                )
                end_time = time.time()
                print(f"Runner.run completed in {end_time - start_time:.2f} seconds, result: {str(result.final_output)[:100]}...")

                return jsonify({
                    "response": str(result.final_output),
                    "conversation_id": conversation_id,
                    "session_id": session_id,
                    "status": "success"
                })

            except Exception as e:
                print(f"Error in chat endpoint: {e}")
                import traceback
                traceback.print_exc()
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/conversations', methods=['GET'])
        async def get_conversations():
            """获取会话的对话列表"""
            if not self.context_mgr:
                return jsonify({"error": "Context manager not initialized"}), 500

            try:
                session_id = request.args.get('session_id', 'default_session')
                conversations = await self.context_mgr.get_conversation_list(session_id)

                return jsonify({
                    "conversations": conversations,
                    "status": "success"
                })

            except Exception as e:
                print(f"Error getting conversations: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/conversations', methods=['POST'])
        async def create_conversation():
            """创建新对话"""
            if not self.context_mgr:
                return jsonify({"error": "Context manager not initialized"}), 500

            try:
                data = await request.get_json()
                session_id = data.get('session_id', 'default_session')
                title = data.get('title')

                conversation_id = await self.context_mgr.create_new_conversation(
                    session_id=session_id,
                    platform_id="web",
                    user_id=session_id,
                    title=title,
                )

                return jsonify({
                    "conversation_id": conversation_id,
                    "status": "success"
                })

            except Exception as e:
                print(f"Error creating conversation: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/conversations/<conversation_id>', methods=['DELETE'])
        async def delete_conversation(conversation_id):
            """删除对话"""
            if not self.context_mgr:
                return jsonify({"error": "Context manager not initialized"}), 500

            try:
                success = await self.context_mgr.delete_conversation(conversation_id)

                if success:
                    return jsonify({"status": "success"})
                else:
                    return jsonify({"error": "Conversation not found"}), 404

            except Exception as e:
                print(f"Error deleting conversation: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/conversations/<conversation_id>/switch', methods=['POST'])
        async def switch_conversation(conversation_id):
            """切换到指定对话"""
            if not self.context_mgr:
                return jsonify({"error": "Context manager not initialized"}), 500

            try:
                data = await request.get_json()
                session_id = data.get('session_id', 'default_session')

                success = await self.context_mgr.switch_conversation(session_id, conversation_id)

                if success:
                    return jsonify({"status": "success"})
                else:
                    return jsonify({"error": "Conversation not found"}), 404

            except Exception as e:
                print(f"Error switching conversation: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/conversations/<conversation_id>/history', methods=['GET'])
        async def get_conversation_history(conversation_id):
            """获取对话历史消息"""
            if not self.context_mgr:
                return jsonify({"error": "Context manager not initialized"}), 500

            try:
                # 获取对话历史
                history = await self.context_mgr.get_conversation_history(conversation_id)

                return jsonify({
                    "conversation_id": conversation_id,
                    "messages": history,
                    "status": "success"
                })

            except Exception as e:
                print(f"Error getting conversation history: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/config', methods=['GET'])
        async def get_config():
            """获取配置"""
            from ..config.config import config_manager
            try:
                config = config_manager.load_config()
                return jsonify(config)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        @self.app.route('/api/config', methods=['PUT'])
        async def update_config():
            """更新配置并热重载"""
            from ..config.config import config_manager
            try:
                data = await request.get_json()
                # 更新配置文件
                with open(config_manager.config_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                # 热重载配置管理器
                config_manager.reload_config()
                # 重新初始化LLM provider和agent配置
                self._init_llm_provider()
                return jsonify({"message": "Configuration updated and reloaded successfully"})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

    async def run(self, host: str = "0.0.0.0", port: int = 8080):
        """启动Web服务器"""
        # 初始化工具系统
        from ..tool import initialize_tools
        from ..config.config import get_agent_config

        agent_config = get_agent_config()
        tool_config = {
            "builtin": {
                "enabled": agent_config.get("enable_tools", True)
            },
            "mcp": {
                "enabled": agent_config.get("enable_mcp", False),
                "filesystem": {
                    "enabled": True,
                    "root_path": os.getcwd()
                }
            }
        }
        await initialize_tools(tool_config)

        print(f"🚀 Starting Automata Dashboard at http://localhost:{port}")
        print(f"📁 Serving static files from: {self.static_folder}")

        try:
            await self.app.run_task(host=host, port=port)
        except Exception as e:
            print(f"❌ Failed to start dashboard server: {e}")
            raise