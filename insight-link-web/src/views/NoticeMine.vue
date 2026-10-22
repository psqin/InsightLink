<template>
  <div class="page">
    <div class="layout">
      <div class="card left-card">
        <div class="title">我发布的通知</div>

        <div class="bar">
          <div class="bar-left">
            <el-input v-model="query.title" clearable placeholder="标题查询" style="width: 180px" @keyup.enter="search" />
            <el-date-picker
              v-model="query.beginDate"
              type="date"
              placeholder="开始日期"
              value-format="YYYY-MM-DD"
              style="width: 180px"
            />
            <el-date-picker
              v-model="query.endDate"
              type="date"
              placeholder="结束日期"
              value-format="YYYY-MM-DD"
              style="width: 180px"
            />
            <div class="bar-actions">
              <el-button type="primary" :loading="loading" @click="search">查询</el-button>
              <el-button :disabled="loading" @click="reset">重置</el-button>
              <el-button type="success" :disabled="loading" @click="openCreate">新增通知</el-button>
            </div>
          </div>
        </div>

        <div class="table-wrap">
          <el-table
            :data="items"
            row-key="id"
            style="width: 100%"
            :empty-text="loading ? '加载中...' : '暂无数据'"
            v-loading="loading"
            :fit="true"
            table-layout="fixed"
          >
            <el-table-column prop="title" label="标题" min-width="260" align="center" show-overflow-tooltip />
            <el-table-column prop="publishTime" label="发布时间" min-width="200" align="center" show-overflow-tooltip />
            <el-table-column prop="type" label="类型" min-width="140" align="center">
              <template #default="{ row }">
                <el-tag effect="light" :type="row?.type === 2 ? 'success' : 'info'">{{ noticeTypeLabel(row?.type) }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" min-width="200" fixed="right" align="center">
              <template #default="{ row }">
                <el-button link type="primary" @click="openView(row)">查看</el-button>
                <el-button link type="warning" @click="openEdit(row)">编辑</el-button>
                <el-button link type="danger" :disabled="deleting" @click="deleteOne(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="pager">
            <el-pagination
              layout="total, sizes, prev, pager, next, jumper"
              :total="total"
              v-model:current-page="query.page"
              v-model:page-size="query.pageSize"
              :page-sizes="[10, 20, 50, 100]"
              :disabled="loading"
              @current-change="onPageChange"
              @size-change="onSizeChange"
            />
          </div>
        </div>
      </div>

      <div class="card right-card">
        <img class="calendar-bg" src="https://psqin001.oss-cn-beijing.aliyuncs.com/a2c30f4e-df6b-4204-b620-e5d6aa908929.jpg" alt="今日节日" />
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

    <el-dialog v-model="detailVisible" :title="detailMode === 'edit' ? '编辑通知' : '查看通知'" width="720px">
      <el-skeleton :loading="detailLoading" animated>
        <template #template>
          <el-skeleton-item variant="h1" style="width: 240px" />
          <el-skeleton-item variant="text" style="margin-top: 12px" />
          <el-skeleton-item variant="rect" style="margin-top: 14px; height: 160px" />
        </template>
        <template #default>
          <el-form label-position="top">
            <el-form-item label="标题">
              <el-input v-model="detailForm.title" :disabled="detailMode !== 'edit' || detailSaving" />
            </el-form-item>
            <el-form-item label="内容">
              <el-input
                v-model="detailForm.content"
                type="textarea"
                :rows="6"
                maxlength="2000"
                show-word-limit
                :disabled="detailMode !== 'edit' || detailSaving"
              />
            </el-form-item>
          </el-form>
        </template>
      </el-skeleton>

      <template #footer>
        <el-button :disabled="detailSaving" @click="detailVisible = false">关闭</el-button>
        <el-button v-if="detailMode === 'edit'" type="primary" :loading="detailSaving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="createVisible" title="新增通知" width="720px">
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="createForm.title" :disabled="createSaving" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input
            v-model="createForm.content"
            type="textarea"
            :rows="6"
            maxlength="2000"
            show-word-limit
            :disabled="createSaving"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button :disabled="createSaving" @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="createSaving" @click="createOne">发布</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../api/http'

const loading = ref(false)
const deleting = ref(false)

const query = ref({
  beginDate: '',
  endDate: '',
  page: 1,
  pageSize: 10,
  title: ''
})

const total = ref(0)
const items = ref([])

const calendarDate = ref(new Date())
const calendarItems = ref([])

const detailVisible = ref(false)
const detailMode = ref('view')
const detailLoading = ref(false)
const detailSaving = ref(false)
const currentId = ref(null)
const detailForm = ref({ title: '', content: '' })

const createVisible = ref(false)
const createSaving = ref(false)
const createForm = ref({ title: '', content: '' })

function noticeTypeLabel(t) {
  if (t === 1) return '系统通知'
  if (t === 2) return '导师通知'
  return t === 0 ? '0' : t ? String(t) : '-'
}

function parseDayKeyFromDateTime(v) {
  if (!v) return ''
  const s = String(v).trim()
  const m = s.match(/^(\d{4}-\d{2}-\d{2})/)
  return m ? m[1] : ''
}

function formatDayKey(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function monthRangeOf(d) {
  const y = d.getFullYear()
  const m = d.getMonth()
  const start = new Date(y, m, 1)
  const end = new Date(y, m + 1, 0)
  return { begin: formatDayKey(start), end: formatDayKey(end) }
}

function dayText(dayKey) {
  const parts = String(dayKey).split('-')
  const d = parts[2]
  return d ? String(Number(d)) : ''
}

const markedDays = computed(() => {
  const set = new Set()
  for (const n of calendarItems.value || []) {
    const k = parseDayKeyFromDateTime(n?.publishTime)
    if (k) set.add(k)
  }
  return set
})

function hasNoticeDay(dayKey) {
  return markedDays.value.has(String(dayKey))
}

async function fetchList(toPage = query.value.page) {
  const page = Number(toPage)
  query.value.page = Number.isFinite(page) && page > 0 ? page : 1
  const params = {
    title: (query.value.title || '').trim() || undefined,
    beginDate: query.value.beginDate || undefined,
    endDate: query.value.endDate || undefined,
    page: query.value.page,
    pageSize: query.value.pageSize
  }
  loading.value = true
  try {
    const { data } = await http.get('/teacher/notice/mine', { params })
    const pageData = data?.data && (data?.data?.records || data?.data?.total !== undefined) ? data.data : data
    total.value = pageData?.total ?? 0
    items.value = Array.isArray(pageData?.records) ? pageData.records : []
  } finally {
    loading.value = false
  }
}

async function fetchCalendarForMonth(dateObj = calendarDate.value) {
  const baseDate = dateObj instanceof Date ? dateObj : new Date()
  const { begin, end } = monthRangeOf(baseDate)
  const params = {
    title: (query.value.title || '').trim() || undefined,
    beginDate: begin,
    endDate: end,
    page: 1,
    pageSize: 1000
  }
  const { data } = await http.get('/teacher/notice/mine', { params })
  const pageData = data?.data && (data?.data?.records || data?.data?.total !== undefined) ? data.data : data
  calendarItems.value = Array.isArray(pageData?.records) ? pageData.records : []
}

function search() {
  fetchList(1)
}

function reset() {
  query.value.title = ''
  query.value.beginDate = ''
  query.value.endDate = ''
  fetchList(1)
}

function onPageChange(p) {
  fetchList(p)
}

function onSizeChange(s) {
  query.value.pageSize = s
  fetchList(1)
}

function openCreate() {
  createForm.value.title = ''
  createForm.value.content = ''
  createVisible.value = true
}

async function createOne() {
  const payload = {
    title: (createForm.value.title || '').trim(),
    content: (createForm.value.content || '').trim()
  }
  if (!payload.title) {
    ElMessage.warning('请填写标题')
    return
  }
  if (!payload.content) {
    ElMessage.warning('请填写内容')
    return
  }
  if (createSaving.value) return
  createSaving.value = true
  try {
    await http.post('/teacher/notice', payload)
    ElMessage.success('发布成功')
    createVisible.value = false
    await fetchList(1)
    await fetchCalendarForMonth()
  } finally {
    createSaving.value = false
  }
}

async function fetchDetail(id) {
  detailLoading.value = true
  try {
    const { data } = await http.get(`/teacher/notice/${id}`)
    const payload = data?.data ?? null
    detailForm.value.title = payload?.title ?? ''
    detailForm.value.content = payload?.content ?? ''
  } finally {
    detailLoading.value = false
  }
}

async function openView(row) {
  const id = row?.id
  if (!id) return
  detailMode.value = 'view'
  currentId.value = id
  detailVisible.value = true
  await fetchDetail(id)
}

async function openEdit(row) {
  const id = row?.id
  if (!id) return
  detailMode.value = 'edit'
  currentId.value = id
  detailVisible.value = true
  await fetchDetail(id)
}

async function saveEdit() {
  const id = currentId.value
  if (!id) return
  const payload = {
    title: (detailForm.value.title || '').trim(),
    content: (detailForm.value.content || '').trim()
  }
  if (!payload.title) {
    ElMessage.warning('请填写标题')
    return
  }
  if (!payload.content) {
    ElMessage.warning('请填写内容')
    return
  }
  detailSaving.value = true
  try {
    await http.put(`/teacher/notice/${id}`, payload)
    ElMessage.success('保存成功')
    detailVisible.value = false
    await fetchList(query.value.page)
    await fetchCalendarForMonth()
  } finally {
    detailSaving.value = false
  }
}

async function deleteOne(row) {
  const id = row?.id
  if (!id) return
  if (deleting.value) return
  try {
    await ElMessageBox.confirm('确认删除该通知？', '删除通知', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch (_) {
    return
  }
  deleting.value = true
  try {
    await http.delete(`/teacher/notice/${id}`)
    ElMessage.success('删除成功')
    await fetchList(1)
    await fetchCalendarForMonth()
  } finally {
    deleting.value = false
  }
}

const calendarMonthKey = computed(() => {
  const d = calendarDate.value instanceof Date ? calendarDate.value : new Date()
  return `${d.getFullYear()}-${d.getMonth()}`
})

watch(
  () => calendarMonthKey.value,
  async () => {
    await fetchCalendarForMonth(calendarDate.value)
  }
)

onMounted(async () => {
  await fetchList(1)
  await fetchCalendarForMonth()
})
</script>

<style scoped>
.page {
  height: 100%;
}
.layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 380px;
  gap: 14px;
  align-items: start;
}
.right-card {
  position: sticky;
  top: 12px;
  overflow: hidden;
}
.right-card .title-row {
  position: relative;
  z-index: 2;
}
.right-card .title {
  text-shadow: 0 1px 4px rgba(255, 255, 255, 0.9), 0 0 10px rgba(255, 255, 255, 1);
}
.card {
  background: #ffffff;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 18px 20px;
}
.title {
  font-size: 16px;
  font-weight: 800;
  color: #111827;
}
.title-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}
.bar {
  margin-top: 14px;
}
.bar-left {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.bar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}
.table-wrap {
  margin-top: 14px;
  overflow-x: auto;
}
.pager {
  margin-top: 14px;
  display: flex;
  justify-content: flex-end;
}
.calendar {
  margin-top: -6px;
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
@media (max-width: 980px) {
  .layout {
    grid-template-columns: 1fr;
  }
  .right-card {
    position: static;
  }
}
</style>
