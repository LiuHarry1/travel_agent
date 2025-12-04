@echo off
REM BGE Embedding Service 启动脚本 (Windows)

echo 🚀 Starting BGE Embedding Service...

REM 检查 Docker 是否运行
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Docker is not running. Please start Docker Desktop first.
    exit /b 1
)

REM 启动服务
docker-compose up -d

REM 等待服务启动
echo ⏳ Waiting for service to start...
timeout /t 5 /nobreak >nul

REM 检查服务状态
docker ps | findstr bge-embedding-service >nul
if errorlevel 1 (
    echo ❌ Service failed to start. Check logs with: docker-compose logs
    exit /b 1
) else (
    echo ✅ BGE Embedding Service is running!
    echo.
    echo 📍 Service URL: http://localhost:8001
    echo 📊 Health check: http://localhost:8001/health
    echo.
    echo To view logs: docker-compose logs -f
    echo To stop: docker-compose down
)

