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
    base_url: Optional[str] = None,
    multi_granularity_chunk_sizes: Optional[List[int]] = None,
    multi_granularity_chunk_overlap: Optional[int] = None
) -> AsyncGenerator[str, None]:
    """Process file with progress updates."""
    document = None
    chunks = None
    
    try:
        # Stage 1: Uploading (already done, but notify)
        logger.info(f"Starting file processing: {filename}")
        yield send_progress("uploading", 10, "File upload completed")
        await asyncio.sleep(0.1)
        
        # Stage 2: Parsing
        logger.info(f"Starting parsing stage for {filename}")
        yield send_progress("parsing", 20, "Parsing file...")
        try:
            from processors.loaders import LoaderFactory
            from config.settings import get_settings
            settings = get_settings()
            # Prefer the provided base_url, otherwise use configured static_base_url
            final_base_url = base_url or settings.static_base_url
            logger.info(f"Creating loader with static_dir={settings.static_dir}, base_url={final_base_url}")
            loader = LoaderFactory.create(
                doc_type, 
                static_dir=settings.static_dir,
                base_url=final_base_url
            )
            document = loader.load(file_path, metadata={"original_filename": filename})
            # document.source contains the saved_source_path (e.g., "static/sources/7a0b3112_interview_experience.pdf")
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
            yield send_progress("parsing", 80, f"Parsing... {char_count} characters read", {
                "char_count": char_count
            })
            await asyncio.sleep(0.05)
            yield send_progress("parsing", 100, f"Parsing completed, {char_count} characters total", {
                "char_count": char_count
            })
            await asyncio.sleep(0.05)
            logger.info(f"Parsing stage completed for {filename}")
        except Exception as e:
            logger.error(f"Parsing error: {str(e)}", exc_info=True)
            yield send_progress("error", 0, f"Parsing failed: {str(e)}", {
                "retryable": True,
                "error_type": type(e).__name__
            })
            return
        
        # Validate document was loaded
        if document is None:
            logger.error("Document is None after parsing")
            yield send_progress("error", 0, "Parsing failed: document is empty", {
                "retryable": True,
                "error_type": "DocumentError"
            })
            return
        
        # Stage 3: Chunking
        logger.info(f"Starting chunking stage for {filename}")
        yield send_progress("chunking", 10, "Chunking...")
        await asyncio.sleep(0.05)  # Give frontend time to update UI
        
        try:
            from processors.chunkers import ChunkerFactory
            from models.document import DocumentType
            from config.settings import get_settings
            import hashlib
            
            settings = get_settings()
            
            # Get original document type from metadata
            original_type = document.metadata.get("original_type") if document.metadata else None
            if original_type:
                doc_type = DocumentType(original_type)
            else:
                # Fallback: use detected type from loader
                doc_type = doc_type  # Use the doc_type parameter
            
            # Get encoding_name from config
            encoding_name = settings.tiktoken_encoding  # Default from config
            
            # Check if multi-granularity chunking is enabled
            if multi_granularity_chunk_sizes is None:
                multi_granularity_chunk_sizes = settings.multi_granularity_chunk_sizes
            
            if multi_granularity_chunk_sizes and len(multi_granularity_chunk_sizes) > 0:
                # Multi-granularity chunking
                if multi_granularity_chunk_overlap is None:
                    multi_granularity_chunk_overlap = settings.multi_granularity_chunk_overlap
                
                logger.info(f"Using multi-granularity chunking with sizes: {multi_granularity_chunk_sizes}, overlap: {multi_granularity_chunk_overlap}")
                all_chunks = []
                
                for idx, granularity in enumerate(multi_granularity_chunk_sizes):
                    chunker = ChunkerFactory.create(
                        doc_type=doc_type,
                        chunk_size=granularity,
                        chunk_overlap=multi_granularity_chunk_overlap,
                        encoding_name=encoding_name
                    )
                    
                    logger.info(f"Chunking with granularity {granularity} using {chunker.__class__.__name__}")
                    granularity_chunks = chunker.chunk(document)
                    
                    # Update chunk metadata and IDs to include granularity
                    for chunk_index, chunk in enumerate(granularity_chunks):
                        # Update chunk_id to include granularity for uniqueness
                        chunk.chunk_id = f"{document.source}_{granularity}_{chunk_index}"
                        
                        # Add granularity metadata
                        chunk.metadata["granularity"] = granularity
                        chunk.metadata["chunk_size"] = granularity
                        chunk.metadata["chunk_overlap"] = multi_granularity_chunk_overlap
                        
                        # Ensure content_type is set if not already
                        if "content_type" not in chunk.metadata:
                            chunk.metadata["content_type"] = "text"
                    
                    all_chunks.extend(granularity_chunks)
                    logger.info(f"Generated {len(granularity_chunks)} chunks with granularity {granularity}")
                    
                    # Update progress
                    progress = 10 + int((idx + 1) / len(multi_granularity_chunk_sizes) * 80)
                    yield send_progress("chunking", progress, f"Chunking with granularity {granularity}... {len(all_chunks)} total chunks", {
                        "chunks_count": len(all_chunks),
                        "current_granularity": granularity
                    })
                    await asyncio.sleep(0.05)
                
                chunks = all_chunks
                logger.info(f"Multi-granularity chunking completed: created {len(chunks)} total chunks")
            else:
                # Single granularity chunking (backward compatible)
                chunk_size_val = chunk_size or service.chunk_size
                chunk_overlap_val = chunk_overlap or service.chunk_overlap
                logger.info(f"Creating chunker with chunk_size={chunk_size_val}, chunk_overlap={chunk_overlap_val}")
                
                # Use ChunkerFactory to get the correct chunker
                chunker = ChunkerFactory.create(
                    doc_type=doc_type,
                    chunk_size=chunk_size_val,
                    chunk_overlap=chunk_overlap_val,
                    encoding_name=encoding_name
                )
                
                logger.info(f"Using {chunker.__class__.__name__} for document type {doc_type.value}")
                logger.info(f"Starting chunk operation on document with {len(document.content)} characters")
                chunks = chunker.chunk(document)
                logger.info(f"Chunking completed: created {len(chunks)} chunks")
            
            yield send_progress("chunking", 90, f"Chunking... {len(chunks)} chunks created", {
                "chunks_count": len(chunks)
            })
            await asyncio.sleep(0.05)
            yield send_progress("chunking", 100, f"Chunking completed, {len(chunks)} chunks created", {
                "chunks_count": len(chunks)
            })
            await asyncio.sleep(0.05)
            logger.info(f"Chunking stage completed for {filename}")
        except Exception as e:
            logger.error(f"Chunking error: {str(e)}", exc_info=True)
            yield send_progress("error", 0, f"Chunking failed: {str(e)}", {
                "retryable": True,
                "error_type": type(e).__name__
            })
            return
        
        if not chunks:
            yield send_progress("error", 0, "No chunks generated", {
                "retryable": False
            })
            return
        
        # Stage 4: Embedding
        logger.info(f"Starting embedding stage for {filename} with {len(chunks)} chunks")
        yield send_progress("embedding", 10, "Generating embeddings...")
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
                yield send_progress("embedding", progress, f"Generated {len(embeddings)}/{len(texts)} embeddings", {
                    "embeddings_generated": len(embeddings),
                    "embeddings_total": len(texts)
                })
                await asyncio.sleep(0.05)
            
            # Attach embeddings
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding
            
            yield send_progress("embedding", 100, f"Embedding generation completed, {len(embeddings)} embeddings total", {
                "embeddings_generated": len(embeddings),
                "embeddings_total": len(texts)
            })
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Embedding error: {str(e)}", exc_info=True)
            yield send_progress("error", 0, f"Embedding generation failed: {str(e)}", {
                "retryable": True,
                "error_type": type(e).__name__
            })
            return
        
        # Stage 5: Indexing
        logger.info(f"Starting indexing stage for {filename} to collection {collection_name}")
        yield send_progress("indexing", 10, "Indexing to Milvus...")
        await asyncio.sleep(0.05)
        
        try:
            logger.info(f"Indexing {len(chunks)} chunks to Milvus collection: {collection_name}")
            chunks_indexed = service.vector_store.index(chunks, collection_name)
            logger.info(f"Indexing completed: {chunks_indexed} chunks indexed")
            yield send_progress("indexing", 90, f"Indexing... {chunks_indexed} chunks indexed", {
                "chunks_indexed": chunks_indexed
            })
            await asyncio.sleep(0.05)
            yield send_progress("indexing", 100, f"Indexing completed, {chunks_indexed} chunks indexed", {
                "chunks_indexed": chunks_indexed
            })
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.error(f"Indexing error: {str(e)}", exc_info=True)
            yield send_progress("error", 0, f"Indexing failed: {str(e)}", {
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
        yield send_progress("completed", 100, f"Successfully indexed {chunks_indexed} chunks to {collection_name}", completion_data)
        await asyncio.sleep(0.1)  # Give frontend time to process final update
        
    except IndexingError as e:
        logger.error(f"Indexing error: {str(e)}", exc_info=True)
        yield send_progress("error", 0, f"Indexing failed: {str(e)}", {
            "retryable": True,
            "error_type": "IndexingError"
        })
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        yield send_progress("error", 0, f"Processing failed: {str(e)}", {
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
    multi_granularity_chunk_sizes: Optional[str] = Form(None),  # JSON string: "[200, 400, 800]"
    multi_granularity_chunk_overlap: Optional[int] = Form(None),
    database: Optional[str] = Form(None)
):
    """
    Upload and index file with real-time progress updates via Server-Sent Events.
    """
    # Get database name from form parameter or default
    if database:
        db_name = database
    else:
        settings = get_settings()
        db_name = settings.milvus_database
    
    # Create indexing service with the correct database
    service = get_indexing_service(db_name)
    
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
        
        # Get hostname and port from request to build base_url
        # If static_base_url is configured, use it; otherwise get from request
        base_url = settings.static_base_url
        if not base_url:
            # Get hostname and port from request
            # Host header usually contains port number (if non-standard port)
            host = request.headers.get("host")
            if not host:
                # If Host header doesn't exist, get from URL
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
        
        # Parse multi-granularity chunk sizes if provided
        parsed_multi_granularity_sizes = None
        if multi_granularity_chunk_sizes:
            try:
                parsed_multi_granularity_sizes = json.loads(multi_granularity_chunk_sizes)
                if not isinstance(parsed_multi_granularity_sizes, list):
                    raise ValueError("multi_granularity_chunk_sizes must be a JSON array")
                # Validate all items are integers
                parsed_multi_granularity_sizes = [int(x) for x in parsed_multi_granularity_sizes]
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                logger.warning(f"Failed to parse multi_granularity_chunk_sizes: {e}, ignoring")
                parsed_multi_granularity_sizes = None
        
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
                base_url,
                parsed_multi_granularity_sizes,
                multi_granularity_chunk_overlap
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
            yield send_progress("error", 0, f"Upload failed: {str(e)}", {
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
    multi_granularity_chunk_sizes: Optional[str] = Form(None),  # JSON string: "[200, 400, 800]"
    multi_granularity_chunk_overlap: Optional[int] = Form(None),
    database: Optional[str] = Form(None)
):
    """
    Upload a file and index it into knowledge base.
    
    Supports: .md, .pdf, .docx, .html, .txt
    """
    # Get database name from form parameter or default
    if database:
        db_name = database
    else:
        settings = get_settings()
        db_name = settings.milvus_database
    
    # Create indexing service with the correct database
    service = get_indexing_service(db_name)
    
    settings = get_settings()
    temp_path = None
    
    try:
        # Get hostname and port from request to build base_url
        # If static_base_url is configured, use it; otherwise get from request
        base_url = settings.static_base_url
        if not base_url:
            # Get hostname and port from request
            # Host header usually contains port number (if non-standard port)
            host = request.headers.get("host")
            if not host:
                # If Host header doesn't exist, get from URL
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
            
            # Parse multi-granularity chunk sizes if provided
            parsed_multi_granularity_sizes = None
            if multi_granularity_chunk_sizes:
                try:
                    parsed_multi_granularity_sizes = json.loads(multi_granularity_chunk_sizes)
                    if not isinstance(parsed_multi_granularity_sizes, list):
                        raise ValueError("multi_granularity_chunk_sizes must be a JSON array")
                    # Validate all items are integers
                    parsed_multi_granularity_sizes = [int(x) for x in parsed_multi_granularity_sizes]
                except (json.JSONDecodeError, ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse multi_granularity_chunk_sizes: {e}, ignoring")
                    parsed_multi_granularity_sizes = None
            
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
            if parsed_multi_granularity_sizes:
                index_kwargs["multi_granularity_chunk_sizes"] = parsed_multi_granularity_sizes
            if multi_granularity_chunk_overlap is not None:
                index_kwargs["multi_granularity_chunk_overlap"] = multi_granularity_chunk_overlap
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
    database: Optional[str] = Form(None)
):
    """Upload and index multiple files."""
    # Get database name from form parameter or default
    if database:
        db_name = database
    else:
        settings = get_settings()
        db_name = settings.milvus_database
    
    # Create indexing service with the correct database
    service = get_indexing_service(db_name)
    
    settings = get_settings()
    
    # Get hostname and port from request to build base_url
    # If static_base_url is configured, use it; otherwise get from request
    base_url = settings.static_base_url
    if not base_url:
        # Get hostname and port from request
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
