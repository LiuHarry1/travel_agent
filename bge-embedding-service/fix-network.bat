@echo off
REM 修复网络问题的脚本 (Windows)

echo 🔧 配置 Docker 镜像加速器...

docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Error: Docker is not running. Please start Docker Desktop first.
    exit /b 1
)

echo.
echo 请按照以下步骤配置 Docker 镜像加速器：
echo.
echo 1. 打开 Docker Desktop
echo 2. 进入 Settings → Docker Engine
echo 3. 添加以下配置到 JSON 中：
echo.
echo {
echo   "registry-mirrors": [
echo     "https://docker.mirrors.ustc.edu.cn",
echo     "https://hub-mirror.c.163.com",
echo     "https://mirror.baidubce.com"
echo   ]
echo }
echo.
echo 4. 点击 'Apply ^& Restart'
echo 5. 等待 Docker 重启后，重新运行: docker compose up -d
echo.

pause

