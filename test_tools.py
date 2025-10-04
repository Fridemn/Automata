#!/usr/bin/env python3
"""
工具系统测试脚本
"""

import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from automata.core.tool import initialize_tools, get_tool_manager


async def test_tools():
    """测试工具系统"""
    print("🔧 Testing tool system...")

    # 初始化工具
    config = {
        "builtin": {
            "enabled": True
        },
        "custom": {
            "enabled": True,
            "functions": {}
        }
    }

    await initialize_tools(config)

    tool_mgr = get_tool_manager()

    print(f"✅ Initialized {len(tool_mgr.get_all_tools())} tools")
    print(f"✅ Function tools: {len(tool_mgr.get_all_function_tools())}")
    print(f"✅ MCP servers: {len(tool_mgr.get_mcp_servers())}")

    # 测试工具
    tools = tool_mgr.get_all_tools()
    for tool in tools:
        print(f"  - {tool.name}: {tool.description}")

    # 测试自定义函数添加
    def test_function(x: int, y: int) -> int:
        """测试函数"""
        return x + y

    tool_mgr.add_custom_function("test_add", test_function, "加法运算")

    print(f"✅ Added custom function, now {len(tool_mgr.get_all_function_tools())} function tools")

    # 清理
    await tool_mgr.cleanup()
    print("✅ Tool system test completed")


if __name__ == "__main__":
    asyncio.run(test_tools())