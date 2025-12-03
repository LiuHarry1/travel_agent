"""Indexing service - main business logic."""
import logging
from typing import List, Optional

from ..models.document import DocumentType
from ..processors.loaders import LoaderFactory
from ..processors.chunkers import RecursiveChunker
from ..processors.embedders import EmbedderFactory
from ..processors.stores import MilvusVectorStore
from ..utils.exceptions import IndexingError

logger = logging.getLogger(__name__)


class IndexingService:
    """Service for indexing documents."""
    
    def __init__(
        self,
        vector_store: Optional[MilvusVectorStore] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200
    ):
        self.vector_store = vector_store or MilvusVectorStore()
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    def index_document(
        self,
        source: str,
        doc_type: DocumentType,
        collection_name: str,
        embedding_provider: str = "qwen",
        embedding_model: Optional[str] = None,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None,
        **kwargs
    ) -> dict:
        """
        Index a single document.
        
        Returns:
            dict with success status and details
        """
        try:
            # 1. Load document
            loader = LoaderFactory.create(doc_type)
            document = loader.load(source, **kwargs)
            logger.info(f"Loaded document: {document.source}")
            
            # 2. Chunk document
            chunker = RecursiveChunker(
                chunk_size=chunk_size or self.chunk_size,
                chunk_overlap=chunk_overlap or self.chunk_overlap
            )
            chunks = chunker.chunk(document)
            logger.info(f"Created {len(chunks)} chunks")
            
            if not chunks:
                return {
                    "success": False,
                    "message": "No chunks generated from document",
                    "chunks_indexed": 0
                }
            
            # 3. Generate embeddings
            embedder = EmbedderFactory.create(
                provider=embedding_provider,
                model=embedding_model
            )
            texts = [chunk.text for chunk in chunks]
            embeddings = embedder.embed(texts)
            logger.info(f"Generated {len(embeddings)} embeddings")
            
            # 4. Attach embeddings
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding
            
            # 5. Index to vector store
            chunks_indexed = self.vector_store.index(chunks, collection_name)
            logger.info(f"Indexed {chunks_indexed} chunks to {collection_name}")
            
            return {
                "success": True,
                "document_id": document.source,
                "chunks_indexed": chunks_indexed,
                "collection_name": collection_name,
                "message": f"Successfully indexed {chunks_indexed} chunks"
            }
            
        except Exception as e:
            logger.error(f"Indexing failed: {str(e)}", exc_info=True)
            raise IndexingError(f"Failed to index document: {str(e)}") from e
    
    def index_batch(
        self,
        sources: List[str],
        doc_types: List[DocumentType],
        collection_name: str,
        **kwargs
    ) -> List[dict]:
        """Index multiple documents."""
        results = []
        for source, doc_type in zip(sources, doc_types):
            try:
                result = self.index_document(
                    source=source,
                    doc_type=doc_type,
                    collection_name=collection_name,
                    **kwargs
                )
                results.append(result)
            except Exception as e:
                results.append({
                    "success": False,
                    "source": source,
                    "message": str(e)
                })
        return results

