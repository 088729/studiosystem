<template>
  <div class="year-grid">
    <div v-for="m in months" :key="m.format('YYYY-MM')" class="year-month" @click="$emit('pick', m)">
      <div class="ym-title">{{ monthName(m) }}</div>
      <div class="ym-weekdays">
        <span v-for="w in WEEKDAYS" :key="w">{{ w }}</span>
      </div>
      <div class="ym-days">
        <span
          v-for="d in daysOf(m)"
          :key="d.format('YYYY-MM-DD')"
          class="ym-day"
          :class="cellClass(d, m)"
        >{{ d.date() }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import dayjs from 'dayjs'

const props = defineProps({ tasks: Array, cursor: Object })
defineEmits(['pick'])

const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']
const MONTH_NAMES = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月']

const months = computed(() =>
  Array.from({ length: 12 }, (_, i) => props.cursor.startOf('year').add(i, 'month'))
)

const monthName = (m) => MONTH_NAMES[m.month()]

// 每个日期的任务数（热力图数据）
const countMap = computed(() => {
  const map = {}
  for (const t of props.tasks || []) {
    const d = dayjs(t.due_at).format('YYYY-MM-DD')
    map[d] = (map[d] || 0) + 1
  }
  return map
})

// 6 行 × 7 列，从月初所在周的周日起（与月视图/主流待办应用一致）
function daysOf(month) {
  const start = month.startOf('month')
  const gridStart = start.subtract(start.day(), 'day')
  return Array.from({ length: 42 }, (_, i) => gridStart.add(i, 'day'))
}

function cellClass(d, month) {
  if (!d.isSame(month, 'month')) return 'other-month'
  if (d.isSame(dayjs(), 'day')) return 'today'
  const c = countMap.value[d.format('YYYY-MM-DD')] || 0
  if (c >= 4) return 'lv3'
  if (c >= 2) return 'lv2'
  if (c >= 1) return 'lv1'
  return ''
}
</script>

<style scoped>
.year-grid {
  height: 100%;
  overflow: auto;
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 24px 16px;
  padding: 12px 16px 24px;
  background: #fff;
}
.year-month { cursor: pointer; min-width: 0; }
.ym-title {
  font-size: 15px; font-weight: 600;
  padding: 4px 2px 10px;
}
.year-month:hover .ym-title { color: var(--ss-primary); }

.ym-weekdays {
  display: grid; grid-template-columns: repeat(7, 1fr);
  margin-bottom: 4px;
}
.ym-weekdays span {
  text-align: center; font-size: 11px; color: var(--ss-text-muted);
  padding: 2px 0;
}

.ym-days {
  display: grid; grid-template-columns: repeat(7, 1fr);
  gap: 2px;
}
.ym-day {
  aspect-ratio: 1;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; border-radius: 3px;
  color: var(--ss-text);
}
.ym-day.other-month { color: var(--ss-text-muted); opacity: 0.45; }

/* 热力：任务越多色越深 */
.ym-day.lv1 { background: #e3edfd; }
.ym-day.lv2 { background: #b9d2fb; }
.ym-day.lv3 { background: #82aef7; color: #1f3f7a; }

/* 今天：实心高亮，优先级最高 */
.ym-day.today { background: var(--ss-primary); color: #fff; font-weight: 600; }
</style>
