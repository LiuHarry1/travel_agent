/**
 * Chat tool calls management hook
 * Handles tool call events during streaming
 */

import { useRef } from 'react'
import type { ToolCall, StreamEvent, ChatResponse } from '../types'

export interface ToolCallManager {
  toolCalls: Map<string, ToolCall>
  handleStreamEvent: (event: StreamEvent, assistantIndexRef: { current: number }, updateHistory: (updater: (prev: ChatResponse['history']) => ChatResponse['history']) => void) => void
  getToolCallsArray: () => ToolCall[]
  clear: () => void
}

export function useChatToolCalls(): ToolCallManager {
  const toolCallsRef = useRef<Map<string, ToolCall>>(new Map())

  const handleStreamEvent = (
    event: StreamEvent,
    assistantIndexRef: { current: number },
    updateHistory: (updater: (prev: ChatResponse['history']) => ChatResponse['history']) => void
  ) => {
    const toolCallId = event.tool_call_id || event.tool
    if (!toolCallId) return

    const updateHistoryWithToolCalls = () => {
      updateHistory((prev) => {
        const updated: ChatResponse['history'] = [...prev]
        let targetIndex = assistantIndexRef.current
        if (targetIndex < 0 || targetIndex >= updated.length) {
          updated.push({ 
            role: 'assistant' as const, 
            content: '',
            toolCalls: Array.from(toolCallsRef.current.values())
          })
          targetIndex = updated.length - 1
          assistantIndexRef.current = targetIndex
        } else {
          const existingTurn = updated[targetIndex]
          updated[targetIndex] = {
            ...existingTurn,
            toolCalls: Array.from(toolCallsRef.current.values()),
          }
        }
        return updated
      })
    }

    if (event.type === 'tool_call_start' && event.tool) {
      // Check if this tool call already exists
      if (toolCallsRef.current.has(toolCallId)) {
        return
      }
      const toolCall: ToolCall = {
        id: toolCallId,
        name: event.tool,
        arguments: (event.input as Record<string, unknown>) || {},
        status: 'calling',
      }
      toolCallsRef.current.set(toolCallId, toolCall)
      updateHistoryWithToolCalls()
    } else if (event.type === 'tool_call_end' && event.tool) {
      const toolCall = toolCallsRef.current.get(toolCallId)
      if (toolCall) {
        toolCall.status = 'completed'
        toolCall.result = event.result
        toolCallsRef.current.set(toolCallId, toolCall)
        updateHistoryWithToolCalls()
      }
    } else if (event.type === 'tool_call_error' && event.tool) {
      const toolCall = toolCallsRef.current.get(toolCallId)
      if (toolCall) {
        toolCall.status = 'error'
        toolCall.error = event.error
        toolCallsRef.current.set(toolCallId, toolCall)
        updateHistoryWithToolCalls()
      }
    }
  }

  const getToolCallsArray = (): ToolCall[] => {
    return Array.from(toolCallsRef.current.values())
  }

  const clear = () => {
    toolCallsRef.current.clear()
  }

  return {
    toolCalls: toolCallsRef.current,
    handleStreamEvent,
    getToolCallsArray,
    clear,
  }
}
