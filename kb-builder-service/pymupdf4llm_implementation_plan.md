# pymupdf4llm 重写方案 - 深度评估与实施计划

## 一、pymupdf4llm 功能深度分析

### 1.1 核心功能

#### `to_markdown()` 方法
```python
pymupdf4llm.to_markdown(
    doc,                    # PDF 路径或 PyMuPDF 文档对象
    pages=None,             # 指定页面列表 [0, 1, 2] (0-based)
    write_images=False,      # 是否提取图片
    page_chunks=False,      # 是否按页分块返回
    image_path=None,        # 图片保存路径（如果指定）
    image_format="png"      # 图片格式
)
```

**返回格式**：
- `page_chunks=False`: 返回完整 Markdown 字符串
- `page_chunks=True`: 返回列表，每个元素是字典：
  ```python
  {
      'text': str,           # 页面的 Markdown 内容
      'metadata': dict,      # 包含 page, format, title 等
      'tables': list,        # 表格信息列表
      'images': list,        # 图片信息列表
      'graphics': list,      # 图形信息列表
      'toc_items': list,     # 目录项列表
      'words': list          # 单词列表
  }
  ```

#### 与 PyMuPDF Layout 集成
- 如果安装了 `pymupdf_layout`，可以使用 `to_json()` 和 `to_text()` 方法
- 提供更好的布局分析（表格检测、页眉页脚、脚注等）

#### LlamaIndex 集成
```python
from pymupdf4llm import LlamaMarkdownReader
reader = LlamaMarkdownReader()
docs = reader.load_data("input.pdf")  # 返回 LlamaIndex Document 列表
```

### 1.2 测试结果关键发现

1. **页面编号**：`metadata['page']` 是 1-based，可直接使用
2. **图片信息**：`chunk['images']` 包含图片字典，有 `number` (xref) 字段
3. **表格信息**：`chunk['tables']` 是列表（需要进一步测试结构）
4. **图片文件**：`write_images=True` 时 Markdown 有引用，但文件可能未保存到磁盘

## 二、当前系统架构分析

### 2.1 PDF Loader 流程
```
PDF 文件 → PDFLoader → PDFExtractor → Markdown + DocumentStructure
```

**当前实现**：
- 使用 `pdfplumber` 提取文本和表格
- 使用 `PyMuPDF` 提取图片
- 手动构建页面标记 `<page>`
- 手动检测标题（HeadingDetector）

### 2.2 PDF Chunker 流程
```
Document → PDFChunker → Chunks (with location info)
```

**当前实现**：
- 使用 `RecursiveCharacterTextSplitter` (tiktoken)
- 处理表格（单独分块）
- 处理页面标记
- 计算字符位置和页面映射

### 2.3 Indexing 流程
```
Chunks → Embedder → VectorStore (Milvus)
```

**当前实现**：
- 生成 embedding
- 存储到 Milvus（包含 metadata 和 location）

## 三、重写方案评估

### 3.1 PDF Loader 重写方案

#### 方案 A: 使用 `page_chunks=True`（推荐）

**优点**：
- 保留页面信息，便于引用
- 可以逐页处理，内存效率高
- 直接获取表格和图片信息
- 元数据完整

**实现要点**：
```python
# 1. 获取分页内容
page_chunks = pymupdf4llm.to_markdown(path, page_chunks=True, write_images=False)

# 2. 打开 PyMuPDF 用于图片提取
doc = fitz.open(path)

# 3. 处理每页
for chunk in page_chunks:
    page_num = chunk['metadata']['page']  # 1-based
    page_text = chunk.get('text', '')
    
    # 提取图片（从 chunk['images']）
    if chunk.get('images'):
        for img_info in chunk['images']:
            xref = img_info['number']
            base_image = doc.extract_image(xref)
            # 使用 ImageHandler 保存
    
    # 提取表格（从 chunk['tables']）
    if chunk.get('tables'):
        # 处理表格信息
    
    # 添加页面标记
    # 合并到完整 Markdown
```

**缺点**：
- 需要手动添加页面标记（保持与现有 chunker 兼容）
- 需要处理图片路径更新

#### 方案 B: 使用完整 Markdown

**优点**：
- 简单直接
- 一次性获取所有内容

**缺点**：
- 失去页面信息（需要手动添加）
- 需要从 Markdown 解析表格和标题

**推荐**：方案 A

### 3.2 PDF Chunker 重写方案

#### 方案 A: 保留现有逻辑（推荐）

**理由**：
- Extractor 会添加页面标记，chunker 可以继续使用
- 表格已经是标准 Markdown 格式，现有逻辑可以处理
- 只需要简化表格检测（标准 Markdown 表格）

**改动**：
1. 简化表格检测：使用正则表达式检测标准 Markdown 表格
2. 保留页面标记处理
3. 简化标题检测（从 Markdown 提取）

#### 方案 B: 基于页面分块

**优点**：
- 可以利用 `page_chunks` 的页面信息
- 更精确的页面引用

**缺点**：
- 需要大幅修改现有逻辑
- 可能破坏页面边界（一个 chunk 可能跨页）

**推荐**：方案 A（最小改动）

### 3.3 Indexing 影响评估

**影响**：
- **最小**：Indexing Service 不需要修改
- Chunks 的格式和 metadata 保持不变
- Location 信息保持不变

**优化机会**：
- 可以利用 `chunk['metadata']` 中的额外信息
- 可以利用 `chunk['toc_items']` 构建更好的索引

## 四、详细实施计划

### 4.1 阶段 1: 重写 PDF Extractor

**文件**: `kb-builder-service/processors/loaders/pdf/pdf_extractor.py`

**核心实现**：

```python
def extract(self, path: Path, file_id: str, ...):
    # 1. 获取分页内容
    page_chunks = pymupdf4llm.to_markdown(
        str(path), 
        page_chunks=True, 
        write_images=False  # 不使用，直接从 PyMuPDF 提取
    )
    
    # 2. 打开 PyMuPDF 用于元数据和图片
    doc = fitz.open(str(path))
    metadata = doc.metadata
    total_pages = len(doc)
    
    # 3. 处理每页
    markdown_parts = []
    current_char_pos = 0
    tables_info = []
    image_counter = 0
    
    for chunk in page_chunks:
        page_num = chunk['metadata']['page']  # 1-based
        page_text = chunk.get('text', '')
        
        # 添加页面标记
        page_start = f'<page page="{page_num}" start_char="{current_char_pos}">\n\n'
        markdown_parts.append(page_start)
        current_pos += len(page_start)
        
        # 处理图片
        if chunk.get('images'):
            for img_info in chunk['images']:
                xref = img_info['number']
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = f".{base_image['ext']}"
                    
                    image_counter += 1
                    img_url = self.image_handler.save_image(
                        image_bytes, file_id, image_counter, image_ext
                    )
                    
                    # 更新 Markdown 中的图片引用（如果有）
                    # 查找并替换图片引用
                except Exception as e:
                    logger.warning(f"Failed to extract image: {e}")
        
        # 提取表格信息
        if chunk.get('tables'):
            for table_idx, table_info in enumerate(chunk['tables']):
                # 解析表格信息（需要测试实际结构）
                tables_info.append({
                    "page": page_num,
                    "index": len(tables_info),
                    # ... 其他信息
                })
        
        # 添加页面内容
        markdown_parts.append(page_text)
        current_pos += len(page_text)
        
        # 关闭页面标记
        page_end = '\n\n</page>\n\n'
        markdown_parts.append(page_end)
        current_pos += len(page_end)
    
    # 4. 从完整 Markdown 提取标题
    full_md = ''.join(markdown_parts)
    headings = self._extract_headings_from_markdown(full_md)
    
    # 5. 构建 DocumentStructure
    structure = StructureBuilder.build_pdf_structure(
        total_pages=total_pages,
        pdf_metadata=metadata if metadata else None,
        tables=tables_info if tables_info else None,
        pdf_headings=headings if headings else None
    )
    
    doc.close()
    return full_md, structure
```

**关键方法**：
- `_extract_tables_from_chunk(chunk, page_num)`: 从 `chunk['tables']` 提取
- `_process_images_from_chunk(chunk, doc, page_num, file_id)`: 处理图片
- `_extract_headings_from_markdown(markdown)`: 从 Markdown 解析标题
- `_update_image_references(text, image_map)`: 更新图片引用

### 4.2 阶段 2: 更新 PDF Loader

**文件**: `kb-builder-service/processors/loaders/pdf/pdf_loader.py`

**改动**：
- 移除 `pdfplumber` 导入和检查
- 添加 `pymupdf4llm` 导入检查
- 简化逻辑（不需要手动打开/关闭 PDF）

### 4.3 阶段 3: 优化 PDF Chunker

**文件**: `kb-builder-service/processors/chunkers/pdf_chunker.py`

**改动**：
1. **简化表格检测**：
   ```python
   # 标准 Markdown 表格模式
   table_pattern = re.compile(
       r'(\|[^\n]+\|\n\|[:\s\-]+\|\n(?:\|[^\n]+\|\n?)+)',
       re.MULTILINE
   )
   ```

2. **保留页面标记处理**：继续使用 `<page>` 标签

3. **简化标题检测**：从 Markdown 提取 `#` 标题（可选）

### 4.4 阶段 4: 删除废弃代码

- 删除 `kb-builder-service/processors/loaders/pdf/heading_detector.py`

### 4.5 阶段 5: 更新依赖

**文件**: `kb-builder-service/requirements.txt`

```txt
# 添加
pymupdf4llm>=0.0.1

# 保留
PyMuPDF>=1.23.0  # 用于元数据和图片提取

# 移除
pdfplumber>=0.10.0  # 不再使用
```

## 五、最佳实践建议

### 5.1 图片处理最佳实践

1. **不使用 `write_images=True`**：
   - 测试显示文件可能未保存
   - 直接从 PyMuPDF 提取更可靠

2. **图片提取流程**：
   ```python
   # 从 chunk['images'] 获取图片信息
   for img_info in chunk['images']:
       xref = img_info['number']  # xref 编号
       base_image = doc.extract_image(xref)
       # 使用 ImageHandler 保存到指定目录
   ```

3. **图片引用更新**：
   - pymupdf4llm 可能在 Markdown 中添加图片引用
   - 需要查找并更新为新的 URL

### 5.2 表格处理最佳实践

1. **从 `chunk['tables']` 提取**：
   - 优先使用 `chunk['tables']` 中的信息
   - 需要测试实际结构

2. **从 Markdown 解析**：
   - 作为备选方案
   - 使用正则表达式检测标准 Markdown 表格

### 5.3 性能优化

1. **使用 `page_chunks=True`**：
   - 逐页处理，内存效率高
   - 适合大文件

2. **延迟图片提取**：
   - 只在需要时提取图片
   - 可以配置是否提取图片

3. **缓存 Markdown**：
   - 可以缓存转换后的 Markdown
   - 避免重复转换

### 5.4 错误处理

1. **pymupdf4llm 异常**：
   - 捕获并转换为 LoaderError
   - 提供有意义的错误信息

2. **图片提取失败**：
   - 记录警告，继续处理
   - 不影响整体流程

3. **表格解析失败**：
   - 回退到 Markdown 解析
   - 记录警告

## 六、测试计划

### 6.1 单元测试

1. **PDF Extractor 测试**：
   - 测试基本转换
   - 测试图片提取
   - 测试表格提取
   - 测试标题提取
   - 测试页面标记

2. **PDF Chunker 测试**：
   - 测试标准 Markdown 表格
   - 测试页面标记处理
   - 测试位置追踪

### 6.2 集成测试

1. **完整流程测试**：
   - Load → Chunk → Index
   - 验证 chunks 格式
   - 验证 metadata
   - 验证 location 信息

2. **边界情况测试**：
   - 无图片的 PDF
   - 无表格的 PDF
   - 多页 PDF
   - 大文件 PDF

## 七、风险评估

### 7.1 技术风险

1. **`chunk['tables']` 结构未知**：
   - **风险**：中等
   - **缓解**：需要测试，准备备选方案（Markdown 解析）

2. **图片引用更新**：
   - **风险**：低
   - **缓解**：可以保留原始引用或更新为新 URL

3. **向后兼容**：
   - **风险**：低（不需要向后兼容）
   - **缓解**：完全重写，不保留旧接口

### 7.2 性能风险

1. **大文件处理**：
   - **风险**：低
   - **缓解**：使用 `page_chunks=True` 逐页处理

2. **图片提取性能**：
   - **风险**：低
   - **缓解**：可以配置是否提取图片

## 八、实施时间表

1. **阶段 1**: PDF Extractor 重写（2-3 天）
2. **阶段 2**: PDF Loader 更新（0.5 天）
3. **阶段 3**: PDF Chunker 优化（1 天）
4. **阶段 4**: 删除废弃代码（0.5 天）
5. **阶段 5**: 更新依赖（0.5 天）
6. **测试**: 单元测试和集成测试（2 天）

**总计**: 约 6-7 天

## 九、总结

### 9.1 优势

1. **简化代码**：减少手动解析逻辑
2. **更好的布局检测**：pymupdf4llm 自动处理多列、表格、标题
3. **标准格式**：输出标准 Markdown，易于处理
4. **维护成本低**：依赖成熟库
5. **性能优化**：支持逐页处理

### 9.2 注意事项

1. **图片处理**：需要直接从 PyMuPDF 提取
2. **表格结构**：需要测试 `chunk['tables']` 的实际结构
3. **页面标记**：需要手动添加以保持兼容性
4. **错误处理**：需要妥善处理各种异常情况

### 9.3 推荐方案

**采用方案 A（使用 `page_chunks=True`）**：
- 保留页面信息
- 直接获取表格和图片信息
- 内存效率高
- 最小改动现有 chunker

