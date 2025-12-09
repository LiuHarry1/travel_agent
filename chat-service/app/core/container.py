"""Dependency injection container for application services."""
from __future__ import annotations

import logging
from typing import Optional

from ..config import get_config
from ..llm import LLMClient
from ..service.chat import ChatService
from ..tools import FunctionRegistry, get_function_registry

logger = logging.getLogger(__name__)


class Container:
    """
    Dependency injection container.
    
    Manages the lifecycle of all application services and provides
    a single source of truth for service instances.
    """
    
    def __init__(self):
        """Initialize container with lazy service creation."""
        self._llm_client: Optional[LLMClient] = None
        self._function_registry: Optional[FunctionRegistry] = None
        self._chat_service: Optional[ChatService] = None
        self._initialized = False
    
    @property
    def llm_client(self) -> LLMClient:
        """Get or create LLM client instance."""
        if self._llm_client is None:
            logger.info("Creating LLM client...")
            self._llm_client = LLMClient()
        return self._llm_client

    @property
    def function_registry(self) -> FunctionRegistry:
        """Get or create function registry instance."""
        if self._function_registry is None:
            logger.info("Creating function registry...")
            self._function_registry = get_function_registry()
        return self._function_registry

    @property
    def chat_service(self) -> ChatService:
        """Get or create chat service instance."""
        if self._chat_service is None:
            logger.info("Creating chat service...")
            self._chat_service = ChatService(
                llm_client=self.llm_client,
                function_registry=self.function_registry
            )
        return self._chat_service
    
    async def initialize(self) -> None:
        """
        Initialize all services that require async initialization.
        
        This should be called during application startup.
        """
        if self._initialized:
            logger.info("Container already initialized")
            return
        
        logger.info("Initializing container services...")
        
        # Initialize function registry (already initialized when accessed)
        try:
            registry = self.function_registry
            logger.info(
                f"Function registry initialized. "
                f"Loaded {len(registry._functions)} functions, "
                f"{len(registry._enabled_functions)} enabled."
            )
        except Exception as e:
            logger.warning(f"Failed to initialize function registry: {e}", exc_info=True)
        
        # Warm up LLM client connection pool to reduce first request latency
        try:
            llm_client = self.llm_client
            provider_client = llm_client._get_client()
            if hasattr(provider_client, 'warmup_connection'):
                await provider_client.warmup_connection()
                logger.info("LLM client connection pool warmed up")
        except Exception as e:
            logger.debug(f"LLM connection warmup skipped: {e}")
        
        self._initialized = True
        logger.info("Container initialization complete")
    
    async def shutdown(self) -> None:
        """
        Cleanup all services.
        
        This should be called during application shutdown.
        """
        logger.info("Shutting down container...")
        
        self._initialized = False
        logger.info("Container shutdown complete")


# Global container instance
_container: Optional[Container] = None


def get_container() -> Container:
    """Get global container instance."""
    global _container
    if _container is None:
        _container = Container()
    return _container


def reset_container() -> None:
    """Reset container (useful for testing)."""
    global _container
    _container = None

