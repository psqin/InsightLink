import axios from 'axios'
import { useAppStore } from '../store'
import router from '../router'
import { streamAssistantRequest } from './assistantStream'

const agentHttp = axios.create({
  baseURL: import.meta.env.VITE_AGENT_API_BASE || 'http://127.0.0.1:8001',
  timeout: 120000
})

// Agent 只接收当前登录导师的请求令牌，由服务端校验身份并转发到 Java 后端。
agentHttp.interceptors.request.use((config) => {
  const store = useAppStore()
  if (store.token) config.headers.token = store.token
  return config
})

agentHttp.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      useAppStore().clearAuth()
      router.push('/login')
    }
    return Promise.reject(error)
  }
)

export default agentHttp

// EventSource 不支持自定义 token 请求头，因此使用 POST fetch，禁止把令牌拼进 URL。
export async function streamAssistantMessage(payload, onEvent, signal) {
  return runAssistantStream('/api/chat/messages/stream', payload, onEvent, signal)
}

// 恢复只发送任务编号和已观察到的 attempt；原问题由服务端取回，使用当前令牌重新鉴权。
export async function resumeAssistantExecution(conversationId, executionId, onEvent, signal, attempt) {
  return runAssistantStream(`/api/chat/conversations/${conversationId}/execution/resume/stream`,
    { execution_id: executionId, attempt }, onEvent, signal)
}

function runAssistantStream(path, payload, onEvent, signal) {
  return streamAssistantRequest({
    baseURL: agentHttp.defaults.baseURL, path, payload, token: useAppStore().token, onEvent, signal,
    onUnauthorized: () => {
      useAppStore().clearAuth()
      router.push('/login')
    }
  })
}
