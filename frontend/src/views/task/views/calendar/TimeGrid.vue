<template>
  <div class="time-grid">
    <div class="tg-header">
      <div class="tg-gutter" />
      <div
        v-for="d in days"
        :key="d.format('YYYY-MM-DD')"
        class="tg-day-head"
        :class="{ today: d.isSame(dayjs(), 'day') }"
      >
        <div class="tg-dow">{{ d.format('ddd') }}</div>
        <div class="tg-date">{{ d.format('D') }}</div>
      </div>
    </div>

    <!-- 全天任务条（清单应用风格：时间轴上方的横条区域） -->
    <div v-if="hasAllDay" class="tg-allday">
      <div class="tg-gutter"><span class="tg-allday-label">全天</span></div>
      <div v-for="d in days" :key="d.format('YYYY-MM-DD')" class="tg-allday-cell">
        <div
          v-for="t in allDayOf(d)"
          :key="t.id"
          class="tg-chip"
          :class="[`p${t.priority || 0}`, { done: t.status === 'done' }]"
          @click="$emit('open', t)"
        >{{ t.title }}</div>
      </div>
    </div>

    <div class="tg-body">
      <div class="tg-gutter">
        <div v-for="h in HOURS" :key="h" class="tg-hour"><span>{{ hourLabel(h) }}</span></div>
      </div>
      <div
        v-for="d in days"
        :key="d.format('YYYY-MM-DD')"
        class="tg-col"
        :class="{ today: d.isSame(dayjs(), 'day') }"
        @dragover.prevent
        @drop="onDrop($event, d)"
      >
        <div v-for="h in HOURS" :key="h" class="tg-slot" @click="$emit('create', d, h)" />
        <div
          v-for="b in timedBlocks(d)"
          :key="b.id"
          class="tg-block"
          :class="[b.type === 'focus' ? 'tg-focus' : `p${b.priority || 0}`, { done: b.type !== 'focus' && b.status === 'done' }]"
          :style="blockStyle(b)"
          :title="b.type === 'focus' ? focusTitle(b) : undefined"
          :draggable="b.type !== 'focus'"
          @dragstart="onDragStart($event, b)"
          @click="b.type !== 'focus' && $emit('open', b)"
        >
          <div v-if="b.type === 'focus'" class="tg-block-head">
            <span class="tg-focus-icon">🍅</span>
            <span class="tg-block-title">{{ b.focusMinutes }}分钟</span>
          </div>
          <template v-else>
            <div class="tg-block-head">
              <span class="tg-check" />
              <span class="tg-block-title">{{ b.title }}</span>
            </div>
            <div v-if="b.duration >= 45" class="tg-block-time">{{ timeRange(b) }}</div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import dayjs from 'dayjs'

const props = defineProps({
  days: { type: Array, required: true },   // dayjs 数组
  tasks: { type: Array, default: () => [] },
  focusSessions: { type: Array, default: () => [] },  // 已完成专注会话（日历容器按可视区间拉取）
})
const emit = defineEmits(['open', 'create', 'reschedule'])

const HOUR_PX = 48
const HOURS = Array.from({ length: 24 }, (_, i) => i)

const hourLabel = (h) => `${String(h).padStart(2, '0')}:00`

function toBlock(t) {
  const base = t.start_at || t.due_at
  if (!base) return null
  const s = dayjs(base)
  const startMin = s.hour() * 60 + s.minute()
  const duration = t.duration_minutes || 60
  return { ...t, startMin, duration }
}

// 全天任务：进入顶部横条，不占时间轴
const allDayOf = (d) =>
  (props.tasks || []).filter((t) => t.all_day && dayjs(t.due_at).isSame(d, 'day'))

const hasAllDay = computed(() => props.days.some((d) => allDayOf(d).length))

// 专注会话 → 时间块：started_at 定位；ended_at 缺失时用 started_at + actual_seconds 推算
function toFocusBlock(f) {
  if (!f.started_at) return null
  const s = dayjs(f.started_at)
  const e = f.ended_at ? dayjs(f.ended_at) : s.add(f.actual_seconds || 0, 'second')
  const startMin = s.hour() * 60 + s.minute()
  const duration = Math.max(1, Math.round(e.diff(s, 'minute', true)))
  return {
    ...f,
    id: `focus-${f.id}`,
    type: 'focus',
    startMin,
    duration,
    focusMinutes: Math.max(1, Math.round((f.actual_seconds || duration * 60) / 60)),
  }
}

// 定时任务块：按开始时间排序后做「车道分配」，重叠任务并排显示
function timedBlocks(d) {
  const taskBlocks = (props.tasks || [])
    .filter((t) => !t.all_day)
    .map(toBlock)
    .filter((b) => b && dayjs(b.start_at || b.due_at).isSame(d, 'day'))
  const focusBlocks = (props.focusSessions || [])
    .map(toFocusBlock)
    .filter((b) => b && dayjs(b.started_at).isSame(d, 'day'))
  const blocks = [...taskBlocks, ...focusBlocks].sort((a, b) => a.startMin - b.startMin)
  const lanes = [] // 每个车道最后占用到的分钟
  for (const b of blocks) {
    let lane = lanes.findIndex((end) => end <= b.startMin)
    if (lane === -1) {
      lanes.push(0)
      lane = lanes.length - 1
    }
    lanes[lane] = b.startMin + b.duration
    b.lane = lane
  }
  const laneCount = Math.max(lanes.length, 1)
  blocks.forEach((b) => { b.laneCount = laneCount })
  return blocks
}

function blockStyle(b) {
  const w = 100 / b.laneCount
  return {
    top: `${(b.startMin / 60) * HOUR_PX}px`,
    height: `${Math.max((b.duration / 60) * HOUR_PX, 22)}px`,
    left: `calc(${b.lane * w}% + 2px)`,
    width: `calc(${w}% - 4px)`,
  }
}

function timeRange(b) {
  const fmt = (m) => `${String(Math.floor(m / 60) % 24).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`
  return `${fmt(b.startMin)}-${fmt(b.startMin + b.duration)}`
}

// 专注块悬浮提示：专注 HH:MM-HH:MM · N 分钟
function focusTitle(b) {
  return `专注 ${timeRange(b)} · ${b.focusMinutes} 分钟`
}

function onDragStart(e, b) {
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', String(b.id))
}

// 落点按 30min 吸附，emit 给容器走 store.rescheduleTask
function onDrop(e, d) {
  const rect = e.currentTarget.getBoundingClientRect()
  const raw = ((e.clientY - rect.top) / HOUR_PX) * 60
  const minute = Math.min(Math.max(Math.round(raw / 30) * 30, 0), 1410)
  const task = props.tasks.find((t) => String(t.id) === e.dataTransfer.getData('text/plain'))
  if (task) emit('reschedule', task, d, minute)
}
</script>

<style scoped>
.time-grid { height: 100%; overflow: auto; background: #fff; }

/* ===== 头部：星期 + 日期，今天高亮 ===== */
.tg-header {
  display: flex;
  position: sticky; top: 0; background: #fff; z-index: 2;
  border-bottom: 1px solid var(--ss-border);
}
.tg-gutter { width: 56px; flex-shrink: 0; }
.tg-day-head { flex: 1; text-align: center; padding: 6px 0 8px; }
.tg-day-head .tg-dow { font-size: 12px; color: var(--ss-text-muted); margin-bottom: 2px; }
.tg-day-head .tg-date {
  width: 26px; height: 26px; line-height: 26px; margin: 0 auto;
  font-size: 15px; font-weight: 600; border-radius: 50%;
}
.tg-day-head.today .tg-dow { color: var(--ss-primary); }
.tg-day-head.today .tg-date { color: #fff; background: var(--ss-primary); }

/* ===== 全天任务条 ===== */
.tg-allday {
  display: flex; align-items: stretch;
  border-bottom: 1px solid var(--ss-border);
  background: #fff;
}
.tg-allday .tg-gutter { display: flex; align-items: center; justify-content: flex-end; }
.tg-allday-label { font-size: 11px; color: var(--ss-text-muted); padding-right: 8px; }
.tg-allday-cell {
  flex: 1; min-height: 28px; padding: 3px 4px;
  display: flex; flex-wrap: wrap; gap: 4px; align-content: flex-start;
  border-left: 1px solid #f0f1f5;
}
.tg-chip {
  font-size: 12px; line-height: 20px; padding: 0 8px;
  border-radius: 5px; cursor: pointer;
  max-width: 100%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.tg-chip.done { opacity: 0.55; text-decoration: line-through; }

/* ===== 时间轴主体 ===== */
.tg-body { display: flex; }
.tg-hour { height: 48px; position: relative; }
.tg-hour span {
  position: absolute; top: 0; right: 8px; transform: translateY(-50%);
  font-size: 11px; color: var(--ss-text-muted);
}
.tg-col { flex: 1; position: relative; border-left: 1px solid #f0f1f5; }
.tg-col.today { background: rgba(64, 158, 255, 0.03); }
.tg-slot { height: 48px; border-bottom: 1px solid #f4f5f8; cursor: pointer; }
.tg-slot:hover { background: var(--ss-primary-light); }

/* ===== 任务块：清单应用风格柔和色块（按优先级配色，与列表页 priority-bar 同色板） ===== */
.tg-block {
  position: absolute;
  border-radius: 6px; padding: 3px 8px;
  font-size: 12px; cursor: pointer; overflow: hidden;
  transition: box-shadow 0.15s;
}
.tg-block:hover { box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12); z-index: 1; }
.tg-block-head { display: flex; align-items: center; gap: 5px; min-width: 0; }
.tg-check {
  width: 10px; height: 10px; flex-shrink: 0;
  border: 1.5px solid currentColor; border-radius: 3px; opacity: 0.7;
}
.tg-block-title {
  font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.tg-block-time { font-size: 11px; opacity: 0.75; margin-top: 1px; padding-left: 15px; }
.tg-block.done { opacity: 0.55; }
.tg-block.done .tg-block-title { text-decoration: line-through; }

.tg-block.p0, .tg-chip.p0 { background: #eef0f4; color: #5f6570; }
.tg-block.p1, .tg-chip.p1 { background: #e6f0fd; color: #2f6fd0; }
.tg-block.p2, .tg-chip.p2 { background: #fbf0db; color: #b5781f; }
.tg-block.p3, .tg-chip.p3 { background: #fde5e5; color: #cf4444; }

/* ===== 专注块：克制的番茄橙半透明，与任务块 p0-p3 蓝绿/红色系区分 ===== */
.tg-block.tg-focus {
  background: rgba(242, 132, 75, 0.16);
  color: #c05a1e;
  border-left: 3px solid #ef8a4c;
  cursor: default;
}
.tg-block.tg-focus .tg-focus-icon { font-size: 11px; flex-shrink: 0; }
.tg-block.tg-focus .tg-block-title { font-weight: 500; }
</style>
