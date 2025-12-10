# API URL 配置指南

## 概述

kb-builder-ui 支持配置后端 API 的 URL，可以通过以下两种方式配置：

1. **环境变量**（构建时配置）
2. **UI 界面配置**（运行时配置，推荐）

## 方式 1：环境变量配置（构建时）

### 步骤

1. 在项目根目录创建 `.env` 文件：

```bash
cd kb-builder-ui
touch .env
```

2. 在 `.env` 文件中添加：

```env
# Backend API URL
VITE_API_URL=http://localhost:8005
```

3. 重启开发服务器：

```bash
npm run dev
```

### 不同环境的配置示例

**开发环境：**
```env
VITE_API_URL=http://localhost:8005
```

**生产环境：**
```env
VITE_API_URL=https://api.yourdomain.com
```

**Docker 环境：**
```env
VITE_API_URL=http://localhost:8005
```

## 方式 2：UI 界面配置（运行时，推荐）

### 步骤

1. 启动前端应用
2. 点击右上角的 **Settings** 按钮（⚙️）
3. 在配置面板中，选择 **API Settings** 标签页
4. 在 **Backend API URL** 输入框中输入你的后端 API URL
5. 点击 **Test Connection** 按钮测试连接
6. 配置会自动保存到浏览器的本地存储中

### 优势

- ✅ 无需重新构建应用
- ✅ 配置保存在浏览器本地，持久化
- ✅ 可以随时切换不同的后端 URL
- ✅ 提供连接测试功能

## 默认值

如果没有配置，默认使用：`http://localhost:8005`

## 常见配置场景

### 场景 1：本地开发

```
API URL: http://localhost:8005
```

### 场景 2：Docker 容器

如果后端运行在 Docker 容器中，且端口已映射：

```
API URL: http://localhost:8005
```

### 场景 3：远程服务器

如果后端部署在远程服务器：

```
API URL: http://your-server-ip:8005
或
API URL: https://api.yourdomain.com
```

### 场景 4：开发代理

如果使用开发代理（如 Vite proxy）：

```
API URL: http://localhost:5173/api
```

## 验证配置

配置完成后，可以通过以下方式验证：

1. **UI 测试**：在 API Settings 标签页点击 "Test Connection"
2. **浏览器控制台**：查看网络请求，确认请求发送到正确的 URL
3. **功能测试**：尝试上传文件，看是否能正常连接到后端

## 故障排除

### 问题 1：CORS 错误

如果遇到 CORS 错误，需要确保后端配置了正确的 CORS 设置：

```python
# 在 kb-builder-service/main.py 中
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # 添加前端 URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 问题 2：连接超时

- 检查后端服务是否正在运行
- 检查 URL 是否正确
- 检查防火墙设置
- 检查端口是否被占用

### 问题 3：配置不生效

- 清除浏览器缓存
- 清除 localStorage：在浏览器控制台运行 `localStorage.removeItem('kb-config')`
- 重新加载页面

## 技术细节

- 配置保存在 `localStorage` 中，键名为 `kb-config`
- API URL 配置在 `AppConfig.apiUrl` 字段中
- 当配置更改时，会自动更新 `ApiClient` 实例的 base URL
- 所有 API 请求都会使用配置的 URL

## 相关文件

- `src/types/config.ts` - 配置类型定义
- `src/api/client.ts` - API 客户端实现
- `src/components/ConfigPanel.tsx` - 配置面板 UI
- `src/App.tsx` - 主应用组件，管理配置状态

