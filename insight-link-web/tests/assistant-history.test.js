import assert from 'node:assert/strict'
import test from 'node:test'
import { useAssistantHistory } from '../src/features/assistant/useAssistantHistory.js'

test('history passes page and title search to the API instead of filtering the first 20 locally', async () => {
  const requests = []
  const state = useAssistantHistory({ get: async (path, config) => {
    requests.push([path, config.params])
    return { data: { items: [{ id: 'owned' }], total: 42 } }
  } })
  state.keyword.value = '  学情分析  '
  await state.loadConversations(2)
  assert.deepEqual(requests, [['/api/chat/conversations', { page: 2, page_size: 20, keyword: '学情分析' }]])
  assert.equal(state.page.value, 2)
  assert.equal(state.total.value, 42)
  assert.deepEqual(state.conversations.value, [{ id: 'owned' }])
})

test('late history search responses cannot replace the current search or revive a disposed page', async () => {
  const pending = []
  const state = useAssistantHistory({ get: () => new Promise(resolve => pending.push(resolve)) })
  const first = state.loadConversations()
  state.keyword.value = '新的标题'
  const second = state.loadConversations()
  pending[1]({ data: { items: [{ id: 'new' }], total: 1 } })
  await second
  pending[0]({ data: { items: [{ id: 'old' }], total: 10 } })
  await first
  assert.deepEqual(state.conversations.value, [{ id: 'new' }])
  const third = state.loadConversations()
  state.disposeHistory()
  pending[2]({ data: { items: [{ id: 'disposed' }], total: 2 } })
  await third
  assert.deepEqual(state.conversations.value, [{ id: 'new' }])
})

test('deleting the last item on a later history page returns to an existing page', async () => {
  const requested = []
  const state = useAssistantHistory({ get: async (_path, config) => {
    requested.push(config.params.page)
    return { data: { items: config.params.page === 1 ? [{ id: 'remaining' }] : [], total: 20 } }
  } })
  await state.loadConversations(2)
  assert.deepEqual(requested, [2, 1])
  assert.equal(state.page.value, 1)
  assert.equal(state.historyLoading.value, false)
  assert.deepEqual(state.conversations.value, [{ id: 'remaining' }])
})
