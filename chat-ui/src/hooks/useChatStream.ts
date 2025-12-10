/**
 * Chat stream processing hook
 * Handles streaming chat responses from the API
 */

import { useRef } from 'react'
import type { ChatPayload, StreamEvent } from '../types'
import { sendChatMessageStream } from '../api'

export interface StreamCallbacks {
  onChunk: (chunk: string) => void
  onDone: () => void
  onError: (error: string) => void
  onEvent?: (event: StreamEvent) => void
}

export interface UseChatStreamReturn {
  startStream: (payload: ChatPayload, callbacks: StreamCallbacks) => Promise<void>
  stopStream: () => void
  abortController: React.MutableRefObject<AbortController | null>
}

export function useChatStream(): UseChatStreamReturn {
  const abortControllerRef = useRef<AbortController | null>(null)

  const startStream = async (payload: ChatPayload, callbacks: StreamCallbacks): Promise<void> => {
    // Create new abort controller for this request
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
      // Handle abort errors silently
      if (error instanceof Error && error.name === 'AbortError') {
        return
      }
      // Other errors are handled by onError callback
      if (error instanceof Error) {
        callbacks.onError(error.message)
      } else {
        callbacks.onError('Stream failed')
      }
    }
  }

  const stopStream = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
  }

  return {
    startStream,
    stopStream,
    abortController: abortControllerRef,
  }
}
