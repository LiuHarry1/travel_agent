"""Indexing service - main business logic."""
from typing import List, Optional

from models.document import DocumentType
from processors.loaders import LoaderFactory
from processors.chunkers import ChunkerFactory
from processors.extractors import LocationExtractor
from processors.embedders import EmbedderFactory
from processors.stores import MilvusVectorStore
from utils.exceptions import IndexingError
from utils.logger import get_logger

logger = get_logger(__name__)


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
        base_url: Optional[str] = None,
        **kwargs
    ) -> dict:
        """
        Index a single document.
        
        Returns:
            dict with success status and details
        """
        try:
            # 1. Load document
            # Use unified loader with static_dir and base_url configuration
            from config.settings import get_settings
            settings = get_settings()
            # Prefer the provided base_url, otherwise use configured static_base_url
            final_base_url = base_url or settings.static_base_url
            loader = LoaderFactory.create(
                doc_type, 
                static_dir=settings.static_dir,
                base_url=final_base_url
            )
            document = loader.load(source, **kwargs)
            logger.info(f"Loaded document: {document.source}")
            
            # 2. Chunk document using type-specific chunker
            # Get original document type from metadata
            original_type = document.metadata.get("original_type")
            if original_type:
                doc_type = DocumentType(original_type)
            else:
                # Fallback: try to detect from source
                from pathlib import Path
                ext = Path(source).suffix.lower()
                type_map = {
                    ".pdf": DocumentType.PDF,
                    ".docx": DocumentType.DOCX,
                    ".doc": DocumentType.DOCX,
                    ".html": DocumentType.HTML,
                    ".htm": DocumentType.HTML,
                    ".md": DocumentType.MARKDOWN,
                    ".markdown": DocumentType.MARKDOWN,
                    ".txt": DocumentType.TXT,
                }
                doc_type = type_map.get(ext, DocumentType.TXT)
            
            # Get encoding_name from config
            from config.settings import get_settings
            settings = get_settings()
            encoding_name = kwargs.get("encoding_name", settings.tiktoken_encoding)
            
            # Check if multi-granularity chunking is enabled
            multi_granularity_sizes = kwargs.get("multi_granularity_chunk_sizes")
            if multi_granularity_sizes is None:
                # Check settings
                multi_granularity_sizes = settings.multi_granularity_chunk_sizes
            
            # Use multi-granularity if configured, otherwise use single granularity
            if multi_granularity_sizes and len(multi_granularity_sizes) > 0:
                # Multi-granularity chunking
                multi_granularity_overlap = kwargs.get(
                    "multi_granularity_chunk_overlap",
                    settings.multi_granularity_chunk_overlap
                )
                chunks = self._generate_multi_granularity_chunks(
                    document=document,
                    doc_type=doc_type,
                    chunk_sizes=multi_granularity_sizes,
                    chunk_overlap=multi_granularity_overlap,
                    encoding_name=encoding_name
                )
                logger.info(f"Created {len(chunks)} multi-granularity chunks using sizes: {multi_granularity_sizes}")
            else:
                # Single granularity chunking (backward compatible)
                chunker = ChunkerFactory.create(
                    doc_type=doc_type,
                    chunk_size=chunk_size or self.chunk_size,
                    chunk_overlap=chunk_overlap or self.chunk_overlap,
                    encoding_name=encoding_name
                )
                chunks = chunker.chunk(document)
                logger.info(f"Created {len(chunks)} chunks using {chunker.__class__.__name__}")
            
            # 3. Enrich chunks with location information
            chunks = self._enrich_with_locations(chunks, doc_type)
            
            if not chunks:
                return {
                    "success": False,
                    "message": "No chunks generated from document",
                    "chunks_indexed": 0
                }
            
            # 4. Generate embeddings
            embedder_kwargs = {}
            if embedding_provider.lower() == "bge" and kwargs.get("bge_api_url"):
                embedder_kwargs["api_url"] = kwargs["bge_api_url"]
            embedder = EmbedderFactory.create(
                provider=embedding_provider,
                model=embedding_model,
                **embedder_kwargs
            )
            texts = [chunk.text for chunk in chunks]
            embeddings = embedder.embed(texts)
            logger.info(f"Generated {len(embeddings)} embeddings")
            
            # 5. Attach embeddings
            for chunk, embedding in zip(chunks, embeddings):
                chunk.embedding = embedding
            
            # 6. Index to vector store
            chunks_indexed = self.vector_store.index(chunks, collection_name)
            logger.info(f"Indexed {chunks_indexed} chunks to {collection_name}")
            
            return {
                "success": True,
                "document_id": document.source,
                "chunks_indexed": chunks_indexed,
                "collection_name": collection_name,
                "document_type": doc_type.value,
                "structure": document.structure.to_dict() if document.structure else None,
                "message": f"Successfully indexed {chunks_indexed} chunks"
            }
            
        except Exception as e:
            logger.error(f"Indexing failed: {str(e)}", exc_info=True)
            raise IndexingError(f"Failed to index document: {str(e)}") from e
    
    def _generate_multi_granularity_chunks(
        self,
        document,
        doc_type: DocumentType,
        chunk_sizes: List[int],
        chunk_overlap: int,
        encoding_name: str
    ) -> List:
        """
        Generate chunks with multiple granularities.
        
        Args:
            document: Document object
            doc_type: Document type
            chunk_sizes: List of chunk sizes (e.g., [200, 400, 800])
            chunk_overlap: Chunk overlap for all granularities
            encoding_name: Tiktoken encoding name
        
        Returns:
            List of chunks with granularity metadata
        """
        all_chunks = []
        
        for granularity in chunk_sizes:
            # Create chunker for this granularity
            chunker = ChunkerFactory.create(
                doc_type=doc_type,
                chunk_size=granularity,
                chunk_overlap=chunk_overlap,
                encoding_name=encoding_name
            )
            
            # Generate chunks for this granularity
            granularity_chunks = chunker.chunk(document)
            
            # Update chunk metadata and IDs to include granularity
            for chunk_index, chunk in enumerate(granularity_chunks):
                # Update chunk_id to include granularity for uniqueness
                chunk.chunk_id = f"{document.source}_{granularity}_{chunk_index}"
                
                # Add granularity metadata
                chunk.metadata["granularity"] = granularity
                chunk.metadata["chunk_size"] = granularity
                chunk.metadata["chunk_overlap"] = chunk_overlap
                
                # Ensure content_type is set if not already
                if "content_type" not in chunk.metadata:
                    chunk.metadata["content_type"] = "text"
            
            all_chunks.extend(granularity_chunks)
            logger.debug(f"Generated {len(granularity_chunks)} chunks with granularity {granularity}")
        
        return all_chunks
    
    def _enrich_with_locations(self, chunks: List, doc_type: DocumentType) -> List:
        """Enrich chunks with location information."""
        extractor = LocationExtractor()
        
        for chunk in chunks:
            # If chunk already has location information (set by chunker), skip
            if chunk.location:
                continue
            
            # Get position information from metadata
            start_pos = chunk.metadata.get("start_pos", 0)
            end_pos = chunk.metadata.get("end_pos", len(chunk.text))
            
            # Extract location information based on file type
            if doc_type == DocumentType.PDF:
                chunk.location = extractor.extract_for_pdf(chunk.text, start_pos, end_pos)
            elif doc_type == DocumentType.DOCX:
                chunk.location = extractor.extract_for_docx(chunk.text, start_pos, end_pos)
            elif doc_type == DocumentType.HTML:
                chunk.location = extractor.extract_for_html(chunk.text, start_pos, end_pos)
            elif doc_type == DocumentType.MARKDOWN:
                chunk.location = extractor.extract_for_markdown(chunk.text, start_pos, end_pos)
            else:
                # Default: only set basic position information
                from models.chunk import ChunkLocation
                chunk.location = ChunkLocation(
                    start_char=start_pos,
                    end_char=end_pos
                )
        
        return chunks
    
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

