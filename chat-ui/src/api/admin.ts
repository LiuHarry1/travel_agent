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

// MCP Config API
export interface MCPConfigResponse {
  config: {
    mcpServers: Record<string, unknown>
  }
  server_count: number
  tool_count: number
}

export interface MCPConfigUpdateRequest {
  config: {
    mcpServers: Record<string, unknown>
  }
}

export interface MCPConfigUpdateResponse {
  status: string
  message: string
  server_count: number
}

export async function getMCPConfig(): Promise<MCPConfigResponse> {
  const response = await fetch(getApiUrl('/api/admin/mcp-config'), {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })
  return handleResponse<MCPConfigResponse>(response)
}

export async function updateMCPConfig(
  payload: MCPConfigUpdateRequest
): Promise<MCPConfigUpdateResponse> {
  const response = await fetch(getApiUrl('/api/admin/mcp-config'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  return handleResponse<MCPConfigUpdateResponse>(response)
}

