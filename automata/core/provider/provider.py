from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

try:
    from agents import Agent, OpenAIChatCompletionsModel, Runner
    from agents.models.multi_provider import OpenAIProvider
    from agents.run import RunConfig

    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False


@dataclass
class ProviderMeta:
    id: str
    model: str
    type: str


class AbstractProvider(abc.ABC):
    def __init__(self, provider_config: dict) -> None:
        super().__init__()
        self.model_name = ""
        self.provider_config = provider_config

    def set_model(self, model_name: str):
        """设置当前使用的模型名称"""
        self.model_name = model_name

    def get_model(self) -> str:
        """获得当前使用的模型名称"""
        return self.model_name

    def meta(self) -> ProviderMeta:
        """获取 Provider 的元数据"""
        provider_type_name = self.provider_config["type"]
        return ProviderMeta(
            id=self.provider_config["id"],
            model=self.get_model(),
            type=provider_type_name,
        )


@dataclass
class LLMResponse:
    role: str
    completion_text: str = ""
    is_chunk: bool = False


class OpenAIAgentProvider(AbstractProvider):
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
            self.agent = Agent(
                name="AutomataAssistant",
                instructions="You are a helpful assistant.",
                model=self.provider_config.get("model", "gpt-4"),
            )
        else:
            self.model_provider = None
            self.agent = None

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
            return ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]
        # OpenAI Agents SDK 默认支持多种模型，这里返回常用模型
        return ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]

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

        # 如果指定了不同的模型或工具，创建临时agent
        if (model and model != self.get_model()) or tools or system_prompt:
            temp_model_provider = OpenAIProvider(
                api_key=self.api_key,
                base_url=self.api_base_url,
                use_responses=False,
            )
            temp_agent = Agent(
                name="AutomataAssistant",
                instructions=system_prompt or "You are a helpful assistant.",
                model=model or self.provider_config.get("model", "gpt-4"),
                tools=tools or [],
            )
            temp_run_config = RunConfig(model_provider=temp_model_provider)
            result = await Runner.run(temp_agent, prompt, run_config=temp_run_config)
        else:
            result = await Runner.run(
                self.agent,
                prompt,
                run_config=self.create_run_config(),
            )

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
    ) -> AsyncGenerator[LLMResponse, None]:
        """获得 LLM 的流式文本对话结果。会使用当前的模型进行对话。在生成的最后会返回一次完整的结果。"""
        if not AGENTS_AVAILABLE:
            yield LLMResponse(
                role="assistant",
                completion_text="OpenAI Agents SDK not available. Please install with: pip install openai-agents",
                is_chunk=True,
            )
            return

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


# 为了兼容性，保留Provider类名
Provider = OpenAIAgentProvider


class OpenAIAgentProvider(AbstractProvider):
    # ... existing code ...

    def get_model_provider(self):
        """获取配置好的 model provider，用于创建 RunConfig"""
        return self.model_provider

    def create_run_config(self):
        """创建运行配置"""
        if not AGENTS_AVAILABLE or not self.model_provider:
            return None
        return RunConfig(model_provider=self.model_provider)
