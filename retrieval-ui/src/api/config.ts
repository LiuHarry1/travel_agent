// Use proxy in development, or direct URL if VITE_API_BASE_URL is set
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || (import.meta.env.DEV ? '' : 'http://localhost:8003')

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



