#!/usr/bin/env python3
"""
CLI script to index documents into knowledge base.

Usage:
    python index_document.py <file_path> [options]
    
Examples:
    # Index a markdown file with default settings
    python index_document.py document.md
    
    # Index with custom collection and embedding provider
    python index_document.py document.md --collection my_kb --embedding-provider qwen
    
    # Index with custom chunk size
    python index_document.py document.md --chunk-size 2000 --chunk-overlap 400
"""
import argparse
import logging

from models.document import DocumentType
from services.indexing_service import IndexingService
from processors.stores import MilvusVectorStore
from config.settings import get_settings
from utils.exceptions import IndexingError

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Index a document into knowledge base",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    
    parser.add_argument(
        "file_path",
        type=str,
        help="Path to the document file"
    )
    
    parser.add_argument(
        "--doc-type",
        type=str,
        choices=["markdown", "pdf", "docx", "html", "txt"],
        default="markdown",
        help="Document type (default: markdown)"
    )
    
    parser.add_argument(
        "--collection",
        type=str,
        default=None,
        help="Collection name (default: from config)"
    )
    
    parser.add_argument(
        "--embedding-provider",
        type=str,
        choices=["qwen", "openai", "bge"],
        default=None,
        help="Embedding provider (default: from config)"
    )
    
    parser.add_argument(
        "--embedding-model",
        type=str,
        default=None,
        help="Embedding model name (default: from config)"
    )
    
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        help="Chunk size in characters (default: from config)"
    )
    
    parser.add_argument(
        "--chunk-overlap",
        type=int,
        default=None,
        help="Chunk overlap in characters (default: from config)"
    )
    
    parser.add_argument(
        "--milvus-host",
        type=str,
        default=None,
        help="Milvus host (default: from config)"
    )
    
    parser.add_argument(
        "--milvus-port",
        type=int,
        default=None,
        help="Milvus port (default: from config)"
    )
    
    parser.add_argument(
        "--milvus-user",
        type=str,
        default=None,
        help="Milvus user (default: from config)"
    )
    
    parser.add_argument(
        "--milvus-password",
        type=str,
        default=None,
        help="Milvus password (default: from config)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Get settings
    settings = get_settings()
    
    # Validate file exists
    file_path = Path(args.file_path)
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        sys.exit(1)
    
    # Map doc type string to enum
    doc_type_map = {
        "markdown": DocumentType.MARKDOWN,
        "pdf": DocumentType.PDF,
        "docx": DocumentType.DOCX,
        "html": DocumentType.HTML,
        "txt": DocumentType.TXT,
    }
    doc_type = doc_type_map[args.doc_type]
    
    # Setup vector store
    vector_store = MilvusVectorStore(
        host=args.milvus_host or settings.milvus_host,
        port=args.milvus_port or settings.milvus_port,
        user=args.milvus_user or settings.milvus_user,
        password=args.milvus_password or settings.milvus_password
    )
    
    # Setup service
    service = IndexingService(
        vector_store=vector_store,
        chunk_size=args.chunk_size or settings.default_chunk_size,
        chunk_overlap=args.chunk_overlap or settings.default_chunk_overlap
    )
    
    # Get collection name
    collection_name = args.collection or settings.default_collection_name
    
    # Get embedding settings
    embedding_provider = args.embedding_provider or settings.default_embedding_provider
    embedding_model = args.embedding_model or settings.default_embedding_model
    
    # Print configuration
    print("\n" + "=" * 60)
    print("Knowledge Base Builder - Document Indexing")
    print("=" * 60)
    print(f"File: {file_path}")
    print(f"Document Type: {doc_type.value}")
    print(f"Collection: {collection_name}")
    print(f"Embedding Provider: {embedding_provider}")
    if embedding_model:
        print(f"Embedding Model: {embedding_model}")
    print(f"Chunk Size: {service.chunk_size}")
    print(f"Chunk Overlap: {service.chunk_overlap}")
    print(f"Milvus: {vector_store.host}:{vector_store.port}")
    print("=" * 60 + "\n")
    
    # Index document
    try:
        result = service.index_document(
            source=str(file_path),
            doc_type=doc_type,
            collection_name=collection_name,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model if embedding_model else None
        )
        
        if result["success"]:
            print("\n✅ Success!")
            print(f"   Document ID: {result['document_id']}")
            print(f"   Chunks Indexed: {result['chunks_indexed']}")
            print(f"   Collection: {result['collection_name']}")
            print(f"   Message: {result['message']}")
            sys.exit(0)
        else:
            print(f"\n❌ Failed: {result['message']}")
            sys.exit(1)
            
    except IndexingError as e:
        logger.error(f"Indexing error: {str(e)}", exc_info=True)
        print(f"\n❌ Indexing failed: {str(e)}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()

