"""
Qwen (Alibaba DashScope) LLM client implementation.
Uses OpenAI-compatible API provided by DashScope.
"""
from __future__ import annotations

from typing import Optional

import os

from .openai import OpenAIClient
from .base import LLMError


class QwenClient(OpenAIClient):
    """Qwen (Alibaba DashScope) LLM client using OpenAI-compatible API endpoint."""

    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment variable."""
        return os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")

    def _get_base_url(self) -> str:
        """Get DashScope base URL pointing to OpenAI-compatible endpoint."""
        return "https://dashscope.aliyuncs.com/compatible-mode/v1"

    def _get_model_name(self) -> str:
        """Get model name from config."""
        if hasattr(self._config, 'llm_model'):
            return self._config.llm_model
        else:
            # Support ConfigurationService
            return self._config.get_settings().llm.model

    def _normalize_payload(self, messages, model=None):
        """Normalize payload - same as OpenAI format since we're using OpenAI-compatible API."""
        # Call parent method which handles OpenAI format
        return super()._normalize_payload(messages, model or self._get_model_name())
