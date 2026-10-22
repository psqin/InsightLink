<template>
  <el-container class="layout">
    <el-header class="header">
      <div class="header-left" @click="goHome">
        <div class="brand">InsightLink</div>
        <div class="subtitle">学业导师点评系统</div>
        <el-tag size="small" effect="light" class="role-tag">{{ roleLabel }}</el-tag>
      </div>
      <div class="header-right">
        <el-dropdown trigger="hover" placement="bottom-end">
          <div class="user">
            <el-avatar :size="30" :src="avatarUrl">{{ avatarFallback }}</el-avatar>
            <div class="name">{{ displayName }}</div>
            <el-icon class="chevron"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="goMyInfo">我的信息</el-dropdown-item>
              <el-dropdown-item divided @click="onLogout">退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>
    <el-container class="body">
      <el-aside width="208px" class="aside">
        <div class="aside-content">
          <el-menu :default-active="activePath" router class="menu">
            <template v-for="item in menuItems" :key="item.path">
              <el-sub-menu v-if="item.children && item.children.length" :index="item.path">
                <template #title>{{ item.label }}</template>
                <el-menu-item v-for="child in item.children" :key="child.path" :index="child.path">{{ child.label }}</el-menu-item>
              </el-sub-menu>
              <el-menu-item v-else :index="item.path">{{ item.label }}</el-menu-item>
            </template>
          </el-menu>

          <div class="weather-widget">
            <div v-if="weatherError" class="weather-msg">{{ weatherError }}</div>
            <div v-else-if="weatherLoading" class="weather-msg">获取天气中...</div>
            <div v-else-if="weatherData" class="weather-content">
              <div class="weather-top">
                <div class="weather-loc" :title="locationName">
                  <el-icon><Location /></el-icon>
                  {{ locationName }}
                </div>
                <div class="weather-time">{{ currentTime }}</div>
              </div>
              <div class="weather-main">
                <div class="weather-temp">
                  <el-icon :style="{ color: weatherData.color, fontSize: '28px', marginRight: '8px' }">
                    <component :is="weatherData.icon" />
                  </el-icon>
                  {{ weatherData.temp }}°
                </div>
                <div class="weather-desc">{{ weatherData.desc }}</div>
              </div>
            </div>
          </div>
        </div>
      </el-aside>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAppStore } from '../store'
import { ArrowDown, Location, Sunny, Moon, Cloudy, Pouring, Lightning, ChatLineRound } from '@element-plus/icons-vue'
import { ElNotification } from 'element-plus'

const route = useRoute()
const router = useRouter()
const store = useAppStore()

// WebSocket instance
let ws = null

function initWebSocket() {
  const userId = store.userId
  if (!userId) return

  // Create WebSocket connection
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const hostname = window.location.hostname || 'localhost'
  const wsUrl = `${protocol}//${hostname}:8080/ws/${userId}`
  
  ws = new WebSocket(wsUrl)
  
  ws.onopen = () => {
    console.log('WebSocket connected')
  }
  
  ws.onmessage = (event) => {
    try {
      const msg = JSON.parse(event.data)
      if (msg.type === 'chat_message') {
        store.setIncomingMessage(msg)
        
        // 消息页自行处理当前会话提示，其他页面才弹出全局通知。
        const isMessagesPage = route.path.includes('/message')
        if (!isMessagesPage) {
          ElNotification({
            title: '新消息',
            message: msg.content,
            position: 'top-right',
            customClass: 'modern-message-notification',
            icon: ChatLineRound,
            onClick: () => {
              const msgPath = store.roleId === 2 ? '/teacher/messages' : '/student/message'
              router.push({ path: msgPath, query: { contactId: msg.senderId } })
            }
          })
        }
      }
    } catch (e) {
      console.error('Failed to parse websocket message', e)
    }
  }
  
  ws.onclose = () => {
    console.log('WebSocket disconnected')
    // Optional: reconnect logic
    setTimeout(initWebSocket, 5000)
  }
  
  ws.onerror = (error) => {
    console.error('WebSocket error:', error)
  }
}

const activePath = computed(() => route.meta?.activeMenu || route.path)
const roleLabel = computed(() => {
  if (store.roleId === 1) return '管理员端'
  if (store.roleId === 2) return '导师端'
  return '学生端'
})
const homePath = computed(() => route.matched.map((r) => r.meta?.homePath).find(Boolean) || '/app')
const displayName = computed(() => store.realName || store.userName || '未命名用户')
const avatarUrl = computed(() => {
  const a = store.avatar
  if (!a) return ''
  if (/^https?:\/\//i.test(a)) return a
  if (a.startsWith('/')) return a
  return a
})
const avatarFallback = computed(() => {
  const name = displayName.value || ''
  return name.trim().slice(0, 1)
})
const menuItems = computed(() => {
  return route.matched.map((r) => r.meta?.menuItems).find((v) => Array.isArray(v) && v.length > 0) || []
})
const roleBase = computed(() => {
  if (store.roleId === 1) return '/admin'
  if (store.roleId === 2) return '/teacher'
  return '/student'
})

function goHome() {
  router.push(homePath.value)
}

function goMyInfo() {
  router.push(`${roleBase.value}/me/profile`)
}

function onLogout() {
  store.clearAuth()
  router.push('/login')
}

const weatherLoading = ref(false)
const weatherError = ref('')
const weatherData = ref(null)
const locationName = ref('未知')
const currentTime = ref('')

let timeTimer = null

function updateTime() {
  const d = new Date()
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  currentTime.value = `${h}:${m}`
}

function getWeatherInfo(code, isNight) {
  if (code === 0) return { desc: '晴', icon: isNight ? Moon : Sunny, color: isNight ? '#fbbf24' : '#f59e0b' }
  if (code === 1 || code === 2 || code === 3) return { desc: '多云', icon: Cloudy, color: '#9ca3af' }
  if (code === 45 || code === 48) return { desc: '雾', icon: Cloudy, color: '#d1d5db' }
  if (code >= 51 && code <= 67) return { desc: '雨', icon: Pouring, color: '#3b82f6' }
  if (code >= 71 && code <= 77) return { desc: '雪', icon: Cloudy, color: '#e5e7eb' }
  if (code >= 80 && code <= 82) return { desc: '阵雨', icon: Pouring, color: '#3b82f6' }
  if (code >= 85 && code <= 86) return { desc: '阵雪', icon: Cloudy, color: '#e5e7eb' }
  if (code >= 95 && code <= 99) return { desc: '雷阵雨', icon: Lightning, color: '#8b5cf6' }
  return { desc: '未知', icon: Cloudy, color: '#9ca3af' }
}

async function fetchWeather() {
  if (!navigator.geolocation) {
    weatherError.value = '不支持定位'
    return
  }
  weatherLoading.value = true
  weatherError.value = ''
  
  navigator.geolocation.getCurrentPosition(
    async (pos) => {
      try {
        const { latitude, longitude } = pos.coords
        
        try {
          const geoRes = await fetch(`https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${latitude}&longitude=${longitude}&localityLanguage=zh`)
          if (geoRes.ok) {
            const geoJson = await geoRes.json()
            locationName.value = geoJson.city || geoJson.locality || geoJson.principalSubdivision || '当前位置'
          }
        } catch (e) {
          console.error('获取位置名称失败', e)
          locationName.value = '当前位置'
        }
        
        const wRes = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${latitude}&longitude=${longitude}&current_weather=true&timezone=auto`)
        if (!wRes.ok) throw new Error('天气请求失败')
        const wJson = await wRes.json()
        
        if (wJson.current_weather) {
          const h = new Date().getHours()
          const isNight = h < 6 || h >= 18
          const info = getWeatherInfo(wJson.current_weather.weathercode, isNight)
          weatherData.value = {
            temp: Math.round(wJson.current_weather.temperature),
            desc: info.desc,
            icon: info.icon,
            color: info.color
          }
        } else {
          throw new Error('解析天气数据失败')
        }
      } catch (err) {
        console.error(err)
        weatherError.value = '获取天气失败'
      } finally {
        weatherLoading.value = false
      }
    },
    (err) => {
      console.error(err)
      weatherError.value = '无法获取定位'
      weatherLoading.value = false
    },
    { timeout: 10000, enableHighAccuracy: false }
  )
}

onMounted(() => {
  updateTime()
  timeTimer = setInterval(updateTime, 10000)
  fetchWeather()
  initWebSocket()
})

onUnmounted(() => {
  if (timeTimer) clearInterval(timeTimer)
  if (ws) {
    ws.onclose = null
    ws.close()
  }
})
</script>

<style scoped>
.layout {
  height: 100vh;
  background: var(--el-bg-color-page);
}
.header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
  z-index: 10;
  color: #ffffff;
}
.header-left {
  display: flex;
  align-items: baseline;
  gap: 12px;
  cursor: pointer;
  user-select: none;
  padding-left: 8px;
}
.role-tag {
  margin-left: 4px;
  border-radius: 6px;
  font-weight: 500;
  background-color: rgba(255, 255, 255, 0.2) !important;
  border-color: rgba(255, 255, 255, 0.3) !important;
  color: #ffffff !important;
}
.user {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 8px;
  transition: background-color 0.2s ease;
}
.user:hover {
  background-color: rgba(255, 255, 255, 0.15);
}
.chevron {
  color: rgba(255, 255, 255, 0.7);
  font-size: 12px;
  margin-left: -4px;
  transition: transform 0.2s ease;
}
.user:hover .chevron {
  color: #ffffff;
}
.name {
  font-size: 14px;
  color: #ffffff;
  font-weight: 600;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dropdown-line {
  display: inline-block;
  min-width: 180px;
}
.brand {
  font-size: 20px;
  font-weight: 800;
  letter-spacing: 0.5px;
  color: #ffffff;
}
.subtitle {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.8);
  font-weight: 500;
}
.body {
  height: calc(100vh - 60px);
}
.aside {
  background: #ffffff;
  border-right: 1px solid rgba(229, 231, 235, 0.5);
  box-shadow: 1px 0 4px rgba(0, 0, 0, 0.01);
  transition: width 0.3s;
  z-index: 5;
  display: flex;
  flex-direction: column;
}
.aside-content {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.menu {
  border-right: none;
  flex: 1;
  overflow-y: auto;
  padding-top: 8px;
}
:deep(.el-menu-item), :deep(.el-sub-menu__title) {
  margin: 4px 12px;
  border-radius: 8px;
  height: 44px;
  line-height: 44px;
}
:deep(.el-menu-item.is-active) {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  font-weight: 600;
}
:deep(.el-menu-item:hover), :deep(.el-sub-menu__title:hover) {
  background-color: #f3f4f6;
}
.main {
  min-width: 0;
  padding: 20px 24px;
  overflow-y: auto;
  overflow-x: hidden;
}

/* 天气组件样式 */
.weather-widget {
  margin: 16px 20px;
  padding: 12px 0;
  border-top: 1px dashed #e5e7eb;
  color: #374151;
  flex: none;
}
.weather-msg {
  font-size: 12px;
  color: #9ca3af;
  text-align: center;
  padding: 10px 0;
}
.weather-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.weather-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #9ca3af;
}
.weather-loc {
  display: flex;
  align-items: center;
  gap: 4px;
  font-weight: 500;
  max-width: 90px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.weather-time {
  font-family: monospace;
  font-weight: 600;
  font-size: 14px;
}
.weather-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.weather-temp {
  display: flex;
  align-items: center;
  font-size: 26px;
  font-weight: 800;
  color: #1f2937;
}
.weather-desc {
  font-size: 14px;
  font-weight: 600;
  color: #6b7280;
  background: #f3f4f6;
  padding: 4px 10px;
  border-radius: 12px;
}
</style>
