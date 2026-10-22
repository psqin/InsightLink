<template>
  <div class="page-bg">
    <div class="card">
      <div class="banner">
        <el-button class="back-btn" :icon="ArrowLeft" @click="goBack">返回</el-button>
        <img src="/images/21634504.jpeg" class="banner-img" />
      </div>
      <div class="body">
        <div class="title">忘记密码</div>
        <el-form :model="form" :rules="rules" ref="formRef" label-position="top" size="large" class="form">
          <el-form-item prop="roleId" label="身份">
            <el-select v-model="form.roleId" placeholder="请选择身份" style="width: 100%">
              <el-option label="管理员" :value="1" />
              <el-option label="导师" :value="2" />
              <el-option label="学生" :value="3" />
            </el-select>
          </el-form-item>

          <el-form-item prop="userMessage" label="用户名或手机号">
            <el-input v-model="form.userMessage" placeholder="请输入用户名或手机号" clearable />
          </el-form-item>

          <el-form-item prop="newPassword" label="新密码">
            <el-input v-model="form.newPassword" type="password" placeholder="请输入新密码" show-password />
          </el-form-item>

          <el-form-item>
            <el-button type="primary" class="btn" :loading="loading" @click="onSubmit">重置密码</el-button>
          </el-form-item>

          <div class="footer">
            <el-link type="primary" @click="goLogin">返回登录</el-link>
          </div>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft } from '@element-plus/icons-vue'
import http from '../api/http'

const router = useRouter()
const loading = ref(false)
const formRef = ref()

const form = ref({
  roleId: 3,
  userMessage: '',
  newPassword: ''
})

const rules = {
  roleId: [{ required: true, message: '请选择身份', trigger: 'change' }],
  userMessage: [{ required: true, message: '请输入用户名或手机号', trigger: 'blur' }],
  newPassword: [{ required: true, message: '请输入新密码', trigger: 'blur' }]
}

async function onSubmit() {
  try {
    await formRef.value.validate()
    loading.value = true
    await http.post('/user/forgetPassword', {
      newPassword: form.value.newPassword,
      roleId: form.value.roleId,
      userMessage: form.value.userMessage
    })
    ElMessage.success('密码已重置，请登录')
    router.push('/login')
  } finally {
    loading.value = false
  }
}

function goLogin() {
  router.push('/login')
}

function goBack() {
  router.back()
}
</script>

<style scoped>
.page-bg {
  position: fixed;
  inset: 0;
  background: linear-gradient(135deg, #4aa4ff 0%, #5bb0ff 40%, #6ac0ff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 16px;
}
.card {
  width: 520px;
  max-width: calc(100vw - 32px);
  max-height: calc(100vh - 32px);
  background: #ffffff;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
}
.banner {
  width: 100%;
  height: 140px;
  background: #f0f5ff;
  position: relative;
  flex: 0 0 auto;
}
.banner-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.back-btn {
  position: absolute;
  top: 12px;
  left: 12px;
  z-index: 1;
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(255, 255, 255, 0.8);
}
.body {
  padding: 14px 22px 18px;
  overflow: auto;
}
.title {
  text-align: center;
  font-size: 22px;
  font-weight: 700;
  color: #1f2937;
  margin-bottom: 10px;
}
.form {
  width: 100%;
}
.btn {
  width: 100%;
}
.footer {
  display: flex;
  justify-content: center;
  margin-top: 6px;
  font-size: 12px;
}
</style>
