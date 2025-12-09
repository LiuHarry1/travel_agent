"""OpenAI Embedding client."""
from typing import List, Optional
import os

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

from .base import BaseEmbedder
from utils.exceptions import EmbeddingError
from utils.logger import get_logger

logger = get_logger(__name__)


class OpenAIEmbedder(BaseEmbedder):
    """OpenAI Embedding client."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        base_url: Optional[str] = None,
        timeout: Optional[int] = None
    ):
        """Initialize OpenAI embedder."""
        if not HAS_OPENAI:
            raise ImportError(
                "openai package is required. Install with: pip install openai"
            )
        
        self._base_url = base_url
        self.api_key = api_key or self._get_api_key()
        self.model = model
        self.timeout = timeout or self._get_default_timeout()
        self._client: Optional[OpenAI] = None
    
    def _get_default_timeout(self) -> int:
        """Get default timeout from settings."""
        try:
            from config.settings import get_settings
            settings = get_settings()
            return settings.embedding_timeout
        except:
            return 300  # Default 5 minutes
    
    def _get_api_key(self) -> Optional[str]:
        """Get API key from environment variable."""
        return os.getenv("OPENAI_API_KEY")
    
    def _get_base_url(self) -> Optional[str]:
        """Get base URL (None means use OpenAI default)."""
        return self._base_url or os.getenv("OPENAI_BASE_URL")
    
    def _get_client(self) -> OpenAI:
        """Get or create OpenAI client."""
        if self._client is None:
            if not self.api_key:
                raise EmbeddingError(
                    "OpenAI API key not found. Set OPENAI_API_KEY environment variable."
                )
            client_kwargs = {
                "api_key": self.api_key,
                "timeout": self.timeout
            }
            if self._get_base_url():
                client_kwargs["base_url"] = self._get_base_url()
            self._client = OpenAI(**client_kwargs)
        return self._client
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI API."""
        if not texts:
            return []
        
        try:
            client = self._get_client()
            # Timeout is set in client initialization
            response = client.embeddings.create(
                model=self.model,
                input=texts
            )
            embeddings = [item.embedding for item in response.data]
            logger.debug(f"Generated {len(embeddings)} embeddings using OpenAI model: {self.model}")
            return embeddings
        except Exception as e:
            logger.error(f"OpenAI embedding error: {str(e)}", exc_info=True)
            raise EmbeddingError(f"OpenAI embedding failed: {str(e)}") from e
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension based on model."""
        dim_map = {
            "text-embedding-3-small": 1536,
            "text-embedding-3-large": 3072,
            "text-embedding-ada-002": 1536,
        }
        return dim_map.get(self.model, 1536)

