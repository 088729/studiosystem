<template>
  <div class="task-list-view flat-list">
    <!-- 回收站：不区分完成状态/不可拖拽，行内提供恢复/彻底删除 -->
    <template v-if="isTrash">
      <TaskItem
        v-for="task in store.tasks"
        :key="task.id"
        :task="task"
        hide-check
      >
        <template #actions>
          <el-button link type="primary" @click="onRestore(task)">恢复</el-button>
          <el-button link type="danger" @click="onPurge(task)">彻底删除</el-button>
        </template>
      </TaskItem>
      <el-empty v-if="!store.tasks.length && !store.loading" description="回收站为空" />
    </template>

    <!-- 今天视图即使无任务也要展示习惯分组 -->
    <template v-else-if="hasContent">
      <!-- 多选开关（16 批量操作）；排序/分组菜单在标题行右侧 ⇅ 图标（对齐主流待办应用） -->
      <div class="list-toolbar">
        <el-button size="small" round :type="selectMode ? 'primary' : 'default'" @click="toggleSelectMode">
          {{ selectMode ? '退出多选' : '多选' }}
        </el-button>
      </div>

      <!-- 已置顶分组（对齐主流待办应用：置顶任务独立成组、始终展示在列表最前端，📌 图标 + 计数 + 可折叠） -->
      <div v-if="pinnedItems.length" class="pinned-section">
        <div class="date-group-toggle" @click="showPinned = !showPinned">
          <ChevronRight :size="14" class="fold-arrow" :class="{ expanded: showPinned }" />
          <Pin :size="13" class="pinned-icon" />
          <span class="date-group-label">已置顶 ({{ pinnedItems.length }})</span>
        </div>
        <draggable
          v-if="showPinned"
          :list="pinnedItems"
          item-key="id"
          :animation="150"
          :group="{ name: 'task-x-group', pull: true, put: true }"
          :disabled="selectMode"
          ghost-class="item-ghost"
          data-gkey="__pinned"
          :move="onDragMove"
          @end="onPinnedDragEnd"
        >
          <template #item="{ element }">
            <TaskItem
              :task="element"
              :data-task-id="element.id"
              :show-check="selectMode"
              :selected="store.selectedIds.includes(element.id)"
              @complete="onComplete"
              @open="onOpen"
              @select="onSelect"
              @contextmenu="onContextMenu"
            />
          </template>
        </draggable>
      </div>

      <!-- 已过期分组：todo 且 due_at < 今日 00:00（本地），置顶标红 -->
      <div v-if="overdueTasks.length" class="overdue-section">
        <div class="overdue-toggle" @click="showOverdue = !showOverdue">
          <ChevronRight :size="14" class="fold-arrow" :class="{ expanded: showOverdue }" />
          <span class="overdue-label">已过期 ({{ overdueTasks.length }})</span>
          <el-button
            size="small"
            text
            type="primary"
            class="postpone-btn"
            @click.stop="postponeOverdue"
          >顺延</el-button>
        </div>
        <template v-if="showOverdue">
          <!-- 分组可拖时，已过期组也作为拖动源（拖到某天组=改期，对齐主流待办应用） -->
          <draggable
            v-if="groupDraggable"
            :list="overdueItems"
            item-key="id"
            :animation="150"
            :group="{ name: 'task-x-group', pull: true, put: false }"
            :disabled="selectMode"
            ghost-class="item-ghost"
            data-gkey="__overdue"
            :move="onDragMove"
            @end="onGroupDragEnd"
          >
            <template #item="{ element }">
              <TaskItem
                :task="element"
                :data-task-id="element.id"
                :show-check="selectMode"
                :selected="store.selectedIds.includes(element.id)"
                @complete="onComplete"
                @open="onOpen"
                @select="onSelect"
                @contextmenu="onContextMenu"
              />
            </template>
          </draggable>
          <TaskItem
            v-else
            v-for="task in overdueTasks"
            :key="task.id"
            :task="task"
            :show-check="selectMode"
            :selected="store.selectedIds.includes(task.id)"
            @complete="onComplete"
            @open="onOpen"
            @select="onSelect"
            @contextmenu="onContextMenu"
          />
        </template>
      </div>

      <!-- 智能清单/分组视图：分组渲染，组头带计数可折叠（对齐主流待办应用「分组」）；清单自定义分组（board_groups）也走这里 -->
      <template v-if="displayGroups">
        <div v-for="group in displayGroups" :key="group.key" class="date-group">
          <div
            class="date-group-toggle"
            @click="toggleDateGroup(group.key)"
            @contextmenu="onGroupContextMenu($event, group)"
          >
            <ChevronRight :size="14" class="fold-arrow" :class="{ expanded: !collapsedDateGroups[group.key] }" />
            <span class="date-group-label">{{ group.label }} ({{ group.tasks.length }})</span>
            <!-- 清单/收集箱自定义分组（对齐主流待办应用）：悬浮组头出现 +（组内添加）与 ⋯（分组菜单），组头右键弹同一菜单 -->
            <template v-if="canManageGroup(group)">
              <Plus :size="14" class="group-add" title="添加任务" @click.stop="startGroupAdd(group)" />
              <MoreVertical :size="14" class="group-more" title="分组菜单" @click.stop="openGroupMenu($event, group)" />
            </template>
          </div>
          <template v-if="!collapsedDateGroups[group.key]">
            <!-- 组头 + 展开的组内快速添加输入框（对齐主流待办应用：点 + 在组头下方出现，回车创建到该分组） -->
            <input
              v-if="addingGroupKey === group.key"
              :ref="(el) => setGroupAddRef(el, group)"
              v-model="groupNewTitle"
              v-auth="'task:create'"
              class="group-inline-add"
              placeholder="+ 添加任务"
              @keydown.enter.prevent="submitGroupAdd(group)"
              @keydown.esc="closeGroupAdd"
              @blur="onGroupAddBlur"
            />
            <!-- 时间/优先级/清单/标签/自定义分组：跨组拖动=智能改属性（对齐主流待办应用）；创建时间分组不可拖 -->
            <draggable
              v-if="groupDraggable"
              :list="groupItems[group.key]"
              item-key="id"
              :animation="150"
              :group="{ name: 'task-x-group', pull: true, put: true }"
              :disabled="selectMode"
              ghost-class="item-ghost"
              :data-gkey="group.key"
              :move="onDragMove"
              @end="onGroupDragEnd"
            >
              <template #item="{ element }">
                <TaskItem
                  :task="element"
                  :data-task-id="element.id"
                  :show-check="selectMode"
                  :selected="store.selectedIds.includes(element.id)"
                  @complete="onComplete"
                  @open="onOpen"
                  @select="onSelect"
                  @contextmenu="onContextMenu"
                />
              </template>
            </draggable>
            <TaskItem
              v-else
              v-for="task in group.tasks"
              :key="task.id"
              :task="task"
              :show-check="selectMode"
              :selected="store.selectedIds.includes(task.id)"
              @complete="onComplete"
              @open="onOpen"
              @select="onSelect"
              @contextmenu="onContextMenu"
            />
          </template>
        </div>
      </template>

      <draggable
        v-else
        v-model="upcomingItems"
        item-key="id"
        :animation="150"
        :group="{ name: 'task-x-group', pull: true, put: true }"
        :disabled="!sortable || selectMode"
        ghost-class="item-ghost"
        data-gkey="__flat"
        :move="onDragMove"
        @end="onDragEnd"
      >
        <template #item="{ element }">
          <TaskItem
            :task="element"
            :data-task-id="element.id"
            :show-check="selectMode"
            :selected="store.selectedIds.includes(element.id)"
            @complete="onComplete"
            @open="onOpen"
            @select="onSelect"
            @contextmenu="onContextMenu"
          />
        </template>
      </draggable>

      <!-- 「今天/最近7天」视图的习惯分组（对齐主流待办应用）：今日待打卡习惯，组头计数 = 未打卡数 -->
      <div v-if="isSmartHabitView && habitStore.inSmart && habitStore.habits.length" class="habit-section">
        <div class="date-group-toggle" @click="showHabits = !showHabits">
          <ChevronRight :size="14" class="fold-arrow" :class="{ expanded: showHabits }" />
          <span class="date-group-label">习惯 ({{ uncheckedHabitCount }})</span>
        </div>
        <template v-if="showHabits">
          <div
            v-for="habit in habitStore.habits"
            :key="habit.id"
            class="habit-row"
            :class="{ done: habit.today_checked || habit.today_skipped }"
            @click="onHabitClick(habit)"
            @contextmenu.prevent="onHabitContextMenu($event, habit)"
          >
            <img :src="habitIconOf(habit.icon)" class="habit-emoji" alt="" />
            <span class="habit-name">{{ habit.name }}</span>
            <span class="habit-progress">{{ habit.today_count }}/{{ habit.target_per_day }}</span>
            <el-button
              size="small"
              round
              :type="habit.today_checked ? 'success' : 'primary'"
              :plain="!habit.today_checked"
              :disabled="habit.today_checked || habit.today_skipped"
              class="habit-checkin-btn"
              @click.stop="onCheckin(habit)"
            ><Check v-if="habit.today_checked" :size="13" style="vertical-align: -2px" /> {{ habit.today_checked ? '已打卡' : habit.today_skipped ? '已跳过' : '打卡' }}</el-button>
          </div>
        </template>
      </div>

      <!-- 「隐藏已完成」（⋯ 菜单）开启时整段不渲染 -->
      <div v-if="sortedDoneTasks.length && !store.hideDone" class="done-section">
        <div class="done-toggle" @click="showDone = !showDone">
          <ChevronRight :size="14" class="fold-arrow" :class="{ expanded: showDone }" />
          已完成 ({{ sortedDoneTasks.length }})
        </div>
        <template v-if="showDone">
          <TaskItem
            v-for="task in sortedDoneTasks"
            :key="task.id"
            :task="task"
            :show-check="selectMode"
            :selected="store.selectedIds.includes(task.id)"
            @complete="onComplete"
            @open="onOpen"
            @select="onSelect"
            @contextmenu="onContextMenu"
          />
        </template>
      </div>

    </template>

    <el-empty v-else-if="!store.loading" :description="emptyText" />

    <!-- 任务行右键上下文菜单 -->
    <TaskContextMenu ref="ctxMenu" />
    <!-- 分组头右键/⋯ 上下文菜单（重命名/上方/下方添加/移动到/删除） -->
    <GroupContextMenu ref="groupMenu" />
    <!-- 习惯行右键上下文菜单 -->
    <HabitContextMenu ref="habitMenu" />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ChevronRight, Check, Pin, MoreVertical, Plus } from 'lucide-vue-next'
import { habitIconOf } from '@/utils/habitIcons'
import dayjs from 'dayjs'
import draggable from 'vuedraggable'
import { useTaskStore } from '@/stores/task'
import { useAuthStore } from '@/stores/auth'
import { useHabitStore } from '@/stores/habit'
import TaskItem from '../TaskItem.vue'
import TaskContextMenu from '../TaskContextMenu.vue'
import GroupContextMenu from '../GroupContextMenu.vue'
import HabitContextMenu from '@/views/habit/HabitContextMenu.vue'

const store = useTaskStore()
const authStore = useAuthStore()
const habitStore = useHabitStore()
const showDone = ref(true)
const showOverdue = ref(true)
const showPinned = ref(true)
const showHabits = ref(true)
const selectMode = ref(false)  // 16 多选模式

// 「今天」「最近7天」视图进入时拉取习惯列表（最近7天同样按今天状态展示；保持简单，不做缓存优化）
const isSmartHabitView = computed(() => ['smart:today', 'smart:next7'].includes(store.activeListKey))
watch(
  isSmartHabitView,
  (v) => { if (v) habitStore.fetchHabits() },
  { immediate: true }
)

// 组头计数 = 未打卡数（已跳过不计入）；已打卡的行以完成态展示
const uncheckedHabitCount = computed(
  () => habitStore.habits.filter((h) => !h.today_checked && !h.today_skipped).length
)

// 列表区是否有内容（今天/最近7天视图含习惯分组）
const hasContent = computed(
  () =>
    store.todoTasks.length > 0 ||
    store.doneTasks.length > 0 ||
    !!boardGroups.value || // 空清单但已有自定义分组时仍渲染分区（组头 + 可组内添加）
    (isSmartHabitView.value && habitStore.inSmart && habitStore.habits.length > 0)
)

async function onCheckin(habit) {
  if (habit.today_checked || habit.today_skipped) return
  await habitStore.checkin(habit.id)
  ElMessage.success(`「${habit.name}」打卡成功`)
}

// 点习惯行（非按钮区）：打开右侧习惯详情面板，同时收起任务详情（两栏互斥，对齐主流待办应用）
function onHabitClick(habit) {
  store.closeDetail()
  habitStore.openHabit(habit.id)
}

// 习惯行右键菜单（对齐主流待办应用：开始专注›/记录日志/跳过打卡/未完成）
const habitMenu = ref(null)
function onHabitContextMenu(event, habit) {
  habitMenu.value?.open(event, habit)
}

const emptyText = computed(() =>
  store.activeListKey === 'smart:today' ? '今天没有任务，享受当下 ☕' : '暂无任务'
)

const isTrash = computed(() => store.activeListKey === 'smart:trash')

// 逾期判定与「今天」智能清单口径一致：todo 且 due_at < 今日 00:00（本地）
const isOverdue = (t) =>
  t.status === 'todo' && t.due_at && dayjs(t.due_at).isBefore(dayjs().startOf('day'))

// ---------- 排序/分组：状态在 task store（头部 ⇅ 菜单与本视图共用，每视图记忆 localStorage） ----------
const sortCfg = computed(() => store.sortCfg)
const effectiveGroup = computed(() => store.effectiveGroup)
const SORT_VALUE = {
  due: (t) => (t.due_at ? dayjs(t.due_at).valueOf() : null),
  priority: (t) => t.priority || 0,
  title: (t) => t.title || '',
  created: (t) => (t.created_at ? dayjs(t.created_at).valueOf() : 0),
}
// 组内排序：置顶优先；选了排序方式后按所选键排序（无日期沉底），默认=保持后端/sort_order 次序（稳定排序）
function applySort(arr) {
  const pins = arr.filter((t) => t.is_pinned)
  const rest = arr.filter((t) => !t.is_pinned)
  const { by, order } = sortCfg.value
  if (by !== 'default') {
    const get = SORT_VALUE[by]
    const dir = order === 'desc' ? -1 : 1
    rest.sort((a, b) => {
      const va = get(a)
      const vb = get(b)
      if (va == null && vb == null) return 0
      if (va == null) return 1
      if (vb == null) return -1
      const cmp = typeof va === 'string' ? va.localeCompare(vb, 'zh') : va - vb
      return cmp * dir
    })
  }
  return [...pins, ...rest]
}

// ---------- 同组/平铺手动排序：智能清单后端无字段存「视图内顺序」，本地按「视图|口径|组键」记忆 ----------
// 自定义清单/收集箱平铺仍走后端 sort_order（onDragEnd），不走这里
const dayOrderMap = ref(JSON.parse(localStorage.getItem('sun_task_day_order') || '{}'))
const orderKeyOf = (gkey) => `${store.activeListKey}|${effectiveGroup.value}|${gkey}`
function persistManualOrder(gkey, ids) {
  dayOrderMap.value = { ...dayOrderMap.value, [orderKeyOf(gkey)]: ids }
  localStorage.setItem('sun_task_day_order', JSON.stringify(dayOrderMap.value))
}
// 仅在默认排序下套用手动顺序（用户显式选了排序方式时以字段排序为准）
function applyManualOrder(arr, gkey) {
  if (sortCfg.value.by !== 'default') return arr
  const ord = dayOrderMap.value[orderKeyOf(gkey)]
  if (!ord || !ord.length) return arr
  const idx = new Map(ord.map((id, i) => [id, i]))
  return [...arr].sort((a, b) => (idx.get(a.id) ?? Infinity) - (idx.get(b.id) ?? Infinity)) // 未记过的保持原相对序沉底
}

const overdueTasks = computed(() => applyManualOrder(applySort(store.todoTasks.filter((t) => isOverdue(t) && !t.is_pinned)), '__overdue'))
const upcomingTasks = computed(() => applyManualOrder(applySort(store.todoTasks.filter((t) => !isOverdue(t) && !t.is_pinned)), '__flat'))
// 置顶任务独立成组（对齐主流待办应用「已置顶」）：从已过期/平铺/分组中排除，只出现在顶部置顶区
const pinnedTasks = computed(() => applyManualOrder(store.todoTasks.filter((t) => t.is_pinned), '__pinned'))
const sortedDoneTasks = computed(() => applySort(store.doneTasks))

// 拖拽排序：自定义清单/收集箱平铺可拖（后端 sort_order）；其他智能清单平铺在默认排序下也可拖（本地记忆顺序）；
// 分组激活时转为跨组改属性/同组记忆顺序。对齐主流待办应用：排序方式非「默认」时自定义清单仍可拖，拖动落库后自动切回默认
const sortable = computed(() => {
  if (displayGroups.value) return false
  const key = store.activeListKey
  if (key.startsWith('list:') || key === 'smart:inbox') return true
  return sortCfg.value.by === 'default'
})

// ---------- 分组（选项/默认规则在 store，此处只做切组渲染） ----------

const WEEKDAYS = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

function dateGroupLabel(d) {
  if (!d) return '无日期'
  if (d.isSame(dayjs(), 'day')) return `今天 ${WEEKDAYS[d.day()]}`
  if (d.isSame(dayjs().add(1, 'day'), 'day')) return '明天'
  return `${d.month() + 1}月${d.date()}日 ${WEEKDAYS[d.day()]}`
}

const PRIORITY_GROUP_LABEL = { 3: '高优先级', 2: '中优先级', 1: '低优先级', 0: '无优先级' }

// 分组计算：组内沿用 applySort（置顶优先+所选排序）；组间按各自口径排序
const groups = computed(() => {
  const by = effectiveGroup.value
  if (by === 'none' || by === 'boardGroup') return null // 自定义分组走 boardGroups 分区
  const listOrd = (id) => (id == null ? -1 : Math.max(0, store.lists.findIndex((l) => l.id === id)))
  const listNameOf = (id) => (id == null ? '收集箱' : store.lists.find((l) => l.id === id)?.name || '清单')
  const map = new Map()
  for (const t of upcomingTasks.value) {
    let key, label, ord
    if (by === 'time') {
      const d = t.due_at ? dayjs(t.due_at).startOf('day') : null
      key = d ? d.format('YYYY-MM-DD') : 'none'
      label = dateGroupLabel(d)
      ord = d ? d.valueOf() : Infinity
    } else if (by === 'created') {
      const d = t.created_at ? dayjs(t.created_at).startOf('day') : null
      key = d ? d.format('YYYY-MM-DD') : 'none'
      label = dateGroupLabel(d)
      ord = d ? -d.valueOf() : Infinity // 创建时间：新的在前
    } else if (by === 'priority') {
      const p = t.priority || 0
      key = `p${p}`
      label = PRIORITY_GROUP_LABEL[p]
      ord = -p // 高→低
    } else if (by === 'list') {
      key = t.list_id || 'inbox'
      label = listNameOf(t.list_id)
      ord = listOrd(t.list_id)
    } else {
      // tag：取第一个标签，无标签沉底
      const tg = (t.tags || [])[0]
      key = tg || 'none'
      label = tg || '无标签'
      ord = tg ? 0 : Infinity
    }
    if (!map.has(key)) map.set(key, { key, label, ord, tasks: [] })
    map.get(key).tasks.push(t)
  }
  const arr = [...map.values()]
  for (const g of arr) g.tasks = applyManualOrder(applySort(g.tasks), g.key)
  arr.sort((a, b) => a.ord - b.ord || a.key.localeCompare(b.key, 'zh'))
  return arr
})

// ---------- 自定义分组分区（对齐主流待办应用「分组/编辑分组」）：⇅ 分组=「自定义」时按分区渲染 ----------
// 来源：清单视图=清单 board_groups；收集箱=用户级 inbox_board_groups（两者可管理：组头 +/⋯菜单+右键+拖动改 group）；
// 其余智能视图=当前视图任务 group 名并集（只读展示：无 +/⋯/无右键菜单/不可拖——智能清单不支持创建分组）
const boardGroups = computed(() => {
  if (effectiveGroup.value !== 'boardGroup') return null // 手动选了其他分组维度（含「无」）时让位
  const viewKey = store.activeListKey
  let defs, manageable
  if (viewKey.startsWith('list:')) {
    defs = store.activeList?.board_groups || []
    manageable = true
  } else if (viewKey === 'smart:inbox') {
    defs = store.inboxGroups
    manageable = true
  } else {
    defs = unionGroupNames()
    manageable = false
  }
  if (!defs.length) return null
  const all = [
    { key: '__ungrouped', label: '未分组', ord: -1, boardGroup: false, manageable: false },
    ...defs.map((g, i) => ({ key: g, label: g, ord: i, boardGroup: true, manageable })),
  ]
  const map = new Map(all.map((d) => [d.key, { ...d, tasks: [] }]))
  for (const t of upcomingTasks.value) {
    const key = t.group && map.has(t.group) ? t.group : '__ungrouped'
    map.get(key).tasks.push(t)
  }
  const arr = [...map.values()]
  for (const g of arr) g.tasks = applyManualOrder(applySort(g.tasks), g.key)
  return arr.sort((a, b) => a.ord - b.ord)
})
// 智能视图并集：当前视图任务出现过的 group 名，按「收集箱组序 → 来源清单侧栏序+组内序」排序
function unionGroupNames() {
  const rank = new Map()
  store.inboxGroups.forEach((g, gi) => rank.set(g, gi)) // 收集箱在侧栏最上，其分组排最前
  store.lists.forEach((l, li) =>
    (l.board_groups || []).forEach((g, gi) => {
      if (!rank.has(g)) rank.set(g, 1000 + li * 100 + gi)
    })
  )
  const names = new Set()
  for (const t of upcomingTasks.value) if (t.group) names.add(t.group)
  return [...names].sort((a, b) => (rank.get(a) ?? 99999) - (rank.get(b) ?? 99999) || a.localeCompare(b, 'zh'))
}
// 自定义分组是否可管理（清单/收集箱）：决定组头 +/⋯ 按钮、组头右键菜单、拖动
const boardGroupManageable = computed(() => !!boardGroups.value?.some((g) => g.manageable))
const displayGroups = computed(() => groups.value || boardGroups.value)

// ---------- 组头操作（对齐主流待办应用）：悬浮 +（组内添加任务）与 ⋯/右键（分组菜单） ----------
function canManageGroup(group) {
  return !!group.manageable && authStore.hasPerm('task:manage')
}

const groupMenu = ref(null)
// ⋯ 点击：菜单锚定在按钮下方
function openGroupMenu(e, group) {
  const rect = e.currentTarget.getBoundingClientRect()
  groupMenu.value?.open(rect.left, rect.bottom + 6, group)
}
// 组头右键：菜单跟随光标；不可管理的分组（智能视图并集）不拦截浏览器菜单
function onGroupContextMenu(e, group) {
  if (!canManageGroup(group)) return
  e.preventDefault()
  groupMenu.value?.open(e.clientX, e.clientY, group)
}

// 组内快速添加：点 + 在组头下方展开输入框，回车创建到该分组（对齐主流待办应用），Esc/失焦收起
const addingGroupKey = ref(null)
const groupNewTitle = ref('')
let groupAddEl = null
let groupAddBlurTimer = null
function setGroupAddRef(el, group) {
  groupAddEl = addingGroupKey.value === group.key ? el : null
}
async function startGroupAdd(group) {
  clearTimeout(groupAddBlurTimer)
  addingGroupKey.value = group.key
  groupNewTitle.value = ''
  await nextTick()
  groupAddEl?.focus()
}
function closeGroupAdd() {
  addingGroupKey.value = null
  groupNewTitle.value = ''
  groupAddEl = null
}
// 失焦延迟收起：给「+」按钮的 click 留一拍（输入框立即移除会产生布局位移吃掉点击）
function onGroupAddBlur() {
  clearTimeout(groupAddBlurTimer)
  groupAddBlurTimer = setTimeout(() => {
    if (addingGroupKey.value) closeGroupAdd()
  }, 150)
}
async function submitGroupAdd(group) {
  const title = groupNewTitle.value.trim()
  if (!title) {
    closeGroupAdd()
    return
  }
  await store.createTask(
    store.applyDefaults({
      title,
      // 收集箱显式传 null（applyDefaults 不覆盖 null）；清单视图带清单 id
      list_id: store.activeListKey === 'smart:inbox' ? null : store.activeList.id,
      group: group.key === '__ungrouped' ? null : group.key,
    })
  )
  groupNewTitle.value = '' // 连续添加：清空并保持输入框展开
  nextTick(() => groupAddEl?.focus())
}

const collapsedDateGroups = ref({})
function toggleDateGroup(key) {
  collapsedDateGroups.value = {
    ...collapsedDateGroups.value,
    [key]: !collapsedDateGroups.value[key],
  }
}

// ---------- 分组内跨组拖动（对齐主流待办应用）：拖到目标组=智能改属性 ----------
// 时间分组=改日期（保留时刻/全天，无日期组=清除日期）；优先级分组=改优先级；清单分组=移动清单；自定义分组=改 group。
// 创建时间分组不可拖；同组内拖动不落库（智能清单不支持自定义排序），DOM 回弹。
const groupDraggable = computed(
  () => ['time', 'priority', 'list', 'tag'].includes(effectiveGroup.value) || boardGroupManageable.value
)

// 各组/已过期组的可变副本（Sortable 会原地 splice :list 数组，不能直接拖 computed 里的数组）
const groupItems = ref({})
watch(
  displayGroups,
  (val) => {
    const map = {}
    if (val) for (const g of val) map[g.key] = [...g.tasks]
    groupItems.value = map
  },
  { immediate: true, deep: true }
)
const overdueItems = ref([])
watch(
  overdueTasks,
  (val) => { overdueItems.value = [...val] },
  { immediate: true, deep: true }
)
const pinnedItems = ref([])
watch(
  pinnedTasks,
  (val) => { pinnedItems.value = [...val] },
  { immediate: true, deep: true }
)

function revertGroupDom(evt) {
  const el = evt.item
  const parent = evt.from
  // 排除拖动元素自身后，原位置 oldIndex 处的元素就是还原后的「下一个兄弟」
  const others = [...parent.children].filter((c) => c !== el)
  parent.insertBefore(el, others[evt.oldIndex] || null)
}

// ---------- 拖动转子任务（对齐主流待办应用：拖到目标任务「右下方」= 转为其子任务） ----------
// 区域规则：相对拖动起点明显右移（>48px，即「往右下拽」的手势）+ 目标行下半部 → 子任务模式
//（高亮目标行、取消排序插入）；垂直拖动（右移不明显）保持原排序/跨组语义。
// 三个 draggable（平铺/分组/已过期）共用 :move prop（@move 事件拿不到 originalEvent）。
const subtaskTarget = ref(null) // { id, el }
let dragStartX = 0
// 拖动起点 x：用捕获阶段 pointerdown 记录（HTML5 DnD 的 dragstart 坐标不可靠）
const _recordDragStart = (e) => { dragStartX = e.clientX }
onMounted(() => document.addEventListener('pointerdown', _recordDragStart, true))
onBeforeUnmount(() => document.removeEventListener('pointerdown', _recordDragStart, true))
function clearSubtaskTarget() {
  if (subtaskTarget.value?.el) subtaskTarget.value.el.classList.remove('subtask-drop-target')
  subtaskTarget.value = null
}
function onDragMove(evt, originalEvent) {
  clearSubtaskTarget()
  const rel = evt.related
  if (!rel || !rel.classList || !rel.classList.contains('task-item') || rel === evt.dragged) return
  const rect = rel.getBoundingClientRect()
  const x = originalEvent.clientX - rect.left
  const y = originalEvent.clientY - rect.top
  const movedRight = originalEvent.clientX - dragStartX > 48
  if (movedRight && y > rect.height * 0.5 && x > 80 && x < rect.width && rel.dataset.taskId) {
    subtaskTarget.value = { id: rel.dataset.taskId, el: rel }
    rel.classList.add('subtask-drop-target')
    return false // 取消排序插入，松手走转子任务
  }
}
// 拖动结束统一入口：优先处理「转子任务」，返回 true 表示已接管
async function tryConvertSubtask(evt) {
  if (!subtaskTarget.value) return false
  const pid = subtaskTarget.value.id
  const taskId = evt.item.dataset.taskId
  clearSubtaskTarget()
  if (!taskId || taskId === pid) return true
  try {
    await store.updateTask(taskId, { parent_id: pid })
    ElMessage.success('已转为子任务')
  } catch {
    // 拦截器已弹错误提示（如含子任务/层级限制）
  }
  await store.fetchTasks() // 刷新列表（子任务不再出现在列表）
  return true
}

async function onGroupDragEnd(evt) {
  if (await tryConvertSubtask(evt)) return
  const from = evt.from.dataset.gkey
  const to = evt.to.dataset.gkey
  if (!to) { revertGroupDom(evt); return }
  if (from === to) {
    // 同组内拖动 = 组内手动排序：Sortable 已把副本数组/DOM 换成新顺序，本地记忆（智能清单无后端字段可存）
    if (evt.newIndex !== evt.oldIndex) {
      const ids = (from === '__overdue' ? overdueItems.value : groupItems.value[from] || []).map((t) => t.id)
      persistManualOrder(from, ids)
    }
    return
  }
  const taskId = evt.item.dataset.taskId
  const task = store.todoTasks.find((t) => t.id === taskId)
  if (!task) { revertGroupDom(evt); return }
  try {
    if (!(await applyGroupTarget(task, to))) {
      revertGroupDom(evt)
      return
    }
  } catch {
    // 拦截器已弹错误提示
  } finally {
    await store.fetchTasks() // 统一重拉，刷新分组渲染并覆盖 Sortable 的 DOM 移动
  }
}

// 跨组落点的属性修改（时间=改期/优先级=改优先级/清单=移动/标签=首标签/自定义分组=改 group；返回 false=不支持）
async function applyGroupTarget(task, to) {
  const by = boardGroups.value ? 'boardGroup' : effectiveGroup.value
  const taskId = task.id
  if (by === 'boardGroup') {
    await store.updateTask(taskId, { group: to === '__ungrouped' ? null : to })
  } else if (by === 'time') {
    if (to === 'none') {
      await store.updateTask(taskId, { due_at: null, start_at: null })
    } else {
      const target = dayjs(to)
      const anchor = task.due_at || task.start_at
      const payload = {}
      if (anchor) {
        const diff = target.startOf('day').diff(dayjs(anchor).startOf('day'), 'day')
        if (task.due_at) payload.due_at = dayjs(task.due_at).add(diff, 'day').toISOString()
        if (task.start_at) payload.start_at = dayjs(task.start_at).add(diff, 'day').toISOString()
      } else {
        payload.due_at = (task.all_day ? target.startOf('day') : target.hour(23).minute(59).second(0)).toISOString()
      }
      await store.updateTask(taskId, payload)
    }
  } else if (by === 'priority') {
    await store.updateTask(taskId, { priority: Number(to.slice(1)) })
  } else if (by === 'list') {
    await store.move(taskId, to === 'inbox' ? null : to)
  } else if (by === 'tag') {
    // 拖到某标签组=该标签置顶为首要标签（分组键是首标签，保留其余标签）；拖到「无标签」组=清空标签
    const tags = to === 'none' ? [] : [to, ...(task.tags || []).filter((t) => t !== to)]
    await store.updateTask(taskId, { tags })
  } else {
    return false
  }
  return true
}

// 置顶区拖动结束：同区=重排（自定义清单落 sort_order/智能清单本地记忆）；拖入=置顶，拖出=取消置顶+目标组语义
async function onPinnedDragEnd(evt) {
  if (await tryConvertSubtask(evt)) return
  const from = evt.from.dataset.gkey
  const to = evt.to.dataset.gkey
  const taskId = evt.item.dataset.taskId
  if (from === '__pinned' && to === '__pinned') {
    if (evt.newIndex === evt.oldIndex) return
    const key = store.activeListKey
    if (!groups.value && (key.startsWith('list:') || key === 'smart:inbox') && sortCfg.value.by === 'default') {
      try {
        const id = pinnedItems.value[evt.newIndex]?.id
        const payload =
          evt.newIndex < pinnedItems.value.length - 1
            ? { before_task_id: pinnedItems.value[evt.newIndex + 1].id }
            : { after_task_id: pinnedItems.value[evt.newIndex - 1].id }
        await store.sort(id, payload)
      } finally {
        await store.fetchTasks()
      }
    } else {
      persistManualOrder('__pinned', pinnedItems.value.map((t) => t.id))
    }
    return
  }
  if (!to) { revertGroupDom(evt); return }
  const task = store.todoTasks.find((t) => t.id === taskId)
  try {
    if (to === '__pinned') {
      await store.updateTask(taskId, { is_pinned: true })
      ElMessage.success('已置顶')
    } else if (from === '__pinned') {
      await store.updateTask(taskId, { is_pinned: false })
      ElMessage.success('已取消置顶')
      if (task) await applyGroupTarget(task, to) // 分组模式下同时应用目标组语义（如改期）
    }
  } catch {
    // 拦截器已弹错误提示
  } finally {
    await store.fetchTasks()
  }
}

// 「顺延」：循环 PATCH 把已过期任务改期到今天（all_day 存当地 00:00 对应 UTC，非全天改今天 23:59）
async function postponeOverdue() {
  const today = dayjs().startOf('day')
  let failed = 0
  for (const t of overdueTasks.value) {
    const due = t.all_day ? today : today.hour(23).minute(59).second(0)
    try {
      await store.updateTask(t.id, { due_at: due.toISOString() })
    } catch {
      failed++ // 拦截器已弹错误提示
    }
  }
  if (!failed) ElMessage.success(`已顺延 ${overdueTasks.value.length} 项任务到今天`)
  else ElMessage.warning(`部分任务顺延失败（${failed} 项）`)
}

const upcomingItems = ref([])
watch(
  () => upcomingTasks.value,
  (val) => { upcomingItems.value = [...val] },
  { immediate: true, deep: true }
)

async function onDragEnd(evt) {
  if (await tryConvertSubtask(evt)) return
  // 置顶区 ↔ 平铺区跨区拖动：只改置顶标记，落点顺序由置顶区/平铺各自管理
  const from = evt.from.dataset.gkey
  const to = evt.to.dataset.gkey
  if (from !== to && (from === '__pinned' || to === '__pinned')) {
    try {
      await store.updateTask(evt.item.dataset.taskId, { is_pinned: to === '__pinned' })
      ElMessage.success(to === '__pinned' ? '已置顶' : '已取消置顶')
    } catch {
      // 拦截器已弹错误提示
    } finally {
      await store.fetchTasks()
    }
    return
  }
  if (evt.newIndex === evt.oldIndex) return
  const key = store.activeListKey
  if (!key.startsWith('list:') && key !== 'smart:inbox') {
    // 智能清单平铺：本地记忆手动顺序（Sortable 已更新 upcomingItems 与 DOM，persist 触发重算保持一致）
    persistManualOrder('__flat', upcomingItems.value.map((t) => t.id))
    return
  }
  try {
    if (sortCfg.value.by !== 'default') {
      // 对齐主流待办应用：非默认排序下拖动 = 把当前显示顺序固化为手动顺序，并自动切回默认（自定义）排序
      const items = upcomingItems.value
      for (let i = 0; i < items.length; i++) {
        const so = (i + 1) * 1024
        if (items[i].sort_order !== so) await store.sort(items[i].id, { sort_order: so })
      }
      store.setSortBy('default')
      ElMessage.success('已切换为「默认」排序，可自由拖拽排序')
    } else {
      const taskId = upcomingItems.value[evt.newIndex]?.id
      if (taskId === undefined) return
      const payload =
        evt.newIndex < upcomingItems.value.length - 1
          ? { before_task_id: upcomingItems.value[evt.newIndex + 1].id }
          : { after_task_id: upcomingItems.value[evt.newIndex - 1].id } // B4：落尾交后端算 sort_order，不再前端硬编码 +1024
      await store.sort(taskId, payload)
    }
    await store.fetchTasks() // sort_order 变了但数组位置没变，重拉以后端次序刷新，避免弹回
  } catch {
    await store.fetchTasks() // 失败回滚
  }
}

function onComplete(task, done) {
  store.complete(task.id, done)
}

function onOpen(task, evt) {
  // Shift+点击 = 范围选择（锚点→当前）；Ctrl/Cmd+点击 = 加选/取消单个（均自动进入多选模式，对齐主流待办应用桌面端）
  if (evt?.shiftKey) {
    rangeSelect(task.id)
    return
  }
  if (evt?.ctrlKey || evt?.metaKey) {
    if (!selectMode.value) {
      selectMode.value = true
      store.closeDetail()
    }
    store.toggleSelect(task.id)
    lastClickId.value = task.id
    return
  }
  if (selectMode.value) {  // 多选模式下点击行 = 切换勾选，不开详情
    store.toggleSelect(task.id)
    lastClickId.value = task.id
    return
  }
  lastClickId.value = task.id
  store.openDetail(task.id)
}

// 右键上下文菜单（对齐主流待办应用：仅弹菜单，不强制选中详情）
const ctxMenu = ref(null)
function onContextMenu(task, evt) {
  ctxMenu.value?.open(evt.clientX, evt.clientY, task)
}

// ---------- 多选 / 批量操作（16） ----------
watch(
  () => store.activeListKey,
  () => { selectMode.value = false }  // 切清单退出多选（selectedIds 由 store.selectList 清空）
)
// 选择从有到无（批量面板「取消」/删除/移动后）同步退出多选模式；
// 批量面板本身在 TaskManager 层按 selectedIds 非空原位替换详情栏
watch(
  () => store.selectedIds.length,
  (n, prev) => { if (!n && prev > 0) selectMode.value = false }
)

function toggleSelectMode() {
  selectMode.value = !selectMode.value
  if (!selectMode.value) store.clearSelection()
  else store.closeDetail() // 对齐主流待办应用：批量操作面板占据右栏，与详情互斥
}

// ---------- Shift/Ctrl 多选（对齐主流待办应用桌面端：按住 Shift 点选多个/首尾任务即范围选择，Ctrl 点选加选单个） ----------
const lastClickId = ref(null) // 范围选择锚点（最近一次普通/Ctrl 点击的任务）
// 当前渲染顺序的任务 id（置顶区→已过期→分组/平铺→已完成），Shift 范围按此顺序计算
const displayOrderIds = computed(() => {
  const ids = []
  for (const t of pinnedItems.value) ids.push(t.id)
  for (const t of overdueItems.value) ids.push(t.id)
  if (groups.value) {
    for (const g of groups.value) {
      if (collapsedDateGroups.value[g.key]) continue
      for (const t of groupItems.value[g.key] || []) ids.push(t.id)
    }
  } else {
    for (const t of upcomingItems.value) ids.push(t.id)
  }
  if (showDone.value && !store.hideDone) for (const t of sortedDoneTasks.value) ids.push(t.id)
  return ids
})
function rangeSelect(id) {
  if (!selectMode.value) {
    selectMode.value = true
    store.closeDetail()
  }
  const ids = displayOrderIds.value
  const a = ids.indexOf(lastClickId.value)
  const b = ids.indexOf(id)
  if (a === -1 || b === -1 || a === b) {
    if (!store.selectedIds.includes(id)) store.toggleSelect(id)
    lastClickId.value = id
    return
  }
  const [s, e] = a < b ? [a, b] : [b, a]
  // 按住 Shift 连续点选 = 累加范围（锚点保持首次点击任务）
  const cur = new Set(store.selectedIds)
  for (const x of ids.slice(s, e + 1)) cur.add(x)
  store.setSelected([...cur])
}

function onSelect(task) {
  store.toggleSelect(task.id)
}


async function onRestore(task) {
  await store.restoreTask(task.id)
  ElMessage.success('已恢复')
}

async function onPurge(task) {
  try {
    await ElMessageBox.confirm('彻底删除后不可恢复，确定？', '警告', {
      type: 'warning',
      confirmButtonText: '彻底删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  await store.purgeTask(task.id)
  ElMessage.success('已彻底删除')
}
</script>

<style scoped>
.list-toolbar {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-bottom: 8px;
}
.overdue-section {
  margin-bottom: 12px;
}
.overdue-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: #f56c6c;
  cursor: pointer;
  padding: 6px 4px;
  user-select: none;
}
.fold-arrow {
  transition: transform 0.2s;
  flex-shrink: 0;
}
.fold-arrow.expanded {
  transform: rotate(90deg);
}
.overdue-label {
  font-weight: 500;
  flex: 1;
}
.postpone-btn {
  margin-left: auto;
}
.date-group {
  margin-bottom: 12px;
}
.date-group-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--ss-text-secondary);
  cursor: pointer;
  padding: 6px 4px;
  user-select: none;
}

.date-group-label {
  font-weight: 500;
  color: var(--ss-text);
}

/* 清单/收集箱自定义分组组头操作（对齐主流待办应用）：+ 添加任务 / ⋯ 分组菜单，默认隐藏、悬浮组头显示 */
.group-add,
.group-more {
  margin-left: 4px;
  color: var(--ss-text-muted);
  display: none;
  align-items: center;
  cursor: pointer;
  flex-shrink: 0;
  border-radius: 4px;
  padding: 2px;
}
.date-group-toggle:hover .group-add,
.date-group-toggle:hover .group-more {
  display: inline-flex;
}
.group-add:hover,
.group-more:hover {
  color: var(--ss-text);
  background: var(--ss-bg);
}
/* 组头 + 展开的组内快速添加输入框（对齐主流待办应用：轻量单行，聚焦蓝框） */
.group-inline-add {
  display: block;
  width: calc(100% - 22px);
  margin: 2px 0 6px 18px;
  border: 1px solid var(--ss-primary);
  border-radius: 6px;
  outline: none;
  padding: 6px 10px;
  font-size: 13px;
  font-family: inherit;
  color: var(--ss-text);
  background: #fff;
  box-sizing: border-box;
}
.group-inline-add::placeholder {
  color: var(--ss-text-muted);
}
.pinned-section {
  margin-bottom: 12px;
}
.pinned-icon {
  color: #f7b500;
  flex-shrink: 0;
}
.habit-section {
  margin-bottom: 12px;
}
.habit-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: #fff;
  border-radius: var(--ss-radius-sm);
  border: 1px solid var(--ss-border);
  margin-bottom: 8px;
  cursor: pointer;
}
.habit-row:hover {
  border-color: var(--ss-primary);
}
.habit-emoji {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
}
.habit-name {
  flex: 1;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.habit-row.done .habit-name {
  text-decoration: line-through;
  color: var(--ss-text-muted);
}
.habit-progress {
  font-size: 12px;
  color: var(--ss-text-secondary);
}
.habit-checkin-btn {
  flex-shrink: 0;
}
.done-section {
  margin-top: 12px;
}
.done-toggle {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--ss-text-secondary);
  cursor: pointer;
  padding: 6px 4px;
  user-select: none;
}

.item-ghost {
  opacity: 0.4;
}

/* 拖动转子任务：目标行高亮（浅蓝底 + 蓝色底边，对齐主流待办应用「拖到右下方」反馈） */
:deep(.task-item.subtask-drop-target) {
  background: #eef3ff;
  border-radius: 6px;
  box-shadow: inset 0 -2px 0 #4772fa;
}

/* ===== 列表行扁平化（对齐主流待办应用任务行样式）：无卡片边框/间距/阴影/分隔线，行间留白，悬停浅灰底 ===== */
.flat-list :deep(.task-item) {
  border: none;
  border-radius: 0;
  margin-bottom: 0;
  box-shadow: none;
  background: transparent;
  padding: 0; /* 内边距移到 main-line，让悬停底色整行通栏 */
}
.flat-list :deep(.task-item:hover) {
  background: transparent;
  box-shadow: none;
}
/* 主行：整行通栏，独立悬停/选中底色 */
.flat-list :deep(.main-line) {
  padding: 12px 12px 12px 26px;
}
.flat-list :deep(.main-line:hover) {
  background: var(--ss-bg);
}
/* 悬停主行显示 ⋯ 更多按钮 + 拖拽手柄（对齐主流待办应用） */
.flat-list :deep(.main-line:hover .row-more) {
  display: inline-flex;
}
.flat-list :deep(.main-line:hover .row-grip) {
  opacity: 1;
}
.flat-list :deep(.task-item.selected) {
  background: transparent;
}
.flat-list :deep(.task-item.selected .main-line) {
  background: var(--ss-primary-light);
}
/* 优先级条贴到行最左边缘（对齐主流待办应用彩色竖条） */
.flat-list :deep(.priority-bar) {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  border-radius: 0;
}
/* 子任务行=独立整行：与主行同高、独立悬停（对齐主流待办应用：无分隔线） */
.flat-list :deep(.sub-inline) {
  margin: 0;
}
.flat-list :deep(.sub-inline-row) {
  border-radius: 0;
  margin-left: 0;
  padding: 10px 12px 10px 7px;
}
.flat-list :deep(.sub-inline-row:hover) {
  background: var(--ss-bg);
}
/* 拖动转子任务高亮放在最后，避免被扁平 hover 覆盖 */
.flat-list :deep(.task-item.subtask-drop-target) {
  background: #eef3ff;
  box-shadow: inset 0 -2px 0 #4772fa;
}
</style>
