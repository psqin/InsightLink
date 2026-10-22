<template>
  <div class="register-bg">
    <div class="card">
      <div class="banner">
        <el-button class="back-btn" :icon="ArrowLeft" @click="goBack">返回</el-button>
        <img src="/images/21634504.jpeg" class="banner-img" />
      </div>
      <div class="body">
        <div class="title">用户注册</div>
        <el-form :model="form" :rules="rules" ref="formRef" label-position="top" size="large" class="form">
          <el-form-item prop="roleId" label="身份">
            <el-select v-model="form.roleId" placeholder="请选择身份" style="width: 100%">
              <el-option label="管理员" :value="1" />
              <el-option label="导师" :value="2" />
              <el-option label="学生" :value="3" />
            </el-select>
          </el-form-item>

          <el-form-item prop="realName" label="真实姓名">
            <el-input v-model="form.realName" placeholder="请输入真实姓名" clearable />
          </el-form-item>

          <el-form-item prop="phone" label="手机号">
            <el-input v-model="form.phone" placeholder="请输入手机号" clearable />
          </el-form-item>

          <el-form-item prop="password" label="密码">
            <el-input v-model="form.password" type="password" placeholder="请输入密码" show-password />
          </el-form-item>

          <el-collapse v-model="advanced" class="advanced">
            <el-collapse-item title="更多信息（可选）" name="more">
              <el-form-item prop="email" label="邮箱">
                <el-input v-model="form.email" placeholder="请输入邮箱" clearable />
              </el-form-item>

              <el-form-item prop="gender" label="性别">
                <el-select v-model="form.gender" placeholder="请选择性别" style="width: 100%">
                  <el-option label="保密" :value="0" />
                  <el-option label="男" :value="1" />
                  <el-option label="女" :value="2" />
                </el-select>
              </el-form-item>

              <el-form-item prop="birthday" label="出生年月">
                <el-date-picker
                  v-model="form.birthday"
                  type="date"
                  placeholder="请选择日期"
                  style="width: 100%"
                  value-format="YYYY-MM-DD"
                />
              </el-form-item>
            </el-collapse-item>
          </el-collapse>

          <el-form-item>
            <el-button type="primary" class="btn" :loading="loading" @click="onSubmit">注册</el-button>
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
const advanced = ref([])

const form = ref({
  roleId: 3,
  realName: '',
  phone: '',
  password: '',
  email: '',
  gender: 0,
  birthday: ''
})

const rules = {
  roleId: [{ required: true, message: '请选择身份', trigger: 'change' }],
  realName: [{ required: true, message: '请输入真实姓名', trigger: 'blur' }],
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1\d{10}$/, message: '手机号格式不正确', trigger: 'blur' }
  ],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  email: [
    {
      validator: (_, value, callback) => {
        if (!value) return callback()
        const ok = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)
        callback(ok ? undefined : new Error('邮箱格式不正确'))
      },
      trigger: 'blur'
    }
  ]
}

async function onSubmit() {
  try {
    await formRef.value.validate()
    loading.value = true
    await http.post('/user/register', {
      avatar: '',
      birthday: form.value.birthday || '',
      email: form.value.email || '',
      gender: form.value.gender ?? 0,
      password: form.value.password,
      phone: form.value.phone,
      realName: form.value.realName,
      roleId: form.value.roleId
    })
    ElMessage.success('注册成功，请登录')
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
.register-bg {
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
.advanced {
  margin-bottom: 10px;
}
.footer {
  display: flex;
  justify-content: center;
  margin-top: 6px;
  font-size: 12px;
}
</style>
