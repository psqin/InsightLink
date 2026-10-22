<template>
  <div class="page">
    <div class="card">
      <div class="head">
        <div class="head-left">
          <el-button class="back" link type="primary" @click="goBack">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <div class="head-title">{{ material?.title || '材料查看' }}</div>
        </div>
        <div class="head-right">
          <el-tag effect="light">{{ materialTypeLabel(material?.materialType) }}</el-tag>
          <el-tag :type="material?.evaluated === 1 ? 'success' : 'info'" effect="light">{{ evaluatedLabel(material?.evaluated) }}</el-tag>
        </div>
      </div>

      <el-skeleton :loading="loading" animated>
        <template #template>
          <el-skeleton-item variant="h1" style="width: 240px" />
          <el-skeleton-item variant="text" style="margin-top: 12px" />
          <el-skeleton-item variant="text" style="margin-top: 8px" />
          <el-skeleton-item variant="rect" style="margin-top: 14px; height: 180px" />
        </template>
        <template #default>
          <div v-if="!material" class="empty">暂无内容</div>
          <div v-else>
            <div class="meta">
              <div class="meta-item">
                <div class="k">提交时间</div>
                <div class="v">{{ material.submitTime || '-' }}</div>
              </div>
              <div class="meta-item" v-if="material.evaluated === 1">
                <div class="k">批阅时间</div>
                <div class="v">{{ material.evaluationTime || '-' }}</div>
              </div>
              <div class="meta-item" v-if="material.evaluated === 1">
                <div class="k">批阅导师</div>
                <div class="v">{{ material.teacherRealName || '-' }}</div>
              </div>
            </div>

            <div class="body">
              <div class="main-content">
                <div class="section">
                  <div class="section-title">材料内容</div>
                  <div class="content">{{ material.content || '-' }}</div>
                </div>

                <div class="section" v-if="material.fileUrl" style="margin-top: 14px; padding: 0;">
                  <div class="section-title" style="padding: 14px 16px; display: flex; justify-content: space-between; align-items: center; margin-bottom: 0;">
                    <span>附件预览</span>
                    <el-button type="primary" link @click="downloadAttachment(material.fileUrl)">
                      <el-icon><Download /></el-icon> 下载附件
                    </el-button>
                  </div>
                  <div class="file-preview-wrapper">
                    <iframe v-if="getFileType(material.fileUrl) === 'pdf'" :src="material.fileUrl" class="preview-frame"></iframe>
                    <iframe v-else-if="getFileType(material.fileUrl) === 'office'" :src="'https://view.officeapps.live.com/op/embed.aspx?src=' + encodeURIComponent(material.fileUrl)" class="preview-frame"></iframe>
                    <img v-else-if="getFileType(material.fileUrl) === 'image'" :src="material.fileUrl" class="preview-img" />
                    <div v-else class="unsupported-msg">
                      <el-icon :size="48" color="#9ca3af"><Document /></el-icon>
                      <div style="margin-top: 10px; color: #6b7280;">该格式暂不支持预览，请下载后查看</div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="side">
                <div class="score-card">
                  <div class="score-top">
                    <div class="section-title">评分</div>
                  </div>
                  <div class="score-main">
                    <div class="score-number" :class="{ pop: scorePop, muted: material.evaluated !== 1 && !hasDraftScore }">
                      {{ displayScoreText }}
                    </div>
                    <div class="score-unit">/ 100</div>
                  </div>
                  <div class="score-progress">
                    <el-progress
                      v-if="material.evaluated === 1 || hasDraftScore"
                      type="circle"
                      :percentage="displayScorePercent"
                      :stroke-width="10"
                      :width="110"
                      :color="scoreColor"
                    />
                    <div v-else class="score-empty">未批阅</div>
                  </div>
                </div>

                <transition name="fade-slide">
                  <div v-if="material.evaluated === 1" class="section">
                    <div class="section-title">导师评语</div>
                    <div class="content">{{ material.evaluationContent || '-' }}</div>
                  </div>
                </transition>
              </div>
            </div>

            <div class="section evaluate">
              <div class="section-title">{{ material.evaluated === 1 ? '修改评价' : '材料评价' }}</div>
              <el-form label-position="top">
                <div class="evaluate-grid">
                  <el-form-item label="评分（0-100）">
                    <el-input-number
                      v-model="form.score"
                      :min="0"
                      :max="100"
                      controls-position="right"
                      style="width: 180px"
                      :disabled="saving"
                    />
                  </el-form-item>
                </div>

                <el-form-item label="评价内容">
                  <el-input
                    v-model="form.content"
                    type="textarea"
                    :rows="4"
                    maxlength="1000"
                    show-word-limit
                    :disabled="saving"
                  />
                </el-form-item>

                <div class="evaluate-actions">
                  <el-button @click="router.push({ path: '/teacher/assistant', query: { materialId: material.id } })">
                    与学业 AI 助手讨论材料
                  </el-button>
                  <el-button
                    v-if="material.evaluated !== 1"
                    type="success"
                    plain
                    :loading="agentLoading"
                    :disabled="saving"
                    @click="generateAgentDraft"
                  >AI 生成评语草稿</el-button>
                  <el-button type="primary" :loading="saving" @click="submitEvaluation">
                    {{ material.evaluated === 1 ? '保存修改' : '提交评价' }}
                  </el-button>
                  <el-button :disabled="saving" @click="resetForm">重置</el-button>
                </div>
              </el-form>
            </div>
          </div>
        </template>
      </el-skeleton>
    </div>

    <el-dialog
      v-model="agentDialogOpen"
      title="AI 点评草稿"
      width="720px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <el-alert
        title="草稿仅供导师参考；请核对引用和事实，评分由导师填写。"
        type="warning"
        :closable="false"
        show-icon
      />
      <el-alert
        v-for="(warning, index) in agentRun?.warnings || []"
        :key="`warning-${index}`"
        class="agent-warning"
        :title="warning"
        type="warning"
        :closable="false"
      />
      <template v-if="agentRun?.draft">
        <div class="agent-block">
          <strong>材料概述</strong>
          <p>{{ agentRun.draft.summary }}</p>
        </div>
        <div class="agent-block" v-if="agentRun.draft.strengths?.length">
          <strong>可肯定之处</strong>
          <ul>
            <li v-for="(claim, index) in agentRun.draft.strengths" :key="`strength-${index}`">
              {{ claim.text }} <span class="agent-evidence">{{ sourceLabel(claim.source_id) }}：{{ claim.quote }}</span>
            </li>
          </ul>
        </div>
        <div class="agent-block" v-if="agentRun.draft.concerns?.length">
          <strong>待核实之处</strong>
          <ul>
            <li v-for="(claim, index) in agentRun.draft.concerns" :key="`concern-${index}`">
              {{ claim.text }} <span class="agent-evidence">{{ sourceLabel(claim.source_id) }}：{{ claim.quote }}</span>
            </li>
          </ul>
        </div>
        <div class="agent-block" v-if="agentRun.draft.actions?.length">
          <strong>建议行动</strong>
          <ul><li v-for="(action, index) in agentRun.draft.actions" :key="`action-${index}`">{{ action }}</li></ul>
        </div>
        <el-form-item label="确认或修改评语">
          <el-input v-model="agentComment" type="textarea" :rows="5" maxlength="1000" show-word-limit />
        </el-form-item>
      </template>
      <template #footer>
        <el-button :loading="agentSaving" @click="rejectAgentDraft">不采用</el-button>
        <el-button type="primary" :loading="agentSaving" :disabled="!agentComment.trim()" @click="approveAgentDraft">
          采用到评语输入框
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import http from '../api/http'
import agentHttp from '../api/agentHttp'
import { requestErrorMessage } from '../api/requestErrorMessage'
import { ArrowLeft, Document, Download } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const agentLoading = ref(false)
const agentSaving = ref(false)
const agentDialogOpen = ref(false)
const agentRun = ref(null)
const agentComment = ref('')
const material = ref(null)
const scoreValue = ref(0)
const scorePop = ref(false)

const form = ref({
  content: '',
  id: undefined,
  materialId: undefined,
  score: undefined
})

const materialId = computed(() => {
  const raw = route.params?.id
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
})

function materialTypeLabel(t) {
  if (t === 1) return '学习计划'
  if (t === 2) return '进度汇报'
  if (t === 3) return '自我总结'
  return t === 0 ? '0' : t ? String(t) : '-'
}

function evaluatedLabel(v) {
  return v === 1 ? '已批阅' : '未批阅'
}

const hasDraftScore = computed(() => {
  if (form.value.score === '' || form.value.score === undefined || form.value.score === null) return false
  const v = Number(form.value.score)
  return Number.isFinite(v)
})

const displayScoreNumber = computed(() => {
  if (material.value?.evaluated === 1) return Number(scoreValue.value)
  if (hasDraftScore.value) return Number(form.value.score)
  return NaN
})

const displayScoreText = computed(() => {
  const v = displayScoreNumber.value
  return Number.isFinite(v) ? String(Math.round(v)) : '-'
})

const displayScorePercent = computed(() => {
  const v = displayScoreNumber.value
  if (!Number.isFinite(v)) return 0
  return Math.max(0, Math.min(100, Math.round(v)))
})

const scoreColor = computed(() => {
  const v = displayScorePercent.value
  if (v >= 85) return '#16a34a'
  if (v >= 60) return '#f59e0b'
  return '#ef4444'
})

function animateScore(toScore) {
  const target = Math.max(0, Math.min(100, Number(toScore)))
  if (!Number.isFinite(target)) {
    scoreValue.value = 0
    return
  }

  const from = Number.isFinite(scoreValue.value) ? scoreValue.value : 0
  const start = performance.now()
  const duration = 700

  scorePop.value = true
  window.setTimeout(() => {
    scorePop.value = false
  }, 520)

  const step = (now) => {
    const p = Math.min(1, (now - start) / duration)
    const eased = 1 - Math.pow(1 - p, 3)
    scoreValue.value = from + (target - from) * eased
    if (p < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

async function fetchMaterial() {
  const id = materialId.value
  if (!id) {
    material.value = null
    return
  }
  loading.value = true
  try {
    const { data } = await http.get(`/teacher/evaluation/${id}`)
    material.value = data?.data || null
  } finally {
    loading.value = false
  }
}

function applyFormFromMaterial() {
  const m = material.value
  form.value.materialId = m?.id ?? materialId.value ?? undefined
  if (m?.evaluated === 1) {
    form.value.id = m?.evaluationId ?? undefined
    form.value.score = m?.score ?? undefined
    form.value.content = m?.evaluationContent ?? ''
    const v = m?.score
    if (v !== undefined && v !== null) {
      scoreValue.value = 0
      animateScore(v)
    }
    return
  }
  scoreValue.value = 0
  form.value.id = undefined
  form.value.score = undefined
  form.value.content = ''
}

function resetForm() {
  applyFormFromMaterial()
}

function sourceLabel(sourceId) {
  const source = agentRun.value?.sources?.find((item) => item.id === sourceId)
  return source?.title || `来源 ${sourceId}`
}

// 生成有材料证据的草稿并等待导师审阅，不直接提交正式能力评价。
async function generateAgentDraft() {
  if (!material.value?.id) return
  if (!material.value?.content?.trim() && !material.value?.fileUrl) {
    ElMessage.warning('材料正文和附件均为空，无法生成草稿')
    return
  }
  agentLoading.value = true
  try {
    const { data } = await agentHttp.post('/api/runs', { material_id: material.value.id })
    if (data?.status !== 'awaiting_approval' || !data?.draft) {
      const issues = data?.review?.issues?.join('；')
      ElMessage.warning(issues || '草稿未通过复核，请稍后重试')
      return
    }
    agentRun.value = data
    agentComment.value = data.draft.comment || ''
    agentDialogOpen.value = true
  } catch (error) {
    ElMessage.error(requestErrorMessage(error))
  } finally {
    agentLoading.value = false
  }
}

// 导师确认后仅把评语写入当前表单，正式保存仍走原评价提交按钮。
async function approveAgentDraft() {
  if (!agentRun.value?.run_id || !agentComment.value.trim()) return
  agentSaving.value = true
  try {
    const { data } = await agentHttp.post(`/api/runs/${agentRun.value.run_id}/decision`, {
      decision: 'approve', edited_comment: agentComment.value.trim()
    })
    form.value.content = data.final_comment
    agentDialogOpen.value = false
    agentRun.value = null
    ElMessage.success('草稿已填入评语；请填写评分并检查后提交')
  } catch (error) {
    ElMessage.error(requestErrorMessage(error))
    if (error?.response?.status === 409) {
      agentDialogOpen.value = false
      agentRun.value = null
      await fetchMaterial()
    }
  } finally {
    agentSaving.value = false
  }
}

// 拒绝草稿时通知 Agent 结束待审批运行，避免留下可重复采用的草稿。
async function rejectAgentDraft() {
  if (!agentRun.value?.run_id) {
    agentDialogOpen.value = false
    return
  }
  agentSaving.value = true
  try {
    await agentHttp.post(`/api/runs/${agentRun.value.run_id}/decision`, { decision: 'reject' })
    agentDialogOpen.value = false
    agentRun.value = null
  } catch (error) {
    ElMessage.error(requestErrorMessage(error))
  } finally {
    agentSaving.value = false
  }
}

async function submitEvaluation() {
  const m = material.value
  const materialIdVal = m?.id ?? materialId.value
  if (!materialIdVal) return

  const payload = {
    content: (form.value.content || '').trim() || undefined,
    id: form.value.id ?? undefined,
    materialId: materialIdVal,
    score: form.value.score === '' || form.value.score === undefined || form.value.score === null ? undefined : Number(form.value.score)
  }

  if (payload.score === undefined) {
    ElMessage.warning('请填写评分')
    return
  }

  saving.value = true
  try {
    if (m?.evaluated === 1) {
      await http.put('/teacher/evaluation', payload)
      ElMessage.success('修改成功')
    } else {
      const createPayload = { content: payload.content, materialId: payload.materialId, score: payload.score }
      await http.post('/teacher/evaluation', createPayload)
      ElMessage.success('评价成功')
    }
    await fetchMaterial()
  } finally {
    saving.value = false
  }
}

function getFileType(url) {
  if (!url) return 'unknown'
  const lower = url.toLowerCase()
  if (lower.endsWith('.pdf')) return 'pdf'
  if (/\.(doc|docx|xls|xlsx|ppt|pptx)$/.test(lower)) return 'office'
  if (/\.(png|jpg|jpeg|gif|webp)$/.test(lower)) return 'image'
  return 'unknown'
}

function downloadAttachment(url) {
  window.open(url, '_blank')
}

function goBack() {
  router.push({ path: '/teacher/evaluation', query: route.query || {} })
}

watch(
  () => materialId.value,
  () => {
    agentDialogOpen.value = false
    agentRun.value = null
    fetchMaterial()
  }
)

watch(
  () => material.value,
  () => {
    applyFormFromMaterial()
  },
  { immediate: true }
)

onMounted(() => {
  fetchMaterial()
})
</script>

<style scoped>
.agent-block { margin: 16px 0; }
.agent-warning { margin-top: 10px; }
.agent-block p { margin: 8px 0 0; white-space: pre-wrap; }
.agent-block ul { margin: 8px 0 0; padding-left: 20px; }
.agent-block li { margin-bottom: 8px; }
.agent-evidence { color: #6b7280; font-size: 12px; }
.page {
  height: 100%;
}
.card {
  background: #ffffff;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 18px 20px;
}
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.head-left {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.back {
  padding: 0;
}
.head-title {
  font-size: 16px;
  font-weight: 800;
  color: #111827;
  max-width: 520px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.head-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 18px;
  margin-top: 14px;
  margin-bottom: 12px;
}
.meta-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.k {
  font-size: 12px;
  color: #6b7280;
}
.v {
  font-size: 12px;
  color: #111827;
}
.body {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 14px 18px;
  align-items: start;
}
.section {
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 14px 16px;
}
.section-title {
  font-size: 13px;
  font-weight: 800;
  color: #111827;
  margin-bottom: 10px;
}
.content {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  color: #111827;
  line-height: 1.65;
}
.side {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.score-card {
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 14px 16px;
}
.score-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.score-main {
  display: flex;
  align-items: baseline;
  gap: 6px;
  margin-top: 6px;
}
.score-number {
  font-size: 40px;
  font-weight: 900;
  letter-spacing: 0.4px;
  color: #111827;
  transform-origin: left center;
}
.score-number.muted {
  color: #9ca3af;
}
.score-number.pop {
  animation: score-pop 520ms ease;
}
.score-unit {
  font-size: 12px;
  color: #6b7280;
}
.score-progress {
  display: flex;
  justify-content: center;
  margin-top: 10px;
}
.score-empty {
  font-size: 12px;
  color: #6b7280;
  padding: 24px 0;
}
.empty {
  margin-top: 10px;
  font-size: 12px;
  color: #6b7280;
}
.file-preview-wrapper {
  position: relative;
  height: 800px;
  background: #f9fafb;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-top: 1px solid #ebeef5;
}
.preview-frame {
  width: 100%;
  height: 100%;
  border: none;
}
.preview-img {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
}
.unsupported-msg {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}
.evaluate {
  margin-top: 14px;
}
.evaluate-grid {
  display: grid;
  grid-template-columns: 1fr;
}
.evaluate-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.fade-slide-enter-active,
.fade-slide-leave-active {
  transition: opacity 200ms ease, transform 200ms ease;
}
.fade-slide-enter-from,
.fade-slide-leave-to {
  opacity: 0;
  transform: translateY(6px);
}
@keyframes score-pop {
  0% {
    transform: scale(1);
  }
  35% {
    transform: scale(1.08);
  }
  100% {
    transform: scale(1);
  }
}
@media (max-width: 960px) {
  .body {
    grid-template-columns: 1fr;
  }
  .head-title {
    max-width: 280px;
  }
}
</style>
