<template>
  <div class="page">
    <div class="card">
      <div class="title">数据概览</div>
      <div class="hint">提示：展示系统核心数据统计与趋势</div>

      <!-- 概览数据已删除 -->

      <div class="section">
        <div class="section-title">核心统计图</div>
        <el-skeleton :loading="overviewLoading" animated>
          <template #template>
            <el-skeleton-item variant="rect" style="height: 220px" />
          </template>
          <template #default>
            <div v-if="!overview" class="empty">暂无数据</div>
            <div v-else class="chart-grid">
              <div class="chart-card">
                <div class="chart-title">用户角色分布</div>
                <v-chart :option="userRolePieOption" autoresize style="height: 240px" />
                <div class="total-line"><span class="total-chip">总数：{{ n(overview.users?.total) }}</span></div>
              </div>
              <div class="chart-card">
                <div class="chart-title">材料类型分布</div>
                <v-chart :option="materialTypePieOption" autoresize style="height: 240px" />
                <div class="total-line"><span class="total-chip">总数：{{ n(overview.materials?.total) }}</span></div>
              </div>
              <div class="chart-card">
                <div class="chart-title">通知类型分布</div>
                <v-chart :option="noticeTypePieOption" autoresize style="height: 240px" />
                <div class="total-line">
                  <span class="total-chip">总数：{{ n(overview.notices?.system) + n(overview.notices?.teacher) }}</span>
                </div>
              </div>
              <div class="chart-card">
                <div class="chart-title">学校结构</div>
                <v-chart :option="schoolsPieOption" autoresize style="height: 240px" />
                <div class="total-line">
                  <span class="total-chip">
                    总数：{{ n(overview.schools?.universities) + n(overview.schools?.colleges) + n(overview.schools?.majors) + n(overview.schools?.classes) }}
                  </span>
                </div>
              </div>
              <div class="chart-card">
                <div class="chart-title">材料批阅情况</div>
                <v-chart :option="evaluatedPieOption" autoresize style="height: 240px" />
                <div class="total-line">
                  <span class="total-chip">
                    总数：{{ n(overview.rates?.evaluatedRate?.evaluatedMaterials) + n(overview.rates?.evaluatedRate?.unEvaluatedMaterials) }}
                  </span>
                </div>
              </div>
              <div class="chart-card">
                <div class="chart-title">学生绑定情况</div>
                <v-chart :option="bindPieOption" autoresize style="height: 240px" />
                <div class="total-line"><span class="total-chip">总数：{{ n(overview.rates?.bindRate?.studentsTotal) }}</span></div>
              </div>
            </div>
          </template>
        </el-skeleton>
      </div>

      <div class="section">
        <div class="section-title">学校维度分布</div>
        <el-skeleton :loading="schoolLoading" animated>
          <template #template>
            <el-skeleton-item variant="text" style="width: 220px" />
            <el-skeleton-item variant="rect" style="margin-top: 12px; height: 220px" />
          </template>
          <template #default>
            <div class="dist-grid">
              <div class="dist-card">
                <div class="dist-title">学生分布（按学校）</div>
                <v-chart :option="studentsByUniversityBar" autoresize style="height: 260px" />
              </div>
              <div class="dist-card">
                <div class="dist-title">导师分布（按学校）</div>
                <v-chart :option="teachersByUniversityBar" autoresize style="height: 260px" />
              </div>
            </div>
          </template>
        </el-skeleton>
      </div>

      <div class="section">
        <div class="section-title">近N日趋势数据（折线图）</div>
        <div class="trend-filter">
          <el-select v-model="days" style="width: 120px">
            <el-option :value="7" label="近7日" />
            <el-option :value="14" label="近14日" />
            <el-option :value="30" label="近30日" />
          </el-select>
        </div>
        <el-skeleton :loading="trendLoading" animated>
          <template #template>
            <el-skeleton-item variant="text" style="width: 140px" />
          </template>
          <template #default>
            <div v-if="!trend || !trend.labels || trend.labels.length === 0" class="empty">暂无数据</div>
            <v-chart :option="trendLineOption" autoresize style="height: 360px" />
          </template>
        </el-skeleton>
      </div>
    </div>
  </div>
  </template>

<script setup>
import { onMounted, ref, watch, computed } from 'vue'
import http from '../api/http'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, LineChart, BarChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, TitleComponent, GridComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, PieChart, LineChart, BarChart, TooltipComponent, LegendComponent, TitleComponent, GridComponent])

const overview = ref(null)
const schoolDist = ref({})
const trend = ref({ labels: [], series: {} })
const days = ref(7)

const overviewLoading = ref(false)
const schoolLoading = ref(false)
const trendLoading = ref(false)

function n(v) {
  const num = Number(v)
  return Number.isFinite(num) ? num : 0
}

function pct(v) {
  const num = Number(v)
  if (!Number.isFinite(num)) return '0%'
  return `${num}%`
}

function rateWidth(v) {
  const num = Number(v)
  if (!Number.isFinite(num)) return '0%'
  const clamped = Math.max(0, Math.min(100, num))
  return `${clamped}%`
}

function trendLabel(k) {
  const map = {
    usersTotal: '用户总数',
    admins: '管理员',
    teachers: '导师',
    students: '学生',
    materialsTotal: '材料总数',
    typePlan: '学习计划',
    typeReport: '进度汇报',
    typeSummary: '自我总结',
    evaluationsTotal: '批阅总数',
    noticesSystem: '系统通知',
    noticesTeacher: '导师通知',
    bindingsTotal: '绑定总数'
  }
  return map[k] || k
}

const userRolePieOption = computed(() => {
  const users = overview.value?.users || {}
  return {
    tooltip: { trigger: 'item', formatter: (p) => `${p.name}: ${p.value}（${p.percent}%）` },
    legend: { bottom: 0, icon: 'circle' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        avoidLabelOverlap: true,
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: true, formatter: '{b}: {c}' },
        data: [
          { name: '管理员', value: Number(users.admins) || 0 },
          { name: '导师', value: Number(users.teachers) || 0 },
          { name: '学生', value: Number(users.students) || 0 }
        ]
      }
    ]
  }
})

const materialTypePieOption = computed(() => {
  const materials = overview.value?.materials || {}
  return {
    tooltip: { trigger: 'item', formatter: (p) => `${p.name}: ${p.value}（${p.percent}%）` },
    legend: { bottom: 0, icon: 'circle' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: true, formatter: '{b}: {c}' },
        data: [
          { name: '学习计划', value: Number(materials.typePlan) || 0 },
          { name: '进度汇报', value: Number(materials.typeReport) || 0 },
          { name: '自我总结', value: Number(materials.typeSummary) || 0 }
        ]
      }
    ]
  }
})

const noticeTypePieOption = computed(() => {
  const notices = overview.value?.notices || {}
  return {
    tooltip: { trigger: 'item', formatter: (p) => `${p.name}: ${p.value}（${p.percent}%）` },
    legend: { bottom: 0, icon: 'circle' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: true, formatter: '{b}: {c}' },
        data: [
          { name: '系统', value: Number(notices.system) || 0 },
          { name: '导师', value: Number(notices.teacher) || 0 }
        ]
      }
    ]
  }
})

const schoolsPieOption = computed(() => {
  const s = overview.value?.schools || {}
  return {
    tooltip: { trigger: 'item', formatter: (p) => `${p.name}: ${p.value}（${p.percent}%）` },
    legend: { bottom: 0, icon: 'circle' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: true, formatter: '{b}: {c}' },
        data: [
          { name: '学校', value: Number(s.universities) || 0 },
          { name: '学院', value: Number(s.colleges) || 0 },
          { name: '专业', value: Number(s.majors) || 0 },
          { name: '班级', value: Number(s.classes) || 0 }
        ]
      }
    ]
  }
})

const evaluatedPieOption = computed(() => {
  const rate = overview.value?.rates?.evaluatedRate || {}
  return {
    tooltip: { trigger: 'item', formatter: (p) => `${p.name}: ${p.value}（${p.percent}%）` },
    legend: { bottom: 0, icon: 'circle' },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: true, formatter: '{b}: {c}' },
        data: [
          { name: '已批阅', value: Number(rate.evaluatedMaterials) || 0 },
          { name: '未批阅', value: Number(rate.unEvaluatedMaterials) || 0 }
        ]
      }
    ]
  }
})

const bindPieOption = computed(() => {
  const rate = overview.value?.rates?.bindRate || {}
  return {
    tooltip: { trigger: 'item', formatter: (p) => `${p.name}: ${p.value}（${p.percent}%）` },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: ['40%', '70%'],
        itemStyle: { borderRadius: 6, borderColor: '#fff', borderWidth: 2 },
        label: { show: true, formatter: '{b}: {c}' },
        data: [
          { name: '已绑定', value: Number(rate.boundStudents) || 0 },
          { name: '未绑定', value: Number(rate.unboundStudents) || 0 }
        ]
      }
    ]
  }
})

const studentsByUniversityBar = computed(() => {
  const list = overview.value && schoolDist.value?.studentsByUniversity ? schoolDist.value.studentsByUniversity : []
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
    xAxis: { type: 'category', data: list.map((i) => i?.name || '-') },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', name: '学生数', data: list.map((i) => Number(i?.count) || 0) }]
  }
})

const teachersByUniversityBar = computed(() => {
  const list = overview.value && schoolDist.value?.teachersByUniversity ? schoolDist.value.teachersByUniversity : []
  return {
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
    xAxis: { type: 'category', data: list.map((i) => i?.name || '-') },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', name: '导师数', data: list.map((i) => Number(i?.count) || 0) }]
  }
})

const trendLineOption = computed(() => {
  const labels = trend.value?.labels || []
  const s = trend.value?.series || {}
  function arr(k) {
    const a = s[k]
    return Array.isArray(a) ? a.map((v) => Number(v) || 0) : []
  }
  const series = [
    { name: '用户总数', data: arr('usersTotal') },
    { name: '学生', data: arr('students') },
    { name: '导师', data: arr('teachers') },
    { name: '材料总数', data: arr('materialsTotal') },
    { name: '系统通知', data: arr('noticesSystem') },
    { name: '绑定总数', data: arr('bindingsTotal') }
  ].map((it) => ({ type: 'line', smooth: true, symbolSize: 6, ...it }))
  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, icon: 'circle' },
    grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: labels },
    yAxis: { type: 'value' },
    series
  }
})

async function fetchOverview() {
  overviewLoading.value = true
  try {
    const { data } = await http.get('/admin/report/overview')
    overview.value = data?.data || null
  } finally {
    overviewLoading.value = false
  }
}

async function fetchSchool() {
  schoolLoading.value = true
  try {
    const { data } = await http.get('/admin/report/distribution/school')
    schoolDist.value = data?.data || {}
  } finally {
    schoolLoading.value = false
  }
}

async function fetchTrend() {
  trendLoading.value = true
  try {
    const { data } = await http.get('/admin/report/trend', { params: { days: days.value } })
    trend.value = data?.data || { labels: [], series: {} }
  } finally {
    trendLoading.value = false
  }
}

onMounted(() => {
  fetchOverview()
  fetchSchool()
  fetchTrend()
})

watch(days, () => {
  fetchTrend()
})
</script>

<style scoped>
.page {
  height: 100%;
}
.card {
  background: #ffffff;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 18px 20px;
}
.title {
  font-size: 16px;
  font-weight: 700;
  color: #111827;
}
.hint {
  margin-top: 8px;
  font-size: 12px;
  color: #6b7280;
}
.section {
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 14px 16px;
  margin-top: 14px;
}
.section-title {
  font-size: 13px;
  font-weight: 800;
  color: #111827;
  margin-bottom: 10px;
}
.empty {
  font-size: 12px;
  color: #6b7280;
}
.overview-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.tile {
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 12px 14px;
}
.tile-title {
  font-size: 13px;
  font-weight: 800;
  color: #111827;
}
.tile-main {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin-top: 6px;
}
.num {
  font-size: 28px;
  font-weight: 900;
  color: #111827;
}
.unit {
  font-size: 12px;
  color: #6b7280;
}
.tile-sub {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 6px 10px;
  margin-top: 10px;
  font-size: 12px;
  color: #111827;
}
.progress {
  height: 8px;
  border-radius: 6px;
  background: #f3f4f6;
  margin-top: 10px;
  overflow: hidden;
}
.bar {
  height: 100%;
  background: var(--el-color-primary);
}
.progress-label {
  margin-top: 6px;
  font-size: 12px;
  color: #6b7280;
}
.dist-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}
.chart-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.chart-card {
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 12px 14px;
}
.total-line {
  margin-top: 8px;
}
.total-chip {
  display: inline-block;
  font-size: 12px;
  color: #111827;
  border: 1px solid #ebeef5;
  border-radius: 999px;
  padding: 4px 10px;
  background: linear-gradient(90deg, #eef2ff, #f0f9ff);
  position: relative;
  overflow: hidden;
  box-shadow: 0 1px 6px rgba(64, 158, 255, 0.12);
}
.total-chip::after {
  content: '';
  position: absolute;
  top: 0;
  left: -30%;
  width: 30%;
  height: 100%;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0), rgba(255, 255, 255, 0.6), rgba(255, 255, 255, 0));
  animation: shine 2400ms ease-in-out infinite;
}
.total-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(64, 158, 255, 0.18);
}
@keyframes shine {
  0% {
    left: -40%;
  }
  55% {
    left: 110%;
  }
  100% {
    left: 110%;
  }
}
.chart-title {
  font-size: 13px;
  font-weight: 800;
  color: #111827;
  margin-bottom: 6px;
}
.dist-card {
  border: 1px solid #ebeef5;
  border-radius: 12px;
  padding: 12px 14px;
}
.dist-title {
  font-size: 13px;
  font-weight: 800;
  color: #111827;
  margin-bottom: 10px;
}
.pct-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}
.pct-bar {
  width: 140px;
  height: 8px;
  border-radius: 6px;
  background: #f3f4f6;
  overflow: hidden;
}
.pct-inner {
  height: 100%;
  background: var(--el-color-primary);
}
.pct-text {
  font-size: 12px;
  color: #6b7280;
}
.trend-filter {
  margin-bottom: 10px;
}
.trend-table {
  border: 1px solid #ebeef5;
  border-radius: 12px;
  overflow: hidden;
}
.trend-scroll {
  width: 100%;
  overflow-x: auto;
}
.trend-scroll table {
  width: max-content;
  border-collapse: collapse;
}
.trend-scroll th,
.trend-scroll td {
  padding: 8px 12px;
  border-bottom: 1px solid #ebeef5;
  font-size: 12px;
  white-space: nowrap;
}
.trend-scroll thead th {
  background: #f9fafb;
  color: #6b7280;
}
.metric {
  font-weight: 800;
  color: #111827;
}
@media (max-width: 960px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
  .dist-grid {
    grid-template-columns: 1fr;
  }
  .chart-grid {
    grid-template-columns: 1fr;
  }
}
</style>
