import { API_BASE_URL } from './apiConfig'

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed with status ${response.status}`)
  }
  return response.json() as Promise<T>
}

export interface PipelineList {
  default: string | null
  pipelines: string[]
}

export interface PipelineConfig {
  pipeline_name: string
  yaml: string
}

export interface ParsedPipelineConfig {
  embedding_models?: string[] | string | object
  milvus?: {
    collection?: string
    [key: string]: any
  }
  rerank?: {
    api_url?: string
    [key: string]: any
  }
  retrieval?: {
    top_k_per_model?: number
    rerank_top_k?: number
    final_top_k?: number
    [key: string]: any
  }
  chunk_sizes?: {
    initial_search?: number
    rerank_input?: number
    llm_filter_input?: number
    [key: string]: any
  }
  llm_filter?: {
    model?: string
    [key: string]: any
  }
  [key: string]: any
}

export interface ValidationResult {
  valid: boolean
  errors: Record<string, any>
}

export async function getPipelines(): Promise<PipelineList> {
  const url = `${API_BASE_URL}/api/v1/config/pipelines`
  console.log('Fetching pipelines from:', url)
  const response = await fetch(url, {
    method: 'GET',
  })
  console.log('Response status:', response.status, response.statusText)
  if (!response.ok) {
    const errorText = await response.text()
    console.error('API error:', errorText)
    throw new Error(errorText || `Request failed with status ${response.status}`)
  }
  return handleResponse<PipelineList>(response)
}

export async function getPipeline(pipelineName: string): Promise<PipelineConfig> {
  const response = await fetch(`${API_BASE_URL}/api/v1/config/pipelines/${encodeURIComponent(pipelineName)}`, {
    method: 'GET',
  })
  return handleResponse<PipelineConfig>(response)
}

export async function createPipeline(pipelineName: string, yaml: string): Promise<PipelineConfig> {
  const response = await fetch(`${API_BASE_URL}/api/v1/config/pipelines`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ pipeline_name: pipelineName, yaml }),
  })
  return handleResponse<PipelineConfig>(response)
}

export async function updatePipeline(pipelineName: string, yaml: string): Promise<PipelineConfig> {
  const response = await fetch(`${API_BASE_URL}/api/v1/config/pipelines/${encodeURIComponent(pipelineName)}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ yaml }),
  })
  return handleResponse<PipelineConfig>(response)
}

export async function deletePipeline(pipelineName: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/config/pipelines/${encodeURIComponent(pipelineName)}`, {
    method: 'DELETE',
  })
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed with status ${response.status}`)
  }
}

export async function validatePipeline(pipelineName: string, yaml?: string): Promise<ValidationResult> {
  const body: any = {}
  if (yaml) {
    body.yaml = yaml
  }
  const response = await fetch(`${API_BASE_URL}/api/v1/config/pipelines/${encodeURIComponent(pipelineName)}/validate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
  return handleResponse<ValidationResult>(response)
}

export async function setDefaultPipeline(pipelineName: string): Promise<{ default: string }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/config/default`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ pipeline_name: pipelineName }),
  })
  return handleResponse<{ default: string }>(response)
}



