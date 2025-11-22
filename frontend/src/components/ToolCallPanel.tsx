import { useState } from 'react'
import type { ToolCall } from '../types'

interface ToolCallPanelProps {
  toolCall: ToolCall
}

export function ToolCallPanel({ toolCall }: ToolCallPanelProps) {
  const [expanded, setExpanded] = useState(false)
  const [inputExpanded, setInputExpanded] = useState(false)
  const [resultExpanded, setResultExpanded] = useState(false)

  const getStatusIcon = () => {
    switch (toolCall.status) {
      case 'calling':
        return (
          <div className="tool-call-spinner">
            <span></span>
            <span></span>
            <span></span>
          </div>
        )
      case 'completed':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        )
      case 'error':
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        )
      default:
        return (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
        )
    }
  }

  const getStatusText = () => {
    switch (toolCall.status) {
      case 'calling':
        return '调用中...'
      case 'completed':
        return '已完成'
      case 'error':
        return '失败'
      default:
        return '未知'
    }
  }

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

  const getResultSummary = (): { text: string; count?: number } => {
    if (!toolCall.result) return { text: '' }
    
    try {
      const result = typeof toolCall.result === 'string' 
        ? JSON.parse(toolCall.result) 
        : toolCall.result
      
      // Handle different result types
      if (typeof result === 'object' && result !== null) {
        // If result has results array (like Tavily search results)
        if (Array.isArray(result.results) && result.results.length > 0) {
          return { text: `${result.results.length}篇资料`, count: result.results.length }
        }
        // If result has data array
        if (Array.isArray(result.data) && result.data.length > 0) {
          return { text: `${result.data.length}篇资料`, count: result.data.length }
        }
        // If result has items array
        if (Array.isArray(result.items) && result.items.length > 0) {
          return { text: `${result.items.length}篇资料`, count: result.items.length }
        }
        // If result has answer field (like Tavily)
        if (result.answer) {
          // Also check if there are results
          if (Array.isArray(result.results) && result.results.length > 0) {
            return { text: `${result.results.length}篇资料`, count: result.results.length }
          }
          return { text: result.answer.substring(0, 50) + (result.answer.length > 50 ? '...' : '') }
        }
        // If result has text field
        if (result.text) {
          return { text: result.text.substring(0, 50) + (result.text.length > 50 ? '...' : '') }
        }
        // If result has content field
        if (result.content) {
          return { text: result.content.substring(0, 50) + (result.content.length > 50 ? '...' : '') }
        }
        // Count object keys
        const keys = Object.keys(result)
        if (keys.length > 0) {
          return { text: `包含 ${keys.length} 个字段` }
        }
      }
      
      // If result is a string
      if (typeof result === 'string') {
        return { text: result.substring(0, 50) + (result.length > 50 ? '...' : '') }
      }
      
      return { text: '执行成功' }
    } catch {
      // If parsing fails, treat as string
      const str = String(toolCall.result)
      return { text: str.substring(0, 50) + (str.length > 50 ? '...' : '') }
    }
  }

  const status = toolCall.status || 'calling'
  const hasInput = toolCall.arguments && Object.keys(toolCall.arguments).length > 0
  const hasResult = toolCall.result !== undefined && toolCall.result !== null
  const hasError = toolCall.error
  const resultSummary = hasResult ? getResultSummary() : { text: '' }

  return (
    <div className={`tool-call-panel ${status}`}>
      <button
        className="tool-call-panel-header"
        onClick={() => setExpanded(!expanded)}
        type="button"
      >
        <div className="tool-call-panel-title">
          <span className="tool-call-icon">{getStatusIcon()}</span>
          <span className="tool-call-name">{toolCall.name}</span>
          <span className={`tool-call-status-badge ${status}`}>{getStatusText()}</span>
        </div>
        <svg
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className={`tool-call-expand-icon ${expanded ? 'expanded' : ''}`}
        >
          <polyline points="6 9 12 15 18 9" />
        </svg>
      </button>
      
      {/* Compact summary view when collapsed and has result - similar to image 2 style */}
      {!expanded && hasResult && status === 'completed' && resultSummary.text && (
        <button
          className="tool-call-summary"
          onClick={() => setExpanded(true)}
          type="button"
        >
          <span className="tool-call-summary-text">{resultSummary.text}</span>
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="tool-call-summary-arrow"
          >
            <polyline points="9 18 15 12 9 6" />
          </svg>
        </button>
      )}

      {expanded && (
        <div className="tool-call-panel-content">
          {hasInput && (
            <div className="tool-call-section">
              <button
                className="tool-call-section-header"
                onClick={() => setInputExpanded(!inputExpanded)}
                type="button"
              >
                <span>输入参数</span>
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className={inputExpanded ? 'expanded' : ''}
                >
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </button>
              {inputExpanded && (
                <pre className="tool-call-json">{formatJSON(toolCall.arguments)}</pre>
              )}
            </div>
          )}

          {hasResult && (
            <div className="tool-call-section">
              <button
                className="tool-call-section-header"
                onClick={() => setResultExpanded(!resultExpanded)}
                type="button"
              >
                <span>执行结果</span>
                {resultSummary.text && (
                  <span className="tool-call-result-preview">{resultSummary.text}</span>
                )}
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  className={resultExpanded ? 'expanded' : ''}
                >
                  <polyline points="6 9 12 15 18 9" />
                </svg>
              </button>
              {resultExpanded && (
                <pre className="tool-call-json">{formatJSON(toolCall.result)}</pre>
              )}
            </div>
          )}

          {hasError && (
            <div className="tool-call-error-section">
              <div className="tool-call-error-label">错误信息</div>
              <div className="tool-call-error-message">{toolCall.error}</div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

