"""Indexing API routes."""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional, List, AsyncGenerator
import tempfile
import os
import json
import asyncio
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


def send_progress(stage: str, progress: int, message: str, data: dict = None) -> str:
    """Format progress message for SSE."""
    payload = {
        "stage": stage,
        "progress": progress,
        "message": message,
        **(data or {})
    }
    return f"data: {json.dumps(payload)}\n\n"


async def process_file_with_progress(
    file_path: str,
    filename: str,
    doc_type: DocumentType,
    collection_name: str,
    embedding_provider: str,
    embedding_model: Optional[str],
    chunk_size: Optional[int],
    chunk_overlap: Optional[int],
    service: IndexingService
) -> AsyncGenerator[str, None]:
    """Process file with progress updates."""
    try:
        # Stage 1: Uploading (already done, but notify)
        yield send_progress("uploading", 10, "文件上传完成")
        await asyncio.sleep(0.1)
        
        # Stage 2: Parsing
        yield send_progress("parsing", 20, "正在解析文件...")
        from processors.loaders import LoaderFactory
        loader = LoaderFactory.create(doc_type)
        document = loader.load(file_path, metadata={"original_filename": filename})
        char_count = len(document.content)
        yield send_progress("parsing", 40, f"解析完成，共 {char_count} 个字符", {
            "char_count": char_count
        })
        await asyncio.sleep(0.05)
        
        # Stage 3: Chunking
        yield send_progress("chunking", 50, "正在分块...")
        from processors.chunkers import RecursiveChunker
        chunker = RecursiveChunker(
            chunk_size=chunk_size or service.chunk_size,
            chunk_overlap=chunk_overlap or service.chunk_overlap
        )
        chunks = chunker.chunk(document)
        yield send_progress("chunking", 70, f"创建了 {len(chunks)} 个 chunks", {
            "chunks_count": len(chunks)
        })
        await asyncio.sleep(0.05)
        
        if not chunks:
            yield send_progress("error", 0, "未生成任何 chunks", {
                "retryable": False
            })
            return
        
        # Stage 4: Embedding
        yield send_progress("embedding", 75, "生成嵌入向量中...")
        from processors.embedders import EmbedderFactory
        embedder = EmbedderFactory.create(
            provider=embedding_provider,
            model=embedding_model
        )
        texts = [chunk.text for chunk in chunks]
        
        # Generate embeddings in batches for progress tracking
        batch_size = 10
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch_embeddings = embedder.embed(batch)
            embeddings.extend(batch_embeddings)
            progress = 75 + int((i + len(batch)) / len(texts) * 10)
            yield send_progress("embedding", progress, f"已生成 {len(embeddings)}/{len(texts)} 个嵌入向量", {
                "embeddings_generated": len(embeddings),
                "embeddings_total": len(texts)
            })
            await asyncio.sleep(0.05)
        
        # Attach embeddings
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        
        yield send_progress("embedding", 90, "嵌入向量生成完成")
        await asyncio.sleep(0.05)
        
        # Stage 5: Indexing
        yield send_progress("indexing", 92, "索引到 Milvus 中...")
        chunks_indexed = service.vector_store.index(chunks, collection_name)
        yield send_progress("indexing", 98, f"已索引 {chunks_indexed} 个 chunks", {
            "chunks_indexed": chunks_indexed
        })
        await asyncio.sleep(0.05)
        
        # Stage 6: Completed
        yield send_progress("completed", 100, f"成功索引 {chunks_indexed} 个 chunks 到 {collection_name}", {
            "chunks_indexed": chunks_indexed,
            "collection_name": collection_name,
            "filename": filename
        })
        
    except IndexingError as e:
        logger.error(f"Indexing error: {str(e)}", exc_info=True)
        yield send_progress("error", 0, f"索引失败: {str(e)}", {
            "retryable": True,
            "error_type": "IndexingError"
        })
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        yield send_progress("error", 0, f"处理失败: {str(e)}", {
            "retryable": True,
            "error_type": type(e).__name__
        })


@router.post("/upload/stream")
async def upload_and_index_stream(
    file: UploadFile = File(...),
    collection_name: Optional[str] = Form(None),
    embedding_provider: Optional[str] = Form(None),
    embedding_model: Optional[str] = Form(None),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
    service: IndexingService = Depends(get_indexing_service)
):
    """
    Upload and index file with real-time progress updates via Server-Sent Events.
    """
    settings = get_settings()
    temp_path = None
    
    try:
        # Log received parameters for debugging
        logger.debug(f"Received upload request: filename={file.filename}, "
                    f"collection_name={collection_name}, "
                    f"embedding_provider={embedding_provider}, "
                    f"chunk_size={chunk_size}, chunk_overlap={chunk_overlap}")
        
        # Validate filename
        if not file.filename:
            raise HTTPException(status_code=422, detail="Filename is required")
        
        # Normalize empty strings to None for optional fields
        collection_name = collection_name if collection_name and collection_name.strip() else None
        embedding_provider = embedding_provider if embedding_provider and embedding_provider.strip() else None
        embedding_model = embedding_model if embedding_model and embedding_model.strip() else None
        
        # Detect document type
        doc_type = detect_document_type(file.filename)
        
        # Save uploaded file temporarily
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_path = tmp.name
        
        # Process with progress updates
        async def generate():
            async for progress in process_file_with_progress(
                temp_path,
                file.filename or "unknown",
                doc_type,
                collection_name or settings.default_collection_name,
                embedding_provider or settings.default_embedding_provider,
                embedding_model,
                chunk_size,
                chunk_overlap,
                service
            ):
                yield progress
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
        
    except Exception as e:
        logger.error(f"Upload stream error: {str(e)}", exc_info=True)
        async def error_stream():
            yield send_progress("error", 0, f"上传失败: {str(e)}", {
                "retryable": True,
                "error_type": type(e).__name__
            })
        return StreamingResponse(error_stream(), media_type="text/event-stream")
    finally:
        # Cleanup temp file after a delay (to allow processing)
        if temp_path:
            async def cleanup():
                await asyncio.sleep(5)  # Wait 5 seconds before cleanup
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
            asyncio.create_task(cleanup())


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
        raise HTTPException(
            status_code=500,
            detail={
                "error": str(e),
                "error_type": "IndexingError",
                "retryable": True
            }
        )
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Internal server error: {str(e)}",
                "error_type": type(e).__name__,
                "retryable": True
            }
        )
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
                        "message": str(e),
                        "error_type": type(e).__name__,
                        "retryable": True
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
