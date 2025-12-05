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


@router.get("/{collection_name}/sources/{document_id}/file")
async def get_source_file_url(
    collection_name: str,
    document_id: str,
    vector_store: MilvusVectorStore = Depends(get_vector_store)
):
    """Get the URL to view a source file."""
    from pathlib import Path
    from config.settings import get_settings
    
    try:
        settings = get_settings()
        static_dir = Path(settings.static_dir)
        
        # Get file_path from the collection
        vector_store._connect()
        from pymilvus import Collection
        collection = Collection(collection_name, using=vector_store.alias)
        collection.load()
        
        # Query for a chunk with this document_id to get file_path
        escaped_doc_id = document_id.replace('"', '\\"')
        expr = f'document_id == "{escaped_doc_id}"'
        results = collection.query(
            expr=expr,
            output_fields=["file_path"],
            limit=1
        )
        
        if not results or not results[0].get("file_path"):
            raise HTTPException(
                status_code=404,
                detail=f"Source file not found: {document_id}. No file_path found in collection."
            )
        
        file_path_str = results[0]["file_path"]
        logger.info(f"Found file_path from collection: {file_path_str}")
        
        # Use file_path from collection
        if file_path_str:
            # file_path_str might be relative like "sources/7a0b3112_面试经验.pdf"
            # or absolute path
            if Path(file_path_str).is_absolute():
                file_path = Path(file_path_str)
            else:
                # Try relative to static_dir
                file_path = static_dir / file_path_str
                if not file_path.exists():
                    # Try as path from sources_dir
                    sources_dir = static_dir / "sources"
                    if "sources" in file_path_str or file_path_str.startswith("sources/"):
                        path_parts = file_path_str.replace("\\", "/").split("/")
                        if "sources" in path_parts:
                            sources_index = path_parts.index("sources")
                            filename = "/".join(path_parts[sources_index + 1:])
                            file_path = sources_dir / filename
                        else:
                            file_path = sources_dir / file_path_str
                    else:
                        file_path = sources_dir / file_path_str
        
        if not file_path or not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Source file not found: {document_id}. File path from collection: {file_path_str}, resolved path: {file_path}"
            )
        
        # Build the URL
        base_url = settings.static_base_url.rstrip("/") if settings.static_base_url else ""
        relative_path = file_path.relative_to(static_dir)
        file_url = f"{base_url}/static/{relative_path.as_posix()}" if base_url else f"/static/{relative_path.as_posix()}"
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "collection_name": collection_name,
                "document_id": document_id,
                "file_url": file_url,
                "filename": file_path.name,
                "file_path": str(file_path)
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get source file URL: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get source file URL: {str(e)}"
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

