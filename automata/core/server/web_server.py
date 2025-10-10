#!/usr/bin/env python3
"""
Automata Web服务器，用于服务前端静态文件
"""

from __future__ import annotations

import asyncio
import json
import logging
import os

from agents import Agent
from quart import Quart, jsonify, request

from automata.core.utils.path_utils import get_static_folder

from ..config.config import get_agent_config, get_openai_config
from ..managers.context_mgr import ContextManager
from ..provider.sources.openai_source import create_openai_source_provider_from_config
from ..tool import get_tool_manager, initialize_tools
from .router import setup_routes

# 配置日志
logging.getLogger("quart.app").setLevel(logging.INFO)
logging.getLogger("quart.serving").setLevel(logging.WARNING)


class AutomataDashboard:
    def __init__(self, webui_dir: str | None = None):
        # 设置静态文件目录
        if webui_dir and os.path.exists(webui_dir):
            self.static_folder = os.path.abspath(webui_dir)
        else:
            # 默认使用dashboard/dist目录
            self.static_folder = get_static_folder()

        self.app = Quart(
            "automata-dashboard",
            static_folder=self.static_folder,
            static_url_path="/",
        )
        self.app.config["MAX_CONTENT_LENGTH"] = 128 * 1024 * 1024  # 128MB

        # 初始化LLM provider
        self._init_llm_provider()

        # 设置路由
        self._setup_routes()

    def _init_llm_provider(self):
        """初始化LLM provider和上下文管理器"""
        try:
            self.provider = create_openai_source_provider_from_config()
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

            # 任务管理器
            self.task_manager = None

        except Exception:
            self.provider = None
            self.agent = None
            self.run_config = None
            self.context_mgr = None
            self.agent_sessions = {}
            self.agent_cache = {}
            self.global_agent = None

    def set_task_manager(self, task_manager):
        """设置任务管理器"""
        self.task_manager = task_manager

    def _get_or_create_agent(self, conversation_id: str):
        """获取或创建Agent实例 - 现在使用全局Agent"""
        if self.global_agent is None:
            get_agent_config()
            tool_mgr = get_tool_manager()

            # 获取所有函数工具和 MCP 服务器
            tools = tool_mgr.get_all_function_tools()
            mcp_servers = tool_mgr.get_mcp_servers()

            openai_config = get_openai_config()
            model = openai_config.get("model")
            if not model:
                msg = "Model must be specified in openai config"
                raise ValueError(msg)

            self.global_agent = Agent(
                name=self.agent_config["name"],
                instructions=self.agent_config["instructions"],
                model=model,
                tools=tools,
                mcp_servers=mcp_servers,
            )
        return self.global_agent

    def cleanup_old_sessions(self, max_sessions: int = 100):
        """清理旧的session缓存，避免内存泄漏"""
        if len(self.agent_sessions) > max_sessions:
            # 简单的LRU清理：移除最早的session
            sessions_to_remove = list(self.agent_sessions.keys())[: -max_sessions // 2]
            for conv_id in sessions_to_remove:
                if conv_id in self.agent_sessions:
                    del self.agent_sessions[conv_id]

    def _setup_routes(self):
        """设置路由"""

        setup_routes(self.app, self)

    async def run(self, host: str = "0.0.0.0", port: int = 8080):
        """启动Web服务器"""
        # 初始化工具系统

        agent_config = get_agent_config()
        tool_config = {
            "builtin": {
                "enabled": agent_config.get("enable_tools", True),
            },
            "mcp": {
                "enabled": agent_config.get("enable_mcp", False),
                "filesystem": {
                    "enabled": True,
                    "root_path": os.getcwd(),
                },
            },
        }
        await initialize_tools(tool_config)

        try:
            await self.app.run_task(host=host, port=port)
        except Exception:
            raise
