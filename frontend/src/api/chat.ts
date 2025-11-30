/**
 * Chat API endpoints
 */

import type { ChatPayload, StreamEvent } from '../types'
import { getApiUrl } from './client'

export async function sendChatMessageStream(
  payload: ChatPayload,
  onChunk: (chunk: string) => void,
  onDone: () => void,
  onError: (error: string) => void,
  onEvent?: (event: StreamEvent) => void,
  abortSignal?: AbortSignal
): Promise<void> {
  const response = await fetch(getApiUrl('/agent/message/stream'), {
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

  const reader = response.body?.getReader()
  const decoder = new TextDecoder()

  if (!reader) {
    throw new Error('Failed to get response reader')
  }

  let buffer = ''

  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || '' // Keep incomplete line in buffer

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6) // Remove 'data: ' prefix
          try {
            const parsed = JSON.parse(data) as StreamEvent
            if (parsed.type === 'chunk') {
              onChunk(parsed.content || '')
            } else if (parsed.type === 'done') {
              onDone()
              return
            } else if (parsed.type === 'error') {
              onError(parsed.content || parsed.error || 'Unknown error')
              return
            } else if (onEvent) {
              onEvent(parsed)
            }
          } catch (e) {
            // Skip invalid JSON lines
            console.warn('Failed to parse SSE data:', data, e)
          }
        }
      }
    }
  } finally {
    reader.releaseLock()
  }
}

