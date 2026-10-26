<template>
  <!-- 多选批量面板（对齐主流待办应用桌面端）：原位替代右侧详情栏（同一个框，不是悬浮面板/弹框）；
       属性行=纯「图标+名称」行，点击在面板内手风琴展开编辑（无弹出层）；底部两列灰底操作卡片 -->
  <aside class="batch-panel" :class="{ 'overlay-timeline': store.viewMode === 'timeline' }">
    <div class="bp-header">
      <span class="bp-count">已选择 {{ store.selectedIds.length }} 项</span>
      <span class="bp-cancel" @click="store.clearSelection()">取消</span>
    </div>

    <div class="bp-rows">
      <!-- 日期与提醒：行内展开完整日期面板（批量取 due_at/all_day，选了提醒才批量落提醒） -->
      <div class="bp-row" :class="{ active: expandKey === 'date' }" @click="toggleExpand('date')">
        <Calendar :size="16" class="bp-row-icon" /> 日期与提醒
      </div>
      <div v-if="expandKey === 'date'" class="bp-expand">
        <TaskDatePicker inline @change="onBatchDue" />
      </div>
      <!-- 推迟：按各任务自身日期整体平移（保留时刻/全天），无日期的落目标日全天 -->
      <div class="bp-row" :class="{ active: expandKey === 'postpone' }" @click="toggleExpand('postpone')">
        <RotateCw :size="16" class="bp-row-icon" /> 推迟
      </div>
      <div v-if="expandKey === 'postpone'" class="bp-expand">
        <div v-for="o in postponeOptions" :key="o.label" class="bp-opt" @click="onPostpone(o)">
          <span>{{ o.label }}</span>
        </div>
      </div>
      <div class="bp-row" :class="{ active: expandKey === 'priority' }" @click="toggleExpand('priority')">
        <Flag :size="16" class="bp-row-icon" /> 优先级
      </div>
      <div v-if="expandKey === 'priority'" class="bp-expand">
        <div v-for="o in priorityOptions" :key="o.value" class="bp-opt" @click="apply('priority', { priority: o.value })">
          <Flag :size="14" :color="o.color" :fill="o.value ? o.color : 'none'" />
          <span>{{ o.label }}</span>
        </div>
      </div>
      <div class="bp-row" :class="{ active: expandKey === 'list' }" @click="toggleExpand('list')">
        <Inbox :size="16" class="bp-row-icon" /> 移动到
      </div>
      <div v-if="expandKey === 'list'" class="bp-expand lists">
        <div class="bp-opt" @click="apply('move', { list_id: null })">
          <Inbox :size="14" />
          <span>收集箱</span>
        </div>
        <div v-for="l in store.lists" :key="l.id" class="bp-opt" @click="apply('move', { list_id: l.id })">
          <Inbox :size="14" />
          <span>{{ l.name }}</span>
        </div>
      </div>
      <!-- 标签：批量加标签（并集，不移除已有）；全部选中项已有该标签时打勾 -->
      <div class="bp-row" :class="{ active: expandKey === 'tags' }" @click="toggleExpand('tags')">
        <Tag :size="16" class="bp-row-icon" /> 标签
      </div>
      <div v-if="expandKey === 'tags'" class="bp-expand lists">
        <div v-if="!store.tagCounts.length" class="bp-empty">暂无标签，可在添加任务时用 ~标签 创建</div>
        <div v-for="t in store.tagCounts" :key="t.tag" class="bp-opt" @click="onAddTag(t.tag)">
          <Tag :size="14" />
          <span>{{ t.tag }}</span>
          <Check v-if="allHaveTag(t.tag)" :size="13" class="bp-opt-check" />
        </div>
      </div>
    </div>

    <!-- 关联主任务：行内选择主任务（当前视图顶级任务，排除选中项） -->
    <div v-if="expandKey === 'parent'" class="bp-expand parents">
      <div class="bp-parent-tip">选择主任务，选中任务将转为它的子任务：</div>
      <div v-if="!parentCandidates.length" class="bp-empty">当前视图没有可作主任务的任务</div>
      <div v-for="t in parentCandidates" :key="t.id" class="bp-opt" @click="onSetParent(t)">
        <span>{{ t.title }}</span>
      </div>
    </div>

    <div class="bp-grid">
      <button class="bp-btn" @click="apply('complete', { done: true })">
        <Check :size="18" color="#3b82f6" />完成
      </button>
      <button class="bp-btn" @click="apply('pin', { pinned: true })">
        <Pin :size="18" color="#f59e0b" />置顶
      </button>
      <button class="bp-btn" :class="{ active: expandKey === 'parent' }" @click="toggleExpand('parent')">
        <Link2 :size="18" color="#6366f1" />关联主任务
      </button>
      <button class="bp-btn" @click="onDuplicate">
        <Copy :size="18" color="#14b8a6" />创建副本
      </button>
      <!-- 合并（对齐主流待办应用：多任务并为新任务的子任务） -->
      <button class="bp-btn" @click="onMerge">
        <Merge :size="18" color="#8b5cf6" />合并
      </button>
      <!-- 打开便签（对齐主流待办应用：选中项中的笔记直接打开详情） -->
      <button v-if="firstNote" class="bp-btn" @click="onOpenNote">
        <BookOpen :size="18" color="#0ea5e9" />打开便签
      </button>
      <button class="bp-btn" @click="onCopyText">
        <ClipboardCopy :size="18" color="#64748b" />复制文本
      </button>
      <button class="bp-btn danger" @click="onDelete">
        <Trash2 :size="18" color="#f56c6c" />删除
      </button>
    </div>
  </aside>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Calendar, RotateCw, Flag, Inbox, Tag, Check, Pin, Link2, Copy, ClipboardCopy, Trash2, Merge, BookOpen } from 'lucide-vue-next'
import dayjs from 'dayjs'
import { useTaskStore } from '@/stores/task'
import TaskDatePicker from './TaskDatePicker.vue'

const store = useTaskStore()

// 属性行手风琴展开（无弹出层）：'date' | 'postpone' | 'priority' | 'list' | 'tags' | 'parent'
const expandKey = ref(null)
function toggleExpand(key) {
  expandKey.value = expandKey.value === key ? null : key
}

// 选中任务（按当前渲染顺序）
const selectedTasks = computed(() => store.tasks.filter((t) => store.selectedIds.includes(t.id)))

const priorityOptions = [
  { value: 3, label: '高优先级', color: '#f56c6c' },
  { value: 2, label: '中优先级', color: '#e6a23c' },
  { value: 1, label: '低优先级', color: '#409eff' },
  { value: 0, label: '无优先级', color: '#9ca3af' },
]
const postponeOptions = [
  { label: '明天', n: 1, unit: 'day' },
  { label: '下周', n: 7, unit: 'day' },
  { label: '下月', n: 1, unit: 'month' },
]
// 可作主任务的候选：当前视图顶级任务、不在选中集合内
const parentCandidates = computed(() =>
  store.tasks.filter((t) => !t.parent_id && !store.selectedIds.includes(t.id))
)

async function apply(action, payload = {}) {
  expandKey.value = null
  const res = await store.batch(action, payload)
  if (res.failed?.length) {
    ElMessage.warning(`成功 ${res.ok} 项，失败 ${res.failed.length} 项`)
  } else {
    ElMessage.success(`已批量处理 ${res.ok} 项`)
  }
}

function onBatchDue(p) {
  // 行内日期面板提交：{ due_at, all_day, reminders, persistent_reminder, ... }；
  // 批量仅取日期（due_at=null 即批量清除日期）；用户选了提醒才批量落提醒（不带则保留各任务原提醒）
  if (!p) return
  const payload = { due_at: p.due_at ?? null, all_day: p.all_day ?? true }
  if (p.reminders?.length) {
    payload.reminders = p.reminders
    payload.persistent_reminder = !!p.persistent_reminder
  }
  apply('due', payload)
}

// 推迟：逐任务按自身日期平移（保留时刻/全天，时间段任务同步平移 start_at）；无日期任务落目标日全天
async function onPostpone(o) {
  expandKey.value = null
  const ids = [...store.selectedIds]
  let ok = 0
  for (const id of ids) {
    const t = store.tasks.find((x) => x.id === id)
    if (!t) continue
    const data = {}
    if (t.due_at) {
      data.due_at = dayjs(t.due_at).add(o.n, o.unit).toISOString()
      data.all_day = t.all_day ?? true
      if (t.start_at) data.start_at = dayjs(t.start_at).add(o.n, o.unit).toISOString()
    } else {
      data.due_at = dayjs().add(o.n, o.unit).startOf('day').toISOString()
      data.all_day = true
    }
    try {
      await store.updateTask(id, data)
      ok++
    } catch {
      // 拦截器已弹错误提示
    }
  }
  ElMessage.success(`已推迟${o.label === '明天' ? '到明天' : o.label === '下周' ? '一周' : '一月'} ${ok} 项`)
}

// 批量加标签（并集）
function allHaveTag(tag) {
  return selectedTasks.value.length > 0 && selectedTasks.value.every((t) => (t.tags || []).includes(tag))
}
function onAddTag(tag) {
  if (allHaveTag(tag)) return
  apply('tags', { tags: [tag] })
}

// 关联主任务：逐任务 PATCH parent_id（含子任务的任务后端会拒绝，计入失败数）
async function onSetParent(parent) {
  expandKey.value = null
  const ids = [...store.selectedIds]
  let ok = 0
  let fail = 0
  for (const id of ids) {
    try {
      await store.updateTask(id, { parent_id: parent.id })
      ok++
    } catch {
      fail++
    }
  }
  if (fail) ElMessage.warning(`成功 ${ok} 项，失败 ${fail} 项（含子任务的任务不能转为子任务）`)
  else ElMessage.success(`已关联到「${parent.title}」`)
  await store.fetchTasks()
  store.clearSelection()
}

// 批量创建副本（对齐主流待办应用批量面板「创建副本」：复制标题/备注/清单/优先级/标签/日期，不含子任务/提醒/重复）
// 合并（对齐主流待办应用批量面板）：把选中任务合并为一个新任务的子任务
const firstNote = computed(() => selectedTasks.value.find((t) => t.is_note))
async function onMerge() {
  const tasks = selectedTasks.value.filter((t) => !t.is_note)
  if (!tasks.length) return ElMessage.warning('请选择要合并的任务')
  try {
    const { value } = await ElMessageBox.prompt(`将 ${tasks.length} 个任务合并为新任务的子任务`, '合并任务', {
      inputValue: tasks[0].title,
      inputPlaceholder: '新任务标题',
    })
    const title = (value || '').trim()
    if (!title) return
    const parent = await store.createTask({ title, list_id: tasks[0].list_id ?? null })
    let ok = 0
    for (const t of tasks) {
      try {
        await store.updateTask(t.id, { parent_id: parent.id })
        ok++
      } catch { /* 含子任务的任务会被后端拒绝，跳过 */ }
    }
    ElMessage.success(`已合并 ${ok}/${tasks.length} 个任务`)
    store.selectedIds = []
    await store.fetchTasks()
  } catch { /* 取消 */ }
}

// 打开便签（对齐主流待办应用批量面板）：打开选中项中的第一个笔记
function onOpenNote() {
  if (!firstNote.value) return
  store.openDetail(firstNote.value.id)
  store.selectedIds = []
}

async function onDuplicate() {
  const ids = [...store.selectedIds]
  let ok = 0
  for (const id of ids) {
    const t = store.tasks.find((x) => x.id === id)
    if (!t) continue
    try {
      await store.createTask({
        title: t.title,
        note: t.note || null,
        list_id: t.list_id ?? null,
        priority: t.priority || 0,
        tags: [...(t.tags || [])],
        due_at: t.due_at || null,
        all_day: t.all_day ?? true,
      })
      ok++
    } catch {
      // 拦截器已弹错误提示
    }
  }
  ElMessage.success(`已创建 ${ok} 个副本`)
  store.clearSelection()
}

// 复制文本：按渲染顺序逐行复制标题到剪贴板
async function onCopyText() {
  const lines = selectedTasks.value.map((t) => t.title)
  if (!lines.length) return
  try {
    await navigator.clipboard.writeText(lines.join('\n'))
    ElMessage.success(`已复制 ${lines.length} 项`)
  } catch {
    ElMessage.error('复制失败（浏览器未授权剪贴板）')
  }
}

async function onDelete() {
  try {
    await ElMessageBox.confirm(`将删除已选的 ${store.selectedIds.length} 项任务（移入回收站），确定？`, '批量删除', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  apply('delete')
}
</script>

<style scoped>
/* 与详情栏（.task-detail-panel）同一框体：右栏第三列，非悬浮面板 */
.batch-panel {
  position: relative;
  width: 35%;
  min-width: 420px;
  flex-shrink: 0;
  height: 100%;
  overflow-y: auto;
  background: #fff;
  border-left: 1px solid var(--ss-border);
  padding: 16px;
  display: flex;
  flex-direction: column;
}
.batch-panel.overlay-timeline {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  height: auto;
  z-index: 30;
  box-shadow: -6px 0 18px rgba(0, 0, 0, 0.1);
}
.bp-header {
  display: flex;
  align-items: center;
  font-size: 14px;
  padding: 2px 4px 12px;
}
.bp-count {
  flex: 1;
  font-weight: 600;
}
.bp-cancel {
  color: var(--ss-primary);
  cursor: pointer;
  font-size: 13px;
}
.bp-cancel:hover {
  text-decoration: underline;
}
/* 属性行：纯「图标+名称」行（对齐主流待办应用批量面板） */
.bp-rows {
  display: flex;
  flex-direction: column;
}
.bp-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 8px;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  color: var(--ss-text);
}
.bp-row:hover,
.bp-row.active {
  background: var(--ss-bg);
}
.bp-row-icon {
  color: var(--ss-text-muted);
}
/* 行内手风琴展开编辑区 */
.bp-expand {
  padding: 6px 2px 10px;
}
.bp-expand.lists,
.bp-expand.parents {
  max-height: 260px;
  overflow: auto;
}
.bp-parent-tip {
  font-size: 12px;
  color: var(--ss-text-muted);
  padding: 2px 10px 6px;
}
.bp-empty {
  font-size: 13px;
  color: var(--ss-text-muted);
  padding: 10px;
}
.bp-opt {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  color: var(--ss-text);
}
.bp-opt:hover {
  background: var(--ss-bg);
}
.bp-opt span {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bp-opt-check {
  margin-left: auto;
  color: var(--ss-primary);
}
/* 操作卡片：两列灰底大卡（对齐主流待办应用：彩色图标在上、文字在下） */
.bp-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-top: 18px;
}
.bp-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 0;
  border: none;
  border-radius: 8px;
  background: var(--ss-bg);
  font-size: 13px;
  cursor: pointer;
  color: var(--ss-text);
}
.bp-btn:hover,
.bp-btn.active {
  filter: brightness(0.96);
}
</style>
