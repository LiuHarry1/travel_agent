# 静态文件基础 URL 配置

## 概述

`static_base_url` 配置项用于设置静态文件（图片）的完整 URL。如果配置了此选项，生成的 Markdown 中的图片链接将使用完整的 URL，而不是相对路径。

## 配置方式

### 方法 1: 环境变量

在 `.env` 文件中添加：

```env
STATIC_BASE_URL=http://localhost:8001
```

### 方法 2: 配置文件

在 `config/settings.py` 中：

```python
static_base_url: str = "http://localhost:8001"
```

## 使用示例

### 不配置 base_url（使用相对路径）

如果 `static_base_url` 为空或未配置，生成的图片 URL 为相对路径：

```html
<img src="/static/images/8836c9a7_tmpzlkzf2jj_image_4.jpeg" alt="Page 1 Image 4" />
```

### 配置 base_url（使用完整 URL）

如果配置了 `static_base_url=http://localhost:8001`，生成的图片 URL 为完整路径：

```html
<img src="http://localhost:8001/static/images/8836c9a7_tmpzlkzf2jj_image_4.jpeg" alt="Page 1 Image 4" />
```

## 应用场景

### 场景 1: 本地开发

```env
STATIC_BASE_URL=http://localhost:8001
```

### 场景 2: 生产环境

```env
STATIC_BASE_URL=https://api.example.com
```

### 场景 3: 使用 CDN

```env
STATIC_BASE_URL=https://cdn.example.com
```

### 场景 4: 相对路径（默认）

```env
STATIC_BASE_URL=
```

或者不设置此配置项，将使用相对路径。

## 注意事项

1. **URL 格式**：确保 base_url 不包含末尾斜杠，系统会自动处理
   - ✅ 正确：`http://localhost:8001`
   - ❌ 错误：`http://localhost:8001/`

2. **协议**：建议使用 `http://` 或 `https://`，但也可以使用其他协议

3. **端口**：如果 FastAPI 运行在非标准端口，记得包含端口号

4. **相对路径**：如果 base_url 为空，将使用相对路径，适合前后端同域的情况

## 示例配置

### 开发环境

```env
STATIC_BASE_URL=http://localhost:8001
STATIC_DIR=static
```

### 生产环境

```env
STATIC_BASE_URL=https://api.yourcompany.com
STATIC_DIR=/var/www/static
```

### Docker 环境

```env
STATIC_BASE_URL=http://localhost:8001
STATIC_DIR=/app/static
```

## 代码示例

```python
from processors.loaders import LoaderFactory
from models.document import DocumentType
from config.settings import get_settings

settings = get_settings()

# 创建加载器，自动使用配置的 base_url
loader = LoaderFactory.create(
    DocumentType.PDF,
    static_dir=settings.static_dir,
    base_url=settings.static_base_url
)

# 加载文档
document = loader.load("document.pdf")

# document.content 中的图片 URL 将使用配置的 base_url
```

