"""API-based reranker implementation."""
from typing import List, Dict, Any, Optional
import requests
from app.infrastructure.rerankers.base import BaseReranker
from app.infrastructure.config.pipeline_config import RerankConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)


class APIReranker(BaseReranker):
    """API-based reranker."""
    
    def __init__(self, config: RerankConfig):
        """Initialize API reranker."""
        self.config = config
        self.api_url = config.api_url
        self.model = config.model
    
    def rerank(
        self,
        query: str,
        chunks: List[Dict[str, Any]],
        top_k: int = 20
    ) -> List[Dict[str, Any]]:
        """Re-rank using external API."""
        if not chunks or not self.api_url:
            return chunks[:top_k]
        
        logger.info(f"Re-ranking {len(chunks)} chunks using API: {self.api_url}")
        
        # Prepare request payload
        documents = [chunk.get("text", "") for chunk in chunks]
        
        payload = {
            "query": query,
            "documents": documents,
            "top_k": min(top_k, len(chunks))
        }
        
        if self.model:
            payload["model"] = self.model
        
        # Make API request
        timeout = getattr(self.config, 'timeout', 30)
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=timeout
            )
            response.raise_for_status()
            result = response.json()
            
            # Parse response from reranker service
            # Format: {"results": [{"index": 0, "relevance_score": 0.9}, ...]}
            # Results are already sorted by relevance_score (descending, higher is better)
            if "results" not in result:
                logger.warning(f"Unexpected rerank response format: {result}")
                return chunks[:top_k]
            
            # Results from reranker service are already sorted by relevance_score (descending)
            # Use them in the order returned
            reranked = []
            for r in result["results"][:top_k]:
                idx = r.get("index", -1)
                if 0 <= idx < len(chunks):
                    chunk = chunks[idx].copy()
                    chunk["rerank_score"] = r.get("relevance_score", 0.0)
                    reranked.append(chunk)
            
            logger.info(f"Re-ranked {len(chunks)} chunks to {len(reranked)} using reranker service")
            return reranked
        except requests.exceptions.ConnectionError as e:
            logger.warning(
                f"Reranker service unavailable (connection refused): {self.api_url}. "
                f"Falling back to original order without reranking."
            )
            # Return original chunks in original order when reranker is unavailable
            return chunks[:top_k]
        except requests.exceptions.Timeout as e:
            logger.warning(
                f"Reranker service timeout: {self.api_url}. "
                f"Falling back to original order without reranking."
            )
            return chunks[:top_k]
        except Exception as e:
            logger.error(f"Rerank API call failed: {e}. Falling back to original order.", exc_info=True)
            # Fallback to original order on any other error
            return chunks[:top_k]

