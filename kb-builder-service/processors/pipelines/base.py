"""Base pipeline interface."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from models.document import Document
from models.chunk import Chunk


class BasePipeline(ABC):
    """Base class for document processing pipelines."""
    
    @abstractmethod
    def load(self, source: str, **kwargs) -> Document:
        """
        Load document from source.
        
        Args:
            source: Path to document file
            **kwargs: Additional arguments (e.g., file_id)
        
        Returns:
            Document object
        """
        pass
    
    @abstractmethod
    def chunk(self, document: Document, **kwargs) -> List[Chunk]:
        """
        Chunk document into smaller pieces.
        
        Args:
            document: Document object
            **kwargs: Additional arguments (e.g., chunk_size, chunk_overlap)
        
        Returns:
            List of Chunk objects
        """
        pass
    
    @abstractmethod
    def index(
        self,
        chunks: List[Chunk],
        collection_name: str,
        embedder,
        vector_store,
        **kwargs
    ) -> int:
        """
        Index chunks (generate embeddings and store to vector database).
        
        Args:
            chunks: List of Chunk objects
            collection_name: Collection name in vector database
            embedder: Embedder instance
            vector_store: VectorStore instance
            **kwargs: Additional arguments
        
        Returns:
            Number of chunks indexed
        """
        pass
    
    def process(
        self,
        source: str,
        collection_name: str,
        embedder,
        vector_store,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Complete processing pipeline: load → chunk → index.
        
        Args:
            source: Path to document file
            collection_name: Collection name in vector database
            embedder: Embedder instance
            vector_store: VectorStore instance
            **kwargs: Additional arguments
        
        Returns:
            Dictionary with processing results
        """
        # Load document
        document = self.load(source, **kwargs)
        
        # Chunk document
        chunks = self.chunk(document, **kwargs)
        
        if not chunks:
            return {
                "success": False,
                "message": "No chunks generated from document",
                "chunks_indexed": 0,
                "document_id": document.source
            }
        
        # Index chunks
        chunks_indexed = self.index(chunks, collection_name, embedder, vector_store, **kwargs)
        
        return {
            "success": True,
            "document_id": document.source,
            "chunks_indexed": chunks_indexed,
            "collection_name": collection_name,
            "document_type": document.doc_type.value,
            "structure": document.structure.to_dict() if document.structure else None,
            "message": f"Successfully indexed {chunks_indexed} chunks"
        }

