"""Retrieval service source implementation."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, List

import httpx

from ....core.exceptions import RAGError
from .base import BaseRetrievalSource, RetrievalResult

logger = logging.getLogger(__name__)


class RetrievalServiceSource(BaseRetrievalSource):
    """Retrieval source that uses the retrieval-service API."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize retrieval service source.
        
        Args:
            config: Configuration dict with 'url' and optionally 'pipeline_name'
        """
        super().__init__(config)
        self.url = config.get("url") or os.getenv(
            "RETRIEVAL_SERVICE_URL",
            "http://localhost:8001"
        )
        self.default_pipeline = config.get("pipeline_name", "default")
        self.timeout = config.get("timeout", 30.0)
    
    def get_source_type(self) -> str:
        """Get source type identifier."""
        return "retrieval_service"
    
    async def search(
        self,
        query: str,
        pipeline_name: str = "default",
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """
        Search using retrieval service.
        
        Args:
            query: Search query
            pipeline_name: Pipeline name (uses default if not provided)
            top_k: Maximum number of results (not used by retrieval-service, it has its own limit)
            
        Returns:
            List of RetrievalResult objects
        """
        if not pipeline_name or pipeline_name == "default":
            pipeline_name = self.default_pipeline
        
        url = f"{self.url}/api/search"
        
        try:
            async with httpx.AsyncClient(timeout=float(self.timeout)) as client:
                response = await client.post(
                    url,
                    json={
                        "query": query,
                        "pipeline_name": pipeline_name
                    }
                )
                response.raise_for_status()
                data = response.json()
                
                # Convert response to RetrievalResult objects
                results = []
                for item in data.get("results", []):
                    chunk_id = item.get("chunk_id")
                    text = item.get("text", "")
                    score = item.get("score")  # May not be present
                    
                    if chunk_id is not None and text:
                        results.append(RetrievalResult(
                            chunk_id=chunk_id,
                            text=text,
                            score=score,
                            metadata={"source": "retrieval_service", "pipeline": pipeline_name}
                        ))
                
                logger.info(f"Retrieval service returned {len(results)} results for query: {query[:50]}")
                return results
                
        except httpx.RequestError as e:
            logger.error(f"Retrieval service request error: {e}")
            raise RAGError(
                message=f"Failed to connect to retrieval service: {str(e)}",
                details={"url": url, "query": query[:100]}
            ) from e
        except httpx.HTTPStatusError as e:
            logger.error(f"Retrieval service HTTP error: {e.response.status_code}")
            raise RAGError(
                message=f"Retrieval service returned error: {e.response.status_code}",
                details={"url": url, "status_code": e.response.status_code, "query": query[:100]}
            ) from e
        except Exception as e:
            logger.error(f"Retrieval service error: {e}", exc_info=True)
            raise RAGError(
                message=f"Unexpected error in retrieval service: {str(e)}",
                details={"url": url, "query": query[:100]}
            ) from e

