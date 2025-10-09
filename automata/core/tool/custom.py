#!/usr/bin/env python3
"""
自定义函数工具
支持动态注册和调用自定义函数
"""

from __future__ import annotations

from typing import Any, Callable

from agents import FunctionTool, function_tool

from .base import BaseTool, ToolConfig


class CustomFunctionTool(BaseTool):
    """自定义函数工具"""

    def __init__(self, config: ToolConfig, task_manager=None):
        super().__init__(config, task_manager)
        self._functions: dict[str, Callable] = {}

    def initialize(self) -> None:
        """初始化工具"""
        # 从配置中加载预定义函数
        predefined_functions = self.config.config.get("functions", {})
        for name, func_info in predefined_functions.items():
            if isinstance(func_info, dict):
                self.register_function(
                    name=name,
                    func=func_info.get("function"),
                    description=func_info.get("description", ""),
                    parameters=func_info.get("parameters", {}),
                )

    def register_function(
        self,
        name: str,
        func: Callable,
        description: str = "",
        parameters: dict[str, Any] | None = None,
    ) -> None:
        """注册自定义函数"""
        if parameters is None:
            parameters = {}

        # 创建函数工具
        function_tool_decorator = function_tool(description=description)

        # 如果有参数信息，添加到函数的注解中
        if parameters:
            # 这里可以扩展参数处理逻辑
            pass

        # 应用装饰器
        decorated_func = function_tool_decorator(func)

        # 存储函数
        self._functions[name] = decorated_func

        # 重新生成函数工具列表
        self._generate_function_tools()

    def unregister_function(self, name: str) -> None:
        """注销自定义函数"""
        if name in self._functions:
            del self._functions[name]
            self._generate_function_tools()

    def call_function(self, name: str, *args, **kwargs) -> Any:
        """调用自定义函数"""
        if name not in self._functions:
            msg = f"Function '{name}' not found"
            raise ValueError(msg)

        func = self._functions[name]
        return func(*args, **kwargs)

    def get_registered_functions(self) -> list[str]:
        """获取已注册的函数列表"""
        return list(self._functions.keys())

    def _generate_function_tools(self) -> None:
        """生成函数工具列表"""
        self._function_tools = list(self._functions.values())

    def get_function_tools(self) -> list[FunctionTool]:
        """获取函数工具列表"""
        if not self.active:
            return []
        return self._function_tools

    def cleanup(self) -> None:
        """清理资源"""
        self._functions.clear()
        self._function_tools.clear()


# 便捷函数
def create_custom_function_tool(
    name: str,
    functions: dict[str, dict[str, Any]] | None = None,
    task_manager=None,
) -> CustomFunctionTool:
    """创建自定义函数工具"""
    if functions is None:
        functions = {}

    config = ToolConfig(
        name=name,
        description=f"Custom function tool: {name}",
        config={"functions": functions},
    )

    tool = CustomFunctionTool(config, task_manager)
    tool.initialize()
    return tool
