# Retrieval System - Quick Start Guide

这是一个完整的RAG检索系统，包含后端服务（retrieval-service）和前端UI（retrieval-ui）。

## 系统架构

1. **多Embedding模型查询**: 使用多个embedding模型在Milvus中查询
2. **去重**: 根据chunk_id去重，保留最佳分数
3. **重排序**: 使用re-rank模型重排序（当前为mock实现）
4. **LLM过滤**: 使用Qwen LLM过滤不相关的chunks
5. **返回结果**: 最终返回相关的chunks

## 后端设置 (retrieval-service)

### 1. 安装依赖

```bash
cd retrieval-service
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件：

```env
# Milvus配置
MILVUS_HOST=localhost
MILVUS_PORT=19530
MILVUS_COLLECTION_NAME=knowledge_base

# Embedding模型（逗号分隔）
EMBEDDING_MODELS=qwen:text-embedding-v2,bge:BAAI/bge-large-en-v1.5

# BGE API URL（如果使用BGE API模式）
BGE_API_URL=http://localhost:8001

# Qwen LLM配置
QWEN_API_KEY=your_dashscope_api_key_here
QWEN_MODEL=qwen-plus

# 检索设置
TOP_K_PER_MODEL=10
RERANK_TOP_K=20
FINAL_TOP_K=10
```

### 3. 启动服务

```bash
python run.py
```

或者：

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

服务将在 `http://localhost:8000` 启动。

## 前端设置 (retrieval-ui)

### 1. 安装依赖

```bash
cd retrieval-ui
npm install
```

### 2. 配置API URL（可选）

创建 `.env` 文件：

```env
VITE_API_BASE_URL=http://localhost:8000
```

### 3. 启动开发服务器

```bash
npm run dev
```

前端将在 `http://localhost:5173` 启动。

## API端点

### 1. 搜索（返回最终结果）

```bash
POST http://localhost:8000/api/v1/retrieval/search
Content-Type: application/json

{
  "query": "你的问题"
}
```

### 2. 搜索（带调试信息）

```bash
POST http://localhost:8000/api/v1/retrieval/search/debug
Content-Type: application/json

{
  "query": "你的问题"
}
```

返回所有中间步骤的结果，用于调试。

## 前端功能

- **查询输入**: 输入问题并搜索
- **步骤展示**: 查看每个步骤的结果：
  - 每个embedding模型的搜索结果
  - 去重后的结果
  - 重排序后的结果
  - LLM过滤后的最终结果
- **可展开/折叠**: 每个步骤可以展开或折叠查看
- **详细信息**: 显示chunk ID、文本、分数等信息

## 注意事项

1. **Milvus连接**: 确保Milvus服务正在运行，并且collection已创建
2. **Embedding模型**: 根据你的需求配置embedding模型
3. **API密钥**: 确保设置了Qwen API密钥（用于LLM过滤）
4. **BGE服务**: 如果使用BGE embedding，确保BGE API服务正在运行

## 故障排除

1. **Milvus连接失败**: 检查Milvus服务是否运行，端口是否正确
2. **Embedding错误**: 检查API密钥和模型配置
3. **LLM过滤失败**: 检查Qwen API密钥是否正确设置
4. **前端无法连接后端**: 检查CORS配置和API URL



给我建立一个retrieval system , 目的是为我的rag chatbot 服务的，一共有两个项目，retrieval-service 和retrieval-ui, 
后端功能是根据多个embedding model 在milvus 知识数据库里做查询。 利用不同embedding查到的所有的结果要用chunk_id 做一下去重复。
然后调用re-rank模型做重排。最后调用大模型（qwen）根据用户的问题进一步去重。最后返回相关chunks. 

re-rank模型暂时没有，你可以mock一下，

后端要有两个api, 一个是返回最终重排结果，chunk_id + text， 还有一个是返回 每一步骤的结果，用于页面的显示，做debug用。
页面上我需要一个可以输入问题，并且可以展示每一个模型的搜索结果，去重复之后的结果，rerank之后的结果， 以及模型过滤没有用的chunk的最总的结果。

后端用python, 前端用react



给我想一下retrieval service 哪些可以配置的。比如我在调用search/debug或者search的时候，需要传入某个项目名字，以及问题，然后这个项目要在retrieval-service 这里根据项目名字查询相应的知识数据库地址，database, 和collection.  然后在 milvus中搜索。 rarank的逻辑应该是可以根据项目名字查询配置的rarank 模型地址，然后调用。llm  evaluation 也是一样，根据项目名字查询具体的llm 然后调用。 还有chunk size 多少在每个步骤中。等等。