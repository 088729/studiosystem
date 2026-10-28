<template>
  <!-- 习惯打卡（对齐主流待办应用桌面端：本周圆环条 + 分组行式列表 + 右侧详情四卡/月历打卡表/打卡日志） -->
  <div class="habit-manager">
    <header class="hm-header">
      <h2 class="hm-title">打卡</h2>
      <el-radio-group v-model="tab" size="small" class="hm-tabs">
        <el-radio-button value="active">坚持中</el-radio-button>
        <el-radio-button value="archived">已归档</el-radio-button>
      </el-radio-group>
      <div class="hm-tools">
        <el-tooltip content="新建习惯" placement="top">
          <span class="hm-icon-btn" @click="editDialog?.open(null)"><Plus :size="16" /></span>
        </el-tooltip>
        <el-dropdown trigger="click">
          <span class="hm-icon-btn"><MoreHorizontal :size="16" /></span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item>
                <span class="hm-menu-row">
                  在“今天”、“最近7天”中显示
                  <el-switch v-model="showInSmart" size="small" @click.stop />
                </span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </header>

    <div v-loading="store.loading" class="hm-main">
      <!-- 左：周环条 + 日期 + 分组列表 -->
      <aside class="hm-left">
        <div class="hm-week">
          <div
            v-for="(d, i) in weekDays"
            :key="d.date"
            class="hm-week-cell"
            :class="{ today: d.date === todayStr, future: d.date > todayStr }"
            @click="selectedDate = d.date"
          >
            <span class="hm-week-label">{{ '一二三四五六日'[i] }}</span>
            <svg class="hm-ring" viewBox="0 0 40 40">
              <circle cx="20" cy="20" r="16" fill="none" stroke="#eef0f5" stroke-width="4" />
              <circle
                cx="20" cy="20" r="16" fill="none"
                stroke="#4f6ef7" stroke-width="4"
                stroke-linecap="round"
                :stroke-dasharray="ringDash(d)"
                transform="rotate(-90 20 20)"
              />
              <text x="20" y="24" text-anchor="middle" class="hm-ring-num">{{ d.date.slice(8) }}</text>
            </svg>
          </div>
        </div>

        <div class="hm-datebar">
          <span class="hm-date-chip" :class="{ off: selectedDate !== todayStr }">
            {{ dayjs(selectedDate).format('M月D日') }}
            <span v-if="selectedDate !== todayStr" class="hm-date-x" title="回到今天" @click="selectedDate = todayStr">×</span>
          </span>
        </div>

        <div v-if="tab === 'active'" class="hm-list">
          <template v-for="g in groupedHabits" :key="g.key">
            <div class="hm-group-head" @click="toggleGroup(g.key)">
              <span class="hm-caret" :class="{ open: !collapsed.has(g.key) }">›</span>
              <span class="hm-group-name">{{ g.label }}</span>
              <span class="hm-group-count">{{ g.items.length }}</span>
            </div>
            <div v-if="!collapsed.has(g.key)" class="hm-rows">
              <div
                v-for="h in g.items"
                :key="h.id"
                class="hm-row"
                :class="{ active: store.activeHabitId === h.id }"
                @click="selectHabit(h)"
              >
                <span class="hm-dot" :style="{ background: h.color }">
                  <img :src="habitIconOf(h.icon)" class="hm-dot-icon" alt="" />
                </span>
                <div class="hm-row-mid">
                  <div class="hm-row-name">{{ h.name }}</div>
                  <div class="hm-row-meta">⚡{{ h.total_days }}天 🔥{{ h.streak }}天</div>
                </div>
                <button
                  class="hm-check"
                  :class="{ on: h.today_checked }"
                  :style="h.today_checked ? { background: h.color, borderColor: h.color } : {}"
                  :title="checkTitle(h)"
                  @click.stop="onCheck(h)"
                >
                  <Check v-if="h.today_checked" :size="13" />
                </button>
              </div>
            </div>
          </template>
          <el-empty v-if="!activeHabits.length" description="还没有习惯，点右上角 ＋ 开始" :image-size="70" />
        </div>

        <!-- 已归档 -->
        <div v-else class="hm-list">
          <div v-for="h in archivedHabits" :key="h.id" class="hm-row">
            <span class="hm-dot" :style="{ background: h.color }">
              <img :src="habitIconOf(h.icon)" class="hm-dot-icon" alt="" />
            </span>
            <div class="hm-row-mid">
              <div class="hm-row-name">{{ h.name }}</div>
              <div class="hm-row-meta">⚡{{ h.total_days }}天 🔥{{ h.streak }}天</div>
            </div>
            <el-button size="small" text type="primary" @click="store.update(h.id, { is_archived: false })">恢复</el-button>
            <el-button size="small" text type="danger" @click="onDelete(h)">删除</el-button>
          </div>
          <el-empty v-if="!archivedHabits.length" description="暂无归档" :image-size="70" />
        </div>
      </aside>

      <!-- 右：习惯详情（四卡 + 月历打卡表 + 打卡日志） -->
      <section v-if="active" class="hm-detail">
        <header class="hd-head">
          <span class="hm-dot hd-dot" :style="{ background: active.color }">
            <img :src="habitIconOf(active.icon)" class="hm-dot-icon" alt="" />
          </span>
          <span class="hd-name">{{ active.name }}</span>
          <el-dropdown trigger="click" @command="(c) => onCommand(c, active)">
            <span class="hm-icon-btn"><MoreHorizontal :size="15" /></span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit" v-if="authStore.hasPerm('task:edit')">编辑</el-dropdown-item>
                <el-dropdown-item command="focus" v-auth="'task:run'">开始专注</el-dropdown-item>
                <el-dropdown-item command="log">记录日志</el-dropdown-item>
                <el-dropdown-item command="archive" v-if="authStore.hasPerm('task:edit')">归档</el-dropdown-item>
                <el-dropdown-item command="delete" divided v-if="authStore.hasPerm('task:delete')">
                  <span style="color: #ef4444">删除</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </header>

        <div class="hd-cards">
          <div class="hd-card"><span class="hd-card-label">🥇 月打卡</span><span class="hd-card-value">{{ stats.month_checked }}<small> 天</small></span></div>
          <div class="hd-card"><span class="hd-card-label">⚡ 总打卡</span><span class="hd-card-value">{{ stats.total_days }}<small> 天</small></span></div>
          <div class="hd-card"><span class="hd-card-label">🏆 月完成率</span><span class="hd-card-value">{{ stats.month_rate }}<small> %</small></span></div>
          <div class="hd-card"><span class="hd-card-label">🔥 当前连续</span><span class="hd-card-value">{{ stats.streak }}<small> 天</small></span></div>
        </div>

        <div class="hd-month-nav">
          <span class="hd-nav-btn" @click="shiftMonth(-1)">‹</span>
          <span class="hd-month-label">{{ dayjs(monthCursor + '-01').format('YYYY年M月') }}</span>
          <span class="hd-nav-btn" @click="shiftMonth(1)">›</span>
          <span class="hd-month-sub">共打卡 {{ stats.month_checked }} 天 · 计划 {{ stats.planned_days }} 天 · 最高连续 {{ stats.best_streak }} 天</span>
        </div>

        <div class="hd-cal">
          <div class="hd-cal-head"><span v-for="w in '一二三四五六日'" :key="w">{{ w }}</span></div>
          <div class="hd-cal-grid">
            <span v-for="(cell, i) in calendarCells" :key="i" class="hd-cal-cell" :class="{ pad: !cell }">
              <template v-if="cell">
                <span
                  class="hd-day"
                  :class="cellCls(cell)"
                  :title="cell.date + (cell.count ? ` · ${cell.count} 次` : '')"
                  @click="onDayClick(cell)"
                >{{ cell.day }}</span>
              </template>
            </span>
          </div>
        </div>

        <div class="hd-logs">
          <div class="hd-logs-title">打卡日志</div>
          <div v-if="!monthLogs.length" class="hd-logs-empty">本月暂无打卡记录</div>
          <div v-for="log in monthLogs" :key="log.date" class="hd-log-row">
            <img v-if="log.mood" :src="moodImg(log.mood)" class="hd-log-mood" alt="" />
            <span class="hd-log-date">{{ dayjs(log.date).format('M月D日') }} 周{{ '日一二三四五六'[dayjs(log.date).day()] }}</span>
            <span v-if="log.skipped" class="hd-log-count">已跳过</span>
            <span v-else class="hd-log-count">✓ {{ log.count }} 次</span>
            <span v-if="log.note" class="hd-log-note">{{ log.note }}</span>
          </div>
        </div>
      </section>

      <section v-else class="hm-detail hm-detail-empty">
        <el-empty description="选择左侧习惯查看打卡统计" :image-size="90" />
      </section>
    </div>

    <HabitEditDialog ref="editDialog" />
    <HabitLogDialog ref="logDialog" />
    <HabitContextMenu ref="habitMenu" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { Plus, MoreHorizontal, Check } from 'lucide-vue-next'
import dayjs from 'dayjs'
import { useHabitStore } from '@/stores/habit'
import { useAuthStore } from '@/stores/auth'
import { usePomodoroStore } from '@/stores/pomodoro'
import HabitEditDialog from './HabitEditDialog.vue'
import HabitLogDialog from './HabitLogDialog.vue'
import HabitContextMenu from './HabitContextMenu.vue'
import { habitIconOf } from '@/utils/habitIcons'
import mood1 from '@/assets/moods/mood1.svg'
import mood2 from '@/assets/moods/mood2.svg'
import mood3 from '@/assets/moods/mood3.svg'
import mood4 from '@/assets/moods/mood4.svg'
import mood5 from '@/assets/moods/mood5.svg'

const store = useHabitStore()
const authStore = useAuthStore()
const pomoStore = usePomodoroStore()
const editDialog = ref(null)
const logDialog = ref(null)
const habitMenu = ref(null)

const tab = ref('active')
const todayStr = dayjs().format('YYYY-MM-DD')
const selectedDate = ref(todayStr)
const weekDays = ref([])
const collapsed = ref(new Set())
const monthCursor = ref(dayjs().format('YYYY-MM'))
const stats = ref({ month_checked: 0, total_days: 0, month_rate: 0, streak: 0, planned_days: 0, best_streak: 0, days: {} })
const monthLogs = ref([])

const activeHabits = computed(() => store.habits.filter((h) => !h.is_archived))
const archivedHabits = computed(() => store.habits.filter((h) => h.is_archived))
const active = computed(() => store.habits.find((h) => h.id === store.activeHabitId) || null)

const showInSmart = computed({
  get: () => store.inSmart,
  set: (v) => store.setInSmart(v),
})

const groupedHabits = computed(() => {
  const m = new Map()
  for (const h of activeHabits.value) {
    const g = h.group || '其他'
    if (!m.has(g)) m.set(g, [])
    m.get(g).push(h)
  }
  return [...m.entries()].map(([label, items]) => ({ key: 'g:' + label, label, items }))
})

function toggleGroup(key) {
  const s = new Set(collapsed.value)
  s.has(key) ? s.delete(key) : s.add(key)
  collapsed.value = s
}

function ringDash(d) {
  const total = d.total || 0
  const p = total ? d.done / total : 0
  const c = 2 * Math.PI * 16
  return `${(p * c).toFixed(1)} ${c.toFixed(1)}`
}

function checkTitle(h) {
  if (h.today_checked) return '已达标，点击取消'
  if (h.goal_type === 'amount') return `打卡（${h.today_count}/${h.target_per_day}）`
  return '打卡'
}

async function refreshWeek() {
  weekDays.value = await store.fetchWeek()
}

async function selectHabit(h) {
  await store.openHabit(h.id)
  monthCursor.value = dayjs().format('YYYY-MM')
  await loadStats()
}

async function loadStats() {
  if (!store.activeHabitId) return
  stats.value = await store.fetchStats(store.activeHabitId, monthCursor.value)
  const start = monthCursor.value + '-01'
  const end = dayjs(start).endOf('month').format('YYYY-MM-DD')
  monthLogs.value = await store.fetchLogs(store.activeHabitId, { start, end })
}

function shiftMonth(n) {
  monthCursor.value = dayjs(monthCursor.value + '-01').add(n, 'month').format('YYYY-MM')
  loadStats()
}

// 月历格子：补月首空位 + 每天 {date, day, count, done, skipped}
const calendarCells = computed(() => {
  const first = dayjs(monthCursor.value + '-01')
  const pad = (first.day() + 6) % 7
  const daysInMonth = first.daysInMonth()
  const cells = new Array(pad).fill(null)
  for (let d = 1; d <= daysInMonth; d++) {
    const date = `${monthCursor.value}-${String(d).padStart(2, '0')}`
    const info = stats.value.days?.[date] || {}
    cells.push({ date, day: d, count: info.count || 0, done: !!info.done, skipped: !!info.skipped })
  }
  return cells
})

function cellCls(cell) {
  const cls = []
  if (cell.done) cls.push('done')
  else if (cell.skipped) cls.push('skipped')
  else if (cell.date < todayStr && cell.date >= (active.value?.start_date || '0000')) cls.push('missed')
  if (cell.date > todayStr) cls.push('future')
  if (cell.date === todayStr) cls.push('today')
  return cls.join(' ')
}

// ---------- 打卡（三种方式，对齐主流待办应用） ----------
async function onCheck(h) {
  if (h.today_checked) {
    await store.uncheckin(h.id, selectedDate.value)
    ElMessage.success('已取消')
    return
  }
  const done = await doCheckin(h, selectedDate.value)
  if (done && h.auto_log) {
    await store.openHabit(h.id)
    logDialog.value?.open(h, selectedDate.value, true)
  }
}

async function doCheckin(h, date) {
  if (h.checkin_mode === 'manual') {
    let amount = 1
    try {
      const { value } = await ElMessageBox.prompt(
        `「${h.name}」本次完成量（目标 ${h.target_per_day}）`, '手动记录',
        { inputValue: '1', inputPattern: /^\d+$/, inputErrorMessage: '请输入数量' }
      )
      amount = Math.max(1, parseInt(value, 10) || 1)
    } catch { return false }
    await store.checkin(h.id, date, null, null, amount)
    ElMessage.success(`已记录 ${amount} 次`)
  } else {
    await store.checkin(h.id, date)
    ElMessage.success(`「${h.name}」打卡成功`)
  }
  await refreshWeek()
  if (store.activeHabitId === h.id) await loadStats()
  const fresh = store.habits.find((x) => x.id === h.id)
  return !!fresh?.today_checked
}

async function onDayClick(cell) {
  const h = active.value
  if (!h || cell.date > todayStr) return
  if (cell.done) {
    await store.uncheckin(h.id, cell.date)
  } else {
    const was = await doCheckin(h, cell.date)
    if (was && h.auto_log) {
      await store.openHabit(h.id)
      logDialog.value?.open(h, cell.date, true)
      return
    }
  }
  await loadStats()
}

function moodImg(m) {
  return [mood1, mood2, mood3, mood4, mood5][Math.min(5, Math.max(1, m)) - 1]
}

async function onCommand(cmd, h) {
  if (cmd === 'edit') editDialog.value?.open(h)
  else if (cmd === 'focus') {
    try {
      await pomoStore.start(null, 25)
      pomoStore.openPanel()
    } catch { /* 已有进行中会话等 */ }
  }
  else if (cmd === 'log') logDialog.value?.open(h, todayStr, false)
  else if (cmd === 'archive') {
    await store.update(h.id, { is_archived: true })
    ElMessage.success('已归档')
  } else if (cmd === 'delete') onDelete(h)
}

async function onDelete(h) {
  try {
    await ElMessageBox.confirm('习惯将被永久移除，所有打卡记录也会被清空，无法恢复。', `删除「${h.name}」`, {
      type: 'error',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch { return }
  await store.remove(h.id)
  if (store.activeHabitId === h.id) store.closeHabit()
  ElMessage.success('已删除')
  await refreshWeek()
}

// ---------- 打卡提醒（Web 端：应用打开时到点弹通知） ----------
let _remindTimer = null
function checkReminders() {
  const now = dayjs().format('HH:mm')
  const today = dayjs().format('YYYY-MM-DD')
  for (const h of activeHabits.value) {
    for (const t of h.reminders || []) {
      const key = `habit_reminded:${h.id}:${today}:${t}`
      if (t === now && !sessionStorage.getItem(key)) {
        sessionStorage.setItem(key, '1')
        ElNotification({ title: '习惯打卡提醒', message: `该「${h.name}」打卡啦 💪`, type: 'info' })
      }
    }
  }
}

onMounted(async () => {
  await store.fetchHabits(selectedDate.value)
  await refreshWeek()
  checkReminders()
  _remindTimer = setInterval(checkReminders, 30000)
})
onBeforeUnmount(() => clearInterval(_remindTimer))

// 切换日期 → 重新拉取该日达标状态
watch(selectedDate, async (d) => {
  await store.fetchHabits(d)
  await refreshWeek()
})
watch(tab, async () => {
  await store.fetchHabits(selectedDate.value)
})
</script>

<style scoped>
.habit-manager {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 4px 8px;
  box-sizing: border-box;
}
.hm-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 4px 10px;
}
.hm-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--ss-text, #303133);
}
.hm-tools {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 6px;
}
.hm-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--ss-text-secondary);
}
.hm-icon-btn:hover {
  background: var(--ss-fill, #f7f7f9);
  color: var(--el-color-primary);
}
.hm-menu-row {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  width: 100%;
}
.hm-main {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 16px;
}
/* 左列 */
.hm-left {
  width: 340px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
  border-right: 1px solid var(--ss-border-light, #f0f0f0);
  padding-right: 12px;
}
.hm-week {
  display: flex;
  justify-content: space-between;
  gap: 2px;
  padding: 2px 0 8px;
}
.hm-week-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 6px 2px;
  border-radius: 10px;
  cursor: pointer;
}
.hm-week-cell.today {
  background: #eef1fe;
}
.hm-week-cell.future {
  opacity: 0.45;
  cursor: default;
}
.hm-week-label {
  font-size: 11px;
  color: var(--ss-text-muted);
}
.hm-ring {
  width: 40px;
  height: 40px;
}
.hm-ring-num {
  font-size: 12px;
  fill: var(--ss-text);
  font-weight: 600;
}
.hm-datebar {
  padding: 0 2px 6px;
}
.hm-date-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--ss-text-muted);
  background: var(--ss-fill, #f7f7f9);
  border-radius: 999px;
  padding: 3px 10px;
}
.hm-date-chip.off {
  color: var(--el-color-primary);
  background: #eef1fe;
}
.hm-date-x {
  cursor: pointer;
  font-size: 13px;
}
.hm-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
}
.hm-group-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 4px 4px;
  cursor: pointer;
  user-select: none;
}
.hm-caret {
  color: var(--ss-text-muted);
  font-size: 12px;
  transition: transform 0.15s;
}
.hm-caret.open {
  transform: rotate(90deg);
}
.hm-group-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--ss-text);
}
.hm-group-count {
  font-size: 12px;
  color: var(--ss-text-muted);
}
.hm-rows {
  display: flex;
  flex-direction: column;
}
.hm-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px;
  border-radius: 10px;
  cursor: pointer;
  border: 1px solid transparent;
}
.hm-row:hover {
  background: var(--ss-fill, #f7f7f9);
}
.hm-row.active {
  background: #fff;
  border-color: var(--el-color-primary);
}
.hm-dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.hm-dot-icon {
  width: 18px;
  height: 18px;
}
.hm-row-mid {
  flex: 1;
  min-width: 0;
}
.hm-row-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ss-text);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.hm-row-meta {
  font-size: 12px;
  color: var(--ss-text-muted);
  font-variant-numeric: tabular-nums;
}
.hm-check {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  border: 1.5px solid #c8cdd8;
  background: #fff;
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}
/* 右详情 */
.hm-detail {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 4px 8px 16px;
}
.hd-head {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-bottom: 12px;
}
.hd-dot {
  width: 38px;
  height: 38px;
}
.hd-dot .hm-dot-icon {
  width: 22px;
  height: 22px;
}
.hd-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--ss-text);
}
.hd-head .el-dropdown {
  margin-left: auto;
}
.hd-cards {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  padding-bottom: 14px;
}
.hd-card {
  background: var(--ss-fill, #f7f7f9);
  border-radius: 12px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.hd-card-label {
  font-size: 12px;
  color: var(--ss-text-secondary);
}
.hd-card-value {
  font-size: 24px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--ss-text);
}
.hd-card-value small {
  font-size: 12px;
  font-weight: 400;
  color: var(--ss-text-muted);
}
.hd-month-nav {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--ss-text-secondary);
  font-size: 13px;
  padding-bottom: 8px;
}
.hd-nav-btn {
  cursor: pointer;
  font-size: 16px;
  padding: 0 6px;
  user-select: none;
}
.hd-nav-btn:hover {
  color: var(--el-color-primary);
}
.hd-month-label {
  font-weight: 600;
  color: var(--ss-text);
}
.hd-month-sub {
  margin-left: auto;
  font-size: 12px;
  color: var(--ss-text-muted);
}
.hd-cal-head {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  font-size: 12px;
  color: var(--ss-text-muted);
  padding-bottom: 4px;
}
.hd-cal-head span {
  text-align: center;
}
.hd-cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}
.hd-cal-cell {
  aspect-ratio: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.hd-day {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--ss-text-secondary);
  cursor: pointer;
}
.hd-day:hover {
  background: var(--ss-fill, #f7f7f9);
}
.hd-day.done {
  background: #4f6ef7;
  color: #fff;
}
.hd-day.missed {
  color: var(--el-color-danger);
  text-decoration: line-through;
}
.hd-day.future {
  color: #d3d7e0;
  cursor: default;
}
.hd-day.today {
  box-shadow: 0 0 0 2px var(--el-color-primary);
  color: var(--ss-text);
}
.hd-logs {
  margin-top: 14px;
}
.hd-logs-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--ss-text);
  padding-bottom: 6px;
}
.hd-logs-empty {
  font-size: 12px;
  color: var(--ss-text-muted);
  padding: 10px 0;
}
.hd-log-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 2px;
  border-bottom: 1px solid var(--ss-border-light, #f0f0f0);
  font-size: 13px;
}
.hd-log-mood {
  width: 20px;
  height: 20px;
}
.hd-log-date {
  font-weight: 600;
  color: var(--ss-text);
}
.hd-log-count {
  color: var(--ss-text-secondary);
  font-variant-numeric: tabular-nums;
}
.hd-log-note {
  flex: 1;
  min-width: 0;
  color: var(--ss-text-muted);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.hm-detail-empty {
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
