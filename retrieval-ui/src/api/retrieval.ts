import type { RetrievalResponse, DebugRetrievalResponse } from '../types'

// Use proxy in development, or direct URL if VITE_API_BASE_URL is set
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? '' : 'http://localhost:8003')

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed with status ${response.status}`)
  }
  return response.json() as Promise<T>
}

export async function search(query: string, pipelineName?: string): Promise<RetrievalResponse> {
  const body: any = { query }
  if (pipelineName) {
    body.pipeline_name = pipelineName
  }
  const response = await fetch(`${API_BASE_URL}/api/v1/retrieval/search`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
  return handleResponse<RetrievalResponse>(response)
}

export async function searchWithDebug(query: string, pipelineName?: string): Promise<DebugRetrievalResponse> {
  const body: any = { query }
  if (pipelineName) {
    body.pipeline_name = pipelineName
  }
  const response = await fetch(`${API_BASE_URL}/api/v1/retrieval/search/debug`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
  return handleResponse<DebugRetrievalResponse>(response)
}

