from __future__ import annotations

import sys
from typing import Any, List

from automata.core.utils.path_utils import get_project_root


def _get_project_root():
    return get_project_root()


# 添加项目根目录到 Python 路径
sys.path.insert(0, _get_project_root())

try:
    from agents import Agent, Runner
    from agents.models.multi_provider import OpenAIProvider
    from agents.run import RunConfig

    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False

from automata.core.config.config import get_openai_config

from ..provider import AbstractProvider, LLMResponse


class OpenAISourceProvider(AbstractProvider):
    """OpenAI Source Provider，使用 OpenAI Agents SDK"""

    def __init__(self, provider_config: dict, provider_settings: dict) -> None:
        super().__init__(provider_config)
        self.provider_settings = provider_settings
        self.api_key = self.provider_config.get("key", [""])[0]
        self.api_base_url = self.provider_config.get("api_base_url", "")

        if AGENTS_AVAILABLE:
            self.model_provider = OpenAIProvider(
                api_key=self.api_key,
                base_url=self.api_base_url,
                use_responses=False,
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
                use_responses=False,
            )

    async def get_models(self) -> list[str]:
        """获得支持的模型列表"""
        if not AGENTS_AVAILABLE:
            return []
        return []

    async def text_chat(
        self,
        prompt: str,
        session_id: str | None = None,
        image_urls: list[str] | None = None,
        contexts: list | None = None,
        system_prompt: str | None = None,
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ) -> LLMResponse:
        """获得 LLM 的文本对话结果。会使用当前的模型进行对话。"""
        if not AGENTS_AVAILABLE:
            return LLMResponse(
                role="assistant",
                completion_text="OpenAI Agents SDK not available. Please install with: pip install openai-agents",
            )

        if not model:
            msg = "Model must be specified"
            raise ValueError(msg)

        if not system_prompt:
            msg = "System prompt must be specified"
            raise ValueError(msg)

        # 创建临时agent，因为没有默认配置
        temp_model_provider = OpenAIProvider(
            api_key=self.api_key,
            base_url=self.api_base_url,
            use_responses=False,
        )
        temp_agent = Agent(
            name="AutomataAssistant",
            instructions=system_prompt,
            model=model,
            tools=tools or [],
        )
        temp_run_config = RunConfig(model_provider=temp_model_provider)
        result = await Runner.run(temp_agent, prompt, run_config=temp_run_config)

        return LLMResponse(
            role="assistant",
            completion_text=str(result.final_output),
        )

    async def text_chat_stream(
        self,
        prompt: str,
        session_id: str | None = None,
        image_urls: list[str] | None = None,
        contexts: list | None = None,
        system_prompt: str | None = None,
        model: str | None = None,
        tools: list[dict[str, Any]] | None = None,
        **kwargs,
    ):
        """获得 LLM 的流式文本对话结果。会使用当前的模型进行对话。"""
        if not AGENTS_AVAILABLE:
            yield LLMResponse(
                role="assistant",
                completion_text="OpenAI Agents SDK not available. Please install with: pip install openai-agents",
                is_chunk=True,
            )
            return

        if not model:
            msg = "Model must be specified"
            raise ValueError(msg)

        if not system_prompt:
            msg = "System prompt must be specified"
            raise ValueError(msg)

        # OpenAI Agents SDK 支持流式输出，但这里简化实现
        response = await self.text_chat(
            prompt,
            session_id,
            image_urls,
            contexts,
            system_prompt,
            model,
            tools,
            **kwargs,
        )
        yield LLMResponse(
            role="assistant",
            completion_text=response.completion_text,
            is_chunk=True,
        )
        yield response

    def get_model_provider(self):
        """获取配置好的 model provider，用于创建 RunConfig"""
        return self.model_provider

    def create_run_config(self):
        """创建运行配置"""
        if not AGENTS_AVAILABLE or not self.model_provider:
            return None
        return RunConfig(model_provider=self.model_provider)


def create_openai_source_provider_from_config() -> OpenAISourceProvider:
    """从配置文件创建 OpenAI Source Provider"""
    openai_config = get_openai_config()

    api_key = openai_config.get("api_key", "")
    if not api_key:
        msg = "请在config.json中设置openai.api_key"
        raise ValueError(msg)

    provider_config = {
        "id": "openai_source_provider",
        "type": "openai_source",
        "key": [api_key],
        "api_base_url": openai_config.get("api_base_url"),
    }
    provider_settings = {}

    return OpenAISourceProvider(provider_config, provider_settings)
