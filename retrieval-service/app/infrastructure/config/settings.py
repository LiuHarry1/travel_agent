"""Application configuration."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List
import os


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore"  # Ignore extra fields from .env file
    )
    
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
    
    # BGE API URLs (if using BGE via API)
    bge_api_url: str = "http://localhost:8001"
    bge_en_api_url: str = "http://10.150.10.120:6000"
    bge_zh_api_url: str = "http://10.150.10.120:6001"
    
    # Other embedding model API URLs
    nemotron_api_url: str = "http://10.150.10.120:6002/embed"
    snowflake_api_url: str = "http://10.150.10.120:6003/embed"
    
    # Qwen LLM settings
    qwen_api_key: str = ""
    qwen_base_url: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    qwen_model: str = "qwen-plus"
    
    # Retrieval settings
    top_k_per_model: int = 10  # Number of results per embedding model
    rerank_top_k: int = 20  # Number of results to keep after rerank
    final_top_k: int = 10  # Final number of results after LLM filtering
    
    # CORS - Allow all localhost ports for development
    cors_origins: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:8080",
    ]


settings = Settings()



