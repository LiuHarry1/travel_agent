/**
 * Chat title generation hook
 * Handles automatic title generation for new conversations
 */

import { useRef } from 'react'
import type { ChatResponse } from '../types'
import { generateTitle } from '../api'
import { DEFAULT_SESSION_TITLE } from '../constants'
import type { StoredChatSession } from './useChatSessions'

export interface UseChatTitleReturn {
  generateTitleAsync: (
    fullHistory: ChatResponse['history'],
    activeSession: StoredChatSession | null,
    updateActiveSession: (data: { title: string }) => void
  ) => Promise<void>
}

export function useChatTitle(): UseChatTitleReturn {
  const titleGenerationInProgress = useRef(false)

  const generateTitleAsync = async (
    fullHistory: ChatResponse['history'],
    activeSession: StoredChatSession | null,
    updateActiveSession: (data: { title: string }) => void
  ): Promise<void> => {
    // Early return if already in progress - prevent duplicate calls
    if (titleGenerationInProgress.current) {
      console.log('[Title Gen] Skipping: title generation already in progress')
      return
    }
    
    try {
      // Check if this is the first exchange (1 user + 1 assistant message)
      if (fullHistory.length !== 2) {
        console.log('[Title Gen] Skipping: not first exchange. Length:', fullHistory.length)
        return
      }
      
      // Double-check: ensure title hasn't been set already (re-check before API call)
      const currentTitle = activeSession?.title
      if (currentTitle && currentTitle !== DEFAULT_SESSION_TITLE) {
        console.log('[Title Gen] Skipping: title already set to:', currentTitle)
        return
      }
      
      console.log('[Title Gen] Starting title generation...')
      
      // Set flag immediately to prevent duplicate calls
      titleGenerationInProgress.current = true
      
      // Build messages for title generation
      const messages = fullHistory.map((turn) => ({
        role: turn.role,
        content: turn.content || '',
      }))
      
      console.log('[Title Gen] Messages for API:', messages)
      
      // Call API to generate title
      console.log('[Title Gen] Calling generateTitle API...')
      const title = await generateTitle(messages)
      
      console.log('[Title Gen] ✅ Received title from API:', title)
      
      // Final check: ensure title still hasn't been set by another call
      // This prevents race conditions
      const updatedSession = activeSession
      if (updatedSession?.title && updatedSession.title !== DEFAULT_SESSION_TITLE) {
        console.log('[Title Gen] Skipping update: title was set to', updatedSession.title, 'by another call')
        return
      }
      
      // Update session title
      if (title && title !== DEFAULT_SESSION_TITLE) {
        console.log('[Title Gen] ✅ Updating session title to:', title)
        updateActiveSession({ title })
      } else {
        console.log(`[Title Gen] ⚠️ Title was "${DEFAULT_SESSION_TITLE}", not updating`)
      }
    } catch (error) {
      console.error('[Title Gen] ❌ ERROR:', error)
      // Don't show error alert - title generation is not critical
    } finally {
      // Always reset the flag
      titleGenerationInProgress.current = false
    }
  }

  return {
    generateTitleAsync,
  }
}
