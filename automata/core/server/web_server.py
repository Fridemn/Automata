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
            current_dir = os.path.dirname(os.path.abspath(__file__))  # automata/core/server
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

            print("✅ LLM provider and context manager initialized successfully")
        except Exception as e:
            print(f"❌ Failed to initialize LLM provider: {e}")
            self.provider = None
            self.agent = None
            self.run_config = None
            self.context_mgr = None
            self.agent_sessions = {}

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
                from agents import Agent
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

                    # 创建Agent（每个对话可以有不同的配置）
                    agent = Agent(
                        name=self.agent_config["name"],
                        instructions=self.agent_config["instructions"],
                        model=self.provider.provider_config["model"]
                    )
                else:
                    agent_session = self.agent_sessions[conversation_id]
                    self.context_mgr.set_session(conversation_id, agent_session)
                    print(f"Reusing existing session for conversation {conversation_id}")
                    
                    # 复用已有的Agent
                    agent = Agent(
                        name=self.agent_config["name"],
                        instructions=self.agent_config["instructions"],
                        model=self.provider.provider_config["model"]
                    )

                # 调试：检查session中的现有items
                existing_items = await agent_session.get_items()
                print(f"Session has {len(existing_items)} existing items")
                for i, item in enumerate(existing_items[-3:]):  # 只显示最后3个
                    print(f"  Item {i}: {item.get('role', 'unknown')} - {item.get('content', '')[:50]}...")

                # 使用OpenAI Agent SDK的session调用LLM
                from agents import Runner
                print(f"Calling Runner.run with session: {agent_session.session_id}")
                result = await Runner.run(
                    agent,
                    user_query,
                    session=agent_session,
                    run_config=self.run_config
                )
                print(f"Runner.run completed, result: {str(result.final_output)[:100]}...")

                # 调试：检查session更新后的items
                updated_items = await agent_session.get_items()
                print(f"Session now has {len(updated_items)} items after run")
                for i, item in enumerate(updated_items[-3:]):  # 只显示最后3个
                    print(f"  Updated item {i}: {item.get('role', 'unknown')} - {item.get('content', '')[:50]}...")

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

    async def run(self, host: str = "0.0.0.0", port: int = 8080):
        """启动Web服务器"""
        print(f"🚀 Starting Automata Dashboard at http://localhost:{port}")
        print(f"📁 Serving static files from: {self.static_folder}")

        try:
            await self.app.run_task(host=host, port=port)
        except Exception as e:
            print(f"❌ Failed to start dashboard server: {e}")
            raise