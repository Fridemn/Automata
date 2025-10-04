#!/usr/bin/env python3
"""
MCP (Model Context Protocol) 工具支持
"""

import asyncio
import os
from typing import Any, Dict, List, Optional, Union
from agents import FunctionTool
from agents.mcp import MCPServer, MCPServerStdio, MCPServerSse, MCPServerStreamableHttp
from .base import BaseTool, ToolConfig


class MCPTool(BaseTool):
    """MCP 工具"""

    def __init__(self, config: ToolConfig):
        super().__init__(config)
        self._servers: Dict[str, MCPServer] = {}
        self._server_configs: Dict[str, Dict[str, Any]] = {}

    def initialize(self) -> None:
        """初始化 MCP 服务器"""
        server_configs = self.config.config.get("servers", {})
        for server_name, server_config in server_configs.items():
            self.add_server(server_name, server_config)

    def add_server(self, name: str, config: Dict[str, Any]) -> None:
        """添加 MCP 服务器"""
        server_type = config.get("type", "stdio")
        server_config = config.get("config", {})

        self._server_configs[name] = config

        # 根据类型创建服务器
        if server_type == "stdio":
            server = MCPServerStdio(
                name=name,
                params=server_config
            )
        elif server_type == "sse":
            server = MCPServerSse(
                name=name,
                params=server_config
            )
        elif server_type == "streamable_http":
            server = MCPServerStreamableHttp(
                name=name,
                params=server_config
            )
        else:
            raise ValueError(f"Unsupported MCP server type: {server_type}")

        self._servers[name] = server

    async def connect_server(self, name: str) -> None:
        """连接 MCP 服务器"""
        if name not in self._servers:
            raise ValueError(f"MCP server '{name}' not found")

        server = self._servers[name]
        if not hasattr(server, '_connected') or not server._connected:
            await server.connect()

    async def connect_all_servers(self) -> None:
        """连接所有 MCP 服务器"""
        tasks = []
        for name, server in self._servers.items():
            if not hasattr(server, '_connected') or not server._connected:
                tasks.append(self.connect_server(name))

        if tasks:
            await asyncio.gather(*tasks)

    def remove_server(self, name: str) -> None:
        """移除 MCP 服务器"""
        if name in self._servers:
            server = self._servers[name]
            asyncio.create_task(server.cleanup())
            del self._servers[name]

        if name in self._server_configs:
            del self._server_configs[name]

    def get_server(self, name: str) -> Optional[MCPServer]:
        """获取 MCP 服务器"""
        return self._servers.get(name)

    def get_servers(self) -> List[MCPServer]:
        """获取所有 MCP 服务器"""
        return list(self._servers.values())

    def get_function_tools(self) -> List[FunctionTool]:
        """获取函数工具列表"""
        # MCP 服务器本身就是工具，不需要额外的函数工具
        return []

    def get_mcp_servers(self) -> List[MCPServer]:
        """获取 MCP 服务器列表（用于 Agent 初始化）"""
        if not self.active:
            return []
        return self.get_servers()

    async def cleanup(self) -> None:
        """清理资源"""
        cleanup_tasks = []
        for server in self._servers.values():
            cleanup_tasks.append(server.cleanup())

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        self._servers.clear()
        self._server_configs.clear()


class MCPManager:
    """MCP 管理器"""

    def __init__(self):
        self._tools: Dict[str, MCPTool] = {}

    def create_tool(self, name: str, servers: Dict[str, Dict[str, Any]] = None) -> MCPTool:
        """创建 MCP 工具"""
        if servers is None:
            servers = {}

        config = ToolConfig(
            name=name,
            description=f"MCP tool: {name}",
            config={"servers": servers}
        )

        tool = MCPTool(config)
        self._tools[name] = tool
        return tool

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """获取 MCP 工具"""
        return self._tools.get(name)

    def remove_tool(self, name: str) -> None:
        """移除 MCP 工具"""
        if name in self._tools:
            tool = self._tools[name]
            asyncio.create_task(tool.cleanup())
            del self._tools[name]

    async def connect_all(self) -> None:
        """连接所有 MCP 工具的服务器"""
        tasks = []
        for tool in self._tools.values():
            tasks.append(tool.connect_all_servers())

        if tasks:
            await asyncio.gather(*tasks)

    async def cleanup_all(self) -> None:
        """清理所有 MCP 工具"""
        cleanup_tasks = []
        for tool in self._tools.values():
            cleanup_tasks.append(tool.cleanup())

        if cleanup_tasks:
            await asyncio.gather(*cleanup_tasks, return_exceptions=True)

        self._tools.clear()


# 便捷函数
def create_filesystem_mcp_tool(name: str = "filesystem", root_path: str = None) -> MCPTool:
    """创建文件系统 MCP 工具"""
    if root_path is None:
        root_path = os.getcwd()

    servers = {
        "filesystem": {
            "type": "stdio",
            "config": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", root_path]
            }
        }
    }

    manager = MCPManager()
    return manager.create_tool(name, servers)