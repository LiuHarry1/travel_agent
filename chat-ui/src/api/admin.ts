/**
 * Admin API endpoints
 */

import { handleResponse, getApiUrl } from './client'

export interface ProviderInfo {
  value: string
  label: string
}

export interface ProvidersResponse {
  providers: ProviderInfo[]
}

export interface LLMConfigResponse {
  provider: string
  model: string
  ollama_url?: string
  openai_base_url?: string
}

export interface OllamaModelInfo {
  name: string
  size?: number
  modified_at?: string
}

export interface ModelsResponse {
  provider: string
  models: string[]
  ollama_models?: OllamaModelInfo[]
}

export interface UpdateLLMConfigRequest {
  provider: string
  model: string
  ollama_url?: string
  openai_base_url?: string
}

export interface UpdateLLMConfigResponse {
  status: string
  message: string
  provider: string
  model: string
}

export async function getProviders(): Promise<ProvidersResponse> {
  const response = await fetch(getApiUrl('/api/admin/providers'), {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })
  return handleResponse<ProvidersResponse>(response)
}

export async function getLLMConfig(): Promise<LLMConfigResponse> {
  const response = await fetch(getApiUrl('/api/admin/config'), {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })
  return handleResponse<LLMConfigResponse>(response)
}

export async function getAvailableModels(
  provider?: string,
  ollamaUrl?: string
): Promise<ModelsResponse> {
  const params = new URLSearchParams()
  if (provider) params.append('provider', provider)
  if (ollamaUrl) params.append('ollama_url', ollamaUrl)
  
  const url = `${getApiUrl('/api/admin/models')}${params.toString() ? `?${params.toString()}` : ''}`
  const response = await fetch(url, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })
  return handleResponse<ModelsResponse>(response)
}

export async function updateLLMConfig(
  payload: UpdateLLMConfigRequest
): Promise<UpdateLLMConfigResponse> {
  const response = await fetch(getApiUrl('/api/admin/config'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  return handleResponse<UpdateLLMConfigResponse>(response)
}

// Function Calls API
export interface FunctionDefinition {
  name: string
  description: string
  type: 'local' | 'external_api'
  schema: object
  enabled: boolean
  config?: object
}

export interface FunctionCallsResponse {
  available_functions: FunctionDefinition[]
  enabled_functions: string[]
}

export interface FunctionCallsUpdateRequest {
  enabled_functions: string[]
  configs?: Record<string, object>
}

export async function getFunctionCalls(): Promise<FunctionCallsResponse> {
  const response = await fetch(getApiUrl('/api/admin/function-calls'), {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' }
  })
  return handleResponse<FunctionCallsResponse>(response)
}

export async function updateFunctionCalls(
  payload: FunctionCallsUpdateRequest
): Promise<{ status: string; message: string; enabled_functions: string[] }> {
  const response = await fetch(getApiUrl('/api/admin/function-calls'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  return handleResponse(response)
}

// System Prompt API
export interface SystemPromptResponse {
  prompt: string
  template: string
}

export interface SystemPromptUpdateRequest {
  prompt?: string
  template?: string
}

export async function getSystemPrompt(): Promise<SystemPromptResponse> {
  const response = await fetch(getApiUrl('/api/admin/system-prompt'), {
    method: 'GET',
    headers: { 'Content-Type': 'application/json' }
  })
  return handleResponse<SystemPromptResponse>(response)
}

export async function updateSystemPrompt(
  payload: SystemPromptUpdateRequest
): Promise<{ status: string; message: string; prompt: string }> {
  const response = await fetch(getApiUrl('/api/admin/system-prompt'), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  })
  return handleResponse(response)
}

