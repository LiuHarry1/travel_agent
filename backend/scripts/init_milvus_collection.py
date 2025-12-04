"""Script to initialize Milvus collection for travel documents."""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Add backend/app to Python path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.utils.vector_store_service import VectorStoreService


async def main():
    """Initialize Milvus collection."""
    print("Initializing Milvus collection for travel documents...")
    
    # Create vector store service
    vector_store = VectorStoreService()
    
    # Initialize collection
    success = await vector_store.initialize_collection()
    
    if success:
        print(f"✅ Successfully initialized collection '{vector_store.COLLECTION_NAME}'")
        print(f"   - Embedding dimension: {vector_store.EMBEDDING_DIM}")
        print(f"   - Embedding model: {vector_store.EMBEDDING_MODEL}")
    else:
        print(f"❌ Failed to initialize collection '{vector_store.COLLECTION_NAME}'")
        print("   Please check:")
        print("   1. Milvus server is running")
        print("   2. Connection settings are correct")
        print("   3. You have proper permissions")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())



