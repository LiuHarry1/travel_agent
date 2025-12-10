/**
 * Chat state management hook
 * Manages sessionId, message, history, loading, and alert state
 */

import { useState, useLayoutEffect, useRef } from 'react'
import type { ChatResponse, Alert, Suggestion } from '../types'
import { useChatSessions } from './useChatSessions'

export interface UseChatStateReturn {
  sessionId: string | undefined
  message: string
  setMessage: (message: string) => void
  history: ChatResponse['history']
  setHistory: (history: ChatResponse['history'] | ((prev: ChatResponse['history']) => ChatResponse['history'])) => void
  suggestions: Suggestion[] | undefined
  setSuggestions: (suggestions: Suggestion[] | undefined) => void
  loading: boolean
  setLoading: (loading: boolean) => void
  alert: Alert | null
  setAlert: (alert: Alert | null) => void
  updateActiveSession: ReturnType<typeof useChatSessions>['updateActiveSession']
}

export function useChatState(): UseChatStateReturn {
  const { activeSession, updateActiveSession, createSession } = useChatSessions()
  const hasInitialized = useRef(false)

  const [sessionId, setSessionId] = useState<string | undefined>(activeSession?.sessionId)
  const [message, setMessage] = useState('')
  const [history, setHistory] = useState<ChatResponse['history']>(activeSession?.history ?? [])
  const [suggestions, setSuggestions] = useState<Suggestion[] | undefined>(activeSession?.suggestions)
  const [loading, setLoading] = useState(false)
  const [alert, setAlert] = useState<Alert | null>(null)

  // Sync local state when active session changes
  // Use useLayoutEffect for synchronous updates to avoid render issues
  useLayoutEffect(() => {
    if (!activeSession && !hasInitialized.current) {
      hasInitialized.current = true
      createSession()
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
  }, [activeSession, createSession])

  return {
    sessionId,
    message,
    setMessage,
    history,
    setHistory,
    suggestions,
    setSuggestions,
    loading,
    setLoading,
    alert,
    setAlert,
    updateActiveSession,
  }
}
