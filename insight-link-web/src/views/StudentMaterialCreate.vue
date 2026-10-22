<template>
  <div class="page">
    <div class="card">
      <div class="head">
        <div class="head-left">
          <el-button class="back" link type="primary" @click="goBack">
            <el-icon><ArrowLeft /></el-icon>
            返回
          </el-button>
          <div class="head-title">{{ pageTitle }}</div>
        </div>
      </div>

      <div class="form" v-loading="loading">
        <div class="row">
          <div class="label">材料类型</div>
          <div class="value">
            <el-select v-model="form.materialType" placeholder="请选择材料类型" style="width: 100%" :disabled="saving">
              <el-option :value="1" label="学习计划" />
              <el-option :value="2" label="进度汇报" />
              <el-option :value="3" label="自我总结" />
            </el-select>
          </div>
        </div>

        <div class="row">
          <div class="label">标题</div>
          <div class="value">
            <el-input v-model="form.title" placeholder="请输入标题" maxlength="60" show-word-limit :disabled="saving" />
          </div>
        </div>

        <div class="row">
          <div class="label">内容</div>
          <div class="value">
            <el-input
              v-model="form.content"
              type="textarea"
              placeholder="请输入内容"
              :autosize="{ minRows: 10, maxRows: 18 }"
              maxlength="5000"
              show-word-limit
              :disabled="saving"
            />
          </div>
        </div>

        <div class="row">
          <div class="label">附件材料</div>
          <div class="value">
            <el-upload
              class="upload-demo"
              action="#"
              :http-request="uploadFile"
              :on-remove="handleRemove"
              :limit="1"
              :on-exceed="handleExceed"
              :file-list="fileList"
              :disabled="saving"
            >
              <el-button type="primary" plain :disabled="saving">点击上传附件</el-button>
              <template #tip>
                <div class="el-upload__tip">
                  支持 word、pdf 等文档格式（最多上传1个文件）
                </div>
              </template>
            </el-upload>
          </div>
        </div>

        <div class="row">
          <div class="label"></div>
          <div class="value actions">
            <el-button type="primary" :loading="saving" :disabled="saving" @click="submit">提交</el-button>
            <el-button :disabled="saving" @click="goBack">取消</el-button>
          </div>
        </div>
      </div>

      <transition name="fade">
        <div v-if="saving" class="saving-mask">正在提交...</div>
      </transition>
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
const saving = ref(false)
const form = ref({
  title: '',
  materialType: undefined,
  content: '',
  fileUrl: ''
})

const fileList = ref([])

const materialId = computed(() => {
  const raw = route.params?.id
  if (raw === undefined || raw === null || raw === '') return null
  const n = Number(raw)
  return Number.isFinite(n) ? n : null
})

const isEdit = computed(() => materialId.value !== null)
const pageTitle = computed(() => (isEdit.value ? '材料修改' : '材料上传'))

function goBack() {
  router.push({ path: '/student/my-material', query: route.query || {} })
}

function validate() {
  const title = (form.value.title || '').trim()
  const content = (form.value.content || '').trim()
  const materialType = form.value.materialType
  const fileUrl = form.value.fileUrl || ''
  if (!materialType) {
    ElMessage.error('请选择材料类型')
    return null
  }
  if (!title) {
    ElMessage.error('请输入标题')
    return null
  }
  if (!content) {
    ElMessage.error('请输入内容')
    return null
  }
  return { title, materialType, content, fileUrl }
}

async function uploadFile(options) {
  const formData = new FormData()
  formData.append('file', options.file)
  try {
    const { data } = await http.post('/user/common/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
    if (data.code === 1) {
      form.value.fileUrl = data.data
      options.onSuccess(data.data, options.file)
    } else {
      options.onError(new Error(data.msg))
      ElMessage.error(data.msg || '上传失败')
    }
  } catch (error) {
    options.onError(error)
    ElMessage.error('上传失败')
  }
}

function handleRemove() {
  form.value.fileUrl = ''
}

function handleExceed() {
  ElMessage.warning('只能上传一个文件，请先删除已上传的文件')
}

async function fetchMaterialForEdit() {
  if (!isEdit.value) return
  const id = materialId.value
  if (!id) return
  loading.value = true
  try {
    const { data } = await http.get(`/student/material/${id}`)
    const m = data?.data
    form.value = {
      title: m?.title || '',
      materialType: m?.materialType,
      content: m?.content || '',
      fileUrl: m?.fileUrl || ''
    }
    if (m?.fileUrl) {
      const fileName = m.fileUrl.substring(m.fileUrl.lastIndexOf('/') + 1) || '附件文件'
      fileList.value = [{ name: fileName, url: m.fileUrl }]
    } else {
      fileList.value = []
    }
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (saving.value || loading.value) return
  const payload = validate()
  if (!payload) return
  saving.value = true
  try {
    if (isEdit.value) {
      const id = materialId.value
      if (!id) return
      await http.put('/student/material', { ...payload, id })
      ElMessage.success('修改成功')
    } else {
      await http.post('/student/material', payload)
      ElMessage.success('提交成功')
    }
    goBack()
  } finally {
    saving.value = false
  }
}

watch(
  () => materialId.value,
  () => {
    fetchMaterialForEdit()
  }
)

onMounted(() => {
  fetchMaterialForEdit()
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
  position: relative;
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
  font-weight: 800;
  color: #111827;
}
.back {
  padding: 0;
}
.form {
  margin-top: 14px;
  max-width: 820px;
}
.actions {
  display: flex;
  justify-content: flex-start;
  gap: 10px;
}
.row {
  display: grid;
  grid-template-columns: 110px minmax(0, 1fr);
  gap: 10px;
  align-items: start;
  padding: 10px 0;
}
.label {
  font-size: 13px;
  color: #6b7280;
  padding-top: 10px;
}
.value {
  min-width: 0;
}
.saving-mask {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: #111827;
  border-radius: 12px;
  backdrop-filter: blur(2px);
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 160ms ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
@media (max-width: 720px) {
  .row {
    grid-template-columns: 1fr;
  }
  .label {
    padding-top: 0;
  }
}
</style>
