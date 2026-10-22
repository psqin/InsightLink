<template>
  <section class="assistant-workspace" aria-label="学业 AI 助手">
    <button v-if="historyOpen" class="history-backdrop" aria-label="关闭对话记录" @click="historyOpen = false" />
    <aside class="history-rail" :class="{ 'history-rail-open': historyOpen }" aria-label="对话记录">
      <div class="rail-top">
        <div class="rail-heading"><span class="brand-mark">✦</span><span>学业 AI 助手</span></div>
        <button class="new-chat" :disabled="historyBusy" @click="startNew">
          <el-icon><Plus /></el-icon>
          <span>新对话</span>
        </button>
      </div>
      <form class="history-search" role="search" @submit.prevent="loadConversations(1)">
        <el-input v-model="historyKeyword" clearable maxlength="100" size="small" placeholder="搜索对话标题" aria-label="搜索对话标题" @clear="loadConversations(1)" />
        <button type="submit" :disabled="historyLoading" aria-label="搜索历史对话"><el-icon><Search /></el-icon></button>
      </form>
      <div class="history-label">{{ historyKeyword.trim() ? '搜索结果' : '最近对话' }}<span v-if="historyTotal"> · {{ historyTotal }}</span></div>
      <div class="history-list">
        <div v-if="historyLoading" class="history-empty">正在加载对话...</div>
        <div v-else-if="!conversations.length" class="history-empty">{{ historyKeyword.trim() ? '没有找到匹配的对话' : '还没有对话记录' }}</div>
        <div
          v-for="conversation in conversations"
          :key="conversation.id"
          class="history-row"
          :class="{ 'history-item-active': selectedId === conversation.id }"
        >
          <button class="history-item" :title="conversationTitle(conversation)" :disabled="historyBusy" @click="selectConversation(conversation.id)">
            <el-icon><ChatLineRound /></el-icon>
            <span class="history-copy">
              <span class="history-title">{{ conversationTitle(conversation) }}</span>
              <span class="history-meta">{{ conversationDate(conversation) }}</span>
            </span>
          </button>
          <el-dropdown trigger="click" :disabled="historyBusy" @command="handleHistoryCommand($event, conversation)">
            <button class="history-more" :disabled="historyBusy" :aria-label="`管理对话：${conversationTitle(conversation)}`"><el-icon><MoreFilled /></el-icon></button>
            <template #dropdown><el-dropdown-menu>
              <el-dropdown-item command="rename">重命名</el-dropdown-item>
              <el-dropdown-item command="delete" divided>删除对话</el-dropdown-item>
            </el-dropdown-menu></template>
          </el-dropdown>
        </div>
      </div>
      <div v-if="historyTotal > historyPageSize" class="history-pager"><span>{{ historyPage }} / {{ Math.ceil(historyTotal / historyPageSize) }}</span><el-pagination small layout="prev, next" :total="historyTotal" :page-size="historyPageSize" :current-page="historyPage" :disabled="historyLoading" @current-change="loadConversations" /></div>
      <div class="rail-note">对话内容仅供教学参考</div>
    </aside>

    <div class="chat-stage">
      <header class="chat-topbar">
        <div class="chat-topbar-main">
          <button class="history-trigger" @click="historyOpen = true">对话记录</button>
          <div>
            <div class="chat-title">学业 AI 助手</div>
            <div class="chat-subtitle">与你一起梳理学习材料</div>
          </div>
        </div>
        <div class="chat-topbar-actions"><span v-if="activeMaterialId" class="material-badge" :title="activeMaterialLabel">正在参考：{{ activeMaterialLabel }}</span><SkillsDialog :disabled="historyBusy" /><GradingStandardDialog :disabled="taskBusy || suggestionBusy || inputBusy || actionBusy" /></div>
      </header>

      <div ref="messageArea" class="message-scroll" aria-live="polite">
        <div class="message-content-width">
          <div v-if="loading" class="loading-state">正在加载对话...</div>
          <div v-else-if="!messages.length" class="welcome">
            <div class="welcome-mark">✦</div>
            <h1>今天想了解哪位学生的学习情况？</h1>
            <p>可以查询学生资料、分析材料、生成图表与报告，也可以准备能力评价和留言。</p>
            <div class="suggestions">
              <button v-for="suggestion in suggestions" :key="suggestion" @click="fillSuggestion(suggestion)">
                {{ suggestion }}
              </button>
            </div>
          </div>
          <template v-else>
            <div
              v-for="(item, index) in messages"
              :key="index"
              class="message-row"
              :class="item.role === 'user' ? 'user-row' : 'assistant-row'"
            >
              <div v-if="item.role !== 'user'" class="assistant-avatar">✦</div>
              <div class="message-body">
                <div v-if="item.role !== 'user'" class="message-author">学业 AI 助手</div>
                <div v-if="item.role === 'user'" class="message-text">{{ item.content }}</div>
                <div v-else class="message-text markdown-content" v-html="renderMarkdown(item.content)" />
                <div v-if="item.role !== 'user' && messageArtifacts(item.content).length" class="artifact-list">
                  <div v-for="artifact in messageArtifacts(item.content)" :key="artifact.id" class="artifact-card">
                    <img v-if="artifact.name.endsWith('.png') && artifactPreviews[artifact.id]" :src="artifactPreviews[artifact.id]" :alt="artifact.name" class="artifact-preview" />
                    <div class="artifact-card-bottom">
                      <span>{{ artifact.name.endsWith('.png') ? '📊' : '📄' }} {{ artifact.name }}</span>
                      <button type="button" @click="downloadArtifact(artifact)">下载文件</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-if="pendingAction" class="action-preview" role="group" aria-label="待确认业务操作">
              <div class="action-preview-title">待确认：{{ pendingAction.label }}</div>
              <p>对象：{{ pendingAction.target_name }}<span v-if="pendingAction.target_title"> · 《{{ pendingAction.target_title }}》</span></p>
              <p v-if="pendingAction.score !== null && pendingAction.score !== undefined">{{ pendingAction.ai_suggested ? 'AI 建议分数（请导师核对）' : '分数' }}：{{ pendingAction.score }} 分</p>
              <p v-if="pendingAction.score_rationale" class="score-rationale">评分依据：{{ pendingAction.score_rationale }}</p>
              <p v-if="pendingAction.ai_suggested && pendingAction.grading_standard" class="ai-draft-note">生成时采用：{{ pendingAction.grading_standard.source === 'custom' ? '导师自定义评分标准' : '系统默认评分标准' }}。修改标准后，可重新生成建议。</p>
              <p v-if="pendingAction.content" class="action-preview-content">{{ pendingAction.content }}</p>
              <div class="action-preview-actions">
                <el-button :loading="actionBusy" @click="cancelAction">取消</el-button>
                <el-button type="primary" :loading="actionBusy" @click="confirmAction">确认执行</el-button>
              </div>
            </div>
            <form v-if="pendingInput" class="input-request" aria-label="补充操作信息" @submit.prevent="submitDetails">
              <div class="input-request-title">{{ pendingInput.kind === 'send_student_message' ? '准备给学生留言' : '准备能力评价' }}</div>
              <section class="input-section" aria-label="材料或学生信息">
                <div class="input-section-title">{{ pendingInput.kind === 'send_student_message' ? '接收学生' : '评价材料' }}</div>
                <template v-if="pendingInput.kind === 'send_student_message'">
                  <label>
                    <span>学生姓名或学号 <em v-if="pendingInput.missing_fields.includes('student_name')">必填</em></span>
                    <el-input v-model="details.student_name" maxlength="100" placeholder="请输入学生姓名或学号" />
                  </label>
                </template>
                <template v-else>
                  <div v-if="materialSummary" class="material-summary">
                    <strong>{{ materialSummary.title || '未命名材料' }}</strong>
                    <span>{{ materialSummary.student_name }}<span v-if="materialSummary.submit_time"> · 提交于 {{ materialSummary.submit_time }}</span></span>
                    <span>{{ materialTypeLabel(materialSummary.material_type) }} · {{ materialSummary.evaluated ? '已有评价' : '尚未评价' }}</span>
                    <p v-if="materialSummary.content_excerpt">{{ materialSummary.content_excerpt }}</p>
                  </div>
                  <div v-else class="material-picker">
                    <p>从你指导的学生材料中选择{{ pendingInput.kind === 'create_evaluation' ? '尚未评价' : '已有评价' }}的一份。</p>
                    <div class="material-lookup">
                      <el-input v-model="materialSearch.realName" clearable placeholder="学生姓名" @keydown.enter.prevent="searchMaterials" />
                      <el-input v-model="materialSearch.studentNo" clearable placeholder="学号（可选）" @keydown.enter.prevent="searchMaterials" />
                      <el-button native-type="button" :loading="materialSearching" @click="searchMaterials">搜索</el-button>
                    </div>
                    <div v-if="materialSearching" class="material-list-note">正在查找材料...</div>
                    <div v-else-if="materialSearchError" class="material-error">{{ materialSearchError }}</div>
                    <div v-else-if="!materialCandidates.length" class="material-list-note">没有找到符合条件的材料，可调整姓名或学号重试。</div>
                    <div v-else class="material-candidates">
                      <button v-for="row in materialCandidates" :key="row.id" type="button" class="material-candidate" :disabled="materialLoading" @click="selectMaterial(row)">
                        <strong>{{ row.title || '未命名材料' }}</strong>
                        <span>{{ row.studentRealName || '姓名未知' }}<template v-if="row.studentNo"> · {{ row.studentNo }}</template></span>
                        <small>{{ materialTypeLabel(row.materialType) }}<template v-if="row.submitTime"> · {{ row.submitTime }}</template></small>
                      </button>
                    </div>
                    <el-pagination v-if="materialTotal > materialSearch.pageSize" class="material-pager" small layout="prev, pager, next" :total="materialTotal" :page-size="materialSearch.pageSize" :current-page="materialSearch.page" :disabled="materialSearching || materialLoading" @current-change="fetchMaterials" />
                  </div>
                  <p v-if="materialError" class="material-error">{{ materialError }}</p>
                  <button v-if="materialSummary && !activeMaterialId" type="button" class="change-material" @click="changeMaterial">更换材料</button>
                </template>
              </section>
              <section class="input-section" aria-label="补充评价内容">
                <div class="input-section-title">{{ pendingInput.kind === 'send_student_message' ? '留言内容' : '评价内容' }}</div>
                <p v-if="pendingInput.kind !== 'delete_evaluation'">可填写或修改下方内容，也可以直接在聊天框回复。</p>
                <template v-if="['create_evaluation', 'update_evaluation'].includes(pendingInput.kind)">
                  <el-button class="ai-suggest-button" native-type="button" :loading="suggestionBusy" :disabled="!materialSummary || inputBusy" @click="suggestEvaluation">
                    ✦ 让 AI 根据材料生成建议分数和评语
                  </el-button>
                  <p v-if="pendingInput.ai_suggested" class="ai-draft-note">以下是 AI 草稿，不是正式成绩；请核对并按需修改。</p>
                  <details v-if="pendingInput.ai_suggested && pendingInput.grading_standard" class="grading-snapshot"><summary>生成时采用：{{ pendingInput.grading_standard.source === 'custom' ? '导师自定义评分标准' : '系统默认评分标准' }}</summary><p>{{ pendingInput.grading_standard.content }}</p></details>
                  <p v-if="pendingInput.score_rationale" class="score-rationale">评分依据：{{ pendingInput.score_rationale }}</p>
                  <label>
                    <span>分数（0–100） <em v-if="pendingInput.missing_fields.includes('score')">待补充</em></span>
                    <el-input v-model="details.score" type="number" min="0" max="100" step="0.5" placeholder="自行填写或让 AI 提供建议" />
                  </label>
                </template>
                <label v-if="pendingInput.kind !== 'delete_evaluation'">
                  <span>{{ pendingInput.kind === 'send_student_message' ? '留言' : '评语' }} <em v-if="pendingInput.missing_fields.includes('content')">待补充</em></span>
                  <el-input v-model="details.content" type="textarea" :rows="3" maxlength="1000" show-word-limit placeholder="自行填写或让 AI 起草" />
                </label>
                <p v-if="pendingInput.kind === 'delete_evaluation'">请核对上方材料，下一步会展示待删除评价的预览。</p>
              </section>
              <div class="action-preview-actions">
                <el-button native-type="button" :loading="inputBusy" :disabled="suggestionBusy" @click="cancelDetails">取消操作</el-button>
                <el-button type="primary" native-type="submit" :loading="inputBusy" :disabled="suggestionBusy || (pendingInput.kind !== 'send_student_message' && !materialSummary)">生成待确认预览</el-button>
              </div>
            </form>
            <AssistantProgress v-if="taskBusy || progress || harness || progressError" :progress="progress" :harness="harness" :busy="taskBusy" :error="progressError" :execution="execution" />
          </template>
        </div>
      </div>

      <div class="composer-area">
        <div class="composer-inner">
          <div v-if="currentMaterialId && !selectedId" class="material-option">
            <el-checkbox v-model="useCurrentMaterial">引用：{{ currentMaterialLabel }}（含可解析附件）</el-checkbox>
          </div>
          <el-alert v-if="contextWarning" class="context-warning" :title="contextWarning" type="warning" :closable="false" />
          <div v-if="(execution && execution.status !== 'completed') || stateUncertain" class="execution-state" role="status">
            <div><strong>{{ executionStatusLabel }}</strong><p v-if="execution?.message">{{ execution.message }}</p><p v-else-if="canResume">恢复会继续处理原问题，不会重复发送消息；正式评价与留言仍需确认。</p></div>
            <el-button v-if="canResume" size="small" :loading="sending" :disabled="sending || suggestionBusy" @click="resumeExecution">恢复任务</el-button>
            <el-button v-if="stateUncertain" size="small" @click="refreshExecution">核实状态</el-button>
          </div>
          <div class="composer-box">
            <el-input
              ref="composerInput"
              v-model="input"
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 6 }"
              maxlength="2000"
              placeholder="向学业 AI 助手提问"
              :disabled="taskBusy || suggestionBusy"
              @keydown="onComposerKeydown"
            />
            <div class="composer-bottom">
              <span>Enter 发送 · Shift + Enter 换行</span>
              <div class="composer-actions">
                <span class="character-count">{{ input.length }} / 2000</span>
                <el-button v-if="taskBusy" class="stop-button" :loading="cancelBusy" :disabled="!canCancel" aria-label="停止任务" @click="cancelExecution">{{ execution?.status === 'cancel_requested' ? '停止中' : execution?.status === 'committing' ? '保存中' : '停止' }}</el-button>
                <el-button v-else class="send-button" type="primary" circle :disabled="!input.trim() || suggestionBusy" aria-label="发送消息" @click="send">
                  <el-icon><ArrowUp /></el-icon>
                </el-button>
              </div>
            </div>
          </div>
          <p class="disclaimer">AI 回答可能有误。请核对材料与事实，正式评分和点评由导师决定。</p>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { ArrowUp, ChatLineRound, Plus, Search, MoreFilled } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import agentHttp, { streamAssistantMessage, resumeAssistantExecution } from '../../api/agentHttp'
import AssistantProgress from './AssistantProgress.vue'
import GradingStandardDialog from './GradingStandardDialog.vue'
import SkillsDialog from './SkillsDialog.vue'
import { useAssistantProgress } from './useAssistantProgress'
import http from '../../api/http'
import { requestErrorMessage } from '../../api/requestErrorMessage'
import {
  conversationDate, conversationTitle, materialContextLabel, materialTypeLabel,
  messageArtifacts, renderMarkdown
} from './assistantContent'
import { useAssistantArtifacts } from './useAssistantArtifacts'
import { useAssistantHistory } from './useAssistantHistory'
import { useAssistantExecution } from './useAssistantExecution'

const props = defineProps({ currentMaterialId: { type: Number, default: null },
  initialConversationId: { type: String, default: '' } })
const emit = defineEmits(['conversation-change'])

const suggestions = [
  '查询一位学生的班级和专业',
  '帮我概括一份学习材料的主要内容',
  '帮我准备一份能力评价',
  '根据学生材料生成学情图表',
  '给我的学生发送一条留言'
]
const { conversations, keyword: historyKeyword, page: historyPage, pageSize: historyPageSize,
  total: historyTotal, historyLoading, loadConversations, disposeHistory } = useAssistantHistory(
  agentHttp, error => ElMessage.error(requestErrorMessage(error))
)
const selectedId = ref('')
const activeMaterialId = ref(null)
const materialLabels = ref({})
const materialLabelRequests = new Map()
const activeMaterialLabel = computed(() => materialContextLabel(materialLabels.value[activeMaterialId.value]))
const currentMaterialLabel = computed(() => materialContextLabel(materialLabels.value[props.currentMaterialId]))
const useCurrentMaterial = ref(Boolean(props.currentMaterialId))
const contextWarning = ref('')
const messages = ref([])
const { artifactPreviews, clearArtifactPreviews, loadArtifactPreviews, downloadArtifact } = useAssistantArtifacts()
const input = ref('')
const loading = ref(false)
const sending = ref(false)
const { execution, active: executionActive, canCancel, canResume, cancelBusy, stateUncertain,
  statusLabel: executionStatusLabel, observeConversation, beginExecution,
  handleEvent: handleExecutionEvent, refreshExecution, cancelExecution, connectionLost,
  disposeExecution } = useAssistantExecution(agentHttp, {
  onTerminal: ({ conversationId }) => {
    // 连接正常时由本轮 send 收尾统一加载，避免轮询和 result 同时追加相同答复。
    if (!sending.value && selectedId.value === conversationId) void refreshConversationSnapshot(conversationId)
  },
  onError: error => ElMessage.warning(requestErrorMessage(error))
})
const taskBusy = computed(() => sending.value || executionActive.value)
const historyOpen = ref(false)
const pendingAction = ref(null)
const pendingInput = ref(null)
const inputBusy = ref(false)
const suggestionBusy = ref(false)
const materialLoading = ref(false)
const materialSummary = ref(null)
const materialError = ref('')
const materialSearchError = ref('')
const materialSearching = ref(false)
const materialCandidates = ref([])
const materialTotal = ref(0)
const materialSearch = ref({ realName: '', studentNo: '', page: 1, pageSize: 5 })
const details = ref({ material_id: '', student_name: '', score: '', content: '' })
const actionBusy = ref(false)
const historyActionBusy = ref(false)
const historyBusy = computed(() => taskBusy.value || suggestionBusy.value || inputBusy.value || actionBusy.value || historyActionBusy.value)
const messageArea = ref(null)
const composerInput = ref(null)
let conversationLoadVersion = 0
const { progress, harness, progressError, resetProgress, handleProgress, completeProgress } = useAssistantProgress()
let streamController = null
let disposed = false
let materialLoadVersion = 0
let materialSearchVersion = 0

// 顶部与引用选项展示经 Agent 鉴权后的摘要；失败时保留无编号的中性文案。
async function ensureMaterialLabel(id) {
  const materialId = Number(id)
  if (!Number.isInteger(materialId) || materialId <= 0 || materialLabels.value[materialId]) return
  if (materialLabelRequests.has(materialId)) return materialLabelRequests.get(materialId)
  const request = agentHttp.get(`/api/chat/materials/${materialId}/summary`)
    .then(({ data }) => { materialLabels.value = { ...materialLabels.value, [materialId]: data } })
    .catch(() => { /* 详情入口仍可正常对话；请求失败时不展示内部编号。 */ })
    .finally(() => materialLabelRequests.delete(materialId))
  materialLabelRequests.set(materialId, request)
  return request
}

// 人工补充表单会随 Agent 的 pending_input 更新，旧的材料请求必须作废。
function setPendingInput(value) {
  materialLoadVersion += 1
  materialSearchVersion += 1
  pendingInput.value = value || null
  materialSummary.value = null
  materialLoading.value = false
  materialError.value = ''
  materialSearchError.value = ''
  materialCandidates.value = []
  materialTotal.value = 0
  materialSearching.value = false
  materialSearch.value = {
    realName: value?.student_name || '', studentNo: '', page: 1, pageSize: 5
  }
  details.value = {
    material_id: value?.material_id == null ? '' : String(value.material_id),
    student_name: value?.student_name || '',
    score: value?.score == null ? '' : String(value.score),
    content: value?.content || ''
  }
  if (value?.material_id && value.kind !== 'send_student_message') loadMaterialSummary()
  else if (value && value.kind !== 'send_student_message') fetchMaterials()
}

// 更换材料时清除旧材料对应的 AI 评分与评语，避免误提交到新材料。
function changeMaterial() {
  materialLoadVersion += 1
  materialSummary.value = null
  materialLoading.value = false
  details.value.material_id = ''
  details.value.score = ''
  details.value.content = ''
  pendingInput.value = { ...pendingInput.value, ai_suggested: false, score_rationale: '' }
  materialError.value = ''
  fetchMaterials(1)
}

// 使用后端分页接口列出当前导师可评价的材料；版本号阻止旧搜索覆盖新结果。
async function fetchMaterials(page = 1) {
  if (!pendingInput.value || pendingInput.value.kind === 'send_student_message') return
  const version = ++materialSearchVersion
  materialSearch.value.page = page
  materialSearching.value = true
  materialSearchError.value = ''
  materialCandidates.value = []
  materialTotal.value = 0
  try {
    const { data } = await http.get('/teacher/evaluation/page', { params: {
      page, pageSize: materialSearch.value.pageSize,
      realName: materialSearch.value.realName.trim() || undefined,
      studentNo: materialSearch.value.studentNo.trim() || undefined,
      evaluated: pendingInput.value.kind === 'create_evaluation' ? 0 : 1
    } })
    if (version !== materialSearchVersion) return
    const pageData = data?.data && (data.data.records || data.data.total !== undefined) ? data.data : data
    materialCandidates.value = Array.isArray(pageData?.records) ? pageData.records : []
    materialTotal.value = Number(pageData?.total) || 0
  } catch (error) {
    if (version === materialSearchVersion) materialSearchError.value = requestErrorMessage(error)
  } finally {
    if (version === materialSearchVersion) materialSearching.value = false
  }
}

// 搜索条件变化后从第一页重新取数，避免停在不存在的旧页码。
function searchMaterials() {
  fetchMaterials(1)
}

// 选择列表项后用详情接口核验，避免仅凭分页列表中的旧状态提交。
async function selectMaterial(row) {
  details.value.material_id = String(row.id)
  await loadMaterialSummary()
}

// 再向 Agent 获取材料摘要；业务确认前必须核对所选材料是否仍可访问。
async function loadMaterialSummary() {
  const id = Number(details.value.material_id)
  if (!Number.isInteger(id) || id <= 0) {
    materialError.value = '请先选择一份学习材料'
    return
  }
  const version = ++materialLoadVersion
  materialLoading.value = true
  materialError.value = ''
  try {
    const { data } = await agentHttp.get(`/api/chat/materials/${id}/summary`)
    if (version === materialLoadVersion) materialSummary.value = data
  } catch (error) {
    if (version === materialLoadVersion) {
      materialError.value = requestErrorMessage(error)
      materialSummary.value = null
      details.value.material_id = ''
      if (!materialCandidates.value.length) fetchMaterials()
    }
  } finally {
    if (version === materialLoadVersion) materialLoading.value = false
  }
}

// AI 建议仍是待补充草稿，刷新会话后由导师检查分数与评语。
async function suggestEvaluation() {
  if (!pendingInput.value || !materialSummary.value || suggestionBusy.value) return
  suggestionBusy.value = true
  try {
    await agentHttp.post(`/api/chat/inputs/${pendingInput.value.id}/suggest`, {
      material_id: materialSummary.value.material_id
    })
    suggestionBusy.value = false
    await selectConversation(selectedId.value)
    await loadConversations()
  } catch (error) {
    ElMessage.error(requestErrorMessage(error))
  } finally {
    suggestionBusy.value = false
  }
}

async function scrollBottom() {
  await nextTick()
  if (messageArea.value) messageArea.value.scrollTop = messageArea.value.scrollHeight
}

// 修改标题仅影响历史列表，不改变对话内容和已确认的业务对象。
async function handleHistoryCommand(command, conversation) {
  if (historyBusy.value) return
  historyActionBusy.value = true
  try {
    if (command === 'rename') {
      const { value } = await ElMessageBox.prompt('为这段对话设置一个容易查找的名称。', '重命名对话', {
        inputValue: conversation.title || '', confirmButtonText: '保存', cancelButtonText: '取消',
        inputValidator: value => (value?.trim() && value.trim().length <= 80) || '请输入 1–80 个字符的标题'
      })
      await agentHttp.patch(`/api/chat/conversations/${conversation.id}`, { title: value.trim() })
      ElMessage.success('对话已重命名')
    } else if (command === 'delete') {
      await ElMessageBox.confirm(`删除“${conversationTitle(conversation)}”后，将无法在历史列表中继续这段对话。评分标准和长期记忆会保留。`, '删除对话', {
        confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning'
      })
      await agentHttp.delete(`/api/chat/conversations/${conversation.id}`)
      if (selectedId.value === conversation.id) startNew()
      ElMessage.success('对话已删除')
    } else return
    await loadConversations()
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') ElMessage.error(requestErrorMessage(error))
  } finally {
    historyActionBusy.value = false
  }
}

// 新会话只重置前端状态；历史会话仍由 Agent 保存并可在左侧恢复。
function startNew() {
  if (taskBusy.value || suggestionBusy.value || inputBusy.value || actionBusy.value) return
  conversationLoadVersion += 1
  loading.value = false
  selectedId.value = ''
  activeMaterialId.value = null
  useCurrentMaterial.value = Boolean(props.currentMaterialId)
  contextWarning.value = ''
  messages.value = []
  observeConversation('')
  resetProgress()
  clearArtifactPreviews()
  pendingAction.value = null
  setPendingInput(null)
  input.value = ''
  historyOpen.value = false
  nextTick(() => composerInput.value?.focus())
}

// 异步加载历史时用版本号排除已经切走的会话，防止串话。
async function selectConversation(id) {
  if (taskBusy.value || suggestionBusy.value) return
  if (!id) {
    startNew()
    return
  }
  const version = ++conversationLoadVersion
  selectedId.value = id
  observeConversation(id)
  activeMaterialId.value = null
  messages.value = []
  resetProgress()
  clearArtifactPreviews()
  pendingAction.value = null
  setPendingInput(null)
  historyOpen.value = false
  loading.value = true
  try {
    const { data } = await agentHttp.get(`/api/chat/conversations/${id}`)
    if (version !== conversationLoadVersion) return
    applyConversationSnapshot(data)
    observeConversation(data.id, data.execution)
  } catch (error) {
    if (version !== conversationLoadVersion) return
    startNew()
    ElMessage.error(requestErrorMessage(error))
  } finally {
    if (version === conversationLoadVersion) {
      loading.value = false
      await scrollBottom()
    }
  }
}

// 页面刷新、停止与恢复都以服务端会话为准；只替换当前会话，避免跨会话迟到回包串话。
function applyConversationSnapshot(data) {
  selectedId.value = data.id
  activeMaterialId.value = data.material_id
  contextWarning.value = ''
  // 未完成问题存于 execution，不是已完成 HOT 对话；刷新和停止后仍显示其原文。
  messages.value = [...(data.messages || []), ...(data.pending_question
    ? [{ role: 'user', content: data.pending_question }] : [])]
  resetProgress(data.harness || null)
  void loadArtifactPreviews(messages.value)
  pendingAction.value = data.pending_action || null
  setPendingInput(data.pending_input)
}

async function refreshConversationSnapshot(id) {
  const version = conversationLoadVersion
  try {
    const { data } = await agentHttp.get(`/api/chat/conversations/${id}`)
    if (disposed || selectedId.value !== id || version !== conversationLoadVersion) return
    applyConversationSnapshot(data)
    await scrollBottom()
  } catch (error) {
    if (!disposed && selectedId.value === id) contextWarning.value = requestErrorMessage(error)
  }
}

function fillSuggestion(suggestion) {
  input.value = suggestion
  nextTick(() => composerInput.value?.focus())
}

// 保留中文输入法合成状态，避免选择候选词时误发送。
function onComposerKeydown(event) {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) {
    event.preventDefault()
    send()
  }
}

// 只在服务端尚未接收问题时回滚气泡；已有 session 的断线任务通过状态接口核实。
async function send() {
  const question = input.value.trim()
  if (!question || taskBusy.value || suggestionBusy.value) return
  const request = { message: question }
  if (selectedId.value) request.conversation_id = selectedId.value
  else if (useCurrentMaterial.value && props.currentMaterialId) request.material_id = props.currentMaterialId
  input.value = ''
  messages.value.push({ role: 'user', content: question })
  await runExecution(request, question)
}

// 恢复不会再次追加用户气泡，也不从输入框重建原问题，服务端检查原执行的归属和状态。
async function resumeExecution() {
  if (!canResume.value || taskBusy.value || suggestionBusy.value) return
  const { id, attempt } = execution.value
  await runExecution({ conversation_id: selectedId.value }, '', id, attempt)
}

async function runExecution(request, question, resumeId = null, resumeAttempt = undefined) {
  resetProgress()
  sending.value = true
  streamController = new AbortController()
  const version = beginExecution(request.conversation_id || '')
  let accepted = Boolean(resumeId)
  await scrollBottom()
  try {
    const onEvent = (event, detail) => {
      if (disposed) return
      // 首个事件即保存已预留的会话，断线后仍可重新打开查看服务端结果。
      if (event === 'session') {
        accepted = true
        selectedId.value = detail.conversation_id
        if (request.material_id) activeMaterialId.value = request.material_id
      }
      handleExecutionEvent(event, detail, version)
      handleProgress(event, detail)
      void scrollBottom()
    }
    const data = resumeId
      ? await resumeAssistantExecution(request.conversation_id, resumeId, onEvent, streamController.signal, resumeAttempt)
      : await streamAssistantMessage(request, onEvent, streamController.signal)
    if (disposed) return
    if (!data.interrupted) {
      completeProgress(data)
      selectedId.value = data.conversation_id
      activeMaterialId.value = data.material_id
      contextWarning.value = (data.warnings || []).join('；')
      messages.value.push({ role: 'assistant', content: data.answer })
      void loadArtifactPreviews([{ content: data.answer }])
      pendingAction.value = data.pending_action || null
      setPendingInput(data.pending_input)
    }
    await refreshExecution()
    await refreshConversationSnapshot(selectedId.value)
    await loadConversations()
    await scrollBottom()
  } catch (error) {
    if (disposed) return
    const acceptedId = error.response?.data?.conversation_id
    if (acceptedId) {
      if (!accepted) observeConversation(acceptedId)
      accepted = true
      selectedId.value = acceptedId
      if (request.material_id) activeMaterialId.value = request.material_id
    }
    if (!accepted && request.conversation_id) {
      // 请求可能在 session 到达前被拒绝（例如另一窗口已在运行）。先读回真实状态；
      // 未被接收的新输入放回编辑框，绝不把它冒充该运行任务的原问题。
      const existingExecution = await refreshExecution()
      if (existingExecution) { accepted = true; input.value = question }
    }
    if (accepted) {
      connectionLost()
      await refreshExecution()
      await refreshConversationSnapshot(selectedId.value)
      void loadConversations()
    } else {
      messages.value.pop()
      input.value = question
      progressError.value = true
    }
    contextWarning.value = requestErrorMessage(error)
    ElMessage.error(requestErrorMessage(error))
  } finally {
    streamController = null
    sending.value = false
  }
}

// 缺失字段通过表格提交到 Agent；真正写入业务数据仍需下一步确认。
async function submitDetails() {
  if (!pendingInput.value || inputBusy.value || taskBusy.value || suggestionBusy.value) return
  const payload = {}
  if (details.value.material_id !== '') payload.material_id = Number(details.value.material_id)
  if (details.value.student_name.trim()) payload.student_name = details.value.student_name.trim()
  if (details.value.score !== '') payload.score = Number(details.value.score)
  if (details.value.content.trim()) payload.content = details.value.content.trim()
  inputBusy.value = true
  try {
    await agentHttp.post(`/api/chat/inputs/${pendingInput.value.id}/submit`, payload)
    await selectConversation(selectedId.value)
    await loadConversations()
  } catch (error) {
    ElMessage.error(requestErrorMessage(error))
  } finally {
    inputBusy.value = false
  }
}

// 人工补充表单取消后同步 Agent 状态，不能仅在前端隐藏表单。
async function cancelDetails() {
  if (!pendingInput.value || inputBusy.value || taskBusy.value || suggestionBusy.value) return
  inputBusy.value = true
  try {
    await agentHttp.post(`/api/chat/inputs/${pendingInput.value.id}/cancel`)
    await selectConversation(selectedId.value)
  } catch (error) {
    ElMessage.error(requestErrorMessage(error))
  } finally {
    inputBusy.value = false
  }
}

// 明确确认后才触发能力评价或留言的写入。
async function confirmAction() {
  if (!pendingAction.value || actionBusy.value || taskBusy.value) return
  actionBusy.value = true
  try {
    await agentHttp.post(`/api/chat/actions/${pendingAction.value.id}/confirm`)
    pendingAction.value = null
    await selectConversation(selectedId.value)
    await loadConversations()
  } catch (error) {
    ElMessage.error(requestErrorMessage(error))
  } finally {
    actionBusy.value = false
  }
}

// 拒绝待确认操作同样写回 Agent，防止旧预览后续被误执行。
async function cancelAction() {
  if (!pendingAction.value || actionBusy.value || taskBusy.value) return
  actionBusy.value = true
  try {
    await agentHttp.post(`/api/chat/actions/${pendingAction.value.id}/cancel`)
    pendingAction.value = null
    await selectConversation(selectedId.value)
  } catch (error) {
    ElMessage.error(requestErrorMessage(error))
  } finally {
    actionBusy.value = false
  }
}

watch(() => props.currentMaterialId, (id) => {
  useCurrentMaterial.value = Boolean(id)
  void ensureMaterialLabel(id)
}, { immediate: true })
watch(activeMaterialId, (id) => { void ensureMaterialLabel(id) })
watch(selectedId, id => emit('conversation-change', id))
onMounted(() => {
  void loadConversations()
  // 路由仅保留会话标识，刷新后读取已有任务；不保存令牌，也不自动重发原问题。
  if (props.initialConversationId) void selectConversation(props.initialConversationId)
})
// 离开页面只结束接收，服务端继续保存本轮结果；不自动重发原消息。
onBeforeUnmount(() => {
  disposed = true
  conversationLoadVersion += 1
  materialLoadVersion += 1
  materialSearchVersion += 1
  disposeHistory()
  disposeExecution()
  streamController?.abort()
})
</script>

<style scoped src="./AssistantWorkspace.css"></style>
