<template>
  <!-- 番茄专注内容页（对齐主流待办应用窗口版 112812：模式切换顶栏居中 + ＋/🔊/⋯ + 中央圆环 + 右栏概览/日期分组记录 + 底部迷你专注条） -->
  <div ref="panelEl" class="pomodoro-panel">
    <FocusStatsView v-if="statsOpen" @close="statsOpen = false" />
    <template v-else>
    <div class="pomodoro-main">
      <!-- 中：计时区 -->
      <section class="timer-area">
        <!-- 顶栏（对齐主流待办应用：模式切换居中，右侧 ＋ 常用专注 / 白噪音 / ⋯） -->
        <div class="mode-bar">
          <span class="mb-spacer"></span>
          <el-radio-group v-model="store.mode" size="small" :disabled="store.isRunning">
            <el-radio-button value="countdown">番茄计时</el-radio-button>
            <el-radio-button value="stopwatch">正计时</el-radio-button>
          </el-radio-group>
          <div class="mode-tools">
            <!-- 常用专注（对齐主流待办应用：点击进入独立一页 FocusPresetsView） -->
            <el-tooltip content="常用专注" placement="top">
              <span class="mode-icon-btn preset-pop-btn" @click="taskStore.selectList('focus-presets')">
                <Plus :size="16" />
              </span>
            </el-tooltip>
            <!-- 白噪音（对齐主流待办应用：圆形图标宫格弹层） -->
            <el-popover placement="bottom-end" :width="252" trigger="click">
              <template #reference>
                <span class="mode-icon-btn" :class="{ active: store.ambient !== 'none' }">
                  <Volume2 v-if="store.ambient !== 'none'" :size="15" />
                  <VolumeX v-else :size="15" />
                </span>
              </template>
              <div class="ambient-grid">
                <div
                  v-for="t in store.AMBIENT_TYPES"
                  :key="t.key"
                  class="ambient-cell"
                  :class="{ on: store.ambient === t.key }"
                  @click="store.setAmbient(t.key)"
                >
                  <span class="ambient-icon" :class="{ playing: store.ambient === t.key && store.ambientPlaying && t.key !== 'none' }">{{ t.icon }}</span>
                  <span class="ambient-name">{{ t.name }}</span>
                </div>
              </div>
            </el-popover>
            <!-- ⋯：沉浸模式 / Mini 模式 / 专注统计 / 专注设置（对齐主流待办应用菜单） -->
            <el-dropdown trigger="click" @command="onMoreCmd">
              <span class="mode-icon-btn"><MoreVertical :size="15" /></span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="immersive"><span class="menu-ico">⛶</span>沉浸模式</el-dropdown-item>
                  <el-dropdown-item command="mini"><span class="menu-ico">▣</span>Mini 模式</el-dropdown-item>
                  <el-dropdown-item command="stats"><span class="menu-ico">◷</span>统计</el-dropdown-item>
                  <el-dropdown-item command="settings"><span class="menu-ico">☰</span>专注设置</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>

        <!-- 休息中 -->
        <template v-if="store.phase === 'rest'">
          <div class="rest-view">
            <div class="rest-emoji">☕</div>
            <div class="rest-title">休息一下</div>
            <div class="rest-time">{{ store.restText }}</div>
            <div class="rest-actions">
              <el-button round @click="onSkipRest">跳过休息</el-button>
              <el-button round @click="store.dismissEnded()">退出</el-button>
            </div>
          </div>
        </template>

        <!-- 结束页：你刚收获了一个番茄（对齐主流待办应用） -->
        <template v-else-if="store.lastEnded">
          <div class="ended-view">
            <div class="ended-tomato">🍅</div>
            <div class="ended-title">
              {{ store.lastEnded.session.status === 'completed' ? '你刚收获了一个番茄' : '本次专注已结束' }}
            </div>
            <div class="ended-sub">休息 {{ store.focusConfig.short_break_minutes }} 分钟吧</div>
            <!-- 额外时间：点 dashed 徽章计入记录 -->
            <div
              class="extra-badge"
              :class="{ clickable: store.lastEnded.extra > 0 }"
              :title="store.lastEnded.extra > 0 ? '点击将额外时间计入记录' : ''"
              @click="store.claimExtra()"
            >
              +{{ extraText }}
            </div>
            <div class="ended-actions">
              <el-button type="success" round @click="store.startRest()">开始休息</el-button>
              <el-button round @click="onSkipRest">跳过休息</el-button>
              <el-button round @click="store.dismissEnded()">退出</el-button>
            </div>
            <div class="ended-links">
              <!-- 对齐主流待办应用结束页 ⋯ 菜单：编辑专注时长 / 统计 / 专注设置 -->
              <el-dropdown trigger="click" @command="onEndedCmd">
                <span class="ended-link">⋯</span>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item command="edit">编辑专注时长</el-dropdown-item>
                    <el-dropdown-item command="stats"><span class="menu-ico">◷</span>统计</el-dropdown-item>
                    <el-dropdown-item command="settings"><span class="menu-ico">☰</span>专注设置</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              <span class="ended-link" @click="onEditDuration">编辑专注时长</span>
            </div>
          </div>
        </template>

        <!-- 计时中 / 待开始 -->
        <template v-else>
          <!-- 关联预设/任务 chip（对齐主流待办应用：点击可选任务关联到本次专注） -->
          <el-popover
            v-if="!store.isRunning"
            v-model:visible="chipPopVisible"
            placement="bottom"
            :width="300"
            trigger="click"
            popper-class="chip-popper"
            @show="onChipPopShow"
          >
            <template #reference>
              <div class="task-chip clickable" :title="chipText">
                <span v-if="chipIcon" class="chip-icon" :style="{ background: chipColor }">{{ chipIcon }}</span>
                {{ chipText }}
                <ChevronRight :size="12" />
              </div>
            </template>
            <div class="chip-picker">
              <div class="chip-picker-head">
                <span>{{ store.pendingTask ? '已关联任务' : '关联任务（可选）' }}</span>
                <span v-if="store.pendingTask" class="chip-clear" @click="clearPendingTask">清除</span>
              </div>
              <el-input v-model="chipKw" placeholder="搜索任务" size="small" clearable @input="onChipSearch" />
              <div class="chip-picker-list">
                <div v-for="t in chipCandidates" :key="t.id" class="chip-picker-item" @click="pickPendingTask(t)">
                  <span class="chip-picker-title">{{ t.title }}</span>
                  <span class="chip-picker-listname">{{ listNameOf(t.list_id) }}</span>
                </div>
                <div v-if="!chipCandidates.length" class="chip-picker-empty">{{ chipKw ? '无匹配任务' : '暂无任务' }}</div>
              </div>
            </div>
          </el-popover>
          <div v-else class="task-chip" :title="chipText">
            <span v-if="chipIcon" class="chip-icon" :style="{ background: chipColor }">{{ chipIcon }}</span>
            {{ chipText }}
            <ChevronRight v-if="chipText !== '专注'" :size="12" />
          </div>

          <div class="timer-ring" :class="{ paused: store.paused }">
            <el-progress
              type="circle"
              :percentage="store.isRunning ? store.displayProgress : 0"
              :width="ringWidth"
              :stroke-width="4"
              color="#4f6ef7"
            >
              <div class="timer-inner">
                <!-- hover 出 ± 调时（对齐主流待办应用） -->
                <div v-if="store.isRunning" class="time-adjust">
                  <span class="adj-btn" @click="store.adjust(1)">＋</span>
                  <span class="adj-btn" @click="store.adjust(-1)">－</span>
                </div>
                <span class="timer-text">{{ store.isRunning ? store.displayText : idleTimeText }}</span>
                <span v-if="store.isRunning" class="timer-range">{{ timeRangeText }}</span>
              </div>
            </el-progress>
          </div>

          <div class="timer-actions">
            <template v-if="!store.isRunning">
              <el-button type="primary" round size="large" @click="startPure">开始专注</el-button>
            </template>
            <template v-else>
              <el-button round @click="store.togglePause()">{{ store.paused ? '继续' : '暂停' }}</el-button>
              <el-button type="success" round @click="store.finish()">完成</el-button>
              <el-button round @click="store.abandon()">放弃</el-button>
            </template>
          </div>
          <div v-if="store.isRunning && store.paused" class="paused-tip">已暂停（暂停时间不计入专注时长）</div>
        </template>
      </section>

      <!-- 右：专注中/结束=时间线+笔记；空闲=概览+记录（对齐主流待办应用右栏） -->
      <aside class="side-area">
        <template v-if="store.isRunning || store.lastEnded">
          <!-- 对齐主流待办应用专注中/结束右栏：关联名 + 当日时间线迷你图 + 专注笔记 -->
          <div class="run-head">
            <span v-if="runChipIcon" class="p-icon" :style="{ background: runChipColor }">{{ runChipIcon }}</span>
            <span class="run-title">{{ runTitle }}</span>
          </div>
          <div class="side-block">
            <div class="day-timeline">
              <div class="dt-chart">
                <div
                  v-for="h in timelineHours" :key="h"
                  class="dt-row"
                >
                  <span class="dt-hour">{{ h }}</span>
                  <span class="dt-line"></span>
                </div>
                <div class="dt-block" :style="timelineBlockStyle">
                  <span class="dt-dot"></span>
                </div>
              </div>
            </div>
          </div>
          <div class="side-block">
            <div class="side-title">专注笔记</div>
            <el-input
              v-model="note"
              type="textarea"
              :rows="3"
              resize="none"
              placeholder="记录你的想法..."
              :disabled="!store.noteTargetId"
              @input="onNoteInput"
            />
          </div>
        </template>

        <template v-else>
          <div class="side-block">
            <div class="side-title panel-title">概览</div>
            <div class="stat-grid">
              <div class="stat-card">
                <span class="stat-label">今日番茄</span>
                <span class="stat-value">{{ store.stats.today_completed }}</span>
              </div>
              <div class="stat-card">
                <span class="stat-label">今日专注时长</span>
                <span class="stat-value">{{ todayParts.n }}<small v-if="todayParts.u">{{ todayParts.u }}</small></span>
              </div>
              <div class="stat-card">
                <span class="stat-label">总番茄</span>
                <span class="stat-value">{{ store.stats.total_completed }}</span>
              </div>
              <div class="stat-card">
                <span class="stat-label">总专注时长</span>
                <span class="stat-value">{{ totalParts.n }}<small v-if="totalParts.u">{{ totalParts.u }}</small></span>
              </div>
            </div>
          </div>

          <div class="side-block">
            <div class="side-title">
              专注记录
              <span class="side-head-actions">
                <span class="side-add" title="补记专注记录" @click="onAddRecord()"><Plus :size="15" /></span>
                <el-dropdown trigger="click" @command="onMoreCmd">
                  <span class="side-add"><MoreVertical :size="15" /></span>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="immersive"><span class="menu-ico">⛶</span>沉浸模式</el-dropdown-item>
                      <el-dropdown-item command="mini"><span class="menu-ico">▣</span>Mini 模式</el-dropdown-item>
                      <el-dropdown-item command="stats"><span class="menu-ico">◷</span>统计</el-dropdown-item>
                      <el-dropdown-item command="settings"><span class="menu-ico">☰</span>专注设置</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </span>
            </div>
            <el-empty v-if="!store.history.length" description="还没有专注记录" :image-size="50" />
            <div v-else class="history-list">
              <template v-for="g in historyGroups" :key="g.label">
                <div class="h-date">{{ g.label }}</div>
                <div v-for="s in g.items" :key="s.id" class="history-item">
                  <span class="h-ico" :class="s.status">
                    <svg viewBox="0 0 24 24" width="11" height="11" aria-hidden="true">
                      <path fill="#fff" d="M12 8.4c-4.1 0-7.2 2.5-7.2 5.8 0 3.4 3.1 5.9 7.2 5.9s7.2-2.5 7.2-5.9c0-3.3-3.1-5.8-7.2-5.8z" />
                      <path fill="#fff" d="M12 8.8c-.6-1.6 0-3.3 1.6-4.3.3 1.7-.4 3.3-1.6 4.3zM12 8.8c.7-1.3 2.1-2 3.7-2-.6 1.5-2 2.4-3.7 2zM12 8.8c-.8-1.3-2.2-2-3.8-2 .6 1.5 2.1 2.4 3.8 2z" />
                    </svg>
                  </span>
                  <div class="h-body">
                    <div class="h-line">
                      <span class="h-range">{{ historyRange(s) }}</span>
                      <span class="h-min" :class="s.status">{{ Math.round(s.actual_seconds / 60) }}m</span>
                    </div>
                    <div v-if="historyTitle(s)" class="h-sub">{{ historyTitle(s) }}</div>
                  </div>
                </div>
              </template>
            </div>
          </div>
        </template>
      </aside>
    </div>

    <!-- 底部迷你专注条（对齐主流待办应用：准备做什么？ + 时间 + ▶；与常用专注列表页共用） -->
    <FocusMiniBar @bar-click="onMiniBarClick" />
    </template>

    <FocusRecordDialog v-model="recordDialogVisible" :preset="recordPreset" />
    <FocusSettingsDialog v-model="settingsOpen" />
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ChevronRight, Plus, Volume2, VolumeX, MoreVertical } from 'lucide-vue-next'
import dayjs from 'dayjs'
import { fetchTasks } from '@/api/task'
import { usePomodoroStore } from '@/stores/pomodoro'
import { useTaskStore } from '@/stores/task'
import { useHabitStore } from '@/stores/habit'
import FocusRecordDialog from './dialogs/FocusRecordDialog.vue'
import FocusStatsView from './views/FocusStatsView.vue'
import FocusMiniBar from './FocusMiniBar.vue'
import FocusSettingsDialog from './dialogs/FocusSettingsDialog.vue'

const store = usePomodoroStore()
const taskStore = useTaskStore()
const habitStore = useHabitStore()
const duration = ref(25)
const statsOpen = ref(false)

function onMoreCmd(cmd) {
  if (cmd === 'immersive') store.setImmersive(true)
  if (cmd === 'mini') store.setMini(true)
  if (cmd === 'stats') statsOpen.value = true
  if (cmd === 'settings') settingsOpen.value = true
}

// 专注设置弹窗
const settingsOpen = ref(false)

// 空闲态圆环显示所选时长（对齐主流待办应用窗口版：idle 即显示 25:00）
const idleTimeText = computed(() =>
  store.mode === 'stopwatch' ? '00:00' : `${String(duration.value).padStart(2, '0')}:00`
)

// 专注记录：按日期分组（今天/昨天/M月D日/YYYY年M月D日）+ 时段 + 关联名
const historyGroups = computed(() => {
  const groups = []
  const idx = new Map()
  for (const s of store.history) {
    const d = dayjs(s.started_at).startOf('day')
    const today = dayjs().startOf('day')
    const diff = d.diff(today, 'day')
    const label = diff === 0 ? '今天' : diff === -1 ? '昨天' : d.year() === today.year() ? d.format('M月D日') : d.format('YYYY年M月D日')
    if (!idx.has(label)) {
      idx.set(label, groups.length)
      groups.push({ label, items: [] })
    }
    groups[idx.get(label)].items.push(s)
  }
  return groups
})
function historyRange(s) {
  const start = dayjs(s.started_at)
  const end = s.ended_at ? dayjs(s.ended_at) : start.add(Math.round(s.actual_seconds / 60), 'minute')
  return `${start.format('HH:mm')} - ${end.format('HH:mm')}`
}
function historyTitle(s) {
  return taskTitleOf(s.task_id) || presetNameOf(s.preset_id) || (s.habit_id ? habitNameOf(s.habit_id) : '') || (s.note ? '专注笔记' : '')
}
function habitNameOf(id) {
  return habitStore.habits.find((h) => h.id === id)?.name || ''
}

// 全屏按比例放大：以面板宽度为容器，圆环尺寸随宽度缩放（1080px 时 ≈220，与原先一致）
const panelEl = ref(null)
const panelWidth = ref(1080)
let _panelRO = null
onMounted(() => {
  // 侧栏直达不再经过 openPanel()，数据在这里兜底拉取（对齐：概览/记录/预设/习惯名）
  store.loadPresets()
  store.fetchStats()
  store.fetchHistory()
  habitStore.fetchHabits().catch(() => {})
  _panelRO = new ResizeObserver((entries) => {
    const w = entries[0]?.contentRect?.width
    if (w) panelWidth.value = w
  })
  if (panelEl.value) _panelRO.observe(panelEl.value)
})
onBeforeUnmount(() => {
  if (_panelRO) _panelRO.disconnect()
})
const ringWidth = computed(() =>
  Math.round(Math.min(340, Math.max(200, panelWidth.value * 0.204)))
)

// 结束页额外时间 MM:SS
const extraText = computed(() => {
  const e = store.lastEnded?.extra || 0
  const m = Math.floor(e / 60)
  const s = e % 60
  return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
})

const totalMinutes = computed(() => store.stats.total_minutes || 0)

// 时长拆分：数值 + 小字单位（对齐主流待办应用：25 m / 2 h）
const todayParts = computed(() => minParts(store.stats.today_minutes || 0))
const totalParts = computed(() => minParts(totalMinutes.value))
function minParts(min) {
  if (min < 60) return { n: String(min), u: 'm' }
  const h = Math.floor(min / 60)
  const m = min % 60
  return m ? { n: `${h}h${m}`, u: 'm' } : { n: String(h), u: 'h' }
}

const currentTaskTitle = computed(() =>
  store.current?.task_id ? taskTitleOf(store.current.task_id) : ''
)

// 计时区 chip：优先预设（图标+名），其次关联任务
// 计时区 chip：优先当前预设/会话任务，其次待开始的关联任务（pendingTask 在 pomodoro store，沉浸层共用）
const chipText = computed(() => {
  if (store.isRunning || store.lastEnded) {
    return store.currentPreset?.name || currentTaskTitle.value || (store.pendingTask && store.current?.task_id === store.pendingTask.id ? store.pendingTask.title : '') || '专注'
  }
  return store.currentPreset?.name || store.pendingTask?.title || '专注'
})
const chipIcon = computed(() => store.currentPreset?.icon || '')
const chipColor = computed(() => store.currentPreset?.color || '')

// chip 点击 → 选择任务关联到本次专注
const chipPopVisible = ref(false)
const chipKw = ref('')
const chipCandidates = ref([])
function onChipPopShow() {
  chipKw.value = ''
  searchChipTasks('')
}
let _chipTimer = null
function onChipSearch() {
  clearTimeout(_chipTimer)
  _chipTimer = setTimeout(() => searchChipTasks(chipKw.value), 300)
}
async function searchChipTasks(q) {
  const res = await fetchTasks({ q: q || undefined, limit: 30 }).catch(() => ({ items: [] }))
  chipCandidates.value = (res.items || []).filter((t) => !t.is_deleted && t.status !== 'done').slice(0, 30)
}
function pickPendingTask(t) {
  store.setPendingTask({ id: t.id, title: t.title })
  chipPopVisible.value = false
}
function clearPendingTask() {
  store.setPendingTask(null)
}
function listNameOf(listId) {
  if (!listId) return '收集箱'
  return taskStore.lists.find((l) => l.id === listId)?.name || ''
}

// 计时区间：开始时刻 → 预计结束
const timeRangeText = computed(() => {
  if (!store.current) return ''
  const start = dayjs(store.current.started_at)
  const end = start.add(store.current.planned_minutes, 'minute')
  return `${start.format('HH:mm')} - ${end.format('HH:mm')}`
})

// ---------- 当日时间线迷你图（对齐主流待办应用专注中/结束右栏） ----------
const runTitle = computed(() => store.currentPreset?.name || currentTaskTitle.value || '专注')
const runChipIcon = computed(() => store.currentPreset?.icon || '💪')
const runChipColor = computed(() => store.currentPreset?.color || '#f5a623')
const DT_ROW_H = 64
const timelineHours = computed(() => {
  void store.displayText // 随秒针刷新
  const s = activeSessionStart()
  if (!s) return []
  const h0 = s.hour()
  return Array.from({ length: 5 }, (_, i) => (h0 - 1 + i + 48) % 24)
})
const timelineBlockStyle = computed(() => {
  void store.displayText
  const s = activeSessionStart()
  if (!s) return { display: 'none' }
  const startTotal = s.hour() * 60 + s.minute()
  const windowStart = startTotal - 60
  const durMin = Math.max(activeSessionMinutes(), 4)
  const top = ((60 + s.minute()) / 60) * DT_ROW_H
  const height = Math.min((durMin / 60) * DT_ROW_H, 5 * DT_ROW_H - top)
  return { top: top + 'px', height: Math.max(height, 10) + 'px' }
})
function activeSessionStart() {
  if (store.isRunning && store.current?.started_at) return dayjs(store.current.started_at)
  if (store.lastEnded?.session?.started_at) return dayjs(store.lastEnded.session.started_at)
  return null
}
function activeSessionMinutes() {
  if (store.isRunning && store.current) {
    const pausedSec = store.current.paused_seconds || 0
    const endMs = store.paused && store.current.paused_at ? dayjs(store.current.paused_at).valueOf() : Date.now()
    return Math.max(1, Math.round((endMs - dayjs(store.current.started_at).valueOf()) / 60000 - pausedSec / 60))
  }
  if (store.lastEnded?.session) return Math.max(1, Math.round(store.lastEnded.session.actual_seconds / 60))
  return 1
}

function taskTitleOf(taskId) {
  if (!taskId) return ''
  const inList = taskStore.tasks.find((t) => t.id === taskId)
  if (inList) return inList.title
  if (taskStore.activeTaskDetail?.id === taskId) return taskStore.activeTaskDetail.title
  return ''
}

function presetNameOf(presetId) {
  if (!presetId) return ''
  const all = [...store.presets, ...store.presetsArchived]
  return all.find((p) => p.id === presetId)?.name || ''
}

async function startPure() {
  try {
    await store.start(store.pendingTask?.id || null, store.mode === 'stopwatch' ? 0 : duration.value)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail?.message || '开始失败')
  }
}

function onSkipRest() {
  store.endRest()
  store.dismissEnded()
}

async function onEditDuration() {
  if (!store.lastEnded) return
  try {
    const { value } = await ElMessageBox.prompt('专注时长（分钟）', '编辑专注时长', {
      inputValue: Math.round(store.lastEnded.session.actual_seconds / 60),
      inputPattern: /^\d+$/,
      inputErrorMessage: '请输入分钟数',
    })
    await store.editLastDuration(+value)
    ElMessage.success('已更新')
  } catch { /* 取消 */ }
}

// 结束页 ⋯ 菜单：编辑专注时长 / 统计 / 专注设置（对齐主流待办应用 1023a8000）
function onEndedCmd(cmd) {
  if (cmd === 'edit') return onEditDuration()
  if (cmd === 'stats') statsOpen.value = true
  if (cmd === 'settings') settingsOpen.value = true
}

// 专注笔记：绑定当前/结束会话，输入防抖保存
const note = ref('')
let _noteTimer = null
watch(
  () => store.noteTargetId,
  (id) => {
    note.value = store.current?.note ?? store.lastEnded?.session?.note ?? ''
    if (!id) note.value = ''
  },
  { immediate: true }
)
function onNoteInput() {
  clearTimeout(_noteTimer)
  _noteTimer = setTimeout(() => store.saveNote(note.value), 600)
}

// 补记专注记录（弹表单：时长/开始时间/笔记）
const recordDialogVisible = ref(false)
const recordPreset = ref(null)
function onAddRecord(preset = null) {
  recordPreset.value = preset || null
  recordDialogVisible.value = true
}

function onMiniBarClick() {
  panelEl.value?.querySelector('.timer-ring')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}
</script>

<style scoped>
/* 面板自身作宽度容器：内部尺寸用 cqw 随宽度等比缩放（1080px 时 1cqw=10.8px，与原固定值一致） */
.pomodoro-panel {
  container-type: inline-size;
  display: flex;
  flex-direction: column;
  height: 100%;
  max-width: 1600px;
  margin: 0 auto;
  padding: clamp(8px, 0.74cqw, 20px) clamp(12px, 1.11cqw, 28px);
  box-sizing: border-box;
}
.pomodoro-main {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: 0;
}
.p-icon {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: #fff;
  flex-shrink: 0;
}
/* 计时区 */
.timer-area {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: clamp(14px, 1.48cqw, 28px);
  padding-top: 4px;
  padding-right: clamp(8px, 1.11cqw, 20px);
  overflow-y: auto;
}
.mode-bar {
  width: 100%;
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
}
.mode-tools {
  display: flex;
  align-items: center;
  gap: 4px;
  justify-self: end;
}
/* 专注中/结束右栏头部（对齐主流待办应用：💪 关联名） */
.run-head {
  display: flex;
  align-items: center;
  gap: 10px;
}
.run-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--ss-text, #303133);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
/* 当日时间线迷你图（对齐主流待办应用：小时横轨 + 粉色专注块；面板内用灰底卡） */
.day-timeline {
  background: var(--ss-fill, #f7f7f9);
  border: 1px solid var(--ss-border-light, #f0f0f0);
  border-radius: 12px;
  padding: 12px 14px 12px 8px;
}
.dt-chart {
  position: relative;
  height: 320px;
}
.dt-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  height: 64px;
}
.dt-hour {
  width: 26px;
  text-align: right;
  font-size: 12px;
  color: var(--ss-text-muted, #a8abb2);
  font-variant-numeric: tabular-nums;
  transform: translateY(-6px);
}
.dt-line {
  flex: 1;
  border-top: 1px solid var(--ss-border-light, #f0f0f0);
}
.dt-block {
  position: absolute;
  left: 42px;
  right: 10px;
  background: rgba(245, 108, 108, 0.14);
  border-left: 3px solid #f56c6c;
  border-radius: 4px;
}
.dt-dot {
  position: absolute;
  left: -5px;
  top: -4px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #f56c6c;
}
.mode-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--ss-text-secondary, #909399);
}
.mode-icon-btn:hover,
.mode-icon-btn.active {
  background: var(--ss-fill, #f7f7f9);
  color: var(--el-color-primary);
}
.menu-ico {
  display: inline-block;
  width: 20px;
  color: var(--ss-text-secondary, #909399);
}
/* 白噪音宫格弹层 */
.ambient-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.ambient-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  padding: 6px 0;
  border-radius: 10px;
}
.ambient-cell:hover {
  background: var(--ss-fill, #f7f7f9);
}
.ambient-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #eef0f5;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}
.ambient-cell.on .ambient-icon {
  background: var(--el-color-primary);
  box-shadow: 0 0 0 2px #fff, 0 0 0 4px var(--el-color-primary);
}
.ambient-icon.playing {
  animation: ambPulse 1.6s infinite;
}
@keyframes ambPulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.08); }
}
.ambient-name {
  font-size: 12px;
  color: var(--ss-text-secondary, #909399);
}
.ambient-cell.on .ambient-name {
  color: var(--el-color-primary);
}
/* 严格模式菜单项 */
.strict-item {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  width: 100%;
}
.strict-tip {
  font-size: 11px;
  color: var(--ss-text-secondary, #909399);
  flex: 1;
}
.task-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: clamp(240px, 22cqw, 420px);
  padding: 3px 10px;
  font-size: clamp(13px, 1.2cqw, 17px);
  color: var(--ss-text-secondary, #909399);
  background: var(--ss-fill, #f7f7f9);
  border-radius: 999px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.task-chip.clickable {
  cursor: pointer;
}
.task-chip.clickable:hover {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
/* chip 任务选择弹层 */
.chip-picker {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.chip-picker-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: var(--ss-text-secondary, #909399);
}
.chip-clear {
  color: var(--el-color-primary);
  cursor: pointer;
}
.chip-picker-list {
  max-height: 240px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.chip-picker-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 8px;
  border-radius: 8px;
  cursor: pointer;
}
.chip-picker-item:hover {
  background: var(--ss-fill, #f7f7f9);
}
.chip-picker-title {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.chip-picker-listname {
  font-size: 12px;
  color: var(--ss-text-muted, #a8abb2);
  flex-shrink: 0;
}
.chip-picker-empty {
  padding: 20px 0;
  text-align: center;
  font-size: 12px;
  color: var(--ss-text-secondary, #909399);
}
.chip-icon {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 9px;
  color: #fff;
  flex-shrink: 0;
}
.timer-ring.paused :deep(.el-progress-circle) {
  opacity: 0.55;
}
.timer-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.timer-text {
  font-size: clamp(32px, 3.34cqw, 60px);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--ss-text, #303133);
}
.timer-range {
  font-size: clamp(11px, 1.11cqw, 16px);
  color: var(--ss-text-secondary, #909399);
  font-variant-numeric: tabular-nums;
}
/* hover ± 调时（对齐主流待办应用：悬停时间区出加减） */
.time-adjust {
  display: flex;
  gap: clamp(28px, 3.7cqw, 64px);
  font-size: clamp(15px, 1.5cqw, 24px);
  color: var(--el-color-primary);
  opacity: 0;
  transition: opacity 0.15s;
  height: 14px;
}
.timer-ring:hover .time-adjust {
  opacity: 1;
}
.adj-btn {
  cursor: pointer;
  user-select: none;
  padding: 0 6px;
}
.adj-btn:hover {
  font-weight: 700;
}
.timer-actions {
  display: flex;
  gap: 12px;
}
.paused-tip {
  font-size: 12px;
  color: var(--ss-text-secondary, #909399);
}
/* 结束页 */
.ended-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: clamp(10px, 1.11cqw, 20px);
  padding-top: clamp(20px, 2.96cqw, 56px);
}
.ended-tomato {
  font-size: clamp(60px, 6.67cqw, 128px);
  line-height: 1;
}
.ended-title {
  font-size: clamp(16px, 1.67cqw, 28px);
  font-weight: 600;
  color: var(--ss-text, #303133);
}
.ended-sub {
  font-size: clamp(12px, 1.2cqw, 18px);
  color: var(--ss-text-secondary, #909399);
}
.extra-badge {
  min-width: clamp(76px, 7cqw, 120px);
  text-align: center;
  padding: 3px 10px;
  font-size: clamp(12px, 1.2cqw, 17px);
  font-variant-numeric: tabular-nums;
  color: var(--ss-text-secondary, #909399);
  border: 1px dashed var(--ss-border, #dcdfe6);
  border-radius: 999px;
}
.extra-badge.clickable {
  color: var(--el-color-primary);
  border-color: var(--el-color-primary);
  cursor: pointer;
}
.ended-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 8px;
  width: clamp(200px, 18.5cqw, 320px);
}
.ended-actions .el-button + .el-button {
  margin-left: 0;
}
.ended-links {
  margin-top: 4px;
}
.ended-link {
  font-size: clamp(12px, 1.11cqw, 15px);
  color: var(--el-color-primary);
  cursor: pointer;
}
.ended-link:hover {
  opacity: 0.8;
}
/* 休息 */
.rest-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: clamp(8px, 0.93cqw, 18px);
  padding-top: clamp(28px, 4.44cqw, 80px);
}
.rest-emoji {
  font-size: clamp(52px, 5.2cqw, 110px);
}
.rest-title {
  font-size: clamp(15px, 1.5cqw, 22px);
  font-weight: 600;
}
.rest-time {
  font-size: clamp(34px, 3.7cqw, 72px);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  color: var(--el-color-success);
}
.rest-actions {
  display: flex;
  gap: 12px;
  margin-top: 12px;
}
/* 右：独立面板（与任务详情面板同款：35% 宽、白底、仅左边线、通高贴右边） */
.side-area {
  width: 35%;
  min-width: 420px;
  flex-shrink: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: clamp(14px, 1.67cqw, 30px);
  overflow-y: auto;
  background: #fff;
  border-left: 1px solid var(--ss-border);
  border-radius: 0;
  box-shadow: none;
  padding: clamp(14px, 1.48cqw, 24px) clamp(16px, 1.85cqw, 32px) clamp(14px, 1.5cqw, 26px);
  /* 右边缘与详情面板一样贴到内容区右边（抵消 .pomodoro-panel 的右内边距） */
  margin-right: calc(-1 * clamp(12px, 1.11cqw, 28px));
}
.side-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: clamp(14px, 1.3cqw, 19px);
  font-weight: 600;
  color: var(--ss-text, #303133);
  margin-bottom: 8px;
}
.side-title.panel-title {
  font-size: clamp(15px, 1.4cqw, 20px);
}
.side-head-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}
.side-add {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--ss-text-secondary, #909399);
  cursor: pointer;
  font-weight: 400;
}
.side-add:hover {
  color: var(--ss-text, #303133);
}
.stat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: clamp(8px, 0.74cqw, 14px);
}
.stat-card {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: clamp(10px, 0.93cqw, 16px) clamp(12px, 1.11cqw, 20px);
  background: var(--ss-fill, #f7f7f9);
  border-radius: 10px;
}
.stat-label {
  font-size: clamp(12px, 1.11cqw, 15px);
  color: var(--ss-text-secondary, #909399);
}
.stat-value {
  font-size: clamp(20px, 1.85cqw, 34px);
  font-weight: 600;
  color: var(--ss-text, #303133);
  font-variant-numeric: tabular-nums;
}
.stat-value small {
  font-size: 0.5em;
  font-weight: 600;
  margin-left: 2px;
  color: var(--ss-text-secondary, #909399);
}
.history-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.h-date {
  font-size: 12px;
  font-weight: 600;
  color: var(--ss-text-muted, #a8abb2);
  padding: 10px 0 4px;
}
.history-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: clamp(5px, 0.46cqw, 8px) 0;
  border-bottom: 1px solid var(--ss-border-light, #f0f0f0);
}
.history-item:last-child {
  border-bottom: none;
}
/* 记录行图标（对齐主流待办应用：蓝圆白番茄，放弃=灰） */
.h-ico {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #4f6ef7;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
}
.h-ico.abandoned {
  background: #c3c9d4;
}
.h-body {
  flex: 1;
  min-width: 0;
}
.h-line {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  font-size: clamp(13px, 1.2cqw, 15px);
}
.h-range {
  color: var(--ss-text, #303133);
  font-variant-numeric: tabular-nums;
}
.h-sub {
  font-size: 12px;
  color: var(--ss-text-muted, #a8abb2);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  margin-top: 2px;
}
.h-min {
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
  color: var(--ss-text-secondary, #909399);
}
.h-min.abandoned {
  color: var(--el-color-danger);
}
</style>
