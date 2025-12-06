/**
 * Configuration API endpoints
 */

import type { ChecklistItem } from '../types'
import { handleResponse, getApiUrl } from './client'

export interface ConfigResponse {
  system_prompt_template: string
  checklist?: ChecklistItem[]
}

export async function getDefaultConfig(): Promise<ConfigResponse> {
  const response = await fetch(getApiUrl('/config'), {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  })
  return handleResponse<ConfigResponse>(response)
}

export interface SaveConfigPayload {
  system_prompt_template: string
  checklist?: ChecklistItem[]
}

export interface SaveConfigResponse {
  status: string
  message: string
}

export async function saveConfig(payload: SaveConfigPayload): Promise<SaveConfigResponse> {
  const response = await fetch(getApiUrl('/config'), {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  })
  return handleResponse<SaveConfigResponse>(response)
}

