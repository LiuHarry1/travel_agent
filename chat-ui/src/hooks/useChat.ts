/**
 * Main chat hook
 * Combines state management, streaming, tool calls, and title generation
 */

import type { ChatResponse } from '../types'
import { useChatState } from './useChatState'
import { useChatStream } from './useChatStream'
import { useChatToolCalls } from './useChatToolCalls'
import { useChatTitle } from './useChatTitle'
import { useChatSessions } from './useChatSessions'
import { getErrorMessage } from '../utils/errorHandler'
import { MAX_FILE_SIZE } from '../constants'
import { DEFAULT_SESSION_TITLE } from '../constants'

export function useChat() {
  const {
    sessionId,
    message,
    setMessage,
    history,
    setHistory,
    suggestions,
    loading,
    setLoading,
    alert,
    setAlert,
    updateActiveSession,
  } = useChatState()

  const { startStream, stopStream, abortController } = useChatStream()
  const toolCallManager = useChatToolCalls()
  const { generateTitleAsync } = useChatTitle()
  const { activeSession } = useChatSessions()

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
        return size > MAX_FILE_SIZE
      })
      if (oversizedFiles.length > 0) {
        const fileNames = oversizedFiles.map((f) => f.name).join(', ')
        setAlert({
          type: 'error',
          message: `File too large (over ${MAX_FILE_SIZE / (1024 * 1024)}MB): ${fileNames}. Please upload smaller files.`,
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
      updateActiveSession({ history: currentHistory })
    }

    setLoading(true)

    let assistantMessageIndex = -1
    if (userMessageContent) {
      const updatedHistory: ChatResponse['history'] = [...currentHistory, { role: 'assistant' as const, content: '', toolCalls: [] }]
      assistantMessageIndex = updatedHistory.length - 1
      setHistory(updatedHistory)
      updateActiveSession({ history: updatedHistory })
    }

    // Use a ref to track assistant message index so it can be updated in event handlers
    const assistantIndexRef = { current: assistantMessageIndex }
    toolCallManager.clear()

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

      const updateHistoryWithContent = (content: string) => {
        setHistory((prev) => {
          const updated: ChatResponse['history'] = [...prev]
          let targetIndex = assistantIndexRef.current
          if (targetIndex >= 0 && targetIndex < updated.length) {
            // Update content and preserve tool calls
            const existingTurn = updated[targetIndex]
            updated[targetIndex] = {
              role: 'assistant' as const,
              content,
              toolCalls: existingTurn.toolCalls || toolCallManager.getToolCallsArray(),
            }
          } else if (targetIndex < 0 && content) {
            updated.push({ 
              role: 'assistant' as const, 
              content,
              toolCalls: toolCallManager.getToolCallsArray()
            })
            targetIndex = updated.length - 1
            assistantIndexRef.current = targetIndex
          }
          // Update session asynchronously to avoid triggering re-renders during render
          queueMicrotask(() => {
            updateActiveSession({ history: updated })
          })
          return updated
        })
      }

      await startStream(
        payload,
        {
          onChunk: (chunk: string) => {
            accumulatedContent += chunk
            updateHistoryWithContent(accumulatedContent)
          },
          onDone: () => {
            setLoading(false)
            abortController.current = null
            if (currentSessionId) {
              updateActiveSession({ sessionId: currentSessionId })
            }
            
            // Auto-generate title for new conversations (first user+assistant exchange)
            // Only generate once per session, and only if this is the first exchange
            // Check: we have 1 user message, and we just got the first assistant response
            if (currentHistory.length === 1 && 
                accumulatedContent &&
                (!activeSession?.title || activeSession.title === DEFAULT_SESSION_TITLE)) {
              // Build the complete conversation history (user + assistant)
              const fullHistory: ChatResponse['history'] = [
                ...currentHistory,
                { role: 'assistant' as const, content: accumulatedContent, toolCalls: [] }
              ]
              
              // Generate title asynchronously
              generateTitleAsync(fullHistory, activeSession, updateActiveSession)
            }
          },
          onError: (error: string) => {
            setLoading(false)
            abortController.current = null
            if (userMessageContent) {
              setHistory(history)
              setMessage(messageText)
            }
            setAlert({ type: 'error', message: error })
          },
          onEvent: (event) => {
            toolCallManager.handleStreamEvent(event, assistantIndexRef, (updater) => {
              setHistory((prev) => {
                const updated = updater(prev)
                queueMicrotask(() => {
                  updateActiveSession({ history: updated })
                })
                return updated
              })
            })
          },
        }
      )

      // Final update: ensure tool calls are preserved in the final history
      if (accumulatedContent && toolCallManager.getToolCallsArray().length > 0) {
        setHistory((prev) => {
          const updated: ChatResponse['history'] = [...prev]
          let targetIndex = assistantIndexRef.current
          if (targetIndex >= 0 && targetIndex < updated.length) {
            const existingTurn = updated[targetIndex]
            updated[targetIndex] = {
              role: 'assistant' as const,
              content: accumulatedContent,
              toolCalls: existingTurn?.toolCalls || toolCallManager.getToolCallsArray(),
            }
          }
          queueMicrotask(() => {
            updateActiveSession({ history: updated })
          })
          return updated
        })
      }
    } catch (error) {
      setLoading(false)
      abortController.current = null
      
      // Check if error is due to abort
      if (error instanceof Error && error.name === 'AbortError') {
        // Don't show error for user-initiated stop
        return
      }
      
      if (userMessageContent) {
        setHistory(history)
        setMessage(messageText)
      }
      const errorMessage = getErrorMessage(error) || 'Send failed'
      setAlert({ type: 'error', message: errorMessage })
    }
  }

  const stopGeneration = () => {
    stopStream()
    setLoading(false)
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

    // Add empty assistant message
    const updatedHistory: ChatResponse['history'] = [...newHistory, { role: 'assistant' as const, content: '', toolCalls: [] }]
    const assistantMessageIndex = updatedHistory.length - 1
    setHistory(updatedHistory)
    updateActiveSession({ history: updatedHistory })

    // Use a ref to track assistant message index
    const assistantIndexRef = { current: assistantMessageIndex }
    toolCallManager.clear()

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

      const updateHistoryWithContent = (content: string) => {
        setHistory((prev) => {
          const updated: ChatResponse['history'] = [...prev]
          let targetIndex = assistantIndexRef.current
          if (targetIndex >= 0 && targetIndex < updated.length) {
            const existingTurn = updated[targetIndex]
            updated[targetIndex] = {
              role: 'assistant' as const,
              content,
              toolCalls: existingTurn.toolCalls || toolCallManager.getToolCallsArray(),
            }
          }
          queueMicrotask(() => {
            updateActiveSession({ history: updated })
          })
          return updated
        })
      }

      await startStream(
        payload,
        {
          onChunk: (chunk: string) => {
            accumulatedContent += chunk
            updateHistoryWithContent(accumulatedContent)
          },
          onDone: () => {
            setLoading(false)
            abortController.current = null
            if (currentSessionId) {
              updateActiveSession({ sessionId: currentSessionId })
            }
          },
          onError: (error: string) => {
            setLoading(false)
            abortController.current = null
            setAlert({ type: 'error', message: error })
          },
          onEvent: (event) => {
            toolCallManager.handleStreamEvent(event, assistantIndexRef, (updater) => {
              setHistory((prev) => {
                const updated = updater(prev)
                queueMicrotask(() => {
                  updateActiveSession({ history: updated })
                })
                return updated
              })
            })
          },
        }
      )
    } catch (error) {
      setLoading(false)
      abortController.current = null
      
      if (error instanceof Error && error.name === 'AbortError') {
        return
      }
      
      const errorMessage = getErrorMessage(error) || 'Regenerate failed'
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
