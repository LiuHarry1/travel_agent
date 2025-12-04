# 故障排除指南

## 网络连接问题

### 问题：TLS handshake timeout

如果遇到 `TLS handshake timeout` 错误，这通常是因为无法连接到 Docker 镜像源。

### 解决方案

#### 方案 1: 配置 Docker 镜像加速器（推荐）

1. 打开 Docker Desktop
2. 进入 Settings → Docker Engine
3. 添加或修改镜像加速器配置：

```json
{
  "registry-mirrors": [
    "https://docker.mirrors.ustc.edu.cn",
    "https://hub-mirror.c.163.com",
    "https://mirror.baidubce.com"
  ]
}
```

4. 点击 "Apply & Restart"
5. 重新运行 `docker compose up -d`

#### 方案 2: 使用代理

如果你有代理，可以在 Docker Desktop 中配置：

1. Settings → Resources → Proxies
2. 配置你的代理设置
3. 重启 Docker Desktop

#### 方案 3: 手动拉取镜像

```bash
# 先手动拉取基础镜像
docker pull python:3.11-slim

# 然后再构建
docker compose up -d
```

#### 方案 4: 使用国内镜像源构建

修改 Dockerfile，使用国内镜像源：

```dockerfile
FROM registry.cn-hangzhou.aliyuncs.com/google_containers/python:3.11-slim
```

或者使用其他可用的镜像源。

#### 方案 5: 检查网络连接

```bash
# 测试网络连接
ping docker.mirrors.ustc.edu.cn

# 或者尝试直接访问
curl -I https://docker.mirrors.ustc.edu.cn
```

### 临时解决方案：使用预构建镜像

如果网络问题持续，可以考虑：

1. 使用 VPN 或代理
2. 在能正常访问 Docker Hub 的环境中构建镜像，然后导出/导入
3. 联系网络管理员检查防火墙设置

## 其他常见问题

### 端口被占用

如果 8001 端口被占用，修改 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "8002:8000"  # 改为其他端口
```

### 内存不足

如果遇到内存不足错误，减少内存限制：

```yaml
deploy:
  resources:
    limits:
      memory: 2G  # 减少内存限制
```

### 模型下载失败

如果模型下载失败，可以：

1. 手动下载模型到 `~/.cache/huggingface` 目录
2. 使用 VPN 或代理
3. 配置 Hugging Face 镜像源

