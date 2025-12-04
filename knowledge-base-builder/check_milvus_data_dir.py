#!/usr/bin/env python3
"""
Check Milvus data directory and disk space issues.
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
    """Check Milvus data directory."""
    print("=" * 60)
    print("Milvus Data Directory Check")
    print("=" * 60)
    
    # Check actual data directory
    data_dirs = [
        Path("/Users/harry/volumes/milvus"),
        Path("/var/lib/milvus"),
        Path.home() / ".milvus",
        Path.home() / ".milvus_lite",
    ]
    
    print("\n[1] Checking Milvus data directories:")
    for data_dir in data_dirs:
        if data_dir.exists():
            import shutil
            try:
                total, used, free = shutil.disk_usage(data_dir)
                print(f"\n  {data_dir}:")
                print(f"    Total: {total // (1024**3)} GB")
                print(f"    Used:  {used // (1024**3)} GB")
                print(f"    Free:  {free // (1024**3)} GB")
                print(f"    Usage: {used / total * 100:.1f}%")
                
                # Check for large log files
                log_files = list(data_dir.rglob("*.log"))
                if log_files:
                    print(f"    Log files: {len(log_files)}")
                    large_logs = sorted(log_files, key=lambda x: x.stat().st_size, reverse=True)[:5]
                    for log_file in large_logs:
                        size_mb = log_file.stat().st_size / (1024**2)
                        if size_mb > 1:
                            print(f"      {log_file.name}: {size_mb:.2f} MB")
            except Exception as e:
                print(f"    Error checking {data_dir}: {e}")
        else:
            print(f"  {data_dir}: not found")
    
    # Check system disk
    print("\n[2] System disk space:")
    import shutil
    total, used, free = shutil.disk_usage("/")
    print(f"  Total: {total // (1024**3)} GB")
    print(f"  Used:  {used // (1024**3)} GB")
    print(f"  Free:  {free // (1024**3)} GB")
    print(f"  Usage: {used / total * 100:.1f}%")
    
    # Check /var/lib specifically
    print("\n[3] /var/lib disk space:")
    try:
        total, used, free = shutil.disk_usage("/var/lib")
        print(f"  Total: {total // (1024**3)} GB")
        print(f"  Used:  {used // (1024**3)} GB")
        print(f"  Free:  {free // (1024**3)} GB")
        print(f"  Usage: {used / total * 100:.1f}%")
        
        if Path("/var/lib/milvus").exists():
            print(f"  /var/lib/milvus exists")
            try:
                import os
                print(f"  Writable: {os.access('/var/lib/milvus', os.W_OK)}")
            except:
                pass
        else:
            print(f"  /var/lib/milvus does not exist")
    except Exception as e:
        print(f"  Cannot check /var/lib: {e}")
    
    print("\n" + "=" * 60)
    print("Recommendations:")
    print("=" * 60)
    print("If /var/lib/milvus is the issue:")
    print("1. Milvus may be trying to write to /var/lib/milvus but it doesn't exist")
    print("2. Create the directory: sudo mkdir -p /var/lib/milvus")
    print("3. Set permissions: sudo chown -R $USER /var/lib/milvus")
    print("4. Or configure Milvus to use a different data directory")
    print("\nIf using Docker:")
    print("1. Check Docker volume location")
    print("2. Clean up old volumes: docker volume prune")


if __name__ == "__main__":
    main()

