#!/usr/bin/env python3
"""
工具模块独立测试
"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(__file__))

from automata.core.tool.manager import ToolManager
from automata.core.tool.builtin import create_builtin_tools


async def test_tool_modules():
    """测试工具模块"""
    print("🔧 Testing tool modules...")

    # 创建工具管理器
    manager = ToolManager()

    # 初始化配置
    config = {
        "builtin": {
            "enabled": True
        }
    }

    await manager.initialize(config)

    print(f"✅ Initialized {len(manager.get_all_tools())} tools")
    print(f"✅ Function tools: {len(manager.get_all_function_tools())}")

    # 列出所有工具
    tools = manager.get_all_tools()
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")

    # 测试内置工具
    builtin_tool = create_builtin_tools("test_builtin")
    print(f"✅ Created builtin tool with {len(builtin_tool.get_function_tools())} functions")

    # 清理
    await manager.cleanup()
    print("✅ Tool modules test completed")


if __name__ == "__main__":
    asyncio.run(test_tool_modules())