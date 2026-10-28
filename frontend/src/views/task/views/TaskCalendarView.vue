<template>
  <div class="task-calendar">
    <div class="cal-toolbar">
      <span class="cal-title">{{ rangeTitle }}</span>
      <div class="cal-actions">
        <el-button-group>
          <el-button size="small" @click="shift(-1)">‹</el-button>
          <el-button size="small" @click="goToday">今天</el-button>
          <el-button size="small" @click="shift(1)">›</el-button>
        </el-button-group>
        <el-dropdown trigger="click" @command="onViewChange">
          <el-button size="small">
            {{ currentViewName }}<ChevronDown :size="14" style="margin-left: 4px; vertical-align: -2px" />
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item
                v-for="v in VIEW_MODES"
                :key="v.value"
                :command="v.value"
                :class="{ 'is-active-view': store.calendarViewMode === v.value }"
              >{{ v.label }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <div class="cal-body">
      <YearView v-if="store.calendarViewMode === 'year'" :tasks="store.calendarTasks" :cursor="store.calendarCursor" @pick="onPickMonth" />
      <MonthView v-else-if="store.calendarViewMode === 'month'" :tasks="store.calendarTasks" :focus-sessions="store.calendarFocusSessions" :cursor="store.calendarCursor" @open="onOpen" @create="onCreate" @navigate="onNavigate" @reschedule="onReschedule" />
      <WeekView v-else-if="store.calendarViewMode === 'week'" :tasks="store.calendarTasks" :focus-sessions="store.calendarFocusSessions" :cursor="store.calendarCursor" @open="onOpen" @create="onCreate" @reschedule="onReschedule" />
      <DayView v-else-if="store.calendarViewMode === 'day'" :tasks="store.calendarTasks" :focus-sessions="store.calendarFocusSessions" :cursor="store.calendarCursor" @open="onOpen" @create="onCreate" @reschedule="onReschedule" />
      <AgendaView v-else-if="store.calendarViewMode === 'agenda'" :tasks="store.calendarTasks" :cursor="store.calendarCursor" @open="onOpen" />
      <MultiDayView v-else-if="store.calendarViewMode === 'multiday'" :tasks="store.calendarTasks" :focus-sessions="store.calendarFocusSessions" :cursor="store.calendarCursor" @open="onOpen" @create="onCreate" @reschedule="onReschedule" />
      <MultiWeekView v-else :tasks="store.calendarTasks" :focus-sessions="store.calendarFocusSessions" :cursor="store.calendarCursor" @open="onOpen" @create="onCreate" @reschedule="onReschedule" />
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
import dayjs from 'dayjs'
import { useTaskStore } from '@/stores/task'
import YearView from './calendar/YearView.vue'
import MonthView from './calendar/MonthView.vue'
import WeekView from './calendar/WeekView.vue'
import DayView from './calendar/DayView.vue'
import AgendaView from './calendar/AgendaView.vue'
import MultiDayView from './calendar/MultiDayView.vue'
import MultiWeekView from './calendar/MultiWeekView.vue'

const store = useTaskStore()

// 视图切换下拉（对齐主流待办应用：年/月/周/日/日程/多日/多周视图）
const VIEW_MODES = [
  { value: 'year', label: '年视图' },
  { value: 'month', label: '月视图' },
  { value: 'week', label: '周视图' },
  { value: 'day', label: '日视图' },
  { value: 'agenda', label: '日程视图' },
  { value: 'multiday', label: '多日视图' },
  { value: 'multiweek', label: '多周视图' },
]

const currentViewName = computed(
  () => VIEW_MODES.find((v) => v.value === store.calendarViewMode)?.label || '月视图'
)

function onViewChange(v) {
  store.calendarViewMode = v
  store.fetchCalendar()
}

const rangeTitle = computed(() =>
  store.calendarViewMode === 'year'
    ? store.calendarCursor.format('YYYY年')
    : store.calendarCursor.format('YYYY年M月')
)

onMounted(() => store.fetchCalendar())

function shift(dir) {
  const unit = store.calendarViewMode === 'year' ? 'year'
    : ['month', 'agenda'].includes(store.calendarViewMode) ? 'month'
    : store.calendarViewMode === 'day' ? 'day'
    : 'week'
  store.shiftCalendar(dir, unit)
}

function goToday() { store.goCalendarToday() }

function onOpen(task) { store.openDetail(task.id) }

async function onCreate(day, hour = 9) {
  const due = dayjs(day).hour(hour).minute(0).second(0)
  // due_at 已显式指定，applyDefaults 只补默认清单/优先级
  const task = await store.createTask(store.applyDefaults({ title: '新任务', due_at: due.toISOString() }))
  store.openDetail(task.id)
}

function onNavigate(date) { store.setCalendarCursor(dayjs(date)) }

// 拖拽排期：月视图 minute=null 仅改日期；时间轴视图落到具体时段
async function onReschedule(task, day, minute = null) {
  await store.rescheduleTask(task, dayjs(day), minute)
}

function onPickMonth(m) {
  store.calendarViewMode = 'month'
  store.setCalendarCursor(m)
}
</script>

<style scoped>
.task-calendar { display: flex; flex-direction: column; height: 100%; }
.cal-toolbar {
  display: flex; align-items: center; justify-content: space-between;
  padding: 4px 0 10px;
}
.cal-title { font-size: 18px; font-weight: 600; }
.cal-actions { display: flex; align-items: center; gap: 10px; }
.is-active-view { color: var(--ss-primary); font-weight: 600; }
.cal-body { flex: 1; overflow: auto; }
</style>
