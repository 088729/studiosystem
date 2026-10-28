<template>
  <div class="month-view">
    <!-- 星期表头（周日起，与主流待办应用一致） -->
    <div class="mv-weekdays">
      <div v-for="w in WEEKDAYS" :key="w" class="mv-weekday">{{ w }}</div>
    </div>

    <div class="mv-grid">
      <div
        v-for="d in calendarDays"
        :key="d.format('YYYY-MM-DD')"
        class="mv-cell"
        :class="{ 'other-month': !d.isSame(cursor, 'month'), today: d.isSame(dayjs(), 'day') }"
        @click="onCellClick(d)"
        @dragover.prevent
        @drop="onDrop($event, d)"
      >
        <div class="cell-head">
          <span class="cell-day">{{ d.date() }}</span>
          <!-- 节假日调休角标 + 农历（设置-日期与时间开启后显示，与日期弹层同一套逻辑） -->
          <span v-if="cellMeta(d).hd" class="cell-hd" :class="cellMeta(d).hd === '班' ? 'work' : 'rest'">{{ cellMeta(d).hd }}</span>
          <span v-if="cellMeta(d).lunar" class="cell-lunar" :class="{ fest: cellMeta(d).fest }">{{ cellMeta(d).lunar }}</span>
        </div>
        <div
          v-for="task in tasksOf(d).slice(0, 3)"
          :key="task.id"
          class="task-chip"
          :class="[`p${task.priority || 0}`, { done: task.status === 'done' }]"
          draggable="true"
          @dragstart="onDragStart($event, task)"
          @click.stop="$emit('open', task)"
        >
          <span class="chip-check" />
          <span class="chip-title">{{ task.title }}</span>
          <span class="chip-time">{{ timeOf(task) }}</span>
        </div>
        <div v-if="tasksOf(d).length > 3" class="more-chip">+{{ tasksOf(d).length - 3 }}</div>
        <div v-if="focusMinutesOf(d)" class="focus-hint" :title="`当日专注 ${focusMinutesOf(d)} 分钟`">🍅 {{ focusMinutesOf(d) }}分钟</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import { useTaskStore } from '@/stores/task'
import { lunarLabel, holidayTag } from '../../utils'

const props = defineProps({
  tasks: Array,
  focusSessions: { type: Array, default: () => [] },  // 已完成专注会话（当日总分钟指示）
  cursor: Object,
})
const emit = defineEmits(['open', 'create', 'navigate', 'reschedule'])

const store = useTaskStore()
const showLunar = computed(() => !!store.settings?.show_lunar)
const showHoliday = computed(() => !!store.settings?.show_holiday)
// 每个格子的农历/节假日信息（设置关闭时为空，避免无谓计算）
const metaMap = computed(() => {
  const map = {}
  if (!showLunar.value && !showHoliday.value) return map
  for (const d of calendarDays.value) {
    const l = showLunar.value ? lunarLabel(d) : null
    map[d.format('YYYY-MM-DD')] = {
      lunar: l ? l.text : '',
      fest: l ? l.fest : false,
      hd: showHoliday.value ? holidayTag(d) : '',
    }
  }
  return map
})
function cellMeta(d) {
  return metaMap.value[d.format('YYYY-MM-DD')] || { lunar: '', fest: false, hd: '' }
}

// 星期表头/起点跟随「每周开始于」设置（设置-日期与时间）
const weekStart = computed(() => (store.settings?.week_start === 'monday' ? 1 : 0))
const WEEKDAYS = computed(() =>
  weekStart.value === 1
    ? ['周一', '周二', '周三', '周四', '周五', '周六', '周日']
    : ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
)

// 6 行 × 7 列：从月初所在周的起始日起
const calendarDays = computed(() => {
  const monthStart = props.cursor.startOf('month')
  const gridStart = monthStart.subtract((monthStart.day() - weekStart.value + 7) % 7, 'day')
  return Array.from({ length: 42 }, (_, i) => gridStart.add(i, 'day'))
})

const calendarMap = computed(() => {
  const map = {}
  for (const t of props.tasks || []) {
    const d = dayjs(t.due_at).format('YYYY-MM-DD')
    ;(map[d] = map[d] || []).push(t)
  }
  // 日内按时间排序
  for (const list of Object.values(map)) {
    list.sort((a, b) => new Date(a.start_at || a.due_at) - new Date(b.start_at || b.due_at))
  }
  return map
})

const tasksOf = (day) => calendarMap.value[day.format('YYYY-MM-DD')] || []

// 当日专注总分钟（🍅 指示）：按 started_at 归日，actual_seconds 四舍五入到分钟
const focusMinutesMap = computed(() => {
  const map = {}
  for (const f of props.focusSessions || []) {
    if (!f.started_at) continue
    const d = dayjs(f.started_at).format('YYYY-MM-DD')
    map[d] = (map[d] || 0) + Math.max(1, Math.round((f.actual_seconds || 0) / 60))
  }
  return map
})
const focusMinutesOf = (day) => focusMinutesMap.value[day.format('YYYY-MM-DD')] || 0

const timeOf = (t) => {
  if (t.all_day) return '全天'
  const base = t.start_at || t.due_at
  return base ? dayjs(base).format('HH:mm') : ''
}

function onDragStart(e, task) {
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', String(task.id))
}

function onDrop(e, day) {
  const task = (props.tasks || []).find((t) => String(t.id) === e.dataTransfer.getData('text/plain'))
  if (task && !dayjs(task.due_at).isSame(day, 'day')) emit('reschedule', task, day)
}

function onCellClick(day) {
  if (tasksOf(day).length) return
  ElMessageBox.prompt('任务标题', `${day.format('MM-DD')} 新建任务`, {
    confirmButtonText: '创建',
    cancelButtonText: '取消',
    inputValidator: (v) => !!v?.trim() || '标题不能为空',
  })
    .then(() => {
      emit('create', day.startOf('day').hour(9), 9)
    })
    .catch(() => {})
}
</script>

<style scoped>
.month-view {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
}

/* ===== 星期表头 ===== */
.mv-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  border-bottom: 1px solid var(--ss-border);
  flex-shrink: 0;
}
.mv-weekday {
  text-align: center;
  font-size: 12px;
  color: var(--ss-text-muted);
  padding: 8px 0;
}

/* ===== 日期网格：6 行等高填满 ===== */
.mv-grid {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr)); /* minmax(0,·) 防节日名撑宽列 */
  grid-template-rows: repeat(6, 1fr);
  min-height: 0;
}
.mv-cell {
  border-right: 1px solid #f0f1f5;
  border-bottom: 1px solid #f0f1f5;
  padding: 4px 4px 2px;
  cursor: pointer;
  overflow: hidden;
  min-width: 0;
}
.mv-cell:nth-child(7n) { border-right: none; }
.mv-cell:hover { background: #fafbfd; }
.mv-cell.today { background: rgba(64, 158, 255, 0.04); }

.cell-head { display: flex; align-items: center; margin-bottom: 3px; }
/* 农历/节假日（设置-日期与时间）：号数右侧小字 */
.cell-hd {
  font-size: 10px; margin-left: 4px; flex-shrink: 0;
}
.cell-hd.rest { color: #34a853; }
.cell-hd.work { color: #e65d4f; }
.cell-lunar {
  margin-left: auto; font-size: 10px; color: var(--ss-text-muted);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.cell-lunar.fest { color: var(--ss-text, #303133); }
.mv-cell.today .cell-lunar, .mv-cell.today .cell-hd { opacity: 0.9; }
.cell-day {
  width: 22px; height: 22px; line-height: 22px;
  text-align: center; font-size: 13px; font-weight: 500;
  border-radius: 50%;
}
.mv-cell.other-month .cell-day { color: var(--ss-text-muted); opacity: 0.6; font-weight: 400; }
.mv-cell.today .cell-day { color: #fff; background: var(--ss-primary); font-weight: 600; }

/* ===== 任务条：与主流待办应用一致的柔和色块（色板同 TimeGrid/列表页优先级） ===== */
.task-chip {
  display: flex; align-items: center; gap: 5px;
  font-size: 12px; line-height: 20px;
  padding: 0 6px; margin-bottom: 2px;
  border-radius: 5px; cursor: pointer;
  min-width: 0;
}
.task-chip:hover { box-shadow: 0 1px 4px rgba(0, 0, 0, 0.12); }
.chip-check {
  width: 9px; height: 9px; flex-shrink: 0;
  border: 1.5px solid currentColor; border-radius: 2.5px; opacity: 0.65;
}
.chip-title {
  flex: 1; min-width: 0;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.chip-time { font-size: 11px; opacity: 0.7; flex-shrink: 0; }

.task-chip.p0 { background: #eef0f4; color: #5f6570; }
.task-chip.p1 { background: #e6f0fd; color: #2f6fd0; }
.task-chip.p2 { background: #fbf0db; color: #b5781f; }
.task-chip.p3 { background: #fde5e5; color: #cf4444; }
.task-chip.done { opacity: 0.5; }
.task-chip.done .chip-title { text-decoration: line-through; }

.more-chip { font-size: 11px; color: var(--ss-text-muted); padding-left: 4px; }

/* ===== 专注指示：任务条下方小字 🍅 N分钟（克制灰橙） ===== */
.focus-hint {
  font-size: 11px;
  line-height: 18px;
  color: #c26a1b;
  padding-left: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
