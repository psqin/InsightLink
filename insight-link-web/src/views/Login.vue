<template>
  <div class="login-bg">
    <div class="top-brand">
      <div class="top-logo">InsightLink</div>
      <div class="top-slogan">教研赋能，成长可期</div>
      <div class="system-title-top">学业导师点评系统</div>
    </div>
    <div class="login-box">
      <div class="left-visual">
        <img src="/images/VCG211275008670.webp" class="visual-img" />
      </div>
      <div class="right-form">
        <div class="form-wrap">
          <el-form :model="form" :rules="rules" ref="formRef" label-position="top" class="form-area" size="large">
            <div class="welcome">欢迎登录</div>
            <el-form-item prop="roleId">
              <el-select v-model="form.roleId" placeholder="选择身份" style="width: 100%" size="large">
                <el-option label="学生" :value="3" />
                <el-option label="导师" :value="2" />
                <el-option label="管理员" :value="1" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="loginMode === 'phone'" prop="phone">
              <el-input v-model="form.phone" placeholder="请输入手机号" clearable size="large" />
            </el-form-item>
            <el-form-item v-else prop="username">
              <el-input v-model="form.username" placeholder="请输入账号" clearable size="large" />
            </el-form-item>
            <el-form-item prop="password">
              <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password size="large" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" class="confirm-btn" size="large" @click="onSubmit" :loading="loading">登录</el-button>
            </el-form-item>
            <div class="actions-inline">
              <el-link type="primary" @click="toggleMode">{{ loginMode === 'phone' ? '账号登录' : '手机号登录' }}</el-link>
              <span class="sep">|</span>
              <el-link type="primary" @click="onRegister">立即注册</el-link>
              <span class="sep">|</span>
              <el-link type="primary" @click="onForgot">忘记密码</el-link>
            </div>
          </el-form>
        </div>
        
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAppStore } from '../store'
import http from '../api/http'
import { ElMessage } from 'element-plus'

const store = useAppStore()
const router = useRouter()
const loading = ref(false)
const formRef = ref()
const loginMode = ref('phone')
const form = ref({
  username: '',
  phone: '',
  roleId: 3,
  password: ''
})

const rules = {
  roleId: [{ required: true, message: '请选择身份', trigger: 'change' }],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1\d{10}$/, message: '手机号格式不正确', trigger: 'blur' }
  ],
  username: [{ required: true, message: '请输入账号', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

async function onSubmit() {
  try {
    await formRef.value.validate()
    loading.value = true
    const payload = {
      username: loginMode.value === 'account' ? form.value.username : '',
      phone: loginMode.value === 'phone' ? form.value.phone : '',
      roleId: form.value.roleId,
      password: form.value.password
    }
    const { data } = await http.post('/user/login', payload)
    const apiMsg = data?.msg
    const token = data?.data?.token
    if (!token) {
      const err = new Error(apiMsg || '登录失败')
      err.data = data
      throw err
    }
    store.setToken(token)
    store.setUser(data?.data)
    ElMessage.success('登录成功')
    const roleId = data?.data?.roleId
    if (roleId === 1) router.push('/admin')
    else if (roleId === 2) router.push('/teacher')
    else router.push('/student')
  } catch (e) {
    if (e?._notified) return
    const msg = e?.response?.data?.msg || e?.data?.msg || e?.message || '登录失败'
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

function toggleMode() {
  loginMode.value = loginMode.value === 'phone' ? 'account' : 'phone'
  formRef.value?.clearValidate?.()
}

function onRegister() {
  router.push('/register')
}

function onForgot() {
  router.push('/forget-password')
}

</script>

<style scoped>
.login-bg {
  position: fixed;
  inset: 0;
  background: linear-gradient(135deg, #4aa4ff 0%, #5bb0ff 40%, #6ac0ff 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}
.top-brand {
  position: absolute;
  top: 6%;
  left: 50%;
  transform: translateX(-50%);
  text-align: center;
  color: #fff;
}
.top-logo {
  font-size: 38px;
  font-weight: 800;
  letter-spacing: 1px;
  background: linear-gradient(90deg,#ffffff,#e6f2ff);
  -webkit-background-clip: text;
  background-clip: text;
  color: transparent;
}
.top-slogan {
  margin-top: 6px;
  font-size: 16px;
  opacity: 0.9;
}
.system-title-top {
  margin-top: 10px;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: 2px;
}
.login-box {
  width: 950px;
  max-width: 95vw;
  background: rgba(255,255,255,0.15);
  border-radius: 10px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  backdrop-filter: blur(2px);
  box-shadow: 0 12px 32px rgba(0,0,0,0.15);
}
.left-visual {
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f5ff;
  border-top-left-radius: 10px;
  border-bottom-left-radius: 10px;
  overflow: hidden;
}
.visual-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.right-form {
  padding: 24px;
  background: #ffffff;
  border-top-right-radius: 10px;
  border-bottom-right-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.form-wrap {
  width: 100%;
  display: flex;
  justify-content: center;
}
.form-area {
  background: transparent;
  width: 340px;
  max-width: 100%;
}
.welcome {
  font-size: 24px;
  font-weight: 700;
  color: #1f2937;
  text-align: center;
  margin-top: -6px;
  margin-bottom: 18px;
}
.confirm-btn {
  width: 100%;
}
.actions-inline {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 10px;
  margin-top: -6px;
  font-size: 12px;
}
.sep {
  color: #cbd5e1;
}
 
</style>
