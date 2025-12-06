import type { RetrievalResponse, DebugRetrievalResponse } from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed with status ${response.status}`)
  }
  return response.json() as Promise<T>
}

export async function search(query: string): Promise<RetrievalResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/retrieval/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query }),
  })
  return handleResponse<RetrievalResponse>(response)
}

export async function searchWithDebug(query: string): Promise<DebugRetrievalResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/retrieval/search/debug`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ query }),
  })
  return handleResponse<DebugRetrievalResponse>(response)
}

