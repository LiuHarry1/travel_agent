#!/usr/bin/env python3
"""
Diagnostic script to check Milvus disk space and connection.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from processors.stores import MilvusVectorStore
from config.settings import get_settings
from utils.logger import setup_logging, get_logger

setup_logging(log_level=None, console_output=True, file_output=False)
logger = get_logger(__name__)


def main():
    """Check Milvus status and disk space."""
    print("=" * 60)
    print("Milvus Diagnostic Tool")
    print("=" * 60)
    
    # Check system disk space
    print("\n[1] System Disk Space:")
    import shutil
    total, used, free = shutil.disk_usage("/")
    print(f"  Total: {total // (1024**3)} GB")
    print(f"  Used:  {used // (1024**3)} GB")
    print(f"  Free:  {free // (1024**3)} GB")
    print(f"  Usage: {used / total * 100:.1f}%")
    
    # Check Milvus connection
    print("\n[2] Milvus Connection:")
    settings = get_settings()
    try:
        vector_store = MilvusVectorStore(
            host=settings.milvus_host,
            port=settings.milvus_port,
            user=settings.milvus_user if settings.milvus_user else None,
            password=settings.milvus_password if settings.milvus_password else None,
        )
        vector_store._connect()
        print(f"  ✓ Connected to Milvus at {settings.milvus_host}:{settings.milvus_port}")
        
        # List collections
        print("\n[3] Existing Collections:")
        try:
            from pymilvus import utility
            collections = utility.list_collections(using=vector_store.alias)
            if collections:
                print(f"  Found {len(collections)} collections:")
                for coll_name in collections:
                    print(f"    - {coll_name}")
            else:
                print("  No collections found")
        except Exception as e:
            print(f"  ✗ Failed to list collections: {str(e)}")
            
    except Exception as e:
        print(f"  ✗ Failed to connect: {str(e)}")
        print("\n  Suggestions:")
        print("  1. Check if Milvus is running")
        print("  2. Verify host and port settings")
        print("  3. Check Milvus logs for errors")
    
    # Docker check
    print("\n[4] Docker Status (if using Docker):")
    import subprocess
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=milvus", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            containers = result.stdout.strip().split('\n')
            print(f"  Found Milvus containers: {', '.join(containers)}")
            print("\n  To check container disk usage:")
            for container in containers:
                print(f"    docker exec {container} df -h")
        else:
            print("  No Milvus Docker containers found")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("  Docker not available or not installed")
    
    print("\n" + "=" * 60)
    print("Diagnostic Complete")
    print("=" * 60)
    print("\nIf you see 'No space left on device' errors:")
    print("1. If using Docker: docker system prune -a --volumes")
    print("2. Clean up old Milvus logs")
    print("3. Delete unused collections")
    print("4. Check Milvus data directory: /var/lib/milvus (or Docker volume)")


if __name__ == "__main__":
    main()

