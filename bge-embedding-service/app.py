"""BGE Embedding API Service."""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import logging
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
        raise ImportError("Neither sentence-transformers nor transformers is installed")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="BGE Embedding Service", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model instance
_model = None
_tokenizer = None
_model_name = os.getenv("BGE_MODEL_NAME", "BAAI/bge-large-en-v1.5")
_device = os.getenv("BGE_DEVICE", "cpu")


class EmbeddingRequest(BaseModel):
    """Request model for embedding."""
    texts: List[str]
    normalize: Optional[bool] = True


class EmbeddingResponse(BaseModel):
    """Response model for embedding."""
    embeddings: List[List[float]]
    dimension: int
    model: str


def load_model():
    """Load the BGE model."""
    global _model, _tokenizer
    
    if _model is not None:
        return
    
    logger.info(f"Loading BGE model: {_model_name} on device: {_device}")
    
    try:
        if HAS_SENTENCE_TRANSFORMERS:
            _model = SentenceTransformer(_model_name, device=_device)
            logger.info(f"Model loaded successfully using sentence-transformers")
        elif HAS_TRANSFORMERS:
            _tokenizer = AutoTokenizer.from_pretrained(_model_name)
            _model = AutoModel.from_pretrained(_model_name)
            _model.to(_device)
            _model.eval()
            logger.info(f"Model loaded successfully using transformers")
    except Exception as e:
        logger.error(f"Failed to load model: {e}", exc_info=True)
        raise


@app.on_event("startup")
async def startup_event():
    """Load model on startup."""
    load_model()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "model": _model_name,
        "device": _device,
        "model_loaded": _model is not None
    }


@app.post("/embed", response_model=EmbeddingResponse)
async def embed_texts(request: EmbeddingRequest):
    """Generate embeddings for texts."""
    if not request.texts:
        raise HTTPException(status_code=400, detail="texts list cannot be empty")
    
    if _model is None:
        load_model()
    
    try:
        if HAS_SENTENCE_TRANSFORMERS:
            embeddings = _model.encode(
                request.texts,
                convert_to_numpy=True,
                normalize_embeddings=request.normalize,
                show_progress_bar=False
            )
            embeddings = embeddings.tolist()
        elif HAS_TRANSFORMERS:
            import torch
            
            encoded_input = _tokenizer(
                request.texts,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            )
            encoded_input = {k: v.to(_device) for k, v in encoded_input.items()}
            
            with torch.no_grad():
                model_output = _model(**encoded_input)
                embeddings = model_output.last_hidden_state.mean(dim=1)
            
            if request.normalize:
                embeddings = torch.nn.functional.normalize(embeddings, p=2, dim=1)
            
            embeddings = embeddings.cpu().numpy().tolist()
        
        dimension = len(embeddings[0]) if embeddings else 0
        
        logger.info(f"Generated {len(embeddings)} embeddings with dimension {dimension}")
        
        return EmbeddingResponse(
            embeddings=embeddings,
            dimension=dimension,
            model=_model_name
        )
    except Exception as e:
        logger.error(f"Embedding error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Embedding failed: {str(e)}")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "BGE Embedding Service",
        "version": "1.0.0",
        "model": _model_name,
        "endpoints": {
            "health": "/health",
            "embed": "/embed"
        }
    }

