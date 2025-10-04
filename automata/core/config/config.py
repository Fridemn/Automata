#!/usr/bin/env python3
"""
配置管理模块
用于加载和获取配置文件中的各项设置
"""

import json
import os
from typing import Dict, Any

class ConfigManager:
    """配置管理器类"""

    def __init__(self, config_file: str = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径，如果为None则使用默认路径
        """
        if config_file is None:
            # 默认配置文件路径为data目录下的config.json
            self.config_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'config.json')
        else:
            self.config_file = config_file

        self._config = None

    def load_config(self) -> Dict[str, Any]:
        """
        加载配置文件

        Returns:
            配置字典
        """
        if self._config is None:
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except FileNotFoundError:
                raise FileNotFoundError(f"配置文件不存在: {self.config_file}")
            except json.JSONDecodeError as e:
                raise ValueError(f"配置文件格式错误: {e}")

        return self._config

    def get(self, key: str) -> Any:
        """
        获取配置项

        Args:
            key: 配置键，支持点分隔的嵌套键，如 'openai.api_key'

        Returns:
            配置值

        Raises:
            KeyError: 如果配置项不存在
        """
        config = self.load_config()
        keys = key.split('.')

        try:
            value = config
            for k in keys:
                value = value[k]
            # 如果是dict且有'value'键，返回value，否则返回整个dict
            if isinstance(value, dict) and 'value' in value:
                return value['value']
            return value
        except (KeyError, TypeError) as e:
            raise KeyError(f"配置项 '{key}' 不存在于配置文件中") from e

    def get_openai_config(self) -> Dict[str, Any]:
        """获取OpenAI相关配置"""
        openai_config = self.get('openai')
        # 如果是新格式，提取value
        if isinstance(openai_config, dict) and isinstance(list(openai_config.values())[0], dict) and 'value' in list(openai_config.values())[0]:
            return {k: v['value'] for k, v in openai_config.items()}
        return openai_config

    def get_agent_config(self) -> Dict[str, Any]:
        """获取Agent相关配置"""
        agent_config = self.get('agent')
        # 如果是新格式，提取value
        if isinstance(agent_config, dict) and isinstance(list(agent_config.values())[0], dict) and 'value' in list(agent_config.values())[0]:
            return {k: v['value'] for k, v in agent_config.items()}
        return agent_config

    def reload_config(self):
        """重新加载配置文件"""
        self._config = None
        self.load_config()

# 全局配置管理器实例
config_manager = ConfigManager()

# 便捷函数
def get_config(key: str) -> Any:
    """获取配置项的便捷函数"""
    return config_manager.get(key)

def get_openai_config() -> Dict[str, Any]:
    """获取OpenAI配置的便捷函数"""
    return config_manager.get_openai_config()

def get_agent_config() -> Dict[str, Any]:
    """获取Agent配置的便捷函数"""
    return config_manager.get_agent_config()

def reload_config():
    """重新加载配置的便捷函数"""
    config_manager.reload_config()