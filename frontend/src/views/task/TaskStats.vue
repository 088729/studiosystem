<template>
  <div class="stats">
    <div class="stat-cards">
      <div class="stat-card"><div class="num">{{ summary.today_todo }}</div><div class="label">今日待办</div></div>
      <div class="stat-card warn"><div class="num">{{ summary.overdue }}</div><div class="label">已逾期</div></div>
      <div class="stat-card"><div class="num">{{ summary.completed_total }}</div><div class="label">已完成</div></div>
      <div class="stat-card"><div class="num">{{ focusStats.today_minutes }}m</div><div class="label">今日专注</div></div>
    </div>

    <el-card shadow="never" class="block">
      <template #header>清单分布</template>
      <el-empty v-if="!summary.by_list.length" description="暂无待办任务" :image-size="60" />
      <div v-for="b in summary.by_list" :key="b.list_id" class="list-row">
        <span class="list-name">{{ listName(b.list_id) }}</span>
        <el-progress :percentage="pct(b.todo)" :stroke-width="10" />
        <span class="list-count">{{ b.todo }}</span>
      </div>
    </el-card>

    <el-card shadow="never" class="block">
      <template #header>习惯进度（今日 {{ habitDone }}/{{ habitActive }}）</template>
      <el-empty v-if="!activeHabits.length" description="暂无进行中的习惯" :image-size="60" />
      <template v-else>
        <el-progress :percentage="habitPct" :stroke-width="10" class="habit-progress" />
        <div v-for="h in activeHabits" :key="h.id" class="habit-row">
          <span class="color-dot" :style="{ background: h.color || 'var(--ss-primary)' }" />
          <span class="habit-name">{{ h.name }}</span>
          <span class="habit-streak"><Flame :size="13" style="vertical-align: -2px" /> {{ h.streak }}</span>
          <span class="habit-check" :class="{ done: h.today_checked }">
            {{ h.today_checked ? '已打卡' : '未打卡' }}
          </span>
        </div>
      </template>
    </el-card>

    <el-card shadow="never" class="block">
      <template #header>专注趋势（近 7 天）</template>
      <div class="focus-bars">
        <div v-for="(m, i) in focusWeek" :key="i" class="bar-col">
          <div class="bar" :style="{ height: barHeight(m) }" />
          <div class="bar-label">{{ m }}m</div>
          <div class="bar-day">{{ weekDayLabel(i) }}</div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { Flame } from 'lucide-vue-next'
import { computed, onMounted } from 'vue'
import dayjs from 'dayjs'
import { useTaskStore } from '@/stores/task'
import { usePomodoroStore } from '@/stores/pomodoro'
import { useHabitStore } from '@/stores/habit'

const store = useTaskStore()
const pomodoro = usePomodoroStore()
const habit = useHabitStore()

const summary = computed(() => store.summary)
const focusStats = computed(() => pomodoro.stats)

const listName = (id) => (id ? store.lists.find((l) => l.id === id)?.name || '已删除清单' : '收集箱')
const maxTodo = computed(() => Math.max(1, ...summary.value.by_list.map((b) => b.todo)))
const pct = (n) => Math.round((n / maxTodo.value) * 100)

// 习惯今日进度：仅统计进行中的习惯
const activeHabits = computed(() => habit.habits.filter((h) => !h.is_archived))
const habitActive = computed(() => activeHabits.value.length)
const habitDone = computed(() => activeHabits.value.filter((h) => h.today_checked).length)
const habitPct = computed(() =>
  habitActive.value ? Math.round((habitDone.value / habitActive.value) * 100) : 0
)

const focusWeek = computed(() => pomodoro.focusWeek)
const maxFocus = computed(() => Math.max(1, ...focusWeek.value))
const barHeight = (m) => `${Math.round((m / maxFocus.value) * 80)}px`
const weekDayLabel = (i) => dayjs().subtract(6 - i, 'day').format('MM-DD')

onMounted(() => {
  store.fetchSummary()
  pomodoro.fetchStats()
  pomodoro.fetchFocusWeek()
  habit.fetchHabits()
})
</script>

<style scoped>
.stats { display: flex; flex-direction: column; gap: 16px; padding-bottom: 16px; }
.stat-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; }
.stat-card { border: 1px solid var(--ss-border); border-radius: var(--ss-radius-sm); padding: 16px; text-align: center; }
.stat-card.warn .num { color: #f56c6c; }
.stat-card .num { font-size: 28px; font-weight: 700; }
.stat-card .label { color: var(--ss-text-secondary); font-size: 12px; }
.list-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.list-name { width: 100px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.list-row :deep(.el-progress) { flex: 1; }
.list-count { width: 30px; text-align: right; }
.habit-progress { margin-bottom: 12px; }
.habit-row { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid var(--ss-border); font-size: 13px; }
.habit-row:last-child { border-bottom: none; }
.color-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.habit-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.habit-streak { color: var(--ss-text-muted); font-size: 12px; }
.habit-check { font-size: 12px; color: var(--ss-text-muted); }
.habit-check.done { color: #67c23a; }
.focus-bars { display: flex; align-items: flex-end; gap: 12px; height: 120px; }
.bar-col { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; }
.bar { width: 20px; background: var(--ss-primary); border-radius: 3px 3px 0 0; }
.bar-label { font-size: 11px; color: var(--ss-text-muted); margin-top: 4px; }
.bar-day { font-size: 11px; color: var(--ss-text-muted); }
</style>
