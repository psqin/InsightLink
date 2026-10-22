// 公开资料与授权学业数据使用不同措辞；失败状态不能沿用上一轮的成功标签。
export function reviewPresentation(harness, progress, error = false) {
  const status = harness?.review_status || progress?.review?.status
  const failed = Boolean(error || harness?.blocked || [
    'grader_error', 'failed', 'delivery_failed', 'max_iterations_reached', 'unverified', 'budget_exhausted'
  ].includes(status))
  const labels = {
    not_required: '本轮处理完成',
    satisfied: '结果已通过独立复核', skipped: '本轮无需独立复核',
    deterministic: harness?.task_type === 'public' ? '已核对公开来源' : '已核对授权数据',
    needs_revision: '正在根据复核意见修订', grader_error: '独立复核暂不可用',
    failed: '结果未通过复核', unverified: '公开来源尚不足以核实',
    delivery_failed: '文件交付检查未通过', max_iterations_reached: '答复修订后仍有结论未获证据支持',
    budget_exhausted: '达到本轮处理上限，答复尚未完成'
  }
  let label = labels[status] || ''
  if (failed && ['satisfied', 'skipped', 'deterministic'].includes(status)) {
    label = error ? '连接中断，结果尚未核对' : '本轮结果尚未通过核对'
  }
  return { failed, label }
}
