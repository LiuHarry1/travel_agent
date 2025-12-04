#!/bin/bash
# Quick script to check Docker Desktop settings

echo "=========================================="
echo "Docker Desktop 磁盘设置检查"
echo "=========================================="
echo ""
echo "请按照以下步骤操作："
echo ""
echo "1. 打开 Docker Desktop"
echo "2. 点击右上角的设置图标（齿轮 ⚙️）"
echo "3. 选择 'Resources' > 'Advanced'"
echo "4. 找到 'Disk image size' 设置"
echo "5. 增加磁盘大小（建议 256 GB）"
echo "6. 点击 'Apply & Restart'"
echo ""
echo "=========================================="
echo "当前 Docker 磁盘使用情况："
echo "=========================================="

DOCKER_CMD="/Applications/Docker.app/Contents/Resources/bin/docker"

if command -v "$DOCKER_CMD" &> /dev/null || [ -f "$DOCKER_CMD" ]; then
    $DOCKER_CMD system df 2>/dev/null || echo "无法连接到 Docker，请确保 Docker Desktop 正在运行"
else
    echo "Docker 命令未找到"
fi

echo ""
echo "=========================================="
echo "设置完成后，运行以下命令验证："
echo "=========================================="
echo "docker system df"
echo "python check_docker_milvus.py"
echo ""
