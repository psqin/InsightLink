<template>
  <div class="page">
    <div class="card">
      <div class="title">修改学生信息</div>
      <div class="desc">提示：更新学生的学籍信息</div>
      <div class="content">
        <el-skeleton :loading="loading" animated>
          <template #template>
            <el-skeleton-item variant="h1" style="width: 180px" />
            <el-skeleton-item variant="text" style="margin-top: 12px" />
            <el-skeleton-item variant="text" style="margin-top: 8px" />
            <el-skeleton-item variant="text" style="margin-top: 8px" />
          </template>
          <template #default>
            <div class="wrap">
              <div class="top">
                <el-avatar :size="76" :src="topAvatarUrl">{{ avatarFallback }}</el-avatar>
                <div class="top-right">
                  <div class="name">{{ topDisplayName || '-' }}</div>
                  <div class="badges">
                    <div class="badge">学号：{{ editForm.studentNo || '-' }}</div>
                    <div class="badge">入学年份：{{ editForm.entryYear || '-' }}</div>
                  </div>
                </div>
              </div>

              <div class="grid">
                <div class="row">
                  <div class="label">学号：</div>
                  <div class="value-input">
                    <el-input v-model="editForm.studentNo" placeholder="请输入学号" />
                  </div>
                </div>
                <div class="row">
                  <div class="label">入学年份：</div>
                  <div class="value-input">
                    <el-input-number v-model="editForm.entryYear" :min="1900" :max="2100" controls-position="right" style="width: 100%" />
                  </div>
                </div>
                <div class="row">
                  <div class="label">学校：</div>
                  <div class="value-input">
                    <el-select
                      v-model="editForm.universityId"
                      filterable
                      remote
                      reserve-keyword
                      :remote-method="searchUniversities"
                      :loading="universityLoading"
                      placeholder="输入学校名称搜索"
                      style="width: 100%"
                      @change="onUniversityChange"
                    >
                      <el-option v-for="u in universities" :key="u.id" :label="u.name" :value="u.id" />
                    </el-select>
                  </div>
                </div>
                <div class="row">
                  <div class="label">学院：</div>
                  <div class="value-input">
                    <el-select
                      v-model="editForm.collegeId"
                      filterable
                      placeholder="请选择学院"
                      style="width: 100%"
                      :disabled="!editForm.universityId"
                      :loading="collegeLoading"
                      @change="onCollegeChange"
                    >
                      <el-option v-for="c in colleges" :key="c.id" :label="c.name" :value="c.id" />
                    </el-select>
                  </div>
                </div>
                <div class="row">
                  <div class="label">专业：</div>
                  <div class="value-input">
                    <el-select
                      v-model="editForm.majorId"
                      filterable
                      placeholder="请选择专业"
                      style="width: 100%"
                      :disabled="!editForm.collegeId"
                      :loading="majorLoading"
                      @change="onMajorChange"
                    >
                      <el-option v-for="m in majors" :key="m.id" :label="m.name" :value="m.id" />
                    </el-select>
                  </div>
                </div>
                <div class="row">
                  <div class="label">班级：</div>
                  <div class="value-input">
                    <el-select
                      v-model="editForm.classId"
                      filterable
                      placeholder="请选择班级"
                      style="width: 100%"
                      :disabled="!editForm.majorId"
                      :loading="classLoading"
                    >
                      <el-option v-for="cl in classes" :key="cl.id" :label="cl.name" :value="cl.id" />
                    </el-select>
                  </div>
                </div>
              </div>

              <div class="actions">
                <el-button type="primary" :loading="saving" @click="save">保存</el-button>
                <el-button :disabled="saving" @click="goBack">取消</el-button>
              </div>
            </div>
          </template>
        </el-skeleton>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import http from '../api/http'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const saving = ref(false)
const student = ref(null)

const universityLoading = ref(false)
const collegeLoading = ref(false)
const majorLoading = ref(false)
const classLoading = ref(false)

const universities = ref([])
const colleges = ref([])
const majors = ref([])
const classes = ref([])

const studentId = computed(() => {
  const raw = route.params?.id
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
})

const editForm = ref({
  classId: undefined,
  collegeId: undefined,
  entryYear: undefined,
  majorId: undefined,
  studentNo: '',
  universityId: undefined
})

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
function seedOption(list, id, name) {
  const nid = normalizeId(id)
  const nname = (name || '').trim()
  if (!nid || !nname) return
  const exists = list.some((x) => String(x?.id) === String(nid))
  if (!exists) list.push({ id: nid, name: nname })
}
function normalizeUrl(a) {
  if (!a) return ''
  const s = String(a).trim().replace(/`/g, '').trim()
  return s
}
const topDisplayName = computed(() => student.value?.realName || '')
const avatarFallback = computed(() => {
  const name = (topDisplayName.value || '').trim()
  return name ? name.slice(0, 1) : 'S'
})
const topAvatarUrl = computed(() => normalizeUrl(student.value?.avatar))

async function searchUniversities(query) {
  const q = (query || '').trim()
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

async function fetchDetail() {
  const id = studentId.value
  if (id === null) {
    student.value = null
    return
  }
  loading.value = true
  try {
    const { data } = await http.get(`/admin/student/${id}`)
    student.value = data?.data || null
    editForm.value = {
      classId: normalizeId(student.value?.classId) || undefined,
      collegeId: normalizeId(student.value?.collegeId) || undefined,
      entryYear: normalizeId(student.value?.entryYear) || undefined,
      majorId: normalizeId(student.value?.majorId) || undefined,
      studentNo: student.value?.studentNo ? String(student.value.studentNo) : '',
      universityId: normalizeId(student.value?.universityId) || undefined
    }
    universities.value = []
    colleges.value = []
    majors.value = []
    classes.value = []
    seedOption(universities.value, student.value?.universityId, student.value?.universityName)
    seedOption(colleges.value, student.value?.collegeId, student.value?.collegeName)
    seedOption(majors.value, student.value?.majorId, student.value?.majorName)
    seedOption(classes.value, student.value?.classId, student.value?.className)
    if (editForm.value.universityId) await loadColleges(editForm.value.universityId)
    if (editForm.value.collegeId) await loadMajors(editForm.value.collegeId)
    if (editForm.value.majorId) await loadClasses(editForm.value.majorId)
  } finally {
    loading.value = false
  }
}

async function save() {
  if (saving.value) return
  const id = studentId.value
  if (id === null) return
  const payload = {
    classId: normalizeId(editForm.value.classId),
    collegeId: normalizeId(editForm.value.collegeId),
    entryYear: normalizeId(editForm.value.entryYear),
    majorId: normalizeId(editForm.value.majorId),
    studentNo: (editForm.value.studentNo || '').trim(),
    universityId: normalizeId(editForm.value.universityId)
  }
  saving.value = true
  try {
    try {
      await http.put(`/admin/student/${id}`, payload)
    } catch (e) {
      await http.put(`/admin/student/${id}`, { studentInfoDTO: payload })
    }
    ElMessage.success('保存成功')
    goBack()
  } finally {
    saving.value = false
  }
}

async function onUniversityChange(v) {
  editForm.value.collegeId = undefined
  editForm.value.majorId = undefined
  editForm.value.classId = undefined
  colleges.value = []
  majors.value = []
  classes.value = []
  if (v) await loadColleges(v)
}
async function onCollegeChange(v) {
  editForm.value.majorId = undefined
  editForm.value.classId = undefined
  majors.value = []
  classes.value = []
  if (v) await loadMajors(v)
}
async function onMajorChange(v) {
  editForm.value.classId = undefined
  classes.value = []
  if (v) await loadClasses(v)
}

function goBack() {
  router.push('/admin/student')
}

onMounted(() => {
  fetchDetail()
})

watch(studentId, () => {
  fetchDetail()
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
.desc {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}
.content {
  margin-top: 14px;
}
.wrap {
  max-width: 860px;
  margin: 0 auto;
}
.top {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  justify-content: center;
}
.top-right {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
  align-items: center;
}
.name {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  max-width: 340px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.badges {
  display: flex;
  align-items: center;
  gap: 8px;
}
.badge {
  font-size: 12px;
  color: #374151;
  background: #f3f4f6;
  border: 1px solid #e5e7eb;
  border-radius: 999px;
  padding: 4px 10px;
  line-height: 1;
}
.grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 14px 24px;
  max-width: 760px;
  margin: 0 auto;
}
.row {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  min-height: 42px;
}
.label {
  width: auto;
  text-align: left;
  font-size: 13px;
  color: #6b7280;
  flex: 0 0 auto;
}
.value-input {
  min-width: 0;
  max-width: 360px;
  flex: 1 1 auto;
}
.actions {
  display: flex;
  justify-content: center;
  margin-top: 18px;
}
@media (max-width: 880px) {
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
