<template>
  <el-button class="skills-entry" plain size="small" :disabled="disabled" @click="openDialog">技能</el-button>
  <el-dialog v-model="open" append-to-body top="4vh" title="助手技能" width="min(820px, calc(100vw - 32px))" class="skills-dialog" :close-on-click-modal="false" :before-close="beforeClose" @closed="resetEditor">
    <p class="skills-intro">技能用于保存可反复使用的处理步骤。启用的个人技能会在后续提问中按需使用；正式评价与留言仍需确认。</p>
    <el-alert v-if="versionConflict" class="skills-conflict" title="技能版本已变化，当前草稿仍保留。请先复制需要的内容，再刷新查看最新版本。" type="warning" :closable="false" />
    <div class="skills-toolbar">
      <span>系统内置 {{ builtinCount }} 项 · 我的技能 {{ personalCount }} 项</span>
      <div><el-button size="small" :disabled="busy || loading" @click="refresh">刷新</el-button><el-button size="small" type="primary" :disabled="busy" @click="newSkill">新增技能</el-button></div>
    </div>
    <div class="skills-layout">
      <aside v-loading="loading" class="skill-list" aria-label="技能列表">
        <p v-if="!items.length && !loading" class="skill-empty">还没有可用技能</p>
        <button v-for="item in items" :key="item.name" class="skill-item" :class="{ 'skill-item-active': selected?.name === item.name && !creating }" :disabled="busy" @click="showSkill(item)">
          <span class="skill-item-heading"><strong>{{ skillTitle(item) }}</strong><el-tag size="small" :type="item.builtin ? 'info' : item.enabled ? 'success' : 'warning'">{{ item.builtin ? '内置' : item.enabled ? '已启用' : '已停用' }}</el-tag></span>
          <span>{{ item.description }}</span>
        </button>
      </aside>
      <section v-loading="detailLoading" class="skill-detail" aria-label="技能内容">
        <template v-if="creating || selected">
          <div v-if="selected?.builtin && !creating" class="skill-readonly-note">系统内置技能为只读，可查看和导出。需要调整时，可复制内容后新增个人技能。</div>
          <el-form label-position="top" @submit.prevent="save">
            <el-form-item label="技能名称">
              <el-input v-model="draft.name" :disabled="!creating || busy" maxlength="64" placeholder="例如：学习材料对比分析" show-word-limit />
            </el-form-item>
            <el-form-item label="适用场景">
              <el-input v-model="draft.description" type="textarea" :rows="2" :readonly="readOnly" :disabled="busy" maxlength="300" show-word-limit placeholder="说明遇到什么任务时使用这项技能" />
            </el-form-item>
            <el-form-item label="技能步骤与输出要求">
              <el-input v-model="draft.instructions" type="textarea" :rows="12" :readonly="readOnly" :disabled="busy" maxlength="20000" show-word-limit placeholder="使用中文描述处理步骤、核对要求和输出格式" />
            </el-form-item>
          </el-form>
          <p v-if="selected && !creating" class="skill-version">{{ selected.builtin ? '系统内置' : `当前版本 ${selected.version}` }}<template v-if="selected.updated_at"> · {{ formatDate(selected.updated_at) }}</template></p>
          <div class="skill-actions">
            <template v-if="!creating"><el-button size="small" :disabled="busy" @click="downloadSkill">导出技能</el-button><template v-if="!selected.builtin"><el-button size="small" :disabled="busy" @click="toggle">{{ selected.enabled ? '停用' : '启用' }}</el-button><el-button size="small" type="danger" plain :disabled="busy" @click="remove">删除</el-button></template></template>
            <el-button v-if="!readOnly" size="small" type="primary" :loading="busy" :disabled="!validDraft" @click="save">{{ creating ? '创建并启用' : '保存新版本' }}</el-button>
          </div>
          <details v-if="!creating && !selected?.builtin && selected?.history?.length" class="skill-history">
            <summary>历史版本（{{ selected.history.length }}）</summary>
            <div v-for="version in selected.history" :key="version.version" class="skill-history-row"><span>版本 {{ version.version }}<template v-if="version.replaced_at || version.updated_at"> · {{ formatDate(version.replaced_at || version.updated_at) }}</template></span><el-button v-if="version.instructions" size="small" text :disabled="busy" @click="loadHistorical(version)">载入历史内容</el-button></div>
            <p>载入后仍需保存，会生成新版本，不会覆盖历史记录。</p>
          </details>
        </template>
        <div v-else class="skill-empty">选择一项技能查看内容，或新增自己的处理流程。</div>
      </section>
    </div>
    <template #footer><el-button :disabled="busy" @click="closeDialog">关闭</el-button></template>
  </el-dialog>
</template>

<script setup>
import { computed, onBeforeUnmount, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import agentHttp from '../../api/agentHttp'
import { requestErrorMessage } from '../../api/requestErrorMessage'
import { useAssistantSkills } from './useAssistantSkills'

defineProps({ disabled: Boolean })
const open = ref(false)
const busy = ref(false)
const creating = ref(false)
const versionConflict = ref(false)
const draft = ref({ name: '', description: '', instructions: '' })
const savedDraft = ref('')
const { items, selected, loading, detailLoading, loadSkills, selectSkill, saveSkill,
  toggleSkill, deleteSkill, exportSkill, clearSelection, disposeSkills } = useAssistantSkills(agentHttp)
const builtinCount = computed(() => items.value.filter(item => item.builtin).length)
const personalCount = computed(() => items.value.length - builtinCount.value)
const readOnly = computed(() => !creating.value && Boolean(selected.value?.builtin))
const validDraft = computed(() => draft.value.name.trim() && draft.value.description.trim() && draft.value.instructions.trim())
const dirty = computed(() => !readOnly.value && JSON.stringify(draft.value) !== savedDraft.value)

function snapshotDraft(value) {
  draft.value = { name: value ? skillTitle(value) : '', description: value?.description || '', instructions: value?.instructions || '' }
  savedDraft.value = JSON.stringify(draft.value)
  versionConflict.value = false
}

// 每次打开重新读取服务器状态，其他会话对技能的更新也会显示在这里。
async function openDialog() {
  open.value = true
  resetEditor()
  await refresh()
}

async function refresh() {
  if (busy.value || !await discardEdits()) return
  try {
    await loadSkills()
    if (selected.value) {
      const detail = await selectSkill(selected.value.name)
      if (detail) snapshotDraft(detail)
    }
  } catch (error) { showError(error) }
}

function resetEditor() {
  creating.value = false
  clearSelection()
  snapshotDraft(null)
}

async function discardEdits() {
  if (!dirty.value) return true
  try {
    await ElMessageBox.confirm('有尚未保存的技能内容，是否放弃本次修改？', '未保存的修改', {
      confirmButtonText: '放弃修改', cancelButtonText: '继续编辑', type: 'warning'
    })
    return true
  } catch { return false }
}

async function showSkill(item) {
  if (busy.value || !await discardEdits()) return
  creating.value = false
  try {
    const detail = await selectSkill(item.name)
    if (detail) snapshotDraft(detail)
  } catch (error) { showError(error) }
}

async function newSkill() {
  if (!await discardEdits()) return
  clearSelection()
  creating.value = true
  snapshotDraft({ instructions: '## 适用场景\n\n## 处理步骤\n1. 核对任务目标与可用资料。\n2. 根据实际数据处理。\n3. 检查结果。\n\n## 输出要求\n说明结论、依据和需要导师核对的事项。' })
}

async function save() {
  if (busy.value || !validDraft.value || readOnly.value) return
  busy.value = true
  try {
    await saveSkill(draft.value.name.trim(), draft.value, creating.value ? 0 : selected.value.version)
    creating.value = false
    snapshotDraft(selected.value)
    ElMessage.success('技能已保存，将在后续提问中按需使用')
  } catch (error) { showError(error) }
  finally { busy.value = false }
}

async function toggle() {
  if (busy.value || !selected.value || selected.value.builtin || !await discardEdits()) return
  busy.value = true
  try {
    await toggleSkill(selected.value, !selected.value.enabled)
    snapshotDraft(selected.value)
    ElMessage.success(selected.value.enabled ? '技能已启用' : '技能已停用')
  } catch (error) { showError(error) }
  finally { busy.value = false }
}

async function remove() {
  if (busy.value || !selected.value || selected.value.builtin) return
  try {
    await ElMessageBox.confirm(`删除“${selected.value.name}”后，助手将不再使用该个人技能。`, '删除技能', {
      confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
    })
    busy.value = true
    await deleteSkill(selected.value)
    resetEditor()
    ElMessage.success('个人技能已删除')
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') showError(error)
  } finally { busy.value = false }
}

// 导出走带 token 的文件请求与临时 Blob URL，令牌不进入下载地址。
async function downloadSkill() {
  if (!selected.value || busy.value) return
  try {
    const { data } = await exportSkill(selected.value)
    const url = URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href = url
    link.download = `${skillTitle(selected.value).replace(/[<>:"/\\|?*\u0000-\u001f]/g, '_')}.md`
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (error) { ElMessage.error(requestErrorMessage(error)) }
}

function loadHistorical(version) {
  draft.value.description = version.description || ''
  draft.value.instructions = version.instructions || ''
  ElMessage.info('已载入历史内容，请检查并保存为新版本')
}

function formatDate(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString('zh-CN', { hour12: false })
}

function skillTitle(item) { return item.display_name || item.name }

function showError(error) {
  if (error?.response?.status === 409) versionConflict.value = true
  ElMessage.error(requestErrorMessage(error))
}

async function beforeClose(done) {
  if (!busy.value && await discardEdits()) done()
}

function closeDialog() { beforeClose(() => { open.value = false }) }
onBeforeUnmount(disposeSkills)
</script>

<style scoped>
/* 弹窗挂到 body 后独立于导师布局，正文滚动而关闭按钮始终留在视口内。 */
:global(.skills-dialog) { max-height: 92vh; display: flex; flex-direction: column; }
:global(.skills-dialog .el-dialog__body) { overflow-y: auto; min-height: 0; }
:global(.skills-dialog .el-dialog__header), :global(.skills-dialog .el-dialog__footer) { flex-shrink: 0; }
.skills-entry { margin-left: 0; }
.skills-intro { margin: 0 0 16px; color: #718096; font-size: 12px; line-height: 1.7; }
.skills-conflict { margin-bottom: 14px; }
.skills-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 12px; color: #718096; font-size: 12px; }
.skills-layout { display: grid; grid-template-columns: 225px minmax(0, 1fr); gap: 18px; min-height: 420px; }
.skill-list { min-height: 80px; max-height: 570px; overflow-y: auto; border: 1px solid #e5eaf1; border-radius: 9px; background: #f8fafc; padding: 7px; }
.skill-item { display: grid; gap: 7px; width: 100%; margin-bottom: 6px; padding: 10px; border: 1px solid transparent; border-radius: 7px; background: transparent; text-align: left; cursor: pointer; }
.skill-item:hover { background: #edf3fa; }
.skill-item-active { background: #edf4ff; border-color: #c8ddfa; }
.skill-item-heading { display: flex; align-items: center; justify-content: space-between; gap: 6px; }
.skill-item-heading strong { color: #344861; font-size: 12px; overflow-wrap: anywhere; }
.skill-item > span:last-child { color: #8996a8; font-size: 11px; line-height: 1.55; }
.skill-detail { min-width: 0; }
.skill-detail :deep(.el-form-item) { margin-bottom: 14px; }
.skill-detail :deep(.el-form-item__label) { color: #53667e; font-size: 12px; }
.skill-detail :deep(.el-textarea__inner) { font-size: 12px; line-height: 1.7; }
.skill-empty { padding: 28px 12px; color: #94a0b0; text-align: center; font-size: 12px; }
.skill-readonly-note { margin-bottom: 12px; padding: 9px 11px; border-radius: 7px; background: #f0f6ff; color: #657f9c; font-size: 11px; line-height: 1.6; }
.skill-version { color: #91a0b3; font-size: 11px; }
.skill-actions { display: flex; justify-content: flex-end; flex-wrap: wrap; gap: 7px; }
.skill-actions :deep(.el-button + .el-button) { margin-left: 0; }
.skill-history { margin-top: 18px; padding-top: 12px; border-top: 1px solid #e9edf3; color: #7a8b9f; font-size: 11px; }
.skill-history summary { cursor: pointer; }
.skill-history-row { display: flex; justify-content: space-between; align-items: center; gap: 10px; margin-top: 6px; }
@media (max-width: 700px) { .skills-layout { grid-template-columns: minmax(0, 1fr); } .skill-list { max-height: 180px; } }
</style>
