# 统一文档加载器快速开始

## 安装依赖

```bash
cd knowledge-base-builder
pip install -r requirements.txt
```

## 配置

确保 `static` 目录存在（会自动创建）：

```bash
mkdir -p static/sources static/images
```

或在 `.env` 文件中配置：

```env
STATIC_DIR=static
```

## 使用

### 1. 通过 API 上传文件

```bash
curl -X POST "http://localhost:8001/api/v1/upload/stream" \
  -F "file=@document.pdf" \
  -F "collection_name=my_collection" \
  -F "embedding_provider=bge" \
  -F "embedding_model=BAAI/bge-large-en-v1.5"
```

### 2. 在代码中使用

```python
from processors.loaders import LoaderFactory
from models.document import DocumentType

# 创建加载器
loader = LoaderFactory.create(DocumentType.PDF, static_dir="static")

# 加载文档
document = loader.load("path/to/document.pdf")

# 查看转换后的 Markdown
print(document.content)

# 查看元数据
print(document.metadata)
```

## 文件结构

上传文件后，目录结构如下：

```
static/
├── sources/
│   └── a1b2c3d4_document.pdf    # 原文件
└── images/
    ├── a1b2c3d4_image_1.png    # 提取的图片
    └── a1b2c3d4_image_2.jpg
```

## 访问静态文件

启动服务后，可以通过以下 URL 访问：

- 原文件: `http://localhost:8001/static/sources/{file_id}{ext}`
- 图片: `http://localhost:8001/static/images/{file_id}_image_{n}{ext}`

## 支持的格式

- ✅ PDF (`.pdf`)
- ✅ DOCX (`.docx`, `.doc`)
- ✅ HTML (`.html`, `.htm`)
- ✅ Markdown (`.md`, `.markdown`)
- ✅ 纯文本 (`.txt`)

## 注意事项

1. 首次使用需要安装所有依赖
2. PDF 图片提取需要 `PyMuPDF`
3. 网络图片会自动下载
4. 大文件处理可能需要一些时间

