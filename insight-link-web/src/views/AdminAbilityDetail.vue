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
                    <div class="score-number" :class="{ pop: scorePop, muted: material.evaluated !== 1 }">
                      {{ material.evaluated === 1 ? scoreText : '-' }}
                    </div>
                    <div class="score-unit">/ 100</div>
                  </div>
                  <div class="score-progress">
                    <el-progress
                      v-if="material.evaluated === 1"
                      type="circle"
                      :percentage="scorePercent"
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
          </div>
        </template>
      </el-skeleton>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import http from '../api/http'
import { ArrowLeft, Document, Download } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const material = ref(null)
const scoreValue = ref(0)
const scorePop = ref(false)

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

const scoreText = computed(() => {
  const v = scoreValue.value
  return Number.isFinite(v) ? String(Math.round(v)) : '-'
})

const scorePercent = computed(() => {
  const v = Number(scoreValue.value)
  if (!Number.isFinite(v)) return 0
  return Math.max(0, Math.min(100, Math.round(v)))
})

const scoreColor = computed(() => {
  const v = scorePercent.value
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
    const { data } = await http.get(`/admin/material/${id}`)
    material.value = data?.data || null
  } finally {
    loading.value = false
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
  router.push({ path: '/admin/ability', query: route.query || {} })
}

watch(
  () => materialId.value,
  () => {
    fetchMaterial()
  }
)

watch(
  () => material.value,
  (m) => {
    if (m?.evaluated === 1 && m?.score !== null && m?.score !== undefined) {
      animateScore(m.score)
      return
    }
    scoreValue.value = 0
  },
  { immediate: true }
)

onMounted(() => {
  fetchMaterial()
})
</script>

<style scoped>
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
.score-number.pop {
  animation: score-pop 520ms ease;
}
.score-number.muted {
  color: #9ca3af;
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
