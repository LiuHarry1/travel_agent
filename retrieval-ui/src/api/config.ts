import { API_BASE_URL } from './apiConfig'
import { handleResponse, createRequestConfig } from '../utils/api'

export interface PipelineList {
  default: string | null
  pipelines: string[]
}

export interface PipelineConfig {
  pipeline_name: string
  yaml: string
}

export interface MilvusConfig {
  host?: string
  port?: number
  user?: string
  password?: string
  database?: string
  collection?: string
  [key: string]: unknown
}

export interface RerankConfig {
  api_url?: string
  model?: string
  timeout?: number
  [key: string]: unknown
}

export interface RetrievalConfig {
  top_k_per_model?: number
  rerank_top_k?: number
  final_top_k?: number
  [key: string]: unknown
}

export interface ChunkSizesConfig {
  initial_search?: number
  rerank_input?: number
  llm_filter_input?: number
  [key: string]: unknown
}

export interface LLMFilterConfig {
  api_key?: string
  base_url?: string
  model?: string
  [key: string]: unknown
}

export interface ParsedPipelineConfig {
  embedding_models?: string[] | string | Record<string, unknown>
  milvus?: MilvusConfig
  rerank?: RerankConfig
  retrieval?: RetrievalConfig
  chunk_sizes?: ChunkSizesConfig
  llm_filter?: LLMFilterConfig
  [key: string]: unknown
}

export interface ValidationResult {
  valid: boolean
  errors: Record<string, unknown>
}

export async function getPipelines(): Promise<PipelineList> {
  const url = `${API_BASE_URL}/api/v1/config/pipelines`
  if (import.meta.env.DEV) {
    console.log('Fetching pipelines from:', url)
  }
  const response = await fetch(url, createRequestConfig('GET'))
  if (import.meta.env.DEV) {
    console.log('Response status:', response.status, response.statusText)
  }
  return handleResponse<PipelineList>(response)
}

export async function getPipeline(pipelineName: string): Promise<PipelineConfig> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/config/pipelines/${encodeURIComponent(pipelineName)}`,
    createRequestConfig('GET')
  )
  return handleResponse<PipelineConfig>(response)
}

export async function createPipeline(
  pipelineName: string,
  yaml: string
): Promise<PipelineConfig> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/config/pipelines`,
    createRequestConfig('POST', { pipeline_name: pipelineName, yaml })
  )
  return handleResponse<PipelineConfig>(response)
}

export async function updatePipeline(
  pipelineName: string,
  yaml: string
): Promise<PipelineConfig> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/config/pipelines/${encodeURIComponent(pipelineName)}`,
    createRequestConfig('PUT', { yaml })
  )
  return handleResponse<PipelineConfig>(response)
}

export async function deletePipeline(pipelineName: string): Promise<void> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/config/pipelines/${encodeURIComponent(pipelineName)}`,
    createRequestConfig('DELETE')
  )
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed with status ${response.status}`)
  }
}

export async function validatePipeline(
  pipelineName: string,
  yaml?: string
): Promise<ValidationResult> {
  const body: { yaml?: string } = {}
  if (yaml) {
    body.yaml = yaml
  }
  const response = await fetch(
    `${API_BASE_URL}/api/v1/config/pipelines/${encodeURIComponent(pipelineName)}/validate`,
    createRequestConfig('POST', body)
  )
  return handleResponse<ValidationResult>(response)
}

export async function setDefaultPipeline(
  pipelineName: string
): Promise<{ default: string }> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/config/default`,
    createRequestConfig('PUT', { pipeline_name: pipelineName })
  )
  return handleResponse<{ default: string }>(response)
}



