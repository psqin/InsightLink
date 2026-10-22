// 统一提取 Java 与 Agent 的错误信息，避免把 Axios 的英文网络错误直接显示给导师。
export function requestErrorMessage(error) {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string' && detail.trim()) return detail
  const message = error?.response?.data?.msg || error?.response?.data?.message
  if (typeof message === 'string' && message.trim()) return message
  if (error?.code === 'ERR_NETWORK') return '网络连接失败，请确认学业 AI 助手服务正在运行'
  if (error?.code === 'ECONNABORTED') return '请求超时，请稍后重试'
  return error?.message || '助手暂时不可用'
}
