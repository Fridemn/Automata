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
from agents import Agent, Runner, RunConfig, SQLiteSession
from agents.models.multi_provider import OpenAIProvider


class AutomataLauncher:
    """Automata 启动器"""

    def __init__(self, webui_dir: Optional[str] = None):
        self.webui_dir = webui_dir
        self.dashboard_server: Optional[AutomataDashboard] = None
        self.agent: Optional[Agent] = None
        self.run_config: Optional[RunConfig] = None
        self.session: Optional[SQLiteSession] = None

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

        # 创建Agent
        self.agent = Agent(
            name=agent_config.get("name", "AutomataAssistant"),
            instructions=agent_config.get("instructions", "You are a helpful assistant."),
            model=openai_config.get("model", "gpt-4")
        )

        # 创建运行配置
        self.run_config = RunConfig(model_provider=model_provider)

        # 创建session用于对话历史
        self.session = SQLiteSession("automata_cli")

        print("✅ Automata initialized successfully")
        return True

    async def run_cli_mode(self):
        """运行命令行模式"""
        print("💬 Starting CLI mode...")

        while True:
            try:
                # 提示用户输入查询内容
                user_query = input("请输入您的问题 (输入 'exit' 退出): ").strip()

                if user_query.lower() == 'exit':
                    print("再见！")
                    break

                if not user_query:
                    print("查询内容不能为空")
                    continue

                print(f"用户查询: {user_query}")
                print("正在处理中...")

                # 使用Runner运行Agent
                result = await Runner.run(self.agent, user_query, session=self.session, run_config=self.run_config)
                print(f"\nAgent响应: {result.final_output}")

            except KeyboardInterrupt:
                print("\n再见！")
                break
            except Exception as e:
                print(f"发生错误: {e}")

    async def run_web_mode(self):
        """运行Web模式"""
        print("🌐 Starting Web mode...")

        # 初始化仪表板服务器
        self.dashboard_server = AutomataDashboard(self.webui_dir)

        # 启动Web服务器
        await self.dashboard_server.run()

    async def run_combined_mode(self):
        """运行组合模式（CLI + Web）"""
        print("🚀 Starting combined mode (CLI + Web)...")

        # 初始化仪表板服务器
        self.dashboard_server = AutomataDashboard(self.webui_dir)

        # 同时运行CLI和Web服务器
        cli_task = asyncio.create_task(self.run_cli_mode())
        web_task = asyncio.create_task(self.dashboard_server.run())

        try:
            await asyncio.gather(cli_task, web_task)
        except Exception as e:
            print(f"❌ Error in combined mode: {e}")
            raise

    async def start(self, mode: str = "cli"):
        """启动Automata"""
        success = await self.initialize()
        if not success:
            return

        if mode == "cli":
            await self.run_cli_mode()
        elif mode == "web":
            await self.run_web_mode()
        elif mode == "combined":
            await self.run_combined_mode()
        else:
            print(f"❌ Unknown mode: {mode}")
            print("Available modes: cli, web, combined")


async def main():
    parser = argparse.ArgumentParser(description="Automata - AI Personality System")
    parser.add_argument(
        "--mode",
        choices=["cli", "web", "combined"],
        default="cli",
        help="运行模式：cli(命令行), web(网页), combined(命令行+网页)"
    )
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
        await launcher.start(args.mode)
    except KeyboardInterrupt:
        print("\n👋 Shutting down Automata...")
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())