<template>
  <div class="page">
    <div class="card">
      <div class="title">用户管理</div>
      <div class="hint">提示：支持角色过滤、姓名模糊查询</div>

      <div class="bar">
        <div class="bar-left">
          <el-input v-model="query.keyword" clearable placeholder="姓名" style="width: 180px" @keyup.enter="search" />
          <el-input v-model="query.phone" clearable placeholder="手机号" style="width: 180px" @keyup.enter="search" />
          <el-select v-model="query.roleId" clearable placeholder="角色" style="width: 160px">
            <el-option :value="1" label="管理员" />
            <el-option :value="2" label="导师" />
            <el-option :value="3" label="学生" />
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
          <el-table-column prop="username" label="账号" min-width="140" align="center" show-overflow-tooltip />
          <el-table-column label="头像" width="88" align="center">
            <template #default="{ row }">
              <el-avatar :size="34" :src="normalizeAvatar(row?.avatar)">{{ avatarFallback(row) }}</el-avatar>
            </template>
          </el-table-column>
          <el-table-column prop="realName" label="姓名" min-width="140" align="center" show-overflow-tooltip />
          <el-table-column prop="phone" label="手机号" min-width="140" align="center" show-overflow-tooltip />
          <el-table-column prop="roleId" label="角色" min-width="120" align="center">
            <template #default="{ row }">
              <el-tag :type="roleTagType(row?.roleId)" effect="light">{{ roleLabel(row?.roleId) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="email" label="邮箱" min-width="140" align="center" show-overflow-tooltip />
          <el-table-column prop="createTime" label="注册时间" min-width="180" align="center" show-overflow-tooltip />
          <el-table-column label="操作" width="180" fixed="right" align="center">
            <template #default="{ row }">
              <el-button link type="primary" @click="openView(row)">查看</el-button>
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

    <el-dialog v-model="editVisible" title="修改用户" width="560px" :close-on-click-modal="false">
      <el-skeleton :loading="detailLoading" animated>
        <el-form label-width="90px" class="edit-form">
          <el-form-item label="账号">
            <el-input :model-value="detail?.username || ''" disabled />
          </el-form-item>
          <el-form-item label="姓名">
            <el-input v-model="editForm.realName" placeholder="请输入姓名" />
          </el-form-item>
          <el-form-item label="手机号">
            <el-input v-model="editForm.phone" placeholder="请输入手机号" />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="editForm.email" placeholder="请输入邮箱" />
          </el-form-item>
          <el-form-item label="出生年月">
            <el-date-picker v-model="editForm.birthday" type="date" placeholder="请选择日期" style="width: 100%" value-format="YYYY-MM-DD" />
          </el-form-item>
          <el-form-item label="性别">
            <el-radio-group v-model="editForm.gender">
              <el-radio :value="0">保密</el-radio>
              <el-radio :value="1">男</el-radio>
              <el-radio :value="2">女</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="editForm.password" type="password" show-password placeholder="不修改可留空" />
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

const query = ref({
  keyword: '',
  page: 1,
  pageSize: 10,
  phone: '',
  roleId: undefined
})

function roleLabel(roleId) {
  if (roleId === 1) return '管理员'
  if (roleId === 2) return '导师'
  if (roleId === 3) return '学生'
  return roleId === 0 ? '0' : roleId ? String(roleId) : '-'
}

function roleTagType(roleId) {
  if (roleId === 1) return 'danger'
  if (roleId === 2) return 'success'
  if (roleId === 3) return 'info'
  return 'info'
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

function avatarFallback(row) {
  const name = (row?.realName || row?.username || '').trim()
  return name ? name.slice(0, 1) : 'U'
}

const editVisible = ref(false)
const detailLoading = ref(false)
const editSaving = ref(false)
const deleting = ref(false)
const detail = ref(null)
const editForm = ref({
  birthday: '',
  email: '',
  gender: 0,
  phone: '',
  realName: '',
  password: ''
})

async function fetchPage(toPage = query.value.page) {
  const page = Number(toPage)
  query.value.page = Number.isFinite(page) && page > 0 ? page : 1
  const params = {
    keyword: (query.value.keyword || '').trim() || undefined,
    phone: (query.value.phone || '').trim() || undefined,
    roleId: query.value.roleId ?? undefined,
    page: query.value.page,
    pageSize: query.value.pageSize
  }
  loading.value = true
  try {
    const { data } = await http.get('/admin/user/page', { params })
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
    const { data } = await http.get(`/admin/user/${id}`)
    detail.value = data?.data || null
    return detail.value
  } finally {
    detailLoading.value = false
  }
}

function openView(row) {
  const id = row?.id
  if (!id && id !== 0) return
  router.push(`/admin/user/${id}`)
}

async function openEdit(row) {
  const id = row?.id
  if (!id && id !== 0) return
  router.push(`/admin/user/${id}/edit`)
}

async function saveEdit() {
  if (editSaving.value) return
  const id = detail.value?.id
  if (!id && id !== 0) return

  const payload = {
    birthday: editForm.value.birthday || '',
    email: (editForm.value.email || '').trim(),
    gender: editForm.value.gender ?? 0,
    phone: (editForm.value.phone || '').trim(),
    realName: (editForm.value.realName || '').trim(),
    password: (editForm.value.password || '').trim() || undefined
  }

  editSaving.value = true
  try {
    try {
      await http.put(`/admin/user/${id}`, payload)
    } catch (e) {
      await http.put(`/admin/user/${id}`, { adminUserUpdateDTO: payload })
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
    await ElMessageBox.confirm('确认删除该用户？此操作不可恢复。', '确认删除', {
      confirmButtonText: '确认',
      cancelButtonText: '取消',
      type: 'warning'
    })
  } catch (_) {
    return
  }
  deleting.value = true
  try {
    await http.delete(`/admin/user/${id}`)
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
  query.value.keyword = ''
  query.value.phone = ''
  query.value.roleId = undefined
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
</style>
