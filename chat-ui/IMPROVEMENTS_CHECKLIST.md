# Chat-UI 改进清单

## 🚀 快速改进（可立即实施）

### 1. 提取常量

**文件：** `src/constants/index.ts` (新建)

```typescript
// 会话相关
export const DEFAULT_SESSION_TITLE = 'New chat'
export const MAX_SESSIONS = 10
export const CHAT_SESSIONS_STORAGE_KEY = 'chat-ui-sessions-v2'

// 文件上传
export const MAX_FILE_SIZE = 5 * 1024 * 1024 // 5MB
export const VALID_FILE_EXTENSIONS = ['.txt', '.md', '.json', '.text', '.pdf', '.doc', '.docx']

// API
export const DEFAULT_API_BASE_URL = 'http://localhost:8001'
export const SSE_EVENT_PREFIX = 'data: '

// UI
export const AUTO_SCROLL_THRESHOLD = 40 // px
export const TEXTAREA_MAX_HEIGHT = 200 // px
```

**影响文件：**
- `src/hooks/useChatSessions.tsx`
- `src/hooks/useFileUpload.ts`
- `src/api/client.ts`
- `src/components/ChatPage.tsx`

### 2. 创建工具函数模块

**文件：** `src/utils/markdown.ts` (新建)

```typescript
/**
 * Convert image URLs in text to Markdown image format
 */
export function convertImageUrlsToMarkdown(content: string): string {
  const imageUrlPattern = /(https?:\/\/[^\s]+\.(png|jpg|jpeg|gif|webp|svg|bmp))(?![)\]])/gi
  
  return content.replace(imageUrlPattern, (match, ...args) => {
    const beforeMatch = content.substring(0, content.indexOf(match))
    const afterMatch = content.substring(content.indexOf(match) + match.length)
    
    if (beforeMatch.endsWith('![') && afterMatch.startsWith('](')) {
      return match
    }
    
    const filename = match.split('/').pop()?.split('.')[0] || '图片'
    return `![${filename}](${match})`
  })
}
```

**文件：** `src/utils/errorHandler.ts` (新建)

```typescript
export interface ErrorInfo {
  message: string
  code?: string
  retryable?: boolean
}

export function handleError(error: unknown): ErrorInfo {
  if (error instanceof Error) {
    // 网络错误
    if (error.name === 'AbortError') {
      return { message: 'Request cancelled', code: 'ABORT', retryable: false }
    }
    
    // 超时错误
    if (error.message.includes('timeout')) {
      return { message: 'Request timeout', code: 'TIMEOUT', retryable: true }
    }
    
    // 其他错误
    return { message: error.message, retryable: true }
  }
  
  return { message: 'Unknown error occurred', retryable: true }
}
```

### 3. 优化 API Client

**文件：** `src/api/client.ts` (改进)

```typescript
import { handleError, type ErrorInfo } from '../utils/errorHandler'
import { DEFAULT_API_BASE_URL } from '../constants'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? DEFAULT_API_BASE_URL

export interface RequestConfig extends RequestInit {
  timeout?: number
  retries?: number
}

class ApiClient {
  private baseURL: string

  constructor(baseURL: string) {
    this.baseURL = baseURL
  }

  async request<T>(path: string, config: RequestConfig = {}): Promise<T> {
    const { timeout = 30000, retries = 0, ...fetchConfig } = config
    
    const controller = new AbortController()
    const timeoutId = timeout ? setTimeout(() => controller.abort(), timeout) : null
    
    try {
      const response = await fetch(`${this.baseURL}${path}`, {
        ...fetchConfig,
        signal: controller.signal,
      })
      
      if (timeoutId) clearTimeout(timeoutId)
      
      if (!response.ok) {
        const detail = await response.text()
        throw new Error(detail || `Request failed with status ${response.status}`)
      }
      
      return await response.json()
    } catch (error) {
      if (timeoutId) clearTimeout(timeoutId)
      
      const errorInfo = handleError(error)
      
      // 重试逻辑
      if (errorInfo.retryable && retries > 0) {
        await new Promise(resolve => setTimeout(resolve, 1000))
        return this.request<T>(path, { ...config, retries: retries - 1 })
      }
      
      throw error
    }
  }
}

export const apiClient = new ApiClient(API_BASE_URL)

export function getApiUrl(path: string): string {
  return `${API_BASE_URL}${path}`
}
```

### 4. 拆分 useChat Hook

**文件：** `src/hooks/useChatState.ts` (新建)

```typescript
import { useState, useEffect, useRef } from 'react'
import type { ChatResponse, Alert } from '../types'
import { useChatSessions } from './useChatSessions'

export function useChatState() {
  const { activeSession, updateActiveSession, createSession } = useChatSessions()
  const hasInitialized = useRef(false)

  const [sessionId, setSessionId] = useState<string | undefined>(activeSession?.sessionId)
  const [message, setMessage] = useState('')
  const [history, setHistory] = useState<ChatResponse['history']>(activeSession?.history ?? [])
  const [loading, setLoading] = useState(false)
  const [alert, setAlert] = useState<Alert | null>(null)

  // 同步状态
  useEffect(() => {
    if (!activeSession && !hasInitialized.current) {
      hasInitialized.current = true
      createSession()
      return
    }
    
    if (activeSession) {
      hasInitialized.current = true
      setSessionId(activeSession.sessionId)
      setHistory(activeSession.history)
    }
  }, [activeSession, createSession])

  return {
    sessionId,
    message,
    setMessage,
    history,
    setHistory,
    loading,
    setLoading,
    alert,
    setAlert,
    updateActiveSession,
  }
}
```

**文件：** `src/hooks/useChatStream.ts` (新建)

```typescript
import { useRef } from 'react'
import type { StreamEvent, ToolCall } from '../types'
import { sendChatMessageStream } from '../api'

export function useChatStream() {
  const abortControllerRef = useRef<AbortController | null>(null)

  const startStream = async (
    payload: any,
    callbacks: {
      onChunk: (chunk: string) => void
      onDone: () => void
      onError: (error: string) => void
      onEvent?: (event: StreamEvent) => void
    }
  ) => {
    abortControllerRef.current = new AbortController()
    
    try {
      await sendChatMessageStream(
        payload,
        callbacks.onChunk,
        callbacks.onDone,
        callbacks.onError,
        callbacks.onEvent,
        abortControllerRef.current.signal
      )
    } catch (error) {
      if (error instanceof Error && error.name !== 'AbortError') {
        callbacks.onError(error.message)
      }
    }
  }

  const stopStream = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
  }

  return { startStream, stopStream }
}
```

### 5. 拆分 ChatPage 组件

**文件：** `src/components/ChatInput.tsx` (新建)

```typescript
import { useRef, useEffect, type FormEvent } from 'react'
import { FileUploadArea } from './FileUploadArea'
import { Alert } from './Alert'
import { TEXTAREA_MAX_HEIGHT } from '../constants'

interface ChatInputProps {
  message: string
  setMessage: (message: string) => void
  loading: boolean
  filesWithContent: Array<{ file: File; content?: string; loading?: boolean; error?: string }>
  dragOver: boolean
  fileInputRef: React.RefObject<HTMLInputElement>
  onDragOver: (e: React.DragEvent) => void
  onDragLeave: (e: React.DragEvent) => void
  onDrop: (e: React.DragEvent) => void
  onFileSelect: (e: React.ChangeEvent<HTMLInputElement>) => void
  onRemoveFile: (index: number) => void
  onSubmit: (e: FormEvent<HTMLFormElement>) => void
  onStop: () => void
  alert: { type: 'error' | 'success'; message: string } | null
  setAlert: (alert: { type: 'error' | 'success'; message: string } | null) => void
}

export function ChatInput({
  message,
  setMessage,
  loading,
  filesWithContent,
  dragOver,
  fileInputRef,
  onDragOver,
  onDragLeave,
  onDrop,
  onFileSelect,
  onRemoveFile,
  onSubmit,
  onStop,
  alert,
}: ChatInputProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current
    if (!textarea) return

    const adjustHeight = () => {
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, TEXTAREA_MAX_HEIGHT)}px`
    }

    adjustHeight()
    textarea.addEventListener('input', adjustHeight)
    return () => textarea.removeEventListener('input', adjustHeight)
  }, [message])

  return (
    <FileUploadArea
      uploadedFiles={[]}
      dragOver={dragOver}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onFileSelect={onFileSelect}
      onRemoveFile={onRemoveFile}
      fileInputRef={fileInputRef}
    >
      <form onSubmit={onSubmit} className="chat-input-form">
        <div className="chat-input-wrapper">
          {/* File preview */}
          {filesWithContent.length > 0 && (
            <div className="files-preview-inside">
              {/* File preview chips */}
            </div>
          )}
          
          <textarea
            ref={textareaRef}
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={dragOver ? 'Release to upload file...' : 'Enter message...'}
            rows={3}
            className="chat-textarea"
            disabled={loading}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                if (!loading && message.trim()) {
                  onSubmit(e as any)
                }
              }
            }}
          />
          
          <div className="chat-input-actions">
            {/* Action buttons */}
          </div>
        </div>
        {alert && <Alert type={alert.type} message={alert.message} className="alert-toast" />}
      </form>
    </FileUploadArea>
  )
}
```

### 6. 添加 React.memo 优化

**文件：** `src/components/MessageList.tsx` (改进)

```typescript
import { memo, useMemo, useState } from 'react'
// ... imports

export const MessageList = memo(function MessageList({ 
  history, 
  loading, 
  latestUserMessageRef, 
  onRegenerate 
}: MessageListProps) {
  // ... existing code
}, (prevProps, nextProps) => {
  // 自定义比较函数
  return (
    prevProps.history.length === nextProps.history.length &&
    prevProps.loading === nextProps.loading &&
    prevProps.onRegenerate === nextProps.onRegenerate
  )
})
```

### 7. 启用 TypeScript 严格模式

**文件：** `tsconfig.json` (改进)

```json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "alwaysStrict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

## 📋 实施优先级

### 高优先级（立即实施）
- [ ] 提取常量
- [ ] 创建工具函数模块
- [ ] 启用 TypeScript 严格模式
- [ ] 拆分 useChat hook

### 中优先级（1-2周内）
- [ ] 优化 API Client
- [ ] 拆分 ChatPage 组件
- [ ] 添加 React.memo 优化
- [ ] 添加错误边界

### 低优先级（长期改进）
- [ ] 添加单元测试
- [ ] 实现虚拟滚动
- [ ] 完善文档
- [ ] 可访问性改进

## 🔍 代码审查检查点

在实施改进时，注意以下检查点：

1. **类型安全**
   - [ ] 所有函数都有明确的返回类型
   - [ ] 没有使用 `any` 类型
   - [ ] 所有 props 都有类型定义

2. **性能**
   - [ ] 大组件使用 `React.memo`
   - [ ] 回调函数使用 `useCallback`
   - [ ] 计算值使用 `useMemo`

3. **错误处理**
   - [ ] 所有异步操作都有错误处理
   - [ ] 错误信息对用户友好
   - [ ] 有错误日志记录

4. **代码质量**
   - [ ] 没有重复代码
   - [ ] 函数职责单一
   - [ ] 命名清晰明确

5. **测试**
   - [ ] 关键逻辑有单元测试
   - [ ] 组件有渲染测试
   - [ ] 集成测试覆盖主要流程
