"""Qwen embedder implementation."""
from typing import List, Optional
import os
from app.infrastructure.embedders.base import BaseEmbedder
from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from openai import OpenAI
    import httpx
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class QwenEmbedder(BaseEmbedder):
    """Qwen embedding client."""
    
    def __init__(self, model: str = "text-embedding-v2", api_key: Optional[str] = None, proxy: Optional[str] = None):
        """Initialize Qwen embedder.
        
        Args:
            model: Model name to use for embeddings
            api_key: API key for Qwen/DashScope. If not provided, will try DASHSCOPE_API_KEY or QWEN_API_KEY env vars
            proxy: Optional proxy URL. If None, will respect HTTP_PROXY/HTTPS_PROXY env vars. 
                  Set to empty string to disable proxy.
        """
        if not HAS_OPENAI:
            raise ImportError("openai package is required")
        
        self.model = model
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self.proxy = proxy if proxy is not None else os.getenv("QWEN_PROXY")
        self._client = None
        self._dimension = None
    
    def _get_client(self) -> OpenAI:
        """Get OpenAI client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("Qwen API key not found. Please set DASHSCOPE_API_KEY or QWEN_API_KEY environment variable.")
            
            # Configure HTTP client with proxy settings
            # If proxy is explicitly set to empty string, disable proxy
            # Otherwise, let httpx use its default behavior (respects HTTP_PROXY/HTTPS_PROXY env vars)
            if self.proxy == "":
                # Explicitly disable proxy by creating client without proxy
                http_client = httpx.Client(
                    timeout=30.0,
                    proxy=None
                )
            else:
                # Use default httpx behavior (will respect HTTP_PROXY/HTTPS_PROXY if set)
                # Or use explicit proxy if provided
                http_client_kwargs = {"timeout": 30.0}
                if self.proxy:
                    http_client_kwargs["proxy"] = self.proxy
                http_client = httpx.Client(**http_client_kwargs)
            
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                http_client=http_client
            )
        return self._client
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Qwen API."""
        if not texts:
            return []
        
        try:
            client = self._get_client()
            response = client.embeddings.create(
                model=self.model,
                input=texts
            )
            embeddings = [item.embedding for item in response.data]
            
            # Cache dimension from first embedding
            if self._dimension is None and embeddings:
                self._dimension = len(embeddings[0])
            
            return embeddings
        except Exception as e:
            error_msg = str(e)
            # Provide more helpful error messages
            if "Connection refused" in error_msg or "Connection error" in error_msg:
                proxy_info = ""
                if self.proxy:
                    proxy_info = f" (proxy: {self.proxy})"
                elif os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY"):
                    proxy_info = f" (proxy from env: HTTP_PROXY={os.getenv('HTTP_PROXY')}, HTTPS_PROXY={os.getenv('HTTPS_PROXY')})"
                
                logger.error(
                    f"Qwen embedding connection error{proxy_info}. "
                    f"Please check: 1) Network connectivity to {self.base_url}, "
                    f"2) Proxy settings (set QWEN_PROXY='' to disable), "
                    f"3) API key is valid. Original error: {e}",
                    exc_info=True
                )
            else:
                logger.error(f"Qwen embedding error: {e}", exc_info=True)
            raise
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self._dimension is None:
            # Try to get dimension by embedding a test string
            try:
                test_embedding = self.embed(["test"])
                if test_embedding:
                    self._dimension = len(test_embedding[0])
                else:
                    raise ValueError("Could not determine embedding dimension")
            except Exception as e:
                logger.warning(f"Could not determine dimension: {e}")
                # Default dimension for Qwen text-embedding-v2
                self._dimension = 1536
        return self._dimension

