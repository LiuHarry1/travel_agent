#!/bin/bash

# BGE Embedding Service 启动脚本

echo "🚀 Starting BGE Embedding Service..."

# 检查 Docker 是否运行
if ! docker info > /dev/null 2>&1; then
    echo "❌ Error: Docker is not running. Please start Docker Desktop first."
    exit 1
fi

# 启动服务
docker-compose up -d

# 等待服务启动
echo "⏳ Waiting for service to start..."
sleep 5

# 检查服务状态
if docker ps | grep -q bge-embedding-service; then
    echo "✅ BGE Embedding Service is running!"
    echo ""
    echo "📍 Service URL: http://localhost:8001"
    echo "📊 Health check: http://localhost:8001/health"
    echo ""
    echo "To view logs: docker-compose logs -f"
    echo "To stop: docker-compose down"
else
    echo "❌ Service failed to start. Check logs with: docker-compose logs"
    exit 1
fi

