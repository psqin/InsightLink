import assert from 'node:assert/strict'
import test from 'node:test'
import { useAssistantExecution } from '../src/features/assistant/useAssistantExecution.js'
import { streamAssistantRequest } from '../src/api/assistantStream.js'

function scheduler() {
  const jobs = new Map()
  let id = 0
  return { jobs, setTimer: callback => { jobs.set(++id, callback); return id }, clearTimer: key => jobs.delete(key) }
}

const running = { id: 'execution-a', status: 'running', attempt: 1, can_resume: false }

test('cancel_requested remains active until server confirms cancelled and preserves task identity', async () => {
  const requests = []
  const terminal = []
  const clock = scheduler()
  const state = useAssistantExecution({
    post: async (path, payload) => { requests.push([path, payload]); return { data: { execution: { ...running, status: 'cancel_requested' } } } },
    get: async () => ({ data: { execution: { ...running, status: 'cancelled', can_resume: true } } })
  }, { ...clock, onTerminal: value => terminal.push(value) })
  state.observeConversation('chat-a', running)
  await state.cancelExecution()
  assert.deepEqual(requests, [['/api/chat/conversations/chat-a/execution/cancel', { execution_id: 'execution-a', attempt: 1 }]])
  assert.equal(state.active.value, true)
  assert.equal(state.canResume.value, false)
  assert.equal(state.canCancel.value, false)
  assert.match(state.statusLabel.value, /正在停止/)
  state.handleEvent('execution', running)
  assert.equal(state.execution.value.status, 'cancel_requested')
  await state.refreshExecution()
  assert.equal(state.active.value, false)
  assert.equal(state.canResume.value, true)
  assert.equal(terminal.length, 1)
  assert.equal(clock.jobs.size, 0)
})

test('lost cancel response verifies committing rather than claiming stopped', async () => {
  const errors = []
  const state = useAssistantExecution({
    post: async () => { throw new Error('lost response') },
    get: async () => ({ data: { execution: { ...running, status: 'committing' } } })
  }, { ...scheduler(), onError: error => errors.push(error) })
  state.observeConversation('chat-a', running)
  assert.equal(await state.cancelExecution(), false)
  assert.equal(state.execution.value.status, 'committing')
  assert.equal(state.active.value, true)
  assert.equal(state.canCancel.value, false)
  assert.match(state.statusLabel.value, /保存结果/)
  assert.equal(errors.length, 1)
})

test('weak network keeps stop state uncertain and continues verification', async () => {
  const clock = scheduler()
  const state = useAssistantExecution({
    post: async () => { throw new Error('offline') }, get: async () => { throw new Error('offline') }
  }, clock)
  state.observeConversation('chat-a', running)
  await state.cancelExecution()
  assert.equal(state.stateUncertain.value, true)
  assert.equal(state.execution.value.status, 'running')
  assert.match(state.statusLabel.value, /待核实/)
  assert.equal(clock.jobs.size, 1)
  state.disposeExecution()
  assert.equal(clock.jobs.size, 0)
})

test('late cancel and poll replies cannot affect a newly started task', async () => {
  let finishCancel
  let finishPoll
  const state = useAssistantExecution({
    post: () => new Promise(resolve => { finishCancel = resolve }),
    get: () => new Promise(resolve => { finishPoll = resolve })
  }, scheduler())
  state.observeConversation('chat-a', running)
  const cancel = state.cancelExecution()
  const poll = state.refreshExecution()
  const version = state.beginExecution('chat-a')
  state.handleEvent('session', { conversation_id: 'chat-a', execution_id: 'execution-b' }, version)
  state.handleEvent('execution', { id: 'execution-b', status: 'running', attempt: 1 }, version)
  finishCancel({ data: { execution: { ...running, status: 'cancelled' } } })
  finishPoll({ data: { execution: { ...running, status: 'completed' } } })
  await Promise.all([cancel, poll])
  assert.equal(state.execution.value.id, 'execution-b')
  assert.equal(state.execution.value.status, 'running')
  assert.equal(state.cancelBusy.value, false)
})

test('refresh observes existing tasks without executing them, terminal cannot regress, restore needs permission', async () => {
  const clock = scheduler()
  const state = useAssistantExecution({ get: async () => ({ data: { execution: { ...running, status: 'completed' } } }) }, clock)
  const version = state.observeConversation('chat-a', running)
  assert.equal(clock.jobs.size, 1)
  await state.refreshExecution()
  state.handleEvent('execution', running, version)
  assert.equal(state.execution.value.status, 'completed')
  assert.equal(state.canResume.value, false)
  state.observeConversation('chat-a', { ...running, status: 'failed', can_resume: false })
  assert.equal(state.canResume.value, false)
  const resumedVersion = state.beginExecution('chat-a')
  state.handleEvent('session', { conversation_id: 'chat-a', execution_id: running.id, attempt: 2 }, resumedVersion)
  state.handleEvent('execution', { ...running, attempt: 1, status: 'cancelled', can_resume: true }, resumedVersion)
  assert.equal(state.execution.value.status, 'running')
  assert.equal(state.execution.value.attempt, 2)
})

function sseResponse(frames) {
  return new Response(frames.map(([event, data]) => `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`).join(''),
    { headers: { 'Content-Type': 'text/event-stream' } })
}

test('confirmed cancellation without result is a controlled outcome, not a lost user message', async () => {
  const events = []
  const result = await streamAssistantRequest({ baseURL: 'http://agent', path: '/chat', payload: { message: '分析材料' },
    token: 'test-only', onEvent: (event, data) => events.push([event, data]),
    fetchImpl: async () => sseResponse([
      ['session', { conversation_id: 'chat-a', execution_id: running.id }],
      ['execution', { ...running, status: 'cancelled', can_resume: true }]
    ]) })
  assert.equal(result.interrupted, true)
  assert.equal(result.execution.status, 'cancelled')
  assert.equal(result.conversation_id, 'chat-a')
  assert.equal(events.length, 2)
})

test('stream ending with merely cancel_requested cannot report cancelled', async () => {
  await assert.rejects(streamAssistantRequest({ baseURL: 'http://agent', path: '/chat', payload: {},
    token: 'test-only', onEvent: () => {}, fetchImpl: async () => sseResponse([
      ['session', { conversation_id: 'chat-a' }], ['execution', { ...running, status: 'cancel_requested' }]
    ]) }), error => error.response?.data.conversation_id === 'chat-a' && /核实/.test(error.message))
})

test('resume stream sends execution identity and attempt, using supplied current token', async () => {
  let request
  const result = await streamAssistantRequest({ baseURL: 'http://agent/',
    path: '/api/chat/conversations/chat-a/execution/resume/stream', payload: { execution_id: running.id, attempt: 2 },
    token: 'fresh-test-only', onEvent: () => {}, fetchImpl: async (url, options) => {
      request = [url, options]
      return sseResponse([['result', { conversation_id: 'chat-a', answer: '已完成' }]])
    } })
  assert.equal(result.answer, '已完成')
  assert.equal(request[0], 'http://agent/api/chat/conversations/chat-a/execution/resume/stream')
  assert.deepEqual(JSON.parse(request[1].body), { execution_id: running.id, attempt: 2 })
  assert.equal(request[1].headers.token, 'fresh-test-only')
  assert.equal(request[0].includes('fresh-test-only'), false)
})
