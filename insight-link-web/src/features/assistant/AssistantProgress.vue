<template>
  <details class="execution-progress" :class="{ 'execution-error': failed }" :open="busy || undefined">
    <summary><span v-if="busy" class="progress-spinner" /><span v-else class="progress-mark">{{ stopped ? '■' : failed ? '!' : '✓' }}</span>{{ title }}<span class="progress-expand">查看过程</span></summary>
    <div class="progress-detail">
      <ol v-if="plan.length" class="progress-plan"><li v-for="step in plan" :key="step.id" :class="`step-${step.status}`"><span>{{ step.content }}</span><span class="step-status">{{ stepLabel(step.status) }}</span></li></ol>
      <ul v-if="activities.length" class="progress-activities">
        <li v-for="item in activities" :key="item.id"><span>{{ item.kind === 'subagent' ? '✦ ' : '' }}{{ item.label }}</span><span :class="{ 'activity-failed': item.status === 'failed' }">{{ statusLabel(item.status) }}</span></li>
      </ul>
      <p v-if="reviewLabel" class="progress-review">{{ reviewLabel }}</p>
      <p v-if="busy" class="progress-note">正在处理你的问题；正式评价与留言仍需你确认。</p>
      <p v-if="failed" class="progress-note">具体原因请查看本轮答复；已结束的任务不会因重新打开对话而自动重跑。</p>
    </div>
  </details>
</template>

<script setup>
import { computed } from 'vue'
import { reviewPresentation } from './assistantProgressLabels'
const props = defineProps({ progress: Object, harness: Object, execution: Object, busy: Boolean, error: Boolean })
const review = computed(() => reviewPresentation(props.harness, props.progress, props.error))
const stopped = computed(() => ['cancelled', 'interrupted'].includes(props.execution?.status))
const failed = computed(() => props.execution?.status === 'failed' || review.value.failed)
// 流式状态和刷新后恢复的状态使用同一份步骤契约，兼容旧的文字计划。
const plan = computed(() => {
  const steps = props.progress?.planSteps?.length ? props.progress.planSteps : props.harness?.plan_steps
  if (steps?.length) return steps
  const titles = props.progress?.plan?.length ? props.progress.plan : props.harness?.plan || []
  return titles.map((content, index) => ({ id: `template-${index}`, content, status: 'pending' }))
})
const activities = computed(() => (props.progress?.activities || []).slice(-6))
// 停止和保存阶段优先采用执行状态，不能把“流结束”误报为“处理完成”。
const title = computed(() => ({ cancel_requested: '正在停止，等待当前操作退出', committing: '正在保存结果',
  cancelled: '本轮任务已停止', interrupted: '本轮任务已中断', failed: '本轮任务未完成' })[props.execution?.status]
  || (props.error ? '连接暂时中断' : props.busy ? props.progress?.label || '正在准备' : failed.value ? '本轮结果尚未通过核对' : props.progress?.label || '本轮处理完成'))
const reviewLabel = computed(() => stopped.value ? '' : review.value.label)
function statusLabel(status) { return ({ running: props.busy ? '进行中' : '状态待核对', completed: '完成', failed: '未完成' })[status] || '' }
function stepLabel(status) { return ({ pending: '待处理', in_progress: '进行中', completed: '已完成' })[status] || '待核对' }
</script>

<style scoped>
.execution-progress { margin: 0 0 0 40px; padding: 11px 14px; border: 1px solid #e4eaf1; border-radius: 11px; background: #fafbfd; color: #596b80; font-size: 12px; }
summary { display: flex; align-items: center; gap: 8px; cursor: pointer; list-style: none; }
summary::-webkit-details-marker { display: none; }
.progress-expand { margin-left: auto; color: #8896a7; font-size: 11px; }
.progress-mark { color: #4d8379; font-weight: 700; }
.execution-error .progress-mark { color: #b6753f; }
.progress-detail { padding: 10px 0 1px 20px; }
.progress-plan { display: grid; gap: 6px; margin: 0; padding-left: 17px; line-height: 1.6; }
.progress-plan li { padding-left: 2px; }
.step-status { margin-left: 12px; color: #8a99a9; font-size: 11px; white-space: nowrap; }
.step-in_progress { color: #3f72a8; }
.step-completed .step-status { color: #4d8379; }
.progress-activities { display: grid; gap: 7px; margin: 12px 0 0; padding: 10px 0 0; border-top: 1px solid #e8edf3; list-style: none; }
.progress-activities li { display: flex; justify-content: space-between; gap: 12px; }
.progress-activities li > span:last-child { color: #8a99a9; white-space: nowrap; }
.progress-activities .activity-failed { color: #b6753f !important; }
.progress-note { color: #8a99a9; font-size: 11px; line-height: 1.7; }
.progress-review { margin-bottom: 0; color: #526f90; }
.progress-spinner { width: 11px; height: 11px; border: 2px solid #d8e7fa; border-top-color: #4c87ca; border-radius: 50%; animation: spin .9s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { .progress-spinner { animation: none; } }
</style>
