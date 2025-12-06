# Quick Start Guide

## 快速开始

### 1. 安装依赖

```bash
cd kb-builder-service
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件（参考 `.env.example`）：

```bash
# Qwen API Key (必需，如果使用 Qwen embedding)
DASHSCOPE_API_KEY=your_api_key_here

# Milvus 配置（可选，默认值）
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

### 3. 确保 Milvus 运行

确保 Milvus 服务正在运行。如果没有，可以使用 Docker：

```bash
docker run -d --name milvus-standalone \
  -p 19530:19530 \
  -p 9091:9091 \
  milvusdb/milvus:latest
```

### 4. 测试导入文档

使用提供的 CLI 脚本导入文档：

```bash
# 使用默认设置导入 markdown 文件
python index_document.py example.md

# 使用自定义配置
python index_document.py example.md \
  --collection my_knowledge_base \
  --embedding-provider qwen \
  --chunk-size 1000 \
  --chunk-overlap 200
```

### 5. 查看帮助

```bash
python index_document.py --help
```

## 常见用法示例

### 导入单个文档

```bash
python index_document.py document.md
```

### 使用不同的 embedding 提供商

```bash
# 使用 Qwen
python index_document.py document.md --embedding-provider qwen

# 使用 OpenAI
python index_document.py document.md --embedding-provider openai

# 使用 BGE (本地模型)
python index_document.py document.md --embedding-provider bge
```

### 自定义分块大小

```bash
python index_document.py document.md \
  --chunk-size 2000 \
  --chunk-overlap 400
```

### 指定集合名称

```bash
python index_document.py document.md --collection travel_guide
```

## 在 Python 代码中使用

```python
from models.document import DocumentType
from services.indexing_service import IndexingService
from processors.stores import MilvusVectorStore

# 创建服务
vector_store = MilvusVectorStore(host="localhost", port=19530)
service = IndexingService(vector_store=vector_store)

# 导入文档
result = service.index_document(
    source="example.md",
    doc_type=DocumentType.MARKDOWN,
    collection_name="knowledge_base",
    embedding_provider="qwen"
)

print(f"成功导入 {result['chunks_indexed']} 个 chunks")
```

## 故障排除

### 连接 Milvus 失败

- 检查 Milvus 是否运行：`docker ps | grep milvus`
- 检查端口是否正确：默认 19530
- 检查防火墙设置

### Embedding API 错误

- 检查 API key 是否正确设置
- 检查网络连接
- 查看详细日志：使用 `--verbose` 参数

### 文档加载失败

- 检查文件路径是否正确
- 检查文件格式是否支持
- 查看错误日志获取详细信息

