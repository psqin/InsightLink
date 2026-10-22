import DOMPurify from 'dompurify'
import { marked } from 'marked'

// 附件标记由 Agent 写入回答；每次创建新正则，避免全局匹配的 lastIndex 串扰。
function artifactPattern() {
  return /\[\[artifact:([0-9a-f-]{36}):([A-Za-z0-9._-]+)\]\]/g
}

export function conversationTitle(conversation) {
  const title = conversation.title?.replace(/\s+/g, ' ').trim()
  if (title) return title.length > 30 ? `${title.slice(0, 30)}…` : title
  return conversation.material_id ? '材料讨论' : '普通对话'
}

export function conversationDate(conversation) {
  const date = conversation.updated_at || conversation.created_at
  if (!date) return ''
  // Mongo 会话时间是带时区的 UTC ISO 字符串；先转换为浏览器本地时间再展示。
  const parsed = new Date(date)
  if (Number.isNaN(parsed.getTime())) return String(date).slice(0, 16).replace('T', ' ')
  const parts = new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false
  }).formatToParts(parsed)
  const value = Object.fromEntries(parts.map(part => [part.type, part.value]))
  return `${value.year}-${value.month}-${value.day} ${value.hour}:${value.minute}`
}

// 先移除附件占位符，再净化模型生成的 Markdown，避免直接插入不可信 HTML。
export function renderMarkdown(content) {
  return DOMPurify.sanitize(marked.parse((content || '').replace(artifactPattern(), ''), { breaks: true }))
}

export function messageArtifacts(content) {
  return [...(content || '').matchAll(artifactPattern())].map(match => ({ id: match[1], name: match[2] }))
}

export function materialTypeLabel(type) {
  return { 1: '学习计划', 2: '进度汇报', 3: '自我总结' }[type] || '学习材料'
}

// 内部材料 ID 仅用于请求；导师看到的是材料标题、学生与提交时间。
export function materialContextLabel(summary) {
  if (!summary) return '当前材料'
  const title = String(summary.title || '').trim() || '未命名材料'
  const parts = [`《${title}》`]
  if (summary.student_name) parts.push(summary.student_name)
  if (summary.submit_time) parts.push(String(summary.submit_time).slice(0, 16).replace('T', ' '))
  return parts.join(' · ')
}
