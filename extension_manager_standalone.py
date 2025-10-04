#!/usr/bin/env python3
"""
扩展管理器 - 独立版本
用于管理工具扩展的命令行工具
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Any, Optional


class ExtensionInfo:
    """扩展信息"""

    def __init__(self, path: str, package_info: Dict[str, Any]):
        self.path = path
        self.name = package_info.get("name", "")
        self.version = package_info.get("version", "1.0.0")
        self.description = package_info.get("description", "")
        self.category = package_info.get("category", "general")
        self.author = package_info.get("author", "")
        self.dependencies = package_info.get("dependencies", [])
        self.enabled = package_info.get("enabled", True)
        self.main_file = package_info.get("main", "main.py")


class SimpleExtensionLoader:
    """简化的扩展加载器"""

    def __init__(self, extensions_dir: str):
        self.extensions_dir = Path(extensions_dir)

    def discover_extensions(self) -> List[ExtensionInfo]:
        """发现所有扩展"""
        extensions = []

        if not self.extensions_dir.exists():
            return extensions

        for item in self.extensions_dir.iterdir():
            if item.is_dir():
                package_file = item / "package.json"
                if package_file.exists():
                    try:
                        with open(package_file, 'r', encoding='utf-8') as f:
                            package_info = json.load(f)

                        extension = ExtensionInfo(str(item), package_info)
                        extensions.append(extension)
                    except Exception as e:
                        print(f"⚠️ Failed to load extension {item.name}: {e}")

        return extensions


def create_extension_template(name: str, description: str, category: str = "general") -> None:
    """创建扩展模板"""
    # 获取 extensions 目录路径
    current_dir = Path(__file__).parent
    extensions_dir = current_dir / "automata" / "core" / "tool" / "extensions"

    extension_dir = extensions_dir / name

    if extension_dir.exists():
        print(f"Extension {name} already exists")
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
        "dependencies": []
    }

    with open(extension_dir / "package.json", 'w', encoding='utf-8') as f:
        json.dump(package_info, f, indent=2, ensure_ascii=False)

    # 创建 main.py 模板
    main_content = f'''#!/usr/bin/env python3
"""
{name} 扩展
{description}
"""

from automata.core.tool.base import BaseTool, ToolConfig
from agents import function_tool


class {name.replace('_', ' ').title().replace(' ', '')}Tool(BaseTool):
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


def create_tool() -> {name.replace('_', ' ').title().replace(' ', '')}Tool:
    """创建工具实例"""
    config = ToolConfig(
        name="{name}",
        description="{description}",
        enabled=True
    )
    return {name.replace('_', ' ').title().replace(' ', '')}Tool(config)
'''

    with open(extension_dir / "main.py", 'w', encoding='utf-8') as f:
        f.write(main_content)

    print(f"✅ Created extension template: {name}")
    print(f"📁 Location: {extension_dir}")


def list_extensions():
    """列出所有扩展"""
    print("📋 Available Extensions:")
    current_dir = Path(__file__).parent
    extensions_dir = current_dir / "automata" / "core" / "tool" / "extensions"
    loader = SimpleExtensionLoader(str(extensions_dir))
    discovered = loader.discover_extensions()

    if not discovered:
        print("  No extensions found")
        return

    for ext in discovered:
        status = "✅ Enabled" if ext.enabled else "⏭️ Disabled"
        print(f"  - {ext.name}: {ext.description}")
        print(f"    Category: {ext.category} | Status: {status} | Version: {ext.version}")


def disable_extension(name: str):
    """禁用扩展"""
    current_dir = Path(__file__).parent
    extensions_dir = current_dir / "automata" / "core" / "tool" / "extensions"
    package_file = extensions_dir / name / "package.json"

    if not package_file.exists():
        print(f"❌ Extension '{name}' not found")
        return

    try:
        with open(package_file, 'r', encoding='utf-8') as f:
            package_info = json.load(f)

        package_info["enabled"] = False

        with open(package_file, 'w', encoding='utf-8') as f:
            json.dump(package_info, f, indent=2, ensure_ascii=False)

        print(f"✅ Extension '{name}' disabled")
    except Exception as e:
        print(f"❌ Failed to disable extension: {e}")


def enable_extension(name: str):
    """启用扩展"""
    current_dir = Path(__file__).parent
    extensions_dir = current_dir / "automata" / "core" / "tool" / "extensions"
    package_file = extensions_dir / name / "package.json"

    if not package_file.exists():
        print(f"❌ Extension '{name}' not found")
        return

    try:
        with open(package_file, 'r', encoding='utf-8') as f:
            package_info = json.load(f)

        package_info["enabled"] = True

        with open(package_file, 'w', encoding='utf-8') as f:
            json.dump(package_info, f, indent=2, ensure_ascii=False)

        print(f"✅ Extension '{name}' enabled")
    except Exception as e:
        print(f"❌ Failed to enable extension: {e}")


def show_usage():
    """显示使用说明"""
    print("🔧 Automata Extension Manager")
    print("")
    print("Usage:")
    print("  python extension_manager.py list")
    print("  python extension_manager.py create <name> <description> [category]")
    print("  python extension_manager.py enable <name>")
    print("  python extension_manager.py disable <name>")
    print("")
    print("Examples:")
    print("  python extension_manager.py list")
    print("  python extension_manager.py create my_tool 'My custom tool' utility")
    print("  python extension_manager.py enable my_tool")
    print("  python extension_manager.py disable my_tool")


def main():
    if len(sys.argv) < 2:
        show_usage()
        return

    command = sys.argv[1]

    if command == "list":
        list_extensions()
    elif command == "create":
        if len(sys.argv) < 4:
            print("❌ Usage: python extension_manager.py create <name> <description> [category]")
            return
        name = sys.argv[2]
        description = sys.argv[3]
        category = sys.argv[4] if len(sys.argv) > 4 else "general"
        create_extension_template(name, description, category)
    elif command == "enable":
        if len(sys.argv) < 3:
            print("❌ Usage: python extension_manager.py enable <name>")
            return
        name = sys.argv[2]
        enable_extension(name)
    elif command == "disable":
        if len(sys.argv) < 3:
            print("❌ Usage: python extension_manager.py disable <name>")
            return
        name = sys.argv[2]
        disable_extension(name)
    else:
        print(f"❌ Unknown command: {command}")
        show_usage()


if __name__ == "__main__":
    main()