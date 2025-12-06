"""BAAI BGE Embedding client."""
from typing import List, Optional
import os

try:
    from sentence_transformers import SentenceTransformer
    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:
    HAS_SENTENCE_TRANSFORMERS = False
    try:
        from transformers import AutoTokenizer, AutoModel
        import torch
        HAS_TRANSFORMERS = True
    except ImportError:
        HAS_TRANSFORMERS = False

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

from .base import BaseEmbedder
from utils.exceptions import EmbeddingError
from utils.logger import get_logger

logger = get_logger(__name__)


class BGEEmbedder(BaseEmbedder):
    """
    BAAI BGE Embedding client using Hugging Face models or API service.
    
    Supports models:
    - BAAI/bge-large-en-v1.5: 1024 dimensions (English)
    - BAAI/bge-base-en-v1.5: 768 dimensions (English)
    - BAAI/bge-small-en-v1.5: 384 dimensions (English)
    
    Can work in two modes:
    1. Local mode: Loads model directly (requires sentence-transformers or transformers) - NOT RECOMMENDED
    2. API mode: Uses remote embedding service via HTTP API (RECOMMENDED)
    
    API endpoints are determined by model:
    - English BGE models (bge-*-en-*): /embed/en
    - Chinese BGE models (bge-*-zh-*): /embed/zh
    - Other models: /embed
    """
    
    def __init__(
        self,
        model_name: str = "BAAI/bge-large-en-v1.5",
        device: Optional[str] = None,
        model_kwargs: Optional[dict] = None,
        api_url: Optional[str] = None
    ):
        """Initialize BGE embedder.
        
        Args:
            model_name: Hugging Face model name
            device: Device to run model on (cpu/cuda)
            model_kwargs: Additional model arguments
            api_url: If provided, use API service instead of local model
        """
        self.model_name = model_name
        self.device = device or self._detect_device()
        self.model_kwargs = model_kwargs or {}
        self.api_url = api_url or os.getenv("BGE_API_URL", None)
        self._model = None
        self._tokenizer = None
        self._use_api = self.api_url is not None
    
    def _detect_device(self) -> str:
        """Auto-detect best device."""
        if HAS_SENTENCE_TRANSFORMERS or HAS_TRANSFORMERS:
            try:
                import torch
                if torch.cuda.is_available():
                    return "cuda"
            except ImportError:
                pass
        return "cpu"
    
    def _load_model(self):
        """Load the embedding model."""
        if self._model is not None:
            return
        
        try:
            if HAS_SENTENCE_TRANSFORMERS:
                logger.info(f"Loading BGE model using sentence-transformers: {self.model_name}")
                self._model = SentenceTransformer(
                    self.model_name,
                    device=self.device,
                    **self.model_kwargs
                )
                logger.info(f"BGE model loaded successfully on {self.device}")
            elif HAS_TRANSFORMERS:
                logger.info(f"Loading BGE model using transformers: {self.model_name}")
                self._tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self._model = AutoModel.from_pretrained(
                    self.model_name,
                    **self.model_kwargs
                )
                self._model.to(self.device)
                self._model.eval()
                logger.info(f"BGE model loaded successfully on {self.device}")
            else:
                raise EmbeddingError(
                    "Neither sentence-transformers nor transformers library is installed. "
                    "Install one: pip install sentence-transformers "
                    "or pip install transformers torch"
                )
        except Exception as e:
            logger.error(f"Failed to load BGE model: {str(e)}", exc_info=True)
            raise EmbeddingError(f"Failed to load BGE model: {str(e)}") from e
    
    def _encode_with_sentence_transformers(self, texts: List[str]) -> List[List[float]]:
        """Encode texts using sentence-transformers."""
        embeddings = self._model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False
        )
        return embeddings.tolist()
    
    def _encode_with_transformers(self, texts: List[str]) -> List[List[float]]:
        """Encode texts using transformers library."""
        import torch
        
        encoded_input = self._tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt"
        )
        encoded_input = {k: v.to(self.device) for k, v in encoded_input.items()}
        
        with torch.no_grad():
            model_output = self._model(**encoded_input)
            embeddings = model_output.last_hidden_state.mean(dim=1)
        
        embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
        embeddings = embeddings.cpu().numpy()
        
        return embeddings.tolist()
    
    def _get_api_endpoint(self) -> str:
        """Get API endpoint based on model name."""
        # Determine endpoint based on model name
        model_lower = self.model_name.lower()
        
        if "bge-large-en" in model_lower or "bge-base-en" in model_lower or "bge-small-en" in model_lower:
            # English BGE models use /embed/en
            return f"{self.api_url}/embed/en"
        elif "bge-large-zh" in model_lower or "bge-base-zh" in model_lower or "bge-small-zh" in model_lower:
            # Chinese BGE models use /embed/zh
            return f"{self.api_url}/embed/zh"
        else:
            # Other models (e.g., nvidia/llama-nemotron-embed-1b-v2) use /embed
            return f"{self.api_url}/embed"
    
    def _embed_via_api(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings via API service."""
        if not HAS_REQUESTS:
            raise EmbeddingError("requests library is required for API mode. Install with: pip install requests")
        
        if not self.api_url:
            raise EmbeddingError("BGE API URL is not configured. Please set BGE_API_URL or provide api_url parameter.")
        
        endpoint = self._get_api_endpoint()
        logger.info(f"Calling BGE API endpoint: {endpoint} for model: {self.model_name}")
        
        try:
            response = requests.post(
                endpoint,
                json={"texts": texts},
                timeout=300  # 5 minutes timeout for large batches
            )
            response.raise_for_status()
            result = response.json()
            
            # Handle different response formats
            if "embeddings" in result:
                embeddings = result["embeddings"]
            elif "data" in result and isinstance(result["data"], list):
                # Some APIs return {"data": [[...], [...]]}
                embeddings = result["data"]
            else:
                # Try to get embeddings from root level if it's a list
                embeddings = result if isinstance(result, list) else result.get("embedding", [])
            
            if not embeddings:
                raise EmbeddingError("Empty embeddings returned from API")
            
            logger.debug(f"Received {len(embeddings)} embeddings from API")
            return embeddings
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {str(e)}", exc_info=True)
            raise EmbeddingError(f"BGE API request failed: {str(e)}") from e
        except (KeyError, TypeError) as e:
            logger.error(f"Invalid API response format: {str(e)}", exc_info=True)
            raise EmbeddingError(f"Invalid API response format: {str(e)}") from e
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using BGE model."""
        if not texts:
            return []
        
        try:
            # Use API if configured
            if self._use_api:
                logger.debug(f"Using BGE API service at {self.api_url}")
                embeddings = self._embed_via_api(texts)
                logger.debug(f"Generated {len(embeddings)} embeddings via API")
                return embeddings
            
            # Otherwise use local model
            self._load_model()
            
            if HAS_SENTENCE_TRANSFORMERS:
                embeddings = self._encode_with_sentence_transformers(texts)
            elif HAS_TRANSFORMERS:
                embeddings = self._encode_with_transformers(texts)
            else:
                raise EmbeddingError("No embedding library available. Install sentence-transformers or transformers, or set BGE_API_URL to use API mode.")
            
            logger.debug(f"Generated {len(embeddings)} embeddings using BGE model: {self.model_name}")
            return embeddings
        except Exception as e:
            logger.error(f"BGE embedding error: {str(e)}", exc_info=True)
            raise EmbeddingError(f"BGE embedding failed: {str(e)}") from e
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension based on model."""
        dim_map = {
            "BAAI/bge-large-en-v1.5": 1024,
            "BAAI/bge-base-en-v1.5": 768,
            "BAAI/bge-small-en-v1.5": 384,
            "BAAI/bge-large-zh-v1.5": 1024,
            "BAAI/bge-base-zh-v1.5": 768,
            "BAAI/bge-small-zh-v1.5": 384,
            "nvidia/llama-nemotron-embed-1b-v2": 1024,
        }
        if self.model_name in dim_map:
            return dim_map[self.model_name]
        if "large" in self.model_name.lower():
            return 1024
        elif "base" in self.model_name.lower():
            return 768
        elif "small" in self.model_name.lower():
            return 384
        return 1024

