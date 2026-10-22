import axios from 'axios'
import { useAppStore } from '../store'
import { ElMessage } from 'element-plus'
import router from '../router'

const baseURL = import.meta.env.VITE_API_BASE ?? ''

const http = axios.create({
  baseURL,
  timeout: 15000
})

http.interceptors.request.use((config) => {
  const store = useAppStore()
  if (store.token) {
    config.headers.token = store.token
  }
  return config
})

http.interceptors.response.use(
  (resp) => {
    const payload = resp?.data
    const rawCode = payload?.code
    const normalizedCode =
      typeof rawCode === 'number' ? rawCode : typeof rawCode === 'string' ? Number(rawCode) : undefined
    const isKnownCode = typeof normalizedCode === 'number' && !Number.isNaN(normalizedCode)
    if (payload && isKnownCode && normalizedCode !== 1) {
      const msg = payload?.msg || '操作失败'
      ElMessage.error(msg)
      const err = new Error(msg)
      err._notified = true
      err.data = payload
      err.response = resp
      return Promise.reject(err)
    }
    return resp
  },
  (error) => {
    const status = error?.response?.status
    if (status === 401) {
      const store = useAppStore()
      store.clearAuth()
      if (!error?._notified) {
        ElMessage.error('登录已过期，请重新登录')
        error._notified = true
      }
      const currentPath = router?.currentRoute?.value?.path
      if (currentPath && currentPath !== '/login') {
        router.push('/login')
      }
      return Promise.reject(error)
    }
    const msg =
      error?.response?.data?.msg ||
      error?.response?.data?.message ||
      error?.data?.msg ||
      error?.message ||
      '请求失败'
    ElMessage.error(msg)
    error._notified = true
    return Promise.reject(error)
  }
)

export default http
