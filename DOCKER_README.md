# Docker 部署指南

本文档说明如何使用 Docker 构建和运行 Knowledge Base Builder 项目。

## 项目结构

- `knowledge-base-builder/` - 后端 FastAPI 服务
- `knowledge-base-builder-ui/` - 前端 React 应用

## 快速开始

### 方式 1: 使用 Docker Compose (推荐)

使用 docker-compose 可以一键启动所有服务（包括 Milvus）：

```bash
# 在项目根目录执行
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

服务访问地址：
- 前端: http://localhost
- 后端 API: http://localhost:8000
- API 文档: http://localhost:8000/docs
- Milvus: localhost:19530

### 方式 2: 单独构建镜像

#### 构建后端镜像

```bash
cd knowledge-base-builder
docker build -t knowledge-base-builder:latest .
```

运行后端容器：

```bash
docker run -d \
  --name kb-backend \
  -p 8000:8000 \
  -e MILVUS_HOST=your-milvus-host \
  -e MILVUS_PORT=19530 \
  -v $(pwd)/logs:/app/logs \
  knowledge-base-builder:latest
```

#### 构建前端镜像

```bash
cd knowledge-base-builder-ui
docker build -t knowledge-base-builder-ui:latest .
```

运行前端容器：

```bash
docker run -d \
  --name kb-frontend \
  -p 80:80 \
  knowledge-base-builder-ui:latest
```

## 环境变量

### 后端环境变量

在 `knowledge-base-builder/.env` 文件中配置，或通过 Docker 环境变量传递：

```bash
MILVUS_HOST=milvus          # Milvus 主机地址
MILVUS_PORT=19530          # Milvus 端口
MILVUS_USER=               # Milvus 用户名（可选）
MILVUS_PASSWORD=           # Milvus 密码（可选）
CORS_ORIGINS=http://localhost:80  # CORS 允许的源
DASHSCOPE_API_KEY=         # Qwen API Key（可选）
OPENAI_API_KEY=            # OpenAI API Key（可选）
OPENAI_BASE_URL=           # OpenAI Base URL（可选）
```

### 前端环境变量

前端构建时可以通过环境变量配置 API URL：

```bash
VITE_API_URL=http://localhost:8000
```

## 数据持久化

使用 docker-compose 时，以下数据会被持久化：

- `milvus-data`: Milvus 向量数据
- `etcd-data`: etcd 元数据
- `minio-data`: MinIO 对象存储
- `./knowledge-base-builder/logs`: 应用日志

## 健康检查

两个服务都包含健康检查：

- 后端: `GET /health`
- 前端: nginx 默认健康检查

## 故障排查

### 查看容器日志

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs backend
docker-compose logs frontend
docker-compose logs milvus
```

### 进入容器调试

```bash
# 进入后端容器
docker exec -it knowledge-base-builder-api bash

# 进入前端容器
docker exec -it knowledge-base-builder-ui sh
```

### 清理数据

```bash
# 停止并删除所有容器和数据卷
docker-compose down -v
```

## 生产环境建议

1. **使用环境变量文件**: 创建 `.env` 文件管理敏感信息
2. **配置 HTTPS**: 使用反向代理（如 Traefik 或 Nginx）配置 SSL
3. **资源限制**: 在 docker-compose.yml 中添加资源限制
4. **日志管理**: 配置日志轮转和集中日志管理
5. **备份策略**: 定期备份 Milvus 数据卷

