<template>
  <div class="page">
    <div class="card">
      <div class="title">导师管理</div>
      <div class="hint">提示：支持姓名、工号、学校、院系、职称等条件查询</div>

      <div class="bar">
        <div class="bar-left">
          <el-input v-model="query.realName" clearable placeholder="姓名" style="width: 140px" @keyup.enter="search" />
          <el-input v-model="query.teacherNo" clearable placeholder="工号" style="width: 140px" @keyup.enter="search" />
          <el-input v-model="query.title" clearable placeholder="职称" style="width: 140px" @keyup.enter="search" />
          <el-select
            v-model="query.universityId"
            filterable
            remote
            reserve-keyword
            :remote-method="searchUniversities"
            :loading="universityLoading"
            clearable
            placeholder="学校"
            style="width: 140px"
            @change="onUniversityChange"
          >
            <el-option v-for="u in universities" :key="u.id" :label="u.name" :value="u.id" />
          </el-select>
          <el-select
            v-model="query.deptId"
            filterable
            clearable
            placeholder="院系"
            style="width: 140px"
            :disabled="!query.universityId"
            :loading="deptLoading"
          >
            <el-option v-for="d in depts" :key="d.id" :label="d.name" :value="d.id" />
          </el-select>
          <div class="bar-actions">
            <el-button type="primary" :loading="loading" @click="search">搜索</el-button>
            <el-button :disabled="loading" @click="reset">重置</el-button>
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
        >
          <el-table-column prop="teacherNo" label="工号" min-width="140" align="center" show-overflow-tooltip />
          <el-table-column label="头像" width="88" align="center">
            <template #default="{ row }">
              <el-avatar :size="34" :src="normalizeUrl(row?.avatar)">{{ avatarFallback(row?.realName) }}</el-avatar>
            </template>
          </el-table-column>
          <el-table-column label="姓名" min-width="140" align="center" show-overflow-tooltip>
            <template #default="{ row }">
              <span
                class="click-name"
                role="button"
                tabindex="0"
                @click="openUser(row)"
                @keydown.enter.prevent="openUser(row)"
                @keydown.space.prevent="openUser(row)"
              >
                {{ row?.realName || '-' }}
              </span>
            </template>
          </el-table-column>
          <el-table-column prop="gender" label="性别" min-width="100" align="center">
            <template #default="{ row }">
              {{ genderLabel(row?.gender) }}
            </template>
          </el-table-column>
          <el-table-column prop="title" label="职称" min-width="140" align="center" show-overflow-tooltip />
          <el-table-column prop="universityName" label="学校" min-width="160" align="center" show-overflow-tooltip />
          <el-table-column prop="deptName" label="院系" min-width="160" align="center" show-overflow-tooltip />
          <el-table-column prop="phone" label="手机号" min-width="140" align="center" show-overflow-tooltip />
          <el-table-column prop="email" label="邮箱" min-width="180" align="center" show-overflow-tooltip />
          <el-table-column label="研究领域" min-width="240" align="center" show-overflow-tooltip>
            <template #default="{ row }">{{ row?.researchField || '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right" align="center">
            <template #default="{ row }">
              <el-button link type="warning" @click="openEdit(row)">修改</el-button>
              <el-button link type="danger" :disabled="deleting" @click="removeRow(row)">删除</el-button>
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
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '../api/http'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const deleting = ref(false)
const records = ref([])
const total = ref(0)

const query = ref({
  realName: '',
  teacherNo: '',
  title: '',
  universityId: undefined,
  deptId: undefined,
  page: 1,
  pageSize: 10
})

const universityLoading = ref(false)
const deptLoading = ref(false)
const universities = ref([])
const depts = ref([])

function normalizeId(v) {
  if (v === undefined || v === null || v === '') return undefined
  const n = Number(v)
  return Number.isFinite(n) ? n : v
}
function getName(x) {
  return x?.name ?? x?.universityName ?? x?.deptName ?? ''
}
function asArray(v) {
  if (Array.isArray(v)) return v
  if (Array.isArray(v?.records)) return v.records
  if (Array.isArray(v?.list)) return v.list
  if (Array.isArray(v?.items)) return v.items
  if (Array.isArray(v?.rows)) return v.rows
  return []
}
function normalizeUrl(a) {
  if (!a) return ''
  const s = String(a).trim().replace(/`/g, '').trim()
  return s
}
function avatarFallback(name) {
  const s = (name || '').trim()
  return s ? s.slice(0, 1) : 'T'
}
function genderLabel(v) {
  const n = Number(v)
  if (n === 1) return '男'
  if (n === 2) return '女'
  if (n === 0) return '保密'
  return '-'
}

function openEdit(row) {
  const id = row?.id
  if (!id && id !== 0) return
  router.push(`/admin/teacher/${id}/edit`)
}

function openUser(row) {
  const userId = row?.userId
  if (!userId && userId !== 0) return
  router.push(`/admin/user/${userId}`)
}

async function removeRow(row) {
  const id = row?.id
  if (!id && id !== 0) return
  try {
    await ElMessageBox.confirm('确认删除该导师？此操作不可恢复。', '确认删除', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch (_) {
    return
  }
  deleting.value = true
  try {
    await http.delete(`/admin/teacher/${id}`)
    ElMessage.success('删除成功')
    const nextPage = records.value.length <= 1 && query.value.page > 1 ? query.value.page - 1 : query.value.page
    await fetchPage(nextPage)
  } finally {
    deleting.value = false
  }
}

async function searchUniversities(keyword) {
  const q = (keyword || '').trim()
  if (!q) return
  universityLoading.value = true
  try {
    const { data } = await http.get('/school-hierarchy/universities/search', { params: { name: q } })
    const arr = asArray(data?.data)
    universities.value = arr.map((x) => ({ id: normalizeId(x?.id), name: getName(x) })).filter((x) => x.id && x.name)
  } finally {
    universityLoading.value = false
  }
}

async function loadDepts(universityId) {
  const id = normalizeId(universityId)
  if (!id) return
  deptLoading.value = true
  try {
    const { data } = await http.get(`/school-hierarchy/universities/${id}/colleges`)
    const arr = asArray(data?.data)
    depts.value = arr.map((x) => ({ id: normalizeId(x?.id), name: getName(x) })).filter((x) => x.id && x.name)
  } finally {
    deptLoading.value = false
  }
}

async function onUniversityChange(v) {
  query.value.deptId = undefined
  depts.value = []
  if (v) await loadDepts(v)
}

async function fetchPage(page = query.value.page) {
  const params = {
    realName: (query.value.realName || '').trim() || undefined,
    teacherNo: (query.value.teacherNo || '').trim() || undefined,
    title: (query.value.title || '').trim() || undefined,
    universityId: query.value.universityId ?? undefined,
    deptId: query.value.deptId ?? undefined,
    page: page,
    pageSize: query.value.pageSize
  }
  loading.value = true
  try {
    const { data } = await http.get('/admin/teacher/page', { params })
    const pageData = data?.data || {}
    records.value = asArray(pageData?.records)
    total.value = Number(pageData?.total || 0)
    query.value.page = page
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
  query.value.realName = ''
  query.value.teacherNo = ''
  query.value.title = ''
  query.value.universityId = undefined
  query.value.deptId = undefined
  depts.value = []
  fetchPage(1)
}

function onPageChange(p) {
  fetchPage(p)
}

function onSizeChange(s) {
  fetchPage(1)
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
