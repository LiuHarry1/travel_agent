# 表格 Chunking 和定位方案

## 一、测试结果总结

基于 SN74HC163DataSheet.pdf 的测试：
- **总表格数**: 17 个
- **小表格** (≤10行): 11 个
- **中等表格** (11-30行): 6 个
- **大表格** (>30行): 0 个

**表格结构**（从 pymupdf4llm）：
```python
{
    'bbox': (x0, y0, x1, y1),  # 边界框坐标
    'rows': 13,                 # 行数
    'columns': 5                # 列数
}
```

## 二、表格 Chunking 策略

### 2.1 策略分类

#### 小表格 (≤10行)
- **策略**: `single_chunk` - 整个表格作为一个 chunk
- **理由**: 小表格内容少，适合作为一个完整的语义单元
- **实现**: 直接使用表格内容创建一个 chunk

#### 中等表格 (11-30行)
- **策略**: `split_by_rows` - 按行分组
- **理由**: 中等表格可能需要拆分，但不需要保留表头
- **实现**: 
  - 每 5-10 行一组
  - 每组创建一个 chunk
  - 可选：第一组包含表头

#### 大表格 (>30行)
- **策略**: `split_by_rows_with_header` - 按行分组，每组保留表头
- **理由**: 大表格需要拆分，且每组需要表头以保持上下文
- **实现**:
  - 每 10-15 行一组
  - 每组都包含表头（前 1-2 行）
  - 每组创建一个 chunk

### 2.2 实现细节

```python
def chunk_table(table_info, table_content, chunk_size=1000):
    """
    Chunk a table based on its size.
    
    Args:
        table_info: {'bbox': tuple, 'rows': int, 'columns': int}
        table_content: Table content as markdown or text
        chunk_size: Target chunk size in tokens
    
    Returns:
        List of table chunks
    """
    rows = table_info['rows']
    cols = table_info['columns']
    
    # Estimate tokens
    token_count = estimate_tokens(table_content)
    
    # Small table: single chunk
    if rows <= 10 or token_count <= chunk_size:
        return [create_table_chunk(
            content=table_content,
            table_index=table_info['table_index'],
            chunk_index=0,
            row_range=(0, rows - 1)
        )]
    
    # Medium/Large table: split by rows
    rows_per_chunk = calculate_rows_per_chunk(rows, chunk_size)
    chunks = []
    
    # Parse table to get header and data rows
    header_rows, data_rows = parse_table_rows(table_content)
    
    chunk_index = 0
    for i in range(0, len(data_rows), rows_per_chunk):
        group_rows = data_rows[i:i + rows_per_chunk]
        
        # Combine header with data rows
        chunk_content = '\n'.join(header_rows + group_rows)
        
        row_start = i
        row_end = min(i + rows_per_chunk - 1, len(data_rows) - 1)
        
        chunk = create_table_chunk(
            content=chunk_content,
            table_index=table_info['table_index'],
            chunk_index=chunk_index,
            row_range=(row_start, row_end),
            has_header=True
        )
        chunks.append(chunk)
        chunk_index += 1
    
    return chunks
```

## 三、表格内容提取

### 3.1 从 bbox 提取内容

pymupdf4llm 的 `chunk['tables']` 只包含元数据，表格内容在 `chunk['text']` 中。需要使用 bbox 定位表格内容。

**方法 1: 使用 PyMuPDF 从 bbox 提取**
```python
def extract_table_content_by_bbox(page_obj, bbox):
    """
    Extract table content from PDF using bbox coordinates.
    
    Args:
        page_obj: PyMuPDF Page object
        bbox: (x0, y0, x1, y1) tuple
    
    Returns:
        Table content as text
    """
    x0, y0, x1, y1 = bbox
    rect = fitz.Rect(x0, y0, x1, y1)
    
    # Extract text from bbox area
    text = page_obj.get_text("text", clip=rect)
    
    # Optionally: Extract as markdown table
    # This might require additional processing
    
    return text
```

**方法 2: 从 Markdown 文本中定位**
```python
def extract_table_from_markdown(page_text, bbox, page_obj):
    """
    Extract table content from markdown text using bbox.
    
    Since pymupdf4llm converts tables to markdown, we can:
    1. Try to find markdown table in text
    2. Or extract text from bbox and convert to markdown table
    """
    # Option 1: Find markdown table pattern near bbox area
    # This is approximate - bbox might not exactly match markdown position
    
    # Option 2: Extract from bbox and format as markdown
    text = page_obj.get_text("text", clip=fitz.Rect(*bbox))
    
    # Convert to markdown table format
    # This requires parsing the text structure
    markdown_table = convert_text_to_markdown_table(text)
    
    return markdown_table
```

**方法 3: 使用 PyMuPDF Layout（如果可用）**
```python
# If pymupdf_layout is installed, use structured extraction
from pymupdf_layout import Layout

layout = Layout(page_obj)
tables = layout.find_tables()

for table in tables:
    if table.bbox.intersects(fitz.Rect(*bbox)):
        # Get structured table data
        table_data = table.extract()
        # Convert to markdown
        markdown_table = table_data.to_markdown()
        return markdown_table
```

### 3.2 推荐方案

**优先使用**: 方法 1（PyMuPDF bbox 提取）+ 方法 2（Markdown 解析）结合
- 使用 bbox 从 PDF 提取文本
- 尝试从 Markdown 文本中找到对应的表格
- 如果找不到，使用提取的文本构建 Markdown 表格

## 四、Chunk ID 和定位机制

### 4.1 Chunk ID 设计

#### 表格 Chunk ID 格式
```
{document_id}_table_{table_index}_chunk_{chunk_index}
```

**示例**:
- `SN74HC163DataSheet_table_0_chunk_0` - 第一个表格的第一个 chunk
- `SN74HC163DataSheet_table_5_chunk_2` - 第 6 个表格的第 3 个 chunk（如果表格被拆分）

#### 组件说明
- `document_id`: PDF 文件名或唯一 ID
- `table_index`: 表格在文档中的索引（0-based，全局）
- `chunk_index`: Chunk 在表格中的索引（0-based，如果表格被拆分）

### 4.2 Location Metadata

每个 table chunk 应包含以下定位信息：

```python
{
    'location': {
        'type': 'table',
        'page': 1,                    # 页面号（1-based）
        'table_index': 0,              # 表格索引（全局）
        'bbox': [120.0, 447.5, 502.8, 633.0],  # 边界框
        'row_range': (0, 12),          # 行范围（如果表格被拆分）
        'column_range': (0, 4),        # 列范围（如果需要）
    },
    'metadata': {
        'table_rows': 13,              # 总行数
        'table_columns': 5,            # 总列数
        'chunk_type': 'table',          # Chunk 类型
        'is_split': False,              # 是否被拆分
        'has_header': True              # 是否包含表头
    }
}
```

### 4.3 从 Chunk ID 定位到 PDF

#### 步骤 1: 解析 Chunk ID
```python
def parse_table_chunk_id(chunk_id):
    """
    Parse table chunk ID to extract components.
    
    Example: 'SN74HC163DataSheet_table_0_chunk_0'
    Returns: {
        'document_id': 'SN74HC163DataSheet',
        'table_index': 0,
        'chunk_index': 0
    }
    """
    parts = chunk_id.split('_')
    # Find 'table' and 'chunk' indices
    table_idx = parts.index('table')
    chunk_idx = parts.index('chunk')
    
    document_id = '_'.join(parts[:table_idx])
    table_index = int(parts[table_idx + 1])
    chunk_index = int(parts[chunk_idx + 1])
    
    return {
        'document_id': document_id,
        'table_index': table_index,
        'chunk_index': chunk_index
    }
```

#### 步骤 2: 查找表格信息
```python
def locate_table_in_pdf(chunk_id, pdf_path, table_registry):
    """
    Locate table in PDF using chunk ID.
    
    Args:
        chunk_id: Table chunk ID
        pdf_path: Path to PDF file
        table_registry: Registry of all tables (from extraction)
    
    Returns:
        Location information for navigation
    """
    parsed = parse_table_chunk_id(chunk_id)
    table_index = parsed['table_index']
    chunk_index = parsed['chunk_index']
    
    # Find table in registry
    table_info = table_registry[table_index]
    
    # Get location
    location = {
        'page': table_info['page'],
        'bbox': table_info['bbox'],
        'table_index': table_index
    }
    
    # If table is split, get row range for this chunk
    if chunk_index > 0:
        # Calculate row range based on chunk index
        row_range = calculate_row_range(
            table_info['rows'],
            chunk_index,
            rows_per_chunk=table_info.get('rows_per_chunk', 10)
        )
        location['row_range'] = row_range
    
    return location
```

#### 步骤 3: PDF 导航
```python
def navigate_to_table_in_pdf(pdf_path, location):
    """
    Navigate to table location in PDF.
    
    This can be used by frontend to:
    1. Open PDF at specific page
    2. Highlight bbox area
    3. Scroll to table
    """
    return {
        'pdf_path': str(pdf_path),
        'page': location['page'],
        'bbox': location['bbox'],
        'action': 'navigate',
        'highlight': True  # Frontend can highlight the bbox area
    }
```

### 4.4 实现示例

```python
class TableChunkLocation:
    """Location information for table chunks."""
    
    def __init__(self, page, table_index, bbox, row_range=None):
        self.page = page
        self.table_index = table_index
        self.bbox = bbox  # [x0, y0, x1, y1]
        self.row_range = row_range  # (start, end) if table is split
    
    def to_dict(self):
        return {
            'page': self.page,
            'table_index': self.table_index,
            'bbox': self.bbox,
            'row_range': self.row_range
        }
    
    def get_citation(self):
        """Generate citation text."""
        parts = [f"Page {self.page}"]
        if self.row_range:
            parts.append(f"Rows {self.row_range[0]}-{self.row_range[1]}")
        return ", ".join(parts)
    
    def get_navigation_url(self, base_url, pdf_path):
        """Generate URL for PDF navigation."""
        params = {
            'page': self.page,
            'bbox': ','.join(map(str, self.bbox))
        }
        if self.row_range:
            params['rows'] = f"{self.row_range[0]}-{self.row_range[1]}"
        
        query = '&'.join(f"{k}={v}" for k, v in params.items())
        return f"{base_url}/pdf/{pdf_path}?{query}"
```

## 五、完整实现流程

### 5.1 表格提取和 Chunking 流程

```
1. 使用 pymupdf4llm 提取 page_chunks
   ↓
2. 遍历每个 chunk，提取 tables 信息
   ↓
3. 对于每个表格：
   a. 从 bbox 提取表格内容（PyMuPDF）
   b. 或从 Markdown 文本中定位表格
   c. 根据表格大小决定 chunking 策略
   d. 创建 table chunks
   ↓
4. 为每个 chunk 生成：
   - Chunk ID
   - Location metadata
   - Content
```

### 5.2 定位流程

```
1. 接收 chunk_id
   ↓
2. 解析 chunk_id 获取 table_index 和 chunk_index
   ↓
3. 从 table_registry 查找表格信息
   ↓
4. 构建 location 信息（page, bbox, row_range）
   ↓
5. 返回导航信息（可用于前端高亮和跳转）
```

## 六、注意事项

1. **表格内容提取**：
   - bbox 坐标可能不完全准确
   - 需要处理表格跨页的情况
   - 需要处理表格格式（合并单元格等）

2. **Chunking 策略**：
   - 小表格保持完整，避免拆分
   - 大表格拆分时保留表头
   - 考虑表格的语义完整性

3. **定位精度**：
   - bbox 提供精确的位置信息
   - row_range 提供行级别的定位
   - 可以进一步细化到单元格级别（如果需要）

4. **性能考虑**：
   - 表格提取可能较慢，考虑缓存
   - 大表格的拆分需要合理控制 chunk 数量

## 七、下一步实施

1. **实现表格内容提取**：使用 bbox 从 PDF 提取
2. **实现表格 chunking**：根据大小采用不同策略
3. **实现定位机制**：Chunk ID -> PDF 位置
4. **集成到现有系统**：更新 PDF Extractor 和 Chunker

