/**
 * Unified API Client
 * Provides centralized error handling, retry logic, and timeout control
 */

import { DEFAULT_API_BASE_URL } from '../constants'
import { handleError } from '../utils/errorHandler'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? DEFAULT_API_BASE_URL

export interface RequestConfig extends RequestInit {
  timeout?: number
  retries?: number
  retryDelay?: number
}

class ApiClient {
  private baseURL: string

  constructor(baseURL: string) {
    this.baseURL = baseURL
  }

  /**
   * Make a request with error handling, retry logic, and timeout
   */
  async request<T>(path: string, config: RequestConfig = {}): Promise<T> {
    const { 
      timeout = 30000, 
      retries = 0, 
      retryDelay = 1000,
      ...fetchConfig 
    } = config
    
    const controller = new AbortController()
    const timeoutId = timeout ? setTimeout(() => controller.abort(), timeout) : null
    
    try {
      const response = await fetch(`${this.baseURL}${path}`, {
        ...fetchConfig,
        signal: controller.signal,
      })
      
      if (timeoutId) clearTimeout(timeoutId)
      
      if (!response.ok) {
        const detail = await response.text()
        const error = new Error(detail || `Request failed with status ${response.status}`)
        // Add status code to error for better error handling
        ;(error as any).status = response.status
        throw error
      }
      
      return await response.json() as T
    } catch (error) {
      if (timeoutId) clearTimeout(timeoutId)
      
      const errorInfo = handleError(error)
      
      // Retry logic with exponential backoff
      if (errorInfo.retryable && retries > 0) {
        const delay = retryDelay * Math.pow(2, retries - config.retries!)
        await new Promise(resolve => setTimeout(resolve, delay))
        return this.request<T>(path, { ...config, retries: retries - 1 })
      }
      
      throw error
    }
  }

  /**
   * GET request
   */
  async get<T>(path: string, config?: RequestConfig): Promise<T> {
    return this.request<T>(path, { ...config, method: 'GET' })
  }

  /**
   * POST request
   */
  async post<T>(path: string, data?: unknown, config?: RequestConfig): Promise<T> {
    return this.request<T>(path, {
      ...config,
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...config?.headers,
      },
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  /**
   * PUT request
   */
  async put<T>(path: string, data?: unknown, config?: RequestConfig): Promise<T> {
    return this.request<T>(path, {
      ...config,
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        ...config?.headers,
      },
      body: data ? JSON.stringify(data) : undefined,
    })
  }

  /**
   * DELETE request
   */
  async delete<T>(path: string, config?: RequestConfig): Promise<T> {
    return this.request<T>(path, { ...config, method: 'DELETE' })
  }
}

export const apiClient = new ApiClient(API_BASE_URL)

/**
 * Get full API URL for a path
 */
export function getApiUrl(path: string): string {
  return `${API_BASE_URL}${path}`
}

/**
 * Legacy response handler (kept for backward compatibility)
 */
export async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed with status ${response.status}`)
  }
  return response.json() as Promise<T>
}

export { API_BASE_URL }
