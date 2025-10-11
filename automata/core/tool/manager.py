#!/usr/bin/env python3
"""
工具管理器
统一管理所有工具的注册、初始化和生命周期
"""

from __future__ import annotations

import json
import logging
import os
from typing import TYPE_CHECKING, Any

from automata.core.utils.path_utils import get_data_dir

from .base import ToolRegistry
from .mcp import create_filesystem_mcp_tool
from .sources import get_tool_loader

if TYPE_CHECKING:
    from agents import FunctionTool

    from automata.core.tasks.task_manager import TaskManager

    from .base import BaseTool


logger = logging.getLogger(__name__)


class ToolStateManager:
    """工具状态管理器"""

    def __init__(self, state_file: str | None = None):
        if state_file is None:
            state_file = os.path.join(get_data_dir(), "tool_states.json")
        self.state_file = state_file
        self._disabled_tools: set[str] = set()
        self._load_states()

    def _load_states(self) -> None:
        """加载状态"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, encoding="utf-8") as f:
                    states = json.load(f)
                    self._disabled_tools = set(states.get("disabled_tools", []))
        except Exception as e:
            logger.exception(f"加载工具状态失败: {e}")
            self._disabled_tools = set()

    def _save_states(self) -> None:
        """保存状态"""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            states = {
                "disabled_tools": list(self._disabled_tools),
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(states, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.exception(f"保存工具状态失败: {e}")

    def is_tool_disabled(self, name: str) -> bool:
        """检查工具是否被禁用"""
        return name in self._disabled_tools

    def disable_tool(self, name: str) -> None:
        """禁用工具"""
        self._disabled_tools.add(name)
        self._save_states()

    def enable_tool(self, name: str) -> None:
        """启用工具"""
        self._disabled_tools.discard(name)
        self._save_states()

    def get_disabled_tools(self) -> set[str]:
        """获取被禁用的工具列表"""
        return self._disabled_tools.copy()


class SourceManager:
    """源管理器"""

    def __init__(self):
        self.tool_loader = get_tool_loader()
        self.loaded_tools: dict[str, BaseTool] = {}

    def load_all_sources(
        self,
        task_manager: TaskManager | None = None,
    ) -> list[BaseTool]:
        """加载所有源"""
        sources = self.tool_loader.load_all_sources(task_manager)
        for tool in sources:
            self.loaded_tools[tool.name] = tool
        return sources

    def enable_source(self, name: str) -> bool:
        """启用源"""
        if name in self.loaded_tools:
            self.loaded_tools[name].enable()
            return True
        return self.tool_loader.enable_source(name)

    def disable_source(self, name: str) -> bool:
        """禁用源"""
        if name in self.loaded_tools:
            self.loaded_tools[name].disable()
            return True
        return self.tool_loader.disable_source(name)

    def get_source_status(self, name: str) -> dict[str, Any] | None:
        """获取源状态"""
        if name in self.loaded_tools:
            tool = self.loaded_tools[name]
            source_info = self.tool_loader.loaded_sources.get(name)
            return {
                "name": tool.name,
                "desc": source_info.desc if source_info else tool.description,
                "enabled": tool.enabled,
                "active": tool.active,
                "version": source_info.version if source_info else "unknown",
                "author": source_info.author if source_info else "unknown",
            }
        return self.tool_loader.get_source_status(name)

    def get_loaded_tools(self) -> list[BaseTool]:
        """获取已加载的工具"""
        return list(self.loaded_tools.values())


class ToolManager:
    """工具管理器"""

    def __init__(
        self,
        data_dir: str | None = None,
        task_manager: TaskManager | None = None,
    ):
        self.registry = ToolRegistry()
        self.state_manager = ToolStateManager()
        self.source_manager = SourceManager()
        self.task_manager = task_manager
        self._initialized = False
        self.sources_loaded = False
        self.config = None

    async def initialize(self, config: dict[str, Any] | None = None) -> None:
        """初始化工具管理器"""
        if self._initialized:
            return

        self.config = config or {}

        # 初始化 MCP 工具
        mcp_config = self.config.get("mcp", {})
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
        self._lazy_load_sources()
        return self.registry.get_enabled_tools()

    def _lazy_load_sources(self) -> None:
        """懒加载sources工具"""
        if not self.sources_loaded and self.config:
            sources_config = self.config.get("sources", {})
            if sources_config.get("enabled", True):
                source_tools = self.source_manager.load_all_sources(
                    self.task_manager,
                )
                for tool in source_tools:
                    category = "sources"
                    self.registry.register(tool, category)
                self.sources_loaded = True
                # 应用工具状态
                self._apply_tool_states()

    def get_all_function_tools(self) -> list[FunctionTool]:
        """获取所有函数工具"""
        self._lazy_load_sources()
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
        self._lazy_load_sources()
        # 首先尝试在注册表中启用
        if self.registry.enable_tool(name):
            self.state_manager.enable_tool(name)
            return True

        # 如果不在注册表中，尝试在源中启用
        if self.source_manager.enable_source(name):
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
        self._lazy_load_sources()
        # 首先尝试在注册表中禁用
        if self.registry.disable_tool(name):
            self.state_manager.disable_tool(name)
            return True

        # 如果不在注册表中，尝试在源中禁用
        if self.source_manager.disable_source(name):
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
        self._lazy_load_sources()
        # 首先在注册表中查找
        status = self.registry.get_tool_status(name)
        if status:
            return status

        # 如果不在注册表中，在源中查找
        return self.source_manager.get_source_status(name)

    def get_all_tools_status(self) -> list[dict[str, Any]]:
        """获取所有工具的状态信息"""
        self._lazy_load_sources()

        status_list = []

        # 获取注册表中的工具状态
        registry_statuses = self.registry.get_all_tools_status()
        status_list.extend(registry_statuses)

        # 添加源的状态（避免重复）
        existing_names = {status["name"] for status in status_list}
        for tool in self.source_manager.get_loaded_tools():
            if tool.name not in existing_names:
                source_status = self.source_manager.get_source_status(tool.name)
                if source_status:
                    status_list.append(source_status)

        return status_list

    def _apply_tool_states(self) -> None:
        # 应用普通工具的禁用状态
        for tool_name in self.state_manager.get_disabled_tools():
            # 尝试在注册表中禁用
            if not self.registry.disable_tool(tool_name):
                # 如果不在注册表中，尝试在源中禁用
                self.source_manager.disable_source(tool_name)

    async def cleanup(self) -> None:
        """清理所有工具"""
        # MCP工具现在通过注册表管理，所以不需要单独的MCPManager
        self.registry.cleanup_all()
        self._initialized = False
        self.sources_loaded = False

    async def save_and_reload(self) -> None:
        """保存状态并重新加载工具"""
        # 重新初始化工具
        await self.cleanup()
        await self.initialize(self.config)

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
