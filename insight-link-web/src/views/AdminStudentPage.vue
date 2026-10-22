<template>
  <div class="page">
    <div class="card">
      <div class="title">学生管理</div>
      <div class="hint">提示：支持姓名、学号、学校等条件查询</div>

      <div class="bar">
        <div class="bar-left">
          <el-input v-model="query.realName" clearable placeholder="姓名" style="width: 140px" @keyup.enter="search" />
          <el-input v-model="query.studentNo" clearable placeholder="学号" style="width: 140px" @keyup.enter="search" />
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
            v-model="query.collegeId"
            filterable
            clearable
            placeholder="学院"
            style="width: 140px"
            :disabled="!query.universityId"
            :loading="collegeLoading"
            @change="onCollegeChange"
          >
            <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <el-select
            v-model="query.majorId"
            filterable
            clearable
            placeholder="专业"
            style="width: 140px"
            :disabled="!query.collegeId"
            :loading="majorLoading"
            @change="onMajorChange"
          >
            <el-option v-for="m in majors" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
          <el-select
            v-model="query.classId"
            filterable
            clearable
            placeholder="班级"
            style="width: 140px"
            :disabled="!query.majorId"
            :loading="classLoading"
          >
            <el-option v-for="cl in classes" :key="cl.id" :label="cl.name" :value="cl.id" />
          </el-select>
          <el-input v-model="query.entryYear" clearable placeholder="入学年份" style="width: 140px" @keyup.enter="search" />
          <el-select v-model="query.bindStatus" clearable placeholder="绑定状态" style="width: 140px">
            <el-option :value="0" label="未绑定" />
            <el-option :value="1" label="已绑定" />
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
          <el-table-column prop="studentNo" label="学号" min-width="140" align="center" show-overflow-tooltip />
          <el-table-column label="头像" width="88" align="center">
            <template #default="{ row }">
              <el-avatar :size="34" :src="normalizeAvatar(row?.avatar)">{{ avatarFallback(row) }}</el-avatar>
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
          <el-table-column prop="universityName" label="学校" min-width="160" align="center" show-overflow-tooltip />
          <el-table-column prop="collegeName" label="学院" min-width="160" align="center" show-overflow-tooltip />
          <el-table-column prop="majorName" label="专业" min-width="160" align="center" show-overflow-tooltip />
          <el-table-column prop="className" label="班级" min-width="160" align="center" show-overflow-tooltip />
          <el-table-column prop="entryYear" label="入学年份" min-width="120" align="center" />
          <el-table-column prop="bindStatus" label="绑定状态" min-width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="row?.bindStatus === 1 ? 'success' : 'info'" effect="light">
                {{ row?.bindStatus === 1 ? '已绑定' : '未绑定' }}
              </el-tag>
            </template>
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

    <el-dialog v-model="editVisible" title="修改学生" width="560px" :close-on-click-modal="false">
      <el-skeleton :loading="detailLoading" animated>
        <el-form label-width="110px" class="edit-form">
          <el-form-item label="学号">
            <el-input :model-value="detail?.studentNo || ''" disabled />
          </el-form-item>
          <el-form-item label="姓名">
            <el-input v-model="editForm.realName" placeholder="请输入姓名" />
          </el-form-item>
          <el-form-item label="入学年份">
            <el-input v-model="editForm.entryYear" placeholder="请输入入学年份" />
          </el-form-item>
          <el-form-item label="绑定状态">
            <el-radio-group v-model="editForm.bindStatus">
              <el-radio :value="0">未绑定</el-radio>
              <el-radio :value="1">已绑定</el-radio>
            </el-radio-group>
          </el-form-item>
        </el-form>
      </el-skeleton>
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
import http from '../api/http'
import { ElMessage, ElMessageBox } from 'element-plus'

const router = useRouter()
const loading = ref(false)
const total = ref(0)
const records = ref([])

const universityLoading = ref(false)
const collegeLoading = ref(false)
const majorLoading = ref(false)
const classLoading = ref(false)

const universities = ref([])
const colleges = ref([])
const majors = ref([])
const classes = ref([])

const query = ref({
  realName: '',
  studentNo: '',
  universityId: undefined,
  collegeId: undefined,
  majorId: undefined,
  classId: undefined,
  entryYear: '',
  bindStatus: undefined,
  page: 1,
  pageSize: 10
})

function genderLabel(v) {
  if (v === 1) return '男'
  if (v === 2) return '女'
  return '保密'
}

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

function normalizeAvatar(a) {
  if (!a) return ''
  const s = String(a).trim().replace(/`/g, '').trim()
  return s
}

function avatarFallback(row) {
  const name = (row?.realName || row?.studentNo || '').trim()
  return name ? name.slice(0, 1) : 'S'
}

function openUser(row) {
  const userId = row?.userId
  if (!userId && userId !== 0) return
  router.push(`/admin/user/${userId}`)
}

async function searchUniversities(q) {
  const keyword = (q || '').trim()
  if (!keyword) return
  universityLoading.value = true
  try {
    const { data } = await http.get('/school-hierarchy/universities/search', { params: { name: keyword } })
    const arr = asArray(data?.data)
    universities.value = arr.map((x) => ({ id: normalizeId(x?.id), name: getName(x) })).filter((x) => x.id && x.name)
  } finally {
    universityLoading.value = false
  }
}

async function loadColleges(universityId) {
  const id = normalizeId(universityId)
  if (!id) return
  collegeLoading.value = true
  try {
    const { data } = await http.get(`/school-hierarchy/universities/${id}/colleges`)
    const arr = asArray(data?.data)
    colleges.value = arr.map((x) => ({ id: normalizeId(x?.id), name: getName(x) })).filter((x) => x.id && x.name)
  } finally {
    collegeLoading.value = false
  }
}

async function loadMajors(collegeId) {
  const id = normalizeId(collegeId)
  if (!id) return
  majorLoading.value = true
  try {
    const { data } = await http.get(`/school-hierarchy/colleges/${id}/majors`)
    const arr = asArray(data?.data)
    majors.value = arr.map((x) => ({ id: normalizeId(x?.id), name: getName(x) })).filter((x) => x.id && x.name)
  } finally {
    majorLoading.value = false
  }
}

async function loadClasses(majorId) {
  const id = normalizeId(majorId)
  if (!id) return
  classLoading.value = true
  try {
    const { data } = await http.get(`/school-hierarchy/majors/${id}/classes`)
    const arr = asArray(data?.data)
    classes.value = arr.map((x) => ({ id: normalizeId(x?.id), name: getName(x) })).filter((x) => x.id && x.name)
  } finally {
    classLoading.value = false
  }
}

async function onUniversityChange(v) {
  query.value.collegeId = undefined
  query.value.majorId = undefined
  query.value.classId = undefined
  colleges.value = []
  majors.value = []
  classes.value = []
  if (v) await loadColleges(v)
}

async function onCollegeChange(v) {
  query.value.majorId = undefined
  query.value.classId = undefined
  majors.value = []
  classes.value = []
  if (v) await loadMajors(v)
}

async function onMajorChange(v) {
  query.value.classId = undefined
  classes.value = []
  if (v) await loadClasses(v)
}

const editVisible = ref(false)
const detailLoading = ref(false)
const editSaving = ref(false)
const deleting = ref(false)
const detail = ref(null)
const editForm = ref({
  realName: '',
  entryYear: '',
  bindStatus: 0
})

async function fetchPage(toPage = query.value.page) {
  const page = Number(toPage)
  query.value.page = Number.isFinite(page) && page > 0 ? page : 1
  const entryYear = normalizeId((query.value.entryYear || '').trim())
  const params = {
    realName: (query.value.realName || '').trim() || undefined,
    studentNo: (query.value.studentNo || '').trim() || undefined,
    universityId: query.value.universityId ?? undefined,
    collegeId: query.value.collegeId ?? undefined,
    majorId: query.value.majorId ?? undefined,
    classId: query.value.classId ?? undefined,
    entryYear: entryYear ?? undefined,
    bindStatus: query.value.bindStatus ?? undefined,
    page: query.value.page,
    pageSize: query.value.pageSize
  }
  loading.value = true
  try {
    const { data } = await http.get('/admin/student/page', { params })
    const pageData = data?.data || {}
    total.value = pageData?.total ?? 0
    records.value = Array.isArray(pageData?.records) ? pageData.records : []
  } finally {
    loading.value = false
  }
}

async function fetchDetail(id) {
  if (!id && id !== 0) return null
  detailLoading.value = true
  try {
    const { data } = await http.get(`/admin/student/${id}`)
    detail.value = data?.data || null
    return detail.value
  } finally {
    detailLoading.value = false
  }
}

async function openEdit(row) {
  const id = row?.id
  if (!id && id !== 0) return
  router.push(`/admin/student/${id}/edit`)
}

async function saveEdit() {
  if (editSaving.value) return
  const id = detail.value?.id
  if (!id && id !== 0) return
  const payload = {
    realName: (editForm.value.realName || '').trim(),
    entryYear: (editForm.value.entryYear || '').trim(),
    bindStatus: editForm.value.bindStatus ?? 0
  }
  editSaving.value = true
  try {
    try {
      await http.put(`/admin/student/${id}`, payload)
    } catch (e) {
      await http.put(`/admin/student/${id}`, { adminStudentUpdateDTO: payload })
    }
    ElMessage.success('保存成功')
    editVisible.value = false
    await fetchPage(query.value.page)
  } finally {
    editSaving.value = false
  }
}

async function removeRow(row) {
  const id = row?.id
  if (!id && id !== 0) return
  try {
    await ElMessageBox.confirm('确认删除该学生？此操作不可恢复。', '确认删除', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch (_) {
    return
  }
  deleting.value = true
  try {
    await http.delete(`/admin/student/${id}`)
    ElMessage.success('删除成功')
    const nextPage = records.value.length <= 1 && query.value.page > 1 ? query.value.page - 1 : query.value.page
    await fetchPage(nextPage)
  } finally {
    deleting.value = false
  }
}

function search() {
  if (loading.value) return
  fetchPage(1)
}

function reset() {
  if (loading.value) return
  query.value.realName = ''
  query.value.studentNo = ''
  query.value.universityId = undefined
  query.value.collegeId = undefined
  query.value.majorId = undefined
  query.value.classId = undefined
  query.value.entryYear = ''
  query.value.bindStatus = undefined
  colleges.value = []
  majors.value = []
  classes.value = []
  fetchPage(1)
}

function onPageChange(p) {
  fetchPage(p)
}

function onSizeChange() {
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
.edit-form {
  padding-top: 8px;
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
