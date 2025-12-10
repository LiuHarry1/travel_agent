/**
 * API 配置模块
 * 统一管理后端 API 的基础 URL
 * 
 * 配置优先级：
 * 1. VITE_API_BASE_URL 环境变量（如果设置）
 * 2. 开发模式下使用空字符串（通过 Vite proxy 代理）
 * 3. 生产模式下如果没有设置环境变量，使用默认值
 */

function getApiBaseUrl(): string {
  // 如果设置了 VITE_API_BASE_URL，直接使用
  if (import.meta.env.VITE_API_BASE_URL) {
    return import.meta.env.VITE_API_BASE_URL
  }

  // 开发模式下，使用空字符串（通过 Vite proxy 代理到后端）
  if (import.meta.env.DEV) {
    return ''
  }

  // 生产模式下，如果没有设置环境变量，返回空字符串（使用相对路径）
  // 这样可以确保在生产环境中使用与前端相同的域名
  return ''
}

export const API_BASE_URL = getApiBaseUrl()

// 导出用于调试
if (import.meta.env.DEV) {
  console.log('API Base URL:', API_BASE_URL || '(using proxy)')
}

