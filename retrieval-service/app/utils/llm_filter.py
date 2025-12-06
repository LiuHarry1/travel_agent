"""LLM-based chunk filtering."""
from typing import List, Dict, Any, Optional
import os
from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class QwenLLMFilter:
    """Qwen LLM for filtering irrelevant chunks."""
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None, model: str = "qwen-plus"):
        """Initialize Qwen LLM filter."""
        if not HAS_OPENAI:
            raise ImportError("openai package is required")
        
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
        self.base_url = base_url or "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.model = model
        self._client = None
    
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
            
            prompt = f"""你是一个文档检索助手。用户提出了一个问题，下面是一些检索到的文档片段。

用户问题：{query}

文档片段：
{chunks_text}

请根据用户问题，从上述文档片段中选择最相关的 {top_k} 个片段。只返回这些片段的ID，用逗号分隔，格式如：1,3,5,7

只返回ID列表，不要其他内容。"""

            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一个专业的文档检索助手，能够准确判断文档片段与问题的相关性。"},
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

