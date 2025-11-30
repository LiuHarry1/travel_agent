/**
 * Title generation API
 */

import { getApiUrl } from './client'

export interface GenerateTitleRequest {
  messages: Array<{
    role: string
    content: string
  }>
}

export interface GenerateTitleResponse {
  title: string
}

/**
 * Generate a conversation title using AI
 */
export async function generateTitle(
  messages: Array<{ role: string; content: string }>
): Promise<string> {
  const response = await fetch(getApiUrl('/agent/generate-title'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ messages }),
  })

  if (!response.ok) {
    throw new Error(`Failed to generate title: ${response.statusText}`)
  }

  const data: GenerateTitleResponse = await response.json()
  return data.title
}


