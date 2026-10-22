import { computed, ref } from 'vue'

const ACTIVE = new Set(['running', 'cancel_requested', 'committing'])
const RESUMABLE = new Set(['cancelled', 'interrupted', 'failed'])
const TERMINAL = new Set([...RESUMABLE, 'completed'])
const ACTIVE_ORDER = { running: 0, cancel_requested: 1, committing: 2 }

/**
 * 会话执行状态与网络连接分开管理：关闭 SSE 不能证明任务已经停止。
 * 服务端状态是唯一依据；每次切换会话、开始新任务或恢复都会递增 generation，
 * 防止旧轮询、旧停止响应及旧 SSE 事件覆盖新一轮任务。
 */
export function useAssistantExecution(client, {
  onTerminal = () => {}, onError = () => {}, pollInterval = 1500,
  setTimer = setTimeout, clearTimer = clearTimeout
} = {}) {
  const execution = ref(null)
  const cancelBusy = ref(false)
  const stateUncertain = ref(false)
  const active = computed(() => ACTIVE.has(execution.value?.status))
  const canCancel = computed(() => Boolean(execution.value?.id)
    && execution.value.status === 'running' && !cancelBusy.value)
  const canResume = computed(() => Boolean(execution.value?.id)
    && RESUMABLE.has(execution.value.status) && execution.value.can_resume === true)
  const statusLabel = computed(() => {
    if (stateUncertain.value) return '连接中断，任务状态待核实'
    if (cancelBusy.value) return '正在请求停止，请稍候'
    return ({ running: '正在处理', cancel_requested: '正在停止，等待当前操作退出',
      committing: '正在保存结果，请稍候', cancelled: '本轮任务已停止',
      interrupted: '本轮任务已中断', failed: '本轮任务未完成', completed: '本轮处理完成' })[execution.value?.status] || ''
  })
  let conversationId = ''
  let generation = 0
  let pollTimer = null
  let disposed = false

  function stopPolling() {
    if (pollTimer !== null) clearTimer(pollTimer)
    pollTimer = null
  }

  function schedulePoll() {
    stopPolling()
    if (!disposed && conversationId && (active.value || stateUncertain.value)) {
      pollTimer = setTimer(() => { pollTimer = null; void refreshExecution() }, pollInterval)
    }
  }

  // 同一个任务终态不能被迟到的 running/cancel_requested 回包倒退；attempt 支持原 ID 恢复。
  function applyExecution(value, { notify = true, replaceCurrent = false } = {}) {
    if (!value || !value.id) return
    let previous = execution.value
    if (previous?.id && previous.id !== value.id) {
      if (!replaceCurrent) return
      // 当前会话的最新查询可能发现另一窗口已经开始新任务；只允许状态查询切换 ID。
      previous = null
    }
    if (previous && Number(value.attempt || 0) < Number(previous.attempt || 0)) return
    if (previous && Number(value.attempt || 0) === Number(previous.attempt || 0)
      && TERMINAL.has(previous.status) && ACTIVE.has(value.status)) return
    if (previous && Number(value.attempt || 0) === Number(previous.attempt || 0)
      && ACTIVE_ORDER[value.status] < ACTIVE_ORDER[previous.status]) return
    const wasActive = ACTIVE.has(previous?.status)
    execution.value = { ...value }
    stateUncertain.value = false
    schedulePoll()
    if (notify && wasActive && TERMINAL.has(value.status)) {
      void onTerminal({ conversationId, execution: execution.value })
    }
  }

  /** 历史加载和刷新只观察状态，不自动重发问题或自动恢复任务。 */
  function observeConversation(id, value = null) {
    if (disposed) return generation
    generation += 1
    stopPolling()
    conversationId = id || ''
    execution.value = value ? { ...value } : null
    cancelBusy.value = false
    stateUncertain.value = false
    schedulePoll()
    return generation
  }

  /** 开始/恢复先解除旧任务绑定，收到 session 后再锁定本轮 execution_id。 */
  function beginExecution(id = '') {
    return observeConversation(id)
  }

  function handleEvent(event, data, expectedGeneration = generation) {
    if (disposed || expectedGeneration !== generation) return
    if (event === 'session') {
      conversationId = data.conversation_id || conversationId
      if (data.execution_id) execution.value = {
        id: data.execution_id, status: 'running', attempt: data.attempt || 0, can_resume: false
      }
      schedulePoll()
    } else if (event === 'execution') applyExecution(data.execution || data)
  }

  async function refreshExecution() {
    if (disposed || !conversationId) return null
    const version = generation
    const target = conversationId
    try {
      const { data } = await client.get(`/api/chat/conversations/${target}/execution`)
      if (disposed || version !== generation) return null
      if (data.execution) applyExecution(data.execution, { replaceCurrent: true })
      else { stateUncertain.value = false; stopPolling() }
      return data.execution || null
    } catch (error) {
      if (disposed || version !== generation) return null
      // 鉴权失败由统一 HTTP 拦截器处理，不持续轮询过期令牌。
      stateUncertain.value = true
      if (error.response?.status !== 401 && error.response?.status !== 404) schedulePoll()
      return null
    }
  }

  /** 请求停止后继续接收事件和轮询；请求丢失时先核实，绝不乐观展示“已停止”。 */
  async function cancelExecution() {
    if (disposed || !canCancel.value || !conversationId) return false
    const version = generation
    const target = conversationId
    const executionId = execution.value.id
    const attempt = execution.value.attempt
    cancelBusy.value = true
    try {
      const { data } = await client.post(`/api/chat/conversations/${target}/execution/cancel`,
        { execution_id: executionId, attempt })
      if (disposed || version !== generation) return false
      applyExecution(data.execution)
      return true
    } catch (error) {
      if (disposed || version !== generation) return false
      stateUncertain.value = true
      // 409 也必须读回状态：可能刚好已完成或进入保存阶段，不等同停止成功。
      await refreshExecution()
      if (!disposed && version === generation) onError(error)
      return false
    } finally {
      if (!disposed && version === generation) { cancelBusy.value = false; schedulePoll() }
    }
  }

  function connectionLost() {
    if (disposed || !conversationId) return
    stateUncertain.value = true
    void refreshExecution()
  }

  function disposeExecution() {
    disposed = true
    generation += 1
    stopPolling()
  }

  return { execution, active, canCancel, canResume, cancelBusy, stateUncertain, statusLabel,
    observeConversation, beginExecution, handleEvent, refreshExecution, cancelExecution,
    connectionLost, disposeExecution }
}
