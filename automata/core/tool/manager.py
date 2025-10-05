#!/usr/bin/env python3
"""
工具管理器
统一管理所有工具的注册、初始化和生命周期
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Optional, Union, TYPE_CHECKING
from agents import FunctionTool
from .base import ToolRegistry, ToolConfig
from .async_task_tool import create_async_task_tool
from .mcp import MCPTool, MCPManager, create_filesystem_mcp_tool
from .extensions import get_extension_loader

if TYPE_CHECKING:
    from ..task_manager import TaskManager


class ToolManager:
    """工具管理器"""

    def __init__(self, data_dir: str = None, task_manager: Optional['TaskManager'] = None):
        self.registry = ToolRegistry()
        self.mcp_manager = MCPManager()
        self.extension_loader = get_extension_loader()
        self.task_manager = task_manager
        self._initialized = False

        # 状态持久化
        if data_dir is None:
            data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        self.state_file = os.path.join(data_dir, 'tool_states.json')
        self._disabled_tools: set = set()
        self._builtin_disabled_tools: set = set()  # builtin子工具的禁用状态

        # 加载之前保存的状态
        self._load_tool_states()

    async def initialize(self, config: Dict[str, Any] = None) -> None:
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
                task_manager=self.task_manager
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
                    task_manager=self.task_manager
                )
                self.registry.register(fs_tool, "mcp")

            # 其他 MCP 服务器
            servers = mcp_config.get("servers", {})
            if servers:
                mcp_tool = self.mcp_manager.create_tool("mcp_servers", servers, self.task_manager)
                self.registry.register(mcp_tool, "mcp")

        # 连接所有 MCP 服务器
        await self.mcp_manager.connect_all()

        # 加载所有扩展
        extensions_config = config.get("extensions", {})
        if extensions_config.get("enabled", True):
            extension_tools = self.extension_loader.load_all_extensions(task_manager=self.task_manager)
            for tool in extension_tools:
                category = "extensions"
                # 尝试从扩展信息中获取类别
                extension_name = tool.name
                if extension_name in self.extension_loader.loaded_extensions:
                    ext_info = self.extension_loader.loaded_extensions[extension_name]
                    category = ext_info.category
                self.registry.register(tool, category)

        # 应用之前保存的工具状态
        self._apply_tool_states()

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
                self._builtin_disabled_tools.discard(subtool_name)
                self._save_tool_states()
                return True
            return False

        # 首先尝试在注册表中启用
        if self.registry.enable_tool(name):
            self._disabled_tools.discard(name)
            self._save_tool_states()
            return True

        # 如果不在注册表中，尝试在扩展中启用
        if self.extension_loader.enable_extension(name):
            self._disabled_tools.discard(name)
            self._save_tool_states()
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
                self._builtin_disabled_tools.add(subtool_name)
                self._save_tool_states()
                return True
            return False

        # 首先尝试在注册表中禁用
        if self.registry.disable_tool(name):
            self._disabled_tools.add(name)
            self._save_tool_states()
            return True

        # 如果不在注册表中，尝试在扩展中禁用
        if self.extension_loader.disable_extension(name):
            self._disabled_tools.add(name)
            self._save_tool_states()
            return True

        return False

    def get_tool_status(self, name: str) -> Optional[Dict[str, Any]]:
        """获取工具状态信息

        Args:
            name: 工具名称

        Returns:
            包含工具状态信息的字典，None表示工具不存在
        """
        # 检查是否是builtin子工具
        if name.startswith("builtin."):
            subtool_name = name.split(".", 1)[1]
            builtin_subtools = self._get_builtin_subtools_status()
            for subtool in builtin_subtools:
                if subtool['name'] == name:
                    return subtool
            return None

        # 首先在注册表中查找
        status = self.registry.get_tool_status(name)
        if status:
            return status

        # 如果不在注册表中，在扩展中查找
        return self.extension_loader.get_extension_status(name)

    def get_all_tools_status(self) -> List[Dict[str, Any]]:
        """获取所有工具的状态信息"""
        status_list = []

        # 获取注册表中的工具状态
        registry_statuses = self.registry.get_all_tools_status()

        for status in registry_statuses:
            if status['name'] == 'builtin':
                # 展开builtin工具的子工具
                builtin_subtools = self._get_builtin_subtools_status()
                status_list.extend(builtin_subtools)
            else:
                status_list.append(status)

        # 添加扩展的状态（避免重复）
        existing_names = {status['name'] for status in status_list}
        for name in self.extension_loader.loaded_tools:
            if name not in existing_names:
                ext_status = self.extension_loader.get_extension_status(name)
                if ext_status:
                    status_list.append(ext_status)

        return status_list

    def _get_builtin_subtools_status(self) -> List[Dict[str, Any]]:
        """获取builtin工具子工具的状态"""
        builtin_tool = self.get_tool("builtin")
        if not builtin_tool:
            return []

        subtools_status = []
        builtin_subtools = {
            "time": "获取当前时间",
            "calculator": "数学计算器",
            "file": "文件操作工具",
            "system": "系统信息工具"
        }

        disabled_tools = self._builtin_disabled_tools

        for subtool_name, description in builtin_subtools.items():
            # 如果disabled_tools包含该工具，则禁用；否则启用
            is_enabled = subtool_name not in disabled_tools
            is_active = builtin_tool.active and is_enabled

            subtools_status.append({
                "name": f"builtin.{subtool_name}",
                "description": description,
                "category": "builtin",
                "version": builtin_tool.config.version if hasattr(builtin_tool.config, 'version') else "1.0.0",
                "enabled": is_enabled,
                "active": is_active,
                "parent": "builtin"
            })

        return subtools_status

    def enable_builtin_tool(self, tool_name: str) -> bool:
        """启用内置工具的特定子工具

        Args:
            tool_name: 子工具名称 (如 "time", "calculator", "file", "system")

        Returns:
            bool: 是否成功启用
        """
        builtin_tool = self.get_tool("builtin")
        if builtin_tool and hasattr(builtin_tool, 'enable_tool'):
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
        if builtin_tool and hasattr(builtin_tool, 'disable_tool'):
            builtin_tool.disable_tool(tool_name)
            return True
        return False

    def get_builtin_tools_status(self) -> List[str]:
        """获取启用的内置子工具列表"""
        all_builtin_subtools = ["time", "calculator", "file", "system"]
        disabled_tools = self._builtin_disabled_tools
        enabled_tools = [tool for tool in all_builtin_subtools if tool not in disabled_tools]
        return enabled_tools

    def _load_tool_states(self) -> None:
        """加载工具状态"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    states = json.load(f)
                    self._disabled_tools = set(states.get('disabled_tools', []))
                    self._builtin_disabled_tools = set(states.get('builtin_disabled_tools', []))
        except Exception as e:
            print(f"加载工具状态失败: {e}")
            self._disabled_tools = set()
            self._builtin_disabled_tools = set()

    def _save_tool_states(self) -> None:
        """保存工具状态"""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            states = {
                'disabled_tools': list(self._disabled_tools),
                'builtin_disabled_tools': list(self._builtin_disabled_tools)
            }
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(states, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"保存工具状态失败: {e}")

    def _apply_tool_states(self) -> None:
        """应用之前保存的工具状态"""
        # 应用普通工具的禁用状态
        for tool_name in self._disabled_tools:
            # 尝试在注册表中禁用
            if not self.registry.disable_tool(tool_name):
                # 如果不在注册表中，尝试在扩展中禁用
                self.extension_loader.disable_extension(tool_name)
        
        # builtin子工具的状态已经通过_disabled_tools在initialize时设置

    async def cleanup(self) -> None:
        """清理所有工具"""
        await self.mcp_manager.cleanup_all()
        self.registry.cleanup_all()
        self._initialized = False

    async def save_and_reload(self) -> None:
        """保存状态并重新加载工具"""
        # 保存当前状态
        self._save_tool_states()
        
        # 重新初始化工具
        await self.cleanup()
        await self.initialize()
        
        # 重新应用保存的状态
        self._apply_tool_states()

    def is_initialized(self) -> bool:
        """检查是否已初始化"""
        return self._initialized


# 全局工具管理器实例
tool_manager = ToolManager()


async def initialize_tools(config: Dict[str, Any] = None, task_manager=None) -> ToolManager:
    """初始化工具系统"""
    tool_manager.task_manager = task_manager
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