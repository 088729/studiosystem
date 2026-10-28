<template>
  <!-- 时间线视图（对齐主流待办应用「时间线」）：月/日双表头 + 任务条直接排在共享日期轴上；
       清单按 board_groups 分泳道、收集箱按 inbox_board_groups（可折叠，空分组也渲染便于点击添加）；
       无分组的视图（智能清单等）为平面泳道；两端 ‹ › 翻页 / 今天 / 日周月粒度 -->
  <div class="tl-wrap">
    <div class="tl-main">
      <div v-if="!scheduled.length && !unscheduled.length && !grouped" class="tl-empty">
        <el-empty description="暂无任务" />
      </div>
      <div v-else class="tl-scroll" ref="scrollRef" @click="onBlankClick">
        <div class="tl-inner" :style="{ width: (grouped ? LEFT_W : 0) + days.length * PPD + 'px', '--ppd': PPD + 'px' }">
          <!-- 月表头（吸顶）：月分段 + 吸右控制条（‹ › 今天 粒度） -->
          <div class="tl-month-row">
            <div v-if="grouped" class="tl-corner tl-sticky" />
            <div
              v-for="(seg, i) in topSegs"
              :key="i"
              class="tl-month"
              :style="{ width: seg.span * PPD + 'px' }"
            ><span class="tl-month-label" :style="{ left: (grouped ? LEFT_W + 8 : 8) + 'px' }">{{ seg.label }}</span></div>
            <div class="tl-controls" @click.stop>
              <span class="tl-ctl-btn" :class="{ on: uspOpen }" @click="uspOpen = !uspOpen">
                安排任务<template v-if="unscheduled.length">&nbsp;{{ unscheduled.length }}</template>
              </span>
              <span class="tl-ctl-btn" @click="backToday">今天</span>
              <el-dropdown trigger="click" @command="(m) => (granularity = m)">
                <span class="tl-ctl-btn">{{ granLabel }}<ChevronDown :size="11" style="margin-left: 2px" /></span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="day">日</el-dropdown-item>
                    <el-dropdown-item command="week">周</el-dropdown-item>
                    <el-dropdown-item command="month">月</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              <!-- 显示设置（对齐官方 ⋯-显示设置：任务块颜色） -->
              <el-dropdown trigger="click" @command="onCtlCmd">
                <span class="tl-ctl-btn"><MoreVertical :size="12" /></span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="display">显示设置</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>
          <!-- 日表头（吸顶）：日=日期+星期 / 周=日期 / 月=月份；两端 ‹ › 平移窗口（对齐主流待办应用） -->
          <div class="tl-day-row">
            <div v-if="grouped" class="tl-corner tl-sticky" />
            <div class="tl-nav tl-nav-l" :style="{ left: (grouped ? LEFT_W : 0) + 'px' }" title="向前" @click.stop="shift(-1)">
              <ChevronLeft :size="14" />
            </div>
            <div
              v-for="c in headerCells"
              :key="c.key"
              class="tl-day"
              :class="{ today: c.isToday, weekend: c.isWeekend }"
              :style="{ width: c.span * PPD + 'px' }"
            >
              <span class="tl-day-num">{{ c.label }}</span>
              <span v-if="c.week" class="tl-day-week">{{ c.week }}</span>
            </div>
            <div class="tl-nav tl-nav-r" title="向后" @click.stop="shift(1)">
              <ChevronRight :size="14" />
            </div>
          </div>

          <!-- 背景层：周末/今天列底色（月粒度下只画今天） -->
          <div class="tl-bg" :style="{ left: (grouped ? LEFT_W : 0) + 'px', width: days.length * PPD + 'px' }">
            <div
              v-for="(d, i) in days"
              :key="d.key"
              class="tl-bg-cell"
              :class="{ weekend: granularity !== 'month' && d.isWeekend, today: d.isToday }"
              :style="{ left: i * PPD + 'px', width: PPD + 'px' }"
            />
          </div>

          <!-- 分组泳道（或平面泳道） -->
          <div
            v-for="sec in sections"
            :key="sec.key"
            class="tl-section"
            :style="{ height: secHeight(sec) + 'px' }"
          >
            <div v-if="grouped" class="tl-sec-label tl-sticky" @click="toggleSec(sec)">
              <ChevronRight :size="13" class="fold-arrow" :class="{ expanded: !collapsedSecs[sec.key] }" />
              <span class="tl-sec-name">{{ sec.label }}</span>
              <span class="tl-sec-count">{{ sec.tasks.length }}</span>
            </div>
            <div class="tl-track" :data-gkey="sec.manageable ? sec.key : ''" :style="{ width: days.length * PPD + 'px' }">
              <template v-if="!collapsedSecs[sec.key]">
                <div
                  v-for="b in sec.bars"
                  :key="b.t.id"
                  class="tl-bar"
                  :class="{ done: b.t.status === 'done' }"
                  :style="{ left: b.left + 'px', width: b.width + 'px', top: b.top + 'px', ...barStyle(b.t) }"
                  :title="b.t.title"
                  @pointerdown="onBarDown($event, b.t)"
                >
                  <span class="tl-rz tl-rz-l" title="调整开始" @pointerdown.stop="onResizeDown($event, b.t, 'l', $event.currentTarget.parentElement)" />
                  <span v-if="b.t.priority" class="tl-prio" :style="{ background: prioColor(b.t.priority) }" />{{ b.t.title }}
                  <span class="tl-rz tl-rz-r" title="调整时长" @pointerdown.stop="onResizeDown($event, b.t, 'r', $event.currentTarget.parentElement)" />
                </div>
              </template>
            </div>
          </div>

          <!-- 今天竖线 -->
          <div class="tl-today-line" :style="{ left: (grouped ? LEFT_W : 0) + todayIdx * PPD + 'px' }" />
          <!-- 安排任务拖入时的落点占位条 -->
          <div
            v-if="dropGhost"
            class="tl-drop-ghost"
            :style="{ left: dropGhost.left + 'px', top: dropGhost.top + 'px', width: dropGhost.width + 'px', background: dropGhost.bg, color: dropGhost.color }"
          >{{ dropGhost.title }}</div>
          <!-- 点击空白快速添加（对齐主流待办应用时间线）：点击列出蓝色占位条 + 迷你添加卡片（日期行/多行标题/清单选择） -->
          <template v-if="addState">
            <div class="tl-add-ghost" :style="{ left: addState.left + 'px', top: addState.top + 'px', width: PPD - 3 + 'px' }" />
            <div class="tl-add" :style="{ left: addState.cardLeft + 'px', top: addState.top + 28 + 'px' }" @click.stop @pointerdown.stop>
              <div class="tl-add-card">
                <div class="tl-add-date-row">
                  <TaskDatePicker
                    :due-at="addState.due"
                    :all-day="addState.allDay"
                    :start-at="addState.startAt"
                    @change="onAddDate"
                  >
                    <template #trigger="{ label }">
                      <span class="tl-add-date" :class="{ overdue: addOverdueDays > 0 }">
                        <Calendar :size="14" />
                        {{ label || addState.day.format('M月D日') }}<template v-if="addOverdueDays > 0">, 延期{{ addOverdueDays }}天</template>
                      </span>
                    </template>
                  </TaskDatePicker>
                  <el-dropdown trigger="click" @command="(p) => (addPriority = p)">
                    <span class="tl-add-flag" :title="'优先级：' + prioLabel(addPriority)">
                      <Flag :size="15" :color="prioColor(addPriority) || '#666'" :fill="addPriority ? prioColor(addPriority) : 'none'" />
                    </span>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item v-for="o in prioOptions" :key="o.value" :command="o.value">
                          <Flag :size="12" :color="o.color" :fill="o.value ? o.color : 'none'" style="margin-right: 6px; vertical-align: -1px" />{{ o.label }}
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
                <input
                  ref="addInputRef"
                  v-model="addTitle"
                  class="tl-add-title"
                  placeholder="准备做什么？"
                  @keydown.enter.prevent="addDescRef?.focus()"
                  @keydown.ctrl.enter.prevent="submitAdd"
                  @keydown.esc.stop="cancelAdd"
                />
                <textarea
                  ref="addDescRef"
                  v-model="addDesc"
                  class="tl-add-desc"
                  placeholder="添加详情"
                  @keydown.ctrl.enter.prevent="submitAdd"
                  @keydown.esc.stop="cancelAdd"
                />
                <div class="tl-add-footer">
                  <el-dropdown trigger="click" @command="(v) => (addListId = v)">
                    <span class="tl-add-list-trigger">
                      <Inbox v-if="addListId === '__inbox'" :size="14" />
                      <span v-else class="tl-add-list-dot" :style="{ background: addListColor }" />
                      {{ addListName }}
                    </span>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="__inbox">收集箱</el-dropdown-item>
                        <el-dropdown-item v-for="l in store.lists" :key="l.id" :command="l.id">{{ l.name }}</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </div>
            </div>
          </template>
          <!-- 点击任务条：迷你任务卡片（对齐主流待办应用） -->
          <TimelineTaskCard
            v-if="viewState"
            :task-id="viewState.id"
            :left="viewState.left"
            :top="viewState.top"
            @close="viewState = null"
          />
        </div>
      </div>
    </div>
    <!-- 右侧安排任务面板（对齐官方：无日期任务列出，拖入时间线排期） -->
    <aside v-if="uspOpen" class="tl-usp" @click.stop @pointerdown.stop>
      <div class="tl-usp-head">
        <span class="tl-usp-title">安排任务</span>
        <span class="tl-usp-count">{{ unscheduled.length }}</span>
        <span class="tl-usp-close" title="收起" @click="uspOpen = false"><X :size="13" /></span>
      </div>
      <div class="tl-usp-list">
        <div v-if="!unscheduled.length" class="tl-usp-empty">暂无未安排任务</div>
        <div
          v-for="t in unscheduled"
          :key="t.id"
          class="tl-usp-item"
          :class="{ dragging: uspDrag?.t.id === t.id && uspDrag.dragging }"
          :style="barStyle(t)"
          :title="t.title + '（拖入时间线安排）'"
          @pointerdown="onUspDown($event, t)"
        >
          <span v-if="t.priority" class="tl-prio" :style="{ background: prioColor(t.priority) }" />
          <span class="tl-usp-item-title">{{ t.title }}</span>
        </div>
      </div>
    </aside>
    <!-- 拖出的悬浮幽灵条（跟随光标） -->
    <div v-if="uspGhost" class="tl-usp-ghost" :style="{ left: uspGhost.x + 'px', top: uspGhost.y + 'px', ...barStyle(uspGhost.t) }">
      <span class="tl-usp-item-title">{{ uspGhost.t.title }}</span>
    </div>
    <!-- 显示设置（任务块颜色方案） -->
    <el-dialog v-model="dispOpen" title="显示设置" width="300px" append-to-body class="tl-disp-dialog">
      <div class="tl-disp">
        <div class="tl-disp-label">任务块颜色</div>
        <el-radio-group v-model="colorMode" class="tl-disp-radios">
          <el-radio value="list">清单颜色</el-radio>
          <el-radio value="priority">优先级颜色</el-radio>
        </el-radio-group>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import dayjs from 'dayjs'
import { ChevronLeft, ChevronRight, ChevronDown, Calendar, Flag, Inbox, MoreVertical, X } from 'lucide-vue-next'
import { useTaskStore } from '@/stores/task'
import { useAuthStore } from '@/stores/auth'
import TaskDatePicker from '../TaskDatePicker.vue'
import TimelineTaskCard from './TimelineTaskCard.vue'

const store = useTaskStore()
const authStore = useAuthStore()
const LEFT_W = 120 // 分组泳道左列宽
const LANE_H = 30 // 泳道单条层高
const MONTH_H = 26
const DAY_H = 34
const WEEK = ['日', '一', '二', '三', '四', '五', '六']
const GRANS = { day: { ppd: 96, label: '日' }, week: { ppd: 28, label: '周' }, month: { ppd: 8, label: '月' } }

// ---------- 粒度（日/周/月 = 每天像素宽），本地记忆 ----------
const granularity = ref(localStorage.getItem('task-timeline-gran') || 'day')
watch(granularity, (v) => localStorage.setItem('task-timeline-gran', v))
const PPD = computed(() => GRANS[granularity.value].ppd)
const granLabel = computed(() => GRANS[granularity.value].label)

const tasks = computed(() => {
  const all = [...store.todoTasks, ...store.doneTasks]
  return store.hideDone ? all.filter((t) => t.status !== 'done') : all
})
const scheduled = computed(() => tasks.value.filter((t) => t.due_at || t.start_at))
const unscheduled = computed(() => tasks.value.filter((t) => !t.due_at && !t.start_at && t.status !== 'done'))

// ---------- 日期窗口：今天 -7 ~ +21 兜底并覆盖所有任务起止；navOffset 支持 ‹ › 平移 ----------
const navOffset = ref(0)
const dayStart = computed(() => {
  let min = dayjs().subtract(7, 'day').startOf('day')
  for (const t of tasks.value) {
    for (const k of ['start_at', 'due_at']) {
      const d = t[k] ? dayjs(t[k]).startOf('day') : null
      if (d && d.isBefore(min)) min = d
    }
  }
  return min.add(navOffset.value, 'day')
})
const dayEnd = computed(() => {
  let max = dayjs().add(21, 'day').startOf('day')
  for (const t of tasks.value) {
    for (const k of ['start_at', 'due_at']) {
      const d = t[k] ? dayjs(t[k]).startOf('day') : null
      if (d && d.isAfter(max)) max = d
    }
  }
  return max.add(navOffset.value, 'day')
})
const days = computed(() => {
  const arr = []
  let d = dayStart.value
  while (!d.isAfter(dayEnd.value)) {
    arr.push({
      key: d.format('YYYY-MM-DD'),
      d,
      week: WEEK[d.day()],
      isToday: d.isSame(dayjs(), 'day'),
      isWeekend: d.day() === 0 || d.day() === 6,
    })
    d = d.add(1, 'day')
  }
  return arr
})
const todayIdx = computed(() => Math.max(0, dayjs().startOf('day').diff(dayStart.value, 'day')))

// 顶部分段：日/周=月分段（M月）；月粒度=年分段（YYYY年）
const monthSegs = computed(() => segmentBy((d) => d.format('YYYY-MM'), (d) => `${d.month() + 1}月`))
const yearSegs = computed(() => segmentBy((d) => d.format('YYYY'), (d) => `${d.year()}年`))
const topSegs = computed(() => (granularity.value === 'month' ? yearSegs.value : monthSegs.value))
function segmentBy(keyFn, labelFn) {
  const segs = []
  for (const day of days.value) {
    const k = keyFn(day.d)
    const last = segs[segs.length - 1]
    if (last && last.k === k) last.span += 1
    else segs.push({ k, label: labelFn(day.d), span: 1 })
  }
  return segs
}
// 日表头单元：日=每天(日期+星期)；周=每天(仅日期)；月=每月(月份)
const headerCells = computed(() => {
  if (granularity.value === 'month') {
    return monthSegs.value.map((s, i) => ({ key: s.k + i, label: s.label, span: s.span, isToday: false, isWeekend: false }))
  }
  const withWeek = granularity.value === 'day'
  return days.value.map((d) => ({ key: d.key, label: d.d.date(), week: withWeek ? d.week : '', span: 1, isToday: d.isToday, isWeekend: d.isWeekend }))
})

// ---------- 泳道分节：清单=board_groups / 收集箱=inbox_board_groups（可管理）；全部=按清单泳道（对齐官方文件夹）；其余视图平面 ----------
const groupDefs = computed(() => {
  const key = store.activeListKey
  if (key.startsWith('list:')) {
    return (store.activeList?.board_groups || []).map((name) => ({ key: name, label: name, manageable: true }))
  }
  if (key === 'smart:inbox') {
    return store.inboxGroups.map((name) => ({ key: name, label: name, manageable: true }))
  }
  if (key === 'smart:all') {
    // 全部视图按清单分泳道（官方文件夹时间线的对应形态）
    return store.lists.filter((l) => l.kind !== 'note').map((l) => ({ key: 'list:' + l.id, label: l.name, manageable: false }))
  }
  return []
})
const grouped = computed(() => groupDefs.value.length > 0)

function rangeOf(t) {
  let start = (t.start_at ? dayjs(t.start_at) : dayjs(t.due_at)).startOf('day')
  let end = dayjs(t.due_at || t.start_at).startOf('day')
  if (end.isBefore(start)) [start, end] = [end, start]
  return { start, end }
}

// 单节任务条打包：按开始日排序后贪心装入首个不重叠泳道，返回 bars（含像素定位）与泳道数
function buildSection(def, secTasks) {
  const lanes = [] // 每泳道记录最后占用的结束日 idx
  const bars = []
  const sorted = [...secTasks].sort((a, b) => rangeOf(a).start.valueOf() - rangeOf(b).start.valueOf())
  const maxIdx = days.value.length - 1
  for (const t of sorted) {
    const { start, end } = rangeOf(t)
    let si = start.diff(dayStart.value, 'day')
    let ei = end.diff(dayStart.value, 'day')
    if (ei < 0 || si > maxIdx) continue // 不在可视窗口
    si = Math.max(0, si)
    ei = Math.min(maxIdx, ei)
    let lane = lanes.findIndex((lastEnd) => lastEnd < si)
    if (lane === -1) {
      lanes.push(ei)
      lane = lanes.length - 1
    } else {
      lanes[lane] = ei
    }
    bars.push({
      t,
      left: si * PPD.value,
      width: Math.max((ei - si + 1) * PPD.value - 3, 10),
      top: lane * LANE_H + 4,
    })
  }
  return { ...def, tasks: secTasks, bars, laneCount: Math.max(lanes.length, 1) }
}

const sections = computed(() => {
  if (!grouped.value) {
    return [buildSection({ key: '__flat', label: '', manageable: false }, scheduled.value)]
  }
  const isAll = store.activeListKey === 'smart:all'
  // 每泳道自带 match；未分组=清单/收集箱按 group  miss、全部按无清单
  const defs = [
    isAll
      ? { key: '__ungrouped', label: '未分组', manageable: false, match: (t) => !t.list_id }
      : { key: '__ungrouped', label: '未分组', manageable: false, match: (t) => !t.group || !groupKeySet.value.has(t.group) },
    ...groupDefs.value.map((g) =>
      isAll
        ? { ...g, match: (t) => t.list_id === g.key.slice(5) }
        : { ...g, match: (t) => t.group === g.key }
    ),
  ]
  return defs.map((d) => buildSection(d, scheduled.value.filter(d.match)))
})
const groupKeySet = computed(() => new Set(groupDefs.value.map((g) => g.key)))

const collapsedSecs = ref({})
function toggleSec(sec) {
  collapsedSecs.value = { ...collapsedSecs.value, [sec.key]: !collapsedSecs.value[sec.key] }
}
function secHeight(sec) {
  if (grouped.value && collapsedSecs.value[sec.key]) return 30
  return sec.laneCount * LANE_H + 6
}

// 任务条颜色：清单色 / 优先级色（显示设置可切，本地记忆）；条=同色系 pastel 底+深色字（对齐官方）
const colorMode = ref(localStorage.getItem('task-timeline-colormode') || 'list')
watch(colorMode, (v) => localStorage.setItem('task-timeline-colormode', v))
function rawColor(t) {
  if (colorMode.value === 'priority') return prioColor(t.priority) || '#4772fa'
  return store.lists.find((l) => l.id === t.list_id)?.color || '#4772fa'
}
function hexToRgba(hex, a) {
  const h = hex.replace('#', '')
  const n = parseInt(h.length === 3 ? h.split('').map((c) => c + c).join('') : h, 16)
  return `rgba(${(n >> 16) & 255},${(n >> 8) & 255},${n & 255},${a})`
}
function barStyle(t) {
  const c = rawColor(t)
  return { background: hexToRgba(c, 0.18), color: c }
}
const prioOptions = [
  { value: 3, label: '高优先级', color: '#f56c6c' },
  { value: 2, label: '中优先级', color: '#e6a23c' },
  { value: 1, label: '低优先级', color: '#409eff' },
  { value: 0, label: '无优先级', color: '#9ca3af' },
]
const prioColor = (p) => prioOptions.find((o) => o.value === p)?.color
const prioLabel = (p) => prioOptions.find((o) => o.value === p)?.label

// ---------- 顶部控制：‹ › 平移窗口 / 今天回中 ----------
function shift(dir) {
  navOffset.value += dir * (granularity.value === 'month' ? 62 : 14)
}
function backToday() {
  navOffset.value = 0
  scrollToToday()
}

// ---------- 任务条拖动：水平位移 = 平移起止日期；未移动视为点击打开详情 ----------
const scrollRef = ref(null)
let dragState = null
let suppressBlankClick = false // 拖动任务条后抑制紧随的 click，避免误弹添加框
function onBarDown(e, t) {
  e.preventDefault()
  dragState = { t, x0: e.clientX, el: e.currentTarget, days: 0, moved: false }
  window.addEventListener('pointermove', onBarMove)
  window.addEventListener('pointerup', onBarUp, { once: true })
}
function onBarMove(e) {
  if (!dragState) return
  const dx = e.clientX - dragState.x0
  const dDays = Math.round(dx / PPD.value)
  if (Math.abs(dx) > 5) dragState.moved = true
  if (dDays !== dragState.days) {
    dragState.days = dDays
    dragState.el.style.transform = `translateX(${dDays * PPD.value}px)`
  }
}
async function onBarUp() {
  window.removeEventListener('pointermove', onBarMove)
  if (!dragState) return
  const { t, el, days: dd, moved } = dragState
  dragState = null
  if (!moved) {
    openTaskCard(t, el)
    return
  }
  el.style.transform = ''
  suppressBlankClick = true // 凡发生位移都抑制紧随的 click（即使位移不足一天未改期）
  if (!dd) return
  const payload = { due_at: dayjs(t.due_at).add(dd, 'day').toISOString() }
  if (t.start_at) payload.start_at = dayjs(t.start_at).add(dd, 'day').toISOString()
  await store.updateTask(t.id, payload)
}

// ---------- 任务条边缘拖拽调时长（对齐官方：拖右缘改截止/时长，拖左缘改开始） ----------
let rzState = null
function onResizeDown(e, t, side, barEl) {
  e.preventDefault()
  const rect = barEl.getBoundingClientRect()
  const { start, end } = rangeOf(t)
  rzState = {
    t,
    side,
    el: barEl,
    x0: e.clientX,
    days: 0,
    origLeft: rect.left,
    origWidth: rect.width,
    startIdx: start.diff(dayStart.value, 'day'),
    endIdx: end.diff(dayStart.value, 'day'),
  }
  window.addEventListener('pointermove', onResizeMove)
  window.addEventListener('pointerup', onResizeUp, { once: true })
}
function onResizeMove(e) {
  if (!rzState) return
  const dDays = Math.round((e.clientX - rzState.x0) / PPD.value)
  let nd = dDays
  if (rzState.side === 'r') nd = Math.max(dDays, rzState.startIdx - rzState.endIdx) // 最短 1 天
  else nd = Math.min(dDays, rzState.endIdx - rzState.startIdx) // 左缘不越过右缘
  rzState.days = nd
  const px = nd * PPD.value
  if (rzState.side === 'r') {
    rzState.el.style.width = Math.max(rzState.origWidth + px, PPD.value - 3) + 'px'
  } else {
    rzState.el.style.left = rzState.origLeft + px + 'px'
    rzState.el.style.width = Math.max(rzState.origWidth - px, PPD.value - 3) + 'px'
  }
}
async function onResizeUp() {
  window.removeEventListener('pointermove', onResizeMove)
  if (!rzState) return
  const { t, side, el, days: nd } = rzState
  rzState = null
  el.style.width = ''
  el.style.left = ''
  if (!nd) return
  suppressBlankClick = true
  const due = dayjs(t.due_at || t.start_at)
  const tod = { h: due.hour(), m: due.minute() }
  const dayAt = (idx) => dayStart.value.add(idx, 'day').hour(tod.h).minute(tod.m).second(0)
  const payload = {}
  if (side === 'r') {
    // 右缘：移动截止日；无 start_at 的任务先补 start_at=原截止日（变区间），截止日顺延
    if (!t.start_at) payload.start_at = dayStart.value.add(rzStartIdxOf(t), 'day').hour(tod.h).minute(tod.m).second(0).toISOString()
    payload.due_at = dayAt(rangeOf(t).end.diff(dayStart.value, 'day') + nd).toISOString()
  } else {
    // 左缘：移动开始日；无 start_at 的任务先补 start_at=原截止日（区间右端不动）
    if (!t.start_at) payload.start_at = dayStart.value.add(rzStartIdxOf(t), 'day').hour(tod.h).minute(tod.m).second(0).toISOString()
    else payload.start_at = dayAt(t.start_at ? dayjs(t.start_at).diff(dayStart.value, 'day') + nd : nd).toISOString()
  }
  await store.updateTask(t.id, payload)
}
// 无 start_at 任务补 start_at 时用其当前起始（=截止）日的 idx
function rzStartIdxOf(t) {
  return rangeOf(t).start.diff(dayStart.value, 'day')
}

// ---------- 安排任务面板：拖入时间线排期（对齐官方右侧「安排任务」） ----------
const uspOpen = ref(localStorage.getItem('task-timeline-usp') !== '0')
watch(uspOpen, (v) => localStorage.setItem('task-timeline-usp', v ? '1' : '0'))
const uspDrag = ref(null) // { t, x0, y0, dragging }
const uspGhost = ref(null) // { t, x, y }
const dropGhost = ref(null) // { left, top, width, bg, color, title }
function onUspDown(e, t) {
  if (e.button !== 0) return
  uspDrag.value = { t, x0: e.clientX, y0: e.clientY, dragging: false }
  window.addEventListener('pointermove', onUspMove)
  window.addEventListener('pointerup', onUspUp, { once: true })
}
function onUspMove(e) {
  const d = uspDrag.value
  if (!d) return
  if (!d.dragging && Math.hypot(e.clientX - d.x0, e.clientY - d.y0) > 6) {
    d.dragging = true
    uspGhost.value = { t: d.t, x: e.clientX + 12, y: e.clientY + 10 }
  }
  if (d.dragging) {
    uspGhost.value = { ...uspGhost.value, x: e.clientX + 12, y: e.clientY + 10 }
    updateDropGhost(e.clientX, e.clientY)
  }
}
function updateDropGhost(cx, cy) {
  const hit = dropTargetAt(cx, cy)
  if (!hit) {
    dropGhost.value = null
    return
  }
  const st = barStyle(uspDrag.value.t)
  dropGhost.value = {
    left: (grouped.value ? LEFT_W : 0) + hit.idx * PPD.value + 1,
    top: hit.top,
    width: PPD.value - 3,
    bg: st.background,
    color: st.color,
    title: uspDrag.value.t.title,
  }
}
// 命中检测：光标在滚动区内 → 由 x 算日期列、y 算泳道行高（占位条贴在命中泳道轨道）
function dropTargetAt(cx, cy) {
  if (!scrollRef.value) return null
  const rect = scrollRef.value.getBoundingClientRect()
  if (cx < rect.left || cx > rect.right || cy < rect.top || cy > rect.bottom) return null
  const x = cx - rect.left + scrollRef.value.scrollLeft - (grouped.value ? LEFT_W : 0)
  const y = cy - rect.top + scrollRef.value.scrollTop
  const idx = Math.min(days.value.length - 1, Math.max(0, Math.floor(x / PPD.value)))
  const sec = sections.value.find((s) => y >= secTop(s) && y < secTop(s) + secHeight(s))
  return { idx, day: dayStart.value.add(idx, 'day'), top: (sec ? secTop(sec) : y - 13) + 6, gkey: sec?.manageable ? sec.key : '' }
}
function secTop(sec) {
  let top = MONTH_H + DAY_H
  for (const s of sections.value) {
    if (s === sec) return top
    top += secHeight(s)
  }
  return top
}
async function onUspUp(e) {
  window.removeEventListener('pointermove', onUspMove)
  const d = uspDrag.value
  uspDrag.value = null
  uspGhost.value = null
  dropGhost.value = null
  if (!d?.dragging) return
  suppressBlankClick = true
  const hit = dropTargetAt(e.clientX, e.clientY)
  if (!hit) return
  const payload = { due_at: hit.day.hour(0).minute(0).second(0).toISOString(), all_day: true }
  // 落在可管理泳道（清单分组/收集箱分组）→ 带分组，规则与空白添加一致
  const sameCtx = store.activeListKey.startsWith('list:')
    ? (d.t.list_id || null) === store.activeListKey.replace('list:', '')
    : store.activeListKey === 'smart:inbox' && !d.t.list_id
  if (hit.gkey && hit.gkey !== '__ungrouped' && sameCtx) payload.group = hit.gkey
  await store.updateTask(d.t.id, payload)
  // 拖入的任务若不在当前智能清单范围，刷新让列表归位
  if (store.activeListKey.startsWith('smart:') && !['smart:all', 'smart:inbox'].includes(store.activeListKey)) {
    await store.fetchTasks()
  }
}

// ---------- 控制条 ⋯：显示设置 ----------
const dispOpen = ref(false)
function onCtlCmd(cmd) {
  if (cmd === 'display') dispOpen.value = true
}

// ---------- 点击任务条：迷你任务卡片（对齐主流待办应用），锚在任务条右侧 ----------
const VIEW_W = 400
const VIEW_H = 460
const viewState = ref(null) // { id, left, top }
function openTaskCard(t, el) {
  addState.value = null // 与添加卡片互斥
  if (!scrollRef.value) return
  const rect = el.getBoundingClientRect()
  const crect = scrollRef.value.getBoundingClientRect()
  let left = rect.right - crect.left + scrollRef.value.scrollLeft + 8
  left = Math.max(grouped.value ? LEFT_W : 0, Math.min(left, scrollRef.value.scrollLeft + scrollRef.value.clientWidth - VIEW_W - 8))
  let top = rect.top - crect.top + scrollRef.value.scrollTop - 6
  top = Math.max(MONTH_H + DAY_H + 2, Math.min(top, scrollRef.value.scrollTop + scrollRef.value.clientHeight - VIEW_H))
  viewState.value = { id: t.id, left, top }
}

// ---------- 点击空白添加任务（对齐主流待办应用时间线）：占位条 + 迷你添加卡片（日期/优先级/清单） ----------
const ADD_CARD_W = 308
const ADD_CARD_H = 230
const addState = ref(null) // { day, due, allDay, startAt, group, left, cardLeft, top }
const addTitle = ref('')
const addDesc = ref('')
const addPriority = ref(0)
const addListId = ref(null)
const addInputRef = ref(null)
const addDescRef = ref(null)

// 点击日期已过 → 红色「已延期N天」（对齐主流待办应用添加卡）
const addOverdueDays = computed(() => {
  if (!addState.value?.due) return 0
  return Math.max(0, dayjs().startOf('day').diff(dayjs(addState.value.due).startOf('day'), 'day'))
})
// 卡片底部清单选择：默认当前清单/收集箱（__inbox 哨兵）
const addListName = computed(() =>
  addListId.value === '__inbox' ? '收集箱' : store.lists.find((l) => l.id === addListId.value)?.name || '收集箱',
)
const addListColor = computed(() => store.lists.find((l) => l.id === addListId.value)?.color || '#4772fa')

function onBlankClick(e) {
  if (suppressBlankClick) {
    suppressBlankClick = false
    return
  }
  // 任务条/分组名/表头/控制条/添加卡片/任务卡片自身不触发；无创建权限忽略
  if (e.target.closest('.tl-bar, .tl-sec-label, .tl-month-row, .tl-day-row, .tl-add, .tl-view')) return
  viewState.value = null // 点空白关掉任务卡片
  if (!authStore.hasPerm('task:create')) return
  if (!scrollRef.value) return
  const rect = scrollRef.value.getBoundingClientRect()
  const x = e.clientX - rect.left + scrollRef.value.scrollLeft - (grouped.value ? LEFT_W : 0)
  const idx = Math.min(days.value.length - 1, Math.max(0, Math.floor(x / PPD.value)))
  const y = e.clientY - rect.top + scrollRef.value.scrollTop
  // 分组泳道内点击 → 新任务带该分组（未分组/平面泳道不带）
  const gkey = e.target.closest('[data-gkey]')?.dataset.gkey
  const day = dayStart.value.add(idx, 'day')
  const left = (grouped.value ? LEFT_W : 0) + idx * PPD.value
  // 卡片不超出可视区右边/底边
  const cardLeft = Math.max(grouped.value ? LEFT_W : 0, Math.min(left, scrollRef.value.scrollLeft + scrollRef.value.clientWidth - ADD_CARD_W - 8))
  const top = Math.max(MONTH_H + DAY_H + 4, Math.min(y - 11, scrollRef.value.scrollTop + scrollRef.value.clientHeight - ADD_CARD_H))
  addState.value = {
    day,
    due: day.hour(0).minute(0).second(0).toISOString(),
    allDay: true,
    startAt: null,
    group: gkey && gkey !== '__ungrouped' ? gkey : null,
    left,
    cardLeft,
    top,
  }
  addTitle.value = ''
  addDesc.value = ''
  addPriority.value = 0
  addListId.value = store.activeListKey.startsWith('list:') ? store.activeListKey.replace('list:', '') : '__inbox'
  nextTick(() => addInputRef.value?.focus())
}

// 卡片打开时：全局 pointerdown 捕获——点卡片/弹层外部则提交或取消（日期弹层是 teleport 的，不能用 blur）
watch(addState, (v) => {
  if (v) window.addEventListener('pointerdown', onGlobalDown, true)
  else window.removeEventListener('pointerdown', onGlobalDown, true)
})
function onGlobalDown(e) {
  if (!addState.value) return
  if (e.target.closest('.tl-add, .el-popper, .el-select-dropdown')) return
  if (addTitle.value.trim()) submitAdd()
  else cancelAdd()
}

function onAddDate(payload) {
  // payload: { due_at, all_day, start_at, reminders, persistent_reminder, recurrence }
  if (!addState.value) return
  addState.value.due = payload.due_at
  addState.value.allDay = payload.all_day
  addState.value.startAt = payload.start_at
  addState.value.datePayload = payload
}

async function submitAdd() {
  if (!addState.value) return
  const title = addTitle.value.trim()
  const { due, allDay, startAt, group } = addState.value
  const listId = addListId.value === '__inbox' ? null : addListId.value
  const data = { title, due_at: due, all_day: allDay, list_id: listId }
  const note = addDesc.value.trim()
  if (note) data.note = note
  const dp = addState.value.datePayload
  if (startAt) data.start_at = startAt
  if (dp) {
    if (dp.reminders?.length) data.reminders = dp.reminders
    if (dp.recurrence) data.recurrence = dp.recurrence
  }
  addState.value = null
  if (addPriority.value) data.priority = addPriority.value
  // 分组仅在目标与当前泳道上下文一致时保留（清单→同清单 / 收集箱→收集箱），否则跨清单带组会被后端拒绝
  const sameCtx = store.activeListKey.startsWith('list:')
    ? listId === store.activeListKey.replace('list:', '')
    : store.activeListKey === 'smart:inbox' && listId === null
  if (group && sameCtx) data.group = group
  store.applyDefaults(data)
  await store.createTask(data)
  // 智能清单（今天/明天/最近7天）无法本地预判新任务是否命中视图，直接刷新
  if (store.activeListKey.startsWith('smart:') && !['smart:all', 'smart:inbox'].includes(store.activeListKey)) {
    await store.fetchTasks()
  }
}
function cancelAdd() {
  addState.value = null
}

// 进入视图/数据加载后滚动到今天列（紧跟吸左分组列之后，保证任务条可见）
function scrollToToday() {
  nextTick(() => {
    if (scrollRef.value) scrollRef.value.scrollLeft = Math.max(0, todayIdx.value * PPD.value - 60)
  })
}
onMounted(scrollToToday)
watch(() => store.tasks.length, scrollToToday)
</script>

<style scoped>
.tl-wrap {
  display: flex;
  height: 100%;
  overflow: hidden;
}
.tl-main {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}
.tl-empty {
  padding-top: 60px;
}
.tl-scroll {
  height: 100%;
  overflow: auto;
}
.tl-inner {
  position: relative;
  min-height: 100%;
}
/* ---------- 双表头：月行 + 日行（均吸顶） ---------- */
.tl-month-row {
  display: flex;
  position: sticky;
  top: 0;
  z-index: 6;
  height: 26px;
  background: #fff;
  border-bottom: 1px solid var(--ss-bg);
}
.tl-day-row {
  display: flex;
  position: sticky;
  top: 26px;
  z-index: 6;
  background: #fff;
  border-bottom: 1px solid var(--ss-border);
}
.tl-sticky {
  position: sticky;
  left: 0;
  z-index: 7;
  background: #fff;
}
.tl-corner {
  width: 120px;
  flex-shrink: 0;
  border-right: 1px solid var(--ss-border);
}
.tl-month {
  flex-shrink: 0;
  padding: 4px 0;
  font-size: 12px;
  color: var(--ss-text-muted);
  border-left: 1px solid var(--ss-bg);
  white-space: nowrap;
}
/* 月份标签吸左：横向滚动时当月标签钉在分组列右侧（对齐主流待办应用） */
.tl-month-label {
  position: sticky;
  display: inline-block;
  padding: 0 8px;
}
/* 吸右控制条：‹ › 今天 粒度（对齐主流待办应用表头右上） */
.tl-controls {
  margin-left: auto;
  position: sticky;
  right: 0;
  z-index: 8;
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 0 8px;
  background: #fff;
}
.tl-ctl {
  cursor: pointer;
  color: var(--ss-text-muted);
  padding: 2px;
  border-radius: 4px;
}
.tl-ctl:hover {
  background: var(--ss-bg);
  color: var(--ss-text);
}
.tl-ctl-btn {
  display: inline-flex;
  align-items: center;
  font-size: 12px;
  color: var(--ss-text-secondary);
  cursor: pointer;
  padding: 2px 8px;
  border-radius: 4px;
  white-space: nowrap;
}
.tl-ctl-btn:hover {
  background: var(--ss-bg);
}
/* 两端平移箭头（对齐主流待办应用时间线头尾 ‹ ›）：吸左/吸右悬浮在日表头上 */
.tl-nav {
  position: sticky;
  z-index: 8;
  width: 24px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ss-text-muted);
  background: #fff;
  cursor: pointer;
}
.tl-nav:hover {
  color: var(--ss-primary);
}
.tl-nav-l {
  margin-right: -24px;
  border-right: 1px solid var(--ss-bg);
}
.tl-nav-r {
  right: 0;
  margin-left: -24px;
  border-left: 1px solid var(--ss-bg);
}
.tl-day {
  flex-shrink: 0;
  text-align: center;
  padding: 4px 0;
  font-size: 12px;
  color: var(--ss-text-secondary);
  border-left: 1px solid var(--ss-bg);
  overflow: hidden;
}
.tl-day.today {
  color: var(--ss-primary);
  font-weight: 600;
}
.tl-day-num {
  display: block;
  font-size: 13px;
}
.tl-day-week {
  display: block;
  font-size: 11px;
  color: var(--ss-text-muted);
}
/* ---------- 背景层：周末灰底 / 今天主色浅底 ---------- */
.tl-bg {
  position: absolute;
  top: 60px; /* MONTH_H + DAY_H */
  bottom: 0;
  z-index: 0;
  pointer-events: none;
}
.tl-bg-cell {
  position: absolute;
  top: 0;
  bottom: 0;
}
.tl-bg-cell.weekend {
  background: #fafafa;
}
.tl-bg-cell.today {
  background: var(--ss-primary-light);
}
/* ---------- 泳道分节 ---------- */
.tl-section {
  display: flex;
  position: relative;
  z-index: 1;
  border-bottom: 1px solid var(--ss-bg);
}
.tl-sec-label {
  width: 120px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 0 8px;
  font-size: 12px;
  color: var(--ss-text-secondary);
  border-right: 1px solid var(--ss-border);
  cursor: pointer;
  overflow: hidden;
}
.tl-sec-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tl-sec-count {
  margin-left: auto;
  font-size: 11px;
  color: var(--ss-text-muted);
}
.fold-arrow {
  transition: transform 0.15s;
  flex-shrink: 0;
}
.fold-arrow.expanded {
  transform: rotate(90deg);
}
.tl-track {
  position: relative;
  flex-shrink: 0;
  height: 100%;
  background: repeating-linear-gradient(to right, var(--ss-bg) 0 1px, transparent 1px var(--ppd, 48px));
}
.tl-bar {
  position: absolute;
  height: 22px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 22px;
  padding: 0 8px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  cursor: grab;
  user-select: none;
  opacity: 0.92;
}
.tl-bar:hover {
  opacity: 1;
}
.tl-bar.done {
  opacity: 0.45;
}
/* 两端调时长热区（对齐官方：贴边出现把手，光标 ew-resize） */
.tl-rz {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 8px;
  cursor: ew-resize;
  z-index: 2;
}
.tl-rz-l { left: -2px; }
.tl-rz-r { right: -2px; }
.tl-rz::after {
  content: '';
  position: absolute;
  top: 4px;
  bottom: 4px;
  left: 3px;
  width: 2px;
  border-radius: 1px;
  background: currentColor;
  opacity: 0;
  transition: opacity 0.12s;
}
.tl-rz:hover::after {
  opacity: 0.55;
}
/* 安排任务拖入落点占位条 */
.tl-drop-ghost {
  position: absolute;
  height: 22px;
  line-height: 22px;
  border-radius: 6px;
  font-size: 12px;
  padding: 0 8px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  opacity: 0.85;
  pointer-events: none;
  z-index: 4;
  outline: 1.5px dashed currentColor;
  outline-offset: 1px;
}
/* 右侧安排任务面板（对齐官方：白底贴右、标题+计数、pastel 条列表） */
.tl-usp {
  width: 264px;
  flex-shrink: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-left: 1px solid var(--ss-border);
}
.tl-usp-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 12px 14px 10px;
  border-bottom: 1px solid var(--ss-border-light, #f0f0f0);
}
.tl-usp-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ss-text, #303133);
}
.tl-usp-count {
  font-size: 12px;
  color: var(--ss-text-muted, #a8abb2);
  font-variant-numeric: tabular-nums;
}
.tl-usp-close {
  margin-left: auto;
  display: inline-flex;
  padding: 3px;
  border-radius: 4px;
  color: var(--ss-text-muted, #a8abb2);
  cursor: pointer;
}
.tl-usp-close:hover {
  background: var(--ss-fill, #f7f7f9);
  color: var(--ss-text, #303133);
}
.tl-usp-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.tl-usp-empty {
  padding: 40px 0;
  text-align: center;
  font-size: 12px;
  color: var(--ss-text-muted, #a8abb2);
}
.tl-usp-item {
  display: flex;
  align-items: center;
  gap: 4px;
  height: 26px;
  padding: 0 10px;
  border-radius: 6px;
  font-size: 12px;
  cursor: grab;
  user-select: none;
  overflow: hidden;
  white-space: nowrap;
}
.tl-usp-item:hover {
  filter: brightness(0.96);
}
.tl-usp-item.dragging {
  opacity: 0.35;
}
.tl-usp-item-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* 拖出的跟随幽灵条 */
.tl-usp-ghost {
  position: fixed;
  z-index: 3000;
  height: 26px;
  max-width: 240px;
  padding: 0 10px;
  border-radius: 6px;
  font-size: 12px;
  line-height: 26px;
  pointer-events: none;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.18);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
}
/* 控制条按钮激活态（安排任务展开中） */
.tl-ctl-btn.on {
  color: var(--ss-primary);
  background: var(--ss-primary-light, #eef1fe);
}
/* 显示设置弹窗 */
.tl-disp-label {
  font-size: 13px;
  color: var(--ss-text-secondary, #909399);
  margin-bottom: 8px;
}
.tl-disp-radios {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
}
.tl-prio {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  margin-right: 4px;
  vertical-align: 1px;
}
.tl-today-line {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 2px;
  background: var(--ss-primary);
  opacity: 0.5;
  pointer-events: none;
  z-index: 2;
}
/* 点击空白快速添加：蓝色占位条 + 迷你添加卡片（对齐主流待办应用） */
.tl-add-ghost {
  position: absolute;
  height: 26px;
  border-radius: 13px;
  background: var(--ss-primary);
  opacity: 0.9;
  pointer-events: none;
  z-index: 3;
}
.tl-add {
  position: absolute;
  z-index: 9;
}
.tl-add-card {
  width: 308px;
  height: 230px; /* 固定卡片大小（对齐主流待办应用），不随内容收缩 */
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.16);
  border: 1px solid rgba(0, 0, 0, 0.06);
  overflow: hidden;
}
.tl-add-date-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 11px 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
}
.tl-add-date {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--ss-primary);
  cursor: pointer;
}
.tl-add-date.overdue {
  color: #e64a3b;
}
.tl-add-flag {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
}
.tl-add-flag:hover {
  background: rgba(0, 0, 0, 0.05);
}
.tl-add-title {
  width: 100%;
  border: none;
  outline: none;
  font-size: 14px;
  font-weight: 600;
  font-family: inherit;
  padding: 12px 16px 4px;
  background: transparent;
  color: #333;
  box-sizing: border-box;
  flex-shrink: 0;
}
.tl-add-title::placeholder {
  color: #b8b8b8;
  font-weight: 500;
}
.tl-add-desc {
  flex: 1;
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  font-size: 13px;
  font-family: inherit;
  line-height: 1.6;
  padding: 4px 16px 8px;
  background: transparent;
  color: #555;
  box-sizing: border-box;
}
.tl-add-desc::placeholder {
  color: #c5c5c5;
}
.tl-add-footer {
  padding: 4px 16px 12px;
  flex-shrink: 0;
}
.tl-add-list-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #333;
  cursor: pointer;
  padding: 3px 6px;
  margin-left: -6px;
  border-radius: 5px;
}
.tl-add-list-trigger:hover {
  background: rgba(0, 0, 0, 0.04);
}
.tl-add-list-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
</style>
