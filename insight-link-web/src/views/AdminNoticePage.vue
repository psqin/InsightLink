<template>
  <div class="page">
    <div class="card">
      <div class="title">通知管理</div>
      <div class="hint">提示：可按发布人姓名、发布时间筛选</div>

      <div class="bar">
        <div class="bar-left">
          <el-input
            v-model="query.publisherRealName"
            clearable
            placeholder="发布人"
            style="width: 180px"
            @keyup.enter="search"
          />
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
            <el-button type="success" :disabled="loading" @click="openCreate">发布通知</el-button>
          </div>
        </div>
      </div>

      <div class="table-wrap">
        <el-table
          :data="records"
          row-key="id"
          style="width: 100%"
          :empty-text="loading ? '加载中...' : '暂无数据'"
          v-loading="loading"
          :fit="true"
          table-layout="fixed"
        >
          <el-table-column prop="title" label="标题" min-width="260" align="center" show-overflow-tooltip />
          <el-table-column label="发布人" min-width="160" align="center" show-overflow-tooltip>
            <template #default="{ row }">
              <span
                class="click-name"
                role="button"
                tabindex="0"
                @click="openUser(row)"
                @keydown.enter.prevent="openUser(row)"
                @keydown.space.prevent="openUser(row)"
              >
                {{ row?.publisherRealName || '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="publishTime" label="发布时间" min-width="200" align="center" show-overflow-tooltip />
          <el-table-column prop="type" label="类型" min-width="140" align="center">
            <template #default="{ row }">
              <el-tag effect="light" :type="row?.type === 2 ? 'success' : 'info'">{{ noticeTypeLabel(row?.type) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="240" fixed="right" align="center">
            <template #default="{ row }">
              <el-button link type="primary" @click="openView(row)">查看</el-button>
              <el-button link type="warning" @click="openEdit(row)">修改</el-button>
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

    <el-dialog v-model="detailVisible" title="查看通知" width="720px">
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input :model-value="current?.title || ''" disabled />
        </el-form-item>
        <el-form-item label="发布人">
          <el-input :model-value="current?.publisherRealName || ''" disabled />
        </el-form-item>
        <el-form-item label="发布时间">
          <el-input :model-value="current?.publishTime || ''" disabled />
        </el-form-item>
        <el-form-item label="内容">
          <el-input :model-value="current?.content || ''" type="textarea" :rows="8" disabled />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="detailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="createVisible" title="发布通知" width="720px">
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

    <el-dialog v-model="editVisible" title="修改通知" width="720px">
      <el-form label-position="top">
        <el-form-item label="标题">
          <el-input v-model="editForm.title" :disabled="editSaving" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input
            v-model="editForm.content"
            type="textarea"
            :rows="6"
            maxlength="2000"
            show-word-limit
            :disabled="editSaving"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button :disabled="editSaving" @click="editVisible = false">取消</el-button>
        <el-button type="primary" :loading="editSaving" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../api/http'

const router = useRouter()
const loading = ref(false)
const deleting = ref(false)

const query = ref({
  beginDate: '',
  endDate: '',
  page: 1,
  pageSize: 10,
  publisherRealName: ''
})

const total = ref(0)
const records = ref([])

const detailVisible = ref(false)
const current = ref(null)

const createVisible = ref(false)
const createSaving = ref(false)
const createForm = ref({ title: '', content: '' })

const editVisible = ref(false)
const editSaving = ref(false)
const editId = ref(null)
const editForm = ref({ title: '', content: '' })

function noticeTypeLabel(t) {
  if (t === 1) return '系统通知'
  if (t === 2) return '导师通知'
  return t === 0 ? '0' : t ? String(t) : '-'
}

function asArray(v) {
  if (Array.isArray(v)) return v
  if (Array.isArray(v?.records)) return v.records
  return []
}

async function fetchPage(toPage = query.value.page) {
  const page = Number(toPage)
  query.value.page = Number.isFinite(page) && page > 0 ? page : 1

  const params = {
    beginDate: query.value.beginDate || undefined,
    endDate: query.value.endDate || undefined,
    page: query.value.page,
    pageSize: query.value.pageSize,
    publisherRealName: (query.value.publisherRealName || '').trim() || undefined
  }

  loading.value = true
  try {
    const { data } = await http.get('/admin/notice/page', { params })
    const pageData = data?.data || {}
    total.value = Number(pageData?.total || 0)
    records.value = asArray(pageData?.records)
  } finally {
    loading.value = false
  }
}

function search() {
  if (loading.value) return
  fetchPage(1)
}

function reset() {
  if (loading.value) return
  query.value.publisherRealName = ''
  query.value.beginDate = ''
  query.value.endDate = ''
  fetchPage(1)
}

function onPageChange(p) {
  fetchPage(p)
}

function onSizeChange() {
  fetchPage(1)
}

function openView(row) {
  current.value = row || null
  detailVisible.value = true
}

function openCreate() {
  createForm.value.title = ''
  createForm.value.content = ''
  createVisible.value = true
}

function openUser(row) {
  const userId = row?.userId
  if (!userId && userId !== 0) return
  router.push(`/admin/user/${userId}`)
}

function openEdit(row) {
  const id = row?.id
  if (!id && id !== 0) return
  editId.value = id
  editForm.value.title = row?.title ?? ''
  editForm.value.content = row?.content ?? ''
  editVisible.value = true
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
    await fetchPage(1)
  } finally {
    createSaving.value = false
  }
}

async function saveEdit() {
  const id = editId.value
  if (!id && id !== 0) return

  const payload = {
    title: (editForm.value.title || '').trim(),
    content: (editForm.value.content || '').trim()
  }

  if (!payload.title) {
    ElMessage.warning('请填写标题')
    return
  }
  if (!payload.content) {
    ElMessage.warning('请填写内容')
    return
  }
  if (editSaving.value) return

  editSaving.value = true
  try {
    await http.put(`/admin/notice/${id}`, payload)
    ElMessage.success('保存成功')
    editVisible.value = false
    await fetchPage(query.value.page)
  } finally {
    editSaving.value = false
  }
}

async function deleteOne(row) {
  const id = row?.id
  if (!id && id !== 0) return
  if (deleting.value) return
  try {
    await ElMessageBox.confirm('确认删除该通知？此操作不可恢复。', '删除通知', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch (_) {
    return
  }
  deleting.value = true
  try {
    try {
      await http.delete(`/admin/notice/${id}`)
    } catch (e) {
      await http.delete('/admin/notice', { params: { id } })
    }
    ElMessage.success('删除成功')
    const nextPage = records.value.length <= 1 && query.value.page > 1 ? query.value.page - 1 : query.value.page
    await fetchPage(nextPage)
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  fetchPage(1)
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
.title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}
.hint {
  margin-top: 6px;
  font-size: 12px;
  color: #6b7280;
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
.click-name {
  cursor: pointer;
  color: #111827;
  user-select: none;
}
.click-name:hover {
  color: var(--el-color-primary);
}
.click-name:focus-visible {
  outline: 0;
  box-shadow: 0 0 0 3px rgba(64, 158, 255, 0.22);
  border-radius: 6px;
}
</style>
