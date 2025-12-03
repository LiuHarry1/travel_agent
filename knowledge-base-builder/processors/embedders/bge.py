"""BAAI BGE Embedding client."""
from typing import List, Optional
import logging

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

from .base import BaseEmbedder
from utils.exceptions import EmbeddingError

logger = logging.getLogger(__name__)


class BGEEmbedder(BaseEmbedder):
    """
    BAAI BGE Embedding client using Hugging Face models.
    
    Supports models:
    - BAAI/bge-large-en-v1.5: 1024 dimensions (English)
    - BAAI/bge-base-en-v1.5: 768 dimensions (English)
    - BAAI/bge-small-en-v1.5: 384 dimensions (English)
    """
    
    def __init__(
        self,
        model_name: str = "BAAI/bge-large-en-v1.5",
        device: Optional[str] = None,
        model_kwargs: Optional[dict] = None
    ):
        """Initialize BGE embedder."""
        self.model_name = model_name
        self.device = device or self._detect_device()
        self.model_kwargs = model_kwargs or {}
        self._model = None
        self._tokenizer = None
    
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
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using BGE model."""
        if not texts:
            return []
        
        try:
            self._load_model()
            
            if HAS_SENTENCE_TRANSFORMERS:
                embeddings = self._encode_with_sentence_transformers(texts)
            elif HAS_TRANSFORMERS:
                embeddings = self._encode_with_transformers(texts)
            else:
                raise EmbeddingError("No embedding library available")
            
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

