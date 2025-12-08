/**
 * 错误处理工具
 * 统一处理应用中的错误
 */

/**
 * 从错误对象中提取用户友好的错误消息
 * @param error - 错误对象（可能是 Error、字符串或其他类型）
 * @returns 用户友好的错误消息
 */
export function getErrorMessage(error: unknown): string {
  if (error instanceof Error) {
    return error.message
  }
  if (typeof error === 'string') {
    return error
  }
  return 'An unexpected error occurred'
}

/**
 * 记录错误到控制台（开发环境）
 * @param context - 错误上下文描述
 * @param error - 错误对象
 */
export function logError(context: string, error: unknown): void {
  if (import.meta.env.DEV) {
    console.error(`[${context}]`, error)
  }
}

/**
 * 处理 API 错误
 * @param context - 错误上下文
 * @param error - 错误对象
 * @returns 用户友好的错误消息
 */
export function handleApiError(context: string, error: unknown): string {
  logError(context, error)
  return getErrorMessage(error)
}

