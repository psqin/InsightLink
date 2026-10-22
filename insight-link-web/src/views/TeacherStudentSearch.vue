<template>
  <div class="page">
    <div class="card">
      <div class="title">{{ pageTitle }}</div>
      <div class="hint">{{ pageHint }}</div>

      <div class="bar">
        <div class="bar-left">
          <el-input v-model="query.studentNo" clearable placeholder="学号" style="width: 180px" @keyup.enter="search" />
          <el-input-number v-model="query.entryYear" :min="1900" :max="2100" controls-position="right" placeholder="入学年份" style="width: 180px" />
          <el-select v-model="query.majorId" clearable placeholder="专业" style="width: 200px" :loading="majorLoading" @change="onMajorChange">
            <el-option v-for="m in majors" :key="m.id" :label="m.name" :value="m.id" />
          </el-select>
          <el-select v-model="query.classId" clearable placeholder="班级" style="width: 220px" :disabled="!query.majorId" :loading="classLoading">
            <el-option v-for="c in classes" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <div class="bar-actions">
            <el-button type="primary" :loading="loading" @click="search">搜索</el-button>
            <el-button :disabled="loading || bindingLoading" @click="reset">重置</el-button>
            <el-button
              v-if="actionMode === 'bind'"
              type="success"
              :disabled="!selectedUserIds.length"
              :loading="bindingLoading"
              @click="bindSelected"
            >
              绑定（{{ selectedUserIds.length }}）
            </el-button>
            <el-button
              v-if="actionMode === 'unbind'"
              type="danger"
              :disabled="!selectedUserIds.length"
              :loading="bindingLoading"
              @click="unbindSelected"
            >
              解绑（{{ selectedUserIds.length }}）
            </el-button>
          </div>
        </div>
      </div>

      <div class="table-wrap">
        <el-table
          ref="tableRef"
          :data="records"
          row-key="userId"
          style="width: 100%"
          :empty-text="loading ? '加载中...' : '暂无数据'"
          v-loading="loading"
          :fit="true"
          table-layout="fixed"
          @selection-change="onSelectionChange"
        >
          <el-table-column v-if="actionMode !== 'none'" type="selection" width="46" align="center" :selectable="rowSelectable" />
          <el-table-column prop="studentNo" label="学号" min-width="160" align="center" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row?.studentNo || '-' }}
            </template>
          </el-table-column>
          <el-table-column label="头像" width="76" align="center">
            <template #default="{ row }">
              <el-avatar :size="34" :src="normalizeAvatarUrl(row?.avatar)">
                {{ (row?.realName || row?.studentNo || '').slice(0, 1) }}
              </el-avatar>
            </template>
          </el-table-column>
          <el-table-column prop="realName" label="姓名" min-width="120" align="center" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row?.realName || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="gender" label="性别" min-width="90" align="center" show-overflow-tooltip>
            <template #default="{ row }">
              {{ genderLabel(row?.gender) }}
            </template>
          </el-table-column>
          <el-table-column prop="entryYear" label="入学年份" min-width="120" align="center" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row?.entryYear ? String(row.entryYear) : '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="majorName" label="专业" min-width="160" align="center" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row?.majorName || '-' }}
            </template>
          </el-table-column>
          <el-table-column prop="className" label="班级" min-width="160" align="center" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row?.className || '-' }}
            </template>
          </el-table-column>
          <el-table-column v-if="isMyStudentsPage" prop="bindTime" label="绑定时间" min-width="160" align="center" show-overflow-tooltip>
            <template #default="{ row }">
              {{ row?.bindTime || '-' }}
            </template>
          </el-table-column>
          <el-table-column v-if="actionMode !== 'none'" label="操作" min-width="210" align="center">
            <template #default="{ row }">
              <el-button v-if="isMyStudentsPage" type="primary" link :disabled="bindingLoading" @click="viewOne(row)">查看</el-button>
              <el-button v-if="isMyStudentsPage" type="primary" link :disabled="bindingLoading" @click="evaluateOne(row)">评价</el-button>
              <el-button
                v-if="actionMode === 'bind'"
                type="primary"
                link
                :disabled="bindingLoading || !rowSelectable(row)"
                @click="bindOne(row)"
              >
                绑定
              </el-button>
              <el-button
                v-if="actionMode === 'unbind'"
                type="danger"
                link
                :disabled="bindingLoading || !rowSelectable(row)"
                @click="unbindOne(row)"
              >
                解绑
              </el-button>
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
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import http from '../api/http'
import { ElMessage, ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()

const isMyStudentsPage = computed(() => route?.meta?.mode === 'my-students' || route?.meta?.title === '我的学生')
const actionMode = computed(() => {
  if (isMyStudentsPage.value) return 'unbind'
  return 'bind'
})

const pageTitle = computed(() => (isMyStudentsPage.value ? '我的学生' : '学生查询'))
const pageHint = computed(() =>
  isMyStudentsPage.value ? '提示：查询到的是已绑定到我的学生' : '提示：查询到的是本学校本学院未绑定导师的学生'
)

const loading = ref(false)
const bindingLoading = ref(false)
const majorLoading = ref(false)
const classLoading = ref(false)
const total = ref(0)
const records = ref([])
const tableRef = ref()
const selectedUserIds = ref([])

const majors = ref([])
const classes = ref([])
const teacher = ref(null)

const query = ref({
  classId: undefined,
  entryYear: undefined,
  majorId: undefined,
  page: 1,
  pageSize: 10,
  studentNo: ''
})

function normalizeAvatarUrl(v) {
  const s = String(v ?? '').trim()
  if (!s) return ''
  return s.replace(/`/g, '').trim()
}

function genderLabel(v) {
  const n = Number(v)
  if (n === 1) return '男'
  if (n === 2) return '女'
  return '-'
}

function rowSelectable(row) {
  return !!normalizeId(row?.userId) && !bindingLoading.value
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

function normalizeStudentRecord(r) {
  return {
    id: r?.id,
    userId: r?.userId,
    studentNo: r?.studentNo ?? '',
    realName: r?.realName ?? '',
    entryYear: r?.entryYear,
    majorName: r?.majorName ?? r?.major ?? '',
    className: r?.className ?? r?.clazz ?? '',
    bindTime: r?.createTime ?? r?.bindTime ?? '',
    avatar: r?.avatar,
    gender: r?.gender
  }
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
    entryYear: query.value.entryYear ?? undefined,
    majorId: query.value.majorId ?? undefined,
    page: query.value.page,
    pageSize: query.value.pageSize,
    studentNo: (query.value.studentNo || '').trim() || undefined
  }
  loading.value = true
  try {
    const endpoint = isMyStudentsPage.value ? '/teacher/ts/page' : '/teacher/search'
    const { data } = await http.get(endpoint, { params })
    const pageData = data?.data && (data?.data?.records || data?.data?.total !== undefined) ? data.data : data
    total.value = pageData?.total ?? 0
    const arr = Array.isArray(pageData?.records) ? pageData.records : []
    records.value = arr.map(normalizeStudentRecord)
  } catch (e) {
    ElMessage.error('查询失败')
  } finally {
    loading.value = false
  }
}

function onSelectionChange(selection) {
  if (actionMode.value === 'none') return
  const ids = (selection || [])
    .map((x) => normalizeId(x?.userId))
    .filter((x) => x !== undefined && x !== null && x !== '')
  selectedUserIds.value = Array.from(new Set(ids))
}

async function bindUsers(userIds) {
  if (actionMode.value !== 'bind') return
  const ids = Array.from(new Set((userIds || []).map((x) => normalizeId(x)).filter((x) => x !== undefined && x !== null && x !== '')))
  if (!ids.length) {
    ElMessage.warning('请选择学生')
    return
  }
  if (bindingLoading.value) return
  try {
    await ElMessageBox.confirm(`确认绑定选中的 ${ids.length} 名学生？`, '确认绑定', {
      confirmButtonText: '绑定',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch (_) {
    return
  }
  bindingLoading.value = true
  try {
    const params = new URLSearchParams()
    ids.forEach((id) => params.append('userids', String(id)))
    await http.post('/teacher/ts', {}, { params })
    ElMessage.success('绑定成功')
    tableRef.value?.clearSelection?.()
    selectedUserIds.value = []
    await fetchPage(1)
  } finally {
    bindingLoading.value = false
  }
}

function bindSelected() {
  if (actionMode.value !== 'bind') return
  bindUsers(selectedUserIds.value)
}

function bindOne(row) {
  if (actionMode.value !== 'bind') return
  const id = normalizeId(row?.userId)
  if (!id) return
  bindUsers([id])
}

async function unbindUsers(userIds) {
  if (actionMode.value !== 'unbind') return
  const ids = Array.from(new Set((userIds || []).map((x) => normalizeId(x)).filter((x) => x !== undefined && x !== null && x !== '')))
  if (!ids.length) {
    ElMessage.warning('请选择学生')
    return
  }
  if (bindingLoading.value) return
  try {
    await ElMessageBox.confirm(`确认解绑选中的 ${ids.length} 名学生？`, '确认解绑', {
      confirmButtonText: '解绑',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch (_) {
    return
  }
  bindingLoading.value = true
  try {
    const params = new URLSearchParams()
    ids.forEach((id) => params.append('userids', String(id)))
    await http.delete('/teacher/ts', { params })
    ElMessage.success('解绑成功')
    tableRef.value?.clearSelection?.()
    selectedUserIds.value = []
    await fetchPage(1)
  } finally {
    bindingLoading.value = false
  }
}

function unbindSelected() {
  if (actionMode.value !== 'unbind') return
  unbindUsers(selectedUserIds.value)
}

function unbindOne(row) {
  if (actionMode.value !== 'unbind') return
  const id = normalizeId(row?.userId)
  if (!id) return
  unbindUsers([id])
}

function viewOne(row) {
  const id = normalizeId(row?.userId)
  if (!id) return
  router.push({ path: `/teacher/my-students/${id}` })
}

function evaluateOne(row) {
  const studentNo = String(row?.studentNo ?? '').trim()
  if (!studentNo) return
  router.push({ path: '/teacher/evaluation', query: { studentNo } })
}

function search() {
  fetchPage(1)
}

function reset() {
  query.value.studentNo = ''
  query.value.entryYear = undefined
  query.value.majorId = undefined
  query.value.classId = undefined
  tableRef.value?.clearSelection?.()
  selectedUserIds.value = []
  fetchPage(1)
}

async function onMajorChange(v) {
  query.value.classId = undefined
  classes.value = []
  tableRef.value?.clearSelection?.()
  selectedUserIds.value = []
  if (v) await loadClasses(v)
}

function onPageChange(p) {
  fetchPage(p)
}

function onSizeChange(s) {
  query.value.pageSize = s
  fetchPage(1)
}

onMounted(async () => {
  await fetchTeacher()
  await loadMajors()
  await fetchPage(1)
})

watch(
  () => route.fullPath,
  async () => {
    tableRef.value?.clearSelection?.()
    selectedUserIds.value = []
    await fetchTeacher()
    await loadMajors()
    await fetchPage(1)
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
