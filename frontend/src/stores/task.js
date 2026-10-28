import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import dayjs from 'dayjs'
import * as taskApi from '@/api/task'
import { parseAllDayDefault } from '@/views/task/utils'
import { playCompletionSound } from '@/utils/reminderSound'

// tz_offset_minutes = 本地 - UTC 的分钟数（东八区 +480）；JS getTimezoneOffset 符号相反，需取负
const tzOffsetMinutes = -new Date().getTimezoneOffset()

const SMART_LISTS = [
  { key: 'smart:today', smart: 'today', name: '今天', icon: 'Sunny' },
  { key: 'smart:tomorrow', smart: 'tomorrow', name: '明天', icon: 'Sunrise' },
  { key: 'smart:next7', smart: 'next7', name: '最近7天', icon: 'Calendar' },
  { key: 'smart:inbox', smart: 'inbox', name: '收集箱', icon: 'Box' },
  { key: 'smart:completed', smart: 'completed', name: '已完成', icon: 'CircleCheck' },
  { key: 'smart:trash', smart: 'trash', name: '回收站', icon: 'Delete' },
  { key: 'smart:all', smart: 'all', name: '全部', icon: 'List' },
]

export const useTaskStore = defineStore('task', () => {
  // ---------- State ----------
  const lists = ref([])
  const activeListKey = ref('smart:today')
  // 视图模式按清单记忆（对齐主流待办应用：每个清单记住自己的 列表/看板/时间线/四象限）
  const VIEW_MODE_KEY = 'sun_task_view_modes'
  const viewModeMap = ref(JSON.parse(localStorage.getItem(VIEW_MODE_KEY) || '{}'))
  // 四象限已升级为独立内容页（非清单内视图）：清掉历史记忆避免落进看板分支
  for (const k of Object.keys(viewModeMap.value)) {
    if (viewModeMap.value[k] === 'quadrant') viewModeMap.value[k] = 'list'
  }
  localStorage.setItem(VIEW_MODE_KEY, JSON.stringify(viewModeMap.value))
  const _initMode = viewModeMap.value[activeListKey.value]
  // 今天/明天/最近7天不支持时间线：初始恢复时同样回退列表
  const viewMode = ref(
    _initMode === 'timeline' && ['smart:today', 'smart:tomorrow', 'smart:next7'].includes(activeListKey.value) ? 'list' : _initMode || 'list',
  )
  // 供建清单弹窗设置清单默认视图（对齐主流待办应用「添加清单-视图」）
  function setViewModeFor(key, mode) {
    viewModeMap.value = { ...viewModeMap.value, [key]: mode }
    localStorage.setItem(VIEW_MODE_KEY, JSON.stringify(viewModeMap.value))
  }
  // 切视图时写入记忆（仅任务清单类 key；日历/统计/习惯不涉及）
  watch(viewMode, (mode) => {
    const key = activeListKey.value
    if (!/^(smart|list|tag|filter):/.test(key)) return
    viewModeMap.value = { ...viewModeMap.value, [key]: mode }
    localStorage.setItem(VIEW_MODE_KEY, JSON.stringify(viewModeMap.value))
  })
  const tasks = ref([])
  const activeTaskId = ref(null)
  const activeTaskDetail = ref(null)
  const loading = ref(false)
  const pendingReminders = ref([])
  const testReminder = ref(null) // 设置-网页提醒「测试」：走真实提醒卡片链路（App.vue watch 后弹出）
  const calendarTasks = ref([])
  const calendarViewMode = ref('month')   // month|week|day|agenda|multiday|multiweek|year
  const calendarCursor = ref(dayjs())     // 当前锚点日期
  const summary = ref({ today_todo: 0, overdue: 0, completed_total: 0, by_list: [], by_smart: {} })
  const settings = ref(null)
  const filters = ref([])
  const tagCounts = ref([])
  const tags = ref([])  // 标签实体（名称/颜色/上级标签），侧栏标签分组与标签选择器数据源
  const selectedIds = ref([])   // 多选模式勾选的任务 id（16 批量操作）
  const searchVisible = ref(false)  // 全局搜索面板（Ctrl/Cmd+K）
  const settingsVisible = ref(false)  // 设置窗口（侧栏左下角「设置」入口）

  // ---------- 日历 ----------
  async function fetchCalendarTasks(start, end) {
    const res = await taskApi.fetchCalendar({
      start: dayjs(start).toISOString(),
      end: dayjs(end).toISOString(),
      tz_offset_minutes: tzOffsetMinutes,
    })
    calendarTasks.value = res.items
  }

  // 日历时间轴/月视图叠加展示「专注块」：同区间拉取，仅展示已完成的会话
  const calendarFocusSessions = ref([])
  async function fetchCalendarFocusSessions(start, end) {
    try {
      const res = await taskApi.fetchFocusSessions({
        start: dayjs(start).toISOString(),
        end: dayjs(end).toISOString(),
      })
      calendarFocusSessions.value = (res.items || []).filter((s) => s.status === 'completed')
    } catch {
      calendarFocusSessions.value = []
    }
  }

  function calendarRange() {
    const c = calendarCursor.value
    switch (calendarViewMode.value) {
      case 'month': return { start: c.startOf('month').startOf('week'), end: c.endOf('month').endOf('week') }
      case 'week': return { start: c.startOf('week'), end: c.endOf('week') }
      case 'day': return { start: c.startOf('day'), end: c.endOf('day') }
      case 'agenda': return { start: c.startOf('month'), end: c.endOf('month') }
      case 'multiday': return { start: c.startOf('day'), end: c.add(2, 'day').endOf('day') }
      case 'multiweek': return { start: c.startOf('week'), end: c.add(2, 'week').endOf('week') }
      case 'year': return { start: c.startOf('year'), end: c.endOf('year') }
      default: return { start: c.startOf('month'), end: c.endOf('month') }
    }
  }

  async function fetchCalendar() {
    const { start, end } = calendarRange()
    await Promise.all([fetchCalendarTasks(start, end), fetchCalendarFocusSessions(start, end)])
  }

  function shiftCalendar(amount, unit) {
    calendarCursor.value = calendarCursor.value.add(amount, unit)
    fetchCalendar()
  }

  function goCalendarToday() {
    calendarCursor.value = dayjs()
    fetchCalendar()
  }

  function setCalendarCursor(d) {
    calendarCursor.value = d
    fetchCalendar()
  }

  // ---------- 统计 ----------
  async function fetchSummary() {
    try {
      summary.value = await taskApi.fetchSummary({ tz_offset_minutes: tzOffsetMinutes })
    } catch {
      // 统计失败静默
    }
  }

  // 侧栏 badge：按 activeListKey 口径从 summary 取未完成数
  function countFor(key) {
    if (key.startsWith('smart:')) return summary.value.by_smart?.[key.replace('smart:', '')] ?? 0
    if (key.startsWith('list:')) {
      const id = key.replace('list:', '')
      return summary.value.by_list?.find((b) => b.list_id === id)?.todo ?? 0
    }
    return 0
  }

  // ---------- 任务默认值设置 ----------
  async function fetchSettings() {
    settings.value = await taskApi.fetchSettings()
  }

  async function saveSettings(data) {
    settings.value = await taskApi.saveSettings(data)
  }

  // 对未显式指定的字段填默认值（01 的智能清单自动日期优先，需由调用方先注入 due_at）
  // list_id 用 === undefined 判断：null 表示调用方显式指定收集箱（如看板收集箱列）
  function applyDefaults(data) {
    const s = settings.value
    if (!s) return data
    if (!data.due_at && s.default_due === 'today') {
      data.due_at = dayjs().hour(18).minute(0).second(0).toISOString()
    } else if (!data.due_at && s.default_due === 'tomorrow') {
      data.due_at = dayjs().add(1, 'day').hour(18).minute(0).second(0).toISOString()
    }
    if (data.priority == null && s.default_priority) data.priority = s.default_priority
    if (data.list_id === undefined && s.default_list_id) data.list_id = s.default_list_id
    // 默认标签：未显式带标签时套用（§任务默认值）
    if (!data.tags?.length && s.default_tags?.length) data.tags = [...s.default_tags]
    // 默认提醒：最终带日期且未显式设提醒时套用。区分全天/有时间两类（对齐主流待办应用任务默认值）
    if (data.due_at && !data.reminders?.length) {
      if (data.all_day) {
        // 全天任务：截止日 -N 天的 HH:mm 绝对提醒（对齐主流待办应用：当天/提前1~3天/提前1周 (09:00)/自定义）
        const p = parseAllDayDefault(s.default_reminder_allday)
        if (p) {
          const [h, m] = p.time.split(':').map(Number)
          data.reminders = [
            { at: dayjs(data.due_at).startOf('day').subtract(p.days, 'day').hour(h).minute(m).second(0).toISOString() },
          ]
        }
      } else if (s.default_reminder_minutes === 'end') {
        // 结束时：任务结束时刻提醒（= due_at；offset 0 随日期漂移）
        data.reminders = [{ at: dayjs(data.due_at).toISOString(), offset_minutes: 0 }]
      } else if (s.default_reminder_minutes != null) {
        // 有时间的任务：按默认分钟数补相对提醒（0 = 准时）；锚定任务开始时刻（时间段任务取 start_at，对齐主流待办应用）
        const anchor = data.start_at || data.due_at
        data.reminders = [{
          at: dayjs(anchor).subtract(s.default_reminder_minutes, 'minute').toISOString(),
          offset_minutes: s.default_reminder_minutes,
        }]
      }
    }
    return data
  }

  // ---------- 提醒推送（SSE 优先，失败降级轮询；App.vue 登录后启动，登出停止） ----------
  let _pollTimer = null
  let _streamAbort = null

  async function pollReminders() {
    try {
      const res = await taskApi.fetchPendingReminders()
      pendingReminders.value = res.items
    } catch {
      // 轮询失败静默，下一轮重试
    }
  }

  // fetch 流式解析 SSE（原生 EventSource 不支持 Authorization header）
  async function startReminderStream(interval) {
    const token = localStorage.getItem('sun_access_token') || sessionStorage.getItem('sun_access_token')
    if (!token) {
      _pollTimer = setInterval(pollReminders, interval)
      return
    }
    const ctrl = new AbortController()
    _streamAbort = ctrl
    try {
      const resp = await fetch('/api/v1/task/views/stream', {
        headers: { Authorization: `Bearer ${token}` },
        signal: ctrl.signal,
      })
      if (!resp.ok || !resp.body) throw new Error('stream unavailable')
      const reader = resp.body.getReader()
      const decoder = new TextDecoder()
      let buf = ''
      for (;;) {
        const { done, value } = await reader.read()
        if (done) break
        buf += decoder.decode(value, { stream: true })
        let idx
        while ((idx = buf.indexOf('\n\n')) >= 0) {
          const chunk = buf.slice(0, idx)
          buf = buf.slice(idx + 2)
          const line = chunk.split('\n').find((l) => l.startsWith('data:'))
          if (line) pendingReminders.value = JSON.parse(line.slice(5).trim())
        }
      }
      throw new Error('stream closed')
    } catch {
      if (ctrl.signal.aborted) return // 主动停止，不降级
      if (!_pollTimer) _pollTimer = setInterval(pollReminders, interval) // 降级轮询
    } finally {
      if (_streamAbort === ctrl) _streamAbort = null
    }
  }

  function startReminderPolling(interval = 60000) {
    if (_pollTimer || _streamAbort) return
    pollReminders()
    startReminderStream(interval)
  }

  function stopReminderPolling() {
    if (_pollTimer) {
      clearInterval(_pollTimer)
      _pollTimer = null
    }
    if (_streamAbort) {
      _streamAbort.abort()
      _streamAbort = null
    }
    pendingReminders.value = []
  }

  async function ackReminder(taskId, opts = {}) {
    await taskApi.ackReminders(taskId, opts)
    pendingReminders.value = pendingReminders.value.filter((i) => i.task_id !== taskId)
  }

  // 测试提醒：构造一条演示提醒，App.vue 监听后用真实提醒卡片弹出（demo 标记，不走后端 ack/完成）
  function showTestReminder() {
    testReminder.value = {
      task_id: '__test__',
      title: '这是一条测试提醒',
      due_at: new Date().toISOString(),
      persistent: false,
      demo: true,
    }
  }

  // ---------- Getters ----------
  const smartLists = computed(() => SMART_LISTS)

  // 当前自定义清单对象（看板分组等清单级配置的入口）；非清单视图时为 null
  const activeList = computed(() => {
    if (!activeListKey.value.startsWith('list:')) return null
    const id = activeListKey.value.slice(5)
    return lists.value.find((l) => l.id === id) || null
  })

  const todoTasks = computed(() => tasks.value.filter((t) => t.status === 'todo'))
  const doneTasks = computed(() => tasks.value.filter((t) => t.status === 'done'))

  const activeTitle = computed(() => {
    if (activeListKey.value === 'calendar') return '日历'
    if (activeListKey.value === 'stats') return '统计'
    if (activeListKey.value === 'habits') return '习惯打卡'
    if (activeListKey.value === 'summary') return '摘要'
    if (activeListKey.value === 'focus') return '番茄专注'
    // 常用专注列表仍是番茄专注窗口内的视图（对齐主流待办应用：标题不变）
    if (activeListKey.value === 'focus-presets') return '番茄专注'
    if (activeListKey.value === 'quadrant') return '四象限'
    if (activeListKey.value.startsWith('smart:')) {
      return SMART_LISTS.find((s) => s.key === activeListKey.value)?.name || ''
    }
    if (activeListKey.value.startsWith('filter:')) {
      const id = activeListKey.value.replace('filter:', '')
      return filters.value.find((f) => f.id === id)?.name || ''
    }
    if (activeListKey.value.startsWith('tag:')) {
      return `#${activeListKey.value.replace('tag:', '')}`
    }
    const id = activeListKey.value.replace('list:', '')
    return lists.value.find((l) => l.id === id)?.name || ''
  })

  const isCalendar = computed(() => activeListKey.value === 'calendar')
  const isStats = computed(() => activeListKey.value === 'stats')
  const isHabits = computed(() => activeListKey.value === 'habits')
  const isSummary = computed(() => activeListKey.value === 'summary')
  const isFocus = computed(() => activeListKey.value === 'focus')
  const isFocusPresets = computed(() => activeListKey.value === 'focus-presets')
  const isQuadrant = computed(() => activeListKey.value === 'quadrant')

  // ---------- 列表排序/分组（对齐主流待办应用标题行 ⇅ 菜单）：每视图记忆，localStorage 持久化 ----------
  // 状态放 store：头部菜单（TaskManager）与列表视图（TaskListView）共用
  const SORT_STORE_KEY = 'sun_task_sort'
  const sortMap = ref(JSON.parse(localStorage.getItem(SORT_STORE_KEY) || '{}'))
  const sortCfg = computed(() => sortMap.value[activeListKey.value] || { by: 'default', order: 'asc' })
  const SORT_OPTIONS = [
    { value: 'default', label: '默认' },
    { value: 'due', label: '时间' },
    { value: 'priority', label: '优先级' },
    { value: 'title', label: '标题' },
    { value: 'created', label: '创建时间' },
  ]
  const GROUP_OPTIONS = [
    { value: 'list', label: '清单' },
    { value: 'time', label: '时间' },
    { value: 'created', label: '创建时间' },
    { value: 'tag', label: '标签' },
    { value: 'priority', label: '优先级' },
    { value: 'none', label: '无' },
  ]
  // 各排序键的默认顺序：时间/创建=从旧到新，优先级=从高到低，标题=A→Z
  const ORDER_DEFAULT = { due: 'asc', priority: 'desc', title: 'asc', created: 'asc' }
  const orderOptions = computed(() => {
    switch (sortCfg.value.by) {
      case 'priority':
        return [{ value: 'desc', label: '从高到低' }, { value: 'asc', label: '从低到高' }]
      case 'title':
        return [{ value: 'asc', label: 'A 到 Z' }, { value: 'desc', label: 'Z 到 A' }]
      default:
        return [{ value: 'asc', label: '从旧到新' }, { value: 'desc', label: '从新到旧' }]
    }
  })
  function _persistSort() {
    localStorage.setItem(SORT_STORE_KEY, JSON.stringify(sortMap.value))
  }
  function setSortBy(by) {
    sortMap.value = { ...sortMap.value, [activeListKey.value]: { ...sortCfg.value, by, order: ORDER_DEFAULT[by] || 'asc' } }
    _persistSort()
  }
  function setSortOrder(order) {
    sortMap.value = { ...sortMap.value, [activeListKey.value]: { ...sortCfg.value, order } }
    _persistSort()
  }
  function setSortGroup(group) {
    sortMap.value = { ...sortMap.value, [activeListKey.value]: { ...sortCfg.value, group } }
    _persistSort()
  }
  // 未手动选分组时：有自定义分组的清单默认按「自定义」分组；智能清单（今天/明天/最近7天）默认按时间；其余不分组
  // 收集箱自定义分组（per-user TaskSettings.inbox_board_groups）
  const inboxGroups = computed(() => settings.value?.inbox_board_groups || [])
  // 时间线视图：今天/最近7天不支持（对齐主流待办应用：这两个智能清单无法切时间线；明天不在侧栏不涉及）；笔记清单也不支持
  const timelineDisabled = computed(() => {
    if (['smart:today', 'smart:tomorrow', 'smart:next7'].includes(activeListKey.value)) return true
    if (activeListKey.value.startsWith('list:')) {
      const lst = lists.value.find((l) => `list:${l.id}` === activeListKey.value)
      return lst?.kind === 'note'
    }
    return false
  })
  const effectiveGroup = computed(() => {
    if (sortCfg.value.group) return sortCfg.value.group
    // 有自定义分组的清单/收集箱默认按「自定义」分组
    if (activeList.value?.board_groups?.length) return 'boardGroup'
    if (activeListKey.value === 'smart:inbox' && inboxGroups.value.length) return 'boardGroup'
    return ['smart:today', 'smart:tomorrow', 'smart:next7'].includes(activeListKey.value) ? 'time' : 'none'
  })
  // 分组子菜单选项：所有任务视图都有「自定义」（对齐主流待办应用；智能清单=并集只读展示）
  const groupOptions = computed(() => [{ value: 'boardGroup', label: '自定义' }, ...GROUP_OPTIONS])
  const sortByLabel = computed(() => SORT_OPTIONS.find((o) => o.value === sortCfg.value.by)?.label || '默认')
  const sortGroupLabel = computed(() => groupOptions.value.find((o) => o.value === effectiveGroup.value)?.label || '无')
  const sortOrderLabel = computed(() => orderOptions.value.find((o) => o.value === sortCfg.value.order)?.label || '')
  // ⇅ 图标高亮：非默认排序或手动选了分组
  const sortActive = computed(() => sortCfg.value.by !== 'default' || !!sortCfg.value.group)

  // ---------- 隐藏已完成（⋯ 菜单开关行）：按视图记忆 ----------
  const HIDE_DONE_KEY = 'sun_task_hide_done'
  const hideDoneMap = ref(JSON.parse(localStorage.getItem(HIDE_DONE_KEY) || '{}'))
  const hideDone = computed(() => !!hideDoneMap.value[activeListKey.value])
  // 显示开关（对齐主流待办应用标题栏 ⋯）：显示详细 = 任务行追加描述预览；显示检查事项 = 子任务行内默认展开
  const showDetail = ref(localStorage.getItem('task_show_detail') === '1')
  const showSubtasks = ref(localStorage.getItem('task_show_subtasks') === '1')
  function toggleShowDetail() {
    showDetail.value = !showDetail.value
    localStorage.setItem('task_show_detail', showDetail.value ? '1' : '0')
  }
  function toggleShowSubtasks() {
    showSubtasks.value = !showSubtasks.value
    localStorage.setItem('task_show_subtasks', showSubtasks.value ? '1' : '0')
  }
  function toggleHideDone() {
    hideDoneMap.value = { ...hideDoneMap.value, [activeListKey.value]: !hideDone.value }
    localStorage.setItem(HIDE_DONE_KEY, JSON.stringify(hideDoneMap.value))
  }

  // ---------- 参数组装 ----------
  function buildQuery() {
    // limit：后端默认 200，大清单（收集箱 600+）会被截断导致分组/看板缺任务；本地应用一次拉全量
    const params = { tz_offset_minutes: tzOffsetMinutes, limit: 2000 }
    const key = activeListKey.value
    if (key === 'calendar') {
      params.smart = 'all'  // 兜底：日历不在此查询
    } else if (key.startsWith('smart:')) {
      params.smart = key.replace('smart:', '')
    } else if (key.startsWith('filter:')) {
      params.filter_id = key.replace('filter:', '')
    } else if (key.startsWith('tag:')) {
      params.tag = key.replace('tag:', '')
    } else if (key.startsWith('list:')) {
      params.list_id = key.replace('list:', '')
    }
    return params
  }

  // ---------- Actions：清单 ----------
  // ---------- 看板分组（清单级 board_groups / 收集箱级 inbox_board_groups） ----------
  async function addBoardGroup(name, index = null) {
    if (activeListKey.value === 'smart:inbox') {
      const r = await taskApi.addInboxGroup(name, index)
      if (settings.value) settings.value.inbox_board_groups = r.board_groups
      return
    }
    const lst = activeList.value
    if (!lst) return
    const item = await taskApi.addListGroup(lst.id, name, index)
    _replaceListLocal(item)
  }

  async function renameBoardGroup(fromName, toName) {
    if (activeListKey.value === 'smart:inbox') {
      const r = await taskApi.renameInboxGroup(fromName, toName)
      if (settings.value) settings.value.inbox_board_groups = r.board_groups
      await fetchTasks() // 重命名由后端级联改任务 group
      return
    }
    const lst = activeList.value
    if (!lst) return
    const item = await taskApi.renameListGroup(lst.id, fromName, toName)
    _replaceListLocal(item)
    await fetchTasks() // 重命名由后端级联改任务 group，刷新当前列表
  }

  async function deleteBoardGroup(name) {
    if (activeListKey.value === 'smart:inbox') {
      const r = await taskApi.deleteInboxGroup(name)
      if (settings.value) settings.value.inbox_board_groups = r.board_groups
      await fetchTasks() // 组内任务回落未分组
      return
    }
    const lst = activeList.value
    if (!lst) return
    const item = await taskApi.deleteListGroup(lst.id, name)
    _replaceListLocal(item)
    await fetchTasks() // 组内任务回落未分组列
  }

  // 分组「移动到」另一清单/收集箱（对齐主流待办应用分组右键菜单）：分组名随迁，组内任务整体移动并保留分组
  // toListId=null 表示移入收集箱；成功后重拉清单（board_groups）/设置（inbox 分组）/当前任务列表
  async function moveBoardGroup(name, toListId) {
    const fromListId = activeListKey.value === 'smart:inbox' ? null : activeList.value?.id ?? null
    await taskApi.moveListGroup(name, fromListId, toListId)
    await Promise.all([fetchLists(), fetchSettings()])
    await fetchTasks()
  }

  function _replaceListLocal(item) {
    const idx = lists.value.findIndex((l) => l.id === item.id)
    if (idx !== -1) lists.value[idx] = item
  }

  async function fetchLists() {
    const res = await taskApi.fetchLists()
    lists.value = res.items
  }

  async function createList(data) {
    const item = await taskApi.createList(data)
    lists.value.push(item)
    return item
  }

  async function updateList(id, data) {
    const item = await taskApi.updateList(id, data)
    const idx = lists.value.findIndex((l) => l.id === id)
    if (idx !== -1) lists.value[idx] = item
    return item
  }

  async function deleteList(id) {
    await taskApi.deleteList(id)
    lists.value = lists.value.filter((l) => l.id !== id)
    if (activeListKey.value === `list:${id}`) {
      await selectList('smart:inbox')
    }
  }

  // ---------- Actions：筛选器 / 标签 ----------
  async function fetchFilters() {
    const res = await taskApi.fetchFilters({ tz_offset_minutes: tzOffsetMinutes })
    filters.value = res.items
  }

  async function createFilter(data) {
    const item = await taskApi.createFilter(data)
    filters.value.push(item)
    return item
  }

  async function updateFilter(id, data) {
    const item = await taskApi.updateFilter(id, data)
    const idx = filters.value.findIndex((f) => f.id === id)
    if (idx !== -1) filters.value[idx] = item
    return item
  }

  async function deleteFilter(id) {
    await taskApi.deleteFilter(id)
    filters.value = filters.value.filter((f) => f.id !== id)
    if (activeListKey.value === `filter:${id}`) {
      await selectList('smart:inbox')
    }
  }

  async function fetchTagCounts() {
    const res = await taskApi.fetchTagCounts()
    tagCounts.value = res.items
  }

  // 侧栏计数徽标（标签分组 + 过滤器行）统一刷新，fire-and-forget
  function _refreshCounts() {
    fetchTagCounts().catch(() => {})
    fetchFilters().catch(() => {})
  }

  // 侧栏标签树：已建实体 ∪ 任务派生标签名（无实体者视为无颜色顶级标签），父标签下缩进子标签
  const sidebarTags = computed(() => {
    const counts = Object.fromEntries(tagCounts.value.map((t) => [t.tag, t.count]))
    const byId = {}
    for (const t of tags.value) {
      byId[t.id] = { id: t.id, name: t.name, color: t.color, count: counts[t.name] || 0, children: [] }
    }
    const rows = []
    for (const t of tags.value) {
      const row = byId[t.id]
      const parent = t.parent_id && byId[t.parent_id]
      if (parent) parent.children.push(row)
      else rows.push(row)
    }
    for (const name of Object.keys(counts)) {
      if (!tags.value.some((t) => t.name === name)) {
        rows.push({ id: null, name, color: null, count: counts[name], children: [] })
      }
    }
    return rows
  })

  async function fetchTags() {
    const res = await taskApi.fetchTags()
    tags.value = res.items
  }

  async function createTag(data) {
    const item = await taskApi.createTag(data)
    tags.value.push(item)
    return item
  }

  async function updateTag(id, data) {
    const item = await taskApi.updateTag(id, data)
    const idx = tags.value.findIndex((t) => t.id === id)
    if (idx !== -1) tags.value[idx] = item
    // 重命名由后端级联改任务 tags 数组，前端刷新当前列表与侧栏计数
    if (data.name) {
      await fetchTasks()
      _refreshCounts()
    }
    return item
  }

  async function deleteTag(id) {
    const tag = tags.value.find((t) => t.id === id)
    await taskApi.deleteTag(id)
    // 下级标签被后端级联删除，一并从本地移除
    tags.value = tags.value.filter((t) => t.id !== id && t.parent_id !== id)
    if (tag && activeListKey.value === `tag:${tag.name}`) {
      await selectList('smart:inbox')
    }
    await fetchTasks()
    _refreshCounts()
  }

  // ---------- Actions：任务 ----------
  async function fetchTasks() {
    if (activeListKey.value === 'calendar') {
      return fetchCalendar()  // 日历走独立取数，避免拼出 list_id='calendar' 导致 404
    }
    loading.value = true
    try {
      const res = await taskApi.fetchTasks(buildQuery())
      tasks.value = res.items
      // 列表视图下右侧详情栏默认展开：未选中任务时自动打开第一个任务（对齐主流待办应用「今天」视图）
      // 多选批量操作中除外：右栏展示批量面板，不自动打开详情
      if (
        !activeTaskId.value &&
        !selectedIds.value.length &&
        tasks.value.length &&
        viewMode.value === 'list' &&
        !['calendar', 'stats', 'habits', 'summary'].includes(activeListKey.value)
      ) {
        openDetail(tasks.value[0].id).catch(() => {})
      }
    } finally {
      loading.value = false
    }
  }

  async function selectList(key) {
    activeListKey.value = key
    selectedIds.value = []
    if (key === 'calendar') {
      closeDetail()
      await fetchCalendar()
    } else if (key === 'stats') {
      closeDetail()
      // 统计页自行取数（summary + focus/stats + 习惯），无需拉任务列表
      await fetchSummary()
    } else if (key === 'habits') {
      closeDetail()
      // 习惯打卡由 HabitManager 挂载时自行取数，无需拉任务列表
    } else if (key === 'summary') {
      closeDetail()
      // 摘要页自行取数（summary/preview + settings），无需拉任务列表
    } else if (key === 'focus') {
      closeDetail()
      // 番茄专注为内容页（PomodoroPanel），计时状态在 pomodoro store，无需拉任务列表
    } else if (key === 'focus-presets') {
      closeDetail()
      // 常用专注为独立内容页（FocusPresetsView，对齐主流待办应用：点进去的单独一页），自行取数
    } else if (key === 'quadrant') {
      closeDetail()
      // 四象限为独立内容页（TaskQuadrantView），跨清单聚合，自行取数
    } else {
      // 恢复该清单记忆的视图模式（每个清单独立记忆，对齐主流待办应用）；今天/最近7天不支持时间线则回退列表
      const remembered = viewModeMap.value[key] || 'list'
      viewMode.value = remembered === 'timeline' && timelineDisabled.value ? 'list' : remembered
      // 时间线视图用任务条旁的迷你卡片承载详情，不保留右侧悬浮详情栏（否则盖住时间线）
      if (viewMode.value === 'timeline') {
        closeDetail()
        await fetchTasks()
        return
      }
      // 详情栏保持/自动展开：打开的任务仍在新视图中则保留详情；否则关闭并由列表视图自动展开第一个任务（无任务则无详情栏）
      const keepId = activeTaskId.value
      await fetchTasks() // keepId 为空时 fetchTasks 内部已自动展开第一个任务
      if (keepId) {
        if (tasks.value.some((t) => t.id === keepId)) {
          refreshDetail().catch(() => {}) // 保留详情并刷新数据（可能在他处被改）
        } else {
          closeDetail()
          if (tasks.value.length && viewMode.value === 'list') openDetail(tasks.value[0].id).catch(() => {})
        }
      }
    }
  }

  async function createTask(data) {
    // 不兜底默认日期：快速添加的落点规则（今天/明天自动带日期）在 TaskQuickAdd.submit() 处理
    const task = await taskApi.createTask(data)
    // 当前视图可能不包含新任务（如带日期的任务建在「收集箱」视图），仅在匹配时插入
    const key = activeListKey.value
    const inCurrentList =
      key === 'smart:all' ||
      (key === 'smart:inbox' && !task.list_id) ||
      key === `list:${task.list_id}` ||
      // 筛选器/标签视图下无法本地预判是否命中，直接整表刷新
      key.startsWith('filter:') ||
      key.startsWith('tag:')
    if (inCurrentList) {
      if (key.startsWith('filter:') || key.startsWith('tag:')) {
        await fetchTasks()
        fetchTagCounts()
      } else {
        tasks.value.unshift(task)
      }
    }
    if (data.tags?.length) _refreshCounts() // 侧栏标签分组计数（fire-and-forget）
    return task
  }

  async function updateTask(id, data) {
    const task = await taskApi.updateTask(id, data)
    _replaceLocal(task)
    if (data.tags) _refreshCounts()
    return task
  }

  // 日历拖拽排期：minute=null 仅改日期（月视图），否则落到具体时段（时间轴视图）
  async function rescheduleTask(task, day, minute = null) {
    const due = dayjs(task.due_at)
    const payload = { due_at: day.hour(due.hour()).minute(due.minute()).second(0).toISOString() }
    if (minute === null) {
      if (task.start_at) {
        const s = dayjs(task.start_at)
        payload.start_at = day.hour(s.hour()).minute(s.minute()).second(0).toISOString()
      }
    } else {
      payload.start_at = day.startOf('day').add(minute, 'minute').toISOString()
      payload.duration_minutes = task.duration_minutes || 60
    }
    return updateTask(task.id, payload)
  }

  async function deleteTask(id) {
    await taskApi.deleteTask(id)
    tasks.value = tasks.value.filter((t) => t.id !== id)
    if (activeTaskId.value === id) closeDetail()
    _refreshCounts()
  }

  async function restoreTask(id) {
    await taskApi.restoreTask(id)
    tasks.value = tasks.value.filter((t) => t.id !== id)
    if (activeTaskId.value === id) closeDetail()
  }

  async function purgeTask(id) {
    await taskApi.purgeTask(id)
    tasks.value = tasks.value.filter((t) => t.id !== id)
    if (activeTaskId.value === id) closeDetail()
  }

  async function complete(id, done) {
    const task = await taskApi.completeTask(id, done)
    _replaceLocal(task)
    // 完成提示音（设置-提醒与通知）：勾选完成时播放所选音色，音量随提醒音量
    const cs = settings.value?.completion_sound
    if (done && cs && cs !== 'none') {
      playCompletionSound(cs, settings.value?.reminder_volume ?? 80)
    }
    _refreshCounts()
    return task
  }

  async function move(id, listId) {
    const task = await taskApi.moveTask(id, { list_id: listId })
    // 移动后若不再属于当前清单视图（自定义清单/收集箱），从列表移除；看板/智能清单（按日期聚合）不受影响
    const key = activeListKey.value
    const isListView = key.startsWith('list:')
    const isInbox = key === 'smart:inbox'
    if ((isListView && task.list_id !== key.slice(5)) || (isInbox && task.list_id != null)) {
      tasks.value = tasks.value.filter((t) => t.id !== id)
      if (activeTaskId.value === id) closeDetail()
      if (activeTaskDetail.value?.id === id) activeTaskDetail.value = task
    } else {
      _replaceLocal(task)
    }
    _refreshCounts()
    return task
  }

  // ---------- 「移动到」弹窗（右键菜单/详情栏底栏共用，store 驱动避免组件互引） ----------
  const moveDialogTaskId = ref(null)
  function openMoveDialog(id) {
    moveDialogTaskId.value = id
  }

  async function sort(id, payload) {
    const task = await taskApi.sortTask(id, payload)
    _replaceLocal(task)
    return task
  }

  // ---------- 批量操作（16） ----------
  function toggleSelect(id) {
    const idx = selectedIds.value.indexOf(id)
    if (idx === -1) selectedIds.value.push(id)
    else selectedIds.value.splice(idx, 1)
  }

  function clearSelection() {
    selectedIds.value = []
  }

  // Shift 范围选择整体写入（对齐主流待办应用桌面端：按住 Shift 点选首尾任务批量选择）
  function setSelected(ids) {
    selectedIds.value = [...ids]
  }

  async function batch(action, payload = {}) {
    const res = await taskApi.batchTasks({ ids: [...selectedIds.value], action, payload })
    // 属性编辑（日期/优先级/置顶/完成）保留选择便于连续操作（对齐主流待办应用）；移动/删除后清空
    if (action === 'delete' || action === 'move') selectedIds.value = []
    await fetchTasks()
    _refreshCounts()
    return res
  }

  async function skip(id) {
    const task = await taskApi.skipTask(id)
    _replaceLocal(task)
    return task
  }

  function _replaceLocal(task) {
    const idx = tasks.value.findIndex((t) => t.id === task.id)
    if (idx !== -1) {
      tasks.value[idx] = task
    }
    const calIdx = calendarTasks.value.findIndex((t) => t.id === task.id)
    if (calIdx !== -1) {
      calendarTasks.value[calIdx] = task
    }
    if (activeTaskDetail.value?.id === task.id) {
      activeTaskDetail.value = { ...activeTaskDetail.value, ...task }
    }
  }

  // ---------- 详情抽屉 ----------
  async function openDetail(id) {
    activeTaskId.value = id
    activeTaskDetail.value = await taskApi.fetchTask(id)
  }

  function closeDetail() {
    activeTaskId.value = null
    activeTaskDetail.value = null
  }

  // ---------- 子任务 ----------
  async function refreshDetail() {
    if (!activeTaskId.value) return
    const detail = await taskApi.fetchTask(activeTaskId.value)
    activeTaskDetail.value = detail
    _replaceLocal(detail)
  }

  async function createSubtask(parentId, title) {
    await taskApi.createTask({ title, parent_id: parentId })
    await refreshDetail()
  }

  async function completeSubtask(id, done) {
    await taskApi.completeTask(id, done)
    await refreshDetail()
  }

  async function deleteSubtask(id) {
    await taskApi.deleteTask(id)
    await refreshDetail()
  }

  return {
    lists,
    activeListKey,
    activeList,
    viewMode,
    setViewModeFor,
    tasks,
    activeTaskId,
    activeTaskDetail,
    loading,
    pendingReminders,
    testReminder,
    calendarTasks,
    summary,
    settings,
    inboxGroups,
    filters,
    tagCounts,
    tags,
    sidebarTags,
    selectedIds,
    searchVisible,
    settingsVisible,
    smartLists,
    todoTasks,
    doneTasks,
    activeTitle,
    isCalendar,
    isStats,
    isHabits,
    isSummary,
    isFocus,
    isFocusPresets,
    isQuadrant,
    sortCfg,
    SORT_OPTIONS,
    GROUP_OPTIONS,
    groupOptions,
    orderOptions,
    setSortBy,
    setSortOrder,
    setSortGroup,
    effectiveGroup,
    timelineDisabled,
    sortByLabel,
    sortGroupLabel,
    sortOrderLabel,
    sortActive,
    hideDone,
    showDetail,
    showSubtasks,
    toggleShowDetail,
    toggleShowSubtasks,
    toggleHideDone,
    fetchLists,
    addBoardGroup,
    renameBoardGroup,
    deleteBoardGroup,
    moveBoardGroup,
    showTestReminder,
    createList,
    updateList,
    deleteList,
    fetchFilters,
    createFilter,
    updateFilter,
    deleteFilter,
    fetchTagCounts,
    fetchTags,
    createTag,
    updateTag,
    deleteTag,
    fetchTasks,
    selectList,
    createTask,
    updateTask,
    deleteTask,
    restoreTask,
    purgeTask,
    complete,
    move,
    sort,
    skip,
    toggleSelect,
    clearSelection,
    setSelected,
    batch,
    openDetail,
    closeDetail,
    refreshDetail,
    createSubtask,
    completeSubtask,
    deleteSubtask,
    startReminderPolling,
    stopReminderPolling,
    ackReminder,
    fetchCalendarTasks,
    calendarFocusSessions,
    fetchCalendar,
    rescheduleTask,
    shiftCalendar,
    goCalendarToday,
    setCalendarCursor,
    calendarViewMode,
    calendarCursor,
    fetchSummary,
    countFor,
    fetchSettings,
    saveSettings,
    applyDefaults,
    moveDialogTaskId,
    openMoveDialog,
  }
})
