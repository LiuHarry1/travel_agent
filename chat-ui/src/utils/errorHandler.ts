/**
 * Error handling utilities
 */

export interface ErrorInfo {
  message: string
  code?: string
  retryable?: boolean
}

/**
 * Handle and normalize errors into a consistent format
 * 
 * @param error - The error to handle (can be Error, string, or unknown)
 * @returns Normalized error information
 */
export function handleError(error: unknown): ErrorInfo {
  if (error instanceof Error) {
    // Network errors
    if (error.name === 'AbortError') {
      return { message: 'Request cancelled', code: 'ABORT', retryable: false }
    }
    
    // Timeout errors
    if (error.message.includes('timeout') || error.message.includes('Timeout')) {
      return { message: 'Request timeout', code: 'TIMEOUT', retryable: true }
    }
    
    // Network failures
    if (error.message.includes('Failed to fetch') || error.message.includes('NetworkError')) {
      return { message: 'Network error. Please check your connection.', code: 'NETWORK', retryable: true }
    }
    
    // Other errors
    return { message: error.message, retryable: true }
  }
  
  // String errors
  if (typeof error === 'string') {
    return { message: error, retryable: true }
  }
  
  // Unknown errors
  return { message: 'Unknown error occurred', retryable: true }
}

/**
 * Get user-friendly error message
 * 
 * @param error - The error to format
 * @returns User-friendly error message
 */
export function getErrorMessage(error: unknown): string {
  return handleError(error).message
}

/**
 * Check if an error is retryable
 * 
 * @param error - The error to check
 * @returns True if the error is retryable
 */
export function isRetryableError(error: unknown): boolean {
  return handleError(error).retryable ?? true
}
