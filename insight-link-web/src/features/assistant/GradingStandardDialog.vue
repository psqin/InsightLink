<template>
  <el-button text :disabled="disabled" @click="open">评分标准</el-button>
  <el-dialog v-model="visible" append-to-body title="我的 AI 评分标准" width="min(620px, 92vw)" :close-on-click-modal="!saving" :show-close="!saving" :close-on-press-escape="!saving">
    <div v-loading="loading" class="grading-settings">
      <div class="grading-current"><el-tag :type="standard?.source === 'custom' ? 'primary' : 'info'">{{ standard?.source === 'custom' ? '使用导师自定义标准' : '使用系统默认标准' }}</el-tag><span>仅对当前导师生效，长期保存</span></div>
      <p>未设置时，AI 按材料类型使用下方默认标准。你的自定义标准对所有材料类型生效，也可在正文中分类型说明。新生成的建议采用当前标准，可随时修改或恢复默认。</p>
      <label class="grading-label" for="teacher-grading-content">自定义评分标准</label>
      <el-input id="teacher-grading-content" v-model="content" type="textarea" :rows="7" maxlength="4000" show-word-limit :disabled="saving || loading" placeholder="例如：完成情况与证据 50 分、分析与反思 30 分、后续改进 20 分。说明每项怎样评判。" />
      <p class="grading-note">请使用 100 分制说明评分维度、权重及要求。标准用于 AI 建议，材料证据要求和导师确认流程仍然生效。不要填写学生隐私或密码。</p>
      <el-alert v-if="error" :title="error" type="warning" :closable="false" />
      <details><summary>查看系统默认标准</summary><div v-for="item in standard?.defaults || []" :key="item.material_type" class="grading-default"><strong>{{ item.label }}</strong><p>{{ item.content }}</p></div></details>
    </div>
    <template #footer>
      <div class="grading-footer"><el-button :disabled="loading || saving || standard?.source !== 'custom'" @click="save('reset')">恢复默认</el-button><span /><el-button :disabled="saving" @click="visible = false">关闭</el-button><el-button type="primary" :loading="saving" :disabled="loading || !standard || !content.trim()" @click="save('save')">保存标准</el-button></div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import agentHttp from '../../api/agentHttp'
import { requestErrorMessage } from '../../api/requestErrorMessage'
defineProps({ disabled: Boolean })
const visible = ref(false), loading = ref(false), saving = ref(false)
const standard = ref(null), content = ref(''), error = ref('')

// 每次打开重新读取，确保聊天中修改的最新标准能立即显示。
async function open() {
  visible.value = true
  loading.value = true
  error.value = ''
  standard.value = null
  content.value = ''
  try {
    const { data } = await agentHttp.get('/api/grading-standard')
    standard.value = data
    content.value = data.content || ''
  } catch (cause) { error.value = requestErrorMessage(cause) }
  finally { loading.value = false }
}

// 版本冲突时保留正在编辑的文本，只刷新服务端版本，避免静默覆盖。
async function save(action) {
  if (!standard.value || saving.value) return
  saving.value = true
  error.value = ''
  try {
    const { data } = await agentHttp.post('/api/grading-standard', {
      action, expected_version: standard.value.version, ...(action === 'save' ? { content: content.value.trim() } : {})
    })
    standard.value = data
    content.value = data.content || ''
    ElMessage.success(action === 'reset' ? '已恢复系统默认评分标准' : '评分标准已长期保存')
  } catch (cause) {
    error.value = requestErrorMessage(cause)
    if (cause.response?.status === 409) {
      try { standard.value = (await agentHttp.get('/api/grading-standard')).data }
      catch { /* 保留原编辑内容和冲突说明，不能假装保存成功。 */ }
    }
  } finally { saving.value = false }
}
</script>

<style scoped>
.grading-settings { display: grid; gap: 12px; max-height: 62vh; overflow-y: auto; padding-right: 4px; color: #53657c; font-size: 13px; }
.grading-settings p { margin: 0; line-height: 1.8; }
.grading-current { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; }
.grading-current > span:last-child, .grading-note { color: #8b98a8; font-size: 12px; }
.grading-label { color: #334155; font-weight: 600; }
summary { color: #4776a9; cursor: pointer; }
.grading-default { display: grid; gap: 5px; padding: 12px 0; border-bottom: 1px solid #edf0f4; }
.grading-default p { white-space: pre-wrap; }
.grading-footer { display: flex; align-items: center; gap: 8px; }
.grading-footer > span { flex: 1; }
</style>
