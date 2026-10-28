<template>
  <div class="task-board-view">
    <div v-for="col in columns" :key="col.key" class="board-column">
      <div class="column-header" @contextmenu="onColContextMenu($event, col)">
        <span v-if="col.color" class="col-dot" :style="{ background: col.color }" />
        <span class="column-name" :class="{ 'is-overdue': col.isOverdue }">{{ col.name }}</span>
        <span class="column-count">{{ col.items.length }}</span>
        <!-- 列头「+」：在列顶展开添加任务输入框（对齐主流待办应用「点分组右上角 + 添加任务」） -->
        <Plus
          v-if="!col.isOverdue && !isTrash && !col.noAdd && authStore.hasPerm('task:create')"
          :size="15"
          class="add-icon"
          @click.stop="openAdd(col)"
        />
        <!-- 列头 ⋯/右键：与列表视图同一分组菜单（重命名/上方/下方添加/移动到/删除） -->
        <MoreVertical
          v-if="canManageCol(col)"
          :size="14"
          class="more-icon column-more"
          title="分组菜单"
          @click.stop="openColMenu($event, col)"
        />
      </div>

      <!-- 列体：flat 时单个拖放区；分组激活时按子分组嵌套（对齐主流待办应用） -->
      <div class="column-body">
        <el-input
          v-if="addOpenKeys.has(col.key)"
          v-model="col.newTitle"
          size="small"
          :placeholder="isNoteList ? '添加笔记' : '添加任务'"
          class="column-add top-add"
          autofocus
          @keyup.enter="addToColumn(col)"
          @keyup.esc="addOpenKeys.delete(col.key)"
          @blur="addOpenKeys.delete(col.key)"
        />
        <template v-for="dg in col.dragGroups" :key="dg.key">
          <div
            v-if="dg.label"
            class="sub-header"
            @click="toggleSub(col.key, dg.key)"
          >
            <ChevronDown :size="13" class="sub-arrow" :class="{ collapsed: isSubCollapsed(col.key, dg.key) }" />
            <span class="sub-label">{{ dg.label }}</span>
            <span class="sub-count">{{ dg.items.length }}</span>
          </div>
          <draggable
            v-show="!dg.label || !isSubCollapsed(col.key, dg.key)"
            v-model="dg.items"
            :group="dg.noPut || col.isOverdue ? { name: 'task-cards', put: false } : 'task-cards'"
            item-key="id"
            class="drag-zone"
            :data-col-key="col.key"
            :data-dg-key="dg.key"
            :animation="150"
            ghost-class="card-ghost"
            @end="(evt) => onDragEnd(evt)"
          >
            <template #item="{ element }">
              <div
                class="board-card"
                :data-id="element.id"
                @click="store.openDetail(element.id)"
                @contextmenu.prevent="onContextMenu(element, $event)"
              >
                <div class="card-top">
                  <!-- 笔记无完成概念：卡片显示 📔 图标（对齐主流待办应用笔记看板卡片） -->
                  <BookOpen v-if="element.is_note" :size="14" class="card-note-flag" />
                  <span
                    v-else
                    class="check-dot"
                    :class="{ checked: element.status === 'done' }"
                    @click.stop="store.complete(element.id, element.status !== 'done')"
                  >
                    <Check v-if="element.status === 'done'" :size="12" />
                  </span>
                  <span class="card-title" :class="{ done: element.status === 'done' }">{{ element.title }}</span>
                </div>
                <!-- 标签 chip（对齐主流待办应用看板卡片） -->
                <div v-if="element.tags?.length" class="card-tags">
                  <span v-for="tg in element.tags" :key="tg" class="card-tag" :style="tagStyle(tg)">{{ tg }}</span>
                </div>
                <div class="card-meta">
                  <span class="priority-bar" :class="`p${element.priority}`" />
                  <!-- 日期天列里卡片不重复显示日期；其余列显示实际日期（逾期红） -->
                  <span v-if="element.due_at && (boardKind === 'list' || !col.day)" class="card-due" :class="{ overdue: isOverdue(element) }">
                    {{ dayjs(element.due_at).format('MM-DD') }}
                  </span>
                  <span v-if="element.subtask_total" class="card-sub">{{ element.subtask_done }}/{{ element.subtask_total }}</span>
                  <!-- 非清单视图卡片显示所属清单名（对齐主流待办应用） -->
                  <span v-if="boardKind === 'group'" class="card-list">{{ listNameOf(element.list_id) }}</span>
                  <el-dropdown
                    trigger="click"
                    class="card-more"
                    @command="(cmd) => onCardCommand(cmd, element)"
                  >
                    <MoreVertical :size="14" class="more-icon" @click.stop />
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="edit" v-if="authStore.hasPerm('task:edit')">编辑</el-dropdown-item>
                        <el-dropdown-item command="delete" v-if="authStore.hasPerm('task:delete')">删除</el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </div>
            </template>
          </draggable>
        </template>
      </div>

      <el-input
        v-if="!col.isOverdue && !isTrash && !col.noAdd"
        v-model="col.newTitle"
        v-auth="'task:create'"
        size="small"
        :placeholder="isNoteList ? '+ 添加笔记' : '+ 添加任务'"
        class="column-add"
        @keyup.enter="addToColumn(col)"
      />
    </div>

    <!-- 尾部「添加分组」内联输入（对齐主流待办应用看板：未聚焦=浅灰「＋添加分组」条；聚焦=白底蓝框+下方幽灵列，回车创建；仅清单分组看板） -->
    <div
      v-if="boardKind === 'list' && authStore.hasPerm('task:manage')"
      class="board-column add-column"
      :class="{ active: addGroupMode }"
    >
      <div class="add-group-bar" @click="focusAddGroup">
        <Plus :size="15" class="add-plus" />
        <input
          ref="addGroupInput"
          v-model="newGroupName"
          class="add-group-input"
          :placeholder="addGroupMode ? '' : '添加分组'"
          @focus="addGroupMode = true"
          @blur="onAddGroupBlur"
          @keydown.enter.prevent="submitNewGroup"
          @keydown.esc="cancelNewGroup"
        />
        <X
          v-if="addGroupMode || newGroupName"
          :size="14"
          class="add-x"
          title="取消"
          @mousedown.prevent
          @click="cancelNewGroup"
        />
      </div>
      <div v-if="addGroupMode" class="ghost-body"></div>
    </div>

    <TaskEditDialog ref="editDialog" />
    <TaskContextMenu ref="ctxMenu" />
    <!-- 分组列头右键/⋯ 上下文菜单（与列表视图共用） -->
    <GroupContextMenu ref="groupMenu" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, nextTick } from 'vue'
import { Check, MoreVertical, Plus, ChevronDown, BookOpen, X } from 'lucide-vue-next'
import { ElMessageBox } from 'element-plus'
import draggable from 'vuedraggable'
import dayjs from 'dayjs'
import { useTaskStore } from '@/stores/task'
import { useAuthStore } from '@/stores/auth'
import TaskEditDialog from '../dialogs/TaskEditDialog.vue'
import TaskContextMenu from '../TaskContextMenu.vue'
import GroupContextMenu from '../GroupContextMenu.vue'

const store = useTaskStore()
const authStore = useAuthStore()

// 看板两种模式（对齐主流待办应用）：
// - list：自定义清单 = 清单内分组看板；收集箱且分组=自定义 = 收集箱分组看板（均可管理分组）
// - group：其余所有视图（智能清单/全部/过滤器/标签）= 列维度跟随 ⇅ 分组
const boardKind = computed(() =>
  store.activeListKey.startsWith('list:') ||
  (store.activeListKey === 'smart:inbox' && store.effectiveGroup === 'boardGroup')
    ? 'list'
    : 'group'
)
const groupBy = computed(() => store.effectiveGroup) // time/created/priority/list/tag/none
const isTrash = computed(() => store.activeListKey === 'smart:trash')
// 笔记清单：卡片无勾选、添加文案为「笔记」（对齐主流待办应用笔记看板）
const isNoteList = computed(() => store.activeList?.kind === 'note')

// 当前可管理的自定义分组：清单 → board_groups；收集箱 → inbox_board_groups
const currentBoardGroups = computed(() => {
  if (store.activeListKey.startsWith('list:')) return store.activeList?.board_groups || []
  if (store.activeListKey === 'smart:inbox') return store.inboxGroups || []
  return null
})

// 未分组列/逾期列/无日期列的固定 key
const DEFAULT_KEY = '__default__'
const OVERDUE_KEY = '__overdue__'
const NODATE_KEY = '__nodate__'

// 卡片右键上下文菜单（与列表视图共用）
const ctxMenu = ref(null)
function onContextMenu(task, evt) {
  ctxMenu.value?.open(evt.clientX, evt.clientY, task)
}
const columns = ref([])
const editDialog = ref(null)

function onCardCommand(cmd, task) {
  if (cmd === 'edit') {
    editDialog.value.open(task)
  } else if (cmd === 'delete') {
    ElMessageBox.confirm('确定删除该任务？子任务将一并删除。', '删除任务', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
      .then(() => store.deleteTask(task.id))
      .catch(() => {})
  }
}

// 卡片辅助：清单名 / 标签样式（对齐主流待办应用卡片显示清单名+标签 chip）
function listNameOf(listId) {
  if (!listId) return '收集箱'
  return store.lists.find((l) => l.id === listId)?.name || '清单'
}
function tagStyle(name) {
  const c = store.tags.find((t) => t.name === name)?.color
  return c ? { color: c, background: `${c}1f` } : {}
}

// ---------- 子分组（拖放分区） ----------
// dg = { key, label|null, items, noPut?, pin?, day?, noDate? }
// 落入语义：pin=置顶、day=改期到该天、noDate=清除日期；noPut=不可拖入（已过期等）
const PRIORITY_GROUPS = [
  { p: 3, label: '高优先级' },
  { p: 2, label: '中优先级' },
  { p: 1, label: '低优先级' },
  { p: 0, label: '无优先级' },
]

// 子分组折叠状态（key = `${colKey}:${dgKey}`），重建不丢
const collapsedSubs = ref(new Set())
function toggleSub(colKey, dgKey) {
  const k = `${colKey}:${dgKey}`
  const next = new Set(collapsedSubs.value)
  if (next.has(k)) next.delete(k)
  else next.add(k)
  collapsedSubs.value = next
}
function isSubCollapsed(colKey, dgKey) {
  return collapsedSubs.value.has(`${colKey}:${dgKey}`)
}

// 时间子分组（创建时间/优先级/清单/标签列内，对齐主流待办应用：已置顶 → 已过期 → 按到期日 → 无日期）
function makeTimeGroups(items) {
  const pinned = items.filter((t) => t.is_pinned)
  const overdueItems = items.filter((t) => !t.is_pinned && isOverdue(t))
  const rest = items.filter((t) => !t.is_pinned && !isOverdue(t))
  const byDay = new Map()
  const noDate = []
  for (const t of rest) {
    if (!t.due_at) { noDate.push(t); continue }
    const k = dayjs(t.due_at).startOf('day').format('YYYY-MM-DD')
    if (!byDay.has(k)) byDay.set(k, [])
    byDay.get(k).push(t)
  }
  const subs = []
  if (pinned.length) subs.push({ key: 'pinned', label: '已置顶', pin: true, items: pinned })
  if (overdueItems.length) subs.push({ key: 'overdue', label: '已过期', noPut: true, items: overdueItems })
  for (const [k, arr] of [...byDay.entries()].sort()) {
    subs.push({ key: k, label: dayLabel(dayjs(k)), day: dayjs(k), items: arr })
  }
  if (noDate.length) subs.push({ key: 'nodate', label: '无日期', noDate: true, items: noDate })
  return subs.length ? subs : [{ key: 'flat', label: null, items: [] }]
}

// ---------- ⇅ 排序/顺序：作用于列/子分组内卡片顺序（对齐主流待办应用） ----------
const SORT_VALUE = {
  due: (t) => (t.due_at ? dayjs(t.due_at).valueOf() : null),
  priority: (t) => t.priority || 0,
  title: (t) => t.title || '',
  created: (t) => (t.created_at ? dayjs(t.created_at).valueOf() : 0),
}
function applyZoneSort(items) {
  const { by, order } = store.sortCfg
  const pins = items.filter((t) => t.is_pinned)
  const rest = items.filter((t) => !t.is_pinned)
  if (by !== 'default') {
    const dir = order === 'desc' ? -1 : 1
    const val = SORT_VALUE[by]
    if (val) {
      rest.sort((a, b) => {
        const va = val(a)
        const vb = val(b)
        if (va == null) return 1 // 无值恒沉底
        if (vb == null) return -1
        const cmp = typeof va === 'string' ? va.localeCompare(vb, 'zh') : va - vb
        return cmp * dir
      })
    }
  }
  return [...pins, ...rest]
}

// ---------- 清单模式：列 = 未分组 + 清单内自定义分组（board_groups） ----------
function buildListColumns() {
  const groups = currentBoardGroups.value || []
  const defs = [
    { key: DEFAULT_KEY, name: '未分组', isDefault: true },
    ...groups.map((g) => ({ key: g, name: g, isDefault: false })),
  ]
  columns.value = defs.map((d) => {
    const items = store.tasks
      .filter((t) => (t.group || DEFAULT_KEY) === d.key)
      .sort((a, b) => a.sort_order - b.sort_order)
    // 未分组列按 已置顶/未置顶 分区（对齐主流待办应用看板），拖入分区=置顶/取消置顶；其余组平铺
    let dragGroups
    if (d.isDefault) {
      const pinned = items.filter((t) => t.is_pinned)
      const rest = items.filter((t) => !t.is_pinned)
      dragGroups = pinned.length
        ? [
            { key: 'pinned', label: '已置顶', pin: true, items: pinned },
            { key: 'unpinned', label: '未置顶', unpin: true, items: rest },
          ]
        : [{ key: 'flat', label: null, unpin: true, items }]
    } else {
      dragGroups = [{ key: 'flat', label: null, items }]
    }
    return { ...d, items, dragGroups, newTitle: '' }
  })
}

// ---------- 分组模式 ----------
const isOverdue = (task) =>
  task.status === 'todo' && task.due_at && dayjs(task.due_at).isBefore(dayjs().startOf('day'))

function dayLabel(d) {
  const today = dayjs().startOf('day')
  if (d.isSame(today, 'day')) return '今天'
  if (d.isSame(today.add(1, 'day'), 'day')) return '明天'
  return `${d.format('M月D日')} 周${'日一二三四五六'[d.day()]}`
}

// 分组=时间（默认）：列 = [已过期] + 今天起 N 天 + [无日期]
// 今天/最近7天为固定范围（空天也显示）；其余视图（收集箱/全部等）覆盖到任务最大到期日
function buildTimeColumns() {
  const today = dayjs().startOf('day')
  const key = store.activeListKey
  const cols = []
  const overdue = store.tasks.filter((t) => isOverdue(t))
  if (overdue.length) {
    cols.push({
      key: OVERDUE_KEY, name: '已过期', isOverdue: true, items: overdue,
      dragGroups: [{ key: 'flat', label: null, items: overdue }], newTitle: '',
    })
  }
  let n
  if (key === 'smart:today') n = 1
  else if (key === 'smart:next7') n = 7
  else {
    // 通用视图：今天..最大到期日（无到期任务则仅今天）
    const maxDue = store.tasks
      .filter((t) => t.due_at && !dayjs(t.due_at).isBefore(today, 'day'))
      .reduce((m, t) => Math.max(m, dayjs(t.due_at).startOf('day').valueOf()), 0)
    n = maxDue ? dayjs(maxDue).diff(today, 'day') + 1 : 0
  }
  for (let i = 0; i < n; i++) {
    const d = today.add(i, 'day')
    const items = store.tasks
      .filter((t) => t.due_at && dayjs(t.due_at).isSame(d, 'day'))
      .sort((a, b) => new Date(a.start_at || a.due_at) - new Date(b.start_at || b.due_at))
    cols.push({ key: d.format('YYYY-MM-DD'), name: dayLabel(d), day: d, items, dragGroups: [{ key: 'flat', label: null, items }], newTitle: '' })
  }
  // 无日期列（今天/最近7天服务端已排除无日期任务，不会出现）
  const noDate = store.tasks.filter((t) => !t.due_at)
  if (noDate.length) {
    cols.push({
      key: NODATE_KEY, name: '无日期', noDateCol: true, items: noDate,
      dragGroups: [{ key: 'flat', label: null, items: noDate }], newTitle: '',
    })
  }
  columns.value = cols
}

// 分组=创建时间（对齐主流待办应用）：列 = 过去7天 / 过去30天 / 更早（仅非空）；
// 创建时间不可改 → 列间不可拖，列内按时间子分组（已置顶/已过期/按天/无日期）可拖改期
function buildCreatedColumns() {
  const today = dayjs().startOf('day')
  const w1 = today.subtract(7, 'day')
  const m1 = today.subtract(30, 'day')
  const buckets = [
    { key: 'w1', name: '过去7天', test: (c) => c.isAfter(w1) },
    { key: 'm1', name: '过去30天', test: (c) => c.isAfter(m1) && !c.isAfter(w1) },
    { key: 'old', name: '更早', test: (c) => !c.isAfter(m1) },
  ]
  const cols = []
  for (const b of buckets) {
    const items = store.tasks
      .filter((t) => b.test(dayjs(t.created_at || t.due_at)))
      .sort((a, b2) => new Date(a.due_at) - new Date(b2.due_at))
    if (!items.length) continue
    cols.push({
      key: b.key, name: b.name, createdBucket: true, items,
      dragGroups: makeTimeGroups(items), newTitle: '',
    })
  }
  columns.value = cols
}

// 分组=优先级（对齐主流待办应用）：列 = 高/中/低/无优先级（仅非空）；
// 列内按时间子分组，跨列拖=改优先级，列内跨子组=置顶/改期
function buildPriorityColumns() {
  const cols = []
  for (const g of PRIORITY_GROUPS) {
    const items = store.tasks
      .filter((t) => (t.priority || 0) === g.p)
      .sort((a, b) => new Date(a.start_at || a.due_at || a.created_at) - new Date(b.start_at || b.due_at || b.created_at))
    // 优先级列四档恒显（含空列）：可直接拖入/列底添加到中、低优先级
    cols.push({
      key: `p${g.p}`, name: g.label, prioBucket: true, prio: g.p, items,
      dragGroups: makeTimeGroups(items), newTitle: '',
    })
  }
  columns.value = cols
}

// 分组=清单（对齐主流待办应用）：列 = 收集箱 + 各自定义清单（仅非空，侧栏顺序）；
// 列内按时间子分组，跨列拖=移动清单（收集箱列=list_id null）
function buildListDimColumns() {
  const defs = [
    { key: 'inbox', name: '收集箱', listId: null },
    ...store.lists.map((l) => ({ key: l.id, name: l.name, listId: l.id, color: l.color })),
  ]
  const cols = []
  for (const d of defs) {
    const items = store.tasks.filter((t) => (t.list_id || null) === d.listId)
    if (!items.length) continue
    cols.push({
      ...d, listDim: true, items,
      dragGroups: makeTimeGroups(items), newTitle: '',
    })
  }
  columns.value = cols
}

// 分组=标签（对齐主流待办应用）：列 = 各首标签（中文排序）+ 无标签沉底（仅非空）；
// 列内按时间子分组，跨列拖=该标签置顶为首要标签（落「无标签」列=清空标签）
function buildTagColumns() {
  const names = [...new Set(store.tasks.map((t) => t.tags?.[0]).filter(Boolean))].sort((a, b) => a.localeCompare(b, 'zh'))
  const defs = [...names.map((n) => ({ key: n, name: n, tagName: n })), { key: '__notag__', name: '无标签', tagName: null }]
  const cols = []
  for (const d of defs) {
    const items = store.tasks.filter((t) => (t.tags?.[0] || null) === d.tagName)
    if (!items.length) continue
    cols.push({
      ...d, tagDim: true, items,
      dragGroups: makeTimeGroups(items), newTitle: '',
    })
  }
  columns.value = cols
}

// 分组=无：单列平铺
function buildFlatColumns() {
  const items = [...store.tasks]
  columns.value = [{
    key: 'all', name: store.activeTitle, items,
    dragGroups: [{ key: 'flat', label: null, items }], newTitle: '',
  }]
}

// 分组=自定义（智能视图，如今天/最近7天）：列=未分组 + 当前任务 group 名并集
// 只读展示（对齐主流待办应用「智能清单不支持创建分组」）：无列头 ⋯、无列底添加、无尾部添加分组；
// 跨列拖=改 group（目标组须属于任务所在清单/收集箱的分组，否则后端 400 → 还原）
function buildCustomDimColumns() {
  const rank = new Map()
  store.inboxGroups.forEach((g, gi) => rank.set(g, gi))
  store.lists.forEach((l, li) =>
    (l.board_groups || []).forEach((g, gi) => {
      if (!rank.has(g)) rank.set(g, 1000 + li * 100 + gi)
    })
  )
  const names = new Set()
  for (const t of store.tasks) if (t.group) names.add(t.group)
  const sorted = [...names].sort((a, b) => (rank.get(a) ?? 99999) - (rank.get(b) ?? 99999) || a.localeCompare(b, 'zh'))
  const defs = [{ key: DEFAULT_KEY, name: '未分组', isDefault: true }, ...sorted.map((g) => ({ key: g, name: g }))]
  columns.value = defs.map((d) => {
    const items = store.tasks.filter((t) => (t.group || DEFAULT_KEY) === d.key)
    return {
      ...d, customDim: true, noAdd: true, items,
      dragGroups: makeTimeGroups(items), newTitle: '',
    }
  })
}

function buildColumns() {
  if (boardKind.value === 'list') buildListColumns()
  else if (groupBy.value === 'created') buildCreatedColumns()
  else if (groupBy.value === 'priority') buildPriorityColumns()
  else if (groupBy.value === 'list') buildListDimColumns()
  else if (groupBy.value === 'tag') buildTagColumns()
  else if (groupBy.value === 'boardGroup') buildCustomDimColumns()
  else if (groupBy.value === 'none') buildFlatColumns()
  else buildTimeColumns()
  // ⇅ 排序/顺序作用于每个拖放分区内（默认=保持各列构建口径）
  if (store.sortCfg.by !== 'default') {
    for (const col of columns.value) {
      col.items = applyZoneSort(col.items)
      for (const dg of col.dragGroups) dg.items = applyZoneSort(dg.items)
    }
  }
}

watch(() => [store.tasks, store.activeList, store.settings, boardKind.value, store.effectiveGroup, store.sortCfg], buildColumns, { immediate: true, deep: true })

async function onDragEnd(evt) {
  const taskId = evt.item.dataset.id
  if (!taskId) return
  const findCol = (key) => columns.value.find((c) => c.key === key)
  const findDg = (col, key) => col?.dragGroups.find((g) => g.key === key)
  const fromCol = findCol(evt.from.dataset.colKey)
  let toCol = findCol(evt.to.dataset.colKey)
  const fromDg = findDg(fromCol, evt.from.dataset.dgKey)
  let toDg = findDg(toCol, evt.to.dataset.dgKey)
  // Sortable 拖拽途中会把卡片实时插入经过的合法容器；若最终落点在不可放区（逾期列/已过期子组），
  // evt.to 会是「途中经过的最后一列」而非指针真实落点 → 以指针坐标下的真实分区为准
  const oe = evt.originalEvent
  const hit = oe && document.elementFromPoint(oe.clientX, oe.clientY)
  const realZone = hit?.closest?.('.drag-zone')
  if (realZone && realZone !== evt.to) {
    toCol = findCol(realZone.dataset.colKey)
    toDg = findDg(toCol, realZone.dataset.dgKey)
  }
  // 非法落点（逾期列/已过期子组/不存在）：重建还原
  if (!toCol || !toDg || toCol.isOverdue || toDg.noPut) {
    buildColumns()
    return
  }

  if (boardKind.value === 'list') {
    const task = store.tasks.find((t) => t.id === taskId)
    if (fromCol !== toCol) {
      // 跨列=改分组；落点分区带置顶语义（未分组列 已置顶/未置顶 分区）时一并应用
      const payload = { group: toCol.isDefault ? null : toCol.key }
      if (toDg.pin) payload.is_pinned = true
      else if (toDg.unpin) payload.is_pinned = false
      await store.updateTask(taskId, payload)
    } else if (toDg.pin && task && !task.is_pinned) {
      await store.updateTask(taskId, { is_pinned: true }) // 拖入已置顶分区
    } else if (toDg.unpin && task && task.is_pinned) {
      await store.updateTask(taskId, { is_pinned: false }) // 拖回未置顶分区
    } else {
      await sortWithin(toDg, taskId)
    }
    return
  }

  // 分组看板：跨列=改列维度属性，跨子组=改时间属性（对齐主流待办应用「拖到对应区域智能修改属性」）
  const task = store.tasks.find((t) => t.id === taskId)
  // 创建时间列：列间不可拖（创建时间是历史事实），直接还原
  if (toCol.createdBucket && fromCol !== toCol) {
    buildColumns()
    return
  }
  const payload = {}
  let moveTo
  // 子组语义（已置顶/某天/无日期）
  const subChanged = fromCol !== toCol || fromDg.key !== toDg.key
  if (subChanged) {
    if (toDg.pin && !task?.is_pinned) payload.is_pinned = true
    else if (toDg.day) payload.due_at = keepTimeOn(task, toDg.day)
    else if (toDg.noDate) { payload.due_at = null; payload.start_at = null }
  }
  // 列语义
  if (toCol.prioBucket && fromCol !== toCol && (task?.priority || 0) !== toCol.prio) {
    payload.priority = toCol.prio
  } else if (toCol.listDim && fromCol !== toCol && (task?.list_id || null) !== toCol.listId) {
    moveTo = toCol.listId // 收集箱列 = null
  } else if (toCol.tagDim && fromCol !== toCol) {
    const cur = task?.tags || []
    const next = toCol.tagName ? [toCol.tagName, ...cur.filter((t) => t !== toCol.tagName)] : []
    if (JSON.stringify(next) !== JSON.stringify(cur)) payload.tags = next
  } else if (toCol.customDim && fromCol !== toCol) {
    // 自定义分组并集列（智能视图）：跨列=改 group（目标组须属于任务所在清单/收集箱）
    const nextGroup = toCol.isDefault ? null : toCol.key
    if ((task?.group || null) !== nextGroup) payload.group = nextGroup
  } else if (toCol.day && fromCol !== toCol) {
    payload.due_at = keepTimeOn(task, toCol.day)
  } else if (toCol.noDateCol && fromCol !== toCol) {
    payload.due_at = null
    payload.start_at = null
  }

  try {
    if (moveTo !== undefined) await store.move(taskId, moveTo)
    if (Object.keys(payload).length) {
      await store.updateTask(taskId, payload)
    } else if (moveTo === undefined && fromCol === toCol && fromDg === toDg) {
      await sortWithin(toDg, taskId)
    } else if (moveTo === undefined && !Object.keys(payload).length) {
      buildColumns() // 跨子组但无语义（如已置顶任务拖到日期组）：还原
    }
  } catch {
    buildColumns() // 落库失败（如目标分组不属于任务所在清单，拦截器已弹提示）→ 还原 DOM
  }
  // store.tasks 更新后 watch 自动重建列
}

// 改期到目标天并保留原时间（无原时间默认 09:00，全天任务保持全天标记）
function keepTimeOn(task, day) {
  const old = dayjs(task?.due_at)
  return day.hour(old.isValid() ? old.hour() : 9).minute(old.isValid() ? old.minute() : 0).second(0).toISOString()
}

async function sortWithin(dg, taskId) {
  const idx = dg.items.findIndex((t) => t.id === taskId)
  if (idx === -1) return
  const payload =
    idx < dg.items.length - 1
      ? { before_task_id: dg.items[idx + 1].id }
      : { sort_order: (dg.items[idx - 1]?.sort_order || 0) + 1024 }
  await store.sort(taskId, payload)
}

async function addToColumn(col) {
  const title = col.newTitle.trim()
  if (!title) return
  if (boardKind.value === 'list') {
    // 清单视图带清单 id；收集箱（inbox 自定义分组列）显式 null（防默认值清单注入）
    const lst = store.activeList
    if (!lst && store.activeListKey !== 'smart:inbox') return
    await store.createTask(
      store.applyDefaults({ title, list_id: lst ? lst.id : null, group: col.isDefault ? null : col.key })
    )
  } else {
    // 分组看板：带上列维度属性（时间列落目标天；创建时间/优先级列落今天 09:00，同日历视图）
    const data = { title }
    if (col.day) data.due_at = col.day.hour(9).minute(0).second(0).toISOString()
    else if (col.createdBucket || col.prioBucket) {
      data.due_at = dayjs().startOf('day').hour(9).minute(0).second(0).toISOString()
    }
    if (col.prioBucket) data.priority = col.prio
    if (col.listDim) data.list_id = col.listId // 收集箱列 = null（显式，防默认值清单注入）
    if (col.tagDim && col.tagName) data.tags = [col.tagName]
    await store.createTask(store.applyDefaults(data))
    // 智能清单为服务端过滤（smart 条件本地不可靠预判），刷新以显示新任务
    await store.fetchTasks()
  }
  col.newTitle = ''
}

// ---------- 分组管理（仅清单模式） ----------
// 列头「+」：展开列顶添加框（按列 key 记录，buildColumns 重建后不丢失，回车可连续添加）
const addOpenKeys = reactive(new Set())
function openAdd(col) {
  addOpenKeys.add(col.key)
}

// ---------- 列头 ⋯/右键菜单（与列表视图同一 GroupContextMenu） ----------
const groupMenu = ref(null)
function canManageCol(col) {
  return boardKind.value === 'list' && !col.isDefault && !col.isOverdue && authStore.hasPerm('task:manage')
}
// ⋯ 点击：菜单锚定在按钮下方
function openColMenu(e, col) {
  const rect = e.currentTarget.getBoundingClientRect()
  groupMenu.value?.open(rect.left, rect.bottom + 6, col)
}
// 列头右键：菜单跟随光标
function onColContextMenu(e, col) {
  if (!canManageCol(col)) return
  e.preventDefault()
  groupMenu.value?.open(e.clientX, e.clientY, col)
}

// ---------- 尾部「添加分组」内联输入（对齐主流待办应用看板） ----------
const addGroupMode = ref(false)
const newGroupName = ref('')
const addGroupInput = ref(null)
let addGroupBlurTimer = null
// TaskManager ⋯ 菜单入口：聚焦内联输入框
async function addGroup() {
  addGroupMode.value = true
  await nextTick()
  addGroupInput.value?.focus()
}
// 点击整条输入带 = 聚焦输入框（扩大命中区域，对齐主流待办应用整块可点）
function focusAddGroup() {
  addGroupMode.value = true
  nextTick(() => addGroupInput.value?.focus())
}
// 失焦延迟收起：给「✕」的 click 留一拍（mousedown 已阻止失焦，这里兜底）
function onAddGroupBlur() {
  clearTimeout(addGroupBlurTimer)
  addGroupBlurTimer = setTimeout(() => {
    if (!newGroupName.value.trim()) {
      addGroupMode.value = false
      newGroupName.value = ''
    }
  }, 150)
}
async function submitNewGroup() {
  const name = newGroupName.value.trim()
  if (!name) return
  try {
    await store.addBoardGroup(name)
    newGroupName.value = '' // 清空并保持聚焦，可连续添加
    nextTick(() => addGroupInput.value?.focus())
  } catch {
    // 失败由请求拦截器统一提示（如分组名已存在）
  }
}
function cancelNewGroup() {
  clearTimeout(addGroupBlurTimer)
  newGroupName.value = ''
  addGroupMode.value = false
  addGroupInput.value?.blur()
}

defineExpose({ addGroup })
</script>

<style scoped>
.task-board-view {
  display: flex;
  gap: 12px;
  height: 100%;
  overflow-x: auto;
  padding-bottom: 8px;
}
.board-column {
  width: 260px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--ss-bg);
  border-radius: var(--ss-radius);
  padding: 10px;
}
.column-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 4px 10px;
  font-size: 14px;
  font-weight: 500;
}
.col-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.column-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.column-name.is-overdue {
  color: #f56c6c;
}
.column-count {
  font-size: 12px;
  color: var(--ss-text-muted);
}
/* 列头「+」：常显，点击在列顶展开添加框（对齐主流待办应用） */
.add-icon {
  color: var(--ss-text-muted);
  cursor: pointer;
  border-radius: 4px;
  padding: 1px;
  flex-shrink: 0;
}
.add-icon:hover {
  color: var(--ss-text);
  background: var(--ss-bg-hover, rgba(0, 0, 0, 0.06));
}
.top-add {
  margin: 0 0 8px;
}
.column-header:hover .column-more {
  color: var(--ss-text);
}
/* 尾部「添加分组」内联列（对齐主流待办应用看板）：未聚焦=浅灰「＋添加分组」条；聚焦=白底蓝框 + 下方幽灵列 */
.add-column {
  background: transparent;
  padding: 0;
}
.add-group-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 38px;
  padding: 0 10px;
  border: 1.5px solid transparent;
  border-radius: var(--ss-radius);
  background: var(--ss-bg);
  cursor: pointer;
  flex-shrink: 0;
}
.add-column.active .add-group-bar {
  background: #fff;
  border-color: var(--ss-primary);
  cursor: text;
}
.add-plus {
  color: var(--ss-primary);
  flex-shrink: 0;
}
.add-group-input {
  flex: 1;
  min-width: 0;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  font-family: inherit;
  color: var(--ss-text);
}
.add-group-input::placeholder {
  color: var(--ss-primary);
  opacity: 0.85;
}
.add-x {
  color: var(--ss-text-muted);
  cursor: pointer;
  flex-shrink: 0;
  border-radius: 50%;
  padding: 1px;
}
.add-x:hover {
  color: var(--ss-text);
}
/* 聚焦后出现的幽灵列体：示意新分组落位 */
.ghost-body {
  flex: 1;
  min-height: 320px;
  margin-top: 10px;
  border-radius: var(--ss-radius);
  background: var(--ss-bg);
}
.column-body {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.drag-zone {
  min-height: 60px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  flex-shrink: 0;
}
/* 子分组头（对齐主流待办应用看板列内分组：▾ 名称 + 计数，点击折叠） */
.sub-header {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 2px 4px;
  font-size: 13px;
  color: var(--ss-text-secondary);
  cursor: pointer;
  user-select: none;
  flex-shrink: 0;
}
.sub-arrow {
  transition: transform 0.15s;
  flex-shrink: 0;
}
.sub-arrow.collapsed {
  transform: rotate(-90deg);
}
.sub-count {
  font-size: 12px;
  color: var(--ss-text-muted);
}
.column-body .sub-header + .drag-zone {
  min-height: 40px;
  margin-bottom: 4px;
}
.board-card {
  background: #fff;
  border: 1px solid var(--ss-border);
  border-radius: var(--ss-radius-sm);
  padding: 10px;
  cursor: pointer;
}
.board-card:hover {
  box-shadow: var(--ss-shadow);
}
.card-top {
  display: flex;
  align-items: center;
  gap: 8px;
}
.card-note-flag {
  color: var(--ss-primary);
  flex-shrink: 0;
}
.check-dot {
  width: 16px;
  height: 16px;
  border: 2px solid var(--ss-text-muted);
  /* 对齐主流待办应用：看板 = 正圆勾选框（四象限才是圆角方块） */
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 11px;
  cursor: pointer;
}
.check-dot.checked {
  background: var(--ss-primary);
  border-color: var(--ss-primary);
}
.card-title {
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-title.done {
  text-decoration: line-through;
  color: var(--ss-text-muted);
}
/* 标签 chip（对齐主流待办应用看板卡片） */
.card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;
}
.card-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--ss-bg);
  color: var(--ss-text-secondary);
}
.card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 6px;
  font-size: 12px;
  color: var(--ss-text-secondary);
}
.priority-bar {
  width: 14px;
  height: 4px;
  border-radius: 2px;
}
.priority-bar.p3 { background: #f56c6c; }
.priority-bar.p2 { background: #e6a23c; }
.priority-bar.p1 { background: #409eff; }
.priority-bar.p0 { background: transparent; }
.card-due.overdue {
  color: #f56c6c;
}
.card-sub {
  color: var(--ss-text-muted);
}
.card-list {
  color: var(--ss-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.card-more {
  margin-left: auto;
  visibility: hidden;
  flex-shrink: 0;
}
.board-card:hover .card-more {
  visibility: visible;
}
.more-icon {
  color: var(--ss-text-muted);
  flex-shrink: 0;
}
.card-ghost {
  opacity: 0.4;
}
.column-add {
  margin-top: 8px;
}
</style>
