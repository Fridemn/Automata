#!/usr/bin/env python3
"""
系统信息工具扩展
提供系统信息相关的工具函数
"""

import platform

try:
    import psutil  # type: ignore

    HAS_PSUTIL = True
except ImportError:
    psutil = None
    HAS_PSUTIL = False

from agents import FunctionTool, function_tool

from automata.core.tool.base import BaseTool, ToolConfig


class SystemInfoTool(BaseTool):
    """系统信息工具"""

    def __init__(self, config: ToolConfig, task_manager=None):
        super().__init__(config, task_manager)

    def initialize(self) -> None:
        """初始化系统信息工具"""
        self._function_tools.append(get_system_info)

    def get_function_tools(self) -> list[FunctionTool]:
        """获取函数工具列表"""
        return self._function_tools


@function_tool
def get_system_info() -> str:
    """获取系统信息"""
    try:
        system = platform.system()
        version = platform.version()
        architecture = platform.architecture()[0]

        # 尝试获取内存和CPU信息
        if HAS_PSUTIL:
            # 获取内存信息
            memory = psutil.virtual_memory()
            memory_info = f"总内存: {memory.total // (1024**3)}GB, 可用: {memory.available // (1024**3)}GB"

            # 获取CPU信息
            cpu_count = psutil.cpu_count()
            cpu_info = f"CPU核心数: {cpu_count}"
        else:
            memory_info = "内存信息: 需要安装 psutil"
            cpu_info = "CPU信息: 需要安装 psutil"

        return f"系统信息:\n- 操作系统: {system} {version}\n- 架构: {architecture}\n- {cpu_info}\n- {memory_info}"
    except Exception as e:
        return f"获取系统信息失败: {e!s}"


def create_tool(name: str = "system_info", task_manager=None) -> SystemInfoTool:
    """创建系统信息工具"""
    config = ToolConfig(
        name=name,
        description="System information tools",
        config={},
    )

    tool = SystemInfoTool(config, task_manager)
    tool.initialize()
    return tool
