#!/usr/bin/env python3
"""
工具状态管理器
负责工具状态的持久化和恢复
"""

import json
import os
import logging
from typing import Any, Dict, List, Set
from ..utils.path_utils import get_data_dir

logger = logging.getLogger(__name__)


class ToolStateManager:
    """工具状态管理器"""

    def __init__(self, state_file: str = None):
        if state_file is None:
            state_file = os.path.join(get_data_dir(), 'tool_states.json')
        self.state_file = state_file
        self._disabled_tools: Set[str] = set()
        self._builtin_disabled_tools: Set[str] = set()
        self._load_states()

    def _load_states(self) -> None:
        """加载状态"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    states = json.load(f)
                    self._disabled_tools = set(states.get('disabled_tools', []))
                    self._builtin_disabled_tools = set(states.get('builtin_disabled_tools', []))
        except Exception as e:
            logger.error(f"加载工具状态失败: {e}")
            self._disabled_tools = set()
            self._builtin_disabled_tools = set()

    def _save_states(self) -> None:
        """保存状态"""
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            states = {
                'disabled_tools': list(self._disabled_tools),
                'builtin_disabled_tools': list(self._builtin_disabled_tools)
            }
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(states, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"保存工具状态失败: {e}")

    def is_tool_disabled(self, name: str) -> bool:
        """检查工具是否被禁用"""
        return name in self._disabled_tools

    def is_builtin_tool_disabled(self, name: str) -> bool:
        """检查builtin子工具是否被禁用"""
        return name in self._builtin_disabled_tools

    def disable_tool(self, name: str) -> None:
        """禁用工具"""
        self._disabled_tools.add(name)
        self._save_states()

    def enable_tool(self, name: str) -> None:
        """启用工具"""
        self._disabled_tools.discard(name)
        self._save_states()

    def disable_builtin_tool(self, name: str) -> None:
        """禁用builtin子工具"""
        self._builtin_disabled_tools.add(name)
        self._save_states()

    def enable_builtin_tool(self, name: str) -> None:
        """启用builtin子工具"""
        self._builtin_disabled_tools.discard(name)
        self._save_states()

    def get_disabled_tools(self) -> Set[str]:
        """获取被禁用的工具列表"""
        return self._disabled_tools.copy()

    def get_disabled_builtin_tools(self) -> Set[str]:
        """获取被禁用的builtin子工具列表"""
        return self._builtin_disabled_tools.copy()