# Docker Desktop 磁盘镜像大小设置指南

## 问题
Milvus 在 Docker Desktop 中运行时出现 "No space left on device" 错误，即使主机磁盘还有空间。这通常是因为 Docker Desktop 的虚拟磁盘镜像文件大小限制。

## 解决方案：增加 Docker Desktop 磁盘镜像大小

### 步骤 1：打开 Docker Desktop 设置

1. **启动 Docker Desktop**（如果还没有运行）
   - 在 Mac 上，点击 Dock 中的 Docker 图标
   - 或者从 Applications 文件夹打开 Docker Desktop

2. **打开设置**
   - 点击 Docker Desktop 窗口右上角的 **设置图标**（齿轮 ⚙️）
   - 或者使用菜单：`Docker Desktop` > `Settings`（或 `Preferences`）

### 步骤 2：进入 Resources 设置

1. 在左侧菜单中，点击 **Resources**
2. 然后点击 **Advanced** 子菜单

### 步骤 3：调整磁盘镜像大小

1. 找到 **Disk image size** 设置
   - 这个设置控制 Docker 可以使用的最大磁盘空间
   - 默认值通常是 **64 GB** 或 **128 GB**

2. **增加磁盘镜像大小**
   - 点击 **Disk image size** 旁边的滑块或输入框
   - 建议设置为：
     - **最小：128 GB**（如果当前是 64 GB）
     - **推荐：256 GB**（如果主机磁盘空间充足）
     - **最大：根据你的主机磁盘空间决定**（不要超过主机可用空间）

3. **应用设置**
   - 点击右下角的 **Apply & Restart** 按钮
   - Docker Desktop 会重启以应用新设置
   - ⚠️ **注意**：这个过程可能需要几分钟，因为 Docker 需要调整虚拟磁盘文件大小

### 步骤 4：验证设置

1. 等待 Docker Desktop 重启完成
2. 重新打开设置 > Resources > Advanced
3. 确认 **Disk image size** 显示为你设置的新值

## 其他相关设置

### 同时检查这些设置：

1. **Memory（内存）**
   - 建议至少 4 GB，如果运行 Milvus 建议 8 GB 或更多

2. **CPUs（CPU 核心数）**
   - 建议至少 2 个核心

3. **Swap（交换空间）**
   - 可以设置为与内存相同的大小

## 如果设置后仍有问题

### 方案 A：清理 Docker 资源

```bash
# 清理未使用的容器、网络、镜像
docker system prune

# 清理所有未使用的资源（包括卷，谨慎使用）
docker system prune -a --volumes
```

### 方案 B：检查 Docker 磁盘使用情况

```bash
# 查看 Docker 磁盘使用
docker system df

# 查看 Milvus 容器磁盘使用
docker exec milvus-standalone df -h
```

### 方案 C：重启 Milvus 容器

```bash
docker restart milvus-standalone
```

## 注意事项

1. **磁盘镜像大小不能超过主机可用空间**
   - 确保你的 Mac 有足够的磁盘空间
   - 可以通过 `df -h` 命令查看

2. **增加磁盘镜像大小需要时间**
   - Docker 需要调整虚拟磁盘文件
   - 这个过程可能需要几分钟到十几分钟

3. **磁盘镜像文件位置**
   - Mac: `~/Library/Containers/com.docker.docker/Data/vms/0/data/Docker.raw`
   - 这个文件会随着你设置的磁盘镜像大小而增长

4. **如果主机磁盘空间不足**
   - 先清理主机磁盘空间
   - 或者考虑将 Docker 数据移动到外部磁盘

## 验证修复

设置完成后，可以运行以下命令验证：

```bash
# 检查 Docker 磁盘使用
docker system df

# 测试 Milvus 连接
python check_docker_milvus.py

# 尝试重新索引文档
# （通过你的应用界面或 API）
```

## 快速参考

**设置路径：**
```
Docker Desktop → Settings (⚙️) → Resources → Advanced → Disk image size
```

**推荐值：**
- 最小：128 GB
- 推荐：256 GB
- 根据主机空间调整

