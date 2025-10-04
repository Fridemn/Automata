#!/usr/bin/env python3
"""
example_tool 扩展
An example tool extension
"""

from automata.core.tool.base import BaseTool, ToolConfig
from agents import function_tool


class ExampleToolTool(BaseTool):
    """example_tool 工具"""

    def __init__(self, config: ToolConfig):
        super().__init__(config)

    def initialize(self):
        """初始化工具"""
        # 在这里定义你的工具函数
        # 使用 @function_tool 装饰器

        @function_tool
        def example_function(param: str) -> str:
            """示例函数"""
            return f"处理参数: {param}"

        # 添加到工具列表
        self._function_tools = [example_function]

    def get_function_tools(self):
        """获取函数工具列表"""
        return self._function_tools


def create_tool() -> ExampleToolTool:
    """创建工具实例"""
    config = ToolConfig(
        name="example_tool",
        description="An example tool extension",
        enabled=True
    )
    return ExampleToolTool(config)
