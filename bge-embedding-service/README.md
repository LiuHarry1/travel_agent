# BGE Embedding Service

这是一个独立的 BGE (BAAI General Embedding) embedding 服务，可以在 Docker 中运行，为 knowledge-base-builder 提供 embedding 功能。

## 功能特性

- 支持 BGE large en v1.5 模型（1024 维）
- 通过 HTTP API 提供 embedding 服务
- 支持批量文本 embedding
- 自动归一化 embeddings
- Docker 容器化部署

## 快速开始

### 使用 Docker Compose（推荐）

1. 进入 `bge-embedding-service` 目录：
```bash
cd bge-embedding-service
```

2. 启动服务：
```bash
docker-compose up -d
```

服务将在 `http://localhost:8001` 启动。

### 使用 Docker 直接运行

```bash
docker build -t bge-embedding-service .
docker run -d -p 8001:8000 \
  -e BGE_MODEL_NAME=BAAI/bge-large-en-v1.5 \
  -e BGE_DEVICE=cpu \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  --name bge-embedding \
  bge-embedding-service
```

## 配置

### 环境变量

- `BGE_MODEL_NAME`: 模型名称（默认: `BAAI/bge-large-en-v1.5`）
- `BGE_DEVICE`: 运行设备（`cpu` 或 `cuda`，默认: `cpu`）

### 端口

默认端口：`8001`（映射到容器内的 8000）

## API 使用

### 健康检查

```bash
curl http://localhost:8001/health
```

### 生成 Embeddings

```bash
curl -X POST http://localhost:8001/embed \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["Hello world", "This is a test"],
    "normalize": true
  }'
```

响应示例：
```json
{
  "embeddings": [
    [0.123, 0.456, ...],
    [0.789, 0.012, ...]
  ],
  "dimension": 1024,
  "model": "BAAI/bge-large-en-v1.5"
}
```

## 在 knowledge-base-builder 中使用

### 方法 1: 环境变量

在 knowledge-base-builder 的 `.env` 文件中添加：

```env
BGE_API_URL=http://localhost:8001
```

### 方法 2: 配置文件

在 `knowledge-base-builder/config/settings.py` 中设置：

```python
bge_api_url: str = "http://localhost:8001"
```

### 方法 3: 在代码中传递

```python
from processors.embedders import EmbedderFactory

embedder = EmbedderFactory.create(
    provider="bge",
    model="BAAI/bge-large-en-v1.5",
    api_url="http://localhost:8001"
)
```

## 在前端页面中使用

在 knowledge-base-builder-ui 的配置页面中：

1. 设置 **Embedding Provider** 为 `bge`
2. 设置 **Embedding Model** 为 `BAAI/bge-large-en-v1.5`
3. 确保 BGE API 服务正在运行（`http://localhost:8001`）

## 注意事项

1. **首次启动**：首次运行时会自动下载模型（约 1.3GB），需要一些时间
2. **内存要求**：建议至少 4GB 可用内存
3. **GPU 支持**：如果有 GPU，可以设置 `BGE_DEVICE=cuda` 来加速
4. **模型缓存**：模型文件会缓存在 `~/.cache/huggingface`，避免重复下载

## 故障排除

### 服务无法启动

检查端口是否被占用：
```bash
netstat -an | grep 8001
```

### 模型加载失败

检查日志：
```bash
docker logs bge-embedding-service
```

### 内存不足

在 `docker-compose.yml` 中调整内存限制：
```yaml
deploy:
  resources:
    limits:
      memory: 6G  # 增加内存限制
```

## 停止服务

```bash
docker-compose down
```

或

```bash
docker stop bge-embedding
docker rm bge-embedding
```

