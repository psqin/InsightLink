<template>
  <div class="page">
    <div class="card">
      <div class="title">院系 / 专业 / 班级管理</div>
      <div class="hint">按类型与所属学校筛选，支持新增、修改、删除</div>
      <div class="bar">
        <div class="bar-left">
          <el-select v-model="deptQuery.deptType" placeholder="类型" style="width: 160px">
            <el-option :value="1" label="学院" />
            <el-option :value="2" label="专业" />
            <el-option :value="3" label="班级" />
          </el-select>
          <el-select
            v-model="deptQuery.universityId"
            clearable
            filterable
            remote
            reserve-keyword
            placeholder="学校名称"
            style="width: 180px"
            :remote-method="remoteSearchUniversities"
            :loading="univSearchLoading"
            @change="onDeptSchoolChange"
          >
            <el-option v-for="u in univOptions" :key="u.id" :value="u.id" :label="u.name" />
          </el-select>
          <el-input v-model="deptQuery.name" clearable placeholder="名称" style="width: 180px" @keyup.enter="fetchDeptPage(1)" />
          <template v-if="deptQuery.deptType === 2 || deptQuery.deptType === 3">
            <el-select v-model="deptQuery.collegeId" clearable placeholder="学院" style="width: 180px" @change="onDeptCollegeChange">
              <el-option v-for="c in collegesForSchool" :key="c.id" :value="c.id" :label="c.name" />
            </el-select>
          </template>
          <template v-if="deptQuery.deptType === 3">
            <el-select v-model="deptQuery.majorId" clearable placeholder="专业" style="width: 180px">
              <el-option v-for="m in majorsForCollege" :key="m.id" :value="m.id" :label="m.name" />
            </el-select>
          </template>
          <div class="bar-actions">
            <el-button type="primary" :loading="deptLoading" @click="fetchDeptPage(1)">查询</el-button>
            <el-button :disabled="deptLoading" @click="resetDeptQuery">重置</el-button>
            <el-button type="success" :disabled="deptLoading" @click="openDeptCreate">新增条目</el-button>
          </div>
        </div>
      </div>
      <div class="table-wrap">
        <el-table
          :data="deptRecords"
          row-key="id"
          style="width: 100%"
          :empty-text="deptLoading ? '加载中...' : '暂无数据'"
          v-loading="deptLoading"
          table-layout="fixed"
          :fit="true"
        >
          <el-table-column prop="name" label="名称" min-width="220" align="center" show-overflow-tooltip />
          <el-table-column label="类型" width="120" align="center">
            <template #default="{ row }">{{ deptTypeLabel(row?.deptType) }}</template>
          </el-table-column>
          <el-table-column prop="universityName" label="所属学校" min-width="220" align="center" show-overflow-tooltip>
            <template #default="{ row }">{{ row?.universityName || universityNameById(row?.universityId) }}</template>
          </el-table-column>
          <el-table-column prop="parentName" label="上级名称" min-width="220" align="center" show-overflow-tooltip>
            <template #default="{ row }">{{ row?.parentName || parentNameFallback(row) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right" align="center">
            <template #default="{ row }">
              <el-button link type="warning" @click="openDeptEdit(row)">编辑</el-button>
              <el-button link type="danger" :disabled="deptDeleting" @click="deleteDept(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
        <div class="pager">
          <el-pagination
            layout="total, sizes, prev, pager, next, jumper"
            :total="deptTotal"
            v-model:current-page="deptQuery.page"
            v-model:page-size="deptQuery.pageSize"
            :page-sizes="[10, 20, 50, 100]"
            :disabled="deptLoading"
            @current-change="onDeptPageChange"
            @size-change="onDeptSizeChange"
          />
        </div>
      </div>
    </div>

    <el-dialog v-model="deptEditVisible" :title="deptEditMode === 'create' ? '新增条目' : '编辑条目'" width="560px" :close-on-click-modal="false">
      <el-form label-width="90px">
        <el-form-item label="类型">
          <el-radio-group v-model="deptEditForm.deptType">
            <el-radio :value="1">学院</el-radio>
            <el-radio :value="2">专业</el-radio>
            <el-radio :value="3">班级</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="名称"><el-input v-model="deptEditForm.name" placeholder="请输入名称" /></el-form-item>
        <el-form-item label="学校">
          <el-select
            v-model="deptEditForm.universityId"
            filterable
            remote
            reserve-keyword
            placeholder="学校名称"
            style="width: 100%"
            :remote-method="remoteSearchUniversities"
            :loading="univSearchLoading"
            @change="onDeptEditSchoolChange"
          >
            <el-option v-for="u in univOptions" :key="u.id" :value="u.id" :label="u.name" />
          </el-select>
        </el-form-item>
        <template v-if="deptEditForm.deptType === 2 || deptEditForm.deptType === 3">
          <el-form-item label="学院">
            <el-select v-model="deptEditForm.collegeId" clearable placeholder="请选择学院" style="width: 100%" @change="onDeptEditCollegeChange">
              <el-option v-for="c in collegesForEdit" :key="c.id" :value="c.id" :label="c.name" />
            </el-select>
          </el-form-item>
        </template>
        <template v-if="deptEditForm.deptType === 3">
          <el-form-item label="专业">
            <el-select v-model="deptEditForm.majorId" clearable placeholder="请选择专业" style="width: 100%">
              <el-option v-for="m in majorsForEdit" :key="m.id" :value="m.id" :label="m.name" />
            </el-select>
          </el-form-item>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="deptEditVisible = false">取消</el-button>
        <el-button type="primary" :loading="deptSaving" @click="saveDeptEdit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import http from '../api/http'
import { ElMessage, ElMessageBox } from 'element-plus'

const univOptions = ref([])
const univSearchLoading = ref(false)

function normalizeToArray(v) {
  if (Array.isArray(v)) return v
  if (Array.isArray(v?.records)) return v.records
  if (Array.isArray(v?.data)) return v.data
  return []
}

function ensureUniversityOption(u) {
  if (!u?.id) return
  const exists = univOptions.value.some((x) => x?.id === u.id)
  if (!exists) {
    univOptions.value = [{ id: u.id, name: u.name || String(u.id), code: u.code }, ...univOptions.value]
  }
}

function universityNameById(id) {
  if (!id && id !== 0) return '-'
  const item = univOptions.value.find((x) => x?.id === id)
  return item?.name || String(id)
}

async function remoteSearchUniversities(keyword) {
  const name = (keyword || '').trim()
  if (!name) {
    univOptions.value = []
    return
  }
  univSearchLoading.value = true
  try {
    const { data } = await http.get('/school-hierarchy/universities/search', { params: { name } })
    const list = normalizeToArray(data?.data)
    univOptions.value = list.map((u) => ({ id: u?.id, name: u?.name, code: u?.code })).filter((u) => u?.id || u?.id === 0)
  } finally {
    univSearchLoading.value = false
  }
}

const deptQuery = ref({
  deptType: 1,
  name: '',
  universityId: undefined,
  collegeId: undefined,
  majorId: undefined,
  page: 1,
  pageSize: 10
})
const deptLoading = ref(false)
const deptTotal = ref(0)
const deptRecords = ref([])
const deptDeleting = ref(false)
const deptSaving = ref(false)

const collegesForSchool = ref([])
const majorsForCollege = ref([])

function deptTypeLabel(t) {
  if (t === 1) return '学院'
  if (t === 2) return '专业'
  if (t === 3) return '班级'
  return String(t ?? '-')
}

function parentNameFallback(row) {
  if (row?.deptType === 2) {
    const item = collegesForSchool.value.find((x) => x?.id === row?.parentId)
    return item?.name || (row?.parentId ?? '-')
  }
  if (row?.deptType === 3) {
    const item = majorsForCollege.value.find((x) => x?.id === row?.parentId)
    return item?.name || (row?.parentId ?? '-')
  }
  return '-'
}

async function fetchDeptPage(toPage = deptQuery.value.page) {
  deptQuery.value.page = Number.isFinite(Number(toPage)) && Number(toPage) > 0 ? Number(toPage) : 1
  const params = {
    deptType: deptQuery.value.deptType,
    name: (deptQuery.value.name || '').trim() || undefined,
    universityId: deptQuery.value.universityId ?? undefined,
    parentId:
      deptQuery.value.deptType === 2
        ? deptQuery.value.collegeId ?? undefined
        : deptQuery.value.deptType === 3
        ? deptQuery.value.majorId ?? undefined
        : undefined,
    page: deptQuery.value.page,
    pageSize: deptQuery.value.pageSize
  }
  deptLoading.value = true
  try {
    const { data } = await http.get('/admin/school-hierarchy/depts/page', { params })
    const pageData = data?.data || {}
    deptTotal.value = pageData?.total ?? 0
    deptRecords.value = Array.isArray(pageData?.records) ? pageData.records : []
  } finally {
    deptLoading.value = false
  }
}

async function fetchCollegesForSchool() {
  if (deptQuery.value.universityId === undefined || deptQuery.value.universityId === null) {
    collegesForSchool.value = []
    return
  }
  const { data } = await http.get(`/school-hierarchy/universities/${deptQuery.value.universityId}/colleges`)
  collegesForSchool.value = normalizeToArray(data?.data)
}

async function fetchMajorsForCollege() {
  if (deptQuery.value.collegeId === undefined || deptQuery.value.collegeId === null) {
    majorsForCollege.value = []
    return
  }
  const { data } = await http.get(`/school-hierarchy/colleges/${deptQuery.value.collegeId}/majors`)
  majorsForCollege.value = normalizeToArray(data?.data)
}

function onDeptSchoolChange() {
  deptQuery.value.collegeId = undefined
  deptQuery.value.majorId = undefined
  fetchCollegesForSchool()
}

function onDeptCollegeChange() {
  deptQuery.value.majorId = undefined
  fetchMajorsForCollege()
}

function resetDeptQuery() {
  deptQuery.value = { deptType: 1, name: '', universityId: undefined, collegeId: undefined, majorId: undefined, page: 1, pageSize: 10 }
  deptRecords.value = []
}

const deptEditVisible = ref(false)
const deptEditMode = ref('create')
const deptEditForm = ref({
  id: undefined,
  deptType: 1,
  name: '',
  universityId: undefined,
  collegeId: undefined,
  majorId: undefined
})
const collegesForEdit = ref([])
const majorsForEdit = ref([])

function openDeptCreate() {
  deptEditMode.value = 'create'
  deptEditForm.value = {
    id: undefined,
    deptType: deptQuery.value.deptType || 1,
    name: '',
    universityId: deptQuery.value.universityId,
    collegeId: deptQuery.value.collegeId,
    majorId: deptQuery.value.majorId
  }
  deptEditVisible.value = true
  if (deptEditForm.value.universityId || deptEditForm.value.universityId === 0) {
    ensureUniversityOption({ id: deptEditForm.value.universityId, name: String(deptEditForm.value.universityId) })
  }
  syncEditParents()
}

async function inferCollegeIdFromMajor(majorId, universityId) {
  if (!majorId || (!universityId && universityId !== 0)) return undefined
  const { data } = await http.get('/admin/school-hierarchy/depts/page', {
    params: { deptType: 2, universityId, page: 1, pageSize: 500 }
  })
  const pageData = data?.data || {}
  const records = Array.isArray(pageData?.records) ? pageData.records : []
  const major = records.find((x) => x?.id === majorId)
  return major?.parentId
}

async function openDeptEdit(row) {
  deptEditMode.value = 'edit'
  deptEditForm.value = {
    id: row?.id,
    deptType: row?.deptType || 1,
    name: row?.name || '',
    universityId: row?.universityId,
    collegeId: row?.deptType === 2 ? row?.parentId : undefined,
    majorId: row?.deptType === 3 ? row?.parentId : undefined
  }
  deptEditVisible.value = true
  if (row?.universityId || row?.universityId === 0) {
    ensureUniversityOption({ id: row.universityId, name: row?.universityName || String(row.universityId) })
  }
  if (deptEditForm.value.deptType === 3 && (deptEditForm.value.universityId || deptEditForm.value.universityId === 0)) {
    try {
      const inferred = await inferCollegeIdFromMajor(deptEditForm.value.majorId, deptEditForm.value.universityId)
      if (inferred || inferred === 0) deptEditForm.value.collegeId = inferred
    } catch {
    }
  }
  syncEditParents()
}

function onDeptEditSchoolChange() {
  deptEditForm.value.collegeId = undefined
  deptEditForm.value.majorId = undefined
  syncEditParents()
}

function onDeptEditCollegeChange() {
  deptEditForm.value.majorId = undefined
  syncEditParents(true)
}

async function syncEditParents(onlyMajors = false) {
  if (!onlyMajors) {
    if (deptEditForm.value.universityId !== undefined && deptEditForm.value.universityId !== null) {
      const { data } = await http.get(`/school-hierarchy/universities/${deptEditForm.value.universityId}/colleges`)
      collegesForEdit.value = normalizeToArray(data?.data)
    } else {
      collegesForEdit.value = []
    }
  }
  if (deptEditForm.value.collegeId !== undefined && deptEditForm.value.collegeId !== null) {
    const { data } = await http.get(`/school-hierarchy/colleges/${deptEditForm.value.collegeId}/majors`)
    majorsForEdit.value = normalizeToArray(data?.data)
  } else {
    majorsForEdit.value = []
  }
}

async function saveDeptEdit() {
  const payload = {
    deptType: deptEditForm.value.deptType,
    name: (deptEditForm.value.name || '').trim(),
    universityId: deptEditForm.value.universityId,
    parentId: deptEditForm.value.deptType === 2 ? deptEditForm.value.collegeId : deptEditForm.value.deptType === 3 ? deptEditForm.value.majorId : undefined
  }
  if (!payload.name) return ElMessage.warning('名称不能为空')
  if (!payload.universityId && payload.universityId !== 0) return ElMessage.warning('请选择学校')
  if (payload.deptType === 2 && !payload.parentId) return ElMessage.warning('请选择学院')
  if (payload.deptType === 3 && !payload.parentId) return ElMessage.warning('请选择专业')
  deptSaving.value = true
  try {
    if (deptEditMode.value === 'create') {
      await http.post('/admin/school-hierarchy/depts', payload)
      ElMessage.success('新增成功')
    } else {
      await http.put(`/admin/school-hierarchy/depts/${deptEditForm.value.id}`, payload)
      ElMessage.success('修改成功')
    }
    deptEditVisible.value = false
    await fetchDeptPage(deptQuery.value.page)
  } finally {
    deptSaving.value = false
  }
}

async function deleteDept(row) {
  if (!row?.id) return
  await ElMessageBox.confirm('确认删除该条目？', '提示', { type: 'warning' })
  deptDeleting.value = true
  try {
    await http.delete(`/admin/school-hierarchy/depts/${row.id}`)
    ElMessage.success('删除成功')
    await fetchDeptPage(deptQuery.value.page)
  } finally {
    deptDeleting.value = false
  }
}

function onDeptPageChange(p) { fetchDeptPage(p) }
function onDeptSizeChange(s) { deptQuery.value.pageSize = s; fetchDeptPage(1) }

watch(() => deptQuery.value.deptType, async () => {
  if (deptQuery.value.deptType === 1) {
    deptQuery.value.collegeId = undefined
    deptQuery.value.majorId = undefined
  }
  if (deptQuery.value.deptType === 2) {
    await fetchCollegesForSchool()
    deptQuery.value.majorId = undefined
  }
  if (deptQuery.value.deptType === 3) {
    await fetchCollegesForSchool()
    await fetchMajorsForCollege()
  }
})

onMounted(async () => {
  await fetchDeptPage(1)
})
</script>

<style scoped>
.page { height: 100%; }
.card {
  background: #ffffff;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 18px 20px;
}
.title { font-size: 18px; font-weight: 600; color: #111827; }
.hint { margin-top: 6px; font-size: 13px; color: #6b7280; }
.bar { display: flex; align-items: center; justify-content: space-between; margin-top: 12px; }
.bar-left { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.bar-actions { display: flex; align-items: center; gap: 10px; }
.table-wrap { margin-top: 10px; }
.pager { margin-top: 10px; display: flex; align-items: center; justify-content: center; }
</style>
