"""Application configuration."""
from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    """Application settings."""
    
    # Milvus settings
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_user: str = ""
    milvus_password: str = ""
    milvus_collection_name: str = "knowledge_base"
    
    # Embedding models configuration
    # Format: "provider:model_name" or just "provider" (uses default model)
    # Can be set via env var as comma-separated string
    embedding_models: List[str] = [
        "qwen:text-embedding-v2",
        "bge:BAAI/bge-large-en-v1.5",
        "openai:text-embedding-3-small"
    ]
    
    def __init__(self, **kwargs):
        """Initialize settings with environment variable parsing."""
        super().__init__(**kwargs)
        # Parse embedding_models from env if provided as comma-separated string
        env_models = os.getenv("EMBEDDING_MODELS")
        if env_models:
            self.embedding_models = [s.strip() for s in env_models.split(",") if s.strip()]
    
    # BGE API URL (if using BGE via API)
    bge_api_url: str = "http://localhost:8001"
    
    # Qwen LLM settings
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-plus"
    
    # Retrieval settings
    top_k_per_model: int = 10  # Number of results per embedding model
    rerank_top_k: int = 20  # Number of results to keep after rerank
    final_top_k: int = 10  # Final number of results after LLM filtering
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"]
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

