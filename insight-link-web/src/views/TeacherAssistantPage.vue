<template>
  <div class="assistant-page">
    <AssistantWorkspace :current-material-id="materialId" :initial-conversation-id="conversationId" @conversation-change="rememberConversation" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AssistantWorkspace from '../features/assistant/AssistantWorkspace.vue'

const route = useRoute()
const router = useRouter()
const conversationId = computed(() => typeof route.query.conversationId === 'string' ? route.query.conversationId : '')

// URL 仅记录当前会话，刷新后可核实正在运行、已停止或可恢复的任务；权限仍由服务端校验。
function rememberConversation(id) {
  const query = { ...route.query }
  if (id) query.conversationId = id
  else delete query.conversationId
  void router.replace({ query })
}
// 从材料详情页进入时带上材料上下文；独立入口保持普通对话模式。
const materialId = computed(() => {
  const id = Number(route.query.materialId)
  return Number.isInteger(id) && id > 0 ? id : null
})
</script>

<style scoped>
.assistant-page {
  height: calc(100vh - 100px);
  min-height: 400px;
}
</style>
