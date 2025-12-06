# MD文件导入Milvus脚本使用说明

## 脚本位置

`backend/scripts/import_md_to_milvus.py`

## 功能

将Markdown文件导入到Milvus向量数据库，包括：
- 文档分片
- 生成向量embeddings
- 存储到Milvus collection

## 使用方法

### 1. 基本使用（导入默认示例文件）

```bash
cd backend
python scripts/import_md_to_milvus.py
```

这会导入 `docs/sample_travel_guide.md` 文件。

### 2. 导入指定文件

```bash
python scripts/import_md_to_milvus.py docs/sample_travel_guide.md
```

或者使用绝对路径：

```bash
python scripts/import_md_to_milvus.py /path/to/your/file.md
```

### 3. 指定文件类型

```bash
python scripts/import_md_to_milvus.py docs/sample_travel_guide.md --file-type md
```

### 4. 查看帮助

```bash
python scripts/import_md_to_milvus.py --help
```

## 前置条件

### 1. Milvus服务运行

确保Milvus服务正在运行：

```bash
# 使用Docker运行Milvus（如果使用Docker）
docker run -d --name milvus-standalone \
  -p 19530:19530 \
  -p 9091:9091 \
  milvusdb/milvus:latest
```

### 2. 环境变量配置

设置Qwen/DashScope API密钥：

```bash
# Windows PowerShell
$env:DASHSCOPE_API_KEY="your-api-key"

# Linux/Mac
export DASHSCOPE_API_KEY="your-api-key"
```

或者设置 `QWEN_API_KEY`：

```bash
export QWEN_API_KEY="your-api-key"
```

### 3. Python依赖

确保已安装所需依赖：

```bash
pip install pymilvus openai
```

## 使用示例

### 示例1：导入示例文件

```bash
cd backend
python scripts/import_md_to_milvus.py docs/sample_travel_guide.md
```

输出示例：

```
============================================================
📚 Markdown File Import Tool
============================================================

📄 Importing file: C:\Users\...\backend\docs\sample_travel_guide.md
   File size: 15,234 bytes

🔧 Initializing vector store service...
📦 Checking/initializing Milvus collection...
✅ Collection 'travel_documents' is ready

🔄 Processing file...
   - Chunking document...
   - Generating embeddings...
   - Storing in Milvus...

✅ Successfully imported 'sample_travel_guide.md' into Milvus!
   Collection: travel_documents
   File type: md
   Total entities in collection: 45
```

### 示例2：导入自定义文件

```bash
python scripts/import_md_to_milvus.py my_custom_guide.md --file-type md
```

## 脚本功能说明

脚本执行以下步骤：

1. **检查文件存在**：验证提供的文件路径是否有效
2. **初始化服务**：创建VectorStoreService实例
3. **初始化Collection**：检查或创建Milvus collection
4. **处理文件**：
   - 读取MD文件内容
   - 使用DocumentChunker进行分片
   - 使用Qwen API生成embeddings
   - 存储到Milvus
5. **显示结果**：显示导入结果和统计信息

## 故障排除

### 错误：File not found

**原因**：文件路径不正确

**解决**：
- 检查文件路径是否正确
- 使用绝对路径或相对于backend目录的相对路径

### 错误：Failed to initialize Milvus collection

**原因**：Milvus服务未运行或连接配置错误

**解决**：
1. 检查Milvus服务是否运行：
   ```bash
   # Docker
   docker ps | grep milvus
   
   # 或者尝试连接
   telnet localhost 19530
   ```

2. 检查Milvus连接配置（默认：localhost:19530）

### 错误：Failed to generate query embedding

**原因**：API密钥未设置或无效

**解决**：
1. 检查环境变量：
   ```bash
   echo $DASHSCOPE_API_KEY
   ```

2. 设置正确的API密钥

### 错误：Import failed

**原因**：可能的原因包括：
- API调用失败
- Milvus写入失败
- 文件格式问题

**解决**：
- 查看详细错误日志
- 检查网络连接
- 验证文件内容格式

## 参数说明

| 参数 | 说明 | 默认值 | 必需 |
|------|------|--------|------|
| `file_path` | MD文件路径 | `docs/sample_travel_guide.md` | 否 |
| `--file-type` | 文件类型标识 | `md` | 否 |

## 输出说明

成功导入后，脚本会显示：
- 导入的文件名
- Collection名称
- 文件类型
- Collection中的实体总数（包括之前导入的数据）

## 后续操作

导入成功后，你可以：

1. **使用RetrieverTool搜索**：
   - 通过chat接口调用retriever工具
   - 使用自然语言查询搜索文档内容

2. **查看collection信息**：
   ```python
   from app.utils.milvus_client import MilvusClient
   
   client = MilvusClient()
   client.connect()
   info = client.get_collection_info("travel_documents")
   print(info)
   ```

3. **直接搜索**：
   ```python
   from app.utils.vector_store_service import VectorStoreService
   
   vector_store = VectorStoreService()
   results = await vector_store.search("日本旅游签证", limit=10)
   ```

## 注意事项

1. **重复导入**：如果同一个文件被多次导入，会产生重复的数据。如需更新，建议先删除旧数据。

2. **文件大小**：大文件会生成大量chunks，可能需要较长时间处理。

3. **API限制**：注意Qwen API的调用频率限制。

4. **网络连接**：需要稳定的网络连接到Milvus和DashScope API。






