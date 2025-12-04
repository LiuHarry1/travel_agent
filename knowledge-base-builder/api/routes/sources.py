"""Source file management API routes."""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import List

from processors.stores import MilvusVectorStore
from config.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/collections", tags=["sources"])


def get_vector_store() -> MilvusVectorStore:
    """Dependency to get vector store."""
    settings = get_settings()
    return MilvusVectorStore(
        host=settings.milvus_host,
        port=settings.milvus_port,
        user=settings.milvus_user,
        password=settings.milvus_password
    )


@router.get("/{collection_name}/sources")
async def list_sources(
    collection_name: str,
    vector_store: MilvusVectorStore = Depends(get_vector_store)
):
    """List all source files in a collection."""
    try:
        sources = vector_store.list_sources(collection_name)
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "collection_name": collection_name,
                "sources": sources,
                "total": len(sources)
            }
        )
    except Exception as e:
        logger.error(f"Failed to list sources: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list sources: {str(e)}"
        )


@router.get("/{collection_name}/sources/{document_id}/chunks")
async def get_source_chunks(
    collection_name: str,
    document_id: str,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    vector_store: MilvusVectorStore = Depends(get_vector_store)
):
    """Get chunks for a specific source file with pagination."""
    try:
        result = vector_store.get_chunks_by_source(
            collection_name=collection_name,
            document_id=document_id,
            page=page,
            page_size=page_size
        )
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "collection_name": collection_name,
                "document_id": document_id,
                **result
            }
        )
    except Exception as e:
        logger.error(f"Failed to get chunks: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get chunks: {str(e)}"
        )


@router.delete("/{collection_name}/sources/{document_id}")
async def delete_source(
    collection_name: str,
    document_id: str,
    vector_store: MilvusVectorStore = Depends(get_vector_store)
):
    """Delete a source file and all its chunks."""
    try:
        deleted_count = vector_store.delete_source(collection_name, document_id)
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "collection_name": collection_name,
                "document_id": document_id,
                "chunks_deleted": deleted_count,
                "message": f"Deleted {deleted_count} chunks for source file"
            }
        )
    except Exception as e:
        logger.error(f"Failed to delete source: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete source: {str(e)}"
        )

