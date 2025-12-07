"""Qwen LLM filter implementation."""
from typing import List, Dict, Any, Optional
import os
from app.infrastructure.llm.llm_filter import BaseLLMFilter
from app.infrastructure.config.pipeline_config import LLMFilterConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class QwenLLMFilter(BaseLLMFilter):
    """LLM for filtering irrelevant chunks."""
    
    def __init__(self, config: LLMFilterConfig):
        """Initialize LLM filter with configuration."""
        if not HAS_OPENAI:
            raise ImportError("openai package is required")
        
        # Use config values, fallback to environment variables if empty
        self.api_key = config.api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
        self.base_url = config.base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.model = config.model
        self._client = None
        
        if not self.api_key:
            logger.warning("LLM API key not found in config or environment variables")
    
    def _get_client(self) -> OpenAI:
        """Get OpenAI client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("Qwen API key not found")
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client
    
    def filter_chunks(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Filter chunks using LLM to determine relevance.
        
        Args:
            query: User query
            chunks: List of chunks with chunk_id and text
            top_k: Number of chunks to return
        
        Returns:
            Filtered list of relevant chunks
        """
        if not chunks:
            return []
        
        logger.info(f"Filtering {len(chunks)} chunks using Qwen LLM")
        
        try:
            client = self._get_client()
            
            # Build prompt
            chunks_text = "\n\n".join([
                f"Chunk {i+1} (ID: {chunk['chunk_id']}):\n{chunk['text']}"
                for i, chunk in enumerate(chunks)
            ])
            
            prompt = f"""You are a document retrieval assistant. A user has asked a question, and below are some retrieved document chunks.

User Question: {query}

Document Chunks:
{chunks_text}

Please select the {top_k} most relevant chunks based on the user's question. Return only the IDs of these chunks, separated by commas, in the format: 1,3,5,7

Return only the ID list, nothing else."""

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a professional document retrieval assistant capable of accurately judging the relevance of document chunks to questions."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content.strip()
            
            # Parse IDs
            try:
                selected_ids = [int(id_str.strip()) for id_str in result_text.split(",")]
            except ValueError:
                logger.warning(f"Failed to parse LLM response: {result_text}, using first {top_k} chunks")
                selected_ids = [chunk["chunk_id"] for chunk in chunks[:top_k]]
            
            # Create mapping
            chunk_map = {chunk["chunk_id"]: chunk for chunk in chunks}
            
            # Filter chunks
            filtered = []
            for chunk_id in selected_ids:
                if chunk_id in chunk_map:
                    filtered.append(chunk_map[chunk_id])
            
            # If LLM didn't return enough, add remaining chunks
            if len(filtered) < top_k:
                remaining_ids = set(chunk["chunk_id"] for chunk in chunks) - set(selected_ids)
                for chunk_id in list(remaining_ids)[:top_k - len(filtered)]:
                    if chunk_id in chunk_map:
                        filtered.append(chunk_map[chunk_id])
            
            logger.info(f"LLM filtered to {len(filtered)} chunks")
            return filtered[:top_k]
            
        except Exception as e:
            logger.error(f"LLM filtering error: {e}", exc_info=True)
            # Fallback: return top_k chunks
            logger.warning("Falling back to returning top_k chunks without LLM filtering")
            return chunks[:top_k]

