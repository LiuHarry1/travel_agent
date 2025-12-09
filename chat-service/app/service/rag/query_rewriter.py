"""Query rewriter using LLM."""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from ...llm import LLMClient

logger = logging.getLogger(__name__)


class QueryRewriter:
    """Rewrites queries using LLM based on conversation history."""
    
    def __init__(self, llm_client: Optional[LLMClient] = None, enabled: bool = True):
        """
        Initialize query rewriter.
        
        Args:
            llm_client: LLM client to use (uses default if None)
            enabled: Whether query rewriting is enabled
        """
        self.llm_client = llm_client or LLMClient()
        self.enabled = enabled
    
    async def rewrite(
        self,
        query: str,
        conversation_history: List[Dict] = None
    ) -> str:
        """
        Rewrite query based on conversation history.
        
        Args:
            query: Original query
            conversation_history: Conversation history for context
            
        Returns:
            Rewritten query optimized for retrieval
        """
        if not self.enabled:
            return query
        
        if not conversation_history:
            # If no history, return query as-is (or do minimal optimization)
            return query
        
        try:
            # Build prompt for query rewriting
            prompt = self._build_rewrite_prompt(query, conversation_history)
            
            # Use LLM to rewrite query
            messages = [
                {"role": "user", "content": prompt}
            ]
            
            rewritten_query = ""
            async for chunk in self.llm_client.chat_stream(messages):
                rewritten_query += chunk
            
            # Clean up the rewritten query
            rewritten_query = rewritten_query.strip()
            
            # Fallback to original if rewrite is empty or too short
            if not rewritten_query or len(rewritten_query) < 2:
                logger.warning(f"Query rewrite resulted in empty/short query, using original")
                return query
            
            logger.info(f"Query rewritten: '{query[:50]}' -> '{rewritten_query[:50]}'")
            return rewritten_query
            
        except Exception as e:
            logger.error(f"Query rewrite failed: {e}, using original query", exc_info=True)
            return query
    
    def _build_rewrite_prompt(
        self,
        query: str,
        conversation_history: List[Dict]
    ) -> str:
        """
        Build prompt for query rewriting.
        
        Args:
            query: Original query
            conversation_history: Conversation history
            
        Returns:
            Prompt string for LLM
        """
        # Extract recent conversation context
        recent_messages = conversation_history[-5:] if conversation_history else []
        context_text = "\n".join([
            f"{msg.get('role', 'user')}: {msg.get('content', '')[:200]}"
            for msg in recent_messages
        ])
        
        prompt = f"""你是一个查询优化专家。你的任务是根据用户问题和对话历史，生成一个优化的搜索查询。

**优化原则：**
1. 提取关键信息：识别问题中的关键实体（地点、时间、主题、人物等）
2. 结合历史对话：如果当前问题涉及之前提到的内容，将上下文信息融入查询
3. 查询优化：将模糊问题具体化，补充缺失的上下文
4. 生成简洁查询：2-10 个词的具体查询，易于检索

**对话历史：**
{context_text}

**当前用户问题：**
{query}

**任务：**
基于对话历史和当前问题，生成一个优化的搜索查询。只返回优化后的查询，不要添加任何解释或其他内容。

**优化后的查询：**
"""
        return prompt

