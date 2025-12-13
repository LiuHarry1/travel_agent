"""Indexing service - main business logic."""
from typing import List, Optional

from models.document import DocumentType
from processors.pipelines import PipelineFactory
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
            # Get settings
            from config.settings import get_settings
            settings = get_settings()
            
            # Prefer the provided base_url, otherwise use configured static_base_url
            final_base_url = base_url or settings.static_base_url
            
            # Get encoding_name from config
            encoding_name = kwargs.get("encoding_name", settings.tiktoken_encoding)
            
            # Check if multi-granularity chunking is enabled
            multi_granularity_sizes = kwargs.get("multi_granularity_chunk_sizes")
            if multi_granularity_sizes is None:
                multi_granularity_sizes = settings.multi_granularity_chunk_sizes
            
            # Create embedder
            embedder_kwargs = {}
            if embedding_provider.lower() == "bge" and kwargs.get("bge_api_url"):
                embedder_kwargs["api_url"] = kwargs["bge_api_url"]
            embedder = EmbedderFactory.create(
                provider=embedding_provider,
                model=embedding_model,
                **embedder_kwargs
            )
            
            # Handle multi-granularity chunking
            if multi_granularity_sizes and len(multi_granularity_sizes) > 0:
                # Multi-granularity: process with each chunk size
                multi_granularity_overlap = kwargs.get(
                    "multi_granularity_chunk_overlap",
                    settings.multi_granularity_chunk_overlap
                )
                
                all_chunks = []
                for granularity in multi_granularity_sizes:
                    # Create pipeline for this granularity
                    pipeline = PipelineFactory.create(
                        doc_type=doc_type,
                        static_dir=settings.static_dir,
                        base_url=final_base_url,
                        chunk_size=granularity,
                        chunk_overlap=multi_granularity_overlap,
                        encoding_name=encoding_name,
                        **{k: v for k, v in kwargs.items() if k not in ['multi_granularity_chunk_sizes', 'multi_granularity_chunk_overlap']}
                    )
                    
                    # Load and chunk
                    document = pipeline.load(source, **kwargs)
                    chunks = pipeline.chunk(document, **kwargs)
                    
                    # Update chunk IDs and metadata to include granularity
                    for chunk_index, chunk in enumerate(chunks):
                        chunk.chunk_id = f"{document.source}_{granularity}_{chunk_index}"
                        chunk.metadata["granularity"] = granularity
                        chunk.metadata["chunk_size"] = granularity
                        chunk.metadata["chunk_overlap"] = multi_granularity_overlap
                        if "content_type" not in chunk.metadata:
                            chunk.metadata["content_type"] = "text"
                    
                    all_chunks.extend(chunks)
                
                # Index all chunks
                chunks_indexed = pipeline.index(all_chunks, collection_name, embedder, self.vector_store, **kwargs)
                logger.info(f"Created {len(all_chunks)} multi-granularity chunks using sizes: {multi_granularity_sizes}")
                
                return {
                    "success": True,
                    "document_id": all_chunks[0].document_id if all_chunks else source,
                    "chunks_indexed": chunks_indexed,
                    "collection_name": collection_name,
                    "document_type": doc_type.value,
                    "message": f"Successfully indexed {chunks_indexed} chunks"
                }
            else:
                # Single granularity: use pipeline's process method
                pipeline = PipelineFactory.create(
                    doc_type=doc_type,
                    static_dir=settings.static_dir,
                    base_url=final_base_url,
                    chunk_size=chunk_size or self.chunk_size,
                    chunk_overlap=chunk_overlap or self.chunk_overlap,
                    encoding_name=encoding_name,
                    **kwargs
                )
                
                # Process document: load → chunk → index
                result = pipeline.process(
                    source=source,
                    collection_name=collection_name,
                    embedder=embedder,
                    vector_store=self.vector_store,
                    **kwargs
                )
                
                return result
            
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

