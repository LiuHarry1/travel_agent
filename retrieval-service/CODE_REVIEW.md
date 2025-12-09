# Retrieval Service 代码审查报告

## 未使用的文件

### 1. `app/core/models/chunk.py` ❌
**状态**: 未使用  
**原因**: 
- 定义了 `Chunk` 类，但代码中实际使用的是字典 (`Dict[str, Any]`)
- `retrieval_service.py` 中使用 `ChunkResult = Dict[str, Any]` 而不是 `Chunk` 类
- API schemas 使用 `ChunkResult` (Pydantic model) 而不是这个类

**建议**: 删除此文件

### 2. `app/core/models/query.py` ❌
**状态**: 未使用  
**原因**:
- 定义了 `Query` 类，但 API 中使用的是 `QueryRequest` (Pydantic schema)
- 没有找到任何导入或使用 `Query` 类的地方

**建议**: 删除此文件

### 3. `app/core/exceptions.py` ❌
**状态**: 未使用  
**原因**:
- 定义了多个异常类 (`RetrievalError`, `EmbeddingError`, `VectorStoreError`, `RerankError`, `LLMFilterError`, `PipelineNotFoundError`, `ConfigurationError`)
- 但没有找到任何导入或使用这些异常的地方
- 代码中直接使用 Python 标准异常或 FastAPI 的 HTTPException

**建议**: 删除此文件（如果未来需要可以保留，但目前未被使用）

### 4. `app/core/services/vector_store.py` ❌
**状态**: 未使用  
**原因**:
- 定义了 `VectorStore` 抽象基类接口
- 但 `MilvusClient` 并没有实现这个接口
- 代码中直接使用 `MilvusClient` 而不是通过接口

**建议**: 删除此文件（或者让 `MilvusClient` 实现这个接口，但目前未被使用）

## 可能冗余的文件

### 5. `run.py` ⚠️
**状态**: 与 `main.py` 功能重复  
**原因**:
- `run.py` 使用 `uvicorn.run("app.main:app", ...)` 
- `main.py` 中也有 `if __name__ == "__main__": uvicorn.run(...)`
- 两者功能相同，只是启动方式略有不同

**建议**: 
- 如果 `run.py` 是为了开发时的便捷启动，可以保留
- 或者统一使用一种启动方式，删除另一个

## 代码结构问题

### 6. `app/infrastructure/llm/llm_filter.py`
**状态**: 基类文件，但实现简单  
**问题**:
- `BaseLLMFilter` 只是一个简单的基类，`filter_chunks` 方法直接抛出 `NotImplementedError`
- `MockLLMFilter` 定义在 `__init__.py` 中，而不是单独文件

**建议**: 
- 可以考虑将 `MockLLMFilter` 移到单独文件
- 或者保持现状（如果代码量不大）

## 已使用的文件（保留）

以下文件都在使用中，应该保留：

✅ `app/core/services/embedder.py` - 被 embedders 使用  
✅ `app/core/services/reranker.py` - 被 rerankers 使用  
✅ `app/core/services/llm_filter.py` - 被 llm filters 使用  
✅ `app/infrastructure/vector_store/connection_pool.py` - 被 MilvusClient 和 main.py 使用  
✅ `app/infrastructure/rerankers/mock_reranker.py` - 被 rerankers/__init__.py 使用  
✅ `app/infrastructure/llm/qwen_filter.py` - 被 llm/__init__.py 使用  
✅ `app/api/schemas/config.py` - 被 routes/config.py 使用  
✅ `app/api/schemas/retrieval.py` - 被 routes/retrieval.py 使用  

## 总结

### ✅ 已删除的文件：
1. ✅ `app/core/models/chunk.py` - 已删除
2. ✅ `app/core/models/query.py` - 已删除
3. ✅ `app/core/exceptions.py` - 已删除
4. ✅ `app/core/services/vector_store.py` - 已删除

### ⚠️ 需要评估的文件：
5. `run.py` (与 main.py 功能重复)
   - `run.py`: 使用 `reload=True` (开发模式，支持热重载)
   - `main.py`: 不使用 reload (生产模式)
   - **建议**: 如果 `run.py` 用于开发时的便捷启动，可以保留。否则可以删除，统一使用 `main.py`

### 代码改进建议：
- 考虑统一异常处理策略（如果删除 exceptions.py，确保错误处理一致）
- 考虑是否让 MilvusClient 实现 VectorStore 接口（如果保留接口）
- 考虑将 MockLLMFilter 移到单独文件以提高代码组织性
