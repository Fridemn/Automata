import os
import sys
from typing import Dict, Any

def _get_project_root():
    from automata.core.utils.path_utils import get_project_root
    return get_project_root()

# 添加项目根目录到 Python 路径
sys.path.insert(0, _get_project_root())

try:
    from agents.models.multi_provider import OpenAIProvider
    from agents.run import RunConfig
    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False

from automata.core.config.config import get_openai_config
from .provider import AbstractProvider, LLMResponse
from .entities import ProviderRequest


class SimpleOpenAIProvider(AbstractProvider):
    """简单的 OpenAI Provider，使用 OpenAIProvider 而不是 ChatCompletionsModel"""

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        super().__init__(provider_config)
        self.provider_settings = provider_settings
        self.api_key = self.provider_config.get("key", [""])[0]
        self.api_base_url = self.provider_config.get("api_base_url", "")

        if AGENTS_AVAILABLE:
            self.model_provider = OpenAIProvider(
                api_key=self.api_key,
                base_url=self.api_base_url,
                use_responses=False
            )
        else:
            self.model_provider = None

    def get_current_key(self) -> str:
        return self.api_key

    def set_key(self, key: str):
        self.api_key = key
        if AGENTS_AVAILABLE:
            self.model_provider = OpenAIProvider(
                api_key=self.api_key,
                base_url=self.api_base_url,
                use_responses=False
            )

    async def get_models(self) -> list[str]:
        """获得支持的模型列表"""
        if not AGENTS_AVAILABLE:
            return ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
        # OpenAI Agents SDK 默认支持多种模型，这里返回常用模型
        return ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]

    async def text_chat(
        self,
        prompt: str,
        session_id: str = None,
        image_urls: list[str] = None,
        contexts: list = None,
        system_prompt: str = None,
        model: str | None = None,
        tools: list[Dict[str, Any]] = None,
        **kwargs,
    ) -> LLMResponse:
        """获得 LLM 的文本对话结果。会使用当前的模型进行对话。"""
        if not AGENTS_AVAILABLE:
            return LLMResponse(
                role="assistant",
                completion_text="OpenAI Agents SDK not available. Please install with: pip install openai-agents"
            )

        # 这里简化实现，返回错误信息，因为这个provider主要用于配置model_provider
        return LLMResponse(
            role="assistant",
            completion_text="This provider is for model configuration only. Use OpenAIAgentProvider for chat."
        )

    async def text_chat_stream(
        self,
        prompt: str,
        session_id: str = None,
        image_urls: list[str] = None,
        contexts: list = None,
        system_prompt: str = None,
        model: str | None = None,
        tools: list[Dict[str, Any]] = None,
        **kwargs,
    ):
        """获得 LLM 的流式文本对话结果。"""
        # 简化实现
        response = await self.text_chat(prompt, session_id, image_urls, contexts, system_prompt, model, tools, **kwargs)
        yield LLMResponse(role="assistant", completion_text=response.completion_text, is_chunk=True)
        yield response

    def get_model_provider(self):
        """获取配置好的 model provider，用于创建 RunConfig"""
        return self.model_provider

    def create_run_config(self):
        """创建运行配置"""
        if not AGENTS_AVAILABLE or not self.model_provider:
            return None
        return RunConfig(model_provider=self.model_provider)


def create_simple_provider_from_config() -> SimpleOpenAIProvider:
    """从配置文件创建简单的 OpenAI Provider"""
    openai_config = get_openai_config()

    api_key = openai_config.get("api_key", "")
    if not api_key:
        raise ValueError("请在config.json中设置openai.api_key")

    provider_config = {
        "id": "simple_openai_provider",
        "type": "openai_simple",
        "key": [api_key],
        "api_base_url": openai_config.get("api_base_url"),
        "model": openai_config.get("model")
    }
    provider_settings = {}

    return SimpleOpenAIProvider(provider_config, provider_settings)