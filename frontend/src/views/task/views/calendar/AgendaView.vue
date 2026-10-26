<template>
  <div class="agenda">
    <div v-for="d in daysWithTasks" :key="d.format('YYYY-MM-DD')" class="agenda-card">
      <div class="agenda-head" :class="{ today: d.isSame(dayjs(), 'day') }">
        <span class="agenda-date">{{ d.format('MM月DD日') }}</span>
        <span class="agenda-dow">{{ d.format('ddd') }}</span>
        <span v-if="d.isSame(dayjs(), 'day')" class="agenda-today-tag">今天</span>
        <span class="agenda-count">{{ tasksOf(d).length }} 项</span>
      </div>
      <div
        v-for="t in tasksOf(d)"
        :key="t.id"
        class="agenda-item"
        :class="[`p${t.priority || 0}`, { done: t.status === 'done' }]"
        @click="$emit('open', t)"
      >
        <span class="item-check" />
        <span class="item-title">{{ t.title }}</span>
        <span class="item-time">{{ timeOf(t) }}</span>
      </div>
    </div>
    <el-empty v-if="!daysWithTasks.length" description="该月暂无任务" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import dayjs from 'dayjs'

const props = defineProps({ tasks: Array, cursor: Object })
defineEmits(['open'])

const days = computed(() => {
  const start = props.cursor.startOf('month')
  return Array.from({ length: props.cursor.daysInMonth() }, (_, i) => start.add(i, 'day'))
})

const tasksOf = (d) => (props.tasks || [])
  .filter((t) => dayjs(t.due_at).isSame(d, 'day'))
  .sort((a, b) => new Date(a.start_at || a.due_at) - new Date(b.start_at || b.due_at))

// 只展示有任务的日期，避免整月空日期刷屏
const daysWithTasks = computed(() => days.value.filter((d) => tasksOf(d).length))

const timeOf = (t) => {
  if (t.all_day) return '全天'
  const base = t.start_at || t.due_at
  return base ? dayjs(base).format('HH:mm') : ''
}
</script>

<style scoped>
.agenda {
  height: 100%;
  overflow: auto;
  padding: 4px 2px 16px;
}

/* ===== 每天一张白色卡片 ===== */
.agenda-card {
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 1px 3px rgba(15, 23, 42, 0.05);
  padding: 10px 12px 8px;
  margin-bottom: 12px;
}

.agenda-head {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding-bottom: 8px;
}
.agenda-date { font-size: 15px; font-weight: 600; }
.agenda-dow { font-size: 12px; color: var(--ss-text-muted); }
.agenda-head.today .agenda-date,
.agenda-head.today .agenda-dow { color: var(--ss-primary); }
.agenda-today-tag {
  font-size: 11px; color: #fff; background: var(--ss-primary);
  border-radius: 4px; padding: 1px 6px;
}
.agenda-count {
  margin-left: auto;
  font-size: 11px; color: var(--ss-text-muted);
}

/* ===== 任务条目：与月视图/时间轴同色系柔和色块 ===== */
.agenda-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  margin-bottom: 6px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: box-shadow 0.15s, transform 0.15s;
}
.agenda-item:hover {
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.1);
  transform: translateX(2px);
}
.item-check {
  width: 11px; height: 11px; flex-shrink: 0;
  border: 1.5px solid currentColor; border-radius: 3.5px; opacity: 0.65;
}
.item-title {
  flex: 1; min-width: 0; font-weight: 500;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.item-time { font-size: 12px; opacity: 0.7; flex-shrink: 0; }

.agenda-item.p0 { background: #eef0f4; color: #5f6570; }
.agenda-item.p1 { background: #e6f0fd; color: #2f6fd0; }
.agenda-item.p2 { background: #fbf0db; color: #b5781f; }
.agenda-item.p3 { background: #fde5e5; color: #cf4444; }
.agenda-item.done { opacity: 0.5; }
.agenda-item.done .item-title { text-decoration: line-through; }
</style>
