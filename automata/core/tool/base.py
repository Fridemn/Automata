#!/usr/bin/env python3
"""
基础工具类和接口
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass
from agents import FunctionTool


@dataclass
class ToolConfig:
    """工具配置"""
    name: str
    description: str
    enabled: bool = True
    config: Dict[str, Any] = None

    def __post_init__(self):
        if self.config is None:
            self.config = {}


class BaseTool(ABC):
    """工具基类"""

    def __init__(self, config: ToolConfig):
        self.config = config
        self._function_tools: List[FunctionTool] = []

    @property
    def name(self) -> str:
        return self.config.name

    @property
    def description(self) -> str:
        return self.config.description

    @property
    def enabled(self) -> bool:
        return self.config.enabled

    @abstractmethod
    def initialize(self) -> None:
        """初始化工具"""
        pass

    @abstractmethod
    def get_function_tools(self) -> List[FunctionTool]:
        """获取函数工具列表"""
        return self._function_tools

    def cleanup(self) -> None:
        """清理资源"""
        pass


class ToolRegistry:
    """工具注册表"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._categories: Dict[str, List[str]] = {}

    def register(self, tool: BaseTool, category: str = "general") -> None:
        """注册工具"""
        # 初始化工具
        tool.initialize()
        self._tools[tool.name] = tool
        if category not in self._categories:
            self._categories[category] = []
        self._categories[category].append(tool.name)

    def unregister(self, name: str) -> None:
        """注销工具"""
        if name in self._tools:
            tool = self._tools[name]
            tool.cleanup()
            del self._tools[name]

            # 从分类中移除
            for category, tools in self._categories.items():
                if name in tools:
                    tools.remove(name)
                    break

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(name)

    def get_tools_by_category(self, category: str) -> List[BaseTool]:
        """按分类获取工具"""
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]

    def get_all_tools(self) -> List[BaseTool]:
        """获取所有工具"""
        return list(self._tools.values())

    def get_enabled_tools(self) -> List[BaseTool]:
        """获取启用的工具"""
        return [tool for tool in self._tools.values() if tool.enabled]

    def get_all_function_tools(self) -> List[FunctionTool]:
        """获取所有函数工具"""
        function_tools = []
        for tool in self.get_enabled_tools():
            function_tools.extend(tool.get_function_tools())
        return function_tools

    def cleanup_all(self) -> None:
        """清理所有工具"""
        for tool in self._tools.values():
            tool.cleanup()
        self._tools.clear()
        self._categories.clear()