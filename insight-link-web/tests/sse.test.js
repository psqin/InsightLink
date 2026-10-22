import assert from 'node:assert/strict'
import test from 'node:test'
import { consumeSSE } from '../src/api/sse.js'

// 用逐字节分片验证中文、CRLF 和多行 data；不能假设一个网络分片就是一个事件。
test('SSE accepts UTF-8 byte boundaries, CRLF, multiline JSON and heartbeats', async () => {
  const source = ': heartbeat\r\n\r\nevent: phase\r\ndata: {"label":\r\ndata: "正在复核"}\r\n\r\nevent: result\ndata: {"answer":"完成"}\n\n'
  const bytes = new TextEncoder().encode(source)
  const body = new ReadableStream({ start(controller) {
    for (const byte of bytes) controller.enqueue(Uint8Array.of(byte))
    controller.close()
  } })
  const events = []
  let activity = 0
  await consumeSSE(body, (event, data) => events.push([event, data]), () => { activity += 1 })
  assert.deepEqual(events, [['phase', { label: '正在复核' }], ['result', { answer: '完成' }]])
  assert.equal(activity, bytes.length)
})

test('truncated frames cannot become successful replies', async () => {
  const events = []
  const body = new Response('event: result\ndata: {"answer":"incomplete').body
  await consumeSSE(body, (...event) => events.push(event))
  assert.deepEqual(events, [])
})

test('invalid event JSON stops consumption and releases reader', async () => {
  const body = new Response('event: result\ndata: not-json\n\n').body
  await assert.rejects(consumeSSE(body, () => {}), SyntaxError)
  assert.equal(body.locked, false)
})
