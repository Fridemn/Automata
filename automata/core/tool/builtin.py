#!/usr/bin/env python3
"""
内置工具
提供常用的基础工具
"""

import os
import datetime
from typing import Annotated, List
from agents import function_tool, FunctionTool
from .base import BaseTool, ToolConfig


class BuiltinTools(BaseTool):
    """内置工具集合"""

    def __init__(self, config: ToolConfig):
        super().__init__(config)
        self._tools_enabled = config.config.get("enabled_tools", [])

    def initialize(self) -> None:
        """初始化内置工具"""
        # 根据配置启用相应的工具
        if "time" in self._tools_enabled or not self._tools_enabled:
            self._function_tools.append(get_current_time)

        if "calculator" in self._tools_enabled or not self._tools_enabled:
            self._function_tools.append(calculate)

        if "file" in self._tools_enabled or not self._tools_enabled:
            self._function_tools.append(read_file_content)
            self._function_tools.append(list_directory)

        if "system" in self._tools_enabled or not self._tools_enabled:
            self._function_tools.append(get_system_info)

    def get_function_tools(self) -> List[FunctionTool]:
        """获取函数工具列表"""
        return self._function_tools

    def enable_tool(self, tool_name: str) -> None:
        """启用工具"""
        if tool_name not in self._tools_enabled:
            self._tools_enabled.append(tool_name)
            self._update_tools()

    def disable_tool(self, tool_name: str) -> None:
        """禁用工具"""
        if tool_name in self._tools_enabled:
            self._tools_enabled.remove(tool_name)
            self._update_tools()

    def _update_tools(self) -> None:
        """更新工具列表"""
        self._function_tools.clear()
        self.initialize()


# 内置工具函数
@function_tool
def get_current_time() -> str:
    """获取当前时间"""
    now = datetime.datetime.now()
    return f"当前时间是: {now.strftime('%Y-%m-%d %H:%M:%S')}"


@function_tool
def calculate(expression: Annotated[str, "要计算的数学表达式，例如 '2 + 3 * 4'"]) -> str:
    """计算数学表达式"""
    try:
        # 使用eval进行计算，但要小心安全
        result = eval(expression, {"__builtins__": {}})
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算错误: {str(e)}"


@function_tool
def read_file_content(file_path: Annotated[str, "要读取的文件路径"]) -> str:
    """读取文件内容"""
    try:
        if not os.path.exists(file_path):
            return f"文件不存在: {file_path}"

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 限制内容长度
        if len(content) > 10000:
            content = content[:10000] + "\n... (内容过长，已截断)"

        return f"文件 {file_path} 的内容:\n{content}"
    except Exception as e:
        return f"读取文件错误: {str(e)}"


@function_tool
def list_directory(dir_path: Annotated[str, "要列出的目录路径"]) -> str:
    """列出目录内容"""
    try:
        if not os.path.exists(dir_path):
            return f"目录不存在: {dir_path}"

        if not os.path.isdir(dir_path):
            return f"路径不是目录: {dir_path}"

        items = os.listdir(dir_path)
        files = [item for item in items if os.path.isfile(os.path.join(dir_path, item))]
        dirs = [item for item in items if os.path.isdir(os.path.join(dir_path, item))]

        result = f"目录 {dir_path} 的内容:\n"
        if dirs:
            result += f"子目录: {', '.join(dirs)}\n"
        if files:
            result += f"文件: {', '.join(files)}\n"

        return result
    except Exception as e:
        return f"列出目录错误: {str(e)}"


@function_tool
def get_system_info() -> str:
    """获取系统信息"""
    import platform

    try:
        system = platform.system()
        version = platform.version()
        architecture = platform.architecture()[0]

        # 尝试获取内存和CPU信息
        try:
            import psutil  # type: ignore
            # 获取内存信息
            memory = psutil.virtual_memory()
            memory_info = f"总内存: {memory.total // (1024**3)}GB, 可用: {memory.available // (1024**3)}GB"

            # 获取CPU信息
            cpu_count = psutil.cpu_count()
            cpu_info = f"CPU核心数: {cpu_count}"
        except ImportError:
            memory_info = "内存信息: 需要安装 psutil"
            cpu_info = "CPU信息: 需要安装 psutil"

        return f"系统信息:\n- 操作系统: {system} {version}\n- 架构: {architecture}\n- {cpu_info}\n- {memory_info}"
    except Exception as e:
        return f"获取系统信息失败: {str(e)}"


# 默认工具列表
DEFAULT_TOOLS = [
    get_current_time,
    calculate,
    read_file_content,
    list_directory,
    get_system_info,
]


def create_builtin_tools(name: str = "builtin", enabled_tools: List[str] = None) -> BuiltinTools:
    """创建内置工具"""
    if enabled_tools is None:
        enabled_tools = []  # 空列表表示启用所有工具

    config = ToolConfig(
        name=name,
        description="Built-in utility tools",
        config={"enabled_tools": enabled_tools}
    )

    tools = BuiltinTools(config)
    tools.initialize()
    return tools