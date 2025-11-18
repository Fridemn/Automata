#!/usr/bin/env python3
"""
MCP (Model Context Protocol) 工具支持
"""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING, Any

import httpx
from agents.mcp import MCPServer, MCPServerSse, MCPServerStdio, MCPServerStreamableHttp
from loguru import logger
from mcp.types import TextContent, Tool

from .base import BaseTool, ToolConfig

if TYPE_CHECKING:
    from agents import FunctionTool


class MCPError(Exception):
    """MCP 相关错误"""


class MCPConnectionError(MCPError):
    """MCP 连接错误"""


class MCPToolError(MCPError):
    """MCP 工具错误"""


class ToolResult:
    """工具结果"""

    def __init__(self, content, structured_content=None):
        self.content = content
        self.structured_content = structured_content


class HttpMCPServer:
    """简单的 HTTP MCP 服务器客户端"""

    def __init__(self, name: str, url: str, api_key: str | None = None):
        self.name = name
        self.base_url = url.rstrip("/")
        self.mcp_url = f"{self.base_url}/mcp/"
        self.api_key = api_key
        self._connected = False
        self.use_structured_content = False  # 添加缺失属性

    async def connect(self):
        """连接到 MCP 服务器"""

        def _raise_connection_error(msg):
            raise MCPConnectionError(msg)

        logger.info(f"Connecting to MCP server at {self.base_url}")
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # 简单健康检查
                logger.debug(f"Checking health at {self.base_url}/health")
                response = await client.get(f"{self.base_url}/health")
                logger.debug(f"Health check status: {response.status_code}")
                if response.status_code == 200:
                    self._connected = True
                    logger.info("Connected successfully")
                    return
            msg = f"Health check failed: {response.status_code}"
            _raise_connection_error(msg)
        except httpx.RequestError as e:
            logger.exception(f"Request error: {e}")
            msg = f"Connection failed: {e}"
            raise MCPConnectionError(msg) from e
        except Exception as e:
            logger.exception(f"Other error: {e}")
            msg = f"Connection failed: {e}"
            raise MCPConnectionError(msg) from e

    async def list_tools(self, run_context=None, agent=None):
        """列出可用工具"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            response = await client.get(f"{self.base_url}/tools", headers=headers)
            if response.status_code != 200:
                msg = f"Failed to list tools: {response.status_code} - {response.text}"
                raise MCPToolError(msg)

            data = response.json()
            tools_data = data.get("tools", [])

            # 转换回Tool对象
            tools = []
            for tool_data in tools_data:
                tools.append(
                    Tool(
                        name=tool_data["name"],
                        description=tool_data["description"],
                        inputSchema=tool_data["inputSchema"],
                    ),
                )
            return tools

    async def call_tool(self, name: str, arguments: dict, run_context=None, agent=None):
        """调用工具"""
        # 调用对应的工具端点
        async with httpx.AsyncClient(timeout=30.0) as client:
            headers = {}
            if self.api_key:
                headers["X-API-Key"] = self.api_key
            response = await client.post(
                f"{self.base_url}/tools/{name}",
                json=arguments,
                headers=headers,
            )
            if response.status_code != 200:
                msg = f"Tool call failed: {response.status_code} - {response.text}"
                raise MCPToolError(msg)

            data = response.json()
            # Handle the response format from Automata MCP server
            if data.get("success"):
                content = data.get("data", {}).get("content", [])
            else:
                error_msg = data.get("error", "Unknown error")
                raise MCPToolError("Tool call failed: " + error_msg)

            text_contents = [
                TextContent(type=item["type"], text=item["text"]) for item in content
            ]
            return ToolResult(content=text_contents)

    async def cleanup(self):
        """清理连接"""
        self._connected = False


class MCPTool(BaseTool):
    """MCP 工具"""

    def __init__(self, config: ToolConfig, task_manager=None):
        super().__init__(config, task_manager)
        self._servers: dict[str, MCPServer] = {}
        self._server_configs: dict[str, dict[str, Any]] = {}

    def initialize(self) -> None:
        """初始化 MCP 服务器"""
        logger.info("Initializing MCP servers")
        # 检查是否有统一服务器配置
        server_url = self.config.config.get("server_url")
        logger.debug(f"Server URL: {server_url}")
        if server_url:
            # 创建统一 MCP 服务器
            logger.info("Adding unified MCP server")
            api_key = self.config.config.get("api_key")
            self.add_server(
                "unified_mcp",
                {
                    "type": "http",
                    "config": {"url": server_url, "api_key": api_key},
                },
            )
        else:
            # 旧方式：从 servers 配置
            server_configs = self.config.config.get("servers", {})
            for server_name, server_config in server_configs.items():
                self.add_server(server_name, server_config)

    def add_server(self, name: str, config: dict[str, Any]) -> None:
        """添加 MCP 服务器"""
        server_type = config.get("type", "stdio")
        server_config = config.get("config", {})

        self._server_configs[name] = config

        # 根据类型创建服务器
        if server_type == "stdio":
            server = MCPServerStdio(
                name=name,
                params=server_config,
            )
        elif server_type == "sse":
            server = MCPServerSse(
                name=name,
                params=server_config,
            )
        elif server_type == "streamable_http":
            server = MCPServerStreamableHttp(
                name=name,
                params=server_config,
            )
        elif server_type == "http":
            api_key = server_config.get("api_key")
            server = HttpMCPServer(
                name=name,
                url=server_config["url"],
                api_key=api_key,
            )
        else:
            msg = f"Unsupported MCP server type: {server_type}"
            raise ValueError(msg)

        self._servers[name] = server

    async def connect_server(self, name: str) -> None:
        """连接 MCP 服务器"""
        if name not in self._servers:
            msg = f"MCP server '{name}' not found"
            raise ValueError(msg)

        server = self._servers[name]
        if not hasattr(server, "_connected") or not server._connected:
            await server.connect()

    async def connect_all_servers(self) -> None:
        """连接所有 MCP 服务器"""
        tasks = []
        for name, server in self._servers.items():
            if not hasattr(server, "_connected") or not server._connected:
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

    def get_server(self, name: str) -> MCPServer | None:
        """获取 MCP 服务器"""
        return self._servers.get(name)

    def get_servers(self) -> list[MCPServer]:
        """获取所有 MCP 服务器"""
        return list(self._servers.values())

    def get_function_tools(self) -> list[FunctionTool]:
        """获取函数工具列表"""
        # MCP 服务器本身就是工具，不需要额外的函数工具
        return []

    def get_mcp_servers(self) -> list[MCPServer]:
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
        self._tools: dict[str, MCPTool] = {}

    def create_tool(
        self,
        name: str,
        servers: dict[str, dict[str, Any]] | None = None,
        task_manager=None,
    ) -> MCPTool:
        """创建 MCP 工具"""
        if servers is None:
            servers = {}

        config = ToolConfig(
            name=name,
            description=f"MCP tool: {name}",
            config={"servers": servers},
        )

        tool = MCPTool(config, task_manager)
        self._tools[name] = tool
        return tool

    def get_tool(self, name: str) -> MCPTool | None:
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
def create_filesystem_mcp_tool(
    name: str = "filesystem",
    root_path: str | None = None,
    task_manager=None,
) -> MCPTool:
    """创建文件系统 MCP 工具"""
    if root_path is None:
        root_path = os.getcwd()

    servers = {
        "filesystem": {
            "type": "stdio",
            "config": {
                "command": "npx",
                "args": ["-y", "@modelcontextprotocol/server-filesystem", root_path],
            },
        },
    }

    config = ToolConfig(
        name=name,
        description=f"Filesystem MCP tool for {root_path}",
        config={"servers": servers},
    )

    return MCPTool(config, task_manager)


def create_unified_mcp_tool(
    server_url: str,
    name: str = "unified_mcp",
    task_manager=None,
    api_key: str | None = None,
) -> MCPTool:
    """创建统一 MCP 工具"""
    config = ToolConfig(
        name=name,
        description=f"Unified MCP client for {server_url}",
        config={"server_url": server_url, "api_key": api_key},
    )

    return MCPTool(config, task_manager)
