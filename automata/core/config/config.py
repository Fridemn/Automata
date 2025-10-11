#!/usr/bin/env python3
"""
配置管理模块
用于加载和获取配置文件中的各项设置
"""

import json
from typing import Any

from automata.core.utils.path_utils import get_config_file, get_tool_config_file


class UnifiedConfigManager:
    """统一配置管理器"""

    def __init__(self):
        self._core_config = None
        self._tool_config = None

        self.core_config_file = get_config_file()
        self.tool_config_file = get_tool_config_file()

    def _load_config_file(self, config_file: str) -> dict[str, Any]:
        """加载单个配置文件"""
        try:
            with open(config_file, encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            # 如果是工具配置文件不存在，返回空配置
            if config_file == self.tool_config_file:
                return {}
            msg = f"配置文件不存在: {config_file}"
            raise FileNotFoundError(msg)
        except json.JSONDecodeError as e:
            msg = f"配置文件格式错误: {e}"
            raise ValueError(msg)

    def _get_nested_value(self, config: dict[str, Any], keys: list) -> Any:
        """获取嵌套配置值"""
        try:
            value = config
            for key in keys:
                value = value[key]
            # 如果是dict且有'value'键，返回value，否则返回整个dict
            if isinstance(value, dict) and "value" in value:
                return value["value"]
            return value
        except (KeyError, TypeError):
            return None

    def get(self, key: str) -> Any:
        """
        获取配置项，支持点分隔的嵌套键

        优先从核心配置获取，如果不存在则从工具配置获取
        """
        keys = key.split(".")

        # 首先尝试从核心配置获取
        if self._core_config is None:
            self._core_config = self._load_config_file(self.core_config_file)

        core_value = self._get_nested_value(self._core_config, keys)
        if core_value is not None:
            return core_value

        # 如果核心配置中没有找到，尝试从工具配置获取
        if self._tool_config is None:
            self._tool_config = self._load_config_file(self.tool_config_file)

        extension_value = self._get_nested_value(self._tool_config, keys)
        if extension_value is not None:
            return extension_value

        msg = f"配置项 '{key}' 在任何配置文件中都不存在"
        raise KeyError(msg)

    def _extract_nested_values(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        递归提取嵌套配置中的value值

        如果配置是新格式（每个子项都是包含'value'键的dict），则提取所有value；
        否则返回原始配置。
        """
        if isinstance(config, dict):
            result = {}
            for key, value in config.items():
                if isinstance(value, dict):
                    # 检查是否是UI元数据格式（包含'value'键）
                    if "value" in value:
                        result[key] = value["value"]
                    else:
                        # 递归处理嵌套结构
                        result[key] = self._extract_nested_values(value)
                else:
                    result[key] = value
            return result
        return config

    def get_openai_config(self) -> dict[str, Any]:
        """获取OpenAI相关配置"""
        openai_config = self.get("openai")
        return self._extract_nested_values(openai_config)

    def get_agent_config(self) -> dict[str, Any]:
        """获取Agent相关配置"""
        agent_config = self.get("agent")
        return self._extract_nested_values(agent_config)

    def get_vector_db_config(self) -> dict[str, Any]:
        """获取向量数据库相关配置"""
        vector_db_config = self.get("vector_db")
        return self._extract_nested_values(vector_db_config)

    def get_tools_config(self) -> dict[str, Any]:
        """获取工具相关配置"""
        tools_config = self.get("tools")
        return self._extract_nested_values(tools_config)

    def get_mcp_config(self) -> dict[str, Any]:
        """获取MCP相关配置"""
        mcp_config = self.get("mcp")
        return self._extract_nested_values(mcp_config)

    def reload_config(self):
        """重新加载所有配置文件"""
        self._core_config = None
        self._tool_config = None

    def load_config(self) -> dict[str, Any]:
        """加载完整的配置用于前端显示"""
        config = {}

        core_config = self.get_core_config()
        config.update(core_config)

        tool_config = self.get_tool_config()
        config.update(tool_config)

        return config

    def get_core_config(self) -> dict[str, Any]:
        """获取核心配置（用于调试）"""
        if self._core_config is None:
            self._core_config = self._load_config_file(self.core_config_file)
        return self._core_config

    def get_tool_config(self) -> dict[str, Any]:
        """获取工具配置（用于调试）"""
        if self._tool_config is None:
            self._tool_config = self._load_config_file(self.tool_config_file)
        return self._tool_config

    def get_core_sections(self) -> list:
        """获取核心配置的section列表"""
        core_config = self.get_core_config()
        return list(core_config.keys())

    def get_extension_sections(self) -> list:
        """获取工具配置的section列表"""
        tool_config = self.get_tool_config()
        return list(tool_config.keys())


# 全局配置管理器实例
config_manager = UnifiedConfigManager()


# 便捷函数
def get_config(key: str) -> Any:
    """获取配置项的便捷函数"""
    return config_manager.get(key)


def get_openai_config() -> dict[str, Any]:
    """获取OpenAI配置的便捷函数"""
    return config_manager.get_openai_config()


def get_agent_config() -> dict[str, Any]:
    """获取Agent配置的便捷函数"""
    return config_manager.get_agent_config()


def get_vector_db_config() -> dict[str, Any]:
    """获取向量数据库配置的便捷函数"""
    return config_manager.get_vector_db_config()


def get_tools_config() -> dict[str, Any]:
    """获取工具配置的便捷函数"""
    return config_manager.get_tools_config()


def get_mcp_config() -> dict[str, Any]:
    """获取MCP配置的便捷函数"""
    return config_manager.get_mcp_config()


def reload_config():
    """重新加载配置的便捷函数"""
    config_manager.reload_config()
