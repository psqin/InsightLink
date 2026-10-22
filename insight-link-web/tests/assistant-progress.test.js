import assert from 'node:assert/strict'
import test from 'node:test'
import { useAssistantProgress } from '../src/features/assistant/useAssistantProgress.js'
import { reviewPresentation } from '../src/features/assistant/assistantProgressLabels.js'

test('dynamic step status changes are kept and saved results restore without auto-completing approval', () => {
  const state = useAssistantProgress()
  const pending = [{ id: 'one', content: '读取材料', status: 'in_progress' },
    { id: 'approval', content: '等待导师确认', status: 'pending' }]
  state.handleProgress('plan', { items: pending.map(step => step.content), steps: pending, source: 'model' })
  assert.equal(state.progress.value.planSteps[0].status, 'in_progress')
  const updated = [{ ...pending[0], status: 'completed' }, pending[1]]
  state.handleProgress('plan', { items: updated.map(step => step.content), steps: updated, source: 'model' })
  assert.equal(state.progress.value.planSteps[0].status, 'completed')
  assert.equal(state.progress.value.planSteps[1].status, 'pending')
  const harness = { plan_steps: updated, plan_source: 'model' }
  state.completeProgress({ harness, pending_action: { id: 'test' } })
  assert.equal(state.progress.value.label, '等待确认操作')
  state.resetProgress(harness)
  assert.equal(state.progress.value, null)
  assert.equal(state.harness.value.plan_steps[1].status, 'pending')
})

test('legacy plan events remain supported', () => {
  const state = useAssistantProgress()
  state.handleProgress('plan', { items: ['授权查询', '回答问题'] })
  assert.deepEqual(state.progress.value.plan, ['授权查询', '回答问题'])
  assert.deepEqual(state.progress.value.planSteps, [])
})

test('public review labels name public sources and blocked results never claim success', () => {
  assert.deepEqual(reviewPresentation({ task_type: 'public', review_status: 'deterministic' }), {
    failed: false, label: '已核对公开来源'
  })
  assert.equal(reviewPresentation({ task_type: 'academic', review_status: 'deterministic' }).label, '已核对授权数据')
  assert.deepEqual(reviewPresentation({ task_type: 'public', review_status: 'deterministic', blocked: true }), {
    failed: true, label: '本轮结果尚未通过核对'
  })
  assert.equal(reviewPresentation({ review_status: 'failed' }).failed, true)
  assert.equal(reviewPresentation({ review_status: 'delivery_failed' }).failed, true)
  assert.deepEqual(reviewPresentation({ review_status: 'budget_exhausted' }), {
    failed: true, label: '达到本轮处理上限，答复尚未完成'
  })
  assert.equal(reviewPresentation({ review_status: 'deterministic' }, null, true).label, '连接中断，结果尚未核对')
})
