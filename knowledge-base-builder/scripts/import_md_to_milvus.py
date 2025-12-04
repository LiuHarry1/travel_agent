"""Script to import markdown file into Milvus vector database."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add backend/app to Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.utils.vector_store_service import VectorStoreService
from app.logger import get_logger

logger = get_logger(__name__)


async def import_md_file(file_path: str, file_type: str = "md"):
    """
    Import a markdown file into Milvus.
    
    Args:
        file_path: Path to the markdown file
        file_type: File type identifier (default: "md")
    """
    # Resolve file path
    file = Path(file_path)
    if not file.is_absolute():
        # If relative path, resolve relative to backend directory
        file = backend_path / file_path
    
    if not file.exists():
        print(f"❌ File not found: {file}")
        print(f"   Please provide the correct path to the markdown file.")
        sys.exit(1)
    
    print(f"📄 Importing file: {file}")
    print(f"   File size: {file.stat().st_size:,} bytes")
    
    # Create vector store service
    print("\n🔧 Initializing vector store service...")
    vector_store = VectorStoreService(
        chunk_size=500,
        chunk_overlap=50,
    )
    
    # Initialize collection if needed
    print("📦 Checking/initializing Milvus collection...")
    if not await vector_store.initialize_collection():
        print("❌ Failed to initialize Milvus collection")
        print("   Please check:")
        print("   1. Milvus server is running")
        print("   2. Connection settings are correct")
        sys.exit(1)
    
    print(f"✅ Collection '{vector_store.COLLECTION_NAME}' is ready\n")
    
    # Process and store the file
    print("🔄 Processing file...")
    print("   - Chunking document...")
    print("   - Generating embeddings...")
    print("   - Storing in Milvus...")
    
    try:
        success = await vector_store.process_and_store_markdown(
            file_path=str(file),
            content=None,  # Read from file
            file_type=file_type,
        )
        
        if success:
            print(f"\n✅ Successfully imported '{file.name}' into Milvus!")
            print(f"   Collection: {vector_store.COLLECTION_NAME}")
            print(f"   File type: {file_type}")
            
            # Get collection stats
            stats = vector_store.milvus_client.get_collection_stats(vector_store.COLLECTION_NAME)
            if stats:
                print(f"   Total entities in collection: {stats.get('num_entities', 'N/A')}")
        else:
            print(f"\n❌ Failed to import file")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error importing file: {e}")
        logger.error(f"Import error: {e}", exc_info=True)
        sys.exit(1)


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Import markdown file into Milvus vector database"
    )
    parser.add_argument(
        "file_path",
        nargs="?",
        default="docs/sample_travel_guide.md",
        help="Path to the markdown file to import (default: docs/sample_travel_guide.md)",
    )
    parser.add_argument(
        "--file-type",
        default="md",
        help="File type identifier (default: md)",
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("📚 Markdown File Import Tool")
    print("=" * 60)
    print()
    
    await import_md_file(args.file_path, args.file_type)


if __name__ == "__main__":
    asyncio.run(main())


