#!/usr/bin/env python3
"""
Script to help clean up Milvus and free disk space.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from processors.stores import MilvusVectorStore
from config.settings import get_settings
from utils.logger import setup_logging, get_logger

setup_logging(log_level=None, console_output=True, file_output=False)
logger = get_logger(__name__)


def list_collections():
    """List all collections."""
    try:
        settings = get_settings()
        vector_store = MilvusVectorStore(
            host=settings.milvus_host,
            port=settings.milvus_port,
            user=settings.milvus_user if settings.milvus_user else None,
            password=settings.milvus_password if settings.milvus_password else None,
        )
        vector_store._connect()
        
        from pymilvus import utility
        collections = utility.list_collections(using=vector_store.alias)
        return collections
    except Exception as e:
        logger.error(f"Failed to list collections: {str(e)}")
        return []


def delete_collection(collection_name: str):
    """Delete a collection."""
    try:
        settings = get_settings()
        vector_store = MilvusVectorStore(
            host=settings.milvus_host,
            port=settings.milvus_port,
            user=settings.milvus_user if settings.milvus_user else None,
            password=settings.milvus_password if settings.milvus_password else None,
        )
        vector_store._connect()
        
        from pymilvus import utility
        utility.drop_collection(collection_name, using=vector_store.alias)
        logger.info(f"Deleted collection: {collection_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete collection {collection_name}: {str(e)}")
        return False


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up Milvus collections")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all collections"
    )
    parser.add_argument(
        "--delete",
        type=str,
        metavar="COLLECTION_NAME",
        help="Delete a specific collection"
    )
    parser.add_argument(
        "--delete-all",
        action="store_true",
        help="Delete all collections (use with caution!)"
    )
    
    args = parser.parse_args()
    
    if args.list:
        print("=" * 60)
        print("Milvus Collections")
        print("=" * 60)
        collections = list_collections()
        if collections:
            for coll in collections:
                print(f"  - {coll}")
        else:
            print("  No collections found")
        return 0
    
    if args.delete:
        print(f"Deleting collection: {args.delete}")
        confirm = input("Are you sure? (yes/no): ")
        if confirm.lower() == "yes":
            if delete_collection(args.delete):
                print(f"✓ Successfully deleted collection: {args.delete}")
            else:
                print(f"✗ Failed to delete collection: {args.delete}")
                return 1
        else:
            print("Cancelled")
        return 0
    
    if args.delete_all:
        print("WARNING: This will delete ALL collections!")
        confirm = input("Are you sure? Type 'DELETE ALL' to confirm: ")
        if confirm == "DELETE ALL":
            collections = list_collections()
            if collections:
                for coll in collections:
                    print(f"Deleting collection: {coll}")
                    delete_collection(coll)
                print(f"✓ Deleted {len(collections)} collections")
            else:
                print("No collections to delete")
        else:
            print("Cancelled")
        return 0
    
    # Default: show help
    parser.print_help()
    print("\nExamples:")
    print("  python cleanup_milvus.py --list")
    print("  python cleanup_milvus.py --delete my_collection")
    print("  python cleanup_milvus.py --delete-all")
    return 0


if __name__ == "__main__":
    sys.exit(main())

