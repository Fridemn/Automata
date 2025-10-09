#!/usr/bin/env python3
"""
file_ops 扩展
File operations extension
"""

from pathlib import Path

from agents import function_tool

from automata.core.tool.base import BaseTool, ToolConfig


class FileOpsTool(BaseTool):
    """file_ops 工具"""

    def __init__(self, config: ToolConfig):
        super().__init__(config)

    def initialize(self):
        """初始化工具"""
        # 在这里定义你的工具函数
        # 使用 @function_tool 装饰器

        @function_tool
        def list_directory(path: str) -> str:
            """列出目录内容"""
            try:
                p = Path(path)
                if not p.exists():
                    return f"路径不存在: {path}"

                if not p.is_dir():
                    return f"路径不是目录: {path}"

                items = []
                for item in p.iterdir():
                    item_type = "dir" if item.is_dir() else "file"
                    items.append(f"{item_type}: {item.name}")

                return "\n".join(items) if items else "目录为空"
            except Exception as e:
                return f"列出目录失败: {e}"

        @function_tool
        def read_file_content(file_path: str, max_lines: int = 50) -> str:
            """读取文件内容"""
            try:
                p = Path(file_path)
                if not p.exists():
                    return f"文件不存在: {file_path}"

                if not p.is_file():
                    return f"路径不是文件: {file_path}"

                with open(p, encoding="utf-8") as f:
                    lines = f.readlines()

                content = "".join(lines[:max_lines])
                if len(lines) > max_lines:
                    content += f"\n... (显示前 {max_lines} 行，共 {len(lines)} 行)"

                return content
            except Exception as e:
                return f"读取文件失败: {e}"

        @function_tool
        def get_file_info(file_path: str) -> str:
            """获取文件信息"""
            try:
                p = Path(file_path)
                if not p.exists():
                    return f"文件不存在: {file_path}"

                stat = p.stat()
                info = {
                    "name": p.name,
                    "path": str(p.absolute()),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "is_file": p.is_file(),
                    "is_dir": p.is_dir(),
                }

                return "\n".join(f"{k}: {v}" for k, v in info.items())
            except Exception as e:
                return f"获取文件信息失败: {e}"

        # 添加到工具列表
        self._function_tools = [list_directory, read_file_content, get_file_info]

    def get_function_tools(self):
        """获取函数工具列表"""
        return self._function_tools


def create_tool() -> FileOpsTool:
    """创建工具实例"""
    config = ToolConfig(
        name="file_ops",
        description="File operations extension",
        enabled=True,
    )
    return FileOpsTool(config)
