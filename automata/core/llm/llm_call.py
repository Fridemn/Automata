import os
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from agents import Agent, Runner
from automata.core.config.config import get_agent_config
from automata.core.provider.simple_provider import create_simple_provider_from_config

# 从配置文件创建 provider
provider = create_simple_provider_from_config()
model_provider = provider.get_model_provider()
run_config = provider.create_run_config()

# 获取配置
agent_config = get_agent_config()

# 创建一个简单的Agent，使用配置文件
agent = Agent(
    name=agent_config["name"],
    instructions=agent_config["instructions"],
    model=provider.provider_config["model"]
)

async def main():
    # 提示用户输入查询内容
    user_query = input("请输入您的问题: ").strip()

    if not user_query:
        print("查询内容不能为空")
        return

    print(f"用户查询: {user_query}")
    print("正在处理中...")

    # 使用Runner运行Agent
    result = await Runner.run(agent, user_query, run_config=run_config)

    print(f"\nAgent响应: {result.final_output}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())