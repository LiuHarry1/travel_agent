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
            # 使用统一加载器，传入 static_dir 和 base_url 配置
            from config.settings import get_settings
            settings = get_settings()
            # 优先使用传入的 base_url，否则使用配置的 static_base_url
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
            
            chunker = ChunkerFactory.create(
                doc_type=doc_type,
                chunk_size=chunk_size or self.chunk_size,
                chunk_overlap=chunk_overlap or self.chunk_overlap
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
    
    def _enrich_with_locations(self, chunks: List, doc_type: DocumentType) -> List:
        """Enrich chunks with location information."""
        extractor = LocationExtractor()
        
        for chunk in chunks:
            # 如果chunk已经有location信息（从chunker设置），跳过
            if chunk.location:
                continue
            
            # 从metadata获取位置信息
            start_pos = chunk.metadata.get("start_pos", 0)
            end_pos = chunk.metadata.get("end_pos", len(chunk.text))
            
            # 根据文件类型提取位置信息
            if doc_type == DocumentType.PDF:
                chunk.location = extractor.extract_for_pdf(chunk.text, start_pos, end_pos)
            elif doc_type == DocumentType.DOCX:
                chunk.location = extractor.extract_for_docx(chunk.text, start_pos, end_pos)
            elif doc_type == DocumentType.HTML:
                chunk.location = extractor.extract_for_html(chunk.text, start_pos, end_pos)
            elif doc_type == DocumentType.MARKDOWN:
                chunk.location = extractor.extract_for_markdown(chunk.text, start_pos, end_pos)
            else:
                # 默认：只设置基本位置信息
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

