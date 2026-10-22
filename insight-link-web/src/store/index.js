import { defineStore } from 'pinia'

function readJson(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return fallback
    return JSON.parse(raw)
  } catch {
    return fallback
  }
}

export const useAppStore = defineStore('app', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: readJson('user', null),
    incomingMessage: null
  }),
  getters: {
    roleId: (s) => s.user?.roleId ?? 0,
    realName: (s) => s.user?.realName ?? '',
    avatar: (s) => s.user?.avatar ?? '',
    userName: (s) => s.user?.userName ?? '',
    userId: (s) => s.user?.id ?? 0
  },
  actions: {
    setToken(t) {
      this.token = t
      localStorage.setItem('token', t || '')
    },
    setUser(u) {
      this.user = u || null
      localStorage.setItem('user', JSON.stringify(this.user))
    },
    setIncomingMessage(msg) {
      this.incomingMessage = msg
    },
    clearToken() {
      this.setToken('')
    },
    clearUser() {
      this.setUser(null)
    },
    clearAuth() {
      this.clearToken()
      this.clearUser()
    }
  }
})
