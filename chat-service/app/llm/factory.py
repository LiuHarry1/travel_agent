"""
LLM Client Factory for creating provider-specific clients.
"""
from __future__ import annotations

from typing import Optional

from .provider import LLMProvider, BaseLLMClient, QwenClient, OpenAIClient, LLMError


class LLMClientFactory:
    """Factory for creating LLM clients based on provider configuration."""

    @staticmethod
    def create_client(provider: Optional[LLMProvider] = None, api_key: Optional[str] = None):
        """
        Create LLM client instance based on provider.

        Args:
            provider: LLM provider (qwen, openai). If None, reads from config.
            api_key: Optional API key override

        Returns:
            BaseLLMClient instance

        Raises:
            ValueError: If provider is not supported or configuration is invalid
        """
        from ..core.config_service import get_config_service

        config_service = get_config_service()

        # Get provider from config if not specified
        if provider is None:
            provider_name = config_service.llm_provider
            try:
                provider = LLMProvider(provider_name.lower())
            except ValueError:
                raise ValueError(
                    f"Unsupported LLM provider: {provider_name}. "
                    f"Supported providers: {[p.value for p in LLMProvider]}"
                )

        # Create client based on provider
        if provider == LLMProvider.QWEN:
            return QwenClient(api_key=api_key, config=config_service)
        elif provider == LLMProvider.OPENAI:
            return OpenAIClient(api_key=api_key, config=config_service)
        else:
            raise ValueError(f"Unsupported provider: {provider}")

    @staticmethod
    def get_default_client():
        """Get default LLM client from configuration."""
        return LLMClientFactory.create_client()


