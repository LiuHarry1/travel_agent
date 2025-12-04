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
        alias: str = "default"
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
                )
                self._connected = True
                logger.info(f"Connected to Milvus at {self.host}:{self.port}")
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
            
            # Ensure collection exists
            if not self._collection_exists(collection_name):
                self._create_collection(collection_name, embedding_dim)
            
            # Prepare data
            # Note: id field is auto_id=True, so we only need to provide text and embedding
            texts = [chunk.text for chunk in chunks]
            embeddings = [list(chunk.embedding) for chunk in chunks]
            
            # Insert data in batches to avoid memory issues
            batch_size = 1000
            collection = Collection(collection_name, using=self.alias)
            
            for i in range(0, len(texts), batch_size):
                batch_texts = texts[i:i + batch_size]
                batch_embeddings = embeddings[i:i + batch_size]
                logger.debug(f"Inserting batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size}")
                collection.insert([batch_texts, batch_embeddings])
            
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

