/**
 * Chat API endpoints
 * Handles streaming chat responses with improved SSE parsing and error recovery
 */

import type { ChatPayload, StreamEvent } from '../types'
import { getApiUrl } from './client'
import { SSE_EVENT_PREFIX } from '../constants'

interface StreamParser {
  buffer: string
  parseLine: (line: string) => StreamEvent | null
  reset: () => void
}

/**
 * Create a stream parser for SSE events
 */
function createStreamParser(): StreamParser {
  let buffer = ''

  const parseLine = (line: string): StreamEvent | null => {
    if (!line.startsWith(SSE_EVENT_PREFIX)) {
      return null
    }

    const data = line.slice(SSE_EVENT_PREFIX.length).trim()
    if (!data) {
      return null
    }

    // Handle special cases
    if (data === '[DONE]') {
      return { type: 'done' }
    }

    try {
      const parsed = JSON.parse(data) as StreamEvent
      return parsed
    } catch (error) {
      console.warn('Failed to parse SSE data:', data, error)
      return null
    }
  }

  const reset = () => {
    buffer = ''
  }

  return {
    get buffer() {
      return buffer
    },
    set buffer(value: string) {
      buffer = value
    },
    parseLine,
    reset,
  }
}

/**
 * Send chat message with streaming response
 * Improved error handling and recovery
 */
export async function sendChatMessageStream(
  payload: ChatPayload,
  onChunk: (chunk: string) => void,
  onDone: () => void,
  onError: (error: string) => void,
  onEvent?: (event: StreamEvent) => void,
  abortSignal?: AbortSignal
): Promise<void> {
  let response: Response | null = null
  let reader: ReadableStreamDefaultReader<Uint8Array> | null = null

  try {
    response = await fetch(getApiUrl('/agent/message/stream'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
      signal: abortSignal,
    })

    if (!response.ok) {
      const detail = await response.text()
      throw new Error(detail || `Request failed with status ${response.status}`)
    }

    if (!response.body) {
      throw new Error('Response body is null')
    }

    reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8', { fatal: false })
    const parser = createStreamParser()

    try {
      while (true) {
        const { done, value } = await reader.read()
        
        if (done) {
          // Check if there's remaining data in buffer
          if (parser.buffer.trim()) {
            const lines = parser.buffer.split('\n')
            for (const line of lines) {
              const event = parser.parseLine(line)
              if (event) {
                if (event.type === 'chunk' && event.content) {
                  onChunk(event.content)
                } else if (onEvent) {
                  onEvent(event)
                }
              }
            }
          }
          break
        }

        // Decode chunk (may contain incomplete UTF-8 sequences)
        parser.buffer += decoder.decode(value, { stream: true })
        
        // Process complete lines
        const lines = parser.buffer.split('\n')
        // Keep the last incomplete line in buffer
        parser.buffer = lines.pop() || ''

        for (const line of lines) {
          if (!line.trim()) continue

          const event = parser.parseLine(line)
          if (!event) continue

          try {
            if (event.type === 'chunk') {
              onChunk(event.content || '')
            } else if (event.type === 'done') {
              onDone()
              return
            } else if (event.type === 'error') {
              onError(event.content || event.error || 'Unknown error')
              return
            } else if (onEvent) {
              onEvent(event)
            }
          } catch (error) {
            console.error('Error handling stream event:', error, event)
            // Continue processing other events even if one fails
          }
        }
      }

      // If we exit the loop without 'done' event, call onDone
      onDone()
    } finally {
      if (reader) {
        reader.releaseLock()
      }
    }
  } catch (error) {
    // Handle abort errors silently
    if (error instanceof Error && error.name === 'AbortError') {
      return
    }

    // Handle network errors
    if (error instanceof TypeError && error.message.includes('fetch')) {
      onError('Network error. Please check your connection.')
      return
    }

    // Handle other errors
    const errorMessage = error instanceof Error ? error.message : 'Stream failed'
    onError(errorMessage)
    throw error
  }
}
