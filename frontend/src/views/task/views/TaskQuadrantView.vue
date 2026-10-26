<template>
  <!-- 四象限独立内容页（对齐主流待办应用桌面端：每象限 = 边界卡片，卡头悬停出 ＋/⋯；
       ＋/点击任务行 = 悬浮任务卡片（新增/编辑共用，回车保存）；拖拽换象限） -->
  <div ref="quadrantEl" class="quadrant">
    <div class="q-grid">
      <section
        v-for="q in QUADRANTS"
        :key="q.key"
        class="q-cell"
        :class="{ dropover: dragOver === q.key }"
        @dragover.prevent="dragOver = q.key"
        @dragleave="dragOver = null"
        @drop.prevent="onDrop(q.key)"
      >
        <header class="q-head">
          <span class="q-badge" :style="{ background: q.color }">{{ q.numeral }}</span>
          <span class="q-label" :style="{ color: q.color }">{{ q.label }}</span>
          <span class="q-count">{{ tasksOf(q.key).length }}</span>
          <span class="q-head-tools">
            <el-popover
              :visible="addOpen && addFor === q.key"
              :width="440"
              trigger="manual"
              placement="bottom-start"
              popper-class="q-addpop"
              @update:visible="(v) => { if (!v) addOpen = false }"
            >
              <template #reference>
                <span class="q-tool-btn" :title="`添加任务到「${q.label}」`" @click="startAdd(q)">
                  <Plus :size="14" />
                </span>
              </template>
              <QuadrantTaskCard
                v-model:text="addText"
                v-model:due="addDue"
                :priority="addPriority"
                v-model:list-id="addListId"
                :lists="store.lists"
                @cycle-priority="cyclePriority('add')"
                @enter="onAdd"
                @more="onAddMore"
              />
            </el-popover>
            <el-dropdown trigger="click" placement="bottom-end">
              <span class="q-tool-btn" title="更多"><MoreHorizontal :size="14" /></span>
              <template #dropdown>
                <div class="qm-panel">
                  <div class="qm-row" @mouseenter="sub = 'group'" @click="sub = 'group'">
                    <Rows3 :size="14" class="qm-icon" /><span>分组</span>
                    <span class="qm-val">{{ groupLabel }}<ChevronRight :size="12" /></span>
                    <div v-show="sub === 'group'" class="qm-sub">
                      <div v-for="o in GROUP_OPTS" :key="o.value" class="qm-opt" @click="setSort('group', o.value)">
                        <Check v-if="sortCfg.group === o.value" :size="13" class="qm-check" />
                        <span v-else class="qm-check-blank" />{{ o.label }}
                      </div>
                    </div>
                  </div>
                  <div class="qm-row" @mouseenter="sub = 'sort'" @click="sub = 'sort'">
                    <ListOrdered :size="14" class="qm-icon" /><span>排序</span>
                    <span class="qm-val">{{ sortLabel }}<ChevronRight :size="12" /></span>
                    <div v-show="sub === 'sort'" class="qm-sub">
                      <div v-for="o in SORT_OPTS" :key="o.value" class="qm-opt" @click="setSort('sort', o.value)">
                        <Check v-if="sortCfg.sort === o.value" :size="13" class="qm-check" />
                        <span v-else class="qm-check-blank" />{{ o.label }}
                      </div>
                    </div>
                  </div>
                  <div class="qm-row" @mouseenter="sub = 'order'" @click="sub = 'order'">
                    <ArrowUpDown :size="14" class="qm-icon" /><span>顺序</span>
                    <span class="qm-val">{{ orderLabel }}<ChevronRight :size="12" /></span>
                    <div v-show="sub === 'order'" class="qm-sub">
                      <div v-for="o in ORDER_OPTS" :key="o.value" class="qm-opt" @click="setSort('order', o.value)">
                        <Check v-if="sortCfg.order === o.value" :size="13" class="qm-check" />
                        <span v-else class="qm-check-blank" />{{ o.label }}
                      </div>
                    </div>
                  </div>
                  <div class="qm-row" @click="toggleHideDone()">
                    <component :is="hideDone ? CheckSquare : Square" :size="14" class="qm-icon" />
                    <span>隐藏已完成</span>
                  </div>
                  <div class="qm-row" @click="rulesOpen = true">
                    <PencilLine :size="14" class="qm-icon" /><span>编辑规则</span>
                  </div>
                  <div class="qm-row" @click="guideOpen = true">
                    <CircleHelp :size="14" class="qm-icon" /><span>使用指南</span>
                  </div>
                </div>
              </template>
            </el-dropdown>
          </span>
        </header>

        <div class="q-body">
          <template v-for="g in groupsOf(q.key)" :key="g.key">
            <div v-if="g.label" class="q-group-head" @click="toggleGroup(g.key)">
              <span class="q-caret" :class="{ open: !collapsed.has(g.key) }">›</span>
              <span class="q-group-name">{{ g.label }}</span>
              <span class="q-count">{{ g.tasks.length }}</span>
            </div>
            <div v-if="!g.label || !collapsed.has(g.key)" class="q-rows">
              <div
                v-for="t in g.tasks"
                :key="t.id"
                class="q-row"
                :class="{ done: t.status === 'done' }"
                :draggable="t.status !== 'done'"
                @click="openEdit(t, $event)"
                @dragstart="onDragStart(t, $event)"
                @dragend="dragOver = null"
                @contextmenu.prevent="ctxMenu?.open($event.clientX, $event.clientY, t)"
              >
                <span class="q-check" :class="{ on: t.status === 'done', overdue: isOverdue(t) }" @click.stop="onComplete(t)">
                  <Check v-if="t.status === 'done'" :size="11" />
                </span>
                <span class="q-title">{{ t.title }}</span>
                <span v-for="tag in (t.tags || []).slice(0, 3)" :key="tag" class="q-tag">{{ tag }}</span>
                <span class="q-meta">
                  <span class="q-list">{{ listName(t.list_id) }}</span>
                  <span v-if="dueLabel(t)" class="q-due" :class="{ overdue: isOverdue(t) }">{{ dueLabel(t) }}</span>
                </span>
              </div>
            </div>
          </template>
          <div v-if="!groupsOf(q.key).length" class="q-empty">没有任务</div>
        </div>
      </section>
    </div>

    <!-- 任务编辑卡片（点击已有任务行弹出，锚定该行；新增/编辑共用布局，回车保存） -->
    <div
      v-if="editTask"
      class="q-edit-anchor"
      :style="{ left: anchor.x + 'px', top: anchor.y + 'px' }"
    >
      <el-popover
        :visible="true"
        trigger="manual"
        placement="bottom-start"
        :width="440"
        popper-class="q-addpop"
        @update:visible="(v) => { if (!v) editTask = null }"
      >
        <template #reference><span class="q-anchor-dot"></span></template>
        <QuadrantTaskCard
          v-model:text="editText"
          v-model:due="editDue"
          :priority="editPriority"
          v-model:list-id="editListId"
          :lists="store.lists"
          deletable
          @cycle-priority="cyclePriority('edit')"
          @enter="saveEdit"
          @more="onEditMore"
        />
      </el-popover>
    </div>

    <!-- 编辑规则：可编辑配置（参与清单 / 紧急天数），改动即时生效并保存本地 -->
    <el-dialog v-model="rulesOpen" title="象限规则" width="460px">
      <div class="q-rules">
        <div class="q-rule-field">
          <div class="q-rule-label">参与清单</div>
          <el-select
            v-model="form.lists"
            multiple
            collapse-tags
            :collapse-tags-tooltip="true"
            placeholder="不选 = 全部清单"
            class="q-rule-select"
          >
            <el-option v-for="l in store.lists" :key="l.id" :label="l.name" :value="l.id" />
          </el-select>
          <div class="q-rule-hint">不选 = 全部清单都参与象限划分；选中则仅所选清单参与</div>
        </div>
        <div class="q-rule-field">
          <div class="q-rule-label">紧急判定</div>
          <div class="q-rule-days">
            <span>截止日期在</span>
            <el-input-number
              v-model="form.urgentDays"
              :min="1"
              :max="30"
              :precision="0"
              controls-position="right"
              class="q-rule-num"
            />
            <span>天内（含已逾期）视为紧急</span>
          </div>
        </div>
        <div class="q-rule-live">
          <div class="q-rule-scope">规则预览（参与清单：{{ listsPreview }}）</div>
          <div v-for="r in liveRules" :key="r.q" class="q-rule-row">
            <span class="q-badge" :style="{ background: r.color }">{{ r.numeral }}</span>
            <div>
              <div class="q-rule-name">{{ r.q }}</div>
              <div class="q-rule-desc">{{ r.rule }}</div>
            </div>
          </div>
        </div>
        <div class="q-rule-note">
          象限由优先级与截止日期推导，拖拽/添加任务会自动调整这两项属性。以上配置即时生效，保存在此浏览器本地（localStorage），不影响其他设备。
        </div>
      </div>
      <template #footer>
        <el-button @click="resetRules">恢复默认</el-button>
        <el-button type="primary" @click="rulesOpen = false">完成</el-button>
      </template>
    </el-dialog>

    <!-- 使用指南 -->
    <el-dialog v-model="guideOpen" title="四象限使用指南" width="460px">
      <div class="q-guide">
        <p>四象限按「重要 × 紧急」两个维度把所有任务分成 4 格，帮助你决定精力分配：</p>
        <ol>
          <li><b style="color:#f56c6c">重要且紧急</b>——立马去做。</li>
          <li><b style="color:#e6a23c">重要不紧急</b>——重点关注，提前计划安排。</li>
          <li><b style="color:#409eff">不重要但紧急</b>——状态低时做，或委派他人。</li>
          <li><b style="color:#67c23a">不重要不紧急</b>——尽量少做。</li>
        </ol>
      </div>
    </el-dialog>

    <TaskContextMenu ref="ctxMenu" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus, MoreHorizontal, Check, PencilLine, Rows3, ListOrdered, ArrowUpDown,
  CheckSquare, Square, CircleHelp, ChevronRight,
} from 'lucide-vue-next'
import dayjs from 'dayjs'
import { useTaskStore } from '@/stores/task'
import { fetchTasks, deleteTask } from '@/api/task'
import TaskContextMenu from '../TaskContextMenu.vue'
import QuadrantTaskCard from './QuadrantTaskCard.vue'

const store = useTaskStore()
const tzOffsetMinutes = -new Date().getTimezoneOffset()

// 对齐主流待办应用：Ⅰ 重要且紧急 / Ⅱ 重要不紧急 / Ⅲ 不重要但紧急 / Ⅳ 不重要不紧急
const QUADRANTS = [
  { key: 'q1', label: '重要且紧急', numeral: 'Ⅰ', color: '#f56c6c' },
  { key: 'q2', label: '重要不紧急', numeral: 'Ⅱ', color: '#e6a23c' },
  { key: 'q3', label: '不重要但紧急', numeral: 'Ⅲ', color: '#409eff' },
  { key: 'q4', label: '不重要不紧急', numeral: 'Ⅳ', color: '#67c23a' },
]
// 时间分组（对齐主流待办应用：已置顶 / 已过期 / 今天 / 明天 / 一周内 / 以后 / 无日期）
const TIME_GROUPS = [
  { key: 'pinned', label: '已置顶' },
  { key: 'overdue', label: '已过期' },
  { key: 'today', label: '今天' },
  { key: 'tomorrow', label: '明天' },
  { key: 'week', label: '一周内' },
  { key: 'later', label: '以后' },
  { key: 'nodate', label: '无日期' },
]
const PRIORITY_GROUPS = [
  { key: 'p3', label: '高优先级', match: (t) => t.priority >= 3 },
  { key: 'p2', label: '中优先级', match: (t) => t.priority === 2 },
  { key: 'p1', label: '低优先级', match: (t) => t.priority === 1 },
  { key: 'p0', label: '无优先级', match: (t) => t.priority === 0 },
]
const GROUP_OPTS = [
  { value: 'time', label: '时间' },
  { value: 'list', label: '清单' },
  { value: 'priority', label: '优先级' },
  { value: 'none', label: '无' },
]
const SORT_OPTS = [
  { value: 'time', label: '时间' },
  { value: 'priority', label: '优先级' },
  { value: 'title', label: '标题' },
  { value: 'default', label: '默认' },
]
const ORDER_OPTS = [
  { value: 'asc', label: '从旧到新' },
  { value: 'desc', label: '从新到旧' },
]

const SORT_KEY = 'quadrant_sort'
const sortCfg = ref({ group: 'time', sort: 'time', order: 'asc', ...(JSON.parse(localStorage.getItem(SORT_KEY) || '{}')) })
const groupLabel = computed(() => GROUP_OPTS.find((o) => o.value === sortCfg.value.group)?.label)
const sortLabel = computed(() => SORT_OPTS.find((o) => o.value === sortCfg.value.sort)?.label)
const orderLabel = computed(() => ORDER_OPTS.find((o) => o.value === sortCfg.value.order)?.label)
const sub = ref('')
function setSort(k, v) {
  sortCfg.value = { ...sortCfg.value, [k]: v }
  localStorage.setItem(SORT_KEY, JSON.stringify(sortCfg.value))
}

const tasks = ref([])
// 编辑规则配置：参与清单（空=全部）、紧急天数、隐藏已完成；本地持久化即时生效
const CFG_KEY = 'quadrant_cfg_v1'
const cfg = ref({ lists: [], urgentDays: 7, hideDone: true, ...(JSON.parse(localStorage.getItem(CFG_KEY) || '{}')) })
const form = reactive({ lists: [...(cfg.value.lists || [])], urgentDays: cfg.value.urgentDays ?? 7 })
const hideDone = ref(cfg.value.hideDone !== false)
function saveCfg(patch = {}) {
  cfg.value = { ...cfg.value, ...patch }
  localStorage.setItem(CFG_KEY, JSON.stringify(cfg.value))
}
watch(
  [() => form.lists, () => form.urgentDays],
  () => {
    saveCfg({ lists: [...form.lists], urgentDays: form.urgentDays })
    reload()
  },
  { deep: true }
)
const listsPreview = computed(() => (form.lists.length ? `已选 ${form.lists.length} 个清单` : '全部清单'))
const liveRules = computed(() => {
  const urgent = `截止临近（${form.urgentDays} 天内或已逾期，高优先级恒紧急）`
  return [
    { q: '重要且紧急', numeral: 'Ⅰ', color: '#f56c6c', rule: `优先级「中/高」+ ${urgent}` },
    { q: '重要不紧急', numeral: 'Ⅱ', color: '#e6a23c', rule: `优先级「中/高」+ 无截止或截止在 ${form.urgentDays} 天以外` },
    { q: '不重要但紧急', numeral: 'Ⅲ', color: '#409eff', rule: `优先级「低/无」+ ${urgent}` },
    { q: '不重要不紧急', numeral: 'Ⅳ', color: '#67c23a', rule: '优先级「低/无」+ 无截止或截止较远' },
  ]
})
function resetRules() {
  form.lists = []
  form.urgentDays = 7
}
const collapsed = ref(new Set())
const dragOver = ref(null)
const rulesOpen = ref(false)
const guideOpen = ref(false)
const ctxMenu = ref(null)
const quadrantEl = ref(null)
let _dragTaskId = null

// ---------- ＋ 新增卡片 ----------
const addOpen = ref(false)
const addFor = ref(null)
const addText = ref('')
const addDue = ref('')
const addPriority = ref(0)
const addListId = ref(null)
const addTags = ref([])

function startAdd(q) {
  const attrs = attrsForQuadrant(q.key)
  addFor.value = q.key
  addPriority.value = attrs.priority
  addDue.value = attrs.due_at ? dayjs(attrs.due_at).format('YYYY-MM-DD') : ''
  addText.value = ''
  addListId.value = null
  addTags.value = []
  addOpen.value = true
}

async function onAdd() {
  const title = addText.value.trim()
  if (!title) return
  const due_at = addDue.value ? dayjs(addDue.value).startOf('day').toISOString() : null
  await store
    .createTask({
      title,
      list_id: addListId.value,
      priority: addPriority.value,
      due_at,
      all_day: true,
      tags: addTags.value,
    })
    .catch(() => {})
  ElMessage.success('已创建')
  addOpen.value = false
  addFor.value = null
  addText.value = ''
  addDue.value = ''
  addPriority.value = 0
  addListId.value = null
  addTags.value = []
  reload()
}

function onAddMore(cmd) {
  if (cmd === 'tag') return inputTags(addTags)
  if (cmd === 'clearDue') addDue.value = ''
}

// ---------- 点击任务行 = 编辑卡片（对齐主流待办应用：已有任务也走悬浮卡片） ----------
const editTask = ref(null)
const editText = ref('')
const editDue = ref('')
const editPriority = ref(0)
const editListId = ref(null)
const editTags = ref([])
const anchor = ref({ x: 0, y: 0 })

function openEdit(t, e) {
  editTask.value = t
  editText.value = t.title
  editDue.value = t.due_at ? dayjs(t.due_at).format('YYYY-MM-DD') : ''
  editPriority.value = t.priority || 0
  editListId.value = t.list_id || null
  editTags.value = [...(t.tags || [])]
  const rect = quadrantEl.value?.getBoundingClientRect()
  anchor.value = { x: (e.clientX || rect?.left || 0) - (rect?.left || 0), y: (e.clientY || 0) - (rect?.top || 0) }
}

async function saveEdit() {
  const t = editTask.value
  const title = editText.value.trim()
  if (!t || !title) return
  const due_at = editDue.value ? dayjs(editDue.value).startOf('day').toISOString() : null
  await store
    .updateTask(t.id, {
      title,
      priority: editPriority.value,
      due_at,
      all_day: true,
      list_id: editListId.value,
      tags: editTags.value,
    })
    .catch(() => {})
  ElMessage.success('已保存')
  editTask.value = null
  reload()
}

async function onEditMore(cmd) {
  if (cmd === 'tag') return inputTags(editTags)
  if (cmd === 'clearDue') return (editDue.value = '')
  if (cmd === 'delete') {
    const t = editTask.value
    if (!t) return
    try {
      await ElMessageBox.confirm(`删除任务「${t.title}」？`, '删除', {
        type: 'warning',
        confirmButtonText: '删除',
        cancelButtonText: '取消',
      })
    } catch { return }
    await deleteTask(t.id).catch(() => {})
    ElMessage.success('已删除')
    editTask.value = null
    reload()
  }
}

async function inputTags(target) {
  try {
    const { value } = await ElMessageBox.prompt('标签名（多个用逗号分隔）', '添加标签', {
      inputValue: target.value.join(', '),
    })
    target.value = value.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
  } catch { /* 取消 */ }
}

function cyclePriority(scope) {
  if (scope === 'add') addPriority.value = (addPriority.value + 1) % 4
  else editPriority.value = (editPriority.value + 1) % 4
}

async function reload() {
  const res = await fetchTasks({ limit: 500, tz_offset_minutes: tzOffsetMinutes }).catch(() => ({ items: [] }))
  let items = res.items || []
  if (cfg.value.lists?.length) items = items.filter((t) => cfg.value.lists.includes(t.list_id))
  tasks.value = items.filter((t) => !hideDone.value || t.status !== 'done')
}
function toggleHideDone() {
  hideDone.value = !hideDone.value
  saveCfg({ hideDone: hideDone.value })
  reload()
}

// 方案 A 映射：重要 = priority>=2；紧急 = due N 天内（含逾期）或 priority>=3（N 可在「编辑规则」中调整）
function getQuadrant(t) {
  const important = t.priority >= 2
  const urgent =
    (t.due_at && dayjs(t.due_at).isBefore(dayjs().add(form.urgentDays, 'day'))) || t.priority >= 3
  if (important && urgent) return 'q1'
  if (important && !urgent) return 'q2'
  if (!important && urgent) return 'q3'
  return 'q4'
}

// 象限对应属性（对齐主流待办应用：重要紧急=今天+高优先级）
function attrsForQuadrant(q) {
  const today = dayjs().startOf('day')
  if (q === 'q1') return { priority: 3, due_at: today.toISOString(), all_day: true }
  if (q === 'q2') return { priority: 2, due_at: null, all_day: true }
  if (q === 'q3') return { priority: 1, due_at: today.toISOString(), all_day: true }
  return { priority: 0, due_at: null, all_day: true }
}

function timeGroupKey(t) {
  if (t.is_pinned && t.status !== 'done') return 'pinned'
  if (t.status === 'done') return 'later'
  if (!t.due_at) return 'nodate'
  const d = dayjs(t.due_at).startOf('day')
  const diff = d.diff(dayjs().startOf('day'), 'day')
  if (diff < 0) return 'overdue'
  if (diff === 0) return 'today'
  if (diff === 1) return 'tomorrow'
  if (diff <= 7) return 'week'
  return 'later'
}

function sorted(arr) {
  const a = [...arr]
  const mul = sortCfg.value.order === 'desc' ? -1 : 1
  if (sortCfg.value.sort === 'time') {
    a.sort((x, y) => {
      if (!x.due_at && !y.due_at) return 0
      if (!x.due_at) return 1
      if (!y.due_at) return -1
      return mul * (dayjs(x.due_at).valueOf() - dayjs(y.due_at).valueOf())
    })
  } else if (sortCfg.value.sort === 'priority') {
    a.sort((x, y) => y.priority - x.priority)
  } else if (sortCfg.value.sort === 'title') {
    a.sort((x, y) => x.title.localeCompare(y.title, 'zh-Hans-CN'))
  }
  return a
}

const byQuadrant = computed(() => {
  const m = { q1: [], q2: [], q3: [], q4: [] }
  for (const t of tasks.value) m[getQuadrant(t)].push(t)
  return m
})
const tasksOf = (k) => byQuadrant.value[k]

function groupsOf(qKey) {
  const list = tasksOf(qKey)
  if (sortCfg.value.group === 'none') return list.length ? [{ key: 'all', label: '', tasks: sorted(list) }] : []
  if (sortCfg.value.group === 'priority') {
    return PRIORITY_GROUPS.map((g) => ({ ...g, tasks: sorted(list.filter(g.match)) })).filter((g) => g.tasks.length)
  }
  if (sortCfg.value.group === 'list') {
    const names = new Map()
    for (const t of list) {
      const n = listName(t.list_id)
      if (!names.has(n)) names.set(n, [])
      names.get(n).push(t)
    }
    return [...names.entries()].map(([label, arr]) => ({ key: 'list:' + label, label, tasks: sorted(arr) }))
  }
  const buckets = new Map(TIME_GROUPS.map((g) => [g.key, []]))
  for (const t of list) buckets.get(timeGroupKey(t))?.push(t)
  return TIME_GROUPS.filter((g) => buckets.get(g.key)?.length).map((g) => ({
    ...g,
    tasks: sorted(buckets.get(g.key)),
  }))
}

function toggleGroup(key) {
  const s = new Set(collapsed.value)
  s.has(key) ? s.delete(key) : s.add(key)
  collapsed.value = s
}

// ---------- 行元信息 ----------
function listName(listId) {
  if (!listId) return '收集箱'
  return store.lists.find((l) => l.id === listId)?.name || ''
}
function isOverdue(t) {
  return !!t.due_at && dayjs(t.due_at).isBefore(dayjs().startOf('day'))
}
function dueLabel(t) {
  if (!t.due_at) return ''
  const d = dayjs(t.due_at)
  const diff = d.startOf('day').diff(dayjs().startOf('day'), 'day')
  if (diff < 0) return d.format('M月D日')
  if (diff === 0) return '今天'
  if (diff === 1) return '明天'
  return d.format('M月D日')
}

async function onComplete(t) {
  await store.complete(t.id, t.status !== 'done').catch(() => {})
  reload()
}

// ---------- 拖拽换象限 ----------
function onDragStart(t, e) {
  _dragTaskId = t.id
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', t.id)
}

async function onDrop(qKey) {
  dragOver.value = null
  const id = _dragTaskId
  _dragTaskId = null
  if (!id) return
  const t = tasks.value.find((x) => x.id === id)
  if (!t || t.status === 'done' || getQuadrant(t) === qKey) return
  const attrs = attrsForQuadrant(qKey)
  if (attrs.due_at && t.due_at && dayjs(t.due_at).isBefore(dayjs(attrs.due_at))) {
    attrs.due_at = t.due_at
  }
  if (qKey === 'q2' || qKey === 'q4') attrs.due_at = null
  await store.updateTask(id, attrs).catch(() => {})
  ElMessage.success('已调整象限')
  reload()
}

onMounted(reload)
</script>

<style scoped>
.quadrant {
  position: relative;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.q-grid {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  grid-template-rows: 1fr 1fr;
  gap: 12px;
}
/* 象限 = 边界卡片（对齐主流待办应用：白底圆角细边框） */
.q-cell {
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  background: #fff;
  border: 1px solid var(--ss-border, #e6e9f0);
  border-radius: 12px;
  transition: box-shadow 0.15s;
}
.q-cell.dropover {
  box-shadow: inset 0 0 0 2px var(--el-color-primary);
}
.q-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 12px 6px;
  flex-shrink: 0;
}
.q-badge {
  width: 18px;
  height: 18px;
  border-radius: 5px;
  color: #fff;
  font-size: 11px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.q-label {
  font-size: 14px;
  font-weight: 600;
}
.q-count {
  font-size: 12px;
  color: var(--ss-text-muted);
  font-variant-numeric: tabular-nums;
}
/* 卡头右侧悬停工具（对齐主流待办应用：灰底小丸 ＋ ⋯） */
.q-head-tools {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  background: var(--ss-fill, #f1f2f6);
  border-radius: 8px;
  padding: 2px;
  opacity: 0;
  transition: opacity 0.15s;
}
.q-cell:hover .q-head-tools {
  opacity: 1;
}
.q-tool-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--ss-text-secondary);
}
.q-tool-btn:hover {
  background: #fff;
  color: var(--el-color-primary);
  box-shadow: var(--ss-shadow, 0 1px 3px rgba(16, 24, 40, 0.1));
}
/* ⋯ 面板（对齐主流待办应用：分组/排序/顺序 + 开关行） */
.qm-panel {
  width: 210px;
  padding: 4px;
}
.qm-row {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
  color: var(--ss-text);
}
.qm-row:hover {
  background: var(--ss-fill, #f7f7f9);
}
.qm-icon {
  color: var(--ss-text-secondary);
  flex-shrink: 0;
}
.qm-val {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  color: var(--ss-text-secondary);
  font-size: 12px;
}
.qm-sub {
  position: absolute;
  left: calc(100% - 6px);
  top: -4px;
  background: #fff;
  border: 1px solid var(--ss-border, #e6e9f0);
  border-radius: 8px;
  box-shadow: var(--ss-shadow-lg, 0 8px 24px rgba(16, 24, 40, 0.12));
  padding: 4px;
  min-width: 110px;
  z-index: 20;
}
.qm-opt {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 8px;
  border-radius: 5px;
  font-size: 13px;
  white-space: nowrap;
}
.qm-opt:hover {
  background: var(--ss-fill, #f7f7f9);
}
.qm-check {
  color: var(--el-color-primary);
}
.qm-check-blank {
  width: 13px;
  flex-shrink: 0;
}
/* 编辑卡片锚点（点击行位置） */
.q-edit-anchor {
  position: absolute;
  z-index: 30;
}
.q-anchor-dot {
  display: inline-block;
  width: 2px;
  height: 18px;
}
.q-body {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 0 8px 8px;
}
.q-group-head {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 4px 4px;
  cursor: pointer;
  user-select: none;
}
.q-caret {
  display: inline-block;
  color: var(--ss-text-muted);
  font-size: 12px;
  transform: rotate(0deg);
  transition: transform 0.15s;
}
.q-caret.open {
  transform: rotate(90deg);
}
.q-group-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--ss-text);
}
.q-rows {
  display: flex;
  flex-direction: column;
}
.q-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 6px;
  border-radius: 6px;
  cursor: grab;
  font-size: 13px;
  color: var(--ss-text);
}
.q-row:hover {
  background: var(--ss-fill, #f7f7f9);
}
.q-row.done {
  opacity: 0.55;
}
.q-row.done .q-title {
  text-decoration: line-through;
}
.q-check {
  width: 16px;
  height: 16px;
  /* 对齐主流待办应用：圆角方块勾选框（非正圆） */
  border-radius: 5px;
  border: 1.5px solid #c8cdd8;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
  cursor: pointer;
}
.q-check:hover {
  border-color: var(--el-color-primary);
}
/* 对齐主流待办应用：逾期任务的勾选框红框提示 */
.q-check.overdue:not(.on) {
  border-color: var(--el-color-danger);
}
.q-check.on {
  background: var(--el-color-primary);
  border-color: var(--el-color-primary);
}
.q-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.q-tag {
  font-size: 11px;
  color: #b8860b;
  background: #faf3d7;
  border-radius: 4px;
  padding: 1px 6px;
  flex-shrink: 0;
}
.q-meta {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
  font-size: 12px;
  color: var(--ss-text-muted);
}
.q-due.overdue {
  color: var(--el-color-danger);
}
.q-empty {
  padding: 40px 0;
  text-align: center;
  font-size: 12px;
  color: var(--ss-text-muted);
}
.q-rules {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.q-rule-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.q-rule-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ss-text);
}
.q-rule-select {
  width: 100%;
}
.q-rule-hint {
  font-size: 12px;
  color: var(--ss-text-muted);
}
.q-rule-days {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: var(--ss-text);
}
.q-rule-num {
  width: 110px;
}
.q-rule-live {
  display: flex;
  flex-direction: column;
  gap: 8px;
  border-top: 1px solid var(--ss-border, #ebeef5);
  padding-top: 10px;
}
.q-rule-scope {
  font-size: 12px;
  color: var(--ss-text-muted);
}
.q-rule-row {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.q-rule-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--ss-text);
}
.q-rule-desc {
  font-size: 12px;
  color: var(--ss-text-secondary);
  margin-top: 2px;
}
.q-rule-note {
  font-size: 12px;
  color: var(--ss-text-muted);
  background: var(--ss-fill, #f7f7f9);
  border-radius: 8px;
  padding: 10px 12px;
  line-height: 1.6;
}
.q-guide {
  font-size: 13px;
  color: var(--ss-text);
  line-height: 1.8;
}
.q-guide ol {
  padding-left: 18px;
}
.q-guide-link {
  font-size: 12px;
  color: var(--ss-text-muted);
}
.q-guide-link a {
  color: var(--el-color-primary);
}
</style>

<style>
/* 快速添加/编辑卡片弹层（popper 挂 body，需全局样式） */
.q-addpop {
  padding: 12px 14px !important;
  border-radius: 14px !important;
  box-shadow: var(--ss-shadow-lg, 0 8px 24px rgba(16, 24, 40, 0.14)) !important;
}
</style>
