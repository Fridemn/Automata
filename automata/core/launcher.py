#!/usr/bin/env python3
"""
Automata 启动器，负责初始化和启动核心组件和仪表板服务器。
"""

import asyncio
import argparse
import os
import sys
from typing import Optional
from automata.core.utils.path_utils import get_project_root

# 添加项目根目录到 Python 路径
sys.path.insert(0, get_project_root())

from automata.core.server.web_server import AutomataDashboard
from automata.core.config.config import get_openai_config, get_agent_config
from automata.core.tool import get_tool_manager, initialize_tools
from automata.core.tasks.task_manager import TaskManager
from automata.core.db.database import DatabaseManager
from automata.core.initialization_manager import InitializationManager
from automata.core.dependency_container import DependencyContainer
from agents import Agent, Runner, RunConfig, SQLiteSession
from agents.models.multi_provider import OpenAIProvider
from agents.mcp import MCPServerStdio


class AutomataLauncher:
    """Automata 启动器"""

    def __init__(self, webui_dir: Optional[str] = None):
        self.webui_dir = webui_dir
        self.dashboard_server: Optional[AutomataDashboard] = None
        self.agent: Optional[Agent] = None
        self.run_config: Optional[RunConfig] = None
        self.session: Optional[SQLiteSession] = None
        self.mcp_servers: list = []

        # 初始化管理器和依赖容器
        self.init_manager = InitializationManager()
        self.container = DependencyContainer()

        # 注册核心服务到容器
        self._register_services()

    def _register_services(self):
        """注册服务到依赖注入容器"""
        # 注册配置服务
        self.container.register_factory("openai_config", lambda: get_openai_config())
        self.container.register_factory("agent_config", lambda: get_agent_config())

        # 注册数据库管理器
        self.container.register(DatabaseManager)

        # 注册任务管理器（依赖数据库管理器）
        async def create_task_manager():
            db_manager = self.container.resolve(DatabaseManager)
            return TaskManager(db_manager)
        self.container.register_factory("TaskManager", create_task_manager)

        # 注册模型提供者（依赖配置）
        async def create_model_provider():
            openai_config = self.container.resolve("openai_config")
            api_key = openai_config.get("api_key")
            api_base_url = openai_config.get("api_base_url")

            return OpenAIProvider(
                api_key=api_key,
                base_url=api_base_url,
                use_responses=False
            )
        self.container.register_factory("OpenAIProvider", create_model_provider)

    async def initialize(self):
        """初始化Automata"""
        print("🔧 Initializing Automata...")

        # 注册初始化器
        self._register_initializers()

        # 执行初始化
        results = await self.init_manager.initialize_all(parallel=True)

        # 检查结果
        summary = self.init_manager.get_results_summary()
        print(f"📊 Initialization Summary: {summary['success']}/{summary['total']} successful")

        if summary['failed'] > 0:
            print("❌ Failed initializations:")
            for name, detail in summary['details'].items():
                if detail['status'] == 'failed':
                    print(f"  - {name}: {detail['error']}")

        success = self.init_manager.is_successful()
        if success:
            print("✅ Automata initialized successfully")
        else:
            print("❌ Automata initialization failed")

        return success

    def _register_initializers(self):
        """注册所有初始化器"""
        # 配置加载（无依赖）
        self.init_manager.register_initializer("config", self._init_configurations)

        # 数据库初始化（无依赖）
        self.init_manager.register_initializer("database", self._init_database)

        # 任务管理器（依赖数据库）
        self.init_manager.register_initializer("task_manager", self._init_task_manager, ["database"])

        # 模型提供者（依赖配置）
        self.init_manager.register_initializer("model_provider", self._init_model_provider, ["config"])

        # 工具系统（依赖任务管理器）
        self.init_manager.register_initializer("tools", self._init_tools, ["task_manager"])

        # Agent创建（依赖配置、模型提供者、工具）
        self.init_manager.register_initializer("agent", self._init_agent, ["config", "model_provider", "tools"])

        # 会话设置（依赖Agent）
        self.init_manager.register_initializer("session", self._init_session, ["agent"])

    async def _init_configurations(self):
        """初始化配置"""
        self.openai_config = self.container.resolve("openai_config")
        self.agent_config = self.container.resolve("agent_config")

        api_key = self.openai_config.get("api_key")
        if not api_key:
            raise ValueError("Please set openai.api_key in data/config.json")

        return {"openai_config": self.openai_config, "agent_config": self.agent_config}

    async def _init_database(self):
        """初始化数据库管理器"""
        self.db_manager = self.container.resolve(DatabaseManager)
        await self.db_manager.initialize()

        return self.db_manager

    async def _init_task_manager(self):
        """初始化任务管理器"""
        self.task_manager = self.container.resolve("TaskManager")

        return self.task_manager

    async def _init_model_provider(self):
        """初始化模型提供者"""
        self.model_provider = self.container.resolve("OpenAIProvider")

        return self.model_provider

    async def _init_tools(self):
        """初始化工具系统"""
        # 从容器获取配置和任务管理器
        agent_config = self.container.resolve("agent_config")
        task_manager = self.container.resolve("TaskManager")

        tool_config = {
            "builtin": {
                "enabled": agent_config.get("enable_tools", True)
            },
            "extensions": {
                "enabled": True  # TODO: 从配置中获取
            },
            "mcp": {
                "enabled": agent_config.get("enable_mcp", False),
                "filesystem": {
                    "enabled": True,  # TODO: 从配置中获取
                    "root_path": os.getcwd()
                }
            }
        }

        await initialize_tools(tool_config, task_manager)

        return tool_config

    async def _init_agent(self):
        """创建Agent"""
        # 从容器获取所需组件
        agent_config = self.container.resolve("agent_config")
        openai_config = self.container.resolve("openai_config")
        model_provider = self.container.resolve("OpenAIProvider")

        tool_mgr = get_tool_manager()
        tools = tool_mgr.get_all_function_tools()
        mcp_servers = tool_mgr.get_mcp_servers()

        self.agent = Agent(
            name=agent_config.get("name"),
            instructions=agent_config.get("instructions"),
            model=openai_config.get("model"),
            tools=tools,
            mcp_servers=mcp_servers
        )

        # 创建运行配置
        self.run_config = RunConfig(model_provider=model_provider)

        return self.agent

    async def _init_session(self):
        """设置会话"""
        self.session = await asyncio.to_thread(SQLiteSession, "automata_cli")

        return self.session

    async def cleanup(self):
        """清理资源"""
        try:
            # 清理工具管理器
            tool_mgr = get_tool_manager()
            await tool_mgr.cleanup()
        except Exception as e:
            print(f"Warning: Error during cleanup: {e}")

    async def run_web_mode(self):
        """运行Web模式"""
        print("🌐 Starting Web mode...")

        # 初始化仪表板服务器
        self.dashboard_server = AutomataDashboard(self.webui_dir)
        self.dashboard_server.set_task_manager(self.task_manager)

        # 启动Web服务器
        await self.dashboard_server.run()

    async def start(self):
        """启动Automata"""
        success = await self.initialize()
        if not success:
            return

        await self.run_web_mode()

        # 清理资源
        await self.cleanup()


async def main():
    parser = argparse.ArgumentParser(description="Automata - AI Personality System")
    parser.add_argument(
        "--webui-dir",
        type=str,
        help="指定WebUI静态文件目录路径",
        default=None
    )

    args = parser.parse_args()

    # 检查环境
    if not (sys.version_info.major == 3 and sys.version_info.minor >= 10):
        print("请使用 Python3.10+ 运行本项目。")
        return

    # 创建启动器
    launcher = AutomataLauncher(args.webui_dir)

    try:
        await launcher.start()
    except KeyboardInterrupt:
        print("\n👋 Shutting down Automata...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())