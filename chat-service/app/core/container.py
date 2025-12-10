"""Dependency injection container for application services."""
from __future__ import annotations

import logging
from typing import Optional

from app.core.config_service import get_config_service
from app.llm import LLMClient
from app.service.chat import ChatService
from app.service.message_processing import MessageProcessingService
from app.service.tool_execution import ToolExecutionService
from app.service.tool_result_formatter import format_tool_result_for_llm
from app.service.rag import RAGOrchestrator, RAGConfig
from app.tools import FunctionRegistry, get_function_registry

logger = logging.getLogger(__name__)


class Container:
    """
    Dependency injection container.
    
    Manages the lifecycle of all application services and provides
    a single source of truth for service instances.
    """
    
    def __init__(self):
        """Initialize container with lazy service creation."""
        self._config_service = None
        self._llm_client: Optional[LLMClient] = None
        self._function_registry: Optional[FunctionRegistry] = None
        self._message_processor: Optional[MessageProcessingService] = None
        self._tool_executor: Optional[ToolExecutionService] = None
        self._rag_orchestrator: Optional[RAGOrchestrator] = None
        self._chat_service: Optional[ChatService] = None
        self._initialized = False
    
    @property
    def config_service(self):
        """Get configuration service instance."""
        if self._config_service is None:
            self._config_service = get_config_service()
        return self._config_service
    
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
    def message_processor(self) -> MessageProcessingService:
        """Get or create message processing service instance."""
        if self._message_processor is None:
            logger.info("Creating message processor...")
            config_service = self.config_service
            self._message_processor = MessageProcessingService(lambda: config_service)
            self._message_processor.set_function_registry(self.function_registry)
        return self._message_processor
    
    @property
    def tool_executor(self) -> ToolExecutionService:
        """Get or create tool execution service instance."""
        if self._tool_executor is None:
            logger.info("Creating tool executor...")
            self._tool_executor = ToolExecutionService(
                self.function_registry,
                format_tool_result_for_llm
            )
        return self._tool_executor
    
    @property
    def rag_orchestrator(self) -> RAGOrchestrator:
        """Get or create RAG orchestrator instance."""
        if self._rag_orchestrator is None:
            logger.info("Creating RAG orchestrator...")
            try:
                from app.service.rag.config import (
                    QueryRewriterConfig, RetrievalSourceConfig, RAGConfig,
                    CacheConfig, ProcessorConfig, InputGuardrailConfig, OutputGuardrailConfig
                )
                config_service = self.config_service
                rag_settings = config_service.get_settings().rag
                
                query_rewriter_config = QueryRewriterConfig(
                    enabled=rag_settings.query_rewriter.enabled,
                    model=rag_settings.query_rewriter.model
                )
                
                sources_config = [
                    RetrievalSourceConfig(
                        type=src.type,
                        enabled=src.enabled,
                        url=src.url,
                        pipeline_name=src.pipeline_name,
                        config=src.config,
                        timeout=getattr(src, 'timeout', 60.0)
                    )
                    for src in rag_settings.sources
                ]
                
                # Convert cache config
                cache_config = None
                if rag_settings.cache and rag_settings.cache.enabled:
                    cache_config = CacheConfig(
                        enabled=rag_settings.cache.enabled,
                        ttl_seconds=rag_settings.cache.ttl_seconds,
                        max_size=rag_settings.cache.max_size
                    )
                
                # Convert processor config
                processor_config = ProcessorConfig(
                    ranking_strategy=rag_settings.processor.ranking_strategy,
                    merge_keep_best_score=rag_settings.processor.merge_keep_best_score
                )
                
                # Convert input guardrail config
                input_guardrail_config = InputGuardrailConfig(
                    enabled=rag_settings.input_guardrail.enabled,
                    strict_mode=rag_settings.input_guardrail.strict_mode,
                    max_query_length=rag_settings.input_guardrail.max_query_length,
                    blocked_patterns=rag_settings.input_guardrail.blocked_patterns,
                    sensitive_patterns=rag_settings.input_guardrail.sensitive_patterns
                )
                
                # Convert output guardrail config
                output_guardrail_config = OutputGuardrailConfig(
                    enabled=rag_settings.output_guardrail.enabled,
                    strict_mode=rag_settings.output_guardrail.strict_mode,
                    max_results=rag_settings.output_guardrail.max_results,
                    filter_sensitive_info=rag_settings.output_guardrail.filter_sensitive_info,
                    validate_relevance=rag_settings.output_guardrail.validate_relevance,
                    sensitive_patterns=rag_settings.output_guardrail.sensitive_patterns
                )
                
                rag_config = RAGConfig(
                    enabled=rag_settings.enabled,
                    strategy=rag_settings.strategy,
                    max_rounds=rag_settings.max_rounds,
                    query_rewriter=query_rewriter_config,
                    sources=sources_config,
                    cache=cache_config,
                    processor=processor_config,
                    input_guardrail=input_guardrail_config,
                    output_guardrail=output_guardrail_config,
                    fallback_on_error=rag_settings.fallback_on_error
                )
                
                self._rag_orchestrator = RAGOrchestrator(
                    config=rag_config,
                    llm_client=self.llm_client
                )
                logger.info(f"RAG orchestrator initialized with strategy: {rag_config.strategy}")
            except Exception as e:
                logger.error(f"Failed to initialize RAG orchestrator: {e}", exc_info=True)
                # Create fallback config
                from app.service.rag.config import (
                    QueryRewriterConfig, RetrievalSourceConfig, RAGConfig,
                    CacheConfig, ProcessorConfig, InputGuardrailConfig, OutputGuardrailConfig
                )
                fallback_config = RAGConfig(
                    enabled=True,
                    strategy="multi_round",
                    max_rounds=3,
                    query_rewriter=QueryRewriterConfig(enabled=True),
                    sources=[RetrievalSourceConfig(
                        type="retrieval_service",
                        enabled=True,
                        url="http://localhost:8003",
                        pipeline_name="default",
                        timeout=60.0
                    )],
                    cache=CacheConfig(enabled=True, ttl_seconds=300, max_size=1000),
                    processor=ProcessorConfig(),
                    input_guardrail=InputGuardrailConfig(enabled=True),
                    output_guardrail=OutputGuardrailConfig(enabled=True),
                    fallback_on_error=True
                )
                self._rag_orchestrator = RAGOrchestrator(config=fallback_config, llm_client=self.llm_client)
                logger.warning("Using fallback RAG config")
        return self._rag_orchestrator

    @property
    def chat_service(self) -> ChatService:
        """Get or create chat service instance."""
        if self._chat_service is None:
            logger.info("Creating chat service...")
            self._chat_service = ChatService(
                llm_client=self.llm_client,
                function_registry=self.function_registry,
                message_processor=self.message_processor,
                tool_executor=self.tool_executor
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
                f"Loaded {len(registry.functions)} functions, "
                f"{len(registry.get_enabled_functions())} enabled."
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

