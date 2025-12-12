# PDF Loading, Chunking, Indexing 和 Location Tracking 完整重写计划

## 一、项目概述

### 1.1 目标
彻底重写 PDF 处理流程，使用 `pymupdf4llm` 替代现有方案，并建立完整的 location tracking 系统，与 chat-service、chat-ui、retrieval-service 集成。

### 1.2 范围
- **kb-builder-service**: PDF loading, chunking, indexing
- **retrieval-service**: Location metadata 返回
- **chat-service**: Citation 生成和 location 传递
- **chat-ui**: Location 显示和 PDF 导航

## 二、架构设计

### 2.1 数据流

```
PDF 文件
  ↓
PDF Loader (pymupdf4llm)
  ↓
PDF Extractor (提取内容 + location metadata)
  ↓
PDF Chunker (分块 + 增强 location)
  ↓
Indexing Service (索引 + 存储 location)
  ↓
Milvus (存储 chunks + location metadata)
  ↓
Retrieval Service (返回 chunks + location)
  ↓
Chat Service (生成 citations)
  ↓
Chat UI (显示 citations + PDF 导航)
```

### 2.2 Location Tracking 架构

```
ChunkLocation (模型)
  ├── 基础位置 (page, bbox, char positions)
  ├── 表格位置 (table_index, row_range, column_range)
  ├── 图片位置 (image_index, image_url)
  └── 导航信息 (navigation_url, highlight_bbox)
  ↓
存储到 Milvus (metadata 字段)
  ↓
Retrieval Service 返回
  ↓
Chat Service 生成 citation
  ↓
Chat UI 显示和导航
```

## 三、详细实施计划

### 阶段 1: PDF Loading 重写 (kb-builder-service)

#### 1.1 重写 PDF Extractor

**文件**: `kb-builder-service/processors/loaders/pdf/pdf_extractor.py`

**核心功能**:
1. 使用 `pymupdf4llm.to_markdown(page_chunks=True)` 获取分页内容
2. 从 `chunk['metadata']['page']` 获取页面号
3. 从 `chunk['tables']` 提取表格元数据
4. 从 `chunk['images']` 提取图片信息
5. 使用 PyMuPDF 直接提取图片（不使用 write_images）
6. 从 Markdown 文本解析标题
7. 构建增强的 DocumentStructure

**关键实现**:
```python
def extract(self, path: Path, file_id: str, ...):
    # 1. 获取分页内容
    page_chunks = pymupdf4llm.to_markdown(str(path), page_chunks=True, write_images=False)
    
    # 2. 打开 PyMuPDF
    doc = fitz.open(str(path))
    
    # 3. 处理每页
    for chunk in page_chunks:
        page_num = chunk['metadata']['page']
        page_text = chunk.get('text', '')
        
        # 提取表格信息（包含 bbox）
        tables_info = extract_tables_from_chunk(chunk, page_num, doc)
        
        # 提取图片
        images_info = extract_images_from_chunk(chunk, page_num, doc, file_id)
        
        # 添加页面标记
        # 合并内容
    
    # 4. 提取标题
    headings = extract_headings_from_markdown(full_md)
    
    # 5. 构建 DocumentStructure
    return markdown_content, structure
```

**表格提取**:
```python
def extract_tables_from_chunk(chunk, page_num, doc):
    """从 chunk 提取表格信息，包含 bbox 用于定位"""
    tables_info = []
    page_obj = doc[page_num - 1]
    
    for table_idx, table in enumerate(chunk.get('tables', [])):
        bbox = table.get('bbox')
        rows = table.get('rows', 0)
        cols = table.get('columns', 0)
        
        # 从 bbox 提取表格内容
        if bbox:
            table_content = extract_table_by_bbox(page_obj, bbox)
        else:
            table_content = ""
        
        tables_info.append({
            'page': page_num,
            'index': len(tables_info),
            'rows': rows,
            'columns': cols,
            'bbox': list(bbox) if bbox else None,
            'has_header': True,  # 需要检测
            'content_preview': table_content[:200] if table_content else None
        })
    
    return tables_info
```

#### 1.2 更新 PDF Loader

**文件**: `kb-builder-service/processors/loaders/pdf/pdf_loader.py`

**改动**:
- 移除 `pdfplumber` 依赖
- 添加 `pymupdf4llm` 检查
- 简化逻辑

#### 1.3 删除废弃代码

- 删除 `kb-builder-service/processors/loaders/pdf/heading_detector.py`

### 阶段 2: PDF Chunking 重写 (kb-builder-service)

#### 2.1 重写 PDF Chunker

**文件**: `kb-builder-service/processors/chunkers/pdf_chunker.py`

**核心功能**:
1. 处理标准 Markdown 表格
2. 根据表格大小采用不同 chunking 策略
3. 为每个 chunk 生成增强的 location metadata
4. 支持表格跨页情况

**表格 Chunking 策略**:
```python
def chunk_table(table_info, table_content, chunk_size=1000):
    """
    根据表格大小决定 chunking 策略
    
    - 小表格 (≤10行): 单个 chunk
    - 中等表格 (11-30行): 按行分组，每 5-10 行
    - 大表格 (>30行): 按行分组，每组保留表头
    """
    rows = table_info['rows']
    
    if rows <= 10:
        # 小表格：单个 chunk
        return [create_table_chunk(...)]
    elif rows <= 30:
        # 中等表格：按行分组
        return split_table_by_rows(table_content, rows_per_chunk=8)
    else:
        # 大表格：按行分组 + 保留表头
        return split_table_by_rows_with_header(table_content, rows_per_chunk=12)
```

**Location Metadata 增强**:
```python
def create_table_chunk(..., table_info, row_range=None):
    """创建表格 chunk，包含完整的 location 信息"""
    location = ChunkLocation(
        start_char=start_pos,
        end_char=end_pos,
        page_number=table_info['page'],
        page_bbox={'x0': bbox[0], 'y0': bbox[1], 'x1': bbox[2], 'y1': bbox[3]},
        table_index=table_info['index'],
        table_cell=None  # 可选：单元格位置
    )
    
    # 添加 row_range 到 metadata
    metadata = {
        **document.metadata,
        'table_row_range': f"{row_range[0]}-{row_range[1]}" if row_range else None,
        'table_rows': table_info['rows'],
        'table_columns': table_info['columns'],
        'table_bbox': table_info['bbox'],
        'content_type': 'table'
    }
    
    return Chunk(..., location=location, metadata=metadata)
```

#### 2.2 更新 ChunkLocation 模型

**文件**: `kb-builder-service/models/chunk.py`

**增强字段**:
```python
@dataclass
class ChunkLocation:
    # ... 现有字段 ...
    
    # 新增：表格行范围
    table_row_range: Optional[Tuple[int, int]] = None  # (start_row, end_row)
    
    # 新增：导航信息
    navigation_url: Optional[str] = None  # PDF 导航 URL
    highlight_bbox: Optional[List[float]] = None  # 高亮区域 bbox
    
    def get_table_citation(self) -> str:
        """生成表格 citation"""
        parts = [f"Table {self.table_index}"]
        if self.page_number:
            parts.append(f"Page {self.page_number}")
        if self.table_row_range:
            parts.append(f"Rows {self.table_row_range[0]}-{self.table_row_range[1]}")
        return ", ".join(parts)
    
    def get_navigation_url(self, base_url: str, pdf_path: str) -> str:
        """生成 PDF 导航 URL"""
        params = {
            'page': self.page_number,
            'bbox': ','.join(map(str, self.highlight_bbox or []))
        }
        if self.table_row_range:
            params['rows'] = f"{self.table_row_range[0]}-{self.table_row_range[1]}"
        
        query = '&'.join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}/api/v1/sources/{pdf_path}?{query}"
```

### 阶段 3: Indexing 更新 (kb-builder-service)

#### 3.1 更新 Indexing Service

**文件**: `kb-builder-service/services/indexing_service.py`

**改动**:
- 确保 location metadata 正确存储到 Milvus
- 添加表格 location 的特殊处理
- 生成 navigation URLs

**关键实现**:
```python
def index_document(...):
    # ... 现有逻辑 ...
    
    # 在存储前，为每个 chunk 生成 navigation URL
    for chunk in chunks:
        if chunk.location:
            chunk.location.navigation_url = generate_navigation_url(
                chunk, base_url, pdf_path
            )
            chunk.location.highlight_bbox = get_highlight_bbox(chunk)
    
    # 存储到 Milvus（location 在 metadata 中）
    chunks_indexed = self.vector_store.index(chunks, collection_name)
```

#### 3.2 更新 Milvus Vector Store

**文件**: `kb-builder-service/processors/stores/milvus.py`

**确保**:
- Location metadata 正确序列化
- 表格 location 信息完整存储

### 阶段 4: Retrieval Service 更新

#### 4.1 更新 Retrieval Response Schema

**文件**: `retrieval-service/app/api/schemas/retrieval.py`

**增强 ChunkResult**:
```python
class ChunkLocation(BaseModel):
    """Chunk location information."""
    page_number: Optional[int] = None
    table_index: Optional[int] = None
    table_row_range: Optional[Tuple[int, int]] = None
    bbox: Optional[List[float]] = None
    navigation_url: Optional[str] = None

class ChunkResult(BaseModel):
    """Chunk result model with location."""
    chunk_id: int
    text: str
    score: Optional[float] = None
    location: Optional[ChunkLocation] = None
    metadata: Optional[Dict[str, Any]] = None
```

#### 4.2 更新 Retrieval Service

**文件**: `retrieval-service/app/services/retrieval_service.py`

**改动**:
```python
def _format_hit_result(self, hit: Any, embedder_name: str) -> Optional[ChunkResult]:
    """提取 chunk 数据，包括 location"""
    # ... 现有逻辑 ...
    
    # 从 entity 提取 location
    if isinstance(entity, dict):
        text = entity.get("text", "")
        location_dict = entity.get("location", {})
        metadata = entity.get("metadata", {})
    else:
        text = getattr(entity, "text", "")
        location_dict = getattr(entity, "location", {})
        metadata = getattr(entity, "metadata", {})
    
    # 构建 location 对象
    location = None
    if location_dict:
        location = ChunkLocation(**location_dict)
    
    return {
        "chunk_id": chunk_id,
        "text": text or "",
        "score": distance,
        "embedder": embedder_name,
        "location": location,
        "metadata": metadata
    }
```

### 阶段 5: Chat Service 更新

#### 5.1 更新 Chat Service

**文件**: `chat-service/app/service/chat_service.py` (或相应文件)

**功能**:
- 从 retrieval results 提取 location
- 生成 citations
- 传递 location 信息给 LLM

**实现**:
```python
def format_retrieval_results(results: List[ChunkResult]) -> str:
    """格式化检索结果，包含 citations"""
    formatted = []
    for i, result in enumerate(results, 1):
        citation = generate_citation(result)
        formatted.append(f"[{i}] {result.text}\nSource: {citation}")
    return "\n\n".join(formatted)

def generate_citation(chunk_result: ChunkResult) -> str:
    """生成 citation 文本"""
    location = chunk_result.location
    if not location:
        return chunk_result.metadata.get('document_id', 'Unknown')
    
    parts = []
    if location.table_index is not None:
        parts.append(f"Table {location.table_index}")
    if location.page_number:
        parts.append(f"Page {location.page_number}")
    if location.table_row_range:
        parts.append(f"Rows {location.table_row_range[0]}-{location.table_row_range[1]}")
    
    return ", ".join(parts) if parts else chunk_result.metadata.get('document_id', 'Unknown')
```

### 阶段 6: Chat UI 更新

#### 6.1 更新 API Types

**文件**: `chat-ui/src/types.ts`

**添加**:
```typescript
export interface ChunkLocation {
  page_number?: number;
  table_index?: number;
  table_row_range?: [number, number];
  bbox?: number[];
  navigation_url?: string;
}

export interface ChunkResult {
  chunk_id: number;
  text: string;
  score?: number;
  location?: ChunkLocation;
  metadata?: Record<string, any>;
}
```

#### 6.2 创建 Citation 组件

**文件**: `chat-ui/src/components/Citation.tsx`

**功能**:
- 显示 citation 文本
- 点击跳转到 PDF
- 高亮显示表格区域

**实现**:
```typescript
interface CitationProps {
  location: ChunkLocation;
  documentId: string;
  baseUrl: string;
}

export function Citation({ location, documentId, baseUrl }: CitationProps) {
  const citationText = generateCitationText(location);
  const navUrl = location.navigation_url || 
    generateNavigationUrl(baseUrl, documentId, location);
  
  return (
    <a 
      href={navUrl} 
      target="_blank"
      className="citation-link"
      onClick={(e) => {
        e.preventDefault();
        navigateToPDF(navUrl, location);
      }}
    >
      {citationText}
    </a>
  );
}

function generateCitationText(location: ChunkLocation): string {
  const parts: string[] = [];
  if (location.table_index !== undefined) {
    parts.push(`Table ${location.table_index}`);
  }
  if (location.page_number) {
    parts.push(`Page ${location.page_number}`);
  }
  if (location.table_row_range) {
    parts.push(`Rows ${location.table_row_range[0]}-${location.table_row_range[1]}`);
  }
  return parts.join(", ");
}
```

#### 6.3 更新 MessageList 组件

**文件**: `chat-ui/src/components/MessageList.tsx`

**功能**:
- 在消息中显示 citations
- 支持点击跳转

#### 6.4 创建 PDF Viewer 组件（可选）

**文件**: `chat-ui/src/components/PDFViewer.tsx`

**功能**:
- 显示 PDF
- 根据 location 跳转到指定页面
- 高亮 bbox 区域

### 阶段 7: API 端点更新

#### 7.1 PDF Source API

**文件**: `kb-builder-service/api/routes/` (相应路由文件)

**功能**:
- 提供 PDF 文件访问
- 支持 page 和 bbox 参数
- 返回 PDF 页面或高亮区域

**端点**:
```
GET /api/v1/sources/{document_id}?page=1&bbox=120,447,502,633&rows=0-12
```

**实现**:
```python
@router.get("/sources/{document_id}")
async def get_source(
    document_id: str,
    page: Optional[int] = None,
    bbox: Optional[str] = None,  # "x0,y0,x1,y1"
    rows: Optional[str] = None    # "start-end"
):
    """获取源文件，支持页面和区域定位"""
    # 查找文件
    file_path = find_source_file(document_id)
    
    if page is not None:
        # 返回指定页面
        if bbox:
            # 返回高亮区域
            return highlight_pdf_region(file_path, page, bbox)
        else:
            # 返回完整页面
            return get_pdf_page(file_path, page)
    else:
        # 返回完整文件
        return FileResponse(file_path)
```

## 四、Location Tracking 详细设计

### 4.1 Location 数据结构

```python
ChunkLocation {
    # 基础位置
    page_number: int
    start_char: int
    end_char: int
    
    # 表格位置
    table_index: int
    table_row_range: (int, int)  # (start_row, end_row)
    table_bbox: [x0, y0, x1, y1]
    
    # 导航信息
    navigation_url: str
    highlight_bbox: [x0, y0, x1, y1]
}
```

### 4.2 Location 生成流程

```
1. PDF Extractor 提取表格信息（包含 bbox）
   ↓
2. PDF Chunker 创建 chunks，添加 location
   ↓
3. Indexing Service 生成 navigation_url
   ↓
4. 存储到 Milvus (location 在 metadata)
   ↓
5. Retrieval Service 返回 location
   ↓
6. Chat Service 生成 citation
   ↓
7. Chat UI 显示和导航
```

### 4.3 Navigation URL 格式

```
{base_url}/api/v1/sources/{document_id}?page={page}&bbox={x0},{y0},{x1},{y1}&rows={start}-{end}
```

**示例**:
```
http://localhost:8001/api/v1/sources/SN74HC163DataSheet?page=1&bbox=120,447,502,633&rows=0-12
```

## 五、实施时间表

### Week 1: PDF Loading 重写
- Day 1-2: 重写 PDF Extractor
- Day 3: 更新 PDF Loader
- Day 4: 删除废弃代码
- Day 5: 测试和调试

### Week 2: PDF Chunking 重写
- Day 1-2: 重写 PDF Chunker（表格处理）
- Day 3: 更新 ChunkLocation 模型
- Day 4: 实现表格 chunking 策略
- Day 5: 测试和调试

### Week 3: Indexing 和 Retrieval 更新
- Day 1-2: 更新 Indexing Service
- Day 3: 更新 Retrieval Service
- Day 4: 更新 API schemas
- Day 5: 测试和调试

### Week 4: Chat Service 和 UI 更新
- Day 1-2: 更新 Chat Service
- Day 3-4: 更新 Chat UI（Citation 组件、PDF 导航）
- Day 5: 集成测试

**总计**: 4 周

## 六、测试计划

### 6.1 单元测试
- PDF Extractor: 表格提取、图片提取、标题提取
- PDF Chunker: 表格 chunking、location 生成
- Location Tracking: URL 生成、citation 生成

### 6.2 集成测试
- 完整流程: Load → Chunk → Index → Retrieve
- Location 传递: 从 indexing 到 UI
- PDF 导航: URL 生成和跳转

### 6.3 端到端测试
- 上传 PDF → 索引 → 检索 → 显示 citation → 点击跳转 PDF

## 七、迁移计划

### 7.1 数据迁移
- 现有 chunks 的 location 信息可能需要重新索引
- 考虑批量重新索引或增量更新

### 7.2 向后兼容
- API 保持向后兼容（可选字段）
- 逐步迁移现有数据

## 八、风险和缓解

### 8.1 技术风险
- **pymupdf4llm 表格内容提取**: 需要测试和备选方案
- **bbox 精度**: 可能需要调整
- **性能**: 大文件处理可能较慢

### 8.2 缓解措施
- 充分测试 pymupdf4llm 功能
- 准备备选方案（PyMuPDF Layout）
- 优化大文件处理（流式处理）

## 九、成功标准

1. ✅ PDF 表格正确提取和 chunking
2. ✅ Location metadata 完整存储和返回
3. ✅ Citations 正确显示
4. ✅ PDF 导航功能正常
5. ✅ 与现有系统无缝集成
6. ✅ 性能满足要求

## 十、下一步行动

1. **立即开始**: 阶段 1 - PDF Loading 重写
2. **并行准备**: UI 组件设计
3. **持续测试**: 每个阶段完成后进行测试
4. **文档更新**: API 文档、用户文档

