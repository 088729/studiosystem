<template>
  <!-- 常用专注列表视图（对齐主流待办应用窗口版 113001：番茄专注窗口内的列表+详情卡，底部迷你专注条保留） -->
  <div class="presets-page">
    <!-- 顶行：坚持中/已归档 tab 居中 + ＋新建在右（对齐主流待办应用：tab 在窗口顶部中央） -->
    <div class="pp-topbar">
      <span class="pp-spacer"></span>
      <el-radio-group v-model="presetTab" size="small">
        <el-radio-button value="active">坚持中</el-radio-button>
        <el-radio-button value="archived">已归档</el-radio-button>
      </el-radio-group>
      <div class="pp-top-tools">
        <span class="preset-add" title="新建常用专注" @click="openPresetDialog(null)">
          <Plus :size="15" />
        </span>
        <!-- ⋯：沉浸模式 / Mini 模式 / 统计 / 专注设置（对齐主流待办应用菜单） -->
        <el-dropdown trigger="click" @command="onMoreCmd">
          <span class="preset-more"><MoreVertical :size="15" /></span>
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

    <div class="pp-body">
      <!-- 左：整页宽列表 -->
      <section class="preset-list-pane">
        <div class="plp-list">
          <el-dropdown
            v-for="p in shownPresets"
            :key="p.id"
            trigger="contextmenu"
            @command="(cmd) => onPresetCommand(cmd, p)"
          >
            <div
              class="preset-row"
              :class="{ selected: selectedPresetId === p.id }"
              @click="onSelectPreset(p)"
            >
              <span class="p-icon" :style="{ background: p.color }">{{ p.icon }}</span>
              <span class="p-name">{{ p.name }}</span>
              <span class="p-total">{{ totalText(p.total_seconds) }}</span>
              <span
                class="p-play"
                :class="{ disabled: store.isRunning }"
                title="开始专注"
                @click.stop="onStartPreset(p)"
              >
                <Play :size="13" fill="currentColor" />
              </span>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit">编辑</el-dropdown-item>
                <el-dropdown-item command="record">添加记录</el-dropdown-item>
                <el-dropdown-item command="archive">{{ p.archived ? '恢复' : '归档' }}</el-dropdown-item>
                <el-dropdown-item command="delete" divided>
                  <span class="p-del">删除</span>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <div v-if="!shownPresets.length" class="preset-empty">
            {{ presetTab === 'active' ? '暂无常用专注，点右上角 ＋ 创建' : '暂无归档' }}
          </div>
        </div>
      </section>

      <!-- 右：详情卡（白底浮卡：关闭 + ⋯；图标名+模式 + 三卡 + 周日条图） -->
      <aside class="preset-detail-pane">
        <template v-if="selectedPreset">
          <div class="preset-detail">
            <div class="pd-head">
              <span class="p-icon pd-icon" :style="{ background: selectedPreset.color }">{{ selectedPreset.icon }}</span>
              <div class="pd-names">
                <div class="pd-name">{{ selectedPreset.name }}</div>
                <div class="pd-mode">
                  {{ selectedPreset.mode === 'stopwatch' ? '正计时' : `番茄计时 ${selectedPreset.duration_minutes}m` }}
                </div>
                <div v-if="presetLinkText" class="pd-link">{{ presetLinkText }}</div>
              </div>
              <div class="pd-tools">
                <el-dropdown trigger="click" @command="(cmd) => onPresetCommand(cmd, selectedPreset)">
                  <span class="pd-more"><MoreVertical :size="16" /></span>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item command="edit">编辑</el-dropdown-item>
                      <el-dropdown-item command="record">添加记录</el-dropdown-item>
                      <el-dropdown-item command="archive">{{ selectedPreset.archived ? '恢复' : '归档' }}</el-dropdown-item>
                      <el-dropdown-item command="delete" divided>
                        <span class="p-del">删除</span>
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <span class="pd-close" @click="selectedPresetId = null">关闭</span>
              </div>
            </div>
            <div class="stat-grid pd-stats">
              <div class="stat-card">
                <span class="stat-label">专注天数</span>
                <span class="stat-value">{{ presetStats.days ?? 0 }}</span>
              </div>
              <div class="stat-card">
                <span class="stat-label">今日时长</span>
                <span class="stat-value">{{ minutesText(presetStats.today_minutes) }}</span>
              </div>
              <div class="stat-card">
                <span class="stat-label">总时长</span>
                <span class="stat-value">{{ minutesText(presetStats.total_minutes) }}</span>
              </div>
            </div>
            <div class="pd-chart">
              <div class="pd-chart-top">
                <span class="pd-chart-total">{{ minutesText(presetStats.total_minutes) }}</span>
                <span class="pd-chart-unit">周</span>
              </div>
              <div class="pd-chart-nav">
                <span class="pd-nav-btn" @click="shiftWeek(-1)">‹</span>
                <span class="pd-week-label">{{ presetStats.week_label }}</span>
                <span class="pd-nav-btn" @click="shiftWeek(1)">›</span>
              </div>
              <div class="pd-chart-body">
                <div class="pd-bars">
                  <div class="pd-gridline" style="bottom: 33.33%"></div>
                  <div class="pd-gridline" style="bottom: 66.66%"></div>
                  <div v-for="(v, i) in presetStats.week_days || []" :key="i" class="pd-bar-col">
                    <div class="pd-bar" :style="{ height: barHeight(v) }" :title="`${v}m`"></div>
                    <span class="pd-bar-day">{{ '日一二三四五六'[i] }}</span>
                  </div>
                </div>
                <div class="pd-axis">
                  <span>{{ fmtTick(chartMax) }}</span>
                  <span>{{ fmtTick(Math.round((chartMax * 2) / 3)) }}</span>
                  <span>{{ fmtTick(Math.round(chartMax / 3)) }}</span>
                  <span>0m</span>
                </div>
              </div>
            </div>
          </div>
        </template>
        <div v-else class="pd-blank">点击左侧常用专注查看详情</div>
      </aside>
    </div>

    <!-- 底部迷你专注条（对齐主流待办应用：列表视图保留） -->
    <FocusMiniBar @bar-click="taskStore.selectList('focus')" />

    <FocusStatsView v-if="statsOpen" @close="statsOpen = false" />
    <FocusPresetDialog v-model="dialogVisible" :preset="editingPreset" @saved="onPresetSaved" />
    <FocusRecordDialog v-model="recordDialogVisible" :preset="recordPreset" />
    <FocusSettingsDialog v-model="settingsOpen" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Play, MoreVertical } from 'lucide-vue-next'
import dayjs from 'dayjs'
import { fetchFocusPresetStats } from '@/api/task'
import { usePomodoroStore } from '@/stores/pomodoro'
import { useTaskStore } from '@/stores/task'
import { useHabitStore } from '@/stores/habit'
import FocusPresetDialog from '../dialogs/FocusPresetDialog.vue'
import FocusRecordDialog from '../dialogs/FocusRecordDialog.vue'
import FocusSettingsDialog from '../dialogs/FocusSettingsDialog.vue'
import FocusStatsView from './FocusStatsView.vue'
import FocusMiniBar from '../FocusMiniBar.vue'

const store = usePomodoroStore()
const taskStore = useTaskStore()
const habitStore = useHabitStore()

// 详情卡关联行：任务 or 习惯（习惯完成自动打卡）
onMounted(() => {
  habitStore.fetchHabits().catch(() => {})
})
const presetLinkText = computed(() => {
  const p = selectedPreset.value
  if (!p) return ''
  if (p.task_id) {
    const t = taskStore.tasks.find((x) => x.id === p.task_id)
    return `🔗 ${t?.title || '已关联任务'}`
  }
  if (p.habit_id) {
    const h = habitStore.habits.find((x) => x.id === p.habit_id)
    return `${h?.icon || '💪'} ${h?.name || '已关联习惯'}（完成自动打卡）`
  }
  return ''
})

function minutesText(min) {
  min = Math.round(min || 0)
  if (min < 60) return `${min}m`
  return `${Math.floor(min / 60)}h${min % 60 ? `${min % 60}m` : ''}`
}
function totalText(seconds) {
  return minutesText(Math.round((seconds || 0) / 60))
}

// ---------- 列表 ----------
const presetTab = ref('active')
const selectedPresetId = ref(null)
const presetStats = ref({})
const tzOffsetMinutes = -new Date().getTimezoneOffset()

function sundayOf(d) {
  return d.subtract(d.day(), 'day').startOf('day')
}
const weekStart = ref(sundayOf(dayjs()))

const shownPresets = computed(() =>
  presetTab.value === 'active' ? store.presets : store.presetsArchived
)
const selectedPreset = computed(() => {
  const all = [...store.presets, ...store.presetsArchived]
  return all.find((p) => p.id === selectedPresetId.value) || null
})

function onSelectPreset(p) {
  selectedPresetId.value = p.id
  weekStart.value = sundayOf(dayjs())
  loadPresetStats()
}

async function loadPresetStats() {
  if (!selectedPresetId.value) return
  presetStats.value = await fetchFocusPresetStats(selectedPresetId.value, {
    tz_offset_minutes: tzOffsetMinutes,
    week_start: weekStart.value.format('YYYY-MM-DD'),
  }).catch(() => ({}))
}

function shiftWeek(n) {
  weekStart.value = weekStart.value.add(n * 7, 'day')
  loadPresetStats()
}

const chartMax = computed(() => {
  const mx = Math.max(...(presetStats.value.week_days || []), 1)
  return Math.max(60, Math.ceil(mx / 60) * 60)
})

function fmtTick(v) {
  return v >= 60 ? `${Math.round(v / 60)}h` : `${v}m`
}

function barHeight(v) {
  return `${Math.max(2, Math.min(100, Math.round((v / chartMax.value) * 100)))}%`
}

// ---------- 行命令 ----------
async function onStartPreset(p) {
  if (store.isRunning) return
  try {
    await store.startPreset(p)
    // 对齐主流待办应用：行 ▶ 启动后回专注主页计时
    taskStore.selectList('focus')
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail?.message || '开始失败')
  }
}

const dialogVisible = ref(false)
const editingPreset = ref(null)
function openPresetDialog(p) {
  editingPreset.value = p
  dialogVisible.value = true
}

const recordDialogVisible = ref(false)
const recordPreset = ref(null)
function onAddRecord(preset = null) {
  recordPreset.value = preset || null
  recordDialogVisible.value = true
}

async function onPresetCommand(cmd, p) {
  if (cmd === 'edit') {
    openPresetDialog(p)
  } else if (cmd === 'record') {
    onAddRecord(p)
  } else if (cmd === 'archive') {
    await store.savePreset({ archived: !p.archived }, p.id)
    ElMessage.success(p.archived ? '已恢复' : '已归档')
  } else if (cmd === 'delete') {
    try {
      await ElMessageBox.confirm(`删除常用专注「${p.name}」？历史专注记录会保留。`, '删除', {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      })
    } catch { return }
    await store.removePreset(p.id)
    if (selectedPresetId.value === p.id) selectedPresetId.value = null
    ElMessage.success('已删除')
  }
}

function onPresetSaved() {
  dialogVisible.value = false
  store.loadPresets()
  if (selectedPresetId.value) loadPresetStats()
}

// ⋯ 菜单：沉浸模式 / Mini 模式 / 统计 / 专注设置
const statsOpen = ref(false)
const settingsOpen = ref(false)
function onMoreCmd(cmd) {
  if (cmd === 'immersive') store.setImmersive(true)
  if (cmd === 'mini') store.setMini(true)
  if (cmd === 'stats') statsOpen.value = true
  if (cmd === 'settings') settingsOpen.value = true
}

// 完成/放弃/补记后刷新累计与详情
watch(
  () => store.stats,
  () => {
    store.loadPresets()
    if (selectedPresetId.value) loadPresetStats()
  }
)

onMounted(() => {
  store.loadPresets()
  store.fetchStats()
})
</script>

<style scoped>
.presets-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
  height: 100%;
  min-height: 0;
}
/* 顶行（对齐主流待办应用：tab 居中、＋ 在右） */
.pp-topbar {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  align-items: center;
  flex-shrink: 0;
}
.pp-top-tools {
  justify-self: end;
  display: flex;
  align-items: center;
  gap: 6px;
}
.preset-more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--ss-text-secondary, #909399);
}
.preset-more:hover {
  background: var(--ss-fill, #f7f7f9);
  color: var(--el-color-primary);
}
.preset-add {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  cursor: pointer;
  color: var(--ss-text-secondary, #909399);
}
.preset-add:hover {
  background: var(--ss-fill, #f7f7f9);
  color: var(--el-color-primary);
}
.menu-ico {
  display: inline-block;
  width: 20px;
  color: var(--ss-text-secondary, #909399);
}
.pp-body {
  flex: 1;
  min-height: 0;
  display: flex;
  gap: clamp(16px, 2cqw, 32px);
}
/* 左：列表 */
.preset-list-pane {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.plp-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 2px 0;
}
.preset-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
}
.preset-row:hover {
  background: var(--ss-fill, #f7f7f9);
}
.preset-row.selected {
  background: var(--ss-fill, #f0f0f2);
}
.p-icon {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: #fff;
  flex-shrink: 0;
}
.p-name {
  font-size: 14px;
  color: var(--ss-text, #303133);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.p-total {
  margin-left: auto;
  font-size: 12px;
  color: var(--ss-text-muted, #a8abb2);
  font-variant-numeric: tabular-nums;
}
.p-play {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--el-color-primary);
  color: #fff;
  flex-shrink: 0;
}
.p-play.disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.p-del {
  color: var(--el-color-danger);
}
.preset-empty {
  padding: 40px 0;
  text-align: center;
  font-size: 13px;
  color: var(--ss-text-secondary, #909399);
}
/* 右：详情卡（对齐主流待办应用：白底浮卡） */
.preset-detail-pane {
  width: clamp(300px, 28cqw, 400px);
  flex-shrink: 0;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.pd-blank {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: var(--ss-text-muted, #a8abb2);
}
.preset-detail {
  display: flex;
  flex-direction: column;
  gap: 16px;
  background: var(--ss-card-bg, #fff);
  border: 1px solid var(--ss-border-light, #f0f0f0);
  border-radius: 12px;
  padding: 16px;
}
.pd-head {
  display: flex;
  align-items: center;
  gap: 12px;
}
.pd-icon {
  width: 44px;
  height: 44px;
  font-size: 20px;
}
.pd-names {
  min-width: 0;
}
.pd-name {
  font-size: 17px;
  font-weight: 600;
  color: var(--ss-text, #303133);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.pd-mode {
  font-size: 12px;
  color: var(--ss-text-secondary, #909399);
  margin-top: 2px;
}
.pd-link {
  font-size: 12px;
  color: var(--ss-text-muted, #a8abb2);
  margin-top: 2px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.pd-tools {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.pd-more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--ss-text-secondary, #909399);
}
.pd-more:hover {
  background: var(--ss-fill, #f7f7f9);
  color: var(--el-color-primary);
}
.pd-close {
  font-size: 13px;
  color: var(--el-color-primary);
  cursor: pointer;
}
.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
}
.stat-card {
  background: var(--ss-fill, #f7f7f9);
  border-radius: 10px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.stat-label {
  font-size: 12px;
  color: var(--ss-text-secondary, #909399);
}
.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--ss-text, #303133);
  font-variant-numeric: tabular-nums;
}
.pd-chart {
  background: var(--ss-fill, #f7f7f9);
  border-radius: 12px;
  padding: 14px;
}
.pd-chart-top {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.pd-chart-total {
  font-size: 20px;
  font-weight: 600;
  color: var(--ss-text, #303133);
  font-variant-numeric: tabular-nums;
}
.pd-chart-unit {
  font-size: 12px;
  color: var(--ss-text-secondary, #909399);
  border: 1px solid var(--ss-border, #dcdfe6);
  border-radius: 999px;
  padding: 1px 10px;
}
.pd-chart-nav {
  display: flex;
  align-items: center;
  gap: 10px;
  margin: 8px 0 12px;
  font-size: 13px;
  color: var(--ss-text-secondary, #909399);
}
.pd-nav-btn {
  cursor: pointer;
  padding: 0 4px;
  user-select: none;
}
.pd-nav-btn:hover {
  color: var(--el-color-primary);
}
.pd-chart-body {
  display: flex;
  gap: 8px;
}
.pd-bars {
  flex: 1;
  height: 140px;
  display: flex;
  align-items: flex-end;
  gap: 6px;
  position: relative;
  border-bottom: 1px solid var(--ss-border-light, #e4e7ed);
}
.pd-gridline {
  position: absolute;
  left: 0;
  right: 0;
  border-top: 1px dashed var(--ss-border-light, #ebeef5);
}
.pd-bar-col {
  flex: 1;
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  gap: 4px;
  position: relative;
  z-index: 1;
}
.pd-bar {
  width: 60%;
  background: #4f6ef7;
  border-radius: 3px 3px 0 0;
  min-height: 2px;
}
.pd-bar-day {
  position: absolute;
  bottom: -20px;
  font-size: 11px;
  color: var(--ss-text-muted, #a8abb2);
}
.pd-axis {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  font-size: 11px;
  color: var(--ss-text-muted, #a8abb2);
  padding-bottom: 20px;
  text-align: right;
}
</style>
