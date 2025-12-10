import { useMemo, useState, memo, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter'
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism'
import type { ChatTurn, ToolCall } from '../types'
import { ToolCallSidebar } from './ToolCallSidebar'
import { CodeCopyButton } from './CodeCopyButton'
import { convertImageUrlsToMarkdown } from '../utils/markdown'

interface MessageListProps {
  history: ChatTurn[]
  loading?: boolean
  latestUserMessageRef?: React.RefObject<HTMLDivElement | null>
  onRegenerate?: () => void
}

export const MessageList = memo(function MessageList({ history, loading, latestUserMessageRef, onRegenerate }: MessageListProps) {
  // Track copied and feedback state for each message by index
  const [copiedStates, setCopiedStates] = useState<Record<number, boolean>>({})
  const [feedbackStates, setFeedbackStates] = useState<Record<number, 'up' | 'down' | null>>({})
  // Track which tool call is selected for sidebar display
  const [selectedToolCall, setSelectedToolCall] = useState<{ messageIndex: number; toolCall: ToolCall } | null>(null)

  const latestUserIndex = useMemo(() => {
    for (let i = history.length - 1; i >= 0; i--) {
      if (history[i].role === 'user') {
        return i
      }
    }
    return null
  }, [history])

  const handleCopy = useCallback(async (content: string, index: number) => {
    try {
      await navigator.clipboard.writeText(content)
      setCopiedStates(prev => ({ ...prev, [index]: true }))
      setTimeout(() => {
        setCopiedStates(prev => ({ ...prev, [index]: false }))
      }, 2000)
    } catch (err) {
      console.error('Failed to copy:', err)
    }
  }, [])

  const handleFeedback = useCallback((type: 'up' | 'down', index: number) => {
    setFeedbackStates(prev => ({ ...prev, [index]: type }))
    // TODO: Send feedback to backend if needed
  }, [])

  if (history.length === 0) {
    return (
      <div className="empty-chat-state">
        <h3 className="empty-chat-title">
          你好！我是您的旅行助手。我可以帮助您规划旅行、回答旅行相关问题、查找目的地信息等。
        </h3>
      </div>
    )
  }

  // Check if last message is from assistant
  const lastAssistantIndex = history.length - 1
  const isLastAssistant = history[history.length - 1]?.role === 'assistant'
  
  // Find the assistant message index that comes right after the latest user message
  const latestAssistantAfterUserIndex = useMemo(() => {
    if (latestUserIndex === null) return null
    // Check if the next message after latest user is an assistant message
    const nextIndex = latestUserIndex + 1
    if (nextIndex < history.length && history[nextIndex]?.role === 'assistant') {
      return nextIndex
    }
    return null
  }, [history, latestUserIndex])

  const handleToolCallSelect = useCallback((messageIndex: number, toolCall: ToolCall) => {
    setSelectedToolCall({ messageIndex, toolCall })
  }, [])

  const handleToolCallClose = useCallback(() => {
    setSelectedToolCall(null)
  }, [])

  return (
    <div className="chat-messages">
      {history.map((turn, index) => {
        const copied = copiedStates[index] || false
        const feedback = feedbackStates[index] || null
        const isLatestUserMessage = latestUserIndex !== null && index === latestUserIndex
        const isLastAssistantMessage = isLastAssistant && index === lastAssistantIndex
        // Apply latest-assistant class to the assistant message right after the latest user message
        // This gives it min-height to push the user message to the top of the viewport (ChatGPT style)
        const isLatestAssistant = latestAssistantAfterUserIndex !== null && 
                                  index === latestAssistantAfterUserIndex
        
        return (
          <div
            key={`message-${index}`}
            ref={isLatestUserMessage ? latestUserMessageRef : undefined}
            className={`message-wrapper ${turn.role} ${isLatestAssistant ? 'latest-assistant' : ''}`}
          >
            <div className="message-content">
              <div className="message-bubble">
                {turn.role === 'assistant' ? (
                  <>
                    {/* Show content if available, or tool calls/typing indicator if no content */}
                    {turn.content ? (
                      <>
                        <ReactMarkdown 
                          remarkPlugins={[remarkGfm]}
                          components={{
                            // eslint-disable-next-line @typescript-eslint/no-explicit-any
                            code: (props: any) => {
                              const { node, inline, className, children, ...restProps } = props
                              const match = /language-(\w+)/.exec(className || '')
                              const language = match ? match[1] : 'text'
                              const codeString = String(children).replace(/\n$/, '')
                              
                              if (!inline && codeString) {
                                // Block code with syntax highlighting and copy button
                                return (
                                  <div className="code-block-wrapper">
                                    <div className="code-block-header">
                                      <span className="code-block-language">{language}</span>
                                      <CodeCopyButton code={codeString} />
                                    </div>
                                    <SyntaxHighlighter
                                      language={language}
                                      style={oneDark}
                                      customStyle={{
                                        margin: 0,
                                        borderRadius: '0 0 8px 8px',
                                        background: '#1e293b',
                                      }}
                                      codeTagProps={{
                                        style: {
                                          fontFamily: '"Fira Code", "Cascadia Code", "Consolas", "Monaco", monospace',
                                          fontSize: '0.875rem',
                                          lineHeight: '1.7',
                                        }
                                      }}
                                    >
                                      {codeString}
                                    </SyntaxHighlighter>
                                  </div>
                                )
                              }
                              
                              // Inline code
                              return (
                                <code className="inline-code" {...restProps}>
                                  {children}
                                </code>
                              )
                            },
                            img: ({ node, ...props }) => (
                              <img 
                                {...props} 
                                style={{ 
                                  maxWidth: 'min(100%, 600px)', 
                                  height: 'auto', 
                                  width: 'auto', 
                                  objectFit: 'contain', 
                                  borderRadius: '8px', 
                                  margin: '0.5rem 0', 
                                  display: 'block' 
                                }} 
                              />
                            ),
                            p: ({ node, children, ...props }) => {
                              // Check if paragraph contains only an image
                              // In ReactMarkdown, images are rendered as img elements in children
                              if (node && typeof node === 'object' && 'children' in node) {
                                const nodeWithChildren = node as { children?: Array<{ tagName?: string }> }
                                if (nodeWithChildren.children && nodeWithChildren.children.length === 1) {
                                  const firstChild = nodeWithChildren.children[0]
                                  // Check if it's an image element by checking tagName property
                                  if (firstChild && firstChild.tagName === 'img') {
                                    return <p {...props} style={{ margin: 0 }}>{children}</p>
                                  }
                                }
                              }
                              return <p {...props}>{children}</p>
                            }
                          }}
                        >
                          {convertImageUrlsToMarkdown(turn.content)}
                        </ReactMarkdown>
                        
                        {/* Tool Calls Icons - show ALL tools (calling, completed, error) AFTER content, BEFORE actions */}
                        {/* Show all tools when message is complete (not loading), or show calling tools even while loading */}
                        {turn.toolCalls && turn.toolCalls.length > 0 && (() => {
                          // Show all tools: calling, completed, and error
                          // If still loading, show calling tools; if done, show all
                          const toolsToShow = (!isLastAssistantMessage || !loading) 
                            ? turn.toolCalls  // Show all when done
                            : turn.toolCalls.filter(tc => tc.status === 'calling')  // Show only calling while loading
                          
                          if (toolsToShow.length === 0) return null
                          
                          return (
                            <div className="tool-calls-icons">
                              {toolsToShow.map((toolCall, tcIndex) => {
                                // Get status-specific styling
                                const statusClass = toolCall.status === 'calling' ? 'calling' 
                                                  : toolCall.status === 'error' ? 'error' 
                                                  : 'completed'
                                
                                return (
                                  <button
                                    key={toolCall.id || `tool-icon-${index}-${tcIndex}`}
                                    className={`tool-call-icon-btn ${statusClass} ${selectedToolCall?.messageIndex === index && selectedToolCall?.toolCall.id === toolCall.id ? 'active' : ''}`}
                                    onClick={() => handleToolCallSelect(index, toolCall)}
                                    title={`${toolCall.name} (${toolCall.status || 'unknown'})`}
                                    type="button"
                                    disabled={toolCall.status === 'calling'}  // Disable click while calling
                                  >
                                    {toolCall.status === 'calling' ? (
                                      <div className="tool-call-spinner-small">
                                        <span></span>
                                        <span></span>
                                        <span></span>
                                      </div>
                                    ) : toolCall.status === 'error' ? (
                                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <circle cx="12" cy="12" r="10" />
                                        <line x1="12" y1="8" x2="12" y2="12" />
                                        <line x1="12" y1="16" x2="12.01" y2="16" />
                                      </svg>
                                    ) : (
                                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 1 .3.7v6.8a1 1 0 0 1-.3.7l-1.6 1.6a1 1 0 0 0 0 1.4 1 1 0 0 0 1.4 0l3-3a1 1 0 0 0 .3-.7V8a1 1 0 0 0-.3-.7l-3-3a1 1 0 0 0-1.4 1.4z" />
                                        <path d="M9.3 17.7a1 1 0 0 0 0-1.4l-1.6-1.6a1 1 0 0 1-.3-.7V8a1 1 0 0 1 .3-.7l1.6-1.6a1 1 0 0 0 0-1.4 1 1 0 0 0-1.4 0l-3 3A1 1 0 0 0 4 8v6.8a1 1 0 0 0 .3.7l3 3a1 1 0 0 0 1.4-1.4z" />
                                      </svg>
                                    )}
                                  </button>
                                )
                              })}
                            </div>
                          )
                        })()}
                        
                        {/* Only show action buttons when not streaming (loading=false or not the last assistant message) */}
                        <div className={`message-actions ${isLastAssistantMessage && !loading ? 'visible' : isLastAssistantMessage && loading ? 'hidden' : 'hidden-on-hover'}`}>
                        <button
                          className="message-action-btn copy-btn"
                          onClick={() => handleCopy(turn.content, index)}
                          title="Copy"
                        >
                          {copied ? (
                            <svg
                              width="18"
                              height="18"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            >
                              <polyline points="20 6 11 15 7 11" />
                            </svg>
                          ) : (
                            <svg
                              width="18"
                              height="18"
                              viewBox="0 0 24 24"
                              fill="none"
                              xmlns="http://www.w3.org/2000/svg"
                            >
                              <path
                                fill="currentColor"
                                fillRule="evenodd"
                                clipRule="evenodd"
                                d="M21 3.5V17a2 2 0 0 1-2 2h-2v-2h2V3.5H9v2h5.857c1.184 0 2.143.895 2.143 2v13c0 1.105-.96 2-2.143 2H5.143C3.959 22.5 3 21.605 3 20.5v-13c0-1.105.96-2 2.143-2H7v-2a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2m-6.143 4H5.143v13h9.714z"
                              />
                            </svg>
                          )}
                        </button>
                        {isLastAssistantMessage && onRegenerate && (
                          <button
                            className="message-action-btn regenerate-btn"
                            onClick={onRegenerate}
                            title="Regenerate"
                          >
                            <svg
                              width="18"
                              height="18"
                              viewBox="0 0 24 24"
                              fill="none"
                              stroke="currentColor"
                              strokeWidth="2"
                              strokeLinecap="round"
                              strokeLinejoin="round"
                            >
                              <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.2" />
                            </svg>
                          </button>
                        )}
                        <button
                          className={`message-action-btn thumbs-btn ${feedback === 'up' ? 'active' : ''}`}
                          onClick={() => handleFeedback('up', index)}
                          title="Thumbs up"
                        >
                          <svg
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                          >
                            <path
                              fill="currentColor"
                              fillRule="evenodd"
                              clipRule="evenodd"
                              d="M9 10.395V20.5h8.557a1 1 0 0 0 .98-.797l1.774-8.576A.937.937 0 0 0 19.393 10h-3.659a2.177 2.177 0 0 1-2.093-2.775L14.678 3.6a.736.736 0 0 0-1.342-.576zM7 11v9.5H5a1 1 0 0 1-1-1V12a1 1 0 0 1 1-1zM5 9a3 3 0 0 0-3 3v7.5a3 3 0 0 0 3 3h12.557a3 3 0 0 0 2.938-2.392l1.774-8.576A2.937 2.937 0 0 0 19.393 8h-3.659a.177.177 0 0 1-.17-.225l1.037-3.627a2.736 2.736 0 0 0-4.989-2.139L7.5 9z"
                            />
                          </svg>
                        </button>
                        <button
                          className={`message-action-btn thumbs-btn ${feedback === 'down' ? 'active' : ''}`}
                          onClick={() => handleFeedback('down', index)}
                          title="Thumbs down"
                        >
                          <svg
                            width="18"
                            height="18"
                            viewBox="0 0 24 24"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                          >
                            <path
                              fill="currentColor"
                              fillRule="evenodd"
                              clipRule="evenodd"
                              d="M15 13.605V3.5H6.443a1 1 0 0 0-.98.797L3.69 12.873A.937.937 0 0 0 4.607 14h3.659a2.177 2.177 0 0 1 2.093 2.775l-1.037 3.627a.736.736 0 0 0 1.342.575zM17 13V3.5h2a1 1 0 0 1 1 1V12a1 1 0 0 1-1 1zm2 2a3 3 0 0 0 3-3V4.5a3 3 0 0 0-3-3H6.443a3 3 0 0 0-2.938 2.392l-1.774 8.576A2.937 2.937 0 0 0 4.607 16h3.659c.117 0 .202.112.17.225l-1.037 3.627a2.736 2.736 0 0 0 4.989 2.139L16.5 15z"
                            />
                          </svg>
                        </button>
                      </div>
                      </>
                    ) : (
                      // No content yet - show typing indicator with tool call info if calling
                      <div className="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                        {turn.toolCalls && turn.toolCalls.length > 0 && turn.toolCalls.some(tc => tc.status === 'calling' || (!tc.status && !tc.result)) && (
                          <span className="typing-tool-call-text">
                            {turn.toolCalls
                              .filter(toolCall => toolCall.status === 'calling' || (!toolCall.status && !toolCall.result))
                              .map(toolCall => `正在调用工具: ${toolCall.name}`)
                              .join(', ')}
                          </span>
                        )}
                      </div>
                    )}
                    
                  </>
                ) : (
                  <div style={{ whiteSpace: 'pre-wrap' }}>{turn.content}</div>
                )}
              </div>
            </div>
          </div>
        )
      })}
      {(() => {
        // Only show separate typing indicator if there's no assistant message in history yet
        // Once assistant message exists in history, typing indicator will be shown there
        const lastTurn = history[history.length - 1]
        return loading && (!history.length || lastTurn?.role !== 'assistant')
      })() && (
        <div className="message-wrapper assistant">
          <div className="message-content">
            <div className="message-bubble typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        </div>
      )}
      
      {/* Tool Call Sidebar */}
      {selectedToolCall && (
        <ToolCallSidebar
          toolCall={selectedToolCall.toolCall}
          onClose={handleToolCallClose}
        />
      )}
    </div>
  )
}, (prevProps, nextProps) => {
  // Custom comparison function for memo
  return (
    prevProps.history.length === nextProps.history.length &&
    prevProps.loading === nextProps.loading &&
    prevProps.onRegenerate === nextProps.onRegenerate &&
    prevProps.latestUserMessageRef === nextProps.latestUserMessageRef
  )
})

