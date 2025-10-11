#!/usr/bin/env python3
"""
源管理器
负责源的加载和管理
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .sources import get_extension_loader

if TYPE_CHECKING:
    from automata.core.tasks.task_manager import TaskManager

    from .base import BaseTool


class SourceManager:
    """源管理器"""

    def __init__(self):
        self.extension_loader = get_extension_loader()
        self.loaded_tools: dict[str, BaseTool] = {}

    def load_all_sources(
        self,
        task_manager: TaskManager | None = None,
    ) -> list[BaseTool]:
        """加载所有源"""
        sources = self.extension_loader.load_all_sources(task_manager)
        for tool in sources:
            self.loaded_tools[tool.name] = tool
        return sources

    def enable_source(self, name: str) -> bool:
        """启用源"""
        if name in self.loaded_tools:
            self.loaded_tools[name].enable()
            return True
        return self.extension_loader.enable_source(name)

    def disable_source(self, name: str) -> bool:
        """禁用源"""
        if name in self.loaded_tools:
            self.loaded_tools[name].disable()
            return True
        return self.extension_loader.disable_source(name)

    def get_source_status(self, name: str) -> dict[str, Any] | None:
        """获取源状态"""
        if name in self.loaded_tools:
            tool = self.loaded_tools[name]
            source_info = self.extension_loader.loaded_sources.get(name)
            return {
                "name": tool.name,
                "desc": source_info.desc if source_info else tool.description,
                "enabled": tool.enabled,
                "active": tool.active,
                "version": source_info.version if source_info else "unknown",
                "author": source_info.author if source_info else "unknown",
            }
        return self.extension_loader.get_source_status(name)

    def get_loaded_tools(self) -> list[BaseTool]:
        """获取已加载的工具"""
        return list(self.loaded_tools.values())
