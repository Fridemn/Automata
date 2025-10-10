import sys

from automata.core.utils.path_utils import get_project_root

# 添加项目根目录到 Python 路径
sys.path.insert(0, get_project_root())

from agents import Agent, Runner

from automata.core.config.config import get_agent_config
from automata.core.provider.sources.openai_source import (
    create_openai_source_provider_from_config,
)

# 从配置文件创建 provider
provider = create_openai_source_provider_from_config()
model_provider = provider.get_model_provider()
run_config = provider.create_run_config()

# 获取配置
agent_config = get_agent_config()

# 创建一个简单的Agent，使用配置文件
agent = Agent(
    name=agent_config["name"],
    instructions=agent_config["instructions"],
    model=provider.provider_config["model"],
)


async def main():
    # 提示用户输入查询内容
    user_query = input("请输入您的问题: ").strip()

    if not user_query:
        return

    # 使用Runner运行Agent
    await Runner.run(agent, user_query, run_config=run_config)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
