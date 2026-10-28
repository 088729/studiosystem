<template>
  <!-- 专注统计（对齐主流待办应用第三期：趋势/最佳时间/热力图/时间线/占比排行/记录管理） -->
  <div class="focus-stats">
    <div class="fs-head">
      <span class="fs-title">专注统计</span>
      <span class="fs-close" @click="emit('close')">关闭</span>
    </div>

    <div class="fs-body">
      <!-- 总览双卡 -->
      <div class="fs-cards">
        <div class="fs-card">
          <div class="fs-card-label">总番茄</div>
          <div class="fs-card-value blue">{{ store.stats.total_completed }}</div>
        </div>
        <div class="fs-card">
          <div class="fs-card-label">总专注时长</div>
          <div class="fs-card-value blue">{{ minutesText(store.stats.total_minutes) }}</div>
        </div>
      </div>

      <!-- 专注趋势 -->
      <div class="fs-sec">
        <div class="fs-sec-head">
          <span class="fs-sec-title">专注趋势</span>
          <div class="fs-sec-tools">
            <el-radio-group v-model="trendPeriod" size="small" @change="onTrendPeriodChange">
              <el-radio-button value="week">周</el-radio-button>
              <el-radio-button value="month">月</el-radio-button>
            </el-radio-group>
            <span class="fs-nav">
              <span class="fs-nav-btn" @click="shiftTrend(-1)">‹</span>
              <span class="fs-nav-label">{{ trend.range_label }}</span>
              <span class="fs-nav-btn" @click="shiftTrend(1)">›</span>
            </span>
          </div>
        </div>
        <div class="fs-sub">每日平均：{{ minutesText(trend.avg_minutes || 0) }}</div>
        <div class="fs-area-wrap">
          <svg class="fs-area" :viewBox="`0 0 ${CHART_W} ${CHART_H}`" preserveAspectRatio="none">
            <defs>
              <linearGradient id="fsAreaGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#4f6ef7" stop-opacity="0.35" />
                <stop offset="100%" stop-color="#4f6ef7" stop-opacity="0.02" />
              </linearGradient>
            </defs>
            <path v-if="areaPath" :d="areaPath" fill="url(#fsAreaGrad)" />
            <path v-if="linePath" :d="linePath" fill="none" stroke="#4f6ef7" stroke-width="2" />
            <circle
              v-for="(p, i) in trendPoints"
              :key="i"
              :cx="p.x"
              :cy="p.y"
              r="3"
              fill="#fff"
              stroke="#4f6ef7"
              stroke-width="2"
            />
          </svg>
        </div>
        <div class="fs-xlabels" v-if="trend.labels && trend.labels.length <= 12">
          <span v-for="(l, i) in trend.labels" :key="i">{{ l }}</span>
        </div>
        <div class="fs-xlabels dense" v-else>
          <span v-for="i in monthLabelIdx" :key="i">{{ trend.labels[i] }}</span>
        </div>
      </div>

      <!-- 最佳专注时间 -->
      <div class="fs-sec">
        <div class="fs-sec-head">
          <span class="fs-sec-title">最佳专注时间</span>
          <span class="fs-nav">
            <span class="fs-nav-btn" @click="shiftMonth(-1)">‹</span>
            <span class="fs-nav-label">{{ hours.month }}</span>
            <span class="fs-nav-btn" @click="shiftMonth(1)">›</span>
          </span>
        </div>
        <div class="fs-hours">
          <div class="fs-hours-axis">
            <span v-for="(t, i) in hourTicks" :key="i">{{ t }}</span>
          </div>
          <div class="fs-hours-bars">
            <div v-for="(v, i) in hours.hours || []" :key="i" class="fs-hour-col" :title="`${String(i).padStart(2, '0')}:00 · ${v}m`">
              <div class="fs-hour-track">
                <div class="fs-hour-bar" :style="{ height: hourHeight(v) }"></div>
              </div>
            </div>
          </div>
        </div>
        <div class="fs-hours-x">
          <span v-for="x in ['00:00', '03:00', '06:00', '09:00', '12:00', '15:00', '18:00', '21:00']" :key="x">{{ x }}</span>
        </div>
      </div>

      <!-- 年度热力图 -->
      <div class="fs-sec">
        <div class="fs-sec-head">
          <span class="fs-sec-title">年度热力图</span>
          <span class="fs-nav">
            <span class="fs-nav-btn" @click="shiftYear(-1)">‹</span>
            <span class="fs-nav-label">{{ heatmap.year }}</span>
            <span class="fs-nav-btn" @click="shiftYear(1)">›</span>
          </span>
        </div>
        <div class="fs-months">
          <span v-for="m in heatmapMonthCols" :key="m.label" :style="{ left: m.left + 'px' }">{{ m.label }}</span>
        </div>
        <div class="fs-heat-wrap">
          <div class="fs-heat" :style="{ gridTemplateRows: 'repeat(7, 1fr)', width: heatCols * 16 + 'px' }">
            <div
              v-for="cell in heatCells"
              :key="cell.key"
              class="fs-heat-cell"
              :style="{ gridColumn: cell.col + 1, gridRow: cell.row + 1, background: cell.color }"
              :title="cell.title"
            ></div>
          </div>
          <div class="fs-heat-legend">
            <div class="fs-heat-legend-row" v-for="l in heatLegend" :key="l.label">
              <span class="fs-heat-legend-chip" :style="{ background: l.color }"></span>
              <span>{{ l.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 专注时间线 -->
      <div class="fs-sec">
        <div class="fs-sec-head">
          <span class="fs-sec-title">专注时间线</span>
          <span class="fs-nav">
            <span class="fs-nav-btn" @click="shiftTimelineWeek(-1)">‹</span>
            <span class="fs-nav-label">{{ timeline.week_label }}</span>
            <span class="fs-nav-btn" @click="shiftTimelineWeek(1)">›</span>
          </span>
        </div>
        <div class="fs-tl">
          <div class="fs-tl-axis">
            <span v-for="r in 6" :key="r">{{ String((r - 1) * 4).padStart(2, '0') }}:00</span>
          </div>
          <div class="fs-tl-grid">
            <div v-for="r in 7" :key="'h' + r" class="fs-tl-line" :style="{ top: ((r - 1) * 100) / 6 + '%' }"></div>
            <div class="fs-tl-cells">
              <div v-for="(col, di) in timelineCells" :key="di" class="fs-tl-col">
                <div
                  v-for="(cell, ri) in col"
                  :key="ri"
                  class="fs-tl-cell"
                  :style="{ background: cell.color }"
                  :title="cell.title"
                ></div>
              </div>
            </div>
          </div>
        </div>
        <div class="fs-tl-days">
          <span v-for="d in '一二三四五六日'" :key="d">{{ d }}</span>
        </div>
      </div>

      <!-- 专注详情：占比 + 排行 -->
      <div class="fs-sec">
        <div class="fs-sec-head">
          <span class="fs-sec-title">专注详情</span>
          <div class="fs-sec-tools">
            <el-radio-group v-model="bdPeriod" size="small" @change="onBdChange">
              <el-radio-button value="day">天</el-radio-button>
              <el-radio-button value="week">周</el-radio-button>
              <el-radio-button value="month">月</el-radio-button>
            </el-radio-group>
            <span class="fs-nav">
              <span class="fs-nav-btn" @click="shiftBd(-1)">‹</span>
              <span class="fs-nav-label">{{ breakdown.range_label }}</span>
              <span class="fs-nav-btn" @click="shiftBd(1)">›</span>
            </span>
          </div>
        </div>
        <div class="fs-bd">
          <div class="fs-donut">
            <svg :viewBox="`0 0 120 120`" class="fs-donut-svg">
              <circle cx="60" cy="60" :r="DONUT_R" fill="none" stroke="#f1f2f7" :stroke-width="DONUT_W" />
              <circle
                v-for="(seg, i) in donutSegments"
                :key="i"
                cx="60"
                cy="60"
                :r="DONUT_R"
                fill="none"
                :stroke="seg.color"
                :stroke-width="DONUT_W"
                :stroke-dasharray="`${seg.len} ${donutC - seg.len}`"
                :stroke-dashoffset="-seg.offset"
                transform="rotate(-90 60 60)"
              />
            </svg>
            <div class="fs-donut-center">
              <div class="fs-donut-total">{{ minutesText(breakdown.total_minutes) }}</div>
              <div class="fs-donut-unit">总时长</div>
            </div>
            <div class="fs-donut-legend">
              <div v-for="(seg, i) in donutSegments" :key="i" class="fs-donut-legend-row">
                <span class="fs-donut-dot" :style="{ background: seg.color }"></span>
                <span class="fs-donut-name">{{ seg.name }}</span>
                <span class="fs-donut-val">{{ minutesText(seg.minutes) }}</span>
              </div>
            </div>
          </div>
          <div class="fs-rank">
            <div class="fs-rank-head">
              <span class="fs-rank-title">专注排行</span>
              <el-radio-group v-model="bdBy" size="small" @change="onBdChange">
                <el-radio-button value="task">按任务</el-radio-button>
                <el-radio-button value="list">按清单</el-radio-button>
              </el-radio-group>
            </div>
            <el-empty v-if="!breakdown.items?.length" description="暂无数据" :image-size="60" />
            <div v-else class="fs-rank-list">
              <div v-for="(item, i) in breakdown.items.slice(0, 8)" :key="item.key" class="fs-rank-row">
                <span class="fs-rank-name">{{ item.name }}</span>
                <span class="fs-rank-val">{{ minutesText(item.minutes) }} · {{ item.pct }}%</span>
                <div class="fs-rank-bar">
                  <div class="fs-rank-fill" :style="{ width: item.pct + '%', background: RANK_COLORS[i % RANK_COLORS.length] }"></div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 专注记录管理 -->
      <div class="fs-sec">
        <div class="fs-sec-head">
          <span class="fs-sec-title">专注记录</span>
          <div class="fs-sec-tools">
            <template v-if="selecting">
              <el-button size="small" text type="danger" :disabled="!selected.length" @click="onBatchDelete">
                批量删除{{ selected.length ? `(${selected.length})` : '' }}
              </el-button>
              <el-button size="small" text @click="selecting = false">取消</el-button>
            </template>
            <template v-else>
              <span class="fs-link" @click="selecting = true">多选</span>
              <span class="fs-link danger" @click="onClearAll">清空</span>
            </template>
            <span class="fs-link" title="补记专注记录" @click="onAddRecord">＋</span>
          </div>
        </div>
        <el-checkbox
          v-if="selecting"
          :model-value="allSelected"
          class="fs-select-all"
          @change="toggleSelectAll"
        >全选本页</el-checkbox>
        <el-empty v-if="!records.length" description="还没有专注记录" :image-size="60" />
        <div v-else class="fs-records">
          <div v-for="s in records" :key="s.id" class="fs-record" :class="{ selecting }" @click="selecting && toggleSelect(s.id)">
            <el-checkbox v-if="selecting" :model-value="selected.includes(s.id)" class="fs-record-check" @click.stop @change="toggleSelect(s.id)" />
            <span class="fs-record-dot" :class="s.status">🍅</span>
            <div class="fs-record-mid">
              <div class="fs-record-line1">
                <span class="fs-record-date">{{ dayjs(s.started_at).format('M月D日') }}</span>
                <span class="fs-record-range">{{ dayjs(s.started_at).format('HH:mm') }} - {{ dayjs(s.ended_at || s.started_at).format('HH:mm') }}</span>
                <span class="fs-record-min">{{ minutesText(Math.round(s.actual_seconds / 60)) }}</span>
              </div>
              <div class="fs-record-line2">{{ recordName(s) }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import { fetchFocusStatsDetail, deleteFocusRecords, fetchFocusSessions } from '@/api/task'
import { usePomodoroStore } from '@/stores/pomodoro'
import { useTaskStore } from '@/stores/task'

const emit = defineEmits(['close'])
const store = usePomodoroStore()
const taskStore = useTaskStore()
const tzOffsetMinutes = -new Date().getTimezoneOffset()

function minutesText(min) {
  min = Math.round(min || 0)
  if (min < 60) return `${min}m`
  return `${Math.floor(min / 60)}h${min % 60 ? `${min % 60}m` : ''}`
}

function mondayOf(d) {
  return d.subtract((d.day() + 6) % 7, 'day').startOf('day')
}

// ---------- 专注趋势 ----------
const CHART_W = 640
const CHART_H = 170
const trend = ref({ labels: [], minutes: [], avg_minutes: 0, range_label: '' })
const trendPeriod = ref('week')
const trendAnchor = ref(dayjs())

async function loadTrend() {
  trend.value = await fetchFocusStatsDetail({
    kind: 'trend',
    period: trendPeriod.value,
    date: trendAnchor.value.format('YYYY-MM-DD'),
    tz_offset_minutes: tzOffsetMinutes,
  }).catch(() => trend.value)
}
function onTrendPeriodChange() {
  trendAnchor.value = dayjs()
  loadTrend()
}
function shiftTrend(n) {
  trendAnchor.value =
    trendPeriod.value === 'week'
      ? trendAnchor.value.add(n * 7, 'day')
      : trendAnchor.value.add(n, 'month')
  loadTrend()
}

const trendMax = computed(() => Math.max(60, ...((trend.value.minutes) || [])))
const trendPoints = computed(() => {
  const mins = trend.value.minutes || []
  if (mins.length < 2) return []
  const step = CHART_W / (mins.length - 1)
  return mins.map((v, i) => ({
    x: i * step,
    y: CHART_H - 8 - (v / trendMax.value) * (CHART_H - 20),
  }))
})
function smoothPath(pts) {
  if (pts.length < 2) return ''
  let d = `M ${pts[0].x} ${pts[0].y}`
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)]
    const p1 = pts[i]
    const p2 = pts[i + 1]
    const p3 = pts[Math.min(pts.length - 1, i + 2)]
    const c1x = p1.x + (p2.x - p0.x) / 6
    const c1y = p1.y + (p2.y - p0.y) / 6
    const c2x = p2.x - (p3.x - p1.x) / 6
    const c2y = p2.y - (p3.y - p1.y) / 6
    d += ` C ${c1x.toFixed(1)} ${c1y.toFixed(1)}, ${c2x.toFixed(1)} ${c2y.toFixed(1)}, ${p2.x} ${p2.y}`
  }
  return d
}
const linePath = computed(() => smoothPath(trendPoints.value))
const areaPath = computed(() =>
  linePath.value ? `${linePath.value} L ${CHART_W} ${CHART_H} L 0 ${CHART_H} Z` : ''
)
const monthLabelIdx = computed(() => {
  const n = (trend.value.labels || []).length
  const idx = []
  for (let i = 0; i < n; i += Math.ceil(n / 10)) idx.push(i)
  return idx
})

// ---------- 最佳专注时间 ----------
const hours = ref({ hours: [], month: '' })
const monthAnchor = ref(dayjs())

async function loadHours() {
  hours.value = await fetchFocusStatsDetail({
    kind: 'hours',
    month: monthAnchor.value.format('YYYY-MM'),
    tz_offset_minutes: tzOffsetMinutes,
  }).catch(() => hours.value)
}
function shiftMonth(n) {
  monthAnchor.value = monthAnchor.value.add(n, 'month')
  loadHours()
}
const hourMax = computed(() => Math.max(60, ...((hours.value.hours) || [])))
const hourTicks = computed(() => {
  const mx = hourMax.value
  return [0, 1, 2, 3, 4].map((i) => minutesText(Math.round((mx * (4 - i)) / 4)))
})
function hourHeight(v) {
  return `${Math.max(2, Math.round((v / hourMax.value) * 100))}%`
}

// ---------- 年度热力图 ----------
const heatmap = ref({ year: dayjs().year(), days: {} })
const yearAnchor = ref(dayjs())

async function loadHeatmap() {
  heatmap.value = await fetchFocusStatsDetail({
    kind: 'heatmap',
    year: String(yearAnchor.value.year()),
    tz_offset_minutes: tzOffsetMinutes,
  }).catch(() => heatmap.value)
}
function shiftYear(n) {
  yearAnchor.value = yearAnchor.value.add(n, 'year')
  loadHeatmap()
}
function heatColor(minutes) {
  if (!minutes) return '#f1f2f7'
  if (minutes < 60) return '#d6e0fd'
  if (minutes < 180) return '#aabcfb'
  if (minutes < 300) return '#6f8af8'
  return '#4f6ef7'
}
const heatLegend = [
  { label: '0m', color: '#f1f2f7' },
  { label: '0-1h', color: '#d6e0fd' },
  { label: '1-3h', color: '#aabcfb' },
  { label: '3-5h', color: '#6f8af8' },
  { label: '>5h', color: '#4f6ef7' },
]
const heatCells = computed(() => {
  const year = heatmap.value.year
  const days = heatmap.value.days || {}
  const jan1 = dayjs(`${year}-01-01`)
  const offset = (jan1.day() + 6) % 7 // 1月1日是周几（周一=0）
  const total = (jan1.year() % 4 === 0 && (jan1.year() % 100 !== 0 || jan1.year() % 400 === 0)) ? 366 : 365
  const cells = []
  for (let doy = 1; doy <= total; doy++) {
    const d = jan1.add(doy - 1, 'day')
    const col = Math.floor((offset + doy - 1) / 7)
    const row = (d.day() + 6) % 7
    const key = d.format('YYYY-MM-DD')
    const minutes = days[key] || 0
    cells.push({
      key,
      col,
      row,
      color: heatColor(minutes),
      title: `${d.format('M月D日')} · ${minutesText(minutes)}`,
    })
  }
  return cells
})
const heatCols = computed(() => {
  if (!heatCells.value.length) return 1
  return Math.max(...heatCells.value.map((c) => c.col)) + 1
})
const heatmapMonthCols = computed(() => {
  const year = heatmap.value.year
  const jan1 = dayjs(`${year}-01-01`)
  const offset = (jan1.day() + 6) % 7
  return [1, 4, 7, 10].map((m) => {
    const first = dayjs(`${year}-${String(m).padStart(2, '0')}-01`)
    const col = Math.floor((offset + first.diff(jan1, 'day')) / 7)
    return { label: `${m}月`, left: col * 16 }
  })
})

// ---------- 专注时间线 ----------
const timeline = ref({ week_label: '本周', cells: [] })
const timelineAnchor = ref(mondayOf(dayjs()))

async function loadTimeline() {
  timeline.value = await fetchFocusStatsDetail({
    kind: 'timeline',
    week_start: timelineAnchor.value.format('YYYY-MM-DD'),
    tz_offset_minutes: tzOffsetMinutes,
  }).catch(() => timeline.value)
}
function shiftTimelineWeek(n) {
  timelineAnchor.value = timelineAnchor.value.add(n * 7, 'day')
  loadTimeline()
}
const timelineCells = computed(() => {
  const cells = timeline.value.cells || []
  return Array.from({ length: 7 }, (_, d) =>
    Array.from({ length: 6 }, (_, r) => {
      let minutes = 0
      for (let h = r * 4; h < r * 4 + 4; h++) minutes += cells[d]?.[h] || 0
      return {
        color: minutes ? heatColor(minutes) : 'transparent',
        title: `${'一二三四五六日'[d]} ${String(r * 4).padStart(2, '0')}:00-${String(r * 4 + 4).padStart(2, '0')}:00 · ${minutesText(minutes)}`,
      }
    })
  )
})

// ---------- 专注详情（占比/排行） ----------
const breakdown = ref({ items: [], total_minutes: 0, range_label: '' })
const bdPeriod = ref('week')
const bdBy = ref('task')
const bdAnchor = ref(dayjs())

async function loadBreakdown() {
  breakdown.value = await fetchFocusStatsDetail({
    kind: 'breakdown',
    by: bdBy.value,
    period: bdPeriod.value,
    date: bdAnchor.value.format('YYYY-MM-DD'),
    tz_offset_minutes: tzOffsetMinutes,
  }).catch(() => breakdown.value)
}
function onBdChange() {
  bdAnchor.value = dayjs()
  loadBreakdown()
}
function shiftBd(n) {
  if (bdPeriod.value === 'day') bdAnchor.value = bdAnchor.value.add(n, 'day')
  else if (bdPeriod.value === 'week') bdAnchor.value = bdAnchor.value.add(n * 7, 'day')
  else bdAnchor.value = bdAnchor.value.add(n, 'month')
  loadBreakdown()
}

const DONUT_R = 44
const DONUT_W = 16
const donutC = 2 * Math.PI * DONUT_R
const RANK_COLORS = ['#4f6ef7', '#f0abfc', '#4ade80', '#fbbf24', '#f87171', '#38bdf8', '#a78bfa', '#fb923c']
const donutSegments = computed(() => {
  const items = (breakdown.value.items || []).slice(0, 6)
  const rest = (breakdown.value.items || []).slice(6)
  const segs = items.map((x, i) => ({ name: x.name, minutes: x.minutes, color: RANK_COLORS[i % RANK_COLORS.length] }))
  if (rest.length) {
    segs.push({ name: '其他', minutes: rest.reduce((a, b) => a + b.minutes, 0), color: '#c9cede' })
  }
  const total = segs.reduce((a, b) => a + b.minutes, 0)
  let acc = 0
  return segs
    .filter((s) => s.minutes > 0 && total > 0)
    .map((s) => {
      const len = (s.minutes / total) * donutC
      const seg = { ...s, len, offset: acc }
      acc += len
      return seg
    })
})

// ---------- 专注记录管理 ----------
const records = ref([])
const selecting = ref(false)
const selected = ref([])

async function loadRecords() {
  const res = await fetchFocusSessions({}).catch(() => ({ items: [] }))
  records.value = (res.items || []).filter((s) => s.status !== 'running').slice(0, 50)
}
const allSelected = computed(
  () => records.value.length > 0 && selected.value.length === records.value.length
)
function toggleSelectAll() {
  selected.value = allSelected.value ? [] : records.value.map((s) => s.id)
}
function toggleSelect(id) {
  selected.value = selected.value.includes(id)
    ? selected.value.filter((x) => x !== id)
    : [...selected.value, id]
}
function recordName(s) {
  if (s.task_id) {
    const t = taskStore.tasks.find((x) => x.id === s.task_id)
    if (t) return t.title
  }
  if (s.preset_id) {
    const all = [...store.presets, ...store.presetsArchived]
    const p = all.find((x) => x.id === s.preset_id)
    if (p) return p.name
  }
  if (s.note) return '专注笔记'
  return '纯计时'
}
async function onBatchDelete() {
  try {
    await ElMessageBox.confirm(`删除选中的 ${selected.value.length} 条专注记录？`, '批量删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch { return }
  await deleteFocusRecords({ ids: selected.value }).catch(() => null)
  ElMessage.success('已删除')
  selected.value = []
  selecting.value = false
  await Promise.all([loadRecords(), store.fetchStats()])
}
async function onClearAll() {
  try {
    await ElMessageBox.confirm('清空全部专注记录？该操作不可恢复。', '清空', {
      type: 'warning',
      confirmButtonText: '清空',
      cancelButtonText: '取消',
    })
  } catch { return }
  await deleteFocusRecords({ all: true }).catch(() => null)
  ElMessage.success('已清空')
  selected.value = []
  selecting.value = false
  await Promise.all([loadRecords(), store.fetchStats()])
}
async function onAddRecord() {
  try {
    const { value } = await ElMessageBox.prompt('补记专注时长（分钟）', '添加专注记录', {
      inputPattern: /^\d+$/,
      inputErrorMessage: '请输入分钟数',
    })
    const minutes = +value
    await store.addRecord({
      planned_minutes: minutes,
      actual_seconds: minutes * 60,
      started_at: dayjs().subtract(minutes, 'minute').toISOString(),
    })
    ElMessage.success('已补记')
  } catch { /* 取消 */ }
}

onMounted(() => {
  store.fetchStats()
  loadTrend()
  loadHours()
  loadHeatmap()
  loadTimeline()
  loadBreakdown()
  loadRecords()
})
</script>

<style scoped>
.focus-stats {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.fs-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-bottom: 10px;
}
.fs-title {
  font-size: clamp(16px, 1.67cqw, 22px);
  font-weight: 600;
  color: var(--ss-text, #303133);
}
.fs-close {
  font-size: clamp(12px, 1.1cqw, 13px);
  color: var(--el-color-primary);
  cursor: pointer;
}
.fs-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: clamp(12px, 1.3cqw, 20px);
  padding-right: 4px;
  padding-bottom: 16px;
}
/* 总览双卡 */
.fs-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: clamp(8px, 0.93cqw, 14px);
}
.fs-card {
  background: var(--ss-fill, #f7f7f9);
  border-radius: 12px;
  padding: clamp(12px, 1.3cqw, 18px) clamp(14px, 1.5cqw, 20px);
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.fs-card-label {
  font-size: clamp(12px, 1.11cqw, 14px);
  color: var(--ss-text-secondary, #909399);
}
.fs-card-value {
  font-size: clamp(22px, 2.4cqw, 34px);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.fs-card-value.blue {
  color: var(--el-color-primary);
}
/* 通用区块 */
.fs-sec {
  background: #fff;
  border: 1px solid var(--ss-border-light, #f0f0f0);
  border-radius: 12px;
  padding: clamp(12px, 1.3cqw, 20px);
}
.fs-sec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 8px;
}
.fs-sec-title {
  font-size: clamp(14px, 1.4cqw, 17px);
  font-weight: 600;
  color: var(--ss-text, #303133);
}
.fs-sec-tools {
  display: flex;
  align-items: center;
  gap: 12px;
}
.fs-nav {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  color: var(--ss-text-secondary, #909399);
  font-size: clamp(12px, 1.1cqw, 14px);
}
.fs-nav-btn {
  cursor: pointer;
  font-size: 16px;
  padding: 0 4px;
  user-select: none;
}
.fs-nav-btn:hover {
  color: var(--el-color-primary);
}
.fs-sub {
  margin-top: 6px;
  font-size: clamp(11px, 1.02cqw, 13px);
  color: var(--ss-text-secondary, #909399);
}
/* 趋势面积图 */
.fs-area-wrap {
  margin-top: 10px;
}
.fs-area {
  width: 100%;
  height: clamp(120px, 14cqw, 180px);
  display: block;
}
.fs-xlabels {
  display: flex;
  justify-content: space-between;
  margin-top: 4px;
  font-size: clamp(10px, 0.93cqw, 12px);
  color: var(--ss-text-secondary, #909399);
}
.fs-xlabels.dense span {
  flex: none;
}
/* 最佳专注时间 */
.fs-hours {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}
.fs-hours-axis {
  width: 52px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  font-size: clamp(10px, 0.93cqw, 12px);
  color: var(--ss-text-secondary, #909399);
  padding-bottom: 18px;
}
.fs-hours-bars {
  flex: 1;
  min-width: 0;
  display: flex;
  gap: 3px;
  height: clamp(130px, 15cqw, 200px);
}
.fs-hour-col {
  flex: 1;
  display: flex;
  align-items: flex-end;
  min-width: 0;
}
.fs-hour-track {
  width: 100%;
  height: 100%;
  background: #f4f5f9;
  border-radius: 3px 3px 0 0;
  display: flex;
  align-items: flex-end;
}
.fs-hour-bar {
  width: 100%;
  background: #4f6ef7;
  border-radius: 3px 3px 0 0;
}
.fs-hours-x {
  display: flex;
  justify-content: space-between;
  margin-top: 6px;
  padding-left: 60px;
  font-size: clamp(10px, 0.93cqw, 12px);
  color: var(--ss-text-secondary, #909399);
}
/* 年度热力图 */
.fs-months {
  position: relative;
  height: 18px;
  margin: 8px 0 4px 30px;
  font-size: clamp(10px, 0.93cqw, 12px);
  color: var(--ss-text-secondary, #909399);
}
.fs-months span {
  position: absolute;
  top: 0;
}
.fs-heat-wrap {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}
.fs-heat {
  display: grid;
  grid-auto-flow: column;
  grid-template-rows: repeat(7, 1fr);
  gap: 3px;
  margin-left: 30px;
}
.fs-heat-cell {
  width: 13px;
  height: 13px;
  border-radius: 3px;
}
.fs-heat-legend {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-left: auto;
  font-size: clamp(10px, 0.93cqw, 12px);
  color: var(--ss-text-secondary, #909399);
}
.fs-heat-legend-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.fs-heat-legend-chip {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}
/* 专注时间线 */
.fs-tl {
  display: flex;
  gap: 10px;
  margin-top: 10px;
}
.fs-tl-axis {
  width: 52px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  font-size: clamp(10px, 0.93cqw, 12px);
  color: var(--ss-text-secondary, #909399);
  padding: 2px 0;
}
.fs-tl-grid {
  position: relative;
  flex: 1;
  min-width: 0;
  height: clamp(140px, 16cqw, 220px);
}
.fs-tl-line {
  position: absolute;
  left: 0;
  right: 0;
  border-top: 1px dashed var(--ss-border-light, #f0f0f0);
}
.fs-tl-cells {
  position: absolute;
  inset: 0;
  display: flex;
  gap: 4px;
}
.fs-tl-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.fs-tl-cell {
  flex: 1;
  border-radius: 3px;
}
.fs-tl-days {
  display: flex;
  margin: 6px 0 0 62px;
}
.fs-tl-days span {
  flex: 1;
  text-align: center;
  font-size: clamp(10px, 0.93cqw, 12px);
  color: var(--ss-text-secondary, #909399);
}
/* 专注详情 */
.fs-bd {
  display: flex;
  gap: clamp(16px, 2.2cqw, 40px);
  margin-top: 12px;
  flex-wrap: wrap;
}
.fs-donut {
  position: relative;
  width: clamp(150px, 15cqw, 190px);
  flex-shrink: 0;
}
.fs-donut-svg {
  width: 100%;
  display: block;
}
.fs-donut-center {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  text-align: center;
}
.fs-donut-total {
  font-size: clamp(16px, 1.7cqw, 22px);
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--ss-text, #303133);
}
.fs-donut-unit {
  font-size: clamp(10px, 0.93cqw, 12px);
  color: var(--ss-text-secondary, #909399);
}
.fs-donut-legend {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.fs-donut-legend-row {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: clamp(11px, 1.02cqw, 13px);
  color: var(--ss-text, #303133);
}
.fs-donut-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.fs-donut-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.fs-donut-val {
  color: var(--ss-text-secondary, #909399);
  font-variant-numeric: tabular-nums;
}
.fs-rank {
  flex: 1;
  min-width: 240px;
}
.fs-rank-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}
.fs-rank-title {
  font-size: clamp(13px, 1.2cqw, 15px);
  font-weight: 600;
  color: var(--ss-text, #303133);
}
.fs-rank-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.fs-rank-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.fs-rank-name {
  font-size: clamp(12px, 1.1cqw, 14px);
  color: var(--ss-text, #303133);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.fs-rank-val {
  font-size: clamp(11px, 1.02cqw, 13px);
  color: var(--ss-text-secondary, #909399);
  font-variant-numeric: tabular-nums;
  margin-left: 8px;
  float: right;
}
.fs-rank-name {
  flex: 1;
}
.fs-rank-row {
  position: relative;
}
.fs-rank-row .fs-rank-name {
  display: inline-block;
  max-width: calc(100% - 90px);
}
.fs-rank-bar {
  height: 6px;
  background: var(--ss-fill, #f7f7f9);
  border-radius: 999px;
  overflow: hidden;
}
.fs-rank-fill {
  height: 100%;
  border-radius: 999px;
}
/* 专注记录 */
.fs-link {
  font-size: clamp(12px, 1.1cqw, 13px);
  color: var(--el-color-primary);
  cursor: pointer;
}
.fs-link.danger {
  color: var(--el-color-danger);
}
.fs-select-all {
  margin-top: 8px;
}
.fs-records {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
}
.fs-record {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px 4px;
  border-bottom: 1px solid var(--ss-border-light, #f0f0f0);
  cursor: default;
}
.fs-record.selecting {
  cursor: pointer;
}
.fs-record-check {
  margin-top: 2px;
}
.fs-record-dot {
  font-size: 14px;
  margin-top: 1px;
  opacity: 0.9;
}
.fs-record-dot.abandoned {
  filter: grayscale(1);
  opacity: 0.5;
}
.fs-record-mid {
  flex: 1;
  min-width: 0;
}
.fs-record-line1 {
  display: flex;
  align-items: center;
  gap: 8px;
}
.fs-record-date {
  font-size: clamp(12px, 1.1cqw, 14px);
  font-weight: 600;
  color: var(--ss-text, #303133);
}
.fs-record-range {
  font-size: clamp(11px, 1.02cqw, 13px);
  color: var(--ss-text-secondary, #909399);
  font-variant-numeric: tabular-nums;
  flex: 1;
}
.fs-record-min {
  font-size: clamp(11px, 1.02cqw, 13px);
  color: var(--ss-text-secondary, #909399);
  font-variant-numeric: tabular-nums;
}
.fs-record-line2 {
  margin-top: 2px;
  font-size: clamp(11px, 1.02cqw, 13px);
  color: var(--ss-text-secondary, #909399);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
</style>
