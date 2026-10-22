import assert from 'node:assert/strict'
import test from 'node:test'
import { useAssistantSkills } from '../src/features/assistant/useAssistantSkills.js'

test('personal skill creation and update encode Chinese names and carry explicit versions', async () => {
  const calls = []
  const state = useAssistantSkills({
    get: async path => ({ data: path.endsWith('/skills') ? { items: [] } : { name: '材料对比', version: 8 } }),
    put: async (path, body) => { calls.push([path, body]); return { data: { name: '材料对比' } } }
  })
  await state.saveSkill('材料对比', { description: '  分析不同材料  ', instructions: '  第一步核对材料。  ' }, 0)
  await state.saveSkill('材料对比', { description: '新的场景', instructions: '新的步骤' }, 8)
  assert.equal(calls[0][0], `/api/chat/skills/${encodeURIComponent('材料对比')}`)
  assert.deepEqual(calls[0][1], { description: '分析不同材料', instructions: '第一步核对材料。', expected_version: 0 })
  assert.equal(calls[1][1].expected_version, 8)
  assert.equal(state.selected.value.name, '材料对比')
})

test('skill toggling and deletion use the displayed current version and export requests a token client blob', async () => {
  const calls = []
  const state = useAssistantSkills({
    get: async (path, config) => { calls.push(['get', path, config]); return { data: { items: [] } } },
    patch: async (path, body) => { calls.push(['patch', path, body]); return { data: { enabled: false } } },
    delete: async (path, config) => { calls.push(['delete', path, config]); return {} }
  })
  const skill = { name: '报告检查', version: 7 }
  await state.toggleSkill(skill, false)
  await state.exportSkill(skill)
  state.selected.value = skill
  await state.deleteSkill(skill)
  assert.deepEqual(calls.find(call => call[0] === 'patch')[2], { enabled: false, expected_version: 7 })
  assert.deepEqual(calls.find(call => call[0] === 'delete')[2], { params: { expected_version: 7 } })
  assert.deepEqual(calls.find(call => call[1].endsWith('/export'))[2], { responseType: 'blob' })
  assert.equal(state.selected.value, null)
})

test('late skill details cannot reopen an old selection after switching or closing the editor', async () => {
  const pending = []
  const state = useAssistantSkills({ get: () => new Promise(resolve => pending.push(resolve)) })
  const first = state.selectSkill('旧技能')
  const second = state.selectSkill('新技能')
  pending[1]({ data: { name: '新技能' } })
  await second
  pending[0]({ data: { name: '旧技能' } })
  await first
  assert.equal(state.selected.value.name, '新技能')
  const third = state.selectSkill('离开后')
  state.clearSelection()
  pending[2]({ data: { name: '离开后' } })
  await third
  assert.equal(state.selected.value, null)
})

test('a skill version conflict never silently refreshes or retries and keeps the displayed snapshot', async () => {
  let writes = 0
  let reads = 0
  const conflict = Object.assign(new Error('技能版本已变化'), { response: { status: 409 } })
  const state = useAssistantSkills({
    get: async () => { reads += 1; return { data: {} } },
    put: async () => { writes += 1; throw conflict }
  })
  state.selected.value = { name: '保留草稿', version: 4 }
  await assert.rejects(state.saveSkill('保留草稿', { description: '说明', instructions: '步骤' }, 4), conflict)
  assert.equal(writes, 1)
  assert.equal(reads, 0)
  assert.deepEqual(state.selected.value, { name: '保留草稿', version: 4 })
})
