"""
OpenAI LLM client implementation.
Supports OpenAI API and OpenAI-compatible proxy servers.
Uses official OpenAI Python SDK for better reliability and maintainability.
"""
from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Optional
import logging
import os
import time

import httpx
from openai import AsyncOpenAI

from .base import BaseLLMClient, LLMError

logger = logging.getLogger(__name__)


class OpenAIClient(BaseLLMClient):
    """OpenAI LLM client for OpenAI API or OpenAI-compatible proxy servers."""

    def __init__(self, api_key: Optional[str] = None, config=None):
        """Initialize OpenAI client with AsyncOpenAI SDK."""
        super().__init__(api_key, config)
        self._openai_client: Optional[AsyncOpenAI] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    def _get_http_client(self) -> httpx.AsyncClient:
        """
        Get or create shared httpx.AsyncClient with connection pooling.
        
        This enables connection reuse and improves performance for multiple requests.
        """
        if self._http_client is None:
            # Configure timeout
            timeout = httpx.Timeout(
                connect=30.0,
                read=self._config.llm_timeout,
                write=30.0,
                pool=30.0
            )
            
            # Configure connection pool limits for better performance
            # max_connections: maximum number of connections in the pool
            # max_keepalive_connections: connections to keep alive for reuse
            # Increased keepalive connections to reduce connection establishment overhead
            limits = httpx.Limits(
                max_connections=100,  # Maximum connections in pool
                max_keepalive_connections=50  # Increased from 20 to 50 for better connection reuse
            )
            
            self._http_client = httpx.AsyncClient(
                timeout=timeout,
                limits=limits,
                http2=True,  # Enable HTTP/2 for better performance
                # Enable connection pooling optimizations
                follow_redirects=True,
            )
        return self._http_client

    def _get_openai_client(self) -> AsyncOpenAI:
        """
        Get or create AsyncOpenAI client instance with connection pooling.
        
        Uses a shared httpx.AsyncClient to enable connection reuse and improve performance.
        """
        if self._openai_client is None:
            base_url = self._get_base_url()
            # Use API key if available, otherwise use placeholder
            # Some providers (like Ollama) may not require a real key
            api_key = self.api_key or "not-set"
            
            # Get shared HTTP client with connection pooling
            http_client = self._get_http_client()
            
            self._openai_client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                http_client=http_client,  # Inject custom httpx client with connection pool
                timeout=self._config.llm_timeout,
            )
        return self._openai_client
    
    async def warmup_connection(self) -> None:
        """
        Warm up connection by making a lightweight request to establish connection.
        
        This helps reduce TTFB (Time To First Byte) for the first real request.
        """
        try:
            client = self._get_openai_client()
            # Make a minimal request to establish connection
            # Use a very small model or a health check endpoint if available
            # For now, we'll just ensure the HTTP client is ready
            http_client = self._get_http_client()
            # The connection will be established on first real request
            # But having the client ready helps
            logger.debug("Connection pool warmed up")
        except Exception as e:
            logger.debug(f"Connection warmup skipped: {e}")

    async def close(self):
        """Close OpenAI client and HTTP client, release resources."""
        await super().close()
        if self._openai_client is not None:
            await self._openai_client.close()
            self._openai_client = None
        if self._http_client is not None:
            await self._http_client.aclose()
            self._http_client = None

    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment variable."""
        return os.getenv("OPENAI_API_KEY")

    def _get_base_url(self) -> str:
        """Get base URL from environment variable or config."""
        base_url = os.getenv("OPENAI_BASE_URL")
        if not base_url:
            # Try to get from config
            llm_config = self._config._config.get("llm", {})
            base_url = llm_config.get("openai_base_url")
            if not base_url:
                # Default to official OpenAI API
                base_url = "https://api.openai.com/v1"
        # Ensure base_url ends with /v1 or /v1/ for OpenAI-compatible format
        base_url = base_url.rstrip("/")
        if not base_url.endswith("/v1"):
            if base_url.endswith("/v1/"):
                base_url = base_url.rstrip("/")
            else:
                base_url = f"{base_url}/v1"
        return base_url

    def _get_model_name(self) -> str:
        """Get model name from config."""
        llm_config = self._config._config.get("llm", {})
        return llm_config.get("openai_model", llm_config.get("model", "gpt-4"))

    def _normalize_payload(self, messages: List[Dict[str, str]], model: Optional[str] = None) -> Dict[str, Any]:
        """Normalize payload for OpenAI API format."""
        payload = {
            "model": model or self._get_model_name(),
            "messages": messages,
        }
        return payload
    
    def _convert_functions_to_tools(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert 'functions' parameter to 'tools' format for OpenAI API.
        OpenAI API uses 'tools' instead of 'functions', and the format is slightly different.
        """
        if "functions" in payload:
            functions = payload.pop("functions")
            # Convert functions to tools format
            tools = []
            for func in functions:
                tools.append({
                    "type": "function",
                    "function": func
                })
            payload["tools"] = tools
            
            # Convert function_call to tool_choice
            if "function_call" in payload:
                function_call = payload.pop("function_call")
                if function_call == "auto":
                    payload["tool_choice"] = "auto"
                elif function_call == "none":
                    payload["tool_choice"] = "none"
                elif isinstance(function_call, dict) and "name" in function_call:
                    payload["tool_choice"] = {
                        "type": "function",
                        "function": {"name": function_call["name"]}
                    }
        
        return payload


    async def _make_stream_request(self, endpoint: str, payload: Dict[str, Any]) -> AsyncGenerator[Any, None]:
        """
        Make async streaming request to OpenAI API using official SDK.
        
        Returns async generator of SDK chunk objects (not just content strings).
        This allows the caller to access full chunk information including tool_calls.
        
        Note: endpoint parameter is kept for interface compatibility but not used,
        as SDK already knows to call chat.completions.create().
        """
        model = payload.get("model", self._get_model_name())
        
        # Convert functions to tools format
        request_params = self._convert_functions_to_tools(payload.copy())
        request_params["stream"] = True

        logger.info(f"OpenAI streaming request (async) - Model: {model}")
        if "tools" in request_params:
            logger.debug(f"Using {len(request_params['tools'])} tools (converted from functions)")

        try:
            # Get client early to ensure connection pool is ready
            client = self._get_openai_client()
            
            # Pre-warm connection by ensuring HTTP client is initialized
            # This helps reduce first request latency
            http_client = self._get_http_client()
            
            # Use SDK's streaming method - returns chunk objects directly
            # The connection pool will reuse existing connections if available
            stream = await client.chat.completions.create(**request_params)
            
            # Yield the full chunk objects so caller can access tool_calls, content, etc.
            async for chunk in stream:
                yield chunk
                
        except Exception as exc:
            logger.error(f"OpenAI streaming error: {str(exc)}", exc_info=True)
            error_msg = str(exc)
            raise LLMError(f"OpenAI streaming error：{error_msg}") from exc