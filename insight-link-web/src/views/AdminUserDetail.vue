<template>
  <div class="page">
    <div class="card">
      <div class="head">
        <div class="head-left">
          <el-button class="back" link type="primary" @click="goBack">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <div class="head-title">用户详情</div>
        </div>
      </div>
      <div class="desc">提示：展示用户基础资料</div>
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
                  <div class="sub">{{ topRoleLabel }}</div>
                </div>
              </div>

              <div class="grid">
                <div class="row">
                  <div class="label">真实姓名：</div>
                  <div class="value">{{ user?.realName || '-' }}</div>
                </div>
                <div class="row">
                  <div class="label">用户名：</div>
                  <div class="value">{{ user?.username || '-' }}</div>
                </div>
                <div class="row">
                  <div class="label">手机号：</div>
                  <div class="value">{{ user?.phone || '-' }}</div>
                </div>
                <div class="row">
                  <div class="label">邮箱：</div>
                  <div class="value">{{ user?.email || '-' }}</div>
                </div>
                <div class="row">
                  <div class="label">出生年月：</div>
                  <div class="value">{{ user?.birthday || '-' }}</div>
                </div>
                <div class="row">
                  <div class="label">性别：</div>
                  <div class="value">{{ genderLabel(user?.gender) }}</div>
                </div>
                <div class="row">
                  <div class="label">注册时间：</div>
                  <div class="value">{{ user?.createTime || '-' }}</div>
                </div>
              </div>

              <div class="actions">
                <div class="action-tile" role="button" tabindex="0" @click="goBack" @keydown.enter.prevent="goBack" @keydown.space.prevent="goBack">
                  <div class="action-tile-left">
                    <div class="action-tile-title">返回上一页</div>
                    <div class="action-tile-sub">回到前一个页面继续操作</div>
                  </div>
                  <div class="action-tile-arrow">→</div>
                </div>
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
import { ArrowLeft } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const user = ref(null)

const userId = computed(() => {
  const raw = route.params?.id
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
})

function roleLabel(roleId) {
  if (roleId === 1) return '管理员'
  if (roleId === 2) return '导师'
  if (roleId === 3) return '学生'
  return roleId === 0 ? '0' : roleId ? String(roleId) : '-'
}

function genderLabel(v) {
  if (v === 1) return '男'
  if (v === 2) return '女'
  return '保密'
}

function normalizeAvatar(a) {
  if (!a) return ''
  const s = String(a).trim().replace(/`/g, '').trim()
  return s
}

const topDisplayName = computed(() => {
  return user.value?.realName || user.value?.username || ''
})
const avatarFallback = computed(() => {
  const name = (topDisplayName.value || '').trim()
  return name ? name.slice(0, 1) : 'U'
})
const topAvatarUrl = computed(() => normalizeAvatar(user.value?.avatar))
const topRoleLabel = computed(() => roleLabel(user.value?.roleId))

async function fetchDetail() {
  const id = userId.value
  if (id === null) {
    user.value = null
    return
  }
  loading.value = true
  try {
    const { data } = await http.get(`/admin/user/${id}`)
    user.value = data?.data || null
  } finally {
    loading.value = false
  }
}

function goBack() {
  if (window.history.length > 1) {
    router.back()
    return
  }
  router.push('/admin/user')
}

onMounted(() => {
  fetchDetail()
})

watch(userId, () => {
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
  min-width: 0;
}
.back {
  padding: 0;
}
.head-title {
  font-size: 16px;
  font-weight: 800;
  color: #111827;
  max-width: 520px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
.sub {
  font-size: 12px;
  color: #6b7280;
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
.value {
  min-width: 0;
  max-width: 360px;
  padding: 0;
  border: none;
  background: transparent;
  color: #111827;
  font-size: 13px;
  text-align: left;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1 1 auto;
}
.actions {
  display: flex;
  justify-content: center;
  margin-top: 18px;
}
.action-tile {
  width: min(520px, 100%);
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
  .grid {
    grid-template-columns: 1fr;
  }
}
</style>
