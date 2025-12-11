"""Indexing API routes."""
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form, Request
from fastapi.responses import JSONResponse, StreamingResponse
from typing import Optional, List, AsyncGenerator
import tempfile
import os
import json
import asyncio
from pathlib import Path
from services.indexing_service import IndexingService
from models.document import DocumentType
from processors.stores import MilvusVectorStore
from config.settings import get_settings
from utils.exceptions import IndexingError
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/v1", tags=["indexing"])


def get_indexing_service(database: str = None) -> IndexingService:
    """Dependency to get indexing service."""
    settings = get_settings()
    db_name = database or settings.milvus_database
    vector_store = MilvusVectorStore(
        host=settings.milvus_host,
        port=settings.milvus_port,
        user=settings.milvus_user,
        password=settings.milvus_password,
        database=db_name
    )
    return IndexingService(
        vector_store=vector_store,
        chunk_size=settings.default_chunk_size,
        chunk_overlap=settings.default_chunk_overlap
    )


def get_database_from_form(database: str = None) -> str:
    """Get database name from form parameter or default."""
    if database:
        return database
    settings = get_settings()
    return settings.milvus_database


def get_indexing_service_with_database(database: str = None) -> IndexingService:
    """Dependency to get indexing service with database parameter."""
    db_name = get_database_from_form(database)
    return get_indexing_service(db_name)


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
    service: IndexingService,
    bge_api_url: Optional[str] = None,
    base_url: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """Process file with progress updates."""
    document = None
    chunks = None
    
    try:
        # Stage 1: Uploading (already done, but notify)
        logger.info(f"Starting file processing: {filename}")
        yield send_progress("uploading", 10, "文件上传完成")
        await asyncio.sleep(0.1)
        
        # Stage 2: Parsing
        logger.info(f"Starting parsing stage for {filename}")
        yield send_progress("parsing", 20, "正在解析文件...")
        try:
            from processors.loaders import LoaderFactory
            from config.settings import get_settings
            settings = get_settings()
            # 优先使用传入的 base_url，否则使用配置的 static_base_url
            final_base_url = base_url or settings.static_base_url
            logger.info(f"Creating loader with static_dir={settings.static_dir}, base_url={final_base_url}")
            loader = LoaderFactory.create(
                doc_type, 
                static_dir=settings.static_dir,
                base_url=final_base_url
            )
            document = loader.load(file_path, metadata={"original_filename": filename})
            # document.source contains the saved_source_path (e.g., "static/sources/7a0b3112_面试经验.pdf")
            # We'll use original filename as document_id for display, but store the actual path in metadata
            saved_source_path = document.source  # This is the actual saved file path
            # Set document_id to original filename for display
            document.source = filename  # Use original filename as document_id
            # Store actual file path in metadata
            if hasattr(document, 'metadata') and document.metadata:
                document.metadata['file_path'] = saved_source_path
                document.metadata['original_filename'] = filename
            char_count = len(document.content)
            logger.info(f"Parsed document: {char_count} characters")
            yield send_progress("parsing", 80, f"解析中，已读取 {char_count} 个字符...", {
                "char_count": char_count
            })
            await asyncio.sleep(0.05)
            yield send_progress("parsing", 100, f"解析完成，共 {char_count} 个字符", {
                "char_count": char_count
            })
            await asyncio.sleep(0.05)
            logger.info(f"Parsing stage completed for {filename}")
        except Exception as e:
            logger.error(f"Parsing error: {str(e)}", exc_info=True)
            yield send_progress("error", 0, f"解析失败: {str(e)}", {
                "retryable": True,
                "error_type": type(e).__name__
            })
            return
        
        # Validate document was loaded
        if document is None:
            logger.error("Document is None after parsing")
            yield send_progress("error", 0, "解析失败: 文档为空", {
                "retryable": True,
                "error_type": "DocumentError"
            })
            return
        
        # Stage 3: Chunking
        logger.info(f"Starting chunking stage for {filename}")
        yield send_progress("chunking", 10, "正在分块...")
        await asyncio.sleep(0.05)  # Give frontend time to update UI
        
        try:
            from processors.chunkers import RecursiveChunker
            chunk_size_val = chunk_size or service.chunk_size
            chunk_overlap_val = chunk_overlap or service.chunk_overlap
            logger.info(f"Creating chunker with chunk_size={chunk_size_val}, chunk_overlap={chunk_overlap_val}")
            
            chunker = RecursiveChunker(
                chunk_size=chunk_size_val,
                chunk_overlap=chunk_overlap_val
            )
            
            logger.info(f"Starting chunk operation on document with {len(document.content)} characters")
            chunks = chunker.chunk(document)
            logger.info(f"Chunking completed: created {len(chunks)} chunks")
            
            yield send_progress("chunking", 90, f"分块中，已创建 {len(chunks)} 个 chunks...", {
                "chunks_count": len(chunks)
            })
            await asyncio.sleep(0.05)
            yield send_progress("chunking", 100, f"分块完成，共创建 {len(chunks)} 个 chunks", {
                "chunks_count": len(chunks)
            })
            await asyncio.sleep(0.05)
            logger.info(f"Chunking stage completed for {filename}")
        except Exception as e:
            logger.error(f"Chunking error: {str(e)}", exc_info=True)
            yield send_progress("error", 0, f"分块失败: {str(e)}", {
                "retryable": True,
                "error_type": type(e).__name__
            })
            return
        
        if not chunks:
            yield send_progress("error", 0, "未生成任何 chunks", {
                "retryable": False
            })
            return
        
        # Stage 4: Embedding
        logger.info(f"Starting embedding stage for {filename} with {len(chunks)} chunks")
        yield send_progress("embedding", 10, "生成嵌入向量中...")
        await asyncio.sleep(0.05)
        
        try:
            from processors.embedders import EmbedderFactory
            logger.info(f"Creating embedder: provider={embedding_provider}, model={embedding_model}, bge_api_url={bge_api_url}")
            embedder_kwargs = {}
            if embedding_provider.lower() == "bge" and bge_api_url:
                embedder_kwargs["api_url"] = bge_api_url
            embedder = EmbedderFactory.create(
                provider=embedding_provider,
                model=embedding_model,
                **embedder_kwargs
            )
            texts = [chunk.text for chunk in chunks]
            logger.info(f"Prepared {len(texts)} texts for embedding")
            
            # Generate embeddings in batches for progress tracking
            batch_size = 10
            embeddings = []
            total_batches = (len(texts) + batch_size - 1) // batch_size
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_embeddings = embedder.embed(batch)
                embeddings.extend(batch_embeddings)
                progress = 10 + int((len(embeddings) / len(texts)) * 80)
                yield send_progress("embedding", progress, f"已生成 {len(embeddings)}/{len(texts)} 个嵌入向量", {
                    "embeddings_generated": len(embeddings),
                    "embeddings_total": len(texts)
                })
                await asyncio.sleep(0.05)
            
            # Attach embeddings
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding
            
            yield send_progress("embedding", 100, f"嵌入向量生成完成，共 {len(embeddings)} 个", {
                "embeddings_generated": len(embeddings),
                "embeddings_total": len(texts)
            })
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Embedding error: {str(e)}", exc_info=True)
            yield send_progress("error", 0, f"生成嵌入向量失败: {str(e)}", {
                "retryable": True,
                "error_type": type(e).__name__
            })
            return
        
        # Stage 5: Indexing
        logger.info(f"Starting indexing stage for {filename} to collection {collection_name}")
        yield send_progress("indexing", 10, "索引到 Milvus 中...")
        await asyncio.sleep(0.05)
        
        try:
            logger.info(f"Indexing {len(chunks)} chunks to Milvus collection: {collection_name}")
            chunks_indexed = service.vector_store.index(chunks, collection_name)
            logger.info(f"Indexing completed: {chunks_indexed} chunks indexed")
            yield send_progress("indexing", 90, f"索引中，已索引 {chunks_indexed} 个 chunks...", {
                "chunks_indexed": chunks_indexed
            })
            await asyncio.sleep(0.05)
            yield send_progress("indexing", 100, f"索引完成，共索引 {chunks_indexed} 个 chunks", {
                "chunks_indexed": chunks_indexed
            })
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Indexing error: {str(e)}", exc_info=True)
            yield send_progress("error", 0, f"索引失败: {str(e)}", {
                "retryable": True,
                "error_type": type(e).__name__
            })
            return
        
        # Stage 6: Completed
        logger.info(f"Processing completed for {filename}: {chunks_indexed} chunks indexed to {collection_name}")
        # Include document structure in completion message if available
        completion_data = {
            "chunks_indexed": chunks_indexed,
            "collection_name": collection_name,
            "filename": filename
        }
        if document and document.structure:
            completion_data["structure"] = document.structure.to_dict()
        yield send_progress("completed", 100, f"成功索引 {chunks_indexed} 个 chunks 到 {collection_name}", completion_data)
        await asyncio.sleep(0.1)  # Give frontend time to process final update
        
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
    request: Request,
    file: UploadFile = File(...),
    collection_name: Optional[str] = Form(None),
    embedding_provider: Optional[str] = Form(None),
    embedding_model: Optional[str] = Form(None),
    bge_api_url: Optional[str] = Form(None),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
    database: Optional[str] = Form(None),
    service: IndexingService = Depends(get_indexing_service_with_database)
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
        bge_api_url = bge_api_url if bge_api_url and bge_api_url.strip() else None
        
        # 从请求中获取 hostname 和端口，构建 base_url
        # 如果配置中有 static_base_url，优先使用配置；否则从请求中获取
        base_url = settings.static_base_url
        if not base_url:
            # 从请求中获取 hostname 和端口
            # Host header 通常已经包含端口号（如果有非标准端口）
            host = request.headers.get("host")
            if not host:
                # 如果 Host header 不存在，从 URL 中获取
                host = request.url.hostname
                port = request.url.port
                if port:
                    host = f"{host}:{port}"
            scheme = request.url.scheme
            base_url = f"{scheme}://{host}"
            logger.info(f"Using request-based base_url: {base_url}")
        
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
                service,
                bge_api_url,
                base_url
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
    request: Request,
    file: UploadFile = File(...),
    collection_name: Optional[str] = Form(None),
    embedding_provider: Optional[str] = Form("qwen"),
    embedding_model: Optional[str] = Form(None),
    bge_api_url: Optional[str] = Form(None),
    chunk_size: Optional[int] = Form(None),
    chunk_overlap: Optional[int] = Form(None),
    database: Optional[str] = Form(None),
    service: IndexingService = Depends(get_indexing_service_with_database)
):
    """
    Upload a file and index it into knowledge base.
    
    Supports: .md, .pdf, .docx, .html, .txt
    """
    settings = get_settings()
    temp_path = None
    
    try:
        # 从请求中获取 hostname 和端口，构建 base_url
        # 如果配置中有 static_base_url，优先使用配置；否则从请求中获取
        base_url = settings.static_base_url
        if not base_url:
            # 从请求中获取 hostname 和端口
            # Host header 通常已经包含端口号（如果有非标准端口）
            host = request.headers.get("host")
            if not host:
                # 如果 Host header 不存在，从 URL 中获取
                host = request.url.hostname
                port = request.url.port
                if port:
                    host = f"{host}:{port}"
            scheme = request.url.scheme
            base_url = f"{scheme}://{host}"
            logger.info(f"Using request-based base_url: {base_url}")
        
        # Detect document type
        doc_type = detect_document_type(file.filename)
        
        # Save uploaded file temporarily
        suffix = Path(file.filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            temp_path = tmp.name
            
            # Index document
            index_kwargs = {
                "source": temp_path,
                "doc_type": doc_type,
                "collection_name": collection_name or settings.default_collection_name,
                "embedding_provider": embedding_provider or settings.default_embedding_provider,
                "embedding_model": embedding_model,
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
                "base_url": base_url,
                "metadata": {"original_filename": file.filename}
            }
            if embedding_provider and embedding_provider.lower() == "bge" and bge_api_url:
                index_kwargs["bge_api_url"] = bge_api_url
            result = service.index_document(**index_kwargs)
            
            if result["success"]:
                return JSONResponse(
                    status_code=200,
                    content={
                        "success": True,
                        "filename": file.filename,
                        "document_id": result["document_id"],
                        "chunks_indexed": result["chunks_indexed"],
                        "collection_name": result["collection_name"],
                        "structure": result.get("structure"),  # Include document structure
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
    request: Request,
    files: List[UploadFile] = File(...),
    collection_name: Optional[str] = Form(None),
    embedding_provider: Optional[str] = Form("qwen"),
    embedding_model: Optional[str] = Form(None),
    bge_api_url: Optional[str] = Form(None),
    database: Optional[str] = Form(None),
    service: IndexingService = Depends(get_indexing_service_with_database)
):
    """Upload and index multiple files."""
    settings = get_settings()
    
    # 从请求中获取 hostname 和端口，构建 base_url
    # 如果配置中有 static_base_url，优先使用配置；否则从请求中获取
    base_url = settings.static_base_url
    if not base_url:
        # 从请求中获取 hostname 和端口
        host = request.headers.get("host") or request.url.hostname
        scheme = request.url.scheme
        port = request.url.port
        if port:
            base_url = f"{scheme}://{host}:{port}"
        else:
            base_url = f"{scheme}://{host}"
        logger.info(f"Using request-based base_url: {base_url}")
    
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
                    index_kwargs = {
                        "source": tmp.name,
                        "doc_type": doc_type,
                        "collection_name": collection_name or settings.default_collection_name,
                        "embedding_provider": embedding_provider or settings.default_embedding_provider,
                        "base_url": base_url,
                        "metadata": {"original_filename": file.filename}
                    }
                    if embedding_model:
                        index_kwargs["embedding_model"] = embedding_model
                    if embedding_provider and embedding_provider.lower() == "bge" and bge_api_url:
                        index_kwargs["bge_api_url"] = bge_api_url
                    result = service.index_document(**index_kwargs)
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
    return {"status": "ok", "service": "kb-builder-service"}
