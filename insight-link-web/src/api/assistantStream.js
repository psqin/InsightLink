import { consumeSSE } from './sse.js'

const STOPPED = new Set(['cancelled', 'interrupted', 'failed'])

/**
 * 消费一轮聊天或恢复请求。网络断开只代表停止接收，不代表服务端已经停止；
 * 只有 execution 终态才可作为取消成功的依据。依赖由调用方注入，便于验证弱网场景。
 */
export async function streamAssistantRequest({ baseURL, path, payload, token, onEvent,
  signal, onUnauthorized = () => {}, fetchImpl = fetch, idleTimeout = 60000 }) {
  const controller = new AbortController()
  const abort = () => controller.abort()
  signal?.addEventListener('abort', abort, { once: true })
  if (signal?.aborted) controller.abort()
  let result = null
  let execution = null
  let conversationId = payload.conversation_id
  let idleTimer
  const touch = () => {
    clearTimeout(idleTimer)
    idleTimer = setTimeout(abort, idleTimeout)
  }
  const asError = (status, data) => {
    if (status === 401) onUnauthorized()
    return Object.assign(new Error(data.detail || '助手暂时不可用'), { response: { status, data } })
  }
  const stoppedResult = () => execution && STOPPED.has(execution.status)
    ? { conversation_id: conversationId, execution, interrupted: true }
    : null
  try {
    touch()
    const response = await fetchImpl(`${baseURL.replace(/\/$/, '')}${path}`, {
      method: 'POST', headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream', token },
      body: JSON.stringify(payload), signal: controller.signal, cache: 'no-store'
    })
    if (!response.ok) throw asError(response.status, await response.json().catch(() => ({})))
    if (!response.headers.get('content-type')?.includes('text/event-stream')) throw new Error('助手返回格式异常')
    await consumeSSE(response.body, (event, data) => {
      touch()
      if (event === 'session') conversationId = data.conversation_id
      if (event === 'execution') execution = data.execution || data
      if (event === 'error') throw asError(data.status || 503, data)
      if (event === 'result') result = data
      onEvent(event, data)
    }, touch)
    if (!result && !stoppedResult()) throw new Error('连接已中断')
    return result || stoppedResult()
  } catch (error) {
    // 已持久化答复或取消终态即使最后一帧丢失仍有效，不能撤销原问题或伪造失败。
    if (result || stoppedResult()) return result || stoppedResult()
    if (!error.response) {
      throw asError(503, { detail: '连接已中断，正在核实服务端任务状态。请勿重复发送原问题。',
        conversation_id: conversationId, retryable: Boolean(conversationId) })
    }
    throw error
  } finally {
    clearTimeout(idleTimer)
    signal?.removeEventListener('abort', abort)
  }
}
