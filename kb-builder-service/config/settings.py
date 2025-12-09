"""Configuration settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
from typing import List, Any, Dict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # Ignore extra fields in .env that are not in the model
        case_sensitive=False
    )
    
    # Milvus
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    milvus_user: str = ""
    milvus_password: str = ""
    milvus_database: str = "default"  # Milvus database name
    
    # Embedding
    default_embedding_provider: str = "openai"  # qwen, openai, bge, bge-en, bge-zh, nemotron, nvidia, snowflake
    default_embedding_model: str = "text-embedding-3-small"  # Model name based on provider
    
    # BGE API URLs
    bge_api_url: str = ""  # General BGE embedding service API URL (e.g., http://localhost:8001)
    bge_en_api_url: str = ""  # English BGE API URL (e.g., http://10.150.115.110:6000)
    bge_zh_api_url: str = ""  # Chinese BGE API URL (e.g., http://10.150.115.110:6001)
    
    # Other embedding API URLs
    nemotron_api_url: str = ""  # NVIDIA Nemotron API URL (e.g., http://10.150.115.110:6002/embed)
    snowflake_api_url: str = ""  # Snowflake Arctic API URL (e.g., http://10.150.115.110:6003/embed)
    
    # Chunking
    default_chunk_size: int = 1000
    default_chunk_overlap: int = 200
    
    # Collection
    default_collection_name: str = "knowledge_base"
    
    # Static files directory
    static_dir: str = "static"  # Directory for storing sources and images
    static_base_url: str = ""  # Base URL for static files (e.g., http://localhost:8001). If empty, uses relative paths.
    
    # CORS - stored as string to avoid JSON parsing issues
    # Use cors_origins_str as the field name to avoid pydantic-settings trying to parse it as JSON
    cors_origins_str: str = "*"
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from string (comma-separated) or return default."""
        if not self.cors_origins_str or not self.cors_origins_str.strip():
            return ["*"]
        # Handle "*" as special case
        if self.cors_origins_str.strip() == "*":
            return ["*"]
        # Split by comma and strip whitespace
        origins = [origin.strip() for origin in self.cors_origins_str.split(",") if origin.strip()]
        return origins if origins else ["*"]
    
    @model_validator(mode='before')
    @classmethod
    def parse_cors_origins_from_env(cls, data: Any) -> Dict[str, Any]:
        """Parse CORS origins from environment variable before validation."""
        if isinstance(data, dict):
            # Handle CORS_ORIGINS from environment - map to cors_origins_str
            if 'CORS_ORIGINS' in data:
                cors_value = data['CORS_ORIGINS']
                if isinstance(cors_value, list):
                    data['cors_origins_str'] = ','.join(str(v) for v in cors_value)
                elif isinstance(cors_value, str):
                    data['cors_origins_str'] = cors_value
                else:
                    data['cors_origins_str'] = "*"
                # Remove the original key to avoid conflicts
                del data['CORS_ORIGINS']
            elif 'cors_origins' in data:
                cors_value = data['cors_origins']
                if isinstance(cors_value, list):
                    data['cors_origins_str'] = ','.join(str(v) for v in cors_value)
                elif isinstance(cors_value, str):
                    data['cors_origins_str'] = cors_value
                else:
                    data['cors_origins_str'] = "*"
                # Remove the original key to avoid conflicts
                del data['cors_origins']
        return data
    
    # API Keys (optional, can be set via environment variables)
    dashscope_api_key: str = ""  # For Qwen/DashScope (also accepts QWEN_API_KEY)
    qwen_api_key: str = ""  # Alternative name for DashScope API key
    openai_api_key: str = ""  # For OpenAI
    openai_base_url: str = ""  # Optional custom base URL for OpenAI-compatible APIs


_settings: Settings = None


def get_settings() -> Settings:
    """Get settings instance."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings

