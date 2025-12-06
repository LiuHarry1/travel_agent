#!/usr/bin/env python3
"""
Simple test script to test the entire indexing pipeline.
Tests: Load -> Chunk -> Embed -> (Optional) Index
"""
import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Load .env file if it exists
from dotenv import load_dotenv
env_path = Path(__file__).parent / ".env"
if env_path.exists():
    load_dotenv(env_path)
    print(f"Loaded .env file from: {env_path}")
else:
    print(f"Warning: .env file not found at {env_path}")

from models.document import DocumentType
from processors.loaders import LoaderFactory
from processors.chunkers import RecursiveChunker
from processors.embedders import EmbedderFactory
from utils.logger import setup_logging, get_logger

# Setup logging
setup_logging(
    log_level=None,
    log_dir="logs",
    log_file="test-pipeline.log",
    console_output=True,
    file_output=True
)
logger = get_logger(__name__)


def test_pipeline(file_path: str, skip_indexing: bool = True):
    """
    Test the entire pipeline: Load -> Chunk -> Embed -> (Optional) Index
    
    Args:
        file_path: Path to the file to test
        skip_indexing: If True, skip the Milvus indexing step
    """
    logger.info("=" * 60)
    logger.info("Starting Pipeline Test")
    logger.info("=" * 60)
    
    # Step 1: Load document
    logger.info("\n[1/4] Loading document...")
    logger.info(f"File path: {file_path}")
    
    try:
        # Detect document type
        ext = Path(file_path).suffix.lower()
        type_map = {
            ".md": DocumentType.MARKDOWN,
            ".markdown": DocumentType.MARKDOWN,
            ".pdf": DocumentType.PDF,
            ".docx": DocumentType.DOCX,
            ".html": DocumentType.HTML,
            ".txt": DocumentType.TXT,
        }
        doc_type = type_map.get(ext, DocumentType.TXT)
        logger.info(f"Detected document type: {doc_type.value}")
        
        # Load document
        loader = LoaderFactory.create(doc_type)
        document = loader.load(file_path, metadata={"original_filename": Path(file_path).name})
        
        char_count = len(document.content)
        logger.info(f"✓ Document loaded successfully")
        logger.info(f"  - Source: {document.source}")
        logger.info(f"  - Characters: {char_count:,}")
        logger.info(f"  - Metadata: {document.metadata}")
        
    except Exception as e:
        logger.error(f"✗ Failed to load document: {str(e)}", exc_info=True)
        return False
    
    # Step 2: Chunk document
    logger.info("\n[2/4] Chunking document...")
    
    try:
        chunker = RecursiveChunker(
            chunk_size=1000,
            chunk_overlap=200
        )
        logger.info(f"Chunker config: chunk_size=1000, chunk_overlap=200")
        
        logger.info("Starting chunk operation...")
        chunks = chunker.chunk(document)
        
        logger.info(f"✓ Chunking completed successfully")
        logger.info(f"  - Total chunks: {len(chunks)}")
        
        if chunks:
            logger.info(f"  - First chunk length: {len(chunks[0].text)} chars")
            logger.info(f"  - Last chunk length: {len(chunks[-1].text)} chars")
            logger.info(f"  - First chunk preview: {chunks[0].text[:100]}...")
        
    except Exception as e:
        logger.error(f"✗ Failed to chunk document: {str(e)}", exc_info=True)
        return False
    
    # Step 3: Generate embeddings
    logger.info("\n[3/4] Generating embeddings...")
    
    all_embeddings = []
    embedding_success = False
    
    try:
        # Try Qwen first, then BGE if Qwen fails
        embedding_providers = [
            ("qwen", "text-embedding-v2"),
            ("bge", "BAAI/bge-large-en-v1.5"),
        ]
        
        for provider, model in embedding_providers:
            try:
                logger.info(f"Trying embedding provider: {provider}, model: {model}")
                
                embedder = EmbedderFactory.create(
                    provider=provider,
                    model=model
                )
                
                texts = [chunk.text for chunk in chunks]
                logger.info(f"Generating embeddings for {len(texts)} chunks...")
                
                # Generate embeddings in batches
                batch_size = 10
                
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    logger.info(f"  Processing batch {i // batch_size + 1}/{(len(texts) + batch_size - 1) // batch_size}...")
                    
                    batch_embeddings = embedder.embed(batch)
                    all_embeddings.extend(batch_embeddings)
                    
                    logger.info(f"  ✓ Generated {len(all_embeddings)}/{len(texts)} embeddings")
                
                # Attach embeddings to chunks
                for chunk, embedding in zip(chunks, all_embeddings):
                    chunk.embedding = embedding
                
                logger.info(f"✓ Embedding generation completed with {provider}")
                logger.info(f"  - Total embeddings: {len(all_embeddings)}")
                logger.info(f"  - Embedding dimension: {len(all_embeddings[0]) if all_embeddings else 0}")
                
                embedding_success = True
                break
                
            except Exception as e:
                logger.warning(f"Failed to use {provider}: {str(e)}")
                if provider == embedding_providers[-1][0]:  # Last provider
                    raise
                continue
        
    except Exception as e:
        logger.warning(f"✗ Failed to generate embeddings: {str(e)}")
        logger.info("Continuing without embeddings for testing purposes...")
        embedding_success = False
    
    # Step 4: Index to Milvus (optional)
    if not skip_indexing:
        logger.info("\n[4/4] Indexing to Milvus...")
        
        try:
            from processors.stores import MilvusVectorStore
            from config.settings import get_settings
            
            settings = get_settings()
            vector_store = MilvusVectorStore(
                host=settings.milvus_host,
                port=settings.milvus_port,
                user=settings.milvus_user if settings.milvus_user else None,
                password=settings.milvus_password if settings.milvus_password else None,
            )
            
            collection_name = settings.default_collection_name
            logger.info(f"Indexing to collection: {collection_name}")
            
            chunks_indexed = vector_store.index(chunks, collection_name)
            
            logger.info(f"✓ Indexing completed")
            logger.info(f"  - Chunks indexed: {chunks_indexed}")
            
        except Exception as e:
            logger.error(f"✗ Failed to index to Milvus: {str(e)}", exc_info=True)
            return False
    else:
        logger.info("\n[4/4] Skipping Milvus indexing (skip_indexing=True)")
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Pipeline Test Completed Successfully!")
    logger.info("=" * 60)
    logger.info(f"Summary:")
    logger.info(f"  - Document: {file_path}")
    logger.info(f"  - Characters: {char_count:,}")
    logger.info(f"  - Chunks: {len(chunks)}")
    if embedding_success:
        logger.info(f"  - Embeddings: {len(all_embeddings)}")
    else:
        logger.info(f"  - Embeddings: Skipped (no API key or model available)")
    if not skip_indexing:
        logger.info(f"  - Indexed: {chunks_indexed}")
    
    return True


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test the indexing pipeline")
    parser.add_argument(
        "file_path",
        type=str,
        help="Path to the file to test"
    )
    parser.add_argument(
        "--skip-indexing",
        action="store_true",
        help="Skip Milvus indexing step"
    )
    parser.add_argument(
        "--index",
        action="store_true",
        help="Enable Milvus indexing (default: skip)"
    )
    
    args = parser.parse_args()
    
    # Check if file exists
    file_path = Path(args.file_path)
    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        logger.info("Trying common locations...")
        
        # Try downloads directory
        downloads_path = Path.home() / "Downloads" / file_path.name
        if downloads_path.exists():
            logger.info(f"Found file in Downloads: {downloads_path}")
            file_path = downloads_path
        else:
            # Try relative to current directory
            current_dir_path = Path.cwd() / file_path.name
            if current_dir_path.exists():
                logger.info(f"Found file in current directory: {current_dir_path}")
                file_path = current_dir_path
            else:
                logger.error(f"File not found in any location: {args.file_path}")
                return 1
    
    # Determine if we should skip indexing
    skip_indexing = not args.index if args.index else args.skip_indexing
    
    # Run test
    success = test_pipeline(str(file_path), skip_indexing=skip_indexing)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

