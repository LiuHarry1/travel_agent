"""Configuration settings."""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application settings."""
    
    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_user: str = ""
    milvus_password: str = ""
    
    # Embedding
    default_embedding_provider: str = "qwen"
    default_embedding_model: str = "text-embedding-v2"
    
    # Chunking
    default_chunk_size: int = 1000
    default_chunk_overlap: int = 200
    
    # Collection
    default_collection_name: str = "knowledge_base"
    
    # CORS
    cors_origins: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


_settings: Settings = None


def get_settings() -> Settings:
    """Get settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

