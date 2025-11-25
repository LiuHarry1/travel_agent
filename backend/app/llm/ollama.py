"""
Ollama LLM client implementation.
Uses OpenAI-compatible API provided by Ollama.
"""
from __future__ import annotations

from typing import Optional

import os

from .openai import OpenAIClient
from .base import LLMError


class OllamaClient(OpenAIClient):
    """Ollama LLM client using OpenAI-compatible API endpoint."""

    def _get_api_key(self) -> Optional[str]:
        """Ollama doesn't require API key, return optional key from env or use placeholder."""
        # Ollama doesn't require a real API key, but we use a placeholder if needed
        return os.getenv("OLLAMA_API_KEY", "ollama")  # Placeholder value

    @property
    def has_api_key(self) -> bool:
        """Ollama doesn't require API key, so always return True."""
        return True

    def _get_base_url(self) -> str:
        """Get Ollama base URL pointing to OpenAI-compatible endpoint."""
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        base_url = base_url.rstrip("/")
        # Ollama OpenAI-compatible API is at /v1 endpoint
        if not base_url.endswith("/v1"):
            base_url = f"{base_url}/v1"
        return base_url

    def _get_model_name(self) -> str:
        """Get model name from config."""
        llm_config = self._config._config.get("llm", {})
        # First try ollama_model, then fall back to model, then default
        return llm_config.get("ollama_model") or llm_config.get("model") or "qwen2.5:32b"

    def _normalize_payload(self, messages, model=None):
        """Normalize payload - same as OpenAI format since we're using OpenAI-compatible API."""
        # Call parent method which handles OpenAI format
        return super()._normalize_payload(messages, model or self._get_model_name())
