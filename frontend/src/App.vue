<template>
  <div class="app-wrapper">
    <aside v-if="authStore.isLoggedIn && !route.meta.hideSidebar" class="app-sidebar" :class="{ collapsed: isCollapsed }">
      <div class="sidebar-header">
        <span class="logo">
          <span class="logo-mark">S</span>
          <span v-show="!isCollapsed" class="logo-text">Studio System</span>
        </span>
        <el-button link class="collapse-btn" @click="toggleCollapse">
          <el-icon>
            <Fold v-if="!isCollapsed" />
            <Expand v-else />
          </el-icon>
        </el-button>
      </div>
      <el-menu
        :collapse="isCollapsed"
        :default-active="activeMenu"
        class="sidebar-menu"
        router
      >
        <el-menu-item index="/case">
          <el-icon><Document /></el-icon>
          <template #title>用例管理</template>
        </el-menu-item>
        <el-menu-item index="/task" v-if="authStore.hasPerm('task:view')">
          <el-icon><Tickets /></el-icon>
          <template #title>任务管理</template>
        </el-menu-item>
        <el-menu-item index="/wiki" v-if="authStore.hasPerm('wiki:view')">
          <el-icon><Notebook /></el-icon>
          <template #title>知识库</template>
        </el-menu-item>

        <el-sub-menu v-if="authStore.hasPerm('sys:manage')" index="/platform">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>后台管理</span>
          </template>
          <el-menu-item index="/platform/admin">用户管理</el-menu-item>
        </el-sub-menu>
      </el-menu>

      <div class="sidebar-footer">
        <el-dropdown v-if="!isCollapsed" trigger="click" @command="handleUserCommand">
          <span class="user-chip">
            <span class="user-avatar">{{ avatarInitial }}</span>
            <span class="user-name">
              {{ authStore.userInfo?.username }}
              <el-icon><ArrowDown /></el-icon>
            </span>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">个人中心</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <el-button v-else link @click="logout">
          <el-icon><SwitchButton /></el-icon>
        </el-button>
      </div>
    </aside>

    <main class="app-main">
      <router-view />
    </main>

    <SearchPanel v-if="authStore.isLoggedIn" />
    <GlobalQuickAdd v-if="authStore.isLoggedIn" />

    <!-- 任务提醒弹窗队列（复刻主流待办应用网页版居中卡片） -->
    <div class="rp-stack">
      <ReminderPopup
        v-for="q in reminderQueue"
        :key="q.item.task_id"
        :item="q.item"
        @dismiss="rpDismiss(q.item)"
        @focus="rpFocus(q.item)"
        @complete="rpComplete(q.item)"
        @snooze="(m) => rpSnooze(q.item, m)"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, h, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElNotification, ElButton } from 'element-plus'
import dayjs from 'dayjs'
import { useAuthStore } from '@/stores/auth'
import { useTaskStore } from '@/stores/task'
import {
  Document,
  Tickets,
  Notebook,
  Setting,
  Fold,
  Expand,
  ArrowDown,
  SwitchButton,
} from '@element-plus/icons-vue'
import { usePomodoroStore } from '@/stores/pomodoro'
import { playReminderSound } from '@/utils/reminderSound'
import SearchPanel from '@/views/task/SearchPanel.vue'
import GlobalQuickAdd from '@/views/task/GlobalQuickAdd.vue'
import ReminderPopup from '@/views/task/ReminderPopup.vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const taskStore = useTaskStore()

// 复制链接的应用内定位：/task?open=<id> 打开时自动展开该任务（对齐主流待办应用「复制链接」）
// 注意：须等 router 初始导航完成后用 router.replace 清 query（直接 replaceState 会被初始导航写回）
onMounted(() => {
  const openId = new URLSearchParams(location.search).get('open')
  if (!openId) return
  taskStore.openDetail(openId).catch(() => {})
  router.isReady().then(() => router.replace({ query: {} })).catch(() => {})
})
const pomodoroStore = usePomodoroStore()

// 登录后恢复未结束的番茄钟
watch(
  () => authStore.isLoggedIn,
  (loggedIn) => loggedIn && pomodoroStore.restore(),
  { immediate: true }
)

// ---------- 网页提醒（设置-提醒与通知）：授权后除应用内弹窗外同时发浏览器系统通知 ----------
function fireWebNotify(title, body, tag) {
  const s = taskStore.settings
  // 显示通知详情（设置-提醒与通知）：关闭后系统通知不展示任务标题（隐私）
  const showDetail = s?.show_notification_detail !== false
  const finalBody = showDetail ? body : '你有一条任务提醒'
  if (typeof window !== 'undefined') window.__lastWebNotify = { title, body: finalBody } // 供 e2e 断言
  if (!s?.web_notification || !('Notification' in window) || Notification.permission !== 'granted') return
  try {
    // icon=应用图标；requireInteraction=常驻不自动消失（对齐主流待办应用 toast 需手动处理）；tag=同任务重弹覆盖旧通知
    new Notification(title, { body: finalBody, icon: '/notify-icon.png', requireInteraction: true, tag })
  } catch {
    // 系统通知不可用时静默
  }
}

// 系统通知标题对齐主流待办应用 toast：今天/明天/M月D日
function _reminderDateLabel(item) {
  const d = item.due_at ? dayjs(item.due_at) : dayjs()
  if (d.isSame(dayjs(), 'day')) return '今天'
  if (d.isSame(dayjs().add(1, 'day'), 'day')) return '明天'
  return `${d.month() + 1}月${d.date()}日`
}

// ---------- 每日提醒（设置-提醒与通知）：到点弹当日汇总（今日待办/逾期），同一天只弹一次 ----------
let _dailyTimer = null
function startDailyReminderCheck() {
  stopDailyReminderCheck()
  _dailyTimer = setInterval(checkDailyReminder, 60 * 1000)
  checkDailyReminder()
}
function stopDailyReminderCheck() {
  if (_dailyTimer) {
    clearInterval(_dailyTimer)
    _dailyTimer = null
  }
}
async function checkDailyReminder() {
  const s = taskStore.settings
  if (!s?.daily_reminder_enabled || !s.daily_reminder_time) return
  const now = dayjs()
  const [hh, mm] = s.daily_reminder_time.split(':').map(Number)
  if (now.hour() * 60 + now.minute() < hh * 60 + mm) return // 未到点
  const todayStr = now.format('YYYY-MM-DD')
  if (localStorage.getItem('sun_daily_reminder_last') === todayStr) return // 今天已弹
  localStorage.setItem('sun_daily_reminder_last', todayStr)
  await taskStore.fetchSummary().catch(() => {})
  const sum = taskStore.summary
  const text = `今日待办 ${sum?.today_todo ?? 0} 项${sum?.overdue ? `，逾期 ${sum.overdue} 项` : ''}`
  const n = ElNotification({
    title: '每日提醒',
    type: 'info',
    duration: 0,
    message: h('div', null, [
      h('div', { style: 'margin-bottom:8px' }, text),
      h(ElButton, {
        size: 'small',
        type: 'primary',
        onClick: () => { n.close(); router.push('/task') },
      }, () => '查看'),
    ]),
  })
  fireWebNotify('每日提醒', text, 'daily-reminder')
}

// ---------- 全局提醒轮询：登录后启动、登出停止，不依赖是否停留在任务页 ----------
watch(
  () => authStore.isLoggedIn,
  (loggedIn) => {
    if (loggedIn) {
      taskStore.startReminderPolling()
      taskStore.fetchSettings().catch(() => {}) // 提醒与通知设置（网页提醒/全局持续提醒/每日提醒）
      startDailyReminderCheck()
    } else {
      taskStore.stopReminderPolling()
      stopDailyReminderCheck()
    }
  },
  { immediate: true }
)

const _notifiedIds = new Set()
// 持续提醒：弹窗被关掉但未处理时，隔 2 分钟允许重新弹出（提醒仍 pending，随轮询重弹）
const PERSISTENT_REPOP_MS = 2 * 60 * 1000
const _repopTimers = new Map()
const reminderQueue = ref([]) // 提醒弹窗队列（复刻主流待办应用网页版居中卡片）

// 按优先级设置提醒（设置-提醒与通知）：开启后按任务优先级选铃声，未设则回落全局铃声
function _soundFor(item) {
  const s = taskStore.settings
  if (s?.priority_sound_enabled) {
    const map = {
      3: s.priority_sound_high,
      2: s.priority_sound_medium,
      1: s.priority_sound_low,
      0: s.priority_sound_none,
    }
    return map[item.priority ?? 0] || s.reminder_sound || 'default'
  }
  return s?.reminder_sound || 'default'
}

watch(
  () => taskStore.pendingReminders,
  (items) => {
    const pendingIds = new Set(items.map((i) => i.task_id))
    // 已 ack/完成的任务清掉重弹定时器
    for (const [id, t] of _repopTimers) {
      if (!pendingIds.has(id)) {
        clearTimeout(t)
        _repopTimers.delete(id)
      }
    }
    // 不再 pending（已在别处处理）的弹窗从队列移除（demo 测试提醒除外）
    reminderQueue.value = reminderQueue.value.filter((q) => pendingIds.has(q.item.task_id) || q.item.demo)
    for (const item of items) {
      if (_notifiedIds.has(item.task_id)) continue
      _notifiedIds.add(item.task_id)
      reminderQueue.value.push({ item })
      playReminderSound(_soundFor(item), taskStore.settings?.reminder_volume ?? 80) // 提醒铃声+音量（设置-提醒与通知）
      fireWebNotify(_reminderDateLabel(item), item.title, `reminder-${item.task_id}`)
    }
  },
  { deep: true }
)

function _rpRemove(taskId) {
  reminderQueue.value = reminderQueue.value.filter((q) => q.item.task_id !== taskId)
}

// 设置-网页提醒「测试」：走真实提醒卡片链路弹出
watch(
  () => taskStore.testReminder,
  (item) => {
    if (!item) return
    taskStore.testReminder = null
    reminderQueue.value.push({ item })
    playReminderSound(taskStore.settings?.reminder_sound || 'default', taskStore.settings?.reminder_volume ?? 80)
    fireWebNotify(_reminderDateLabel(item), item.title, 'reminder-test')
  }
)

// ✕ 关闭：非持续=消费掉（本次触发不再弹）；持续=2 分钟后重弹（对齐主流待办应用「持续提醒直到处理」）
function rpDismiss(item) {
  _rpRemove(item.task_id)
  if (item.demo) return // 测试提醒不消费、不重弹
  const persistent = item.persistent || !!taskStore.settings?.persistent_reminder_all
  if (persistent) {
    if (_repopTimers.has(item.task_id)) return
    _repopTimers.set(
      item.task_id,
      setTimeout(() => {
        _repopTimers.delete(item.task_id)
        _notifiedIds.delete(item.task_id)
      }, PERSISTENT_REPOP_MS)
    )
  } else {
    _notifiedIds.delete(item.task_id)
    taskStore.ackReminder(item.task_id)
  }
}

// ◎ 开始专注：消费提醒 + 启动 25 分钟番茄钟并打开专注面板
function rpFocus(item) {
  _rpRemove(item.task_id)
  if (item.demo) return
  _notifiedIds.delete(item.task_id)
  taskStore.ackReminder(item.task_id)
  pomodoroStore.start(item.task_id, 25).then(() => pomodoroStore.openPanel()).catch(() => {})
}

// 完成：消费提醒 + 勾选完成任务
function rpComplete(item) {
  _rpRemove(item.task_id)
  if (item.demo) return
  _notifiedIds.delete(item.task_id)
  taskStore.ackReminder(item.task_id)
  taskStore.complete(item.task_id, true).catch(() => {})
}

// 稍后提醒：推迟 N 分钟后再触发
function rpSnooze(item, minutes) {
  _rpRemove(item.task_id)
  if (item.demo) return
  _notifiedIds.delete(item.task_id)
  taskStore.ackReminder(item.task_id, { snooze_minutes: minutes })
}

const isCollapsed = ref(false)

// 侧边栏头像：取用户名首字符（大写）
const avatarInitial = computed(() => {
  const name = authStore.userInfo?.username || '?'
  return name.trim().charAt(0).toUpperCase()
})

const activeMenu = computed(() => {
  if (route.path.startsWith('/platform')) return '/platform/admin'
  if (route.path.startsWith('/wiki')) return '/wiki'
  return route.path
})

function toggleCollapse() {
  isCollapsed.value = !isCollapsed.value
}

function handleUserCommand(command) {
  if (command === 'profile') {
    router.push('/profile')
  } else if (command === 'logout') {
    logout()
  }
}

function logout() {
  authStore.logout(router)
}
</script>

<style>
:root {
  --ss-primary: #4f6ef7;
  --ss-primary-hover: #6b85f8;
  --ss-primary-light: #eef1fe;
  --ss-bg: #f3f5f9;
  --ss-border: #e6e9f0;
  --ss-text: #1f2937;
  --ss-text-secondary: #6b7280;
  --ss-text-muted: #9ca3af;
  --ss-radius: 8px;
  --ss-radius-sm: 6px;
  --ss-shadow: 0 1px 3px rgba(16, 24, 40, 0.06), 0 1px 2px rgba(16, 24, 40, 0.04);
  --ss-shadow-lg: 0 8px 24px rgba(16, 24, 40, 0.12);
}
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}
html, body, #app {
  height: 100%;
  /* 全视口壳：页面级永不滚动（滚动全部发生在 .app-main 内部容器）；
     否则 teleported 弹层（dropdown 等）贴边时会把 body 撑出 1px 溢出，
     经典滚动条一出又压缩视口引发横向条，叠出双滚动条 */
  overflow: hidden;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Helvetica, Arial, sans-serif;
  color: var(--ss-text);
  -webkit-font-smoothing: antialiased;
}

/* 清单打印（对齐主流待办应用 ⋯「打印」)：只输出任务主区，隐藏侧栏/页头工具/详情栏/弹层 */
@media print {
  body.printing-list .app-sidebar,
  body.printing-list .task-side,
  body.printing-list .task-main-header .hdr-tools,
  body.printing-list .task-main-header .hdr-icon,
  body.printing-list .task-quick-add,
  body.printing-list .task-detail-panel,
  body.printing-list .task-detail-drawer,
  body.printing-list .el-overlay,
  body.printing-list .el-popper,
  body.printing-list .mini-bar {
    display: none !important;
  }
}
</style>

<style>
/* 提醒弹窗队列：全屏居中容器（无遮罩，不挡页面操作），卡片自身响应点击 */
.rp-stack {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-start;
  padding-top: 18vh; /* 卡片靠上，给向下展开的稍后提醒下拉留空间 */
  gap: 12px;
  pointer-events: none;
  z-index: 4000;
}
</style>

<style scoped>
.app-wrapper {
  height: 100vh;
  display: flex;
}
.app-sidebar {
  width: 220px;
  background: linear-gradient(180deg, #1c2536 0%, #171e2c 100%);
  display: flex;
  flex-direction: column;
  transition: width 0.3s;
}
.app-sidebar.collapsed {
  width: 64px;
}
.sidebar-header {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.logo {
  font-weight: 700;
  font-size: 16px;
  letter-spacing: 0.3px;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  display: flex;
  align-items: center;
  gap: 10px;
}
.logo-mark {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(135deg, #6b85f8, #4f6ef7);
  box-shadow: 0 3px 8px rgba(79, 110, 247, 0.45);
}
.logo-text {
  overflow: hidden;
  text-overflow: ellipsis;
}
.collapse-btn {
  padding: 0;
  font-size: 18px;
  color: rgba(255, 255, 255, 0.55);
}
.collapse-btn:hover {
  color: #fff;
}
.sidebar-menu {
  flex: 1;
  border-right: none;
  background: transparent;
  padding: 12px 8px;
  --el-menu-bg-color: transparent;
  --el-menu-text-color: rgba(255, 255, 255, 0.65);
  --el-menu-hover-bg-color: rgba(255, 255, 255, 0.06);
  --el-menu-hover-text-color: #fff;
  --el-menu-active-color: #fff;
  --el-menu-item-height: 44px;
  --el-menu-sub-item-height: 40px;
}
.sidebar-menu:not(.el-menu--collapse) {
  width: 100%;
}
.sidebar-menu :deep(.el-menu-item),
.sidebar-menu :deep(.el-sub-menu__title) {
  border-radius: var(--ss-radius-sm);
  margin-bottom: 4px;
}
.sidebar-menu :deep(.el-menu-item:hover),
.sidebar-menu :deep(.el-sub-menu__title:hover) {
  background-color: rgba(255, 255, 255, 0.06);
}
.sidebar-menu :deep(.el-menu-item.is-active) {
  background: var(--ss-primary);
  color: #fff;
  box-shadow: 0 4px 12px rgba(79, 110, 247, 0.35);
}
.sidebar-menu :deep(.el-menu) {
  background: transparent;
  --el-menu-bg-color: transparent;
}
.sidebar-footer {
  height: 60px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 16px;
}
.user-chip {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 12px 6px 6px;
  border-radius: 999px;
  transition: background 0.2s;
  max-width: 100%;
}
.user-chip:hover {
  background: rgba(255, 255, 255, 0.08);
}
.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 700;
  color: #fff;
  background: linear-gradient(135deg, #6b85f8, #4f6ef7);
  box-shadow: 0 3px 8px rgba(79, 110, 247, 0.4);
}
.user-name {
  color: rgba(255, 255, 255, 0.78);
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  overflow: hidden;
  white-space: nowrap;
}
.user-chip:hover .user-name {
  color: #fff;
}
.sidebar-footer .el-button {
  color: rgba(255, 255, 255, 0.65);
}
.sidebar-footer .el-button:hover {
  color: #fff;
}
.app-main {
  flex: 1;
  overflow: hidden;
  background: var(--ss-bg);
}
</style>
