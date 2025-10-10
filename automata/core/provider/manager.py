from __future__ import annotations

from .entities import ProviderType
from .provider import Provider


class ProviderManager:
    def __init__(self):
        # 直接创建OpenAI provider
        provider_config = {
            "id": "openai_provider",
            "type": "openai",
            "key": ["your_api_key_here"],
        }
        provider_settings = {}
        self.provider_inst = Provider(provider_config, provider_settings)
        self.curr_provider_inst = self.provider_inst

    def get_using_provider(self, provider_type: ProviderType) -> Provider | None:
        """获取正在使用的提供商实例。"""
        if provider_type == ProviderType.CHAT_COMPLETION:
            return self.curr_provider_inst
        return None

    async def set_provider(self, provider_id: str, provider_type: ProviderType):
        """设置提供商。"""
        if provider_id != "openai_provider":
            msg = f"提供商 {provider_id} 不存在，无法设置。"
            raise ValueError(msg)
        if provider_type == ProviderType.CHAT_COMPLETION:
            self.curr_provider_inst = self.provider_inst

    async def get_provider_by_id(self, provider_id: str) -> Provider | None:
        """根据提供商 ID 获取提供商实例"""
        if provider_id == "openai_provider":
            return self.provider_inst
        return None
