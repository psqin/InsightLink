<template>
  <div class="page">
    <div class="chat-container">
      <div class="contacts-sidebar">
        <div class="sidebar-header">联系人</div>
        <div class="contact-list" v-loading="loadingContacts">
          <div v-for="c in contacts" :key="c.id" 
               class="contact-item" :class="{ active: currentContact?.id === c.id }"
               @click="selectContact(c)">
            <el-avatar :size="40" :src="c.avatar || ''">{{ (c.realName || c.username)?.[0] || '?' }}</el-avatar>
            <div class="contact-info">
              <div class="contact-name">{{ c.realName || c.username }}</div>
              <div class="contact-desc" v-if="c.roleId === 2">导师</div>
              <div class="contact-desc" v-else-if="c.roleId === 3">学生</div>
            </div>
          </div>
          <el-empty v-if="contacts.length === 0 && !loadingContacts" description="暂无联系人" :image-size="60"></el-empty>
        </div>
      </div>
      
      <div class="chat-main" v-if="currentContact">
        <div class="chat-header">
          与 {{ currentContact.realName || currentContact.username }} 沟通中
        </div>
        
        <div class="chat-messages" ref="messagesRef" @scroll="handleScroll" v-loading="loadingHistory && messages.length === 0">
          <div v-if="loadingHistory && messages.length > 0" class="loading-more">
            <el-icon class="is-loading"><Loading /></el-icon> 加载中...
          </div>
          <div v-if="!loadingHistory && messages.length === 0" class="empty-chat">
            暂无沟通记录，发个消息打个招呼吧
          </div>
          <div v-for="m in messages" :key="m.id" class="message-wrapper" :class="{ 'is-me': m.senderId === store.userId }">
            <el-avatar class="msg-avatar" :size="36" :src="m.senderId === store.userId ? store.avatar : currentContact.avatar">
              {{ (m.senderId === store.userId ? store.realName : currentContact.realName)?.[0] || '?' }}
            </el-avatar>
            <div class="msg-content">
              <div class="msg-time" v-if="m.sendTime">{{ m.sendTime }}</div>
              <div class="msg-bubble">{{ m.content }}</div>
            </div>
          </div>
        </div>
        
        <div class="chat-input-area">
          <el-input 
            v-model="inputMsg" 
            type="textarea" 
            :rows="3" 
            resize="none"
            placeholder="输入留言内容，按 Enter 发送 (Shift+Enter 换行)"
            @keydown.enter="handleEnter"
          ></el-input>
          <div class="input-actions">
            <el-button type="primary" :disabled="!inputMsg.trim() || sending" :loading="sending" @click="sendMsg">发送</el-button>
          </div>
        </div>
      </div>
      
      <div class="chat-placeholder" v-else>
        <el-empty description="请选择左侧联系人开始沟通" :image-size="100"></el-empty>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import http from '../api/http'
import { useAppStore } from '../store'
import { ElMessage, ElNotification } from 'element-plus'
import { Loading, ChatLineRound } from '@element-plus/icons-vue'

const store = useAppStore()
const route = useRoute()
const router = useRouter()

const contacts = ref([])
const loadingContacts = ref(false)
const currentContact = ref(null)

const messages = ref([])
const loadingHistory = ref(false)
const historyPageSize = 20
const currentHistoryPage = ref(1)
const hasMoreHistory = ref(false)

const inputMsg = ref('')
const sending = ref(false)
const messagesRef = ref(null)

async function fetchContacts() {
  loadingContacts.value = true
  try {
    const { data } = await http.get('/message/contacts')
    let list = []
    if (data.code === 1) {
      list = data.data || []
    }

    // 1. Merge from route query
    const qId = route.query.contactId ? Number(route.query.contactId) : null
    if (qId) {
      if (!list.find(c => c.id === qId)) {
        list.unshift({
          id: qId,
          realName: route.query.contactName || '未知用户',
          roleId: route.query.contactRole ? Number(route.query.contactRole) : null,
          avatar: route.query.contactAvatar || ''
        })
      }
    }

    // 2. If student, ensure bound teacher is in the list
    if (store.roleId === 3) {
      try {
        const tRes = await http.get('/student/teacher')
        if (tRes.data?.code === 1 && tRes.data?.data) {
          const t = tRes.data.data
          if (t.userId && !list.find(c => c.id === t.userId)) {
            list.push({
              id: t.userId,
              realName: t.realName || '我的导师',
              roleId: 2,
              avatar: t.avatar || ''
            })
          }
        }
      } catch (e) {
        // ignore
      }
    }

    // 3. If teacher and list is still empty, fetch first page of students
    if (store.roleId === 2 && list.length === 0 && !qId) {
      try {
        const sRes = await http.get('/teacher/ts/page', { params: { page: 1, pageSize: 50 } })
        if (sRes.data?.code === 1 && sRes.data?.data?.records) {
          const students = sRes.data.data.records
          students.forEach(s => {
            if (s.userId && !list.find(c => c.id === s.userId)) {
              list.push({
                id: s.userId,
                realName: s.realName || s.studentNo,
                roleId: 3,
                avatar: s.avatar || ''
              })
            }
          })
        }
      } catch (e) {
        // ignore
      }
    }

    contacts.value = list

    if (qId) {
      const target = contacts.value.find(c => c.id === qId)
      if (target) {
        selectContact(target)
      }
    }
  } finally {
    loadingContacts.value = false
  }
}

async function fetchHistory(contactId) {
  if (!contactId) return
  loadingHistory.value = true
  messages.value = []
  hasMoreHistory.value = false
  currentHistoryPage.value = 1

  try {
    // 1. 获取第一页数据，同时得到总数
    const { data } = await http.get(`/message/history/${contactId}`, { params: { page: 1, pageSize: historyPageSize } })
    if (data.code !== 1) return
    
    const total = data.data?.total || 0
    if (total === 0) {
      messages.value = []
      return
    }

    const totalPages = Math.ceil(total / historyPageSize)

    if (totalPages === 1) {
      // 只有一页
      messages.value = data.data?.records || []
      scrollToBottom()
      return
    }

    // 超过一页时，第一页是最老的数据，我们需要的是最新的一页（即最后一页）
    currentHistoryPage.value = totalPages
    const res = await http.get(`/message/history/${contactId}`, { params: { page: currentHistoryPage.value, pageSize: historyPageSize } })
    let list = res.data?.data?.records || []

    // 如果最后一页数据太少（比如只有1条），导致不满一屏无法触发滚动，则再拉一页
    if (list.length < 10 && currentHistoryPage.value > 1) {
      currentHistoryPage.value -= 1
      const prevRes = await http.get(`/message/history/${contactId}`, { params: { page: currentHistoryPage.value, pageSize: historyPageSize } })
      const prevList = prevRes.data?.data?.records || []
      list = [...prevList, ...list]
    }

    messages.value = list
    hasMoreHistory.value = currentHistoryPage.value > 1

    scrollToBottom()
  } finally {
    loadingHistory.value = false
  }
}

async function loadMoreHistory() {
  if (!hasMoreHistory.value || loadingHistory.value || !currentContact.value) return
  
  loadingHistory.value = true
  
  // 保存当前滚动高度，用于加载后恢复位置
  const el = messagesRef.value
  const oldScrollHeight = el ? el.scrollHeight : 0
  
  try {
    currentHistoryPage.value -= 1
    const { data } = await http.get(`/message/history/${currentContact.value.id}`, { params: { page: currentHistoryPage.value, pageSize: historyPageSize } })
    if (data.code === 1) {
      const list = data.data?.records || []
      messages.value = [...list, ...messages.value]
      hasMoreHistory.value = currentHistoryPage.value > 1
      
      // 恢复滚动位置
      nextTick(() => {
        if (el) {
          const newScrollHeight = el.scrollHeight
          el.scrollTop = newScrollHeight - oldScrollHeight
        }
      })
    }
  } finally {
    loadingHistory.value = false
  }
}

function handleScroll(e) {
  if (e.target.scrollTop < 20) {
    loadMoreHistory()
  }
}

function selectContact(c) {
  if (currentContact.value?.id === c.id) return
  currentContact.value = c
  fetchHistory(c.id)
}

function scrollToBottom() {
  nextTick(() => {
    if (messagesRef.value) {
      messagesRef.value.scrollTop = messagesRef.value.scrollHeight
    }
  })
}

function handleEnter(e) {
  if (e.shiftKey) {
    return
  }
  e.preventDefault()
  if (inputMsg.value.trim()) {
    sendMsg()
  }
}

async function sendMsg() {
  if (!inputMsg.value.trim() || !currentContact.value) return
  sending.value = true
  try {
    const { data } = await http.post('/message', {
      content: inputMsg.value.trim(),
      receiverId: currentContact.value.id
    })
    if (data.code === 1) {
      inputMsg.value = ''
      await fetchHistory(currentContact.value.id)
    }
  } finally {
    sending.value = false
  }
}

watch(() => store.incomingMessage, (newMsg) => {
  if (!newMsg) return
  if (currentContact.value && String(currentContact.value.id) === String(newMsg.senderId)) {
    messages.value.push({
      id: 'ws_' + Date.now(),
      senderId: Number(newMsg.senderId),
      content: newMsg.content,
      sendTime: new Date().toLocaleString()
    })
    scrollToBottom()
  } else {
    // from someone else or no current contact
    ElNotification({
      title: '新消息',
      message: newMsg.content,
      position: 'top-right',
      customClass: 'modern-message-notification',
      icon: ChatLineRound,
      onClick: () => {
        const target = contacts.value.find(c => String(c.id) === String(newMsg.senderId))
        if (target) {
          selectContact(target)
        } else {
          router.push({ query: { contactId: newMsg.senderId } }).then(() => {
            fetchContacts()
          })
        }
      }
    })
  }
})

onMounted(() => {
  fetchContacts()
})
</script>

<style scoped>
.page {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.chat-container {
  flex: 1;
  display: flex;
  background: #ffffff;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  overflow: hidden;
  height: calc(100vh - 120px);
  min-height: 500px;
}
.contacts-sidebar {
  width: 280px;
  border-right: 1px solid #ebeef5;
  display: flex;
  flex-direction: column;
  background: #f9fafb;
}
.sidebar-header {
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  border-bottom: 1px solid #ebeef5;
  background: #fff;
  flex-shrink: 0;
}
.contact-list {
  flex: 1;
  overflow-y: auto;
}
.contact-item {
  display: flex;
  align-items: center;
  padding: 12px 20px;
  cursor: pointer;
  transition: background 0.2s;
}
.contact-item:hover {
  background: #f3f4f6;
}
.contact-item.active {
  background: #e5e7eb;
}
.contact-info {
  margin-left: 12px;
  flex: 1;
  overflow: hidden;
}
.contact-name {
  font-size: 14px;
  font-weight: 600;
  color: #111827;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.contact-desc {
  font-size: 12px;
  color: #6b7280;
  margin-top: 4px;
}

.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  min-width: 0;
}
.chat-header {
  height: 56px;
  display: flex;
  align-items: center;
  padding: 0 20px;
  font-size: 16px;
  font-weight: 700;
  color: #111827;
  border-bottom: 1px solid #ebeef5;
  flex-shrink: 0;
}
.chat-messages {
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: #f9fafb;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.loading-more {
  text-align: center;
  color: #999;
  font-size: 12px;
  padding: 10px 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
}
.empty-chat {
  text-align: center;
  color: #9ca3af;
  font-size: 14px;
  margin-top: 40px;
}
.message-wrapper {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  max-width: 80%;
}
.message-wrapper.is-me {
  align-self: flex-end;
  flex-direction: row-reverse;
}
.msg-avatar {
  flex-shrink: 0;
}
.msg-content {
  max-width: 70%;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.message-wrapper.is-me .msg-content {
  align-items: flex-end;
}
.msg-time {
  font-size: 12px;
  color: #9ca3af;
  margin-bottom: 4px;
}
.message-wrapper.is-me .msg-time {
  text-align: right;
}
.msg-bubble {
  background: #fff;
  border: 1px solid #ebeef5;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 14px;
  color: #111827;
  line-height: 1.5;
  word-break: break-word;
  white-space: pre-wrap;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.message-wrapper.is-me .msg-bubble {
  background: #409eff;
  border-color: #409eff;
  color: #fff;
}

.chat-input-area {
  padding: 16px 20px;
  border-top: 1px solid #ebeef5;
  background: #fff;
  flex-shrink: 0;
  display: flex;
  align-items: flex-end;
  gap: 12px;
}
.chat-input-area :deep(.el-textarea) {
  flex: 1;
}
.input-actions {
  display: flex;
  flex-shrink: 0;
}

.chat-placeholder {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f9fafb;
}
</style>