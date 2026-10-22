<template>
  <div class="page">
    <div class="card">
      <div class="title">能力评价</div>
      <div class="hint">提示：仅展示我已绑定学生的材料</div>

      <div class="bar">
        <div class="bar-left">
          <el-input v-model="query.studentNo" clearable placeholder="学号" style="width: 180px" @keyup.enter="search" />
          <el-input v-model="query.realName" clearable placeholder="姓名" style="width: 200px" @keyup.enter="search" />
          <el-select v-model="query.materialType" clearable placeholder="材料类型" style="width: 200px">
            <el-option :value="1" label="学习计划" />
            <el-option :value="2" label="进度汇报" />
            <el-option :value="3" label="自我总结" />
          </el-select>
          <el-select v-model="query.evaluated" clearable placeholder="批阅状态" style="width: 160px">
            <el-option :value="0" label="未批阅" />
            <el-option :value="1" label="已批阅" />
          </el-select>
          <el-select v-model="query.majorId" clearable placeholder="专业" style="width: 200px" :loading="majorLoading" @change="onMajorChange">
            <el-option v-for="m in majors" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
          <el-select v-model="query.classId" clearable placeholder="班级" style="width: 200px" :disabled="!query.majorId" :loading="classLoading">
            <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
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
          :fit="false"
          table-layout="fixed"
        >
          <el-table-column prop="studentNo" label="学号" width="150" align="center" show-overflow-tooltip />
          <el-table-column prop="studentRealName" label="姓名" width="150" align="center" show-overflow-tooltip />
          <el-table-column prop="materialType" label="类型" width="150" align="center" show-overflow-tooltip>
            <template #default="{ row }">
              {{ materialTypeLabel(row?.materialType) }}
            </template>
          </el-table-column>
          <el-table-column prop="title" label="标题" width="260" align="center" show-overflow-tooltip />
          <el-table-column prop="submitTime" label="提交时间" width="180" align="center" show-overflow-tooltip />
          <el-table-column prop="evaluated" label="批阅状态" width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="row?.evaluated === 1 ? 'success' : 'info'" effect="light">{{ row?.evaluated === 1 ? '已批阅' : '未批阅' }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="score" label="得分" width="100" align="center" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row?.score ?? '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="evaluationTime" label="批阅时间" width="180" align="center" show-overflow-tooltip />
          <el-table-column label="操作" width="160" fixed="right" align="center">
            <template #default="{ row }">
              <el-button link type="primary" @click="evaluateRow(row)">评价</el-button>
              <el-button link type="info" :disabled="row?.evaluated !== 1 || canceling" @click="cancelRow(row)">取消</el-button>
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
import { onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import http from '../api/http'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const canceling = ref(false)
const majorLoading = ref(false)
const classLoading = ref(false)

const total = ref(0)
const records = ref([])

const majors = ref([])
const classes = ref([])
const teacher = ref(null)

const query = ref({
  classId: undefined,
  evaluated: undefined,
  majorId: undefined,
  materialType: undefined,
  page: 1,
  pageSize: 10,
  realName: '',
  studentNo: ''
})

function materialTypeLabel(t) {
  if (t === 1) return '学习计划'
  if (t === 2) return '进度汇报'
  if (t === 3) return '自我总结'
  return t === 0 ? '0' : t ? String(t) : '-'
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

async function fetchTeacher() {
  try {
    const { data } = await http.get('/teacher')
    teacher.value = data?.data || null
  } catch (_) {
    teacher.value = null
  }
}

async function loadMajors() {
  const deptId = normalizeId(teacher.value?.deptId)
  if (!deptId) {
    majors.value = []
    return
  }
  majorLoading.value = true
  try {
    const { data } = await http.get(`/school-hierarchy/colleges/${deptId}/majors`)
    const arr = asArray(data?.data)
    majors.value = arr.map((x) => ({ id: normalizeId(x?.id), name: getName(x) })).filter((x) => x.id && x.name)
  } finally {
    majorLoading.value = false
  }
}

async function loadClasses(majorId) {
  const id = normalizeId(majorId)
  if (!id) {
    classes.value = []
    return
  }
  classLoading.value = true
  try {
    const { data } = await http.get(`/school-hierarchy/majors/${id}/classes`)
    const arr = asArray(data?.data)
    classes.value = arr.map((x) => ({ id: normalizeId(x?.id), name: getName(x) })).filter((x) => x.id && x.name)
  } finally {
    classLoading.value = false
  }
}

async function fetchPage(toPage = query.value.page) {
  const page = Number(toPage)
  query.value.page = Number.isFinite(page) && page > 0 ? page : 1
  const params = {
    classId: query.value.classId ?? undefined,
    evaluated: query.value.evaluated ?? undefined,
    majorId: query.value.majorId ?? undefined,
    materialType: query.value.materialType ?? undefined,
    page: query.value.page,
    pageSize: query.value.pageSize,
    realName: (query.value.realName || '').trim() || undefined,
    studentNo: (query.value.studentNo || '').trim() || undefined
  }
  loading.value = true
  try {
    const { data } = await http.get('/teacher/evaluation/page', { params })
    const pageData = data?.data && (data?.data?.records || data?.data?.total !== undefined) ? data.data : data
    total.value = pageData?.total ?? 0
    records.value = Array.isArray(pageData?.records) ? pageData.records : []
  } finally {
    loading.value = false
  }
}

async function onMajorChange(v) {
  query.value.classId = undefined
  classes.value = []
  if (v) await loadClasses(v)
}

function applyRoutePrefill() {
  const rawStudentNo = route.query?.studentNo
  const rawRealName = route.query?.realName
  const rawEvaluated = route.query?.evaluated
  const studentNo = rawStudentNo !== undefined && rawStudentNo !== null ? String(rawStudentNo).trim() : ''
  const realName = rawRealName !== undefined && rawRealName !== null ? String(rawRealName).trim() : ''
  const evaluated =
    rawEvaluated === undefined || rawEvaluated === null || rawEvaluated === ''
      ? undefined
      : Number(rawEvaluated) === 0
        ? 0
        : Number(rawEvaluated) === 1
          ? 1
          : undefined

  if (!studentNo && !realName && evaluated === undefined) return false

  query.value.studentNo = studentNo
  query.value.realName = realName
  query.value.evaluated = evaluated
  query.value.materialType = undefined
  query.value.majorId = undefined
  query.value.classId = undefined
  classes.value = []
  query.value.page = 1
  return true
}

function search() {
  fetchPage(1)
}

function reset() {
  query.value.studentNo = ''
  query.value.realName = ''
  query.value.evaluated = undefined
  query.value.materialType = undefined
  query.value.majorId = undefined
  query.value.classId = undefined
  fetchPage(1)
}

function onPageChange(p) {
  fetchPage(p)
}

function onSizeChange(s) {
  query.value.pageSize = s
  fetchPage(1)
}

function evaluateRow(row) {
  const id = row?.id ?? row?.materialId ?? row?.material_id
  if (!id) {
    ElMessage.warning('缺少材料ID，无法评价')
    return
  }
  router.push({ path: `/teacher/evaluation/${id}`, query: route.query || {} })
}

async function cancelRow(row) {
  const id = row?.evaluationId ?? row?.evaluation_id ?? row?.id
  if (!id) {
    ElMessage.warning('缺少材料ID，无法取消')
    return
  }
  if (canceling.value) return
  try {
    await ElMessageBox.confirm('确认取消本条操作？', '取消', {
      confirmButtonText: '确认',
      cancelButtonText: '返回',
      type: 'warning'
    })
  } catch (_) {
    return
  }
  canceling.value = true
  try {
    await http.delete('/teacher/evaluation', { params: { id } })
    ElMessage.success('取消成功')
    await fetchPage(1)
  } finally {
    canceling.value = false
  }
}

onMounted(async () => {
  await fetchTeacher()
  await loadMajors()
  applyRoutePrefill()
  await fetchPage(1)
})

watch(
  () => [route.query?.studentNo, route.query?.realName, route.query?.evaluated],
  () => {
    const changed = applyRoutePrefill()
    if (changed) fetchPage(1)
  }
)
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
</style>
