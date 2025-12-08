/**
 * API 工具函数
 * 统一处理 API 请求和响应
 */

/**
 * 处理 API 响应
 * @param response - Fetch API 响应对象
 * @returns 解析后的 JSON 数据
 * @throws 如果响应不成功，抛出错误
 */
export async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed with status ${response.status}`)
  }
  return response.json() as Promise<T>
}

/**
 * 创建 API 请求配置
 * @param method - HTTP 方法
 * @param body - 请求体（可选）
 * @returns Fetch API 配置对象
 */
export function createRequestConfig(method: string, body?: unknown): RequestInit {
  const config: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
    },
  }

  if (body !== undefined) {
    config.body = JSON.stringify(body)
  }

  return config
}

