<template>
  <div class="page">
    <div class="card">
      <div class="title">修改导师信息</div>
      <div class="desc">提示：更新导师的学校、院系、职称、研究方向、工号等信息</div>
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
                </div>
              </div>
              <el-form label-width="86px" class="edit-form">
                <el-row :gutter="24">
                  <el-col :span="12">
                    <el-form-item label="学校：">
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
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="院系：">
                      <el-select
                        v-model="editForm.deptId"
                        filterable
                        placeholder="请选择院系"
                        style="width: 100%"
                        :disabled="!editForm.universityId"
                        :loading="deptLoading"
                      >
                        <el-option v-for="d in depts" :key="d.id" :label="d.name" :value="d.id" />
                      </el-select>
                    </el-form-item>
                  </el-col>

                  <el-col :span="12">
                    <el-form-item label="职称：">
                      <el-input v-model="editForm.title" placeholder="请输入职称" />
                    </el-form-item>
                  </el-col>
                  <el-col :span="12">
                    <el-form-item label="工号：">
                      <el-input v-model="editForm.teacherNo" placeholder="请输入工号" />
                    </el-form-item>
                  </el-col>

                  <el-col :span="24">
                    <el-form-item label="研究领域：">
                      <el-input v-model="editForm.researchField" type="textarea" :rows="5" placeholder="请输入研究领域/方向" />
                    </el-form-item>
                  </el-col>
                </el-row>
              </el-form>

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
const teacher = ref(null)

const universityLoading = ref(false)
const deptLoading = ref(false)

const universities = ref([])
const depts = ref([])

const teacherId = computed(() => {
  const raw = route.params?.id
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
})

const editForm = ref({
  deptId: undefined,
  researchField: '',
  teacherNo: '',
  title: '',
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

const topDisplayName = computed(() => teacher.value?.realName || '')
const avatarFallback = computed(() => {
  const name = (topDisplayName.value || '').trim()
  return name ? name.slice(0, 1) : 'T'
})
const topAvatarUrl = computed(() => normalizeUrl(teacher.value?.avatar))

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

async function fetchDetail() {
  const id = teacherId.value
  if (id === null) {
    teacher.value = null
    return
  }
  loading.value = true
  try {
    const { data } = await http.get(`/admin/teacher/${id}`)
    teacher.value = data?.data || null
    editForm.value = {
      deptId: normalizeId(teacher.value?.deptId) || undefined,
      researchField: (teacher.value?.researchField || '').trim(),
      teacherNo: teacher.value?.teacherNo ? String(teacher.value.teacherNo) : '',
      title: (teacher.value?.title || '').trim(),
      universityId: normalizeId(teacher.value?.universityId) || undefined
    }
    universities.value = []
    depts.value = []
    seedOption(universities.value, teacher.value?.universityId, teacher.value?.universityName)
    seedOption(depts.value, teacher.value?.deptId, teacher.value?.deptName)
    if (editForm.value.universityId) await loadDepts(editForm.value.universityId)
  } finally {
    loading.value = false
  }
}

async function onUniversityChange(v) {
  editForm.value.deptId = undefined
  depts.value = []
  if (v) await loadDepts(v)
}

async function save() {
  if (saving.value) return
  const id = teacherId.value
  if (id === null) return
  const payload = {
    deptId: normalizeId(editForm.value.deptId),
    researchField: (editForm.value.researchField || '').trim(),
    teacherNo: (editForm.value.teacherNo || '').trim(),
    title: (editForm.value.title || '').trim(),
    universityId: normalizeId(editForm.value.universityId)
  }
  saving.value = true
  try {
    try {
      await http.put(`/admin/teacher/${id}`, payload)
    } catch (e) {
      await http.put(`/admin/teacher/${id}`, { teacherInfoDTO: payload })
    }
    ElMessage.success('保存成功')
    goBack()
  } finally {
    saving.value = false
  }
}

function goBack() {
  router.push('/admin/teacher')
}

onMounted(() => {
  fetchDetail()
})

watch(teacherId, () => {
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
.edit-form {
  padding-top: 8px;
}
.actions {
  display: flex;
  justify-content: center;
  margin-top: 18px;
}
</style>
