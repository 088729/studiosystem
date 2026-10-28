<template>
  <div class="task-manager">
    <TaskListSidebar class="task-sidebar" />

    <section class="task-main">
      <template v-if="store.isCalendar">
        <TaskCalendarView />
      </template>
      <template v-else-if="store.isStats">
        <header class="task-main-header">
          <h2 class="task-title">{{ store.activeTitle }}</h2>
        </header>
        <div class="task-content stats-content">
          <TaskStats />
        </div>
      </template>
      <template v-else-if="store.isHabits">
        <div class="task-content habits-content">
          <HabitManager />
        </div>
      </template>
      <template v-else-if="store.isSummary">
        <header class="task-main-header">
          <h2 class="task-title">{{ store.activeTitle }}</h2>
        </header>
        <div class="task-content summary-content">
          <SummaryView />
        </div>
      </template>
      <!-- 番茄专注：内容页（对齐主流待办应用：侧栏进入整页专注，中央计时 + 右侧概览/笔记/记录） -->
      <template v-else-if="store.isFocus">
        <header class="task-main-header">
          <h2 class="task-title">{{ store.activeTitle }}</h2>
        </header>
        <div class="task-content focus-content">
          <PomodoroPanel />
        </div>
      </template>
      <!-- 常用专注：独立内容页（对齐主流待办应用桌面端：从专注主页点进去的单独一页，左侧列表 + 右侧详情卡） -->
      <template v-else-if="store.isFocusPresets">
        <header class="task-main-header">
          <h2 class="task-title">{{ store.activeTitle }}</h2>
        </header>
        <div class="task-content focus-content">
          <FocusPresetsView />
        </div>
      </template>
      <!-- 四象限：独立内容页（对齐主流待办应用桌面端：整页 2×2 卡片，无清单头部/快速添加/详情栏） -->
      <template v-else-if="store.isQuadrant">
        <header class="task-main-header">
          <h2 class="task-title">{{ store.activeTitle }}</h2>
        </header>
        <div class="task-content quadrant-content">
          <TaskQuadrantView />
        </div>
      </template>
      <template v-else>
        <header class="task-main-header">
          <h2 class="task-title">{{ store.activeTitle }}</h2>
          <div class="header-actions">
            <!-- 排序（对齐主流待办应用标题行 ⇅ 图标）：分组/排序/顺序行，右侧显示当前值，悬停展开子菜单 -->
            <el-dropdown
              ref="sortDropdown"
              trigger="click"
              placement="bottom-end"
              popper-class="sort-menu-popper"
              @visible-change="(v) => { if (v) sortSub = '' }"
            >
              <button class="hdr-icon sort-btn" :class="{ active: store.sortActive }" title="排序">
                <ArrowUpDown :size="17" />
              </button>
              <template #dropdown>
                <div class="sm-panel">
                  <div class="sm-row sm-row-group" @mouseenter="sortSub = 'group'">
                    <LayoutList :size="15" class="sm-icon" />
                    <span class="sm-label">分组</span>
                    <span class="sm-val">{{ store.sortGroupLabel }}<ChevronRight :size="13" /></span>
                    <div v-if="sortSub === 'group'" class="sm-sub">
                      <div
                        v-for="o in store.groupOptions"
                        :key="o.value"
                        class="sm-opt"
                        @click="pickSort('group', o.value)"
                      >
                        <Check v-if="store.effectiveGroup === o.value" :size="14" class="sm-check" />
                        <span v-else class="sm-check-blank" />{{ o.label }}
                      </div>
                    </div>
                  </div>
                  <div class="sm-row sm-row-sort" @mouseenter="sortSub = 'sort'">
                    <ListOrdered :size="15" class="sm-icon" />
                    <span class="sm-label">排序</span>
                    <span class="sm-val">{{ store.sortByLabel }}<ChevronRight :size="13" /></span>
                    <div v-if="sortSub === 'sort'" class="sm-sub">
                      <div
                        v-for="o in store.SORT_OPTIONS"
                        :key="o.value"
                        class="sm-opt"
                        @click="pickSort('sort', o.value)"
                      >
                        <Check v-if="store.sortCfg.by === o.value" :size="14" class="sm-check" />
                        <span v-else class="sm-check-blank" />{{ o.label }}
                      </div>
                    </div>
                  </div>
                  <div v-if="store.sortCfg.by !== 'default'" class="sm-row sm-row-order" @mouseenter="sortSub = 'order'">
                    <ArrowUpDown :size="15" class="sm-icon" />
                    <span class="sm-label">顺序</span>
                    <span class="sm-val">{{ store.sortOrderLabel }}<ChevronRight :size="13" /></span>
                    <div v-if="sortSub === 'order'" class="sm-sub">
                      <div
                        v-for="o in store.orderOptions"
                        :key="o.value"
                        class="sm-opt"
                        @click="pickSort('order', o.value)"
                      >
                        <Check v-if="store.sortCfg.order === o.value" :size="14" class="sm-check" />
                        <span v-else class="sm-check-blank" />{{ o.label }}
                      </div>
                    </div>
                  </div>
                </div>
              </template>
            </el-dropdown>

            <!-- 更多（对齐主流待办应用标题行 ⋯）：视图图标切换（列表/看板；四象限入口在侧栏） -->
            <el-dropdown ref="viewDropdown" trigger="click" placement="bottom-end">
              <button class="hdr-icon view-btn" title="更多"><MoreHorizontal :size="17" /></button>
              <template #dropdown>
                <div class="vm-panel">
                  <div class="vm-title">视图</div>
                  <div class="vm-icons">
                    <button
                      class="vm-icon"
                      :class="{ active: store.viewMode === 'list' }"
                      title="列表"
                      @click="pickView('list')"
                    ><List :size="18" /></button>
                    <!-- 看板视图：所有任务视图均支持；列维度跟随 ⇅ 分组（对齐主流待办应用） -->
                    <button
                      class="vm-icon"
                      :class="{ active: store.viewMode === 'board' }"
                      title="看板"
                      @click="pickView('board')"
                    ><SquareKanban :size="18" /></button>
                    <!-- 时间线视图：除今天/明天/最近7天外均支持（对齐主流待办应用：这三个智能清单置灰不可进） -->
                    <button
                      class="vm-icon"
                      :class="{ active: store.viewMode === 'timeline', disabled: store.timelineDisabled }"
                      :title="store.timelineDisabled ? '该清单不支持时间线' : '时间线'"
                      @click="pickView('timeline')"
                    ><ChartGantt :size="18" /></button>
                    <!-- 四象限：独立内容页入口（对齐主流待办应用桌面端：整页卡片，点这里直接跳转） -->
                    <button
                      class="vm-icon"
                      :class="{ active: store.isQuadrant }"
                      title="四象限"
                      @click="store.selectList('quadrant')"
                    ><LayoutGrid :size="18" /></button>
                  </div>
                  <!-- 看板视图下追加分组管理入口（仅自定义清单分组看板；对齐主流待办应用看板「+ 添加分组」） -->
                  <div v-if="store.viewMode === 'board' && store.activeListKey.startsWith('list:')" class="vm-row" @click="addBoardGroup">
                    <Plus :size="15" class="vm-row-icon" />
                    <span>添加分组</span>
                  </div>
                  <!-- 开关行（对齐主流待办应用 ⋯ 菜单）：隐藏已完成，按视图记忆 -->
                  <div class="vm-row" @click="toggleHideDone">
                    <component :is="store.hideDone ? CheckSquare : Square" :size="15" class="vm-row-icon" />
                    <span>隐藏已完成</span>
                  </div>
                  <!-- 显示详细：任务行追加描述预览（对齐主流待办应用 ⋯「显示详细」） -->
                  <div class="vm-row" @click="store.toggleShowDetail()">
                    <component :is="store.showDetail ? CheckSquare : Square" :size="15" class="vm-row-icon" />
                    <span>显示详细</span>
                  </div>
                  <!-- 显示检查事项：子任务行内默认展开（对齐主流待办应用 ⋯「显示检查事项」） -->
                  <div class="vm-row" @click="store.toggleShowSubtasks()">
                    <component :is="store.showSubtasks ? CheckSquare : Square" :size="15" class="vm-row-icon" />
                    <span>显示检查事项</span>
                  </div>
                  <!-- 显示设置：打开任务设置窗口（对齐主流待办应用 ⋯「显示设置」齿轮） -->
                  <div class="vm-row" @click="openShowSettings">
                    <Settings2 :size="15" class="vm-row-icon" />
                    <span>显示设置</span>
                  </div>
                  <!-- 打印：打印当前清单任务列表（对齐主流待办应用 ⋯「打印」） -->
                  <div class="vm-row" @click="printList">
                    <Printer :size="15" class="vm-row-icon" />
                    <span>打印</span>
                  </div>
                </div>
              </template>
            </el-dropdown>
          </div>
        </header>

        <div class="summary-bar">
          <el-tag size="small" type="primary" effect="plain">今日待办 {{ store.summary.today_todo }}</el-tag>
          <el-tag size="small" type="danger" effect="plain">逾期 {{ store.summary.overdue }}</el-tag>
          <el-tag size="small" type="success" effect="plain">已完成 {{ store.summary.completed_total }}</el-tag>
        </div>

        <!-- 时间线视图隐藏顶部添加栏（对齐主流待办应用：时间线内点空白按日期添加） -->
        <TaskQuickAdd v-if="store.viewMode !== 'timeline'" />

        <div v-loading="store.loading" class="task-content">
          <TaskListView v-if="store.viewMode === 'list'" />
          <TaskTimelineView v-else-if="store.viewMode === 'timeline'" />
          <TaskBoardView v-else ref="boardViewRef" />
        </div>
      </template>
    </section>

    <!-- 看板视图：详情为居中悬浮卡片（对齐主流待办应用），遮罩点击关闭 -->
    <div
      v-if="store.viewMode === 'board' && store.activeTaskId"
      class="board-detail-mask"
      @click="store.closeDetail()"
    />
    <!-- 有选择时右栏原位替换为批量面板（同一个框，对齐主流待办应用桌面端）；否则详情栏（时间线/专注内容页无详情页） -->
    <TaskBatchPanel v-if="store.selectedIds.length" />
    <TaskDetailDrawer v-else-if="store.viewMode !== 'timeline' && !store.isFocus && !store.isFocusPresets && !store.isQuadrant" />
    <!-- 习惯详情面板：今天视图点习惯行弹出；习惯打卡页自带详情区，不再重复渲染 -->
    <HabitDetailPanel v-if="!store.isHabits" />
    <TaskSettingsDialog />
    <TaskMoveDialog />
    <!-- Mini 模式小浮窗（对齐主流待办应用 ⋯ 菜单：跨页面悬浮的专注小窗） -->
    <FocusMiniWindow />
    <!-- 沉浸模式全屏覆盖层（⋯ 菜单进入，全局单例） -->
    <FocusImmersive v-if="pomodoroStore.immersiveOpen" @close="pomodoroStore.setImmersive(false)" />
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import { ArrowUpDown, MoreHorizontal, LayoutList, ListOrdered, Check, ChevronRight, List, SquareKanban, Square, CheckSquare, ChartGantt, Plus, LayoutGrid, Settings2, Printer } from 'lucide-vue-next'
import { useTaskStore } from '@/stores/task'
import { usePomodoroStore } from '@/stores/pomodoro'
import { useHabitStore } from '@/stores/habit'
import TaskListSidebar from './TaskListSidebar.vue'
import TaskQuickAdd from './TaskQuickAdd.vue'
import TaskListView from './views/TaskListView.vue'
import TaskBoardView from './views/TaskBoardView.vue'
import TaskQuadrantView from './views/TaskQuadrantView.vue'
import TaskTimelineView from './views/TaskTimelineView.vue'
import TaskCalendarView from './views/TaskCalendarView.vue'
import TaskStats from './TaskStats.vue'
import SummaryView from './views/SummaryView.vue'
import HabitManager from '@/views/habit/HabitManager.vue'
import HabitDetailPanel from '@/views/habit/HabitDetailPanel.vue'
import TaskDetailDrawer from './TaskDetailDrawer.vue'
import TaskBatchPanel from './TaskBatchPanel.vue'
import PomodoroPanel from './PomodoroPanel.vue'
import FocusPresetsView from './views/FocusPresetsView.vue'
import FocusMiniWindow from './FocusMiniWindow.vue'
import FocusImmersive from './FocusImmersive.vue'
import TaskSettingsDialog from './dialogs/TaskSettingsDialog.vue'
import TaskMoveDialog from './dialogs/TaskMoveDialog.vue'

const store = useTaskStore()
const pomodoroStore = usePomodoroStore()
const habitStore = useHabitStore()
const boardViewRef = ref(null)

// 标题行 ⇅ 排序菜单：悬停展开哪个子菜单（group/sort/order）；点选后关菜单
const sortDropdown = ref(null)
const viewDropdown = ref(null)
const sortSub = ref('')
function pickSort(kind, value) {
  if (kind === 'group') store.setSortGroup(value)
  else if (kind === 'sort') store.setSortBy(value)
  else store.setSortOrder(value)
  sortDropdown.value?.handleClose()
}
function pickView(mode) {
  if (mode === 'timeline' && store.timelineDisabled) return // 今天/最近7天不支持时间线（对齐主流待办应用）
  store.viewMode = mode
  // 看板详情为居中悬浮卡片、时间线详情为任务条旁的迷你卡片：切入这两种视图时先收起列表视图自动打开的详情
  if (mode === 'board' || mode === 'timeline') store.closeDetail()
  viewDropdown.value?.handleClose()
}

// ⋯ 菜单「添加分组」：弹输入框后走 store（与看板尾部虚线列同一入口）
async function addBoardGroup() {
  viewDropdown.value?.handleClose()
  boardViewRef.value?.addGroup()
}
// 隐藏已完成开关行：切换但不关菜单（对齐主流待办应用开关行行为）
function toggleHideDone() {
  store.toggleHideDone()
}

// 显示设置：打开任务设置窗口（对齐主流待办应用 ⋯ 齿轮）
function openShowSettings() {
  store.settingsVisible = true
}

// 打印当前清单任务列表（对齐主流待办应用 ⋯「打印」）：body 加 printing 类 → 打印样式只留主区 → window.print
function printList() {
  document.body.classList.add('printing-list')
  const cleanup = () => {
    document.body.classList.remove('printing-list')
    window.removeEventListener('afterprint', cleanup)
  }
  window.addEventListener('afterprint', cleanup)
  window.print()
  // 部分浏览器 afterprint 不触发，兜底异步移除
  setTimeout(cleanup, 3000)
}

// 习惯详情面板与任务详情互斥：打开任务详情 / 切换清单时收起习惯面板
watch(
  () => store.activeTaskId,
  (id) => { if (id) habitStore.closeHabit() }
)
watch(
  () => store.activeListKey,
  () => habitStore.closeHabit()
)

onMounted(async () => {
  await store.fetchLists()
  await store.fetchTasks()
  await store.fetchSummary()
  store.fetchSettings()
})

// 看板 = 当前清单的分组显示方式，与列表同取当前清单数据；日历自行按月取数
watch(
  () => store.viewMode,
  () => store.fetchTasks()
)

// 任务数据变化后刷新统计
watch(
  () => store.tasks,
  () => store.fetchSummary()
)
</script>

<style>
/* 非 scoped：排序菜单悬停子菜单会向左飞出 panel，需关掉 el-dropdown 内部 scrollbar 两层的裁剪 */
.sort-menu-popper .el-scrollbar,
.sort-menu-popper .el-scrollbar__wrap {
  overflow: visible;
}
</style>

<style scoped>
.task-manager {
  display: flex;
  height: 100%;
  overflow: hidden;
  position: relative;
}
/* 看板详情悬浮卡片的透明遮罩（拦截看板点击，点击关闭详情） */
.board-detail-mask {
  position: absolute;
  inset: 0;
  z-index: 30;
}
.task-sidebar {
  width: 240px;
  flex-shrink: 0;
  border-right: 1px solid var(--ss-border);
  background: #fff;
}
.task-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  padding: 16px 24px;
  overflow: hidden;
  background: #fff; /* 列表区白底（对齐主流待办应用扁平行样式）；看板列/四象限格自带灰底不受影响 */
}
.task-main-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.header-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}
/* 标题行图标按钮（对齐主流待办应用 💡⇅⋯ 纯图标样式） */
.hdr-icon {
  border: none;
  background: none;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  color: var(--ss-text-secondary);
  display: inline-flex;
  align-items: center;
}
.hdr-icon:hover {
  background: var(--ss-bg);
  color: var(--ss-text);
}
.hdr-icon.active {
  color: var(--ss-primary);
}
/* ⇅ 排序菜单：分组/排序/顺序行 + 悬停子菜单（左向展开，对齐主流待办应用） */
.sm-panel {
  padding: 6px;
  min-width: 190px;
}
.sm-row {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  color: var(--ss-text);
}
.sm-row:hover {
  background: var(--ss-bg);
}
.sm-icon {
  color: var(--ss-text-secondary);
  flex-shrink: 0;
}
.sm-label {
  flex: 1;
}
.sm-val {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  font-size: 13px;
  color: var(--ss-text-muted);
}
.sm-sub {
  position: absolute;
  right: 100%;
  top: -6px;
  margin-right: 2px;
  background: #fff;
  border: 1px solid var(--ss-border);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  padding: 6px;
  min-width: 130px;
  z-index: 10;
}
.sm-opt {
  display: flex;
  align-items: center;
  padding: 7px 10px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  white-space: nowrap;
}
.sm-opt:hover {
  background: var(--ss-bg);
}
.sm-check {
  color: var(--ss-primary);
  margin-right: 6px;
}
.sm-check-blank {
  display: inline-block;
  width: 14px;
  margin-right: 6px;
}
/* ⋯ 更多菜单：视图图标切换 */
.vm-panel {
  padding: 10px 12px 12px;
}
.vm-title {
  font-size: 12px;
  color: var(--ss-text-muted);
  margin-bottom: 8px;
}
.vm-icons {
  display: flex;
  gap: 10px;
}
.vm-icon {
  border: none;
  background: none;
  cursor: pointer;
  padding: 8px;
  border-radius: 8px;
  color: var(--ss-text-secondary);
  display: inline-flex;
}
.vm-icon:hover {
  background: var(--ss-bg);
}
.vm-icon.active {
  color: var(--ss-primary);
  background: var(--ss-primary-light);
}
.vm-icon.disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
.vm-icon.disabled:hover {
  background: none;
}
.vm-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 6px;
  margin-top: 6px;
  border-top: 1px solid var(--ss-border);
  padding-top: 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  color: var(--ss-text);
}
.vm-row:hover {
  background: var(--ss-bg);
}
.vm-row-icon {
  color: var(--ss-text-secondary);
  flex-shrink: 0;
}
.task-title {
  font-size: 18px;
  font-weight: 600;
}
.summary-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
.task-content {
  flex: 1;
  overflow-y: auto;
  margin-top: 12px;
}
/* 番茄专注内容页：整页双栏，内部各自滚动（对齐主流待办应用专注页） */
.focus-content {
  overflow: hidden;
  min-height: 0;
}
/* 四象限内容页：整页 2×2 卡片，内部各自滚动 */
.quadrant-content {
  overflow: hidden;
  min-height: 0;
  margin-top: 0;
}
.stats-content {
  margin-top: 0;
}
.habits-content {
  margin-top: 0;
}
</style>
