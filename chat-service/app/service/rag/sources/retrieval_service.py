"""Retrieval service source implementation."""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List

import httpx

from app.core.exceptions import RAGError
from app.service.rag.sources.base import BaseRetrievalSource, RetrievalResult

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
            "http://localhost:8003"
        )
        self.default_pipeline = config.get("pipeline_name", "default")
        self.timeout = config.get("timeout", 30.0)
        self.max_retries = config.get("max_retries", 3)
        self.retry_delay_base = config.get("retry_delay_base", 1.0)  # Base delay in seconds
        self.fallback_on_error = config.get("fallback_on_error", True)  # Return empty results on error
    
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
        
        # Note: retrieval-service route structure:
        # main.py: prefix="/api/v1"
        # api/__init__.py: prefix="/retrieval"
        # retrieval.py: @router.post("/search")
        # Full path: /api/v1/retrieval/search
        url = f"{self.url}/api/v1/retrieval/search"
        
        logger.info(
            f"Calling retrieval service: URL={url}, query={query[:100]}, "
            f"pipeline={pipeline_name}, timeout={self.timeout}s"
        )
        
        # Retry logic with exponential backoff
        last_exception = None
        for attempt in range(self.max_retries):
            try:
                logger.debug(
                    f"Retrieval service request (attempt {attempt + 1}/{self.max_retries}): "
                    f"POST {url}, pipeline={pipeline_name}"
                )
                
                # Configure timeout with separate connect and read timeouts
                # connect timeout: time to establish connection (shorter)
                # read timeout: time to read response (longer, matches self.timeout)
                timeout_config = httpx.Timeout(
                    connect=10.0,  # 10 seconds to establish connection
                    read=float(self.timeout),  # Full timeout for reading response
                    write=10.0,  # 10 seconds to write request
                    pool=10.0  # 10 seconds to get connection from pool
                )
                
                # Configure connection limits to prevent connection pool exhaustion
                limits = httpx.Limits(
                    max_connections=100,
                    max_keepalive_connections=20
                )
                
                async with httpx.AsyncClient(
                    timeout=timeout_config,
                    limits=limits,
                    follow_redirects=True
                ) as client:
                    response = await client.post(
                        url,
                        json={
                            "query": query,
                            "pipeline_name": pipeline_name
                        },
                        headers={"Content-Type": "application/json"}
                    )
                    
                    logger.debug(
                        f"Retrieval service response: status={response.status_code}, "
                        f"headers={dict(response.headers)}, "
                        f"content_length={response.headers.get('content-length', 'unknown')}"
                    )
                    
                    # Log response body for 502 errors to help diagnose
                    if response.status_code == 502:
                        try:
                            response_text = response.text[:500]  # First 500 chars
                            logger.warning(
                                f"Received 502 Bad Gateway from retrieval service. "
                                f"Response body: {response_text}"
                            )
                        except Exception:
                            pass
                    
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
                    
            except httpx.TimeoutException as e:
                last_exception = e
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay_base * (2 ** attempt)
                    logger.warning(
                        f"Retrieval service timeout (attempt {attempt + 1}/{self.max_retries}), "
                        f"retrying after {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"Retrieval service timeout after {self.max_retries} attempts")
                    if self.fallback_on_error:
                        logger.warning("Returning empty results due to timeout")
                        return []
                    raise RAGError(
                        message=f"Retrieval service timeout after {self.max_retries} attempts",
                        details={"url": url, "query": query[:100]}
                    ) from e
                    
            except httpx.RequestError as e:
                last_exception = e
                # Network errors: retry
                if attempt < self.max_retries - 1:
                    delay = self.retry_delay_base * (2 ** attempt)
                    logger.warning(
                        f"Retrieval service request error (attempt {attempt + 1}/{self.max_retries}): {e}, "
                        f"retrying after {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    logger.error(f"Retrieval service request error after {self.max_retries} attempts: {e}")
                    if self.fallback_on_error:
                        logger.warning("Returning empty results due to connection error")
                        return []
                    raise RAGError(
                        message=f"Failed to connect to retrieval service after {self.max_retries} attempts: {str(e)}",
                        details={"url": url, "query": query[:100]}
                    ) from e
                    
            except httpx.HTTPStatusError as e:
                last_exception = e
                status_code = e.response.status_code
                
                # Server errors (5xx): retry
                if status_code >= 500 and attempt < self.max_retries - 1:
                    delay = self.retry_delay_base * (2 ** attempt)
                    logger.warning(
                        f"Retrieval service server error {status_code} (attempt {attempt + 1}/{self.max_retries}), "
                        f"retrying after {delay:.1f}s"
                    )
                    await asyncio.sleep(delay)
                    continue
                else:
                    # All retries exhausted for server errors, or client errors (4xx)
                    if status_code >= 500:
                        # Server error after all retries
                        logger.error(
                            f"Retrieval service server error {status_code} after {self.max_retries} attempts. "
                            f"URL: {url}, Query: {query[:100]}"
                        )
                    else:
                        # Client error (4xx): don't retry
                        logger.error(
                            f"Retrieval service client error {status_code}. "
                            f"URL: {url}, Query: {query[:100]}"
                        )
                    
                    if self.fallback_on_error:
                        logger.warning(
                            f"Returning empty results due to HTTP error {status_code} "
                            f"(fallback mode enabled). Query: {query[:100]}"
                        )
                        return []
                    raise RAGError(
                        message=f"Retrieval service returned error: {status_code}",
                        details={"url": url, "status_code": status_code, "query": query[:100]}
                    ) from e
                    
            except Exception as e:
                last_exception = e
                logger.error(f"Unexpected error in retrieval service: {e}", exc_info=True)
                if self.fallback_on_error:
                    logger.warning("Returning empty results due to unexpected error")
                    return []
                raise RAGError(
                    message=f"Unexpected error in retrieval service: {str(e)}",
                    details={"url": url, "query": query[:100]}
                ) from e
        
        # All retries exhausted
        if self.fallback_on_error:
            logger.warning(f"All retry attempts failed, returning empty results")
            return []
        else:
            raise RAGError(
                message=f"Retrieval service failed after {self.max_retries} attempts",
                details={"url": url, "query": query[:100], "last_error": str(last_exception)}
            ) from last_exception

