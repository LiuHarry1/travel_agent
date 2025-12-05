"""Milvus vector store implementation."""
from typing import List
import sys
from pathlib import Path

try:
    from pymilvus import (
        connections,
        Collection,
        CollectionSchema,
        FieldSchema,
        DataType,
        utility,
    )
    HAS_PYMILVUS = True
except ImportError:
    HAS_PYMILVUS = False

from .base import BaseVectorStore
from models.chunk import Chunk
from utils.exceptions import IndexingError
from utils.logger import get_logger

logger = get_logger(__name__)


class MilvusVectorStore(BaseVectorStore):
    """Milvus implementation of vector store."""
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 19530,
        user: str = "",
        password: str = "",
        alias: str = "default",
        database: str = "default"
    ):
        """Initialize Milvus vector store."""
        if not HAS_PYMILVUS:
            raise ImportError(
                "pymilvus is required. Install with: pip install pymilvus"
            )
        
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.alias = alias
        self.database = database
        self._connected = False
    
    def _connect(self):
        """Connect to Milvus."""
        if not self._connected:
            try:
                connections.connect(
                    alias=self.alias,
                    host=self.host,
                    port=self.port,
                    user=self.user if self.user else None,
                    password=self.password if self.password else None,
                    db_name=self.database
                )
                self._connected = True
                logger.info(f"Connected to Milvus at {self.host}:{self.port}, database: {self.database}")
            except Exception as e:
                raise IndexingError(f"Failed to connect to Milvus: {str(e)}") from e
    
    def _collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists."""
        try:
            return utility.has_collection(collection_name)
        except Exception:
            return False
    
    def _create_collection(self, collection_name: str, embedding_dim: int):
        """Create collection with schema."""
        try:
            fields = [
                FieldSchema(
                    name="id",
                    dtype=DataType.INT64,
                    is_primary=True,
                    auto_id=True
                ),
                FieldSchema(
                    name="text",
                    dtype=DataType.VARCHAR,
                    max_length=65535
                ),
                FieldSchema(
                    name="embedding",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=embedding_dim
                ),
                FieldSchema(
                    name="document_id",
                    dtype=DataType.VARCHAR,
                    max_length=1024
                ),
                FieldSchema(
                    name="file_path",
                    dtype=DataType.VARCHAR,
                    max_length=2048
                ),
            ]
            
            schema = CollectionSchema(
                fields=fields,
                description="Knowledge base collection"
            )
            
            collection = Collection(
                name=collection_name,
                schema=schema,
                using=self.alias
            )
            
            # Create index
            index_params = {
                "metric_type": "L2",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024}
            }
            collection.create_index("embedding", index_params)
            
            logger.info(f"Created collection '{collection_name}' with dimension {embedding_dim}")
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to create collection: {error_msg}", exc_info=True)
            
            # Provide more helpful error messages for common issues
            if "No space left on device" in error_msg or "ENOSPC" in error_msg:
                raise IndexingError(
                    f"Milvus 磁盘空间不足。\n"
                    f"错误详情: {error_msg}\n"
                    f"建议解决方案:\n"
                    f"1. 检查磁盘空间: df -h\n"
                    f"2. 如果使用 Docker，清理容器和卷: docker system prune -a --volumes\n"
                    f"3. 清理 Milvus 日志文件\n"
                    f"4. 删除不需要的 collection 释放空间"
                ) from e
            else:
                raise IndexingError(f"Failed to create collection: {error_msg}") from e
    
    def index(self, chunks: List[Chunk], collection_name: str) -> int:
        """Index chunks to Milvus."""
        if not chunks:
            return 0
        
        try:
            self._connect()
            
            # Get embedding dimension from first chunk
            if not chunks[0].embedding:
                raise IndexingError("Chunks must have embeddings before indexing")
            
            embedding_dim = len(chunks[0].embedding)
            
            # Ensure collection exists and check schema compatibility
            collection = Collection(collection_name, using=self.alias)
            
            if not self._collection_exists(collection_name):
                self._create_collection(collection_name, embedding_dim)
            else:
                # Check if collection has required fields and correct dimension
                collection.load()
                schema = collection.schema
                
                # Debug: log all field names
                field_names = [field.name for field in schema.fields]
                logger.debug(f"Collection '{collection_name}' schema fields: {field_names}")
                
                has_document_id = any(field.name == "document_id" for field in schema.fields)
                has_file_path = any(field.name == "file_path" for field in schema.fields)
                
                if not has_document_id:
                    logger.warning(
                        f"Collection '{collection_name}' missing 'document_id' field. "
                        f"Available fields: {field_names}"
                    )
                    raise IndexingError(
                        f"Collection '{collection_name}' exists but doesn't have 'document_id' field.\n"
                        f"Available fields: {', '.join(field_names)}\n"
                        f"This collection was created with an older schema. Please:\n"
                        f"1. Delete the collection: DELETE /api/v1/collections/{collection_name}\n"
                        f"2. Re-upload your files to recreate the collection with the new schema"
                    )
                
                if not has_file_path:
                    logger.warning(
                        f"Collection '{collection_name}' missing 'file_path' field. "
                        f"Available fields: {field_names}"
                    )
                    raise IndexingError(
                        f"Collection '{collection_name}' exists but doesn't have 'file_path' field.\n"
                        f"Available fields: {', '.join(field_names)}\n"
                        f"This collection was created with an older schema. Please:\n"
                        f"1. Delete the collection: DELETE /api/v1/collections/{collection_name}\n"
                        f"2. Re-upload your files to recreate the collection with the new schema"
                    )
                
                # Check embedding dimension
                embedding_field = None
                for field in schema.fields:
                    if field.name == "embedding":
                        embedding_field = field
                        break
                
                if embedding_field:
                    schema_dim = embedding_field.params.get("dim")
                    if schema_dim and schema_dim != embedding_dim:
                        logger.error(
                            f"Dimension mismatch: collection expects {schema_dim}D, "
                            f"but embeddings are {embedding_dim}D"
                        )
                        raise IndexingError(
                            f"Embedding dimension mismatch!\n"
                            f"Collection '{collection_name}' was created with {schema_dim}-dimensional embeddings,\n"
                            f"but you're trying to insert {embedding_dim}-dimensional embeddings.\n\n"
                            f"This usually happens when switching embedding providers:\n"
                            f"- Qwen/OpenAI: 1536 dimensions\n"
                            f"- BGE large: 1024 dimensions\n"
                            f"- BGE base: 768 dimensions\n"
                            f"- BGE small: 384 dimensions\n\n"
                            f"Solution:\n"
                            f"1. Delete the collection: DELETE /api/v1/collections/{collection_name}\n"
                            f"2. Re-upload your files with the new embedding provider\n"
                            f"   (The collection will be recreated with the correct dimension)"
                        )
            
            # Ensure collection is loaded
            collection.load()
            
            # Prepare data
            # Note: id field is auto_id=True, so we need to provide text, embedding, document_id, and file_path
            texts = [chunk.text for chunk in chunks]
            embeddings = [list(chunk.embedding) for chunk in chunks]
            document_ids = [chunk.document_id for chunk in chunks]
            file_paths = [chunk.file_path or "" for chunk in chunks]
            
            # Insert data in batches to avoid memory issues
            batch_size = 1000
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_embeddings = embeddings[i:i + batch_size]
                batch_document_ids = document_ids[i:i + batch_size]
                batch_file_paths = file_paths[i:i + batch_size]
                logger.debug(f"Inserting batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size}")
                collection.insert([batch_texts, batch_embeddings, batch_document_ids, batch_file_paths])
            
            # Flush to ensure data is written
            collection.flush()
            
            logger.info(f"Indexed {len(chunks)} chunks to collection '{collection_name}'")
            return len(chunks)
            
        except IndexingError:
            # Re-raise IndexingError as-is (already has helpful message)
            raise
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to index chunks: {error_msg}", exc_info=True)
            
            # Provide more helpful error messages for common issues
            if "No space left on device" in error_msg or "ENOSPC" in error_msg:
                raise IndexingError(
                    f"Milvus 磁盘空间不足。\n"
                    f"错误详情: {error_msg}\n"
                    f"建议解决方案:\n"
                    f"1. 检查磁盘空间: df -h\n"
                    f"2. 如果使用 Docker，清理容器和卷: docker system prune -a --volumes\n"
                    f"3. 清理 Milvus 日志文件\n"
                    f"4. 删除不需要的 collection 释放空间"
                ) from e
            else:
                raise IndexingError(f"Indexing failed: {error_msg}") from e
    
    def list_sources(self, collection_name: str) -> List[dict]:
        """List all unique source files (document_id) in a collection."""
        try:
            self._connect()
            
            if not self._collection_exists(collection_name):
                return []
            
            collection = Collection(collection_name, using=self.alias)
            collection.load()
            
            # Query to get all document_ids and file_paths
            # Milvus doesn't support DISTINCT, so we query all and deduplicate
            # Use a valid field expression to query all records: id >= 0 (always true for auto_id)
            results = collection.query(
                expr="id >= 0",
                output_fields=["document_id", "file_path"],
                limit=16384  # Milvus max limit
            )
            
            # Get unique document_ids, count chunks, and get file_path for each
            source_info = {}  # {doc_id: {"count": int, "file_path": str}}
            for result in results:
                doc_id = result.get("document_id", "")
                if doc_id:
                    if doc_id not in source_info:
                        source_info[doc_id] = {
                            "count": 0,
                            "file_path": result.get("file_path", "")
                        }
                    source_info[doc_id]["count"] += 1
                    # Update file_path if we found one (prefer non-empty)
                    if result.get("file_path") and not source_info[doc_id]["file_path"]:
                        source_info[doc_id]["file_path"] = result.get("file_path", "")
            
            # Convert to list of dicts
            sources = []
            for doc_id, info in source_info.items():
                # doc_id is the original filename (e.g., "面试经验.pdf")
                # file_path is the actual saved path (e.g., "static/sources/7a0b3112_面试经验.pdf")
                sources.append({
                    "document_id": doc_id,
                    "chunk_count": info["count"],
                    "filename": doc_id,  # Original filename for display
                    "file_path": info["file_path"]  # Actual file path
                })
            
            # Sort by filename
            sources.sort(key=lambda x: x["filename"])
            
            return sources
        except Exception as e:
            logger.error(f"Failed to list sources: {str(e)}", exc_info=True)
            raise IndexingError(f"Failed to list sources: {str(e)}") from e
    
    def get_chunks_by_source(
        self, 
        collection_name: str, 
        document_id: str,
        page: int = 1,
        page_size: int = 10
    ) -> dict:
        """Get chunks for a specific source file with pagination."""
        try:
            self._connect()
            
            if not self._collection_exists(collection_name):
                return {"chunks": [], "total": 0, "page": page, "page_size": page_size, "total_pages": 0}
            
            collection = Collection(collection_name, using=self.alias)
            collection.load()
            
            # Query chunks by document_id
            # Escape quotes in document_id for expression
            escaped_doc_id = document_id.replace('"', '\\"')
            expr = f'document_id == "{escaped_doc_id}"'
            
            # Get all results first (Milvus doesn't support offset in query)
            all_results = collection.query(
                expr=expr,
                output_fields=["id", "text", "document_id"],
                limit=16384  # Milvus max limit
            )
            
            total = len(all_results)
            
            # Manual pagination
            offset = (page - 1) * page_size
            paginated_results = all_results[offset:offset + page_size]
            
            chunks = [
                {
                    "id": result.get("id"),
                    "text": result.get("text", ""),
                    "document_id": result.get("document_id", ""),
                    "index": idx + offset
                }
                for idx, result in enumerate(paginated_results)
            ]
            
            return {
                "chunks": chunks,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": (total + page_size - 1) // page_size if total > 0 else 0
            }
        except Exception as e:
            logger.error(f"Failed to get chunks: {str(e)}", exc_info=True)
            raise IndexingError(f"Failed to get chunks: {str(e)}") from e
    
    def delete_source(self, collection_name: str, document_id: str) -> int:
        """Delete all chunks for a specific source file."""
        try:
            self._connect()
            
            if not self._collection_exists(collection_name):
                return 0
            
            collection = Collection(collection_name, using=self.alias)
            collection.load()
            
            # Milvus delete() only supports deletion by primary key (id)
            # So we need to:
            # 1. Query all chunks with matching document_id to get their ids
            # 2. Delete using those ids
            
            # Escape quotes in document_id for expression
            escaped_doc_id = document_id.replace('"', '\\"')
            expr = f'document_id == "{escaped_doc_id}"'
            
            # Query to get all primary keys (ids) of chunks to delete
            # Milvus query doesn't support offset, so we need to get all at once
            results = collection.query(
                expr=expr,
                output_fields=["id"],
                limit=16384  # Milvus max limit
            )
            
            if not results:
                return 0
            
            # Extract all primary key IDs
            ids_to_delete = [result["id"] for result in results]
            deleted_count = len(ids_to_delete)
            
            # Delete using primary keys
            # Format: "id in [1, 2, 3, ...]"
            ids_expr = f"id in [{', '.join(map(str, ids_to_delete))}]"
            collection.delete(expr=ids_expr)
            
            # Flush to ensure deletion is persisted
            collection.flush()
            
            logger.info(f"Deleted {deleted_count} chunks for document_id: {document_id}")
            
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete source: {str(e)}", exc_info=True)
            raise IndexingError(f"Failed to delete source: {str(e)}") from e

