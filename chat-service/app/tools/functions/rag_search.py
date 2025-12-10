"""RAG search function using new RAG orchestrator."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from app.core.exceptions import RAGError
from app.llm import LLMClient
from app.service.rag import RAGOrchestrator, RAGConfig
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Global RAG orchestrator instance (lazy initialization)
_rag_orchestrator: Optional[RAGOrchestrator] = None


def _get_rag_orchestrator() -> RAGOrchestrator:
    """Get or create RAG orchestrator instance."""
    global _rag_orchestrator
    if _rag_orchestrator is None:
        try:
            settings = get_settings()
            rag_settings = settings.rag
            
            # Convert Pydantic model to RAGConfig
            from app.service.rag.config import QueryRewriterConfig, RetrievalSourceConfig, RAGConfig
            
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
                    config=src.config
                )
                for src in rag_settings.sources
            ]
            
            rag_config = RAGConfig(
                enabled=rag_settings.enabled,
                strategy=rag_settings.strategy,
                max_rounds=rag_settings.max_rounds,
                query_rewriter=query_rewriter_config,
                sources=sources_config
            )
            
            _rag_orchestrator = RAGOrchestrator(
                config=rag_config,
                llm_client=LLMClient()
            )
            logger.info(f"RAG orchestrator initialized with strategy: {rag_config.strategy}")
        except Exception as e:
            logger.error(f"Failed to initialize RAG orchestrator: {e}", exc_info=True)
            # Create a minimal fallback config
            from app.service.rag.config import QueryRewriterConfig, RetrievalSourceConfig, RAGConfig
            fallback_config = RAGConfig(
                enabled=True,
                strategy="multi_round",
                max_rounds=3,
                query_rewriter=QueryRewriterConfig(enabled=True),
                sources=[RetrievalSourceConfig(
                    type="retrieval_service",
                    enabled=True,
                    url="http://localhost:8001",
                    pipeline_name="default"
                )]
            )
            _rag_orchestrator = RAGOrchestrator(config=fallback_config, llm_client=LLMClient())
            logger.warning("Using fallback RAG config")
    
    return _rag_orchestrator


async def rag_retrieve(
    query: str,
    conversation_history: Optional[List[Dict]] = None,
    pipeline_name: str = "default"
) -> Dict[str, Any]:
    """
    Retrieve documents using RAG system.
    
    Args:
        query: Search query
        conversation_history: Conversation history for context-aware retrieval
        pipeline_name: Pipeline name (for compatibility, but uses config if available)
    
    Returns:
        Dict with query, results, and metadata
    """
    orchestrator = _get_rag_orchestrator()
    
    # Convert conversation history format if needed
    # Ensure it's a list of dicts with 'role' and 'content' keys
    formatted_history = []
    if conversation_history:
        for msg in conversation_history:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if content:
                    formatted_history.append({"role": role, "content": content})
    
    try:
        result = await orchestrator.retrieve(query, formatted_history)
        
        # Ensure pipeline_name is included in result for compatibility
        if "pipeline_name" not in result:
            result["pipeline_name"] = pipeline_name
        
        return result
    except RAGError as e:
        # Convert RAGError to dict format for function return
        logger.error(f"RAG retrieval error: {e.message}")
        return {
            "query": query,
            "results": [],
            "error": e.message,
            "source": "rag_system",
            "code": e.code
        }


# For backward compatibility, keep the old function name
async def retrieval_service_search(
    query: str,
    pipeline_name: str = "default",
    conversation_history: Optional[List[Dict]] = None
) -> Dict[str, Any]:
    """
    Search using retrieval service (RAG) - backward compatibility wrapper.
    
    This function is kept for compatibility but now uses the new RAG orchestrator.
    For new code, use rag_retrieve() which supports conversation history.
    
    Args:
        query: Search query
        pipeline_name: Pipeline name for retrieval service
        conversation_history: Conversation history for context-aware retrieval
    
    Returns:
        Dict with query and results (chunk_id, text)
    """
    return await rag_retrieve(query, pipeline_name=pipeline_name, conversation_history=conversation_history)


# Updated schema to reflect new capabilities
RETRIEVAL_SERVICE_SCHEMA = {
    "type": "object",
    "properties": {
        "query": {
            "type": "string",
            "description": """用户查询。系统会自动：
1. 基于对话历史优化查询
2. 根据配置的检索策略执行检索（单轮/多轮/并行）
3. 返回相关文档片段

你只需要提供用户的原始问题，系统会自动处理查询优化和检索。"""
        },
        "pipeline_name": {
            "type": "string",
            "description": "Pipeline name for retrieval service",
            "default": "default"
        }
    },
    "required": ["query"]
}
