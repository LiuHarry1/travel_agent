import type { RetrievalResponse, DebugRetrievalResponse } from '../types'
import { API_BASE_URL } from './apiConfig'
import { handleResponse, createRequestConfig } from '../utils/api'

export async function search(query: string, pipelineName?: string): Promise<RetrievalResponse> {
  const body: { query: string; pipeline_name?: string } = { query }
  if (pipelineName) {
    body.pipeline_name = pipelineName
  }
  const response = await fetch(
    `${API_BASE_URL}/api/v1/retrieval/search`,
    createRequestConfig('POST', body)
  )
  return handleResponse<RetrievalResponse>(response)
}

export async function searchWithDebug(
  query: string,
  pipelineName?: string
): Promise<DebugRetrievalResponse> {
  const body: { query: string; pipeline_name?: string } = { query }
  if (pipelineName) {
    body.pipeline_name = pipelineName
  }
  const response = await fetch(
    `${API_BASE_URL}/api/v1/retrieval/search/debug`,
    createRequestConfig('POST', body)
  )
  return handleResponse<DebugRetrievalResponse>(response)
}

