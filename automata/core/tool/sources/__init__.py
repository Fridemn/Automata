#!/usr/bin/env python3
"""
源系统
自动加载和管理工具源
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from loguru import logger

from automata.core.tool.base import BaseTool, ToolConfig


class SourceInfo:
    """源信息"""

    def __init__(self, path: str, metadata: dict[str, Any]):
        self.path = path
        self.name = metadata.get("name", "")
        self.version = metadata.get("version", "1.0.0")
        self.desc = metadata.get("desc", "")
        self.author = metadata.get("author", "")
        self.repo = metadata.get("repo")
        self.main_file = "main.py"  # 默认 main.py


class SourceLoader:
    """源加载器"""

    def __init__(self, sources_dir: str):
        self.sources_dir = Path(sources_dir)
        self.loaded_sources: dict[str, SourceInfo] = {}
        self.loaded_tools: dict[str, BaseTool] = {}

    def discover_sources(self) -> list[SourceInfo]:
        """发现所有源"""
        sources = []

        if not self.sources_dir.exists():
            return sources

        for item in self.sources_dir.iterdir():
            if item.is_dir():
                metadata_file = item / "metadata.yaml"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, encoding="utf-8") as f:
                            metadata = yaml.safe_load(f)

                        source = SourceInfo(str(item), metadata)
                        sources.append(source)
                    except Exception as e:
                        logger.warning(f"Failed to load source {item.name}: {e}")

        return sources

    def load_source(
        self,
        source: SourceInfo,
        task_manager=None,
    ) -> BaseTool | None:
        """加载单个源"""
        try:
            # 检查依赖
            if not self._check_dependencies(source):
                logger.warning(f"Source {source.name} dependencies not satisfied")
                return None

            # 导入主模块
            main_file = Path(source.path) / source.main_file
            if not main_file.exists():
                logger.warning(
                    f"Source {source.name} main file not found: {main_file}",
                )
                return None

            # 动态导入模块
            spec = importlib.util.spec_from_file_location(
                f"source_{source.name}",
                main_file,
            )

            if spec is None or spec.loader is None:
                logger.warning(f"Failed to create spec for source {source.name}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[f"source_{source.name}"] = module

            # 执行模块
            spec.loader.exec_module(module)

            # 获取工具类
            if hasattr(module, "create_tool"):
                # 尝试调用create_tool，传递task_manager如果它接受参数
                create_tool_sig = inspect.signature(module.create_tool)
                if len(create_tool_sig.parameters) > 0:
                    tool = module.create_tool(task_manager=task_manager)
                else:
                    tool = module.create_tool()

                if isinstance(tool, BaseTool):
                    # 设置版本信息
                    tool.config.version = source.version
                    self.loaded_tools[source.name] = tool
                    self.loaded_sources[source.name] = source
                    logger.info(
                        f"Loaded source: {source.name}",
                    )
                    return tool
                logger.warning(
                    f"Source {source.name} create_tool() did not return a BaseTool",
                )
            else:
                logger.warning(
                    f"Source {source.name} does not have create_tool() function",
                )

        except Exception as e:
            logger.exception(f"Failed to load source {source.name}: {e}")
            traceback.print_exc()

        return None

    def load_all_sources(self, task_manager=None) -> list[BaseTool]:
        """加载所有源"""
        sources = self.discover_sources()
        loaded_tools = []

        for source in sources:
            tool = self.load_source(source, task_manager)
            if tool:
                loaded_tools.append(tool)

        return loaded_tools

    def enable_source(self, name: str) -> bool:
        """启用源"""
        if name in self.loaded_tools:
            self.loaded_tools[name].enable()
            return True
        return False

    def disable_source(self, name: str) -> bool:
        """禁用源"""
        if name in self.loaded_tools:
            self.loaded_tools[name].disable()
            return True
        return False

    def get_source_status(self, name: str) -> dict[str, Any] | None:
        """获取源状态"""
        if name in self.loaded_tools:
            tool = self.loaded_tools[name]
            source_info = self.loaded_sources.get(name)
            return {
                "name": tool.name,
                "desc": source_info.desc if source_info else tool.description,
                "enabled": tool.enabled,
                "active": tool.active,
                "version": source_info.version if source_info else "unknown",
                "author": source_info.author if source_info else "unknown",
            }
        return None

    def unload_source(self, name: str) -> None:
        """卸载源"""
        if name in self.loaded_tools:
            tool = self.loaded_tools[name]
            tool.cleanup()
            del self.loaded_tools[name]

        if name in self.loaded_sources:
            del self.loaded_sources[name]

        # 从 sys.modules 中移除
        module_name = f"source_{name}"
        if module_name in sys.modules:
            del sys.modules[module_name]

    def get_loaded_sources(self) -> dict[str, SourceInfo]:
        """获取已加载的源"""
        return self.loaded_sources.copy()

    def get_loaded_tools(self) -> dict[str, BaseTool]:
        """获取已加载的工具"""
        return self.loaded_tools.copy()

    def _check_dependencies(self, source: SourceInfo) -> bool:
        """检查依赖"""
        # 这里可以实现依赖检查逻辑
        # 目前简单返回 True
        return True

    def reload_source(self, name: str) -> BaseTool | None:
        """重新加载源"""
        self.unload_source(name)
        if name in self.loaded_sources:
            source = self.loaded_sources[name]
            return self.load_source(source)
        return None


# 全局源加载器实例
source_loader = SourceLoader(os.path.dirname(__file__))


def get_tool_loader() -> SourceLoader:
    """获取源加载器实例"""
    return source_loader


def load_all_sources() -> list[BaseTool]:
    """加载所有源"""
    return source_loader.load_all_sources()


def create_source_template(
    name: str,
    desc: str,
    author: str = "Automata",
) -> None:
    """创建源模板"""
    source_dir = source_loader.sources_dir / name

    if source_dir.exists():
        logger.warning(f"Source {name} already exists")
        return

    source_dir.mkdir(parents=True)

    # 创建 metadata.yaml
    metadata = {
        "name": name,
        "version": "1.0.0",
        "desc": desc,
        "author": author,
    }

    with open(source_dir / "metadata.yaml", "w", encoding="utf-8") as f:
        yaml.dump(metadata, f, allow_unicode=True, default_flow_style=False)

    # 创建 main.py 模板
    main_content = f'''#!/usr/bin/env python3
"""
{name} 源
{desc}
"""

from automata.core.tool.base import BaseTool, ToolConfig
from agents import function_tool


class {name.replace("_", " ").title().replace(" ", "")}Tool(BaseTool):
    """{name} 工具"""

    def __init__(self, config: ToolConfig):
        super().__init__(config)

    def initialize(self):
        """初始化工具"""
        # 在这里定义你的工具函数
        # 使用 @function_tool 装饰器

        @function_tool
        def example_function(param: str) -> str:
            """示例函数"""
            return f"处理参数: {{param}}"

        # 添加到工具列表
        self._function_tools = [example_function]

    def get_function_tools(self):
        """获取函数工具列表"""
        return self._function_tools


def create_tool() -> {name.replace("_", " ").title().replace(" ", "")}Tool:
    """创建工具实例"""
    config = ToolConfig(
        name="{name}",
        description="{desc}",
        category="general"
    )
    return {name.replace("_", " ").title().replace(" ", "")}Tool(config)
'''

    with open(source_dir / "main.py", "w", encoding="utf-8") as f:
        f.write(main_content)
