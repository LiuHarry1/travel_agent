"""Reranker service implementation."""
import os
import torch
from typing import List, Tuple, Optional
from transformers import AutoModelForSequenceClassification, AutoTokenizer
from app.utils.logger import get_logger

logger = get_logger(__name__)

# Default model - using bge-reranker-base
DEFAULT_MODEL = "BAAI/bge-reranker-base"


class RerankerService:
    """Reranker service using BGE reranker models."""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize reranker service.
        
        Args:
            model_name: Model name (default: BAAI/bge-reranker-base)
        """
        self.model_name = model_name or os.getenv("RERANKER_MODEL", DEFAULT_MODEL)
        self.model: Optional[AutoModelForSequenceClassification] = None
        self.tokenizer: Optional[AutoTokenizer] = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()
    
    def _load_model(self):
        """Load the reranker model."""
        try:
            logger.info(f"Loading reranker model: {self.model_name} on {self.device}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
            self.model.eval()
            self.model.to(self.device)
            logger.info(f"Successfully loaded reranker model: {self.model_name}")
        except Exception as e:
            logger.error(f"Failed to load reranker model {self.model_name}: {e}")
            logger.info(f"Trying alternative model: BAAI/bge-reranker-v2-m3")
            try:
                self.model_name = "BAAI/bge-reranker-v2-m3"
                self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
                self.model = AutoModelForSequenceClassification.from_pretrained(self.model_name)
                self.model.eval()
                self.model.to(self.device)
                logger.info(f"Successfully loaded fallback model: {self.model_name}")
            except Exception as fallback_error:
                logger.error(f"Failed to load fallback model: {fallback_error}", exc_info=True)
                raise RuntimeError(f"Could not load any reranker model. Original error: {e}, Fallback error: {fallback_error}")
    
    def rerank(
        self,
        query: str,
        documents: List[str],
        top_k: Optional[int] = None,
        model: Optional[str] = None
    ) -> List[Tuple[int, float]]:
        """
        Rerank documents based on query relevance.
        
        Args:
            query: User query
            documents: List of document texts
            top_k: Number of top results to return (None = all)
            model: Optional model override (not used currently)
        
        Returns:
            List of tuples (index, relevance_score) sorted by score descending
        """
        if not documents:
            return []
        
        if self.model is None or self.tokenizer is None:
            raise RuntimeError("Reranker model not loaded")
        
        try:
            # Prepare pairs: (query, document) for each document
            pairs = [[query, doc] for doc in documents]
            
            # Tokenize pairs
            inputs = self.tokenizer(
                pairs,
                padding=True,
                truncation=True,
                return_tensors='pt',
                max_length=512
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            
            # Get relevance scores
            with torch.no_grad():
                outputs = self.model(**inputs)
                scores = outputs.logits.squeeze().cpu().tolist()
            
            # Handle single score case
            if not isinstance(scores, list):
                scores = [scores]
            
            # Convert to list of (index, score) tuples
            indexed_scores = [(idx, float(score)) for idx, score in enumerate(scores)]
            
            # Sort by score descending
            indexed_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Return top_k if specified
            if top_k is not None:
                indexed_scores = indexed_scores[:top_k]
            
            return indexed_scores
            
        except Exception as e:
            logger.error(f"Rerank error: {e}", exc_info=True)
            raise

