"""RAG Orchestrator - main entry point for RAG system."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from ...llm import LLMClient
from .config import RAGConfig
from .query_rewriter import QueryRewriter
from .sources.base import BaseRetrievalSource, RetrievalResult
from .sources.retrieval_service import RetrievalServiceSource
from .strategies.base import BaseRetrievalStrategy
from .strategies.single_round import SingleRoundStrategy
from .strategies.multi_round import MultiRoundStrategy
from .strategies.parallel import ParallelStrategy

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
        """Initialize retrieval sources from config."""
        sources = []
        
        for source_config in self.config.sources:
            if not source_config.enabled:
                continue
            
            if source_config.type == "retrieval_service":
                source = RetrievalServiceSource({
                    "url": source_config.url,
                    "pipeline_name": source_config.pipeline_name,
                    **source_config.config
                })
                sources.append(source)
                logger.info(f"Initialized retrieval source: {source_config.type}")
            else:
                logger.warning(f"Unknown retrieval source type: {source_config.type}")
        
        if not sources:
            # Fallback: create default retrieval service source
            logger.warning("No enabled sources found, creating default retrieval service source")
            sources.append(RetrievalServiceSource({
                "url": "http://localhost:8001",
                "pipeline_name": "default"
            }))
        
        return sources
    
    def _initialize_strategy(self) -> BaseRetrievalStrategy:
        """Initialize retrieval strategy from config."""
        strategy_config = {
            "pipeline_name": self.config.sources[0].pipeline_name if self.config.sources else "default",
            "top_k": 10,
            "max_rounds": self.config.max_rounds,
            "min_results_threshold": 3,
            "num_variants": 3
        }
        
        if self.config.strategy == "single_round":
            return SingleRoundStrategy(self.sources, strategy_config)
        elif self.config.strategy == "multi_round":
            return MultiRoundStrategy(self.sources, strategy_config)
        elif self.config.strategy == "parallel":
            return ParallelStrategy(self.sources, strategy_config)
        else:
            logger.warning(f"Unknown strategy: {self.config.strategy}, using multi_round")
            return MultiRoundStrategy(self.sources, strategy_config)
    
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
            
        except Exception as e:
            logger.error(f"RAG retrieval failed: {e}", exc_info=True)
            return {
                "query": query,
                "results": [],
                "error": str(e),
                "source": "rag_system"
            }

