/**
 * API 工具函数
 */

/**
 * 处理 API 响应错误
 * 兼容 FastAPI 的 {detail: ...} 和旧版的 {error: ...} 格式
 */
export const getErrorMessage = (errorData: any): string => {
  if (typeof errorData === 'string') {
    return errorData
  }
  // FastAPI 格式
  if (errorData.detail) {
    return errorData.detail
  }
  // 旧版 Quart 格式
  if (errorData.error) {
    return errorData.error
  }
  return '未知错误'
}

/**
 * 通用的 fetch 包装器，提供统一的错误处理
 */
export const apiFetch = async (url: string, options?: RequestInit) => {
  const response = await fetch(url, options)

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`
    try {
      const errorData = await response.json()
      errorMessage = getErrorMessage(errorData)
    } catch {
      // 如果无法解析 JSON，使用默认错误消息
    }
    throw new Error(errorMessage)
  }

  return response
}
