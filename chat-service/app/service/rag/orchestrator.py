"""RAG Orchestrator - main entry point for RAG system."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.exceptions import RAGError
from app.llm import LLMClient
from app.service.rag.cache import RAGCache
from app.service.rag.config import RAGConfig
from app.service.rag.factories import SourceFactory, StrategyFactory
from app.service.rag.guardrails import InputGuardrail, OutputGuardrail
from app.service.rag.processors import ResultMerger, ResultRanker
from app.service.rag.query_rewriter import QueryRewriter
from app.service.rag.sources.base import BaseRetrievalSource, RetrievalResult
from app.service.rag.strategies.base import BaseRetrievalStrategy

logger = logging.getLogger(__name__)


class RAGOrchestrator:
    """Main orchestrator for RAG system."""
    
    def __init__(
        self,
        config: RAGConfig,
        llm_client: Optional[LLMClient] = None
    ):
        """
        Initialize RAG orchestrator.
        
        Args:
            config: RAG configuration
            llm_client: LLM client for query rewriting
        """
        self.config = config
        self.llm_client = llm_client or LLMClient()
        
        # Initialize query rewriter
        self.query_rewriter = QueryRewriter(
            llm_client=self.llm_client,
            enabled=config.query_rewriter.enabled
        )
        
        # Initialize retrieval sources
        self.sources = self._initialize_sources()
        
        # Initialize retrieval strategy
        self.strategy = self._initialize_strategy()
        
        # Initialize result processors
        self.result_merger = ResultMerger()
        self.result_ranker = ResultRanker()
        
        # Initialize cache (if enabled in config)
        if config.cache and config.cache.enabled:
            self.cache = RAGCache(
                ttl_seconds=config.cache.ttl_seconds,
                max_size=config.cache.max_size
            )
        else:
            self.cache = None
        
        # Initialize guardrails
        if config.input_guardrail and config.input_guardrail.enabled:
            self.input_guardrail = InputGuardrail({
                "enabled": config.input_guardrail.enabled,
                "strict_mode": config.input_guardrail.strict_mode,
                "max_query_length": config.input_guardrail.max_query_length,
                "blocked_patterns": config.input_guardrail.blocked_patterns,
                "sensitive_patterns": config.input_guardrail.sensitive_patterns
            })
        else:
            self.input_guardrail = None
        
        if config.output_guardrail and config.output_guardrail.enabled:
            self.output_guardrail = OutputGuardrail({
                "enabled": config.output_guardrail.enabled,
                "strict_mode": config.output_guardrail.strict_mode,
                "max_results": config.output_guardrail.max_results,
                "filter_sensitive_info": config.output_guardrail.filter_sensitive_info,
                "validate_relevance": config.output_guardrail.validate_relevance,
                "sensitive_patterns": config.output_guardrail.sensitive_patterns
            })
        else:
            self.output_guardrail = None
    
    def _initialize_sources(self) -> List[BaseRetrievalSource]:
        """Initialize retrieval sources from config using factory."""
        sources = []
        
        for source_config in self.config.sources:
            if not source_config.enabled:
                continue
            
            try:
                source = SourceFactory.create(
                    source_config.type,
                    {
                        "url": source_config.url,
                        "pipeline_name": source_config.pipeline_name,
                        "timeout": getattr(source_config, 'timeout', 60.0),
                        **source_config.config
                    }
                )
                sources.append(source)
                logger.info(f"Initialized retrieval source: {source_config.type}")
            except ValueError as e:
                logger.error(f"Failed to create source {source_config.type}: {e}")
                # Continue with other sources instead of failing completely
        
        if not sources:
            # Fallback: create default retrieval service source
            logger.warning("No enabled sources found, creating default retrieval service source")
            try:
                sources.append(SourceFactory.create(
                    "retrieval_service",
                    {
                        "url": "http://localhost:8003",
                        "pipeline_name": "default",
                        "timeout": 60.0
                    }
                ))
            except ValueError as e:
                logger.error(f"Failed to create fallback source: {e}")
        
        return sources
    
    def _initialize_strategy(self) -> BaseRetrievalStrategy:
        """Initialize retrieval strategy from config using factory."""
        strategy_config = {
            "pipeline_name": self.config.sources[0].pipeline_name if self.config.sources else "default",
            "top_k": 10,
            "max_rounds": self.config.max_rounds,
            "min_results_threshold": 3,
            "num_variants": 3
        }
        
        try:
            return StrategyFactory.create(
                self.config.strategy,
                self.sources,
                strategy_config
            )
        except ValueError as e:
            logger.warning(f"Unknown strategy: {self.config.strategy}, using multi_round. Error: {e}")
            # Fallback to multi_round
            return StrategyFactory.create("multi_round", self.sources, strategy_config)
    
    async def retrieve(
        self,
        query: str,
        conversation_history: List[Dict] = None
    ) -> Dict[str, Any]:
        """
        Execute RAG retrieval.
        
        Args:
            query: User query
            conversation_history: Conversation history for context
            
        Returns:
            Dict with query and results
        """
        if not self.config.enabled:
            logger.warning("RAG is disabled, returning empty results")
            return {
                "query": query,
                "results": [],
                "source": "rag_system"
            }
        
        try:
            # Step 0: Input Guardrail validation
            if self.input_guardrail:
                guardrail_result = self.input_guardrail.validate(query, conversation_history)
                if not guardrail_result.is_valid:
                    error_msg = f"Input guardrail validation failed: {guardrail_result.reason}"
                    logger.warning(error_msg)
                    if self.config.input_guardrail.strict_mode:
                        raise RAGError(
                            message=error_msg,
                            details={"query": query[:100], "reason": guardrail_result.reason}
                        )
                    # In non-strict mode, use sanitized query
                    if guardrail_result.sanitized_content:
                        query = guardrail_result.sanitized_content
                        logger.info(f"Using sanitized query: {query[:50]}")
            
            # Step 0.5: Check cache (after guardrail, before query rewrite)
            if self.cache:
                cache_key = self.cache._generate_key(query, conversation_history)
                cached_result = self.cache.get(cache_key)
                if cached_result is not None:
                    logger.info(f"Cache hit for query: {query[:50]}")
                    return cached_result
            
            # Step 1: Rewrite query if enabled
            rewritten_query = await self.query_rewriter.rewrite(query, conversation_history)
            
            # Step 2: Execute retrieval strategy
            logger.info(
                f"Executing retrieval strategy: {self.config.strategy}, "
                f"rewritten_query={rewritten_query[:100]}"
            )
            results = await self.strategy.retrieve(rewritten_query, conversation_history)
            logger.info(f"Retrieval strategy returned {len(results)} results")
            
            # Step 2.5: Post-process results (merge and rank if needed)
            # For multi-round/parallel strategies, results may need merging and ranking
            if self.config.strategy in ("multi_round", "parallel") and results:
                # Results are already deduplicated by strategy, but we ensure they're ranked
                ranking_strategy = self.config.processor.ranking_strategy if self.config.processor else "score"
                results = self.result_ranker.rank(results, strategy=ranking_strategy)
            
            # Step 3: Output Guardrail validation
            if self.output_guardrail:
                guardrail_result = self.output_guardrail.validate(results, query)
                if not guardrail_result.is_valid:
                    error_msg = f"Output guardrail validation failed: {guardrail_result.reason}"
                    logger.warning(error_msg)
                    if self.config.output_guardrail.strict_mode:
                        raise RAGError(
                            message=error_msg,
                            details={"query": query[:100], "reason": guardrail_result.reason}
                        )
                    # In non-strict mode, use filtered results
                    if guardrail_result.filtered_results is not None:
                        results = guardrail_result.filtered_results
                        logger.info(f"Using filtered results: {len(results)} results after guardrail")
            
            # Step 4: Format results
            formatted_results = [
                {
                    "chunk_id": result.chunk_id,
                    "text": result.text
                }
                for result in results
            ]
            
            logger.info(f"RAG retrieval completed: {len(formatted_results)} results for query: {query[:50]}")
            
            # Check if we got empty results (might indicate an error)
            has_results = len(formatted_results) > 0
            
            result = {
                "query": rewritten_query,  # Return rewritten query
                "original_query": query,  # Also include original
                "results": formatted_results,
                "source": "rag_system",
                "strategy": self.config.strategy
            }
            
            # Add warning if no results (might be due to service error)
            if not has_results:
                logger.warning(
                    f"RAG retrieval returned no results for query: {query[:100]}. "
                    f"This might indicate retrieval service issues."
                )
            
            # Step 5: Cache result
            if self.cache:
                cache_key = self.cache._generate_key(query, conversation_history)
                self.cache.set(cache_key, result)
            
            return result
            
        except RAGError:
            # Re-raise RAG errors (but allow fallback if configured)
            # If sources have fallback_on_error=True, they should return empty results instead of raising
            raise
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}", exc_info=True)
            # If we have fallback configured, return empty results instead of raising
            # This allows the system to continue even if RAG fails
            if hasattr(self.config, 'fallback_on_error') and self.config.fallback_on_error:
                logger.warning("RAG retrieval failed, returning empty results as fallback")
                return {
                    "query": query,
                    "results": [],
                    "source": "rag_system",
                    "error": str(e)
                }
            raise RAGError(
                message=f"RAG retrieval failed: {str(e)}",
                details={"query": query[:100], "strategy": self.config.strategy}
            ) from e

