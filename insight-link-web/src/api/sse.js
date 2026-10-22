// 解析 POST fetch 的 SSE 响应，支持 UTF-8 分片、CRLF、多行 data 和心跳注释。
export async function consumeSSE(body, onEvent, onChunk = () => {}) {
  if (!body?.getReader) throw new Error('当前浏览器不支持流式响应')
  const reader = body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  const dispatch = (frame) => {
    let event = 'message'
    const lines = []
    for (const line of frame.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim()
      else if (line.startsWith('data:')) lines.push(line.slice(5).replace(/^ /, ''))
    }
    if (lines.length) onEvent(event, JSON.parse(lines.join('\n')))
  }
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (value) onChunk()
      buffer += decoder.decode(value, { stream: !done })
      // 保留末尾的 CR，以便下一个分片中的 LF 一起归一化。
      buffer = buffer.replace(/\r\n/g, '\n')
      let boundary
      while ((boundary = buffer.indexOf('\n\n')) !== -1) {
        dispatch(buffer.slice(0, boundary))
        buffer = buffer.slice(boundary + 2)
      }
      if (buffer.length > 256 * 1024) throw new Error('流式响应过大，请重新打开对话查看结果')
      if (done) break
    }
  } finally {
    await reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}
