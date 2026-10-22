import { ref } from 'vue'

// 历史记录在服务端搜索和分页；请求版本号保证旧结果不能覆盖新搜索。
export function useAssistantHistory(client, onError = () => {}) {
  const conversations = ref([])
  const keyword = ref('')
  const page = ref(1)
  const pageSize = 20
  const total = ref(0)
  const historyLoading = ref(false)
  let generation = 0
  let disposed = false

  async function loadConversations(requestedPage = page.value) {
    if (disposed) return
    const version = ++generation
    historyLoading.value = true
    try {
      const { data } = await client.get('/api/chat/conversations', { params: {
        page: requestedPage, page_size: pageSize, keyword: keyword.value.trim()
      } })
      if (disposed || version !== generation) return
      const count = Math.max(0, Number(data.total) || 0)
      const lastPage = Math.max(1, Math.ceil(count / pageSize))
      // 删除某页最后一条记录或其他窗口同步删除后，返回仍存在的最后一页。
      if (requestedPage > lastPage) return await loadConversations(lastPage)
      conversations.value = Array.isArray(data.items) ? data.items : []
      total.value = count
      page.value = requestedPage
    } catch (error) {
      if (!disposed && version === generation) onError(error)
    } finally {
      if (!disposed && version === generation) historyLoading.value = false
    }
  }

  function disposeHistory() {
    disposed = true
    generation += 1
  }

  return { conversations, keyword, page, pageSize, total, historyLoading,
    loadConversations, disposeHistory }
}
