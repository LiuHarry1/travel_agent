"""Indexing API routes."""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from typing import Optional, List
import tempfile
import os
from pathlib import Path
import logging

from services.indexing_service import IndexingService
from models.document import DocumentType
from processors.stores import MilvusVectorStore
from config.settings import get_settings
from utils.exceptions import IndexingError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1", tags=["indexing"])


def get_indexing_service() -> IndexingService:
    """Dependency to get indexing service."""
    settings = get_settings()
    vector_store = MilvusVectorStore(
        host=settings.milvus_host,
        port=settings.milvus_port,
        user=settings.milvus_user,
        password=settings.milvus_password
    )
    return IndexingService(
        vector_store=vector_store,
        chunk_size=settings.default_chunk_size,
        chunk_overlap=settings.default_chunk_overlap
    )


def detect_document_type(filename: str) -> DocumentType:
    """Detect document type from filename."""
    ext = Path(filename).suffix.lower()
    type_map = {
        ".md": DocumentType.MARKDOWN,
        ".markdown": DocumentType.MARKDOWN,
        ".pdf": DocumentType.PDF,
        ".docx": DocumentType.DOCX,
        ".doc": DocumentType.DOCX,
        ".html": DocumentType.HTML,
        ".htm": DocumentType.HTML,
        ".txt": DocumentType.TXT,
    }
    return type_map.get(ext, DocumentType.TXT)


@router.post("/upload")
async def upload_and_index(
    file: UploadFile = File(...),
    collection_name: Optional[str] = Form(None),
    embedding_provider: Optional[str] = Form("qwen"),
    embedding_model: Optional[str] = Form(None),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
    service: IndexingService = Depends(get_indexing_service)
):
    """
    Upload a file and index it into knowledge base.
    
    Supports: .md, .pdf, .docx, .html, .txt
    """
    settings = get_settings()
    temp_path = None
    
    try:
        # Detect document type
        doc_type = detect_document_type(file.filename)
        
        # Save uploaded file temporarily
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_path = tmp.name
            
            # Index document
            result = service.index_document(
                source=temp_path,
                doc_type=doc_type,
                collection_name=collection_name or settings.default_collection_name,
                embedding_provider=embedding_provider or settings.default_embedding_provider,
                embedding_model=embedding_model,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                metadata={"original_filename": file.filename}
            )
            
            if result["success"]:
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "filename": file.filename,
                        "document_id": result["document_id"],
                        "chunks_indexed": result["chunks_indexed"],
                        "collection_name": result["collection_name"],
                        "message": result["message"]
                    }
                )
            else:
                raise HTTPException(status_code=400, detail=result["message"])
                
    except IndexingError as e:
        logger.error(f"Indexing error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
    finally:
        # Cleanup temp file
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


@router.post("/upload/batch")
async def upload_batch(
    files: List[UploadFile] = File(...),
    collection_name: Optional[str] = Form(None),
    embedding_provider: Optional[str] = Form("qwen"),
    service: IndexingService = Depends(get_indexing_service)
):
    """Upload and index multiple files."""
    settings = get_settings()
    results = []
    temp_paths = []
    
    try:
        for file in files:
            doc_type = detect_document_type(file.filename)
            
            # Save file temporarily
            suffix = Path(file.filename).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                content = await file.read()
                tmp.write(content)
                temp_paths.append(tmp.name)
                
                try:
                    result = service.index_document(
                        source=tmp.name,
                        doc_type=doc_type,
                        collection_name=collection_name or settings.default_collection_name,
                        embedding_provider=embedding_provider or settings.default_embedding_provider,
                        metadata={"original_filename": file.filename}
                    )
                    results.append({
                        "filename": file.filename,
                        "success": result["success"],
                        "chunks_indexed": result.get("chunks_indexed", 0),
                        "message": result.get("message", "")
                    })
                except Exception as e:
                    results.append({
                        "filename": file.filename,
                        "success": False,
                        "message": str(e)
                    })
        
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "total_files": len(files),
                "results": results
            }
        )
    finally:
        # Cleanup temp files
        for path in temp_paths:
            if os.path.exists(path):
                os.unlink(path)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "knowledge-base-builder"}

