#!/bin/bash

# 修复网络问题的脚本

echo "🔧 配置 Docker 镜像加速器..."

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker Desktop first."
    exit 1
fi

echo ""
echo "请按照以下步骤配置 Docker 镜像加速器："
echo ""
echo "1. 打开 Docker Desktop"
echo "2. 进入 Settings → Docker Engine"
echo "3. 添加以下配置到 JSON 中："
echo ""
cat << 'EOF'
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
EOF
echo ""
echo "4. 点击 'Apply & Restart'"
echo "5. 等待 Docker 重启后，重新运行: docker compose up -d"
echo ""

