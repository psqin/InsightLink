<template>
  <div class="page">
    <div class="card">
      <div class="head">
        <div class="head-left">
          <el-button class="back" link type="primary" @click="goBack">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <div class="head-title">学生信息</div>
        </div>
      </div>

      <el-skeleton :loading="loading" animated>
        <template #template>
          <el-skeleton-item variant="h1" style="width: 240px" />
          <el-skeleton-item variant="text" style="margin-top: 12px" />
          <el-skeleton-item variant="rect" style="margin-top: 14px; height: 180px" />
        </template>
        <template #default>
          <div v-if="!student" class="empty">暂无内容</div>
          <div v-else>
            <div class="profile">
              <el-avatar :size="62" :src="normalizeAvatarUrl(student?.avatar)">{{ avatarFallback }}</el-avatar>
              <div class="profile-main">
                <div class="profile-name-line">
                  <div class="profile-name">{{ student.realName || '-' }}</div>
                  <el-tag effect="light" size="small">{{ genderLabel(student.gender) }}</el-tag>
                </div>
                <div class="profile-sub">{{ student.studentNo || '-' }}</div>
              </div>
            </div>

            <div class="meta">
              <div class="meta-item">
                <div class="k">学校</div>
                <div class="v">{{ student.universityName || '-' }}</div>
              </div>
              <div class="meta-item">
                <div class="k">学院</div>
                <div class="v">{{ student.collegeName || '-' }}</div>
              </div>
              <div class="meta-item">
                <div class="k">专业</div>
                <div class="v">{{ student.majorName || '-' }}</div>
              </div>
              <div class="meta-item">
                <div class="k">班级</div>
                <div class="v">{{ student.className || '-' }}</div>
              </div>
              <div class="meta-item">
                <div class="k">入学年份</div>
                <div class="v">{{ student.entryYear ? `${student.entryYear}` : '-' }}</div>
              </div>
              <div class="meta-item">
                <div class="k">绑定状态</div>
                <div class="v">{{ bindStatusLabel(student.bindStatus) }}</div>
              </div>
            </div>

            <div class="actions">
              <div class="action-tile" role="button" tabindex="0" @click.prevent="goContactStudent" @keydown.enter.prevent="goContactStudent" @keydown.space.prevent="goContactStudent">
                <div class="action-tile-left">
                  <div class="action-tile-title">联系学生</div>
                  <div class="action-tile-sub">点击进入留言信息，向学生发送消息</div>
                </div>
                <div class="action-tile-arrow">→</div>
              </div>
              <div
                class="action-tile"
                role="button"
                tabindex="0"
                @click="goEvaluation"
                @keydown.enter.prevent="goEvaluation"
                @keydown.space.prevent="goEvaluation"
              >
                <div class="action-tile-left">
                  <div class="action-tile-title">材料评价</div>
                  <div class="action-tile-sub">点击进入材料评价</div>
                </div>
                <div class="action-tile-arrow">→</div>
              </div>
            </div>
          </div>
        </template>
      </el-skeleton>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import http from '../api/http'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const student = ref(null)

const studentId = computed(() => {
  const raw = route.params?.id
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
})

const avatarFallback = computed(() => {
  const s = student.value?.realName || student.value?.studentNo || ''
  return String(s).trim().slice(0, 1)
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

function bindStatusLabel(v) {
  const n = Number(v)
  if (n === 1) return '已绑定导师'
  if (n === 0) return '未绑定导师'
  return '-'
}

async function fetchStudent() {
  const id = studentId.value
  if (!id) {
    student.value = null
    return
  }
  loading.value = true
  try {
    const { data } = await http.get(`/teacher/ts/${id}`)
    student.value = data?.data || null
  } catch (_) {
    student.value = null
    ElMessage.error('获取学生信息失败')
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push({ path: '/teacher/my-students', query: route.query || {} })
}

function goContactStudent() {
  const userId = student.value?.userId
  if (userId) {
    router.push({ 
      path: '/teacher/messages', 
      query: { 
        contactId: userId,
        contactName: student.value?.realName,
        contactRole: 3,
        contactAvatar: student.value?.avatar || ''
      } 
    })
  } else {
    router.push('/teacher/messages')
  }
}

function goEvaluation() {
  const studentNo = String(student.value?.studentNo ?? '').trim()
  if (!studentNo) return
  router.push({ path: '/teacher/evaluation', query: { studentNo } })
}

watch(
  () => studentId.value,
  () => {
    fetchStudent()
  }
)

onMounted(() => {
  fetchStudent()
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
.head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}
.head-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.head-title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}
.profile {
  margin-top: 14px;
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
}
.profile-main {
  min-width: 220px;
}
.profile-name-line {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.profile-name {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}
.profile-sub {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
}
.meta {
  margin-top: 16px;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px 18px;
}
.meta-item {
  border: 1px solid #ebeef5;
  border-radius: 10px;
  padding: 12px 14px;
  background: #ffffff;
}
.k {
  font-size: 12px;
  color: #6b7280;
}
.v {
  margin-top: 6px;
  font-size: 13px;
  color: #111827;
  font-weight: 600;
  word-break: break-all;
}
.empty {
  margin-top: 14px;
  font-size: 13px;
  color: #6b7280;
}
.actions {
  margin-top: 16px;
  max-width: 760px;
  margin-left: auto;
  margin-right: auto;
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
}
.action-tile {
  flex: 1 1 320px;
  min-width: 0;
  border-radius: 14px;
  padding: 14px 16px;
  border: 1px solid #e5e7eb;
  background: linear-gradient(180deg, #ffffff 0%, #fbfcff 100%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 14px;
  cursor: pointer;
  user-select: none;
  box-shadow: 0 0 0 rgba(0, 0, 0, 0);
  transition:
    transform 160ms ease,
    box-shadow 160ms ease,
    border-color 160ms ease,
    background 160ms ease;
}
.action-tile:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(17, 24, 39, 0.08);
  border-color: #c7d2fe;
  background: linear-gradient(180deg, #ffffff 0%, #f6f8ff 100%);
}
.action-tile:active {
  transform: translateY(0);
  box-shadow: 0 6px 14px rgba(17, 24, 39, 0.08);
}
.action-tile:focus-visible {
  outline: 0;
  box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.25);
  border-color: #6366f1;
}
.action-tile-left {
  min-width: 0;
}
.action-tile-title {
  font-size: 15px;
  font-weight: 800;
  color: #111827;
  letter-spacing: 0.2px;
}
.action-tile-sub {
  margin-top: 4px;
  font-size: 12px;
  color: #6b7280;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.action-tile-arrow {
  flex: none;
  width: 34px;
  height: 34px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: rgba(99, 102, 241, 0.1);
  color: #4f46e5;
  font-size: 16px;
  font-weight: 800;
  transition: transform 160ms ease, background 160ms ease;
}
.action-tile:hover .action-tile-arrow {
  transform: translateX(2px);
  background: rgba(99, 102, 241, 0.14);
}
@media (max-width: 880px) {
  .meta {
    grid-template-columns: 1fr;
  }
}
</style>
