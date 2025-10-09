#!/usr/bin/env python3
"""
扩展系统
自动加载和管理工具扩展
"""

from __future__ import annotations

import importlib.util
import inspect
import json
import logging
import os
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional

from automata.core.tool.base import BaseTool, ToolConfig

logger = logging.getLogger(__name__)


class ExtensionInfo:
    """扩展信息"""

    def __init__(self, path: str, package_info: dict[str, Any]):
        self.path = path
        self.name = package_info.get("name", "")
        self.version = package_info.get("version", "1.0.0")
        self.description = package_info.get("description", "")
        self.category = package_info.get("category", "general")
        self.author = package_info.get("author", "")
        self.dependencies = package_info.get("dependencies", [])
        self.enabled = package_info.get("enabled", True)
        self.main_file = package_info.get("main", "main.py")


class ExtensionLoader:
    """扩展加载器"""

    def __init__(self, extensions_dir: str):
        self.extensions_dir = Path(extensions_dir)
        self.loaded_extensions: dict[str, ExtensionInfo] = {}
        self.loaded_tools: dict[str, BaseTool] = {}

    def discover_extensions(self) -> list[ExtensionInfo]:
        """发现所有扩展"""
        extensions = []

        if not self.extensions_dir.exists():
            return extensions

        for item in self.extensions_dir.iterdir():
            if item.is_dir():
                package_file = item / "package.json"
                if package_file.exists():
                    try:
                        with open(package_file, encoding="utf-8") as f:
                            package_info = json.load(f)

                        extension = ExtensionInfo(str(item), package_info)
                        extensions.append(extension)
                    except Exception as e:
                        logger.warning(f"Failed to load extension {item.name}: {e}")

        return extensions

    def load_extension(
        self,
        extension: ExtensionInfo,
        task_manager=None,
    ) -> BaseTool | None:
        """加载单个扩展"""
        try:
            # 检查依赖
            if not self._check_dependencies(extension):
                logger.warning(f"Extension {extension.name} dependencies not satisfied")
                return None

            # 导入主模块
            main_file = Path(extension.path) / extension.main_file
            if not main_file.exists():
                logger.warning(
                    f"Extension {extension.name} main file not found: {main_file}",
                )
                return None

            # 动态导入模块
            spec = importlib.util.spec_from_file_location(
                f"extension_{extension.name}",
                main_file,
            )

            if spec is None or spec.loader is None:
                logger.warning(f"Failed to create spec for extension {extension.name}")
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[f"extension_{extension.name}"] = module

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
                    tool.config.version = extension.version
                    self.loaded_tools[extension.name] = tool
                    self.loaded_extensions[extension.name] = extension
                    logger.info(
                        f"Loaded extension: {extension.name} ({extension.category})",
                    )
                    return tool
                logger.warning(
                    f"Extension {extension.name} create_tool() did not return a BaseTool",
                )
            else:
                logger.warning(
                    f"Extension {extension.name} does not have create_tool() function",
                )

        except Exception as e:
            logger.exception(f"Failed to load extension {extension.name}: {e}")
            traceback.print_exc()

        return None

    def load_all_extensions(self, task_manager=None) -> list[BaseTool]:
        """加载所有扩展"""
        extensions = self.discover_extensions()
        loaded_tools = []

        for extension in extensions:
            if extension.enabled:
                tool = self.load_extension(extension, task_manager)
                if tool:
                    loaded_tools.append(tool)
            else:
                logger.info(f"Extension {extension.name} is disabled")

        return loaded_tools

    def enable_extension(self, name: str) -> bool:
        """启用扩展"""
        if name in self.loaded_tools:
            self.loaded_tools[name].enable()
            return True
        return False

    def disable_extension(self, name: str) -> bool:
        """禁用扩展"""
        if name in self.loaded_tools:
            self.loaded_tools[name].disable()
            return True
        return False

    def get_extension_status(self, name: str) -> dict[str, Any] | None:
        """获取扩展状态"""
        if name in self.loaded_tools:
            tool = self.loaded_tools[name]
            ext_info = self.loaded_extensions.get(name)
            return {
                "name": tool.name,
                "description": tool.description,
                "enabled": tool.enabled,
                "active": tool.active,
                "category": ext_info.category if ext_info else "unknown",
                "version": ext_info.version if ext_info else "unknown",
            }
        return None

    def unload_extension(self, name: str) -> None:
        """卸载扩展"""
        if name in self.loaded_tools:
            tool = self.loaded_tools[name]
            tool.cleanup()
            del self.loaded_tools[name]

        if name in self.loaded_extensions:
            del self.loaded_extensions[name]

        # 从 sys.modules 中移除
        module_name = f"extension_{name}"
        if module_name in sys.modules:
            del sys.modules[module_name]

    def get_loaded_extensions(self) -> dict[str, ExtensionInfo]:
        """获取已加载的扩展"""
        return self.loaded_extensions.copy()

    def get_loaded_tools(self) -> dict[str, BaseTool]:
        """获取已加载的工具"""
        return self.loaded_tools.copy()

    def _check_dependencies(self, extension: ExtensionInfo) -> bool:
        """检查依赖"""
        # 这里可以实现依赖检查逻辑
        # 目前简单返回 True
        return True

    def reload_extension(self, name: str) -> BaseTool | None:
        """重新加载扩展"""
        self.unload_extension(name)
        if name in self.loaded_extensions:
            extension = self.loaded_extensions[name]
            return self.load_extension(extension)
        return None


# 全局扩展加载器实例
extension_loader = ExtensionLoader(os.path.dirname(__file__))


def get_extension_loader() -> ExtensionLoader:
    """获取扩展加载器实例"""
    return extension_loader


def load_all_extensions() -> list[BaseTool]:
    """加载所有扩展"""
    return extension_loader.load_all_extensions()


def create_extension_template(
    name: str,
    description: str,
    category: str = "general",
) -> None:
    """创建扩展模板"""
    extension_dir = extension_loader.extensions_dir / name

    if extension_dir.exists():
        logger.warning(f"Extension {name} already exists")
        return

    extension_dir.mkdir(parents=True)

    # 创建 package.json
    package_info = {
        "name": name,
        "version": "1.0.0",
        "description": description,
        "category": category,
        "author": "Automata",
        "main": "main.py",
        "enabled": True,
        "dependencies": [],
    }

    with open(extension_dir / "package.json", "w", encoding="utf-8") as f:
        json.dump(package_info, f, indent=2, ensure_ascii=False)

    # 创建 main.py 模板
    main_content = f'''#!/usr/bin/env python3
"""
{name} 扩展
{description}
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
        description="{description}",
        category="{category}"
    )
    return {name.replace("_", " ").title().replace(" ", "")}Tool(config)
'''

    with open(extension_dir / "main.py", "w", encoding="utf-8") as f:
        f.write(main_content)
