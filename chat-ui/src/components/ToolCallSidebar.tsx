import type { ToolCall } from '../types'

interface ToolCallSidebarProps {
  toolCall: ToolCall
  onClose: () => void
}

export function ToolCallSidebar({ toolCall, onClose }: ToolCallSidebarProps) {
  const formatJSON = (obj: any): string => {
    if (typeof obj === 'string') {
      try {
        const parsed = JSON.parse(obj)
        return JSON.stringify(parsed, null, 2)
      } catch {
        return obj
      }
    }
    if (typeof obj === 'object' && obj !== null) {
      return JSON.stringify(obj, null, 2)
    }
    return String(obj)
  }

  const hasInput = toolCall.arguments && Object.keys(toolCall.arguments).length > 0
  const hasResult = toolCall.result !== undefined && toolCall.result !== null
  const hasError = toolCall.error

  return (
    <>
      {/* Backdrop */}
      <div className="tool-call-sidebar-backdrop" onClick={onClose} />
      
      {/* Sidebar */}
      <div className="tool-call-sidebar">
        <div className="tool-call-sidebar-header">
          <div className="tool-call-sidebar-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 1 .3.7v6.8a1 1 0 0 1-.3.7l-1.6 1.6a1 1 0 0 0 0 1.4 1 1 0 0 0 1.4 0l3-3a1 1 0 0 0 .3-.7V8a1 1 0 0 0-.3-.7l-3-3a1 1 0 0 0-1.4 1.4z" />
              <path d="M9.3 17.7a1 1 0 0 0 0-1.4l-1.6-1.6a1 1 0 0 1-.3-.7V8a1 1 0 0 1 .3-.7l1.6-1.6a1 1 0 0 0 0-1.4 1 1 0 0 0-1.4 0l-3 3A1 1 0 0 0 4 8v6.8a1 1 0 0 0 .3.7l3 3a1 1 0 0 0 1.4-1.4z" />
            </svg>
            <span>{toolCall.name}</span>
          </div>
          <button className="tool-call-sidebar-close" onClick={onClose} type="button">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className="tool-call-sidebar-content">
          {hasInput && (
            <div className="tool-call-sidebar-section">
              <div className="tool-call-sidebar-section-title">输入参数</div>
              <pre className="tool-call-sidebar-json">{formatJSON(toolCall.arguments)}</pre>
            </div>
          )}

          {hasResult && (
            <div className="tool-call-sidebar-section">
              <div className="tool-call-sidebar-section-title">执行结果</div>
              <pre className="tool-call-sidebar-json">{formatJSON(toolCall.result)}</pre>
            </div>
          )}

          {hasError && (
            <div className="tool-call-sidebar-section">
              <div className="tool-call-sidebar-section-title error">错误信息</div>
              <div className="tool-call-sidebar-error">{toolCall.error}</div>
            </div>
          )}

          {!hasInput && !hasResult && !hasError && (
            <div className="tool-call-sidebar-empty">暂无详细信息</div>
          )}
        </div>
      </div>
    </>
  )
}

