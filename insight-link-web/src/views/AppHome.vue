<template>
  <div class="home">
    <div class="grid">
      <div class="left">
        <div class="card">
          <div class="title-row">
            <div class="title">系统通知</div>
          </div>
          <el-skeleton :loading="loading" animated>
            <template #template>
              <el-skeleton-item variant="text" style="width: 80%" />
              <el-skeleton-item variant="text" style="width: 70%; margin-top: 10px" />
              <el-skeleton-item variant="text" style="width: 76%; margin-top: 10px" />
              <el-skeleton-item variant="text" style="width: 66%; margin-top: 10px" />
              <el-skeleton-item variant="text" style="width: 72%; margin-top: 10px" />
            </template>
            <template #default>
              <div class="list">
                <div
                  v-for="(n, i) in systemSlots"
                  :key="String(n?.id ?? `system-${i}`)"
                  :class="['item', { placeholder: !n }]"
                  @click="n && openNotice(n)"
                >
                  <div class="item-title">{{ n?.title || '—' }}</div>
                  <div class="item-time">{{ n?.publishTime || '—' }}</div>
                </div>
              </div>
            </template>
          </el-skeleton>
        </div>

        <div class="card">
          <div class="title-row">
            <div class="title">导师通知</div>
          </div>
          <el-skeleton :loading="loading" animated>
            <template #template>
              <el-skeleton-item variant="text" style="width: 78%" />
              <el-skeleton-item variant="text" style="width: 74%; margin-top: 10px" />
              <el-skeleton-item variant="text" style="width: 68%; margin-top: 10px" />
              <el-skeleton-item variant="text" style="width: 76%; margin-top: 10px" />
              <el-skeleton-item variant="text" style="width: 62%; margin-top: 10px" />
            </template>
            <template #default>
              <div class="list">
                <div
                  v-for="(n, i) in teacherSlots"
                  :key="String(n?.id ?? `teacher-${i}`)"
                  :class="['item', { placeholder: !n }]"
                  @click="n && openNotice(n)"
                >
                  <div class="item-title">{{ n?.title || '—' }}</div>
                  <div class="item-time">{{ n?.publishTime || '—' }}</div>
                </div>
              </div>
            </template>
          </el-skeleton>
        </div>
      </div>

      <div class="right">
        <div class="card calendar-card">
          <img class="calendar-bg" src="https://psqin001.oss-cn-beijing.aliyuncs.com/a2c30f4e-df6b-4204-b620-e5d6aa908929.jpg" alt="今日节日" />
          <!-- https://festival.wifilu.com/festival.php -->
          <div class="title-row">
            <div class="title">日历</div>
          </div>
          <div class="calendar-wrap">
            <el-calendar v-model="calendarDate" class="calendar">
              <template #date-cell="{ data }">
                {{ dayText(data.day) }}
                <span v-if="hasNoticeDay(data.day)" class="notice-ring"></span>
              </template>
            </el-calendar>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="noticeDialogVisible" :title="noticeDialogTitle" width="720px" append-to-body>
      <div class="notice-meta">
        <div class="notice-meta-item">
          <div class="k">发布时间</div>
          <div class="v">{{ currentNotice?.publishTime || '-' }}</div>
        </div>
        <div class="notice-meta-item">
          <div class="k">发布人</div>
          <div class="v">{{ currentNotice?.publisherRealName || (currentNotice?.publisherId ? String(currentNotice.publisherId) : '-') }}</div>
        </div>
      </div>
      <div class="notice-content">{{ currentNotice?.content || '-' }}</div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useAppStore } from '../store'
import http from '../api/http'

const store = useAppStore()
const roleLabel = computed(() => {
  if (store.roleId === 1) return '管理员端'
  if (store.roleId === 2) return '导师端'
  return '学生端'
})

const loading = ref(false)
const systemNotices = ref([])
const teacherNotices = ref([])
const systemSlots = computed(() => padToFive(systemNotices.value))
const teacherSlots = computed(() => padToFive(teacherNotices.value))
const calendarDate = ref(new Date())
const noticeDialogVisible = ref(false)
const currentNotice = ref(null)
const noticeDialogTitle = computed(() => currentNotice.value?.title || `${roleLabel.value}通知`)

function parseDayKeyFromDateTime(v) {
  if (!v) return ''
  const s = String(v).trim()
  const m = s.match(/^(\d{4}-\d{2}-\d{2})/)
  return m ? m[1] : ''
}

function dayText(dayKey) {
  const parts = String(dayKey).split('-')
  const d = parts[2]
  return d ? String(Number(d)) : ''
}

const markedDays = computed(() => {
  const set = new Set()
  const all = []
  if (Array.isArray(systemNotices.value)) all.push(...systemNotices.value)
  if (Array.isArray(teacherNotices.value)) all.push(...teacherNotices.value)
  for (const n of all) {
    const k = parseDayKeyFromDateTime(n?.publishTime)
    if (k) set.add(k)
  }
  return set
})

function hasNoticeDay(dayKey) {
  return markedDays.value.has(String(dayKey))
}

function padToFive(list) {
  const arr = Array.isArray(list) ? list : []
  const out = arr.slice(0, 5)
  while (out.length < 5) out.push(null)
  return out
}

function normalizeNotices(v) {
  if (Array.isArray(v)) return v
  if (!v || typeof v !== 'object') return []
  const values = Object.values(v)
  const arr = []
  for (const x of values) {
    if (Array.isArray(x)) arr.push(...x)
    else if (x && typeof x === 'object') arr.push(x)
  }
  return arr
}

function openNotice(n) {
  currentNotice.value = n || null
  noticeDialogVisible.value = true
}

async function fetchLatestNotices() {
  loading.value = true
  try {
    const { data } = await http.get('/user/notice/latest')
    const payload = data?.data || {}
    systemNotices.value = normalizeNotices(payload?.systemNotices).slice(0, 5)
    teacherNotices.value = normalizeNotices(payload?.teacherNotices).slice(0, 5)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchLatestNotices()
})
</script>

<style scoped>
.home {
  height: 100%;
}
.grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 14px;
  align-items: start;
}
.left {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.right {
  position: sticky;
  top: 12px;
}
.card {
  background: #ffffff;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 18px 20px;
}
.title-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.title {
  font-size: 16px;
  font-weight: 800;
  color: #111827;
}
.list {
  display: flex;
  flex-direction: column;
}
.item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 10px;
  border-radius: 10px;
  cursor: pointer;
  user-select: none;
}
.item.placeholder {
  cursor: default;
}
.item.placeholder:hover {
  background: transparent;
}
.item.placeholder .item-title,
.item.placeholder .item-time {
  color: #c0c4cc;
  font-weight: 500;
}
.item:hover {
  background: #f5f7fb;
}
.item-title {
  font-size: 13px;
  color: #111827;
  font-weight: 600;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.item-time {
  font-size: 12px;
  color: #6b7280;
  flex: none;
}
.calendar {
  margin-top: -6px;
}
.calendar-card {
  position: relative;
  overflow: hidden;
}
.calendar-card .title-row {
  position: relative;
  z-index: 2;
}
.calendar-card .title {
  text-shadow: 0 1px 4px rgba(255, 255, 255, 0.9), 0 0 10px rgba(255, 255, 255, 1);
}
.calendar-wrap {
  position: relative;
  border-radius: 12px;
  overflow: hidden;
  background: transparent;
}
.calendar-bg {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  opacity: 0.65;
  mask-image: linear-gradient(to bottom, black 0%, black 15%, transparent 85%, transparent 100%);
  -webkit-mask-image: linear-gradient(to bottom, black 0%, black 15%, transparent 85%, transparent 100%);
  pointer-events: none;
  z-index: 0;
}
.calendar-wrap :deep(.el-calendar) {
  position: relative;
  z-index: 2;
  background: transparent;
}
.calendar-wrap :deep(.el-calendar__header) {
  position: relative;
  z-index: 2;
  background: transparent;
}
.calendar-wrap :deep(.el-calendar__title) {
  font-weight: 800;
  text-shadow: 0 1px 4px rgba(255, 255, 255, 0.9), 0 0 10px rgba(255, 255, 255, 1);
}
.calendar-wrap :deep(.el-calendar-table thead th) {
  color: #374151;
  font-weight: 700;
  text-shadow: 0 1px 4px rgba(255, 255, 255, 0.9);
}
.calendar-wrap :deep(.el-calendar__body) {
  position: relative;
  z-index: 2;
  background: transparent;
}
.calendar :deep(.el-calendar-day) {
  position: relative;
}
.notice-ring {
  position: absolute;
  left: 50%;
  bottom: 10px;
  transform: translateX(-50%);
  width: 25px;
  height: 25px;
  border-radius: 999px;
  border: 5px solid var(--el-color-primary, #409eff);
  box-sizing: border-box;
  pointer-events: none;
}
.notice-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 10px 18px;
  margin-bottom: 12px;
}
.notice-meta-item {
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
.notice-content {
  white-space: pre-wrap;
  word-break: break-word;
  font-size: 13px;
  color: #111827;
  line-height: 1.65;
}
@media (max-width: 980px) {
  .grid {
    grid-template-columns: 1fr;
  }
  .right {
    position: static;
  }
}
</style>
