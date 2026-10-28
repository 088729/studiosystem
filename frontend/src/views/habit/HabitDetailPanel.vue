<template>
  <!-- 习惯详情面板（对齐主流待办应用：今天视图点习惯行 → 常驻右栏）：统计卡 + 月历打卡 + 打卡日志 -->
  <aside v-if="habit" class="habit-detail-panel">
    <!-- 头部：色圆图标 + 名称 | 「...」功能菜单（对齐主流待办应用）+ 关闭 -->
    <div class="hd-header">
      <span class="hd-icon" :style="{ background: habit.color }"><img :src="habitIcon" class="hd-icon-img" alt="" /></span>
      <span class="hd-name">{{ habit.name }}</span>
      <span class="hd-more-wrap">
        <MoreHorizontal :size="18" class="hd-more" title="更多" @click.stop="menuOpen = !menuOpen" />
        <!-- 「...」菜单：编辑 / 开始专注› / 打卡样式› / 归档 / 删除 -->
        <div v-if="menuOpen" class="hd-menu" @click.stop>
          <div v-if="canEdit" class="hdm-item" @click="onEdit"><SquarePen :size="14" class="hdm-icon" />编辑</div>
          <div class="hdm-item hdm-sub-trigger" @mouseenter="sub = 'focus'" @mouseleave="sub = null">
            <CircleDot :size="14" class="hdm-icon" />开始专注
            <ChevronRight :size="13" class="hdm-arrow" />
            <div v-if="sub === 'focus'" class="hdm-sub">
              <div class="hdm-item" @click="onFocus('pomodoro')">开始番茄专注</div>
              <div class="hdm-item" @click="onFocus('stopwatch')">开始正计时</div>
            </div>
          </div>
          <div v-if="canEdit" class="hdm-item hdm-sub-trigger" @mouseenter="sub = 'style'" @mouseleave="sub = null">
            <CheckSquare :size="14" class="hdm-icon" />打卡样式
            <ChevronRight :size="13" class="hdm-arrow" />
            <div v-if="sub === 'style'" class="hdm-sub">
              <div class="hdm-item" @click="setStyle('check')">
                对勾<Check v-if="(habit.checkin_style || 'check') === 'check'" :size="14" class="hdm-check" />
              </div>
              <div class="hdm-item" @click="setStyle('icon')">
                习惯图标<Check v-if="habit.checkin_style === 'icon'" :size="14" class="hdm-check" />
              </div>
            </div>
          </div>
          <div v-if="canEdit" class="hdm-item" @click="onArchive"><Archive :size="14" class="hdm-icon" />归档</div>
          <div v-if="canDelete" class="hdm-item danger" @click="onDelete"><Trash2 :size="14" class="hdm-icon" />删除</div>
        </div>
      </span>
      <X :size="16" class="hd-close" title="关闭" @click="store.closeHabit()" />
    </div>

    <!-- 统计卡 2x2：月打卡 / 总打卡 / 月完成率 / 当前连续 -->
    <div class="hd-stats">
      <div class="hd-stat">
        <span class="hd-stat-label"><CheckCircle2 :size="14" color="#22c55e" />月打卡</span>
        <span class="hd-stat-value">{{ monthDays }}<em>天</em></span>
      </div>
      <div class="hd-stat">
        <span class="hd-stat-label"><Zap :size="14" color="#3b82f6" />总打卡</span>
        <span class="hd-stat-value">{{ totalDays }}<em>天</em></span>
      </div>
      <div class="hd-stat">
        <span class="hd-stat-label"><Percent :size="14" color="#f59e0b" />月完成率</span>
        <span class="hd-stat-value">{{ monthRate }}<em>%</em></span>
      </div>
      <div class="hd-stat">
        <span class="hd-stat-label"><Flame :size="14" color="#ef4444" />当前连续</span>
        <span class="hd-stat-value">{{ habit.streak || 0 }}<em>天</em></span>
      </div>
    </div>

    <!-- 月历：号数 + 下方打卡圆点；已达标蓝底✓，点过往日期可补卡/取消 -->
    <div class="hd-cal">
      <div class="hd-cal-head">
        <ChevronLeft :size="16" class="hd-nav" @click="shiftMonth(-1)" />
        <span class="hd-cal-title">{{ cursor.year() }}年{{ cursor.month() + 1 }}月</span>
        <ChevronRight :size="16" class="hd-nav" @click="shiftMonth(1)" />
      </div>
      <div class="hd-week">
        <span v-for="w in ['周日', '周一', '周二', '周三', '周四', '周五', '周六']" :key="w">{{ w }}</span>
      </div>
      <div class="hd-grid">
        <div v-for="cell in cells" :key="cell.key" class="hd-day" :class="{ dim: !cell.inMonth }">
          <span class="hd-day-num" :class="{ today: cell.isToday }">{{ cell.date.date() }}</span>
          <span
            class="hd-day-dot"
            :class="{ checked: cell.checked, skipped: cell.skipped, clickable: cell.clickable }"
            :title="cell.skipped ? '已跳过（点击取消跳过）' : ''"
            @click="cell.clickable && store.toggleDate(habit.id, cell.dateStr)"
          >
            <img v-if="cell.checked && habit.checkin_style === 'icon'" :src="habitIcon" class="hd-day-dot-icon" alt="" />
            <Check v-else-if="cell.checked" :size="12" />
            <Minus v-else-if="cell.skipped" :size="12" />
          </span>
        </div>
      </div>
    </div>

    <!-- 打卡日志：当前月份，空态文案对齐主流待办应用 -->
    <div class="hd-logs">
      <div class="hd-logs-title">{{ cursor.month() + 1 }}月打卡日志</div>
      <div v-if="!monthLogs.length" class="hd-logs-empty">这个月没有写打卡日志哦</div>
      <div v-for="log in monthLogs" :key="log.id" class="hd-log-row">
        <span class="hd-log-date">{{ log.date }}</span>
        <span v-if="log.mood" class="hd-log-mood"><img :src="moodImg(log.mood)" :alt="'心情' + log.mood" /></span>
        <span class="hd-log-note">{{ log.skipped ? '已跳过' : log.note || `打卡${log.count > 1 ? ` ×${log.count}` : ''}` }}</span>
      </div>
    </div>
  </aside>
  <!-- 编辑习惯对话框（共享组件） -->
  <HabitEditDialog ref="editDialog" />
</template>

<script setup>
import { computed, ref, watch, onBeforeUnmount } from 'vue'
import dayjs from 'dayjs'
import { ElMessage, ElMessageBox } from 'element-plus'
import { X, Check, ChevronLeft, ChevronRight, CheckCircle2, Zap, Percent, Flame, Minus, MoreHorizontal, SquarePen, CircleDot, CheckSquare, Archive, Trash2 } from 'lucide-vue-next'
import { useHabitStore } from '@/stores/habit'
import { useAuthStore } from '@/stores/auth'
import { usePomodoroStore } from '@/stores/pomodoro'
import HabitEditDialog from './HabitEditDialog.vue'
import { habitIconOf } from '@/utils/habitIcons'

const store = useHabitStore()
const authStore = useAuthStore()
const pomodoroStore = usePomodoroStore()
const canEdit = computed(() => authStore.hasPerm('task:edit'))
const canDelete = computed(() => authStore.hasPerm('task:delete'))
const habit = computed(() => store.habits.find((h) => h.id === store.activeHabitId))
// 习惯图标（对齐主流待办应用：habit.icon key → Noto 图标）
const habitIcon = computed(() => habitIconOf(habit.value?.icon))

// ---------- 头部「...」功能菜单（对齐主流待办应用） ----------
const menuOpen = ref(false)
const sub = ref(null)
const editDialog = ref(null)

function closeMenu() {
  menuOpen.value = false
  sub.value = null
}
const onDocClick = () => closeMenu()
watch(menuOpen, (v) => {
  if (v) document.addEventListener('click', onDocClick, true)
  else document.removeEventListener('click', onDocClick, true)
})
onBeforeUnmount(() => document.removeEventListener('click', onDocClick, true))

function onEdit() {
  closeMenu()
  editDialog.value?.open(habit.value)
}

async function onFocus(kind) {
  closeMenu()
  try {
    if (kind === 'pomodoro') {
      const { value } = await ElMessageBox.prompt('专注时长（分钟），常用 15 / 25 / 45', '开始番茄专注', {
        inputValue: '25',
        inputPattern: /^\d+$/,
        inputErrorMessage: '请输入数字分钟数',
      })
      const minutes = +value
      if (!minutes) return
      pomodoroStore.mode = 'countdown'
      await pomodoroStore.start(null, minutes)
    } else {
      pomodoroStore.mode = 'stopwatch'
      await pomodoroStore.start(null, 0)
    }
    pomodoroStore.openPanel()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error(e?.response?.data?.detail?.message || '开始失败')
  }
}

async function setStyle(style) {
  closeMenu()
  await store.update(habit.value.id, { checkin_style: style })
}

async function onArchive() {
  closeMenu()
  const name = habit.value?.name
  try {
    await ElMessageBox.confirm('习惯会从主视图中隐藏，但不会被删除，可在「已归档」中随时恢复。', `归档「${name}」`, { type: 'warning', confirmButtonText: '归档', cancelButtonText: '取消' })
  } catch {
    return // 用户取消
  }
  await store.update(habit.value.id, { is_archived: true })
  store.closeHabit()
  ElMessage.success(`「${name}」已归档`)
}

async function onDelete() {
  closeMenu()
  const name = habit.value?.name
  try {
    await ElMessageBox.confirm('习惯将被永久移除，所有打卡记录也会被清空，无法恢复。', `删除「${name}」`, { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' })
  } catch {
    return // 用户取消
  }
  await store.remove(habit.value.id)
  store.closeHabit()
}

// 月历游标：切习惯时回到当月
const cursor = ref(dayjs())
watch(
  () => store.activeHabitId,
  () => { cursor.value = dayjs() }
)

// date → log 映射；达标口径与后端一致：count >= target_per_day
const dayMap = computed(() => {
  const m = {}
  for (const l of store.activeLogs) m[l.date] = l
  return m
})
const isDoneDay = (dateStr) => (dayMap.value[dateStr]?.count || 0) >= (habit.value?.target_per_day || 1)

// 周日开头 6x7 网格；仅当月、不晚于今天、不早于 start_date 的日期可点
const cells = computed(() => {
  const first = cursor.value.startOf('month')
  const start = first.subtract(first.day(), 'day')
  const today = dayjs().startOf('day')
  const startDate = habit.value?.start_date || null
  return Array.from({ length: 42 }, (_, i) => {
    const d = start.add(i, 'day')
    const dateStr = d.format('YYYY-MM-DD')
    const inMonth = d.isSame(cursor.value, 'month')
    return {
      key: dateStr,
      date: d,
      dateStr,
      inMonth,
      isToday: d.isSame(today, 'day'),
      checked: inMonth && isDoneDay(dateStr),
      skipped: inMonth && !!dayMap.value[dateStr]?.skipped && !isDoneDay(dateStr),
      clickable: inMonth && !d.isAfter(today, 'day') && (!startDate || dateStr >= startDate),
    }
  })
})

function shiftMonth(delta) {
  cursor.value = cursor.value.add(delta, 'month')
}

// 统计：月打卡天数 / 总打卡天数 / 月完成率（当月=打卡天数÷今天号数，历史月=÷当月总天数）
const monthDays = computed(() => cells.value.filter((c) => c.checked).length)
const totalDays = computed(
  () => store.activeLogs.filter((l) => (l.count || 0) >= (habit.value?.target_per_day || 1)).length
)
const monthRate = computed(() => {
  const isCur = cursor.value.isSame(dayjs(), 'month')
  const denom = isCur ? dayjs().date() : cursor.value.daysInMonth()
  return denom ? Math.round((monthDays.value / denom) * 100) : 0
})

const monthLogs = computed(() =>
  store.activeLogs.filter((l) => dayjs(l.date).isSame(cursor.value, 'month'))
)

// 心情 1~5 → Noto Color Emoji SVG（与记录日志弹窗一致）
import mood1 from '@/assets/moods/mood1.svg'
import mood2 from '@/assets/moods/mood2.svg'
import mood3 from '@/assets/moods/mood3.svg'
import mood4 from '@/assets/moods/mood4.svg'
import mood5 from '@/assets/moods/mood5.svg'
const MOOD_IMGS = [mood1, mood2, mood3, mood4, mood5]
const moodImg = (m) => MOOD_IMGS[m - 1] || ''
</script>

<style scoped>
.habit-detail-panel {
  width: 35%;
  min-width: 420px;
  flex-shrink: 0;
  height: 100%;
  overflow-y: auto;
  background: #fff;
  border-left: 1px solid var(--ss-border);
  padding: 16px 24px;
}
.hd-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 16px;
}
.hd-icon-img {
  width: 17px;
  height: 17px;
  display: block;
}
.hd-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.hd-name {
  font-size: 17px;
  font-weight: 600;
  color: var(--ss-text);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hd-close {
  color: var(--ss-text-muted);
  cursor: pointer;
  flex-shrink: 0;
}
.hd-close:hover {
  color: var(--ss-text);
}
/* 头部「...」功能菜单（对齐主流待办应用） */
.hd-more-wrap {
  position: relative;
  flex-shrink: 0;
  display: flex;
}
.hd-more {
  color: var(--ss-text-muted);
  cursor: pointer;
  border-radius: 4px;
}
.hd-more:hover {
  color: var(--ss-text);
}
.hd-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 132px;
  background: #fff;
  border: 1px solid var(--ss-border);
  border-radius: 8px;
  box-shadow: 0 6px 24px rgb(0 0 0 / 12%);
  padding: 4px;
  z-index: 20;
}
.hdm-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  font-size: 13px;
  color: var(--ss-text);
  border-radius: 5px;
  cursor: pointer;
  white-space: nowrap;
}
.hdm-item:hover {
  background: var(--ss-bg);
}
.hdm-item.danger {
  color: #ef4444;
}
.hdm-item.danger .hdm-icon {
  color: #ef4444;
}
.hdm-icon {
  color: var(--ss-text-muted);
  flex-shrink: 0;
}
.hdm-arrow {
  margin-left: auto;
  color: var(--ss-text-muted);
}
.hdm-check {
  margin-left: auto;
  color: var(--ss-primary);
}
/* 子菜单向左展开（面板在屏幕右侧，对齐主流待办应用） */
.hdm-sub {
  position: absolute;
  right: 100%;
  top: -5px;
  margin-right: 2px;
  min-width: 118px;
  background: #fff;
  border: 1px solid var(--ss-border);
  border-radius: 8px;
  box-shadow: 0 6px 24px rgb(0 0 0 / 12%);
  padding: 4px;
}
/* 统计卡 2x2 */
.hd-stats {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 20px;
}
.hd-stat {
  background: var(--ss-bg);
  border-radius: 8px;
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.hd-stat-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--ss-text-muted);
}
.hd-stat-value {
  font-size: 22px;
  font-weight: 700;
  color: var(--ss-text);
}
.hd-stat-value em {
  font-style: normal;
  font-size: 12px;
  font-weight: 400;
  color: var(--ss-text-muted);
  margin-left: 2px;
}
/* 月历 */
.hd-cal {
  margin-bottom: 20px;
}
.hd-cal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.hd-cal-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ss-text);
}
.hd-nav {
  color: var(--ss-text-muted);
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
}
.hd-nav:hover {
  background: var(--ss-bg);
  color: var(--ss-primary);
}
.hd-week {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  text-align: center;
  font-size: 12px;
  color: var(--ss-text-muted);
  margin-bottom: 4px;
}
.hd-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
}
.hd-day {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 5px 0;
}
.hd-day.dim .hd-day-num {
  color: var(--ss-border);
}
.hd-day-num {
  font-size: 12px;
  color: var(--ss-text);
  line-height: 1;
}
.hd-day-num.today {
  color: var(--ss-primary);
  font-weight: 600;
}
.hd-day-dot {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--ss-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
}
.hd-day-dot.checked {
  background: var(--ss-primary);
}
/* 打卡样式=习惯图标：蓝圈内嵌笑脸（对齐主流待办应用） */
.hd-day-dot-icon {
  width: 14px;
  height: 14px;
  display: block;
}
.hd-day-dot.skipped {
  background: var(--ss-border);
  color: #fff;
}
.hd-day-dot.clickable {
  cursor: pointer;
}
.hd-day-dot.clickable:hover:not(.checked) {
  background: var(--ss-border);
}
/* 打卡日志 */
.hd-logs-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--ss-text);
  margin-bottom: 8px;
}
.hd-logs-empty {
  font-size: 13px;
  color: var(--ss-text-muted);
}
.hd-log-row {
  display: flex;
  gap: 12px;
  padding: 6px 0;
  border-bottom: 1px solid var(--ss-border);
  font-size: 13px;
}
.hd-log-date {
  color: var(--ss-text-muted);
  flex-shrink: 0;
}
.hd-log-note {
  color: var(--ss-text);
  word-break: break-word;
}
.hd-log-mood {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}
.hd-log-mood img {
  width: 16px;
  height: 16px;
}
</style>
