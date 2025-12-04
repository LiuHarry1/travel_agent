# 统一文档加载器实现总结

## ✅ 已完成的功能

### 1. 统一文档加载器 (`UnifiedLoader`)
- ✅ 支持 PDF, DOCX, HTML, TXT, MD 格式
- ✅ 自动转换为 Markdown 格式
- ✅ 原文件保存到 `static/sources/`
- ✅ 图片提取并保存到 `static/images/`
- ✅ 图片路径转换为 HTML `<img>` 标签

### 2. 文件处理功能

#### PDF 处理
- ✅ 文本提取（使用 `pdfplumber`）
- ✅ 图片提取（使用 `PyMuPDF`，可选）
- ✅ 分页处理

#### DOCX 处理
- ✅ 文本提取（使用 `python-docx`）
- ✅ 图片提取（从 ZIP 包中提取）
- ✅ 图片格式自动检测

#### HTML 处理
- ✅ HTML 解析（使用 `beautifulsoup4`）
- ✅ 转换为 Markdown（使用 `markdownify`）
- ✅ 本地图片提取
- ✅ 网络图片下载（使用 `requests`）

#### Markdown 处理
- ✅ 原生 Markdown 支持
- ✅ 图片路径处理（相对路径和绝对路径）
- ✅ 网络图片下载（可选）
- ✅ HTML img 标签处理

#### TXT 处理
- ✅ 纯文本读取
- ✅ 多编码支持（UTF-8, GBK）

### 3. 集成

- ✅ 更新 `LoaderFactory` 自动使用 `UnifiedLoader`
- ✅ 更新 `IndexingService` 使用统一加载器
- ✅ 更新 API 路由使用统一加载器
- ✅ 添加静态文件服务到 FastAPI

### 4. 配置

- ✅ 添加 `static_dir` 配置到 `settings.py`
- ✅ 支持环境变量配置
- ✅ 自动创建目录

### 5. 依赖管理

- ✅ 更新 `requirements.txt` 添加所有必需依赖
- ✅ 可选依赖处理（PyMuPDF 用于 PDF 图片提取）

## 📁 文件结构

```
knowledge-base-builder/
├── processors/
│   └── loaders/
│       ├── unified_loader.py      # 新增：统一加载器
│       ├── factory.py              # 更新：支持统一加载器
│       └── __init__.py             # 更新：导出 UnifiedLoader
├── config/
│   └── settings.py                 # 更新：添加 static_dir 配置
├── services/
│   └── indexing_service.py        # 更新：使用统一加载器
├── api/
│   └── routes/
│       └── indexing.py             # 更新：使用统一加载器
├── main.py                         # 更新：添加静态文件服务
├── requirements.txt                # 更新：添加依赖
└── docs/
    ├── UNIFIED_LOADER.md           # 新增：详细文档
    └── QUICK_START_UNIFIED_LOADER.md  # 新增：快速开始
```

## 🚀 使用方法

### 基本使用

```python
from processors.loaders import LoaderFactory
from models.document import DocumentType

loader = LoaderFactory.create(DocumentType.PDF, static_dir="static")
document = loader.load("document.pdf")
```

### API 使用

通过 API 上传文件，系统会自动使用统一加载器：

```bash
curl -X POST "http://localhost:8001/api/v1/upload/stream" \
  -F "file=@document.pdf" \
  -F "collection_name=my_collection"
```

## 📦 依赖列表

必需依赖：
- `python-docx>=1.1.0` - DOCX 文件
- `pdfplumber>=0.10.0` - PDF 文本提取
- `beautifulsoup4>=4.12.0` - HTML 解析
- `markdownify>=0.11.6` - HTML 转 Markdown
- `Pillow>=10.0.0` - 图片处理
- `requests>=2.31.0` - 网络图片下载（已存在）

可选依赖：
- `PyMuPDF>=1.23.0` - PDF 图片提取（推荐安装）

## 🎯 特性亮点

1. **统一接口**: 所有格式使用相同的接口
2. **自动转换**: 自动转换为 Markdown，便于后续处理
3. **图片处理**: 自动提取、保存和路径转换
4. **网络支持**: 支持下载网络图片
5. **容错处理**: 优雅处理缺失的依赖和错误
6. **编码支持**: 自动处理多种文本编码

## 📝 注意事项

1. **PyMuPDF**: 如果未安装，PDF 图片提取会被跳过，但文本提取仍可工作
2. **网络图片**: 需要网络连接才能下载网络图片
3. **大文件**: 大文件处理可能需要较长时间
4. **内存**: 图片会完全加载到内存，注意大图片的内存占用
5. **静态文件服务**: 确保 FastAPI 静态文件服务已配置

## 🔧 配置选项

在 `.env` 文件中配置：

```env
STATIC_DIR=static
```

或在代码中：

```python
from config.settings import get_settings
settings = get_settings()
static_dir = settings.static_dir  # 默认: "static"
```

## 🐛 故障排除

### PDF 图片无法提取
安装 PyMuPDF: `pip install PyMuPDF`

### 静态文件无法访问
检查 `static` 目录是否存在，以及 FastAPI 静态文件服务是否已配置

### 编码错误
系统会自动尝试 UTF-8 和 GBK 编码

## 📚 文档

- 详细文档: `docs/UNIFIED_LOADER.md`
- 快速开始: `docs/QUICK_START_UNIFIED_LOADER.md`

