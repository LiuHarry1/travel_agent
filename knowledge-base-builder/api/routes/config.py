"""Configuration and testing API routes."""
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import logging

from processors.stores import MilvusVectorStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/config", tags=["config"])


class MilvusConfigRequest(BaseModel):
    """Milvus configuration request."""
    host: str
    port: int
    user: Optional[str] = None
    password: Optional[str] = None


@router.post("/test-milvus")
async def test_milvus_connection(config: MilvusConfigRequest):
    """Test Milvus connection with provided configuration."""
    try:
        vector_store = MilvusVectorStore(
            host=config.host,
            port=config.port,
            user=config.user or "",
            password=config.password or ""
        )
        
        # Try to connect
        from pymilvus import connections
        connections.connect(
            alias="test",
            host=config.host,
            port=config.port,
            user=config.user if config.user else None,
            password=config.password if config.password else None,
        )
        
        # Try to list collections to verify connection
        from pymilvus import utility
        collections = utility.list_collections()
        
        result = {
            "success": True,
            "message": "Connection successful",
            "collections_count": len(collections)
        }
        return JSONResponse(status_code=200, content=result)
    except Exception as e:
        logger.error(f"Milvus connection test failed: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=200,
            content={
                "success": False,
                "message": f"Connection failed: {str(e)}"
            }
        )
    finally:
        try:
            from pymilvus import connections
            connections.disconnect("test")
        except:
            pass


@router.get("/defaults")
async def get_default_config():
    """Get default configuration."""
    from config.settings import get_settings
    settings = get_settings()
    
    return JSONResponse(
        status_code=200,
        content={
            "milvus": {
                "host": settings.milvus_host,
                "port": settings.milvus_port,
                "user": settings.milvus_user,
                "password": settings.milvus_password
            },
            "embedding": {
                "provider": settings.default_embedding_provider,
                "model": settings.default_embedding_model
            },
            "chunking": {
                "chunk_size": settings.default_chunk_size,
                "chunk_overlap": settings.default_chunk_overlap
            },
            "collection": {
                "default_name": settings.default_collection_name
            }
        }
    )

