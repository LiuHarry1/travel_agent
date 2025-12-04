#!/bin/bash
# Script to help fix Milvus disk space issues

echo "=========================================="
echo "Milvus Disk Space Fix Script"
echo "=========================================="
echo ""

# Check if running as root (needed for some operations)
if [ "$EUID" -ne 0 ]; then 
    echo "Note: Some operations may require sudo privileges"
    echo ""
fi

# 1. Check disk space
echo "[1] Checking disk space..."
df -h | grep -E "Filesystem|/var|/$" | head -5
echo ""

# 2. Check Milvus processes
echo "[2] Checking Milvus processes..."
if command -v docker &> /dev/null; then
    echo "Docker containers:"
    docker ps | grep -i milvus || echo "  No Milvus containers found"
    echo ""
    
    echo "Docker disk usage:"
    docker system df
    echo ""
fi

# 3. Check /var/lib/milvus if it exists
echo "[3] Checking Milvus data directory..."
if [ -d "/var/lib/milvus" ]; then
    echo "Milvus data directory size:"
    sudo du -sh /var/lib/milvus 2>/dev/null || du -sh /var/lib/milvus 2>/dev/null || echo "  Cannot access /var/lib/milvus"
    
    echo ""
    echo "Largest files in /var/lib/milvus:"
    sudo find /var/lib/milvus -type f -exec ls -lh {} \; 2>/dev/null | sort -k5 -hr | head -10 || \
    find /var/lib/milvus -type f -exec ls -lh {} \; 2>/dev/null | sort -k5 -hr | head -10 || \
    echo "  Cannot access /var/lib/milvus"
else
    echo "  /var/lib/milvus not found (may be in Docker volume)"
fi
echo ""

# 4. Suggestions
echo "[4] Suggested actions:"
echo ""
echo "Option A: Clean Docker (if using Docker)"
echo "  docker system prune -a --volumes"
echo ""
echo "Option B: Clean Milvus logs (if accessible)"
echo "  sudo find /var/lib/milvus -name '*.log' -type f -delete"
echo ""
echo "Option C: Delete unused collections"
echo "  python cleanup_milvus.py --list"
echo "  python cleanup_milvus.py --delete <collection_name>"
echo ""
echo "Option D: Restart Milvus (may help with stuck files)"
if command -v docker &> /dev/null; then
    echo "  docker restart <milvus_container_name>"
else
    echo "  sudo systemctl restart milvus"
fi
echo ""

echo "=========================================="
echo "Script completed"
echo "=========================================="

