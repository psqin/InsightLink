<template>
  <div class="page">
    <div class="card">
      <div class="title">工作台</div>
      <div class="hint">提示：展示我的概览数据与近N日评价趋势</div>

      <div class="section">
        <div class="section-title">概览数据</div>
        <el-skeleton :loading="overviewLoading" animated>
          <template #template>
            <div class="overview-grid">
              <el-skeleton-item v-for="i in 6" :key="i" variant="rect" style="height: 96px" />
            </div>
          </template>
          <template #default>
            <div v-if="!overview" class="empty">暂无数据</div>
            <div v-else class="overview-grid">
              <div class="tile" @click="goMyStudents">
                <div class="tile-title">我的学生</div>
                <div class="tile-main">
                  <div class="num">{{ n(overview.myStudents) }}</div>
                  <div class="unit">人</div>
                </div>
              </div>
              <div class="tile" @click="goMessages">
                <div class="tile-title">今日学生消息</div>
                <div class="tile-main">
                  <div class="num">{{ n(overview.todayStudentMessages) }}</div>
                  <div class="unit">条</div>
                </div>
              </div>
              <div class="tile" @click="goNotices">
                <div class="tile-title">我的通知</div>
                <div class="tile-main">
                  <div class="num">{{ n(overview.myNotices) }}</div>
                  <div class="unit">条</div>
                </div>
              </div>
              <div class="tile" @click="goEvaluation(0)">
                <div class="tile-title">未评价</div>
                <div class="tile-main">
                  <div class="num">{{ n(overview.unevaluated) }}</div>
                  <div class="unit">次</div>
                </div>
              </div>
              <div class="tile" @click="goEvaluation(1)">
                <div class="tile-title">已评价</div>
                <div class="tile-main">
                  <div class="num">{{ n(overview.evaluated) }}</div>
                  <div class="unit">次</div>
                </div>
              </div>
              <div class="tile" @click="goEvaluation()">
                <div class="tile-title">平均得分</div>
                <div class="tile-main">
                  <div class="num">{{ n(overview.avgScore) }}</div>
                  <div class="unit">分</div>
                </div>
              </div>
            </div>
          </template>
        </el-skeleton>
      </div>

      <div class="section">
        <div class="section-title">评价次数趋势（折线图）</div>
        <div class="trend-filter">
          <el-select v-model="days" style="width: 120px">
            <el-option :value="7" label="近7日" />
            <el-option :value="14" label="近14日" />
            <el-option :value="30" label="近30日" />
          </el-select>
        </div>
        <el-skeleton :loading="trendLoading" animated>
          <template #template>
            <el-skeleton-item variant="rect" style="height: 360px" />
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
import { computed, onMounted, ref, watch } from 'vue'
import http from '../api/http'
import { useRouter } from 'vue-router'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { LineChart } from 'echarts/charts'
import { TooltipComponent, LegendComponent, GridComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, LineChart, TooltipComponent, LegendComponent, GridComponent])

const router = useRouter()

const overview = ref(null)
const trend = ref({ labels: [], series: {} })
const days = ref(7)

const overviewLoading = ref(false)
const trendLoading = ref(false)

function n(v) {
  const num = Number(v)
  return Number.isFinite(num) ? num : 0
}

const trendLineOption = computed(() => {
  const labels = trend.value?.labels || []
  const series = trend.value?.series || {}
  const evalCount = Array.isArray(series.evalCount) ? series.evalCount.map((v) => Number(v) || 0) : []
  return {
    tooltip: { trigger: 'axis' },
    legend: { top: 0, icon: 'circle' },
    grid: { left: '3%', right: '4%', bottom: '10%', containLabel: true },
    xAxis: { type: 'category', boundaryGap: false, data: labels },
    yAxis: { type: 'value' },
    series: [{ type: 'line', smooth: true, symbolSize: 6, name: '评价次数', data: evalCount }]
  }
})

async function fetchOverview() {
  overviewLoading.value = true
  try {
    const { data } = await http.get('/teacher/report/overview')
    overview.value = data?.data || null
  } finally {
    overviewLoading.value = false
  }
}

async function fetchTrend() {
  trendLoading.value = true
  try {
    const { data } = await http.get('/teacher/report/trend', { params: { days: days.value } })
    trend.value = data?.data || { labels: [], series: {} }
  } finally {
    trendLoading.value = false
  }
}

onMounted(() => {
  fetchOverview()
  fetchTrend()
})

watch(days, () => {
  fetchTrend()
})

function goMyStudents() {
  router.push('/teacher/my-students')
}

function goNotices() {
  router.push('/teacher/notice/mine')
}

function goEvaluation(evaluated) {
  const v = evaluated === 0 || evaluated === 1 ? evaluated : undefined
  router.push({ path: '/teacher/evaluation', query: v === undefined ? {} : { evaluated: String(v) } })
}

function goMessages() {
  router.push('/teacher/messages')
}
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
  --accent-rgb: 59, 130, 246;
  cursor: pointer;
  border: 1px solid rgba(var(--accent-rgb), 0.10);
  border-radius: 12px;
  padding: 12px 14px;
  background: linear-gradient(180deg, #ffffff, #fbfcff);
  position: relative;
  overflow: hidden;
  box-shadow: 0 1px 6px rgba(17, 24, 39, 0.05);
  transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
  animation: tile-in 420ms cubic-bezier(0.2, 0.9, 0.2, 1) both;
}
.tile:nth-child(2) {
  --accent-rgb: 168, 85, 247;
  background: linear-gradient(180deg, #ffffff, #fdfcff);
}
.tile:nth-child(3) {
  --accent-rgb: 34, 197, 94;
  background: linear-gradient(180deg, #ffffff, #fbfffd);
}
.tile:nth-child(4) {
  --accent-rgb: 249, 115, 22;
  background: linear-gradient(180deg, #ffffff, #fffaf6);
}
.tile:nth-child(5) {
  --accent-rgb: 14, 165, 233;
  background: linear-gradient(180deg, #ffffff, #f6fcff);
}
.tile:nth-child(6) {
  --accent-rgb: 244, 63, 94;
  background: linear-gradient(180deg, #ffffff, #fff7f9);
}
.tile:nth-child(1) {
  animation-delay: 0ms;
}
.tile:nth-child(2) {
  animation-delay: 60ms;
}
.tile:nth-child(3) {
  animation-delay: 120ms;
}
.tile:nth-child(4) {
  animation-delay: 180ms;
}
.tile:nth-child(5) {
  animation-delay: 240ms;
}
.tile:nth-child(6) {
  animation-delay: 300ms;
}
.tile::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(140px 80px at 12% 16%, rgba(var(--accent-rgb), 0.08), rgba(var(--accent-rgb), 0) 70%),
    radial-gradient(120px 90px at 88% 74%, rgba(var(--accent-rgb), 0.05), rgba(var(--accent-rgb), 0) 72%);
  pointer-events: none;
}
.tile::after {
  content: '';
  position: absolute;
  top: -10%;
  left: -55%;
  width: 45%;
  height: 120%;
  background: linear-gradient(
    90deg,
    rgba(255, 255, 255, 0),
    rgba(255, 255, 255, 0.45),
    rgba(255, 255, 255, 0)
  );
  transform: skewX(-18deg);
  opacity: 0;
  pointer-events: none;
}
.tile:hover {
  transform: translateY(-1px);
  border-color: rgba(var(--accent-rgb), 0.18);
  box-shadow: 0 8px 18px rgba(17, 24, 39, 0.10), 0 2px 8px rgba(var(--accent-rgb), 0.05);
}
.tile:hover::after {
  opacity: 0.65;
  animation: tile-shine 900ms ease-in-out;
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
  color: rgba(var(--accent-rgb), 0.85);
  text-shadow: 0 6px 14px rgba(var(--accent-rgb), 0.08);
}
.unit {
  font-size: 12px;
  color: #6b7280;
}
.trend-filter {
  margin-bottom: 10px;
}
@media (max-width: 960px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
}

@keyframes tile-in {
  0% {
    opacity: 0;
    transform: translateY(6px);
  }
  100% {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes tile-shine {
  0% {
    left: -55%;
  }
  60% {
    left: 115%;
  }
  100% {
    left: 115%;
  }
}

@media (prefers-reduced-motion: reduce) {
  .tile {
    animation: none;
    transition: none;
  }
  .tile:hover::after {
    animation: none;
  }
}
</style>
