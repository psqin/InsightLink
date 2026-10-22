import { onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import agentHttp from '../../api/agentHttp'
import { requestErrorMessage } from '../../api/requestErrorMessage'
import { messageArtifacts } from './assistantContent'

// 附件预览 URL 属于当前会话；切换会话时撤销它们并使未完成的请求失效。
export function useAssistantArtifacts() {
  const artifactPreviews = ref({})
  const loadingIds = new Set()
  let generation = 0

  function clearArtifactPreviews() {
    generation += 1
    Object.values(artifactPreviews.value).forEach(url => URL.revokeObjectURL(url))
    artifactPreviews.value = {}
    loadingIds.clear()
  }

  // 同一附件只请求一次；旧会话的晚到响应立即释放，不能写回新会话。
  async function loadArtifactPreviews(items) {
    const currentGeneration = generation
    const charts = [...new Map(items.flatMap(item => messageArtifacts(item.content))
      .filter(item => item.name.endsWith('.png'))
      .map(item => [item.id, item])).values()]
      .filter(item => !artifactPreviews.value[item.id] && !loadingIds.has(item.id))
    await Promise.all(charts.map(async artifact => {
      loadingIds.add(artifact.id)
      try {
        const { data } = await agentHttp.get(`/api/chat/artifacts/${artifact.id}`, { responseType: 'blob' })
        const url = URL.createObjectURL(data)
        if (currentGeneration !== generation || artifactPreviews.value[artifact.id]) URL.revokeObjectURL(url)
        else artifactPreviews.value[artifact.id] = url
      } catch { /* 附件过期时保留文字回答，下载按钮仍可提示具体错误。 */ }
      finally {
        if (currentGeneration === generation) loadingIds.delete(artifact.id)
      }
    }))
  }

  // 下载使用一次性的对象 URL；不把文件内容或凭据暴露给聊天模型。
  async function downloadArtifact(artifact) {
    try {
      const { data } = await agentHttp.get(`/api/chat/artifacts/${artifact.id}`, { responseType: 'blob' })
      const url = URL.createObjectURL(data)
      const link = document.createElement('a')
      link.href = url
      link.download = artifact.name
      link.click()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (error) {
      ElMessage.error(requestErrorMessage(error))
    }
  }

  onUnmounted(clearArtifactPreviews)
  return { artifactPreviews, clearArtifactPreviews, loadArtifactPreviews, downloadArtifact }
}
