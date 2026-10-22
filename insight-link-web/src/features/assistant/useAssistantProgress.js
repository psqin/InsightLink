import { ref } from 'vue'

// 只呈现服务端受控状态；原始工具参数、检索正文与模型推理不进入进度面板。
export function useAssistantProgress() {
  const progress = ref(null)
  const harness = ref(null)
  const progressError = ref(false)
  function resetProgress(saved = null) {
    progress.value = null
    harness.value = saved
    progressError.value = false
  }
  function handleProgress(event, data) {
    if (!['phase', 'plan', 'tool', 'subagent', 'review', 'interrupt'].includes(event)) return
    if (!progress.value) progress.value = { label: '正在准备', plan: [], planSteps: [], activities: [], review: null }
    if (event === 'phase') progress.value.label = data.label
    if (event === 'plan') {
      progress.value.plan = data.items || []
      progress.value.planSteps = data.steps || []
    }
    if (event === 'review') progress.value.review = data
    if (event === 'interrupt') progress.value.label = data.kind === 'input' ? '等待补充信息' : '等待确认操作'
    if (event === 'tool' || event === 'subagent') {
      const item = { id: data.id, label: data.label, status: data.status, kind: event }
      const index = progress.value.activities.findIndex((existing) => existing.id === item.id)
      if (index !== -1) progress.value.activities[index] = item
      else progress.value.activities.push(item)
      progress.value.activities = progress.value.activities.slice(-30)
    }
  }
  function completeProgress(result) {
    harness.value = result.harness || null
    if (progress.value) progress.value.label = result.pending_input ? '等待补充信息' : result.pending_action ? '等待确认操作' : '处理已结束'
  }
  return { progress, harness, progressError, resetProgress, handleProgress, completeProgress }
}
