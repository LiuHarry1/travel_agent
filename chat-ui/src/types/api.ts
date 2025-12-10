/**
 * API type definitions
 * Centralized types for all API requests and responses
 */

/**
 * Generic API response wrapper
 */
export interface ApiResponse<T> {
  data: T
  error?: ApiError
}

/**
 * API error structure
 */
export interface ApiError {
  code: string
  message: string
  details?: unknown
}

/**
 * HTTP status codes
 */
export type HttpStatusCode = 
  | 200 | 201 | 204
  | 400 | 401 | 403 | 404 | 409 | 422
  | 500 | 502 | 503 | 504

/**
 * Request configuration
 */
export interface RequestConfig {
  timeout?: number
  retries?: number
  retryDelay?: number
  headers?: Record<string, string>
  signal?: AbortSignal
}

/**
 * Pagination parameters
 */
export interface PaginationParams {
  page?: number
  pageSize?: number
  limit?: number
  offset?: number
}

/**
 * Paginated response
 */
export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  hasMore: boolean
}
