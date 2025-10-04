#!/usr/bin/env python3
"""
Automata 启动器，负责初始化和启动核心组件和仪表板服务器。
"""

import asyncio
import argparse
import os
import sys
from typing import Optional

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from automata.core.server.web_server import AutomataDashboard
from automata.core.config.config import get_openai_config, get_agent_config
from automata.core.tool import get_tool_manager, initialize_tools
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

    async def initialize(self):
        """初始化Automata"""
        print("🔧 Initializing Automata...")

        # 获取配置
        try:
            openai_config = get_openai_config()
            agent_config = get_agent_config()
        except Exception as e:
            print(f"❌ Failed to load configuration: {e}")
            return False

        api_key = openai_config.get("api_key")
        if not api_key or api_key == "your_api_key_here":
            print("⚠️  Please set openai.api_key in data/config.json")
            return False

        api_base_url = openai_config.get("api_base_url", "https://api.openai.com/v1")

        # 配置模型提供者
        model_provider = OpenAIProvider(
            api_key=api_key,
            base_url=api_base_url,
            use_responses=False
        )

        # 初始化工具系统
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

        # 获取工具管理器
        tool_mgr = get_tool_manager()

        # 获取所有函数工具和 MCP 服务器
        tools = tool_mgr.get_all_function_tools()
        mcp_servers = tool_mgr.get_mcp_servers()

        # 创建Agent
        self.agent = Agent(
            name=agent_config.get("name", "AutomataAssistant"),
            instructions=agent_config.get("instructions", "You are a helpful assistant."),
            model=openai_config.get("model", "gpt-4"),
            tools=tools,
            mcp_servers=mcp_servers
        )

        # 创建运行配置
        self.run_config = RunConfig(model_provider=model_provider)

        # 创建session用于对话历史
        self.session = SQLiteSession("automata_cli")

        print("✅ Automata initialized successfully")
        return True

    async def cleanup(self):
        """清理资源"""
        # 清理工具管理器
        tool_mgr = get_tool_manager()
        await tool_mgr.cleanup()

    async def run_web_mode(self):
        """运行Web模式"""
        print("🌐 Starting Web mode...")

        # 初始化仪表板服务器
        self.dashboard_server = AutomataDashboard(self.webui_dir)

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

    os.makedirs("data", exist_ok=True)

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