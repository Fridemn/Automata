#!/usr/bin/env python3
"""
calculator 扩展
Simple calculator tool
"""

from __future__ import annotations

import math

from agents import function_tool

from automata.core.tool.base import BaseTool, ToolConfig


class CalculatorTool(BaseTool):
    """calculator 工具"""

    def __init__(self, config: ToolConfig):
        super().__init__(config)

    def initialize(self):
        """初始化工具"""
        # 在这里定义你的工具函数
        # 使用 @function_tool 装饰器

        @function_tool
        def add(a: float, b: float) -> int | float:
            """两个数相加"""
            return a + b

        @function_tool
        def subtract(a: float, b: float) -> int | float:
            """两个数相减"""
            return a - b

        @function_tool
        def multiply(a: float, b: float) -> int | float:
            """两个数相乘"""
            return a * b

        @function_tool
        def divide(a: float, b: float) -> int | float:
            """两个数相除"""
            if b == 0:
                msg = "除数不能为零"
                raise ValueError(msg)
            return a / b

        @function_tool
        def power(base: float, exponent: float) -> int | float:
            """计算幂运算"""
            return base**exponent

        @function_tool
        def square_root(x: float) -> float:
            """计算平方根"""
            if x < 0:
                msg = "不能计算负数的平方根"
                raise ValueError(msg)
            return math.sqrt(x)

        @function_tool
        def factorial(n: int) -> int:
            """计算阶乘"""
            if n < 0:
                msg = "不能计算负数的阶乘"
                raise ValueError(msg)
            if not isinstance(n, int):
                msg = "阶乘只能计算整数"
                raise ValueError(msg)
            return math.factorial(n)

        @function_tool
        def sin(angle: float) -> float:
            """计算正弦值（角度制）"""
            return math.sin(math.radians(angle))

        @function_tool
        def cos(angle: float) -> float:
            """计算余弦值（角度制）"""
            return math.cos(math.radians(angle))

        @function_tool
        def tan(angle: float) -> float:
            """计算正切值（角度制）"""
            return math.tan(math.radians(angle))

        # 添加到工具列表
        self._function_tools = [
            add,
            subtract,
            multiply,
            divide,
            power,
            square_root,
            factorial,
            sin,
            cos,
            tan,
        ]

    def get_function_tools(self):
        """获取函数工具列表"""
        return self._function_tools


def create_tool() -> CalculatorTool:
    """创建工具实例"""
    config = ToolConfig(
        name="calculator",
        description="Simple calculator tool",
        enabled=True,
    )
    return CalculatorTool(config)
