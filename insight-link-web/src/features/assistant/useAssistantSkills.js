import { ref } from 'vue'

// 个人技能使用导师已登录的 API 客户端；界面只传中文名称和显式版本。
export function useAssistantSkills(client) {
  const items = ref([])
  const selected = ref(null)
  const loading = ref(false)
  const detailLoading = ref(false)
  let listVersion = 0
  let detailVersion = 0
  let disposed = false
  const path = name => `/api/chat/skills/${encodeURIComponent(name)}`

  async function loadSkills() {
    const version = ++listVersion
    loading.value = true
    try {
      const { data } = await client.get('/api/chat/skills')
      if (disposed || version !== listVersion) return
      items.value = Array.isArray(data.items) ? data.items : []
    } catch (error) {
      if (!disposed && version === listVersion) throw error
    } finally {
      if (!disposed && version === listVersion) loading.value = false
    }
  }

  async function selectSkill(name) {
    const version = ++detailVersion
    selected.value = null
    detailLoading.value = true
    try {
      const { data } = await client.get(path(name))
      if (disposed || version !== detailVersion) return null
      selected.value = data
      return data
    } catch (error) {
      if (!disposed && version === detailVersion) throw error
      return null
    } finally {
      if (!disposed && version === detailVersion) detailLoading.value = false
    }
  }

  // 每次编辑、启停和删除携带当前版本，其他窗口更新后由服务端拒绝覆盖。
  async function saveSkill(name, draft, expectedVersion = 0) {
    const { data } = await client.put(path(name), {
      description: draft.description.trim(), instructions: draft.instructions.trim(),
      expected_version: expectedVersion
    })
    await loadSkills()
    await selectSkill(data.name || name)
    return data
  }

  async function toggleSkill(item, enabled) {
    const { data } = await client.patch(path(item.name), { enabled, expected_version: item.version })
    await loadSkills()
    if (selected.value?.name === item.name) await selectSkill(item.name)
    return data
  }

  async function deleteSkill(item) {
    await client.delete(path(item.name), { params: { expected_version: item.version } })
    if (selected.value?.name === item.name) clearSelection()
    await loadSkills()
  }

  async function exportSkill(item) {
    return await client.get(`${path(item.name)}/export`, { responseType: 'blob' })
  }

  function clearSelection() {
    detailVersion += 1
    selected.value = null
    detailLoading.value = false
  }

  function disposeSkills() {
    disposed = true
    listVersion += 1
    clearSelection()
  }

  return { items, selected, loading, detailLoading, loadSkills, selectSkill,
    saveSkill, toggleSkill, deleteSkill, exportSkill, clearSelection, disposeSkills }
}
