#!/bin/bash
# Script to fix Docker Milvus disk space issues

DOCKER_CMD="/Applications/Docker.app/Contents/Resources/bin/docker"

echo "=========================================="
echo "Docker Milvus Space Fix"
echo "=========================================="
echo ""

# 1. Check current status
echo "[1] Current Docker disk usage:"
$DOCKER_CMD system df
echo ""

# 2. Clean up options
echo "[2] Available cleanup options:"
echo ""
echo "Option A: Clean up unused containers, networks, images (safe)"
echo "  $DOCKER_CMD system prune"
echo ""
echo "Option B: Clean up everything including volumes (WARNING: may delete data)"
echo "  $DOCKER_CMD system prune -a --volumes"
echo ""
echo "Option C: Clean up only unused images"
echo "  $DOCKER_CMD image prune -a"
echo ""
echo "Option D: Clean up build cache"
echo "  $DOCKER_CMD builder prune -a"
echo ""

# 3. Check Milvus container
echo "[3] Milvus container status:"
MILVUS_CONTAINER=$($DOCKER_CMD ps --filter "name=milvus-standalone" -q)
if [ -n "$MILVUS_CONTAINER" ]; then
    echo "  Container ID: $MILVUS_CONTAINER"
    echo "  Container disk usage:"
    $DOCKER_CMD exec $MILVUS_CONTAINER df -h /var/lib/milvus 2>/dev/null || echo "    Cannot check"
    echo ""
    echo "  To restart Milvus:"
    echo "    $DOCKER_CMD restart $MILVUS_CONTAINER"
else
    echo "  Milvus container not found"
fi
echo ""

# 4. Docker Desktop settings
echo "[4] Docker Desktop Settings:"
echo "  To increase disk space:"
echo "  1. Open Docker Desktop"
echo "  2. Go to Settings (gear icon)"
echo "  3. Resources > Advanced"
echo "  4. Increase 'Disk image size' (default is usually 64GB)"
echo "  5. Click 'Apply & Restart'"
echo ""

# 5. Quick fix - clean up unused resources
echo "[5] Quick fix - Clean up unused Docker resources:"
read -p "Do you want to clean up unused Docker resources? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "  Cleaning up unused containers, networks, and images..."
    $DOCKER_CMD system prune -f
    echo "  ✓ Cleanup completed"
    echo ""
    echo "  New disk usage:"
    $DOCKER_CMD system df
fi

echo ""
echo "=========================================="
echo "Additional Notes:"
echo "=========================================="
echo "If the issue persists:"
echo "1. Check Docker Desktop disk image size in Settings"
echo "2. Restart Milvus container: $DOCKER_CMD restart milvus-standalone"
echo "3. Check if Milvus logs are taking too much space"
echo "4. Consider moving Milvus data to a different location"
echo ""

