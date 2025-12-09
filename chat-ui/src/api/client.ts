/**
 * Base API client utilities
 */

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? 'http://localhost:8001'

export async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text()
    throw new Error(detail || `Request failed with status ${response.status}`)
  }
  return response.json() as Promise<T>
}

export function getApiUrl(path: string): string {
  return `${API_BASE_URL}${path}`
}

export { API_BASE_URL }

