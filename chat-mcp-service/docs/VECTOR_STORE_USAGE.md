# 向量存储系统使用指南

## 概述

本系统实现了MD文件的分片、向量化和存储到Milvus向量数据库的功能，并提供了语义搜索能力。

## 功能特性

1. **智能文档分片**：混合策略，优先按段落/标题边界切分，超过阈值按字符数切分
2. **向量化存储**：使用Qwen text-embedding-v2模型生成1536维向量
3. **向量检索**：基于Milvus的高性能向量相似度搜索
4. **可扩展设计**：支持未来扩展其他文件类型和embedding模型

## 系统架构

### 核心组件

- **DocumentChunker** (`app/utils/document_processor.py`): 文档分片工具
- **VectorStoreService** (`app/utils/vector_store_service.py`): 向量存储服务
- **RetrieverTool** (`app/mcp_tools/tools/retriever_tool.py`): 检索工具，集成到MCP工具系统

### 数据流程

```
MD文件 → DocumentChunker → 文本分片 → Qwen Embedding API → 向量
                                                              ↓
Milvus Collection ← VectorStoreService ← 元数据+向量
                                                              ↓
查询 → Qwen Embedding API → 查询向量 → Milvus搜索 → 返回Top K结果
```

## 使用步骤

### 1. 初始化Milvus Collection

首先需要初始化Milvus collection：

```bash
cd backend
python scripts/init_milvus_collection.py
```

或者通过代码初始化：

```python
from app.utils.vector_store_service import VectorStoreService

vector_store = VectorStoreService()
await vector_store.initialize_collection()
```

### 2. 处理并存储MD文件

```python
from app.utils.vector_store_service import VectorStoreService

# 创建服务实例
vector_store = VectorStoreService(
    chunk_size=500,      # 分片大小
    chunk_overlap=50,    # 重叠大小
)

# 处理并存储MD文件
await vector_store.process_and_store_markdown(
    file_path="docs/sample_travel_guide.md",
    file_type="md",
)

# 或者直接传入内容
await vector_store.process_and_store_markdown(
    file_path="sample.md",
    content="# 标题\n\n内容...",
    file_type="md",
)
```

### 3. 搜索文档

```python
# 搜索相关chunks
results = await vector_store.search(
    query="日本旅游签证要求",
    limit=10,
)

for result in results:
    print(f"文件: {result['file_name']}")
    print(f"内容: {result['text']}")
    print(f"相似度分数: {result['score']}")
    print("---")
```

### 4. 在RetrieverTool中使用

RetrieverTool已经集成到MCP工具系统中，可以通过chat接口调用：

```python
# 在chat服务中自动使用
# 工具会自动调用RetrieverTool进行向量搜索
```

## Milvus Collection Schema

Collection名称: `travel_documents`

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | INT64 | 主键，自动生成 |
| text | VARCHAR(65535) | chunk文本内容 |
| embedding | FLOAT_VECTOR(1536) | 向量，维度1536 |
| file_name | VARCHAR(255) | 文件名 |
| file_type | VARCHAR(50) | 文件类型（如"md"） |
| chunk_index | INT64 | chunk在文件中的索引 |
| metadata | VARCHAR(65535) | JSON格式的元数据 |

## 配置要求

### 环境变量

- `DASHSCOPE_API_KEY` 或 `QWEN_API_KEY`: Qwen/DashScope API密钥（用于embedding）

### Milvus连接

默认连接参数：
- Host: `localhost`
- Port: `19530`

可以通过MilvusClient自定义：

```python
from app.utils.milvus_client import MilvusClient

milvus_client = MilvusClient(
    host="your-milvus-host",
    port=19530,
    user="",
    password="",
)

vector_store = VectorStoreService(milvus_client=milvus_client)
```

## 分片策略

### 混合分片策略

1. **优先按结构切分**：
   - 识别Markdown标题（# ## ### 等）
   - 按段落边界（双换行）切分
   - 保留语义完整性

2. **字符数切分**：
   - 当段落超过chunk_size阈值时
   - 按字符数切分，带overlap
   - 优先在句子边界或单词边界切分

### 参数配置

- `chunk_size`: 默认500字符，最大chunk大小
- `chunk_overlap`: 默认50字符，chunk之间的重叠
- `min_chunk_size`: 默认100字符，最小chunk大小（小于此值会合并）

## 扩展性

### 添加新的文件类型

未来可以扩展DocumentChunker支持其他文件类型：

```python
# 在document_processor.py中添加
class DocumentChunker:
    def chunk_pdf(self, content: str, file_name: str) -> List[DocumentChunk]:
        # PDF分片逻辑
        pass
    
    def chunk_docx(self, content: str, file_name: str) -> List[DocumentChunk]:
        # DOCX分片逻辑
        pass
```

### 切换Embedding模型

VectorStoreService中定义了embedding模型：

```python
EMBEDDING_MODEL = "text-embedding-v2"  # 可以修改为其他模型
EMBEDDING_DIM = 1536                    # 需要匹配模型的维度
```

## 示例文件

示例MD文件位于：`backend/docs/sample_travel_guide.md`

这是一个完整的日本旅游指南，包含多个章节，适合测试分片和检索功能。

## 故障排除

### Collection未创建

- 检查Milvus服务是否运行
- 检查连接配置是否正确
- 运行初始化脚本

### Embedding失败

- 检查API密钥是否正确设置
- 检查网络连接
- 查看日志错误信息

### 搜索无结果

- 确认已存储文档
- 检查collection是否正确加载
- 尝试更通用的查询词

## 性能优化

1. **批量处理**：一次处理多个文件，减少API调用
2. **索引优化**：使用合适的Milvus索引类型（IVF_FLAT, HNSW等）
3. **连接池**：复用Milvus和API连接
4. **异步处理**：使用异步API提高并发性能

## API参考

详细API文档请参考：
- `app/utils/document_processor.py` - DocumentChunker类
- `app/utils/vector_store_service.py` - VectorStoreService类
- `app/mcp_tools/tools/retriever_tool.py` - RetrieverTool类






