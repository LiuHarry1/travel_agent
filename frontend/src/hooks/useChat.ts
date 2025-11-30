import { useState, useEffect, useRef } from 'react'
import type { ChatResponse, Alert, ToolCall, StreamEvent, Suggestion } from '../types'
import { sendChatMessageStream } from '../api/index'
import { useChatSessions } from './useChatSessions'

export function useChat() {
  const { activeSession, updateActiveSession, createSession } = useChatSessions()
  const hasInitialized = useRef(false)
  const abortControllerRef = useRef<AbortController | null>(null)

  const [sessionId, setSessionId] = useState<string | undefined>(activeSession?.sessionId)
  const [message, setMessage] = useState('')
  const [history, setHistory] = useState<ChatResponse['history']>(activeSession?.history ?? [])
  const [suggestions, setSuggestions] = useState<Suggestion[] | undefined>(activeSession?.suggestions)
  const [loading, setLoading] = useState(false)
  const [alert, setAlert] = useState<Alert | null>(null)

  // Sync local state when active session changes
  useEffect(() => {
    if (!activeSession && !hasInitialized.current) {
      // Use setTimeout to defer state update until after render
      // This prevents the "Cannot update component while rendering" error
      hasInitialized.current = true
      setTimeout(() => {
        createSession()
      }, 0)
      return
    }
    
    if (activeSession) {
      hasInitialized.current = true
      setSessionId(activeSession.sessionId)
      // Only update history if it's actually different to avoid unnecessary re-renders
      setHistory((prev) => {
        // Compare by length and last message to avoid unnecessary updates
        if (prev.length !== activeSession.history.length) {
          return activeSession.history
        }
        // If lengths are same, check if last messages are different
        if (prev.length > 0 && activeSession.history.length > 0) {
          const prevLast = prev[prev.length - 1]
          const activeLast = activeSession.history[activeSession.history.length - 1]
          if (prevLast.content !== activeLast.content || 
              prevLast.toolCalls?.length !== activeLast.toolCalls?.length) {
            return activeSession.history
          }
          // Check if tool call statuses changed
          if (prevLast.toolCalls && activeLast.toolCalls) {
            const prevStatuses = prevLast.toolCalls.map(tc => `${tc.id}:${tc.status}`).join(',')
            const activeStatuses = activeLast.toolCalls.map(tc => `${tc.id}:${tc.status}`).join(',')
            if (prevStatuses !== activeStatuses) {
              return activeSession.history
            }
          }
          return prev // No change, return previous to avoid re-render
        }
        return activeSession.history
      })
      setSuggestions(activeSession.suggestions)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeSession])

  const sendMessage = async (text?: string, files?: Array<{ name: string; content: string }>) => {
    const messageText = text || message.trim()

    if (!messageText && (!files || files.length === 0)) {
      setAlert({ type: 'error', message: 'Please enter content to send or upload a file.' })
      return
    }

    // Validate file sizes (already validated in useFileUpload, but double-check)
    if (files && files.length > 0) {
      const oversizedFiles = files.filter((f) => {
        let size = new Blob([f.content]).size
        if (f.content.startsWith('[BINARY_FILE:')) {
          const base64Content = f.content.split(':')[2]?.split(']')[0] || ''
          size = Math.floor(base64Content.length * 0.75)
        }
        return size > 5 * 1024 * 1024
      })
      if (oversizedFiles.length > 0) {
        const fileNames = oversizedFiles.map((f) => f.name).join(', ')
        setAlert({
          type: 'error',
          message: `File too large (over 5MB): ${fileNames}. Please upload smaller files.`,
        })
        return
      }
    }

    setAlert(null)

    const userMessageContent =
      messageText || (files && files.length > 0 ? files.map((f) => `[文件: ${f.name}]`).join(', ') : '')

    const currentHistory: ChatResponse['history'] = userMessageContent
      ? [...history, { role: 'user' as const, content: messageText || userMessageContent }]
      : history

    if (userMessageContent) {
      setHistory(currentHistory)
      // Derive chat title from the first user message if not already set
      if (!activeSession?.title || activeSession.title === 'New chat' || activeSession.title === 'New conversation') {
        const rawTitle = (messageText || userMessageContent).replace(/\s+/g, ' ').trim()
        const newTitle = rawTitle.slice(0, 30) || 'New chat'
        updateActiveSession({ title: newTitle, history: currentHistory })
      } else {
        updateActiveSession({ history: currentHistory })
      }
    }

    setLoading(true)

    // Create abort controller for this request
    abortControllerRef.current = new AbortController()

    let assistantMessageIndex = -1
    if (userMessageContent) {
      const updatedHistory: ChatResponse['history'] = [...currentHistory, { role: 'assistant' as const, content: '', toolCalls: [] }]
      assistantMessageIndex = updatedHistory.length - 1
      setHistory(updatedHistory)
      updateActiveSession({ history: updatedHistory })
    }

    // Use a ref to track assistant message index so it can be updated in event handlers
    const assistantIndexRef = { current: assistantMessageIndex }

    try {
      // Filter out tool messages and tool_calls from history before sending to backend
      // Frontend keeps full history (including tool calls) for display, but backend only needs user/assistant messages
      const filteredHistory = currentHistory.map((turn) => {
        // Only include user and assistant messages, exclude tool messages
        if (turn.role === 'user' || turn.role === 'assistant') {
          return {
            role: turn.role as string,
            content: turn.content || '', // Ensure content is always a string
            // Explicitly exclude tool_calls from being sent to backend
          }
        }
        return null
      }).filter((msg): msg is { role: string; content: string } => msg !== null)

      const payload = {
        session_id: sessionId,
        message: messageText || undefined,
        files,
        messages: filteredHistory,
      }

      let accumulatedContent = ''
      let currentSessionId = sessionId || undefined
      const currentToolCalls = new Map<string, ToolCall>()

      await sendChatMessageStream(
        payload,
        (chunk: string) => {
          accumulatedContent += chunk
          setHistory((prev) => {
            const updated: ChatResponse['history'] = [...prev]
            let targetIndex = assistantIndexRef.current
            if (targetIndex >= 0 && targetIndex < updated.length) {
              // Update content and preserve tool calls
              const existingTurn = updated[targetIndex]
              updated[targetIndex] = {
                role: 'assistant' as const,
                content: accumulatedContent,
                toolCalls: existingTurn.toolCalls || Array.from(currentToolCalls.values()),
              }
            } else if (targetIndex < 0 && accumulatedContent) {
              updated.push({ 
                role: 'assistant' as const, 
                content: accumulatedContent,
                toolCalls: Array.from(currentToolCalls.values())
              })
              targetIndex = updated.length - 1
              assistantIndexRef.current = targetIndex
            }
            // Update session asynchronously to avoid triggering re-renders during render
            setTimeout(() => {
              updateActiveSession({ history: updated })
            }, 0)
            return updated
          })
        },
        () => {
          setLoading(false)
          abortControllerRef.current = null
          if (currentSessionId) {
            setSessionId(currentSessionId)
            updateActiveSession({ sessionId: currentSessionId })
          }
        },
        (error: string) => {
          setLoading(false)
          abortControllerRef.current = null
          if (userMessageContent) {
            setHistory(history)
            setMessage(messageText)
          }
          setAlert({ type: 'error', message: error })
        },
        (event: StreamEvent) => {
          // Handle tool call events
          const toolCallId = event.tool_call_id || event.tool
          if (!toolCallId) return

          const updateHistoryWithToolCalls = () => {
            setHistory((prev) => {
              const updated: ChatResponse['history'] = [...prev]
              let targetIndex = assistantIndexRef.current
              if (targetIndex < 0 || targetIndex >= updated.length) {
                updated.push({ 
                  role: 'assistant' as const, 
                  content: '',
                  toolCalls: Array.from(currentToolCalls.values())
                })
                targetIndex = updated.length - 1
                assistantIndexRef.current = targetIndex
              } else {
                const existingTurn = updated[targetIndex]
                updated[targetIndex] = {
                  ...existingTurn,
                  toolCalls: Array.from(currentToolCalls.values()),
                }
              }
              // Update session asynchronously to avoid triggering re-renders
              setTimeout(() => {
                updateActiveSession({ history: updated })
              }, 0)
              return updated
            })
          }

          if (event.type === 'tool_call_start' && event.tool) {
            // Check if this tool call already exists
            if (currentToolCalls.has(toolCallId)) {
              return
            }
            const toolCall: ToolCall = {
              id: toolCallId,
              name: event.tool,
              arguments: (event.input as Record<string, unknown>) || {},
              status: 'calling',
            }
            currentToolCalls.set(toolCallId, toolCall)
            updateHistoryWithToolCalls()
          } else if (event.type === 'tool_call_end' && event.tool) {
            const toolCall = currentToolCalls.get(toolCallId)
            if (toolCall) {
              toolCall.status = 'completed'
              toolCall.result = event.result
              currentToolCalls.set(toolCallId, toolCall)
              updateHistoryWithToolCalls()
            }
          } else if (event.type === 'tool_call_error' && event.tool) {
            const toolCall = currentToolCalls.get(toolCallId)
            if (toolCall) {
              toolCall.status = 'error'
              toolCall.error = event.error
              currentToolCalls.set(toolCallId, toolCall)
              updateHistoryWithToolCalls()
            }
          }
        },
        abortControllerRef.current.signal
      )

      // Final update: ensure tool calls are preserved in the final history
      if (accumulatedContent && currentToolCalls.size > 0) {
        setHistory((prev) => {
          const updated: ChatResponse['history'] = [...prev]
          let targetIndex = assistantIndexRef.current
          if (targetIndex >= 0 && targetIndex < updated.length) {
            const existingTurn = updated[targetIndex]
            updated[targetIndex] = {
              role: 'assistant' as const,
              content: accumulatedContent,
              toolCalls: existingTurn?.toolCalls || Array.from(currentToolCalls.values()),
            }
          }
          setTimeout(() => {
            updateActiveSession({ history: updated })
          }, 0)
          return updated
        })
      }
    } catch (error) {
      setLoading(false)
      abortControllerRef.current = null
      
      // Check if error is due to abort
      if (error instanceof Error && error.name === 'AbortError') {
        // Don't show error for user-initiated stop
        return
      }
      
      if (userMessageContent) {
        setHistory(history)
        setMessage(messageText)
      }
      const errorMessage = error instanceof Error ? error.message : 'Send failed'
      setAlert({ type: 'error', message: errorMessage })
    }
  }

  const stopGeneration = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
      setLoading(false)
    }
  }

  const regenerateResponse = async () => {
    // Find the last user message in history
    let lastUserMessageIndex = -1
    for (let i = history.length - 1; i >= 0; i--) {
      if (history[i].role === 'user') {
        lastUserMessageIndex = i
        break
      }
    }

    if (lastUserMessageIndex === -1) {
      setAlert({ type: 'error', message: 'No user message found to regenerate from' })
      return
    }

    const lastUserMessage = history[lastUserMessageIndex].content

    // Remove all messages after the last user message (including the old assistant response)
    const newHistory = history.slice(0, lastUserMessageIndex + 1)
    
    // Set the truncated history first
    setHistory(newHistory)
    updateActiveSession({ history: newHistory })

    setAlert(null)
    setLoading(true)

    // Create abort controller for this request
    abortControllerRef.current = new AbortController()

    // Add empty assistant message
    const updatedHistory: ChatResponse['history'] = [...newHistory, { role: 'assistant' as const, content: '', toolCalls: [] }]
    const assistantMessageIndex = updatedHistory.length - 1
    setHistory(updatedHistory)
    updateActiveSession({ history: updatedHistory })

    // Use a ref to track assistant message index
    const assistantIndexRef = { current: assistantMessageIndex }

    try {
      // Filter history for backend
      const filteredHistory = newHistory.map((turn) => {
        if (turn.role === 'user' || turn.role === 'assistant') {
          return {
            role: turn.role as string,
            content: turn.content || '',
          }
        }
        return null
      }).filter((msg): msg is { role: string; content: string } => msg !== null)

      const payload = {
        session_id: sessionId,
        message: lastUserMessage,
        messages: filteredHistory,
      }

      let accumulatedContent = ''
      let currentSessionId = sessionId || undefined
      const currentToolCalls = new Map<string, ToolCall>()

      await sendChatMessageStream(
        payload,
        (chunk: string) => {
          accumulatedContent += chunk
          setHistory((prev) => {
            const updated: ChatResponse['history'] = [...prev]
            let targetIndex = assistantIndexRef.current
            if (targetIndex >= 0 && targetIndex < updated.length) {
              const existingTurn = updated[targetIndex]
              updated[targetIndex] = {
                role: 'assistant' as const,
                content: accumulatedContent,
                toolCalls: existingTurn.toolCalls || Array.from(currentToolCalls.values()),
              }
            }
            setTimeout(() => {
              updateActiveSession({ history: updated })
            }, 0)
            return updated
          })
        },
        () => {
          setLoading(false)
          abortControllerRef.current = null
          if (currentSessionId) {
            setSessionId(currentSessionId)
            updateActiveSession({ sessionId: currentSessionId })
          }
        },
        (error: string) => {
          setLoading(false)
          abortControllerRef.current = null
          setAlert({ type: 'error', message: error })
        },
        (event: StreamEvent) => {
          const toolCallId = event.tool_call_id || event.tool
          if (!toolCallId) return

          const updateHistoryWithToolCalls = () => {
            setHistory((prev) => {
              const updated: ChatResponse['history'] = [...prev]
              let targetIndex = assistantIndexRef.current
              if (targetIndex >= 0 && targetIndex < updated.length) {
                const existingTurn = updated[targetIndex]
                updated[targetIndex] = {
                  ...existingTurn,
                  toolCalls: Array.from(currentToolCalls.values()),
                }
              }
              setTimeout(() => {
                updateActiveSession({ history: updated })
              }, 0)
              return updated
            })
          }

          if (event.type === 'tool_call_start' && event.tool) {
            if (currentToolCalls.has(toolCallId)) {
              return
            }
            const toolCall: ToolCall = {
              id: toolCallId,
              name: event.tool,
              arguments: (event.input as Record<string, unknown>) || {},
              status: 'calling',
            }
            currentToolCalls.set(toolCallId, toolCall)
            updateHistoryWithToolCalls()
          } else if (event.type === 'tool_call_end' && event.tool) {
            const toolCall = currentToolCalls.get(toolCallId)
            if (toolCall) {
              toolCall.status = 'completed'
              toolCall.result = event.result
              currentToolCalls.set(toolCallId, toolCall)
              updateHistoryWithToolCalls()
            }
          } else if (event.type === 'tool_call_error' && event.tool) {
            const toolCall = currentToolCalls.get(toolCallId)
            if (toolCall) {
              toolCall.status = 'error'
              toolCall.error = event.error
              currentToolCalls.set(toolCallId, toolCall)
              updateHistoryWithToolCalls()
            }
          }
        },
        abortControllerRef.current.signal
      )
    } catch (error) {
      setLoading(false)
      abortControllerRef.current = null
      
      if (error instanceof Error && error.name === 'AbortError') {
        return
      }
      
      const errorMessage = error instanceof Error ? error.message : 'Regenerate failed'
      setAlert({ type: 'error', message: errorMessage })
    }
  }

  return {
    sessionId,
    message,
    setMessage,
    history,
    suggestions,
    loading,
    alert,
    setAlert,
    sendMessage,
    stopGeneration,
    regenerateResponse,
  }
}

