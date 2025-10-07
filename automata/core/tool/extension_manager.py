#!/usr/bin/env python3
"""
扩展管理器
负责扩展的加载和管理
"""

from typing import Dict, List, Any, Optional, TYPE_CHECKING
from .extensions import get_extension_loader
from .base import BaseTool

if TYPE_CHECKING:
    from ..tasks.task_manager import TaskManager


class ExtensionManager:
    """扩展管理器"""

    def __init__(self):
        self.extension_loader = get_extension_loader()
        self.loaded_tools: Dict[str, BaseTool] = {}

    def load_all_extensions(self, task_manager: Optional['TaskManager'] = None) -> List[BaseTool]:
        """加载所有扩展"""
        extensions = self.extension_loader.load_all_extensions(task_manager)
        for tool in extensions:
            self.loaded_tools[tool.name] = tool
        return extensions

    def enable_extension(self, name: str) -> bool:
        """启用扩展"""
        if name in self.loaded_tools:
            self.loaded_tools[name].enable()
            return True
        return self.extension_loader.enable_extension(name)

    def disable_extension(self, name: str) -> bool:
        """禁用扩展"""
        if name in self.loaded_tools:
            self.loaded_tools[name].disable()
            return True
        return self.extension_loader.disable_extension(name)

    def get_extension_status(self, name: str) -> Optional[Dict[str, Any]]:
        """获取扩展状态"""
        if name in self.loaded_tools:
            tool = self.loaded_tools[name]
            ext_info = self.extension_loader.loaded_extensions.get(name)
            return {
                "name": tool.name,
                "description": tool.description,
                "enabled": tool.enabled,
                "active": tool.active,
                "category": ext_info.category if ext_info else "unknown",
                "version": ext_info.version if ext_info else "unknown"
            }
        return self.extension_loader.get_extension_status(name)

    def get_loaded_tools(self) -> List[BaseTool]:
        """获取已加载的工具"""
        return list(self.loaded_tools.values())