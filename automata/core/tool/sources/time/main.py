#!/usr/bin/env python3
"""
时间工具扩展
提供时间相关的工具函数
"""

import datetime

from agents import FunctionTool, function_tool

from automata.core.tool.base import BaseTool, ToolConfig


class TimeTool(BaseTool):
    """时间工具"""

    def __init__(self, config: ToolConfig, task_manager=None):
        super().__init__(config, task_manager)

    def initialize(self) -> None:
        """初始化时间工具"""
        self._function_tools.append(get_current_time)

    def get_function_tools(self) -> list[FunctionTool]:
        """获取函数工具列表"""
        return self._function_tools


@function_tool
def get_current_time() -> str:
    """获取当前时间"""
    now = datetime.datetime.now()
    return f"当前时间是: {now.strftime('%Y-%m-%d %H:%M:%S')}"


def create_tool(name: str = "time", task_manager=None) -> TimeTool:
    """创建时间工具"""
    config = ToolConfig(
        name=name,
        description="Time utility tools",
        config={},
    )

    tool = TimeTool(config, task_manager)
    tool.initialize()
    return tool
