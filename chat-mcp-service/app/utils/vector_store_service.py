"""Vector store service for document chunking, embedding, and storage."""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from pymilvus import FieldSchema, DataType
except ImportError:
    raise ImportError(
        "pymilvus is not installed. Install it with: pip install pymilvus"
    )

from app.logger import get_logger
from app.llm.factory import LLMClientFactory
from app.llm.provider import LLMProvider
from app.utils.document_processor import DocumentChunk, DocumentChunker
from app.utils.milvus_client import MilvusClient

logger = get_logger(__name__)


class VectorStoreService:
    """Service for processing documents and storing them in Milvus vector database."""
    
    COLLECTION_NAME = "travel_documents"
    EMBEDDING_DIM = 1536  # text-embedding-v2 dimension
    EMBEDDING_MODEL = "text-embedding-v2"
    
    def __init__(
        self,
        milvus_client: Optional[MilvusClient] = None,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
    ):
        """
        Initialize vector store service.
        
        Args:
            milvus_client: MilvusClient instance (creates new one if not provided)
            chunk_size: Maximum chunk size in characters
            chunk_overlap: Overlap size between chunks
        """
        self.milvus_client = milvus_client or MilvusClient()
        self.chunker = DocumentChunker(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        self._embedding_client = None
    
    def _get_embedding_client(self):
        """Get or create Qwen embedding client."""
        if self._embedding_client is None:
            # Create Qwen client for embeddings
            from app.config import get_config
            config = get_config()
            self._embedding_client = LLMClientFactory.create_client(
                provider=LLMProvider.QWEN,
                api_key=None  # Will use environment variable
            )
        return self._embedding_client
    
    async def initialize_collection(self) -> bool:
        """
        Initialize or create the travel_documents collection in Milvus.
        
        Returns:
            True if collection is ready, False otherwise
        """
        try:
            # Connect to Milvus if not connected
            if not self.milvus_client.is_connected():
                if not self.milvus_client.connect():
                    logger.error("Failed to connect to Milvus")
                    return False
            
            # Check if collection exists
            if self.milvus_client.collection_exists(self.COLLECTION_NAME):
                logger.info(f"Collection '{self.COLLECTION_NAME}' already exists")
                return True
            
            # Create collection with schema
            metadata_fields = [
                FieldSchema(name="file_name", dtype=DataType.VARCHAR, max_length=255),
                FieldSchema(name="file_type", dtype=DataType.VARCHAR, max_length=50),
                FieldSchema(name="chunk_index", dtype=DataType.INT64),
                FieldSchema(name="metadata", dtype=DataType.VARCHAR, max_length=65535),
            ]
            
            success = self.milvus_client.create_collection_with_embedding(
                collection_name=self.COLLECTION_NAME,
                embedding_dim=self.EMBEDDING_DIM,
                id_field_name="id",
                embedding_field_name="embedding",
                text_field_name="text",
                metadata_fields=metadata_fields,
                description="Travel documents collection for vector search",
                auto_id=True,
            )
            
            if success:
                # Create index on embedding field
                self.milvus_client.create_index(
                    collection_name=self.COLLECTION_NAME,
                    field_name="embedding",
                    index_type="IVF_FLAT",
                    metric_type="L2",
                    params={"nlist": 1024},
                )
                logger.info(f"Created and indexed collection '{self.COLLECTION_NAME}'")
            
            return success
            
        except Exception as e:
            logger.error(f"Error initializing collection: {e}", exc_info=True)
            return False
    
    async def process_and_store_markdown(
        self,
        file_path: str,
        content: Optional[str] = None,
        file_type: str = "md",
    ) -> bool:
        """
        Process markdown file and store chunks in Milvus.
        
        Args:
            file_path: Path to the markdown file
            content: Optional file content (if None, reads from file_path)
            file_type: File type identifier (default: "md")
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Ensure collection exists
            if not await self.initialize_collection():
                logger.error("Failed to initialize collection")
                return False
            
            # Read content if not provided
            if content is None:
                file = Path(file_path)
                if not file.exists():
                    logger.error(f"File not found: {file_path}")
                    return False
                content = file.read_text(encoding="utf-8")
            
            file_name = Path(file_path).name
            
            # Chunk the document
            chunks = self.chunker.chunk_markdown(content, file_name=file_name)
            if not chunks:
                logger.warning(f"No chunks created from file: {file_path}")
                return False
            
            logger.info(f"Created {len(chunks)} chunks from {file_name}")
            
            # Generate embeddings for all chunks
            texts = [chunk.text for chunk in chunks]
            embedding_client = self._get_embedding_client()
            embeddings = await embedding_client.get_embeddings(
                texts=texts,
                model=self.EMBEDDING_MODEL,
            )
            
            if len(embeddings) != len(chunks):
                logger.error(f"Embedding count mismatch: {len(embeddings)} != {len(chunks)}")
                return False
            
            # Prepare data for insertion
            data_to_insert = []
            for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
                # Prepare metadata JSON
                metadata_dict = {
                    **chunk.metadata,
                    "file_path": str(file_path),
                    "title": self._extract_title(chunk.text),
                }
                
                data_to_insert.append({
                    "text": chunk.text,
                    "embedding": embedding,
                    "file_name": file_name,
                    "file_type": file_type,
                    "chunk_index": chunk.chunk_index,
                    "metadata": json.dumps(metadata_dict, ensure_ascii=False),
                })
            
            # Insert into Milvus
            field_names = ["text", "embedding", "file_name", "file_type", "chunk_index", "metadata"]
            data_values = [
                [item["text"] for item in data_to_insert],
                [item["embedding"] for item in data_to_insert],
                [item["file_name"] for item in data_to_insert],
                [item["file_type"] for item in data_to_insert],
                [item["chunk_index"] for item in data_to_insert],
                [item["metadata"] for item in data_to_insert],
            ]
            
            result = self.milvus_client.insert(
                collection_name=self.COLLECTION_NAME,
                data=data_values,
                field_names=field_names,
            )
            
            if result:
                logger.info(f"Successfully stored {len(data_to_insert)} chunks from {file_name}")
                return True
            else:
                logger.error(f"Failed to insert chunks into Milvus")
                return False
                
        except Exception as e:
            logger.error(f"Error processing and storing markdown: {e}", exc_info=True)
            return False
    
    def _extract_title(self, text: str) -> str:
        """Extract title from chunk text (first heading or first line)."""
        lines = text.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("#"):
                # Remove markdown heading markers
                title = line.lstrip("#").strip()
                if title:
                    return title
        # Return first line as title
        if lines:
            return lines[0][:100]  # Limit title length
        return ""
    
    async def search(
        self,
        query: str,
        limit: int = 10,
        file_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for similar chunks using vector similarity.
        
        Args:
            query: Search query text
            limit: Number of results to return (default: 10)
            file_type: Optional filter by file type
            
        Returns:
            List of search results with text, metadata, and score
        """
        try:
            # Ensure collection exists
            if not await self.initialize_collection():
                logger.error("Collection not initialized")
                return []
            
            # Generate query embedding
            embedding_client = self._get_embedding_client()
            query_embeddings = await embedding_client.get_embeddings(
                texts=[query],
                model=self.EMBEDDING_MODEL,
            )
            
            if not query_embeddings:
                logger.error("Failed to generate query embedding")
                return []
            
            query_embedding = query_embeddings[0]
            
            # Build filter expression
            expr = None
            if file_type:
                expr = f'file_type == "{file_type}"'
            
            # Search in Milvus
            search_results = self.milvus_client.search(
                collection_name=self.COLLECTION_NAME,
                query_vectors=[query_embedding],
                anns_field="embedding",
                param={"metric_type": "L2", "params": {"nprobe": 10}},
                limit=limit,
                expr=expr,
                output_fields=["text", "file_name", "file_type", "chunk_index", "metadata"],
            )
            
            if not search_results:
                logger.warning("No search results returned")
                return []
            
            # Format results
            # Milvus search returns: List[List[Hit]] where each inner list contains hits for one query vector
            results = []
            for hits in search_results:
                for hit in hits:
                    try:
                        # Access fields from hit.entity (dict-like access)
                        entity_data = hit.entity if hasattr(hit, "entity") else {}
                        
                        # Extract text
                        text = entity_data.get("text", "") if isinstance(entity_data, dict) else getattr(entity_data, "text", "")
                        
                        if not text:
                            continue
                        
                        # Extract metadata JSON string and parse it
                        metadata_str = entity_data.get("metadata", "{}") if isinstance(entity_data, dict) else getattr(entity_data, "metadata", "{}")
                        try:
                            metadata_dict = json.loads(metadata_str) if isinstance(metadata_str, str) else metadata_str
                        except (json.JSONDecodeError, TypeError):
                            metadata_dict = {}
                        
                        result_metadata = {
                            "text": text,
                            "file_name": entity_data.get("file_name", "") if isinstance(entity_data, dict) else getattr(entity_data, "file_name", ""),
                            "file_type": entity_data.get("file_type", "") if isinstance(entity_data, dict) else getattr(entity_data, "file_type", ""),
                            "chunk_index": entity_data.get("chunk_index", 0) if isinstance(entity_data, dict) else getattr(entity_data, "chunk_index", 0),
                            "metadata": metadata_dict,
                            "score": hit.distance if hasattr(hit, "distance") else 0.0,
                        }
                        
                        results.append(result_metadata)
                    except Exception as e:
                        logger.warning(f"Error parsing search result hit: {e}", exc_info=True)
                        continue
            
            logger.info(f"Found {len(results)} search results for query")
            return results
            
        except Exception as e:
            logger.error(f"Error searching vector store: {e}", exc_info=True)
            return []
    
    def delete_document(self, file_name: str) -> bool:
        """
        Delete all chunks of a document by file name.
        
        Args:
            file_name: Name of the file to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            expr = f'file_name == "{file_name}"'
            return self.milvus_client.delete(
                collection_name=self.COLLECTION_NAME,
                expr=expr,
            )
        except Exception as e:
            logger.error(f"Error deleting document: {e}", exc_info=True)
            return False

