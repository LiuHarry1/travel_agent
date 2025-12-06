# 侧边栏布局优化建议

## 当前状态分析

### 布局结构
```
侧边栏 (320px 宽度)
├── Databases 部分
│   ├── 标题 + "New" 按钮
│   └── 数据库列表
└── Collections 部分 (flex: 1)
    ├── 标题 + "New" 按钮
    ├── 搜索框 + 刷新按钮
    └── 集合列表（可滚动）
```

### 当前问题

1. **视觉分隔不够清晰**
   - Databases 有底部边框（`border-bottom`）
   - Collections 有顶部内边距（`padding: var(--spacing-lg)`）
   - 两部分之间的分隔不够明显

2. **间距不统一**
   - Databases: `padding: var(--spacing-md)` (16px)
   - Collections: `padding: var(--spacing-lg)` (24px)
   - 标题间距不一致

3. **滚动区域不明确**
   - Collections 列表可以滚动，但滚动区域不够明显
   - 整体侧边栏的滚动行为可能需要优化

4. **视觉层次**
   - Databases 部分相对较小，可能被忽略
   - 两部分的重要性关系不够清晰

## 优化方案

### 方案 1: 统一间距和分隔（推荐）

**改进点：**
1. 统一两部分的内边距为 `var(--spacing-md)` (16px)
2. 添加清晰的分隔线
3. 优化滚动区域显示

### 方案 2: 增强视觉层次

**改进点：**
1. 为 Databases 部分添加更明显的背景区分
2. 优化两部分之间的间距
3. 统一标题样式（已处理字体大小）

### 方案 3: 优化滚动行为

**改进点：**
1. 明确滚动区域边界
2. 优化滚动条样式
3. 确保 Databases 部分始终可见

## 具体改进建议

### 1. 统一内边距
```css
/* Databases 和 Collections 都使用相同的 padding */
.database-manager {
  padding: var(--spacing-md);
}

.collection-manager {
  padding: var(--spacing-md);
}
```

### 2. 优化分隔线
```css
/* Databases 底部添加更明显的分隔 */
.database-manager {
  border-bottom: 1px solid var(--border-light);
  margin-bottom: var(--spacing-sm);
  padding-bottom: var(--spacing-md);
}
```

### 3. 优化 Collections 的滚动区域
```css
.collection-list {
  /* 确保滚动区域清晰可见 */
  max-height: calc(100vh - 400px); /* 根据实际情况调整 */
  overflow-y: auto;
}
```

### 4. 统一标题区域间距
- Databases 标题：`margin-bottom: var(--spacing-sm)`
- Collections 标题：`margin-bottom: var(--spacing-md)`

建议统一为 `var(--spacing-sm)`

