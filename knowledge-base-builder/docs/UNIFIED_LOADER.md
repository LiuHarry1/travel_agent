# 统一文档加载器使用指南

## 概述

`UnifiedLoader` 是一个统一的文档加载器，支持多种文件格式（PDF, DOCX, HTML, TXT, MD），并将它们统一转换为 Markdown 格式。在转换过程中，它会：

1. **保存原文件**到 `static/sources/` 目录
2. **提取并保存图片**到 `static/images/` 目录
3. **转换图片路径**为 HTML `<img>` 标签，便于在网页中显示

## 支持的文件格式

- **PDF** (`.pdf`) - 使用 `pdfplumber` 和 `PyMuPDF`
- **DOCX** (`.docx`, `.doc`) - 使用 `python-docx`
- **HTML** (`.html`, `.htm`) - 使用 `beautifulsoup4` 和 `markdownify`
- **Markdown** (`.md`, `.markdown`) - 原生支持，处理其中的图片
- **纯文本** (`.txt`) - 直接读取

## 功能特性

### 1. 原文件保存

所有上传的文件都会保存到 `static/sources/` 目录，文件名格式为：`{file_id}{原始扩展名}`

例如：
- 上传 `document.pdf` → 保存为 `static/sources/a1b2c3d4_document.pdf`

### 2. 图片提取和保存

- **PDF**: 提取 PDF 中的图片（需要 PyMuPDF）
- **DOCX**: 提取 Word 文档中的图片
- **HTML**: 提取 HTML 中的图片（包括网络图片下载）
- **Markdown**: 提取 Markdown 中引用的本地图片

所有图片保存到 `static/images/` 目录，文件名格式为：`{file_id}_image_{序号}{扩展名}`

### 3. 图片路径转换

所有图片路径都会转换为 HTML `<img>` 标签，URL 格式为：`/static/images/{文件名}`

例如：
```markdown
![图片描述](local_image.png)
```

转换为：
```html
<img src="/static/images/a1b2c3d4_image_1.png" alt="图片描述" />
```

## 目录结构

```
knowledge-base-builder/
├── static/
│   ├── sources/          # 原文件存储
│   │   ├── a1b2c3d4_document.pdf
│   │   └── b2c3d4e5_report.docx
│   └── images/            # 图片存储
│       ├── a1b2c3d4_image_1.png
│       ├── a1b2c3d4_image_2.jpg
│       └── b2c3d4e5_image_1.png
```

## 配置

在 `config/settings.py` 中配置静态文件目录：

```python
static_dir: str = "static"  # 默认值
```

或通过环境变量：

```env
STATIC_DIR=static
```

## 使用示例

### 基本使用

```python
from processors.loaders import LoaderFactory
from models.document import DocumentType

# 创建加载器（自动使用 UnifiedLoader）
loader = LoaderFactory.create(DocumentType.PDF, static_dir="static")

# 加载文档
document = loader.load("path/to/document.pdf")

# document.content 现在是 Markdown 格式
# document.metadata 包含文件信息
```

### 在索引服务中使用

索引服务已经自动使用 `UnifiedLoader`，无需额外配置：

```python
from services.indexing_service import IndexingService

service = IndexingService()
result = service.index_document(
    source="document.pdf",
    doc_type=DocumentType.PDF,
    collection_name="my_collection",
    embedding_provider="bge",
    embedding_model="BAAI/bge-large-en-v1.5"
)
```

## 静态文件服务

为了在网页中显示图片，需要配置静态文件服务。

### FastAPI 静态文件服务

在 `main.py` 或应用入口添加：

```python
from fastapi.staticfiles import StaticFiles

app.mount("/static", StaticFiles(directory="static"), name="static")
```

### 或者使用 Nginx

```nginx
location /static/ {
    alias /path/to/knowledge-base-builder/static/;
    expires 30d;
    add_header Cache-Control "public, immutable";
}
```

## 依赖安装

确保安装所有必需的依赖：

```bash
pip install -r requirements.txt
```

主要依赖：
- `python-docx>=1.1.0` - DOCX 文件处理
- `pdfplumber>=0.10.0` - PDF 文本提取
- `PyMuPDF>=1.23.0` - PDF 图片提取（推荐）
- `beautifulsoup4>=4.12.0` - HTML 解析
- `markdownify>=0.11.6` - HTML 转 Markdown
- `Pillow>=10.0.0` - 图片处理
- `requests>=2.31.0` - 网络图片下载

## 注意事项

1. **网络图片**: HTML 中的网络图片会被下载并保存到本地
2. **图片格式**: 自动检测图片格式，如果无法检测则使用 `.png`
3. **编码问题**: 自动处理 UTF-8 和 GBK 编码
4. **大文件**: 对于大文件，处理可能需要一些时间
5. **内存使用**: 图片会完全加载到内存，注意大图片的内存占用

## 故障排除

### PDF 图片无法提取

确保安装了 `PyMuPDF`：
```bash
pip install PyMuPDF
```

### HTML 图片下载失败

检查网络连接，或确保 `requests` 库已安装。

### 图片路径不正确

确保静态文件服务已正确配置，并且 `static_dir` 配置正确。

## 示例：完整的文件处理流程

```python
from processors.loaders import LoaderFactory
from models.document import DocumentType
from processors.chunkers import RecursiveChunker
from processors.embedders import EmbedderFactory
from processors.stores import MilvusVectorStore

# 1. 加载文档
loader = LoaderFactory.create(DocumentType.PDF, static_dir="static")
document = loader.load("report.pdf")

# 2. 分块
chunker = RecursiveChunker(chunk_size=1000, chunk_overlap=200)
chunks = chunker.chunk(document)

# 3. 生成嵌入向量
embedder = EmbedderFactory.create(provider="bge", model="BAAI/bge-large-en-v1.5")
texts = [chunk.text for chunk in chunks]
embeddings = embedder.embed(texts)

# 4. 附加嵌入向量
for chunk, embedding in zip(chunks, embeddings):
    chunk.embedding = embedding

# 5. 索引到 Milvus
vector_store = MilvusVectorStore()
vector_store.index(chunks, "my_collection")
```

## 性能优化建议

1. **图片压缩**: 对于大图片，可以考虑压缩后再保存
2. **异步处理**: 对于大量文件，考虑使用异步处理
3. **缓存**: 对于重复处理的文件，可以考虑缓存结果
4. **批量处理**: 对于多个文件，使用批量处理接口

