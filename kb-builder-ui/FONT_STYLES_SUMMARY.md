# 字体样式汇总文档

## 一、全局字体设置

### 1. 字体族 (Font Families)

定义在 `src/styles/variables.css` 中：

```css
/* 无衬线字体（系统默认） */
--font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', 'Oxygen',
  'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', sans-serif;

/* 等宽字体（代码使用） */
--font-mono: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', Consolas, 'Courier New', monospace;
```

### 2. 基础字体设置

在 `src/index.css` 中：

```css
html {
  font-size: 16px;  /* 基础字体大小 */
  -webkit-font-smoothing: antialiased;  /* 字体平滑 */
  -moz-osx-font-smoothing: grayscale;
}

body {
  font-family: var(--font-sans);  /* 使用系统字体栈 */
  line-height: 1.6;  /* 行高 1.6 */
  color: var(--text-primary);  /* 主文本颜色 #111827 */
}
```

---

## 二、字体大小系统 (Font Size Scale)

定义在 `src/styles/variables.css` 中，基于 16px 基础大小：

| CSS 变量 | 大小 (rem) | 像素 (px) | 用途 |
|---------|-----------|----------|------|
| `--text-xs` | 0.75rem | **12px** | 极小文本、辅助信息、标签 |
| `--text-sm` | 0.875rem | **14px** | 小文本、按钮、次要信息 |
| `--text-base` | 1rem | **16px** | 基础文本、正文、默认大小 |
| `--text-lg` | 1.125rem | **18px** | 大文本、小标题 |
| `--text-xl` | 1.25rem | **20px** | 超大文本、标题 |
| `--text-2xl` | 1.5rem | **24px** | 二级标题 |
| `--text-3xl` | 1.875rem | **30px** | 一级标题 |
| `--text-4xl` | 2.25rem | **36px** | 特大标题 |

---

## 三、字体粗细 (Font Weight)

定义在 `src/styles/variables.css` 中：

| CSS 变量 | 值 | 用途 |
|---------|---|------|
| `--font-light` | 300 | 细体（较少使用） |
| `--font-normal` | 400 | 正常（默认） |
| `--font-medium` | 500 | 中等（按钮、标签） |
| `--font-semibold` | 600 | 半粗（次要标题） |
| `--font-bold` | 700 | 粗体（主标题） |

---

## 四、各组件字体使用情况

### 1. 应用标题 (App Header)

**文件**: `src/App.css`

```css
.app-header h1 {
  font-size: var(--text-xl);      /* 20px */
  font-weight: var(--font-bold);   /* 700 */
  letter-spacing: -0.5px;         /* 字母间距 */
  line-height: 1.2;
}
```

### 2. 侧边栏列表项

#### Databases 列表
```css
.database-manager-header h3 {
  font-size: var(--text-sm);        /* 14px */
  font-weight: var(--font-semibold); /* 600 */
}

.database-name {
  font-size: var(--text-sm);        /* 14px */
  font-weight: var(--font-semibold); /* 600 */
}

.database-badge {
  font-size: var(--text-xs);        /* 12px */
  font-weight: var(--font-medium);   /* 500 */
}
```

#### Collections 列表
```css
.collection-header h3 {
  font-size: var(--text-xl);        /* 20px */
  font-weight: var(--font-bold);     /* 700 */
}

.collection-name {
  font-size: var(--text-sm);        /* 14px */
  font-weight: var(--font-semibold); /* 600 */
}

.collection-stats {
  font-size: 11px;                  /* 11px（硬编码） */
}
```

#### Source Files 列表
```css
.source-file-header h3 {
  font-size: var(--text-xl);        /* 20px */
}

.source-file-name {
  font-size: var(--text-sm);        /* 14px */
  font-weight: var(--font-semibold); /* 600 */
}

.source-file-meta {
  font-size: 11px;                  /* 11px（硬编码） */
}
```

### 3. 按钮文字

```css
/* 主要按钮 */
button {
  font-size: var(--text-sm);        /* 14px */
  font-weight: var(--font-medium);   /* 500 */
}

/* 设置按钮 */
.settings-btn {
  font-size: var(--text-sm);        /* 14px */
  font-weight: var(--font-medium);   /* 500 */
}
```

### 4. 表单元素

#### 输入框
```css
.form-group input,
.form-group select {
  font-size: var(--text-sm);        /* 14px 或 var(--text-base) 16px */
  font-family: var(--font-sans);
}
```

#### 标签
```css
.form-group label {
  font-size: var(--text-xs);        /* 12px */
  font-weight: var(--font-semibold); /* 600 */
  text-transform: uppercase;        /* 大写字母 */
  letter-spacing: 0.5px;           /* 字母间距 */
}
```

### 5. 代码/等宽字体使用

```css
/* API URL 输入框 */
.api-url-input {
  font-family: 'Monaco', 'Menlo', 'Courier New', monospace;
  font-size: var(--text-sm);        /* 14px */
}

/* 代码块 */
code {
  font-family: var(--font-mono);
  font-size: var(--text-xs);        /* 12px */
}
```

---

## 五、文本颜色系统

| CSS 变量 | 颜色值 | 用途 |
|---------|--------|------|
| `--text-primary` | #111827 | 主要文本（深灰/黑） |
| `--text-secondary` | #6b7280 | 次要文本（中灰） |
| `--text-tertiary` | #9ca3af | 三级文本（浅灰） |
| `--text-inverse` | #ffffff | 反色文本（白色） |

---

## 六、当前发现的不一致之处

### 1. 硬编码的字体大小

以下位置使用了硬编码的像素值，建议改为 CSS 变量：

- `.collection-stats`: `font-size: 11px;` → 可考虑 `var(--text-xs)` (12px)
- `.source-file-meta`: `font-size: 11px;` → 可考虑 `var(--text-xs)` (12px)
- `.form-group small`: `font-size: 10px;` → 可考虑自定义变量或使用 `var(--text-xs)`

### 2. 行高设置

大部分组件未显式设置 `line-height`，继承自 `body` 的 `1.6`。

---

## 七、建议

1. **统一元数据字体大小**: 将 `11px` 统一改为 `var(--text-xs)` (12px) 或创建新的变量
2. **添加行高变量**: 在 variables.css 中添加行高变量系统
3. **规范代码字体**: 统一所有使用等宽字体的地方使用 `var(--font-mono)`

---

## 八、完整 CSS 变量参考

```css
/* Typography Variables */
--font-sans: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', ...;
--font-mono: 'SF Mono', Monaco, 'Cascadia Code', 'Roboto Mono', ...;

--text-xs: 0.75rem;      /* 12px */
--text-sm: 0.875rem;     /* 14px */
--text-base: 1rem;       /* 16px */
--text-lg: 1.125rem;     /* 18px */
--text-xl: 1.25rem;      /* 20px */
--text-2xl: 1.5rem;      /* 24px */
--text-3xl: 1.875rem;    /* 30px */
--text-4xl: 2.25rem;     /* 36px */

--font-light: 300;
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

