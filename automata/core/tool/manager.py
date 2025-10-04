#!/usr/bin/env python3
"""
工具管理器
统一管理所有工具的注册、初始化和生命周期
"""

import asyncio
from typing import Any, Dict, List, Optional, Union
from agents import FunctionTool
from .base import ToolRegistry, ToolConfig
from .builtin import BuiltinTools, create_builtin_tools
from .custom import CustomFunctionTool, create_custom_function_tool
from .mcp import MCPTool, MCPManager, create_filesystem_mcp_tool


class ToolManager:
    """工具管理器"""

    def __init__(self):
        self.registry = ToolRegistry()
        self.mcp_manager = MCPManager()
        self._initialized = False

    async def initialize(self, config: Dict[str, Any] = None) -> None:
        """初始化工具管理器"""
        if self._initialized:
            return

        if config is None:
            config = {}

        # 初始化内置工具
        builtin_config = config.get("builtin", {})
        if builtin_config.get("enabled", True):
            builtin_tools = create_builtin_tools(
                name="builtin",
                enabled_tools=builtin_config.get("enabled_tools", [])
            )
            self.registry.register(builtin_tools, "builtin")

        # 初始化自定义函数工具
        custom_config = config.get("custom", {})
        if custom_config.get("enabled", False):
            custom_functions = custom_config.get("functions", {})
            custom_tool = create_custom_function_tool(
                name="custom",
                functions=custom_functions
            )
            self.registry.register(custom_tool, "custom")

        # 初始化 MCP 工具
        mcp_config = config.get("mcp", {})
        if mcp_config.get("enabled", False):
            # 文件系统 MCP
            if mcp_config.get("filesystem", {}).get("enabled", False):
                fs_tool = create_filesystem_mcp_tool(
                    name="filesystem_mcp",
                    root_path=mcp_config.get("filesystem", {}).get("root_path")
                )
                self.registry.register(fs_tool, "mcp")

            # 其他 MCP 服务器
            servers = mcp_config.get("servers", {})
            if servers:
                mcp_tool = self.mcp_manager.create_tool("mcp_servers", servers)
                self.registry.register(mcp_tool, "mcp")

        # 连接所有 MCP 服务器
        await self.mcp_manager.connect_all()

        self._initialized = True

    def register_tool(self, tool: Any, category: str = "general") -> None:
        """注册工具"""
        self.registry.register(tool, category)

    def unregister_tool(self, name: str) -> None:
        """注销工具"""
        self.registry.unregister(name)

    def get_tool(self, name: str) -> Optional[Any]:
        """获取工具"""
        return self.registry.get_tool(name)

    def get_tools_by_category(self, category: str) -> List[Any]:
        """按分类获取工具"""
        return self.registry.get_tools_by_category(category)

    def get_all_tools(self) -> List[Any]:
        """获取所有工具"""
        return self.registry.get_all_tools()

    def get_enabled_tools(self) -> List[Any]:
        """获取启用的工具"""
        return self.registry.get_enabled_tools()

    def get_all_function_tools(self) -> List[FunctionTool]:
        """获取所有函数工具"""
        return self.registry.get_all_function_tools()

    def get_mcp_servers(self) -> List[Any]:
        """获取所有 MCP 服务器"""
        mcp_servers = []
        for tool in self.get_tools_by_category("mcp"):
            if hasattr(tool, 'get_mcp_servers'):
                mcp_servers.extend(tool.get_mcp_servers())
        return mcp_servers

    def add_custom_function(self, name: str, func: callable, description: str = "",
                           parameters: Dict[str, Any] = None) -> None:
        """添加自定义函数"""
        custom_tool = self.get_tool("custom")
        if custom_tool and isinstance(custom_tool, CustomFunctionTool):
            custom_tool.register_function(name, func, description, parameters)
        else:
            # 创建新的自定义工具
            custom_tool = create_custom_function_tool("custom", {name: {
                "function": func,
                "description": description,
                "parameters": parameters or {}
            }})
            self.registry.register(custom_tool, "custom")

    def remove_custom_function(self, name: str) -> None:
        """移除自定义函数"""
        custom_tool = self.get_tool("custom")
        if custom_tool and isinstance(custom_tool, CustomFunctionTool):
            custom_tool.unregister_function(name)

    async def cleanup(self) -> None:
        """清理所有工具"""
        await self.mcp_manager.cleanup_all()
        self.registry.cleanup_all()
        self._initialized = False

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized


# 全局工具管理器实例
tool_manager = ToolManager()


async def initialize_tools(config: Dict[str, Any] = None) -> ToolManager:
    """初始化工具系统"""
    await tool_manager.initialize(config)
    return tool_manager


def get_tool_manager() -> ToolManager:
    """获取工具管理器实例"""
    return tool_manager


# 便捷函数
def get_all_function_tools() -> List[FunctionTool]:
    """获取所有函数工具"""
    return tool_manager.get_all_function_tools()


def get_mcp_servers() -> List[Any]:
    """获取所有 MCP 服务器"""
    return tool_manager.get_mcp_servers()