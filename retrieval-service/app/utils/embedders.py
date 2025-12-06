"""Embedding model utilities."""
from typing import List, Optional
import os
from app.utils.logger import get_logger

logger = get_logger(__name__)

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


class BaseEmbedder:
    """Base embedder interface."""
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings."""
        raise NotImplementedError
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        raise NotImplementedError


class QwenEmbedder(BaseEmbedder):
    """Qwen embedding client."""
    
    def __init__(self, model: str = "text-embedding-v2", api_key: Optional[str] = None):
        """Initialize Qwen embedder."""
        if not HAS_OPENAI:
            raise ImportError("openai package is required")
        
        self.model = model
        self.api_key = api_key or os.getenv("DASHSCOPE_API_KEY") or os.getenv("QWEN_API_KEY")
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        self._client = None
    
    def _get_client(self) -> OpenAI:
        """Get OpenAI client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("Qwen API key not found")
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        return self._client
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings."""
        if not texts:
            return []
        
        client = self._get_client()
        response = client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]
    
    @property
    def dimension(self) -> int:
        """Get dimension."""
        return 1536


class BGEEmbedder(BaseEmbedder):
    """BGE embedding client via API."""
    
    def __init__(self, model: str = "BAAI/bge-large-en-v1.5", api_url: Optional[str] = None):
        """Initialize BGE embedder."""
        if not HAS_REQUESTS:
            raise ImportError("requests package is required")
        
        self.model = model
        self.api_url = api_url or os.getenv("BGE_API_URL", "http://localhost:8001")
    
    def _get_endpoint(self) -> str:
        """Get API endpoint."""
        model_lower = self.model.lower()
        if "bge-large-en" in model_lower or "bge-base-en" in model_lower or "bge-small-en" in model_lower:
            return f"{self.api_url}/embed/en"
        elif "bge-large-zh" in model_lower or "bge-base-zh" in model_lower or "bge-small-zh" in model_lower:
            return f"{self.api_url}/embed/zh"
        else:
            return f"{self.api_url}/embed"
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings via API."""
        if not texts:
            return []
        
        endpoint = self._get_endpoint()
        response = requests.post(endpoint, json={"texts": texts}, timeout=300)
        response.raise_for_status()
        result = response.json()
        
        if "embeddings" in result:
            return result["embeddings"]
        elif "data" in result:
            return result["data"]
        else:
            return result if isinstance(result, list) else result.get("embedding", [])
    
    @property
    def dimension(self) -> int:
        """Get dimension."""
        dim_map = {
            "BAAI/bge-large-en-v1.5": 1024,
            "BAAI/bge-base-en-v1.5": 768,
            "BAAI/bge-small-en-v1.5": 384,
        }
        return dim_map.get(self.model, 1024)


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI embedding client."""
    
    def __init__(self, model: str = "text-embedding-3-small", api_key: Optional[str] = None):
        """Initialize OpenAI embedder."""
        if not HAS_OPENAI:
            raise ImportError("openai package is required")
        
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None
    
    def _get_client(self) -> OpenAI:
        """Get OpenAI client."""
        if self._client is None:
            if not self.api_key:
                raise ValueError("OpenAI API key not found")
            self._client = OpenAI(api_key=self.api_key)
        return self._client
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings."""
        if not texts:
            return []
        
        client = self._get_client()
        response = client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in response.data]
    
    @property
    def dimension(self) -> int:
        """Get dimension."""
        if "3-small" in self.model:
            return 1536
        elif "3-large" in self.model:
            return 3072
        return 1536


def create_embedder(provider: str, model: Optional[str] = None) -> BaseEmbedder:
    """Create embedder by provider."""
    provider = provider.lower()
    
    if provider == "qwen":
        model = model or "text-embedding-v2"
        return QwenEmbedder(model=model)
    elif provider == "bge":
        model = model or "BAAI/bge-large-en-v1.5"
        from app.config import settings
        return BGEEmbedder(model=model, api_url=settings.bge_api_url)
    elif provider == "openai":
        model = model or "text-embedding-3-small"
        return OpenAIEmbedder(model=model)
    else:
        raise ValueError(f"Unknown embedder provider: {provider}")

