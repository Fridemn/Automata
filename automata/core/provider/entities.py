from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class ProviderType(enum.Enum):
    CHAT_COMPLETION = "chat_completion"


@dataclass
class ProviderRequest:
    prompt: str
    """提示词"""
    session_id: str = ""
    """会话 ID"""
    image_urls: list[str] = field(default_factory=list)
    """图片 URL 列表"""
    contexts: list[dict] = field(default_factory=list)
    """上下文。格式与 openai 的上下文格式一致"""
    system_prompt: str = ""
    """系统提示词"""
    model: str | None = None
    """模型名称，为 None 时使用提供商的默认模型"""
    tools: list[dict[str, Any]] = field(default_factory=list)
    """工具列表，格式与 openai-agent-sdk 的工具格式一致"""
