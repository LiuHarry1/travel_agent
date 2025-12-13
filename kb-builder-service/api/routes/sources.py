"""Source file management API routes."""
from pathlib import Path
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from typing import List

from processors.stores import MilvusVectorStore
from config.settings import get_settings
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1/collections", tags=["sources"])


def get_vector_store(database: str = None) -> MilvusVectorStore:
    """Dependency to get vector store."""
    settings = get_settings()
    db_name = database or settings.milvus_database
    return MilvusVectorStore(
        host=settings.milvus_host,
        port=settings.milvus_port,
        user=settings.milvus_user,
        password=settings.milvus_password,
        database=db_name
    )


def get_database_from_query(database: str = None) -> str:
    """Get database name from query parameter or default."""
    if database:
        return database
    settings = get_settings()
    return settings.milvus_database


def resolve_file_path(file_path_str: str, static_dir: Path) -> Path:
    """
    Resolve file path from string (handles relative and absolute paths).
    
    Args:
        file_path_str: File path string from collection
        static_dir: Static directory path
    
    Returns:
        Resolved Path object
    """
    if Path(file_path_str).is_absolute():
        return Path(file_path_str)
    
    # Try relative to static_dir
    file_path = static_dir / file_path_str
    if file_path.exists():
        return file_path
    
    # Try as path from markdowns_dir
    markdowns_dir = static_dir / "markdowns"
    if "markdowns" in file_path_str.replace("\\", "/").split("/"):
        path_parts = file_path_str.replace("\\", "/").split("/")
        markdowns_index = path_parts.index("markdowns")
        filename = "/".join(path_parts[markdowns_index + 1:])
        file_path = markdowns_dir / filename
        if file_path.exists():
            return file_path
    
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
    
    return file_path


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
            file_path = resolve_file_path(file_path_str, static_dir)
        
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


@router.get("/{collection_name}/sources/{document_id}/chunks/{chunk_id}/context")
async def get_chunk_context(
    collection_name: str,
    document_id: str,
    chunk_id: str,
    context_before: int = Query(5000, ge=0, le=50000, description="Characters before chunk"),
    context_after: int = Query(5000, ge=0, le=50000, description="Characters after chunk"),
    vector_store: MilvusVectorStore = Depends(get_vector_store)
):
    """
    Get chunk with surrounding context for highlighting.
    Only loads the chunk and its context, not the entire document.
    Optimized for large documents.
    """
    from pathlib import Path
    from config.settings import get_settings
    import json
    
    try:
        settings = get_settings()
        static_dir = Path(settings.static_dir)
        
        # 1. Get chunk information from vector store
        vector_store._connect()
        from pymilvus import Collection
        
        collection = Collection(collection_name, using=vector_store.alias)
        collection.load()
        
        # Check schema to determine available fields
        schema = collection.schema
        has_chunk_id_field = any(field.name == "chunk_id" for field in schema.fields)
        has_file_path_field = any(field.name == "file_path" for field in schema.fields)
        
        # Unified approach: always use id field for query if chunk_id is numeric
        # This works for both old collections (no chunk_id field) and new collections
        try:
            # Try to parse as integer - if it's a number, use id field
            chunk_id_int = int(chunk_id)
            expr = f'id == {chunk_id_int}'
            logger.info(f"Querying chunk by id: {chunk_id_int} (unified approach)")
        except (ValueError, TypeError):
            # If not a number, check if collection has chunk_id field
            if has_chunk_id_field:
                escaped_chunk_id = chunk_id.replace('"', '\\"')
                expr = f'chunk_id == "{escaped_chunk_id}"'
                logger.info(f"Querying chunk by chunk_id field: {escaped_chunk_id}")
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid chunk_id format: {chunk_id}. Expected integer for collections without chunk_id field."
                )
        
        # Build output_fields based on available schema fields
        output_fields = ["id", "text", "document_id"]
        if has_chunk_id_field:
            output_fields.append("chunk_id")
        if has_file_path_field:
            output_fields.append("file_path")
        # metadata should always be available, but check to be safe
        has_metadata_field = any(field.name == "metadata" for field in schema.fields)
        if has_metadata_field:
            output_fields.append("metadata")
        
        results = collection.query(
            expr=expr,
            output_fields=output_fields,
            limit=1
        )
        
        if not results:
            raise HTTPException(
                status_code=404,
                detail=f"Chunk not found: {chunk_id}"
            )
        
        result = results[0]
        
        # Parse metadata and location
        metadata_str = result.get("metadata", "{}")
        if isinstance(metadata_str, str):
            metadata = json.loads(metadata_str)
        else:
            metadata = metadata_str
        
        location = metadata.get("location", {})
        start_char = location.get("start_char", 0)
        end_char = location.get("end_char", 0)
        
        # 2. Get file path - prefer markdown_file_path if available
        # First try to get markdown_file_path from metadata
        markdown_file_path_str = metadata.get("markdown_file_path")
        
        if not markdown_file_path_str:
            # Fallback: query by document_id to get markdown_file_path
            escaped_doc_id = document_id.replace('"', '\\"')
            expr = f'document_id == "{escaped_doc_id}"'
            file_results = collection.query(
                expr=expr,
                output_fields=["metadata"],
                limit=1
            )
            if file_results:
                file_metadata_str = file_results[0].get("metadata", "{}")
                if isinstance(file_metadata_str, str):
                    file_metadata = json.loads(file_metadata_str)
                else:
                    file_metadata = file_metadata_str
                markdown_file_path_str = file_metadata.get("markdown_file_path")
        
        # If still no markdown file, fallback to original file_path
        if not markdown_file_path_str:
            file_path_str = result.get("file_path")
            if not file_path_str:
                # Fallback: query by document_id
                escaped_doc_id = document_id.replace('"', '\\"')
                expr = f'document_id == "{escaped_doc_id}"'
                file_results = collection.query(
                    expr=expr,
                    output_fields=["file_path"],
                    limit=1
                )
                if file_results:
                    file_path_str = file_results[0].get("file_path")
            
            if not file_path_str:
                raise HTTPException(
                    status_code=404,
                    detail=f"File path not found for document: {document_id}"
                )
            
            # Resolve original file path
            file_path = resolve_file_path(file_path_str, static_dir)
        else:
            # Use markdown file path
            file_path = resolve_file_path(markdown_file_path_str, static_dir)
        
        if not file_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"Source file not found: {file_path}"
            )
        
        # 3. Read only the context window (not the entire file)
        # For very large files, we can use file seeking
        file_size = file_path.stat().st_size
        
        # Calculate context window boundaries
        context_start = max(0, start_char - context_before)
        
        # For large files (>10MB), use memory-mapped file or chunked reading
        # For smaller files, read entire file for accuracy
        if file_size > 10 * 1024 * 1024:  # 10MB
            # For large files, read in chunks to avoid loading entire file
            # Read a buffer around the target position
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                # Read from beginning but only keep the context window
                # This is still more efficient than loading entire file into memory
                if context_start > 0:
                    # Skip to context_start (read and discard)
                    # For very large files, this might be slow, but necessary for accuracy
                    f.read(context_start)
                
                # Read context window
                read_size = context_before + (end_char - start_char) + context_after
                context_content = f.read(read_size)
            
            # For large files, we estimate total length
            # Try to get actual character count by reading file in chunks (optional optimization)
            total_length = file_size  # Approximate
            context_end = context_start + len(context_content)
            has_more_before = context_start > 0
            has_more_after = True  # Assume there's more (conservative)
        else:
            # For smaller files, read entire file (faster for small files)
            full_content = file_path.read_text(encoding='utf-8')
            content_length = len(full_content)
            
            # Calculate context window
            context_end = min(content_length, end_char + context_after)
            
            # Extract context
            context_content = full_content[context_start:context_end]
            
            # Get total file length for metadata
            total_length = content_length
            has_more_before = context_start > 0
            has_more_after = context_end < total_length
        
        # Adjust chunk positions relative to context window
        chunk_start_in_context = start_char - context_start
        chunk_end_in_context = end_char - context_start
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "chunk": {
                    "id": result.get("id"),
                    "chunk_id": result.get("chunk_id"),
                    "text": result.get("text", ""),
                    "document_id": result.get("document_id"),
                    "location": location,
                },
                "context": {
                    "content": context_content,
                    "context_start": context_start,  # Absolute position in full document
                    "context_end": context_start + len(context_content),
                    "chunk_start": chunk_start_in_context,  # Relative position in context
                    "chunk_end": chunk_end_in_context,
                    "has_more_before": has_more_before,
                    "has_more_after": has_more_after,
                    "total_length": total_length
                }
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get chunk context: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get chunk context: {str(e)}"
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

