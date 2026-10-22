<template>
  <div class="page">
    <div class="card">
      <div class="title">修改用户</div>
      <div class="desc">提示：更新用户基础资料</div>
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
                    <div class="badge">角色：{{ topRoleLabel }}</div>
                    <div class="badge">账号：{{ user?.username || '-' }}</div>
                  </div>
                </div>
              </div>

              <div class="grid">
                <div class="row">
                  <div class="label">真实姓名：</div>
                  <div class="value-input">
                    <el-input v-model="editForm.realName" placeholder="请输入真实姓名" />
                  </div>
                </div>
                <div class="row">
                  <div class="label">手机号：</div>
                  <div class="value-input">
                    <el-input v-model="editForm.phone" placeholder="请输入手机号" />
                  </div>
                </div>
                <div class="row">
                  <div class="label">邮箱：</div>
                  <div class="value-input">
                    <el-input v-model="editForm.email" placeholder="请输入邮箱" />
                  </div>
                </div>
                <div class="row">
                  <div class="label">出生年月：</div>
                  <div class="value-input">
                    <el-date-picker v-model="editForm.birthday" type="date" placeholder="请选择日期" style="width: 100%" value-format="YYYY-MM-DD" />
                  </div>
                </div>
                <div class="row">
                  <div class="label">性别：</div>
                  <div class="value-input">
                    <el-radio-group v-model="editForm.gender">
                      <el-radio :value="0">保密</el-radio>
                      <el-radio :value="1">男</el-radio>
                      <el-radio :value="2">女</el-radio>
                    </el-radio-group>
                  </div>
                </div>
                <div class="row">
                  <div class="label">密码：</div>
                  <div class="value-input">
                    <el-input v-model="editForm.password" type="password" show-password placeholder="不修改可留空" />
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
const user = ref(null)

const userId = computed(() => {
  const raw = route.params?.id
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
})

const editForm = ref({
  birthday: '',
  email: '',
  gender: 0,
  phone: '',
  realName: '',
  password: ''
})

function roleLabel(roleId) {
  if (roleId === 1) return '管理员'
  if (roleId === 2) return '导师'
  if (roleId === 3) return '学生'
  return roleId === 0 ? '0' : roleId ? String(roleId) : '-'
}
const topDisplayName = computed(() => user.value?.realName || user.value?.username || '')
const avatarFallback = computed(() => {
  const name = (topDisplayName.value || '').trim()
  return name ? name.slice(0, 1) : 'U'
})
function normalizeAvatar(a) {
  if (!a) return ''
  const s = String(a).trim().replace(/`/g, '').trim()
  return s
}
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
    editForm.value = {
      birthday: user.value?.birthday || '',
      email: user.value?.email || '',
      gender: user.value?.gender ?? 0,
      phone: user.value?.phone || '',
      realName: user.value?.realName || '',
      password: ''
    }
  } finally {
    loading.value = false
  }
}

async function save() {
  if (saving.value) return
  const id = userId.value
  if (id === null) return
  const payload = {
    birthday: editForm.value.birthday || '',
    email: (editForm.value.email || '').trim(),
    gender: editForm.value.gender ?? 0,
    phone: (editForm.value.phone || '').trim(),
    realName: (editForm.value.realName || '').trim(),
    password: (editForm.value.password || '').trim() || undefined
  }
  saving.value = true
  try {
    await http.put(`/admin/user/${id}`, payload)
    ElMessage.success('保存成功')
    goBack()
  } finally {
    saving.value = false
  }
}

function goBack() {
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
.value-input {
  min-width: 0;
  max-width: 360px;
  flex: 1 1 auto;
}
.row.row-span {
  grid-column: 1 / -1;
}
.row.row-span .value-input {
  max-width: none;
  width: 100%;
}
.actions {
  display: flex;
  justify-content: center;
  margin-top: 18px;
}
</style>
