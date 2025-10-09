#!/usr/bin/env python3
"""
工具管理器
统一管理所有工具的注册、初始化和生命周期
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .async_task_tool import create_async_task_tool
from .base import ToolRegistry
from .extension_manager import ExtensionManager
from .mcp import create_filesystem_mcp_tool
from .state_manager import ToolStateManager

if TYPE_CHECKING:
    from agents import FunctionTool

    from automata.core.tasks.task_manager import TaskManager


class ToolManager:
    """工具管理器"""

    def __init__(
        self,
        data_dir: str | None = None,
        task_manager: TaskManager | None = None,
    ):
        self.registry = ToolRegistry()
        self.state_manager = ToolStateManager()
        self.extension_manager = ExtensionManager()
        self.task_manager = task_manager
        self._initialized = False

    async def initialize(self, config: dict[str, Any] | None = None) -> None:
        """初始化工具管理器"""
        if self._initialized:
            return

        if config is None:
            config = {}

        # 初始化异步任务工具
        async_task_config = config.get("async_task", {})
        if async_task_config.get("enabled", True):
            async_task_tool = create_async_task_tool(
                name="async_task",
                task_manager=self.task_manager,
            )
            self.registry.register(async_task_tool, "async_task")

        # 初始化 MCP 工具
        mcp_config = config.get("mcp", {})
        if mcp_config.get("enabled", False):
            # 文件系统 MCP
            if mcp_config.get("filesystem", {}).get("enabled", False):
                fs_tool = create_filesystem_mcp_tool(
                    name="filesystem_mcp",
                    root_path=mcp_config.get("filesystem", {}).get("root_path"),
                    task_manager=self.task_manager,
                )
                self.registry.register(fs_tool, "mcp")

        # 连接所有MCP工具的服务器
        await self._connect_mcp_servers()

        # 加载所有扩展
        extensions_config = config.get("extensions", {})
        if extensions_config.get("enabled", True):
            extension_tools = self.extension_manager.load_all_extensions(
                self.task_manager,
            )
            for tool in extension_tools:
                category = "extensions"
                # 尝试从扩展信息中获取类别
                extension_name = tool.name
                if (
                    extension_name
                    in self.extension_manager.extension_loader.loaded_extensions
                ):
                    ext_info = (
                        self.extension_manager.extension_loader.loaded_extensions[
                            extension_name
                        ]
                    )
                    category = ext_info.category
                self.registry.register(tool, category)

        # 应用之前保存的工具状态
        self._apply_tool_states()

        self._initialized = True

    async def _connect_mcp_servers(self) -> None:
        """连接所有MCP服务器"""
        mcp_tools = self.registry.get_tools_by_category("mcp")
        for tool in mcp_tools:
            if hasattr(tool, "connect_all_servers"):
                await tool.connect_all_servers()

    def register_tool(self, tool: Any, category: str = "general") -> None:
        """注册工具"""
        self.registry.register(tool, category)

    def unregister_tool(self, name: str) -> None:
        """注销工具"""
        self.registry.unregister(name)

    def get_tool(self, name: str) -> Any | None:
        """获取工具"""
        return self.registry.get_tool(name)

    def get_tools_by_category(self, category: str) -> list[Any]:
        """按分类获取工具"""
        return self.registry.get_tools_by_category(category)

    def get_all_tools(self) -> list[Any]:
        """获取所有工具"""
        return self.registry.get_all_tools()

    def get_enabled_tools(self) -> list[Any]:
        """获取启用的工具"""
        return self.registry.get_enabled_tools()

    def get_all_function_tools(self) -> list[FunctionTool]:
        """获取所有函数工具"""
        return self.registry.get_all_function_tools()

    def get_mcp_servers(self) -> list[Any]:
        """获取所有 MCP 服务器"""
        mcp_servers = []
        for tool in self.get_tools_by_category("mcp"):
            if hasattr(tool, "get_mcp_servers"):
                mcp_servers.extend(tool.get_mcp_servers())
        return mcp_servers

    def enable_tool(self, name: str) -> bool:
        """启用指定工具

        Args:
            name: 工具名称

        Returns:
            bool: 是否成功启用
        """
        # 检查是否是builtin子工具
        if name.startswith("builtin."):
            subtool_name = name.split(".", 1)[1]
            if self.enable_builtin_tool(subtool_name):
                self.state_manager.enable_builtin_tool(subtool_name)
                return True
            return False

        # 首先尝试在注册表中启用
        if self.registry.enable_tool(name):
            self.state_manager.enable_tool(name)
            return True

        # 如果不在注册表中，尝试在扩展中启用
        if self.extension_manager.enable_extension(name):
            self.state_manager.enable_tool(name)
            return True

        return False

    def disable_tool(self, name: str) -> bool:
        """禁用指定工具

        Args:
            name: 工具名称

        Returns:
            bool: 是否成功禁用
        """
        # 检查是否是builtin子工具
        if name.startswith("builtin."):
            subtool_name = name.split(".", 1)[1]
            if self.disable_builtin_tool(subtool_name):
                self.state_manager.disable_builtin_tool(subtool_name)
                return True
            return False

        # 首先尝试在注册表中禁用
        if self.registry.disable_tool(name):
            self.state_manager.disable_tool(name)
            return True

        # 如果不在注册表中，尝试在扩展中禁用
        if self.extension_manager.disable_extension(name):
            self.state_manager.disable_tool(name)
            return True

        return False

    def get_tool_status(self, name: str) -> dict[str, Any] | None:
        """获取工具状态信息

        Args:
            name: 工具名称

        Returns:
            包含工具状态信息的字典，None表示工具不存在
        """
        # 检查是否是builtin子工具
        if name.startswith("builtin."):
            name.split(".", 1)[1]
            builtin_subtools = self._get_builtin_subtools_status()
            for subtool in builtin_subtools:
                if subtool["name"] == name:
                    return subtool
            return None

        # 首先在注册表中查找
        status = self.registry.get_tool_status(name)
        if status:
            return status

        # 如果不在注册表中，在扩展中查找
        return self.extension_manager.get_extension_status(name)

    def get_all_tools_status(self) -> list[dict[str, Any]]:
        """获取所有工具的状态信息"""
        status_list = []

        # 获取注册表中的工具状态
        registry_statuses = self.registry.get_all_tools_status()

        for status in registry_statuses:
            if status["name"] == "builtin":
                # 展开builtin工具的子工具
                builtin_subtools = self._get_builtin_subtools_status()
                status_list.extend(builtin_subtools)
            else:
                status_list.append(status)

        # 添加扩展的状态（避免重复）
        existing_names = {status["name"] for status in status_list}
        for tool in self.extension_manager.get_loaded_tools():
            if tool.name not in existing_names:
                ext_status = self.extension_manager.get_extension_status(tool.name)
                if ext_status:
                    status_list.append(ext_status)

        return status_list

    def _get_builtin_subtools_status(self) -> list[dict[str, Any]]:
        """获取builtin工具子工具的状态"""
        builtin_tool = self.get_tool("builtin")
        if not builtin_tool:
            return []

        subtools_status = []
        builtin_subtools = {
            "time": "获取当前时间",
            "calculator": "数学计算器",
            "file": "文件操作工具",
            "system": "系统信息工具",
        }

        disabled_tools = self.state_manager.get_disabled_builtin_tools()

        for subtool_name, description in builtin_subtools.items():
            # 如果disabled_tools包含该工具，则禁用；否则启用
            is_enabled = subtool_name not in disabled_tools
            is_active = builtin_tool.active and is_enabled

            subtools_status.append(
                {
                    "name": f"builtin.{subtool_name}",
                    "description": description,
                    "category": "builtin",
                    "version": builtin_tool.config.version
                    if hasattr(builtin_tool.config, "version")
                    else "1.0.0",
                    "enabled": is_enabled,
                    "active": is_active,
                    "parent": "builtin",
                },
            )

        return subtools_status

    def get_builtin_tools_status(self) -> list[str]:
        """获取启用的内置子工具列表"""
        all_builtin_subtools = ["time", "calculator", "file", "system"]
        disabled_tools = self.state_manager.get_disabled_builtin_tools()
        return [tool for tool in all_builtin_subtools if tool not in disabled_tools]

    def enable_builtin_tool(self, tool_name: str) -> bool:
        """启用内置工具的特定子工具

        Args:
            tool_name: 子工具名称 (如 "time", "calculator", "file", "system")

        Returns:
            bool: 是否成功启用
        """
        builtin_tool = self.get_tool("builtin")
        if builtin_tool and hasattr(builtin_tool, "enable_tool"):
            builtin_tool.enable_tool(tool_name)
            return True
        return False

    def disable_builtin_tool(self, tool_name: str) -> bool:
        """禁用内置工具的特定子工具

        Args:
            tool_name: 子工具名称 (如 "time", "calculator", "file", "system")

        Returns:
            bool: 是否成功禁用
        """
        builtin_tool = self.get_tool("builtin")
        if builtin_tool and hasattr(builtin_tool, "disable_tool"):
            builtin_tool.disable_tool(tool_name)
            return True
        return False

    def _apply_tool_states(self) -> None:
        """应用之前保存的工具状态"""
        # 应用普通工具的禁用状态
        for tool_name in self.state_manager.get_disabled_tools():
            # 尝试在注册表中禁用
            if not self.registry.disable_tool(tool_name):
                # 如果不在注册表中，尝试在扩展中禁用
                self.extension_manager.disable_extension(tool_name)

        # 应用builtin子工具的禁用状态
        for subtool_name in self.state_manager.get_disabled_builtin_tools():
            self.disable_builtin_tool(subtool_name)

    async def cleanup(self) -> None:
        """清理所有工具"""
        # MCP工具现在通过注册表管理，所以不需要单独的MCPManager
        self.registry.cleanup_all()
        self._initialized = False

    async def save_and_reload(self) -> None:
        """保存状态并重新加载工具"""
        # 重新初始化工具
        await self.cleanup()
        await self.initialize()

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized


# 全局工具管理器实例
tool_manager = ToolManager()


async def initialize_tools(
    config: dict[str, Any] | None = None,
    task_manager=None,
) -> ToolManager:
    """初始化工具系统"""
    tool_manager.task_manager = task_manager
    await tool_manager.initialize(config)
    return tool_manager


def get_tool_manager() -> ToolManager:
    """获取工具管理器实例"""
    return tool_manager


# 便捷函数
def get_all_function_tools() -> list[FunctionTool]:
    """获取所有函数工具"""
    return tool_manager.get_all_function_tools()


def get_mcp_servers() -> list[Any]:
    """获取所有 MCP 服务器"""
    return tool_manager.get_mcp_servers()
