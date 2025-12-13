"""PDF processing pipeline."""
from typing import List, Dict, Any, Optional
from .base import BasePipeline
from processors.loaders.pdf.pdf_loader import PDFLoader
from processors.chunkers.pdf_chunker import PDFChunker
from processors.trackers.pdf_tracker import PDFLocationTracker
from models.document import Document
from models.chunk import Chunk
from utils.logger import get_logger

logger = get_logger(__name__)


class PDFPipeline(BasePipeline):
    """PDF document processing pipeline."""
    
    def __init__(
        self,
        static_dir: str = "static",
        base_url: str = "",
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
        encoding_name: str = "cl100k_base",
        **kwargs
    ):
        """
        Initialize PDF pipeline.
        
        Args:
            static_dir: Static files directory
            base_url: Base URL for static files
            chunk_size: Chunk size in tokens
            chunk_overlap: Chunk overlap in tokens
            min_chunk_size: Minimum chunk size in tokens
            encoding_name: Tiktoken encoding name
            table_max_rows_per_chunk: Maximum rows per table chunk
            **kwargs: Additional arguments
        """
        self.loader = PDFLoader(static_dir=static_dir, base_url=base_url)
        self.chunker = PDFChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_size=min_chunk_size,
            encoding_name=encoding_name
        )
        self.tracker = PDFLocationTracker()
    
    def load(self, source: str, **kwargs) -> Document:
        """
        Load PDF document.
        
        Args:
            source: Path to PDF file
            **kwargs: Additional arguments (e.g., file_id)
        
        Returns:
            Document object
        """
        logger.info(f"Loading PDF document: {source}")
        document = self.loader.load(source, **kwargs)
        document = self.tracker.track_during_loading(document)
        return document
    
    def chunk(self, document: Document, **kwargs) -> List[Chunk]:
        """
        Chunk PDF document.
        
        Args:
            document: Document object
            **kwargs: Additional arguments
        
        Returns:
            List of Chunk objects
        """
        logger.info(f"Chunking PDF document: {document.source}")
        chunks = self.chunker.chunk(document)
        chunks = self.tracker.track_during_chunking(chunks, document)
        logger.info(f"Created {len(chunks)} chunks from PDF document")
        return chunks
    
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
        if not chunks:
            logger.warning("No chunks to index")
            return 0
        
        logger.info(f"Indexing {len(chunks)} chunks to collection: {collection_name}")
        
        # Generate embeddings
        texts = [chunk.text for chunk in chunks]
        embeddings = embedder.embed(texts)
        logger.info(f"Generated {len(embeddings)} embeddings")
        
        # Attach embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk.embedding = embedding
        
        # Store to vector database
        chunks_indexed = vector_store.index(chunks, collection_name)
        logger.info(f"Indexed {chunks_indexed} chunks to {collection_name}")
        
        return chunks_indexed

