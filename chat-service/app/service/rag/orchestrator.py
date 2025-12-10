"""RAG Orchestrator - main entry point for RAG system."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.exceptions import RAGError
from app.llm import LLMClient
from app.service.rag.config import RAGConfig
from app.service.rag.factories import SourceFactory, StrategyFactory
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
                        "url": "http://localhost:8001",
                        "pipeline_name": "default"
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
            # Step 1: Rewrite query if enabled
            rewritten_query = await self.query_rewriter.rewrite(query, conversation_history)
            
            # Step 2: Execute retrieval strategy
            results = await self.strategy.retrieve(rewritten_query, conversation_history)
            
            # Step 3: Format results
            formatted_results = [
                {
                    "chunk_id": result.chunk_id,
                    "text": result.text
                }
                for result in results
            ]
            
            logger.info(f"RAG retrieval completed: {len(formatted_results)} results for query: {query[:50]}")
            
            return {
                "query": rewritten_query,  # Return rewritten query
                "original_query": query,  # Also include original
                "results": formatted_results,
                "source": "rag_system",
                "strategy": self.config.strategy
            }
            
        except RAGError:
            # Re-raise RAG errors
            raise
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}", exc_info=True)
            raise RAGError(
                message=f"RAG retrieval failed: {str(e)}",
                details={"query": query[:100], "strategy": self.config.strategy}
            ) from e

