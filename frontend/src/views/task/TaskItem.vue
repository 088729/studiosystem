<template>
  <div
    class="task-item"
    :class="{ done: task.status === 'done', selected }"
    @click="$emit('open', task, $event)"
    @contextmenu.prevent="$emit('contextmenu', task, $event)"
  >
    <div class="main-line">
    <!-- 子任务折叠箭头（对齐主流待办应用：绝对定位在圆点左侧内边距区，圆点与普通行对齐；多选模式隐藏） -->
    <span
      v-if="!hideCheck && !showCheck && task.subtask_total"
      class="sub-toggle"
      title="展开/折叠子任务"
      @click.stop="toggleExpand"
      @pointerdown.stop
    >
      <ChevronRight :size="14" class="fold-arrow" :class="{ expanded }" />
    </span>
    <!-- 主行悬停拖拽手柄（对齐主流待办应用：无子任务的行悬停时在箭头列显示 ≡；有子任务的行保留折叠箭头） -->
    <span v-if="!hideCheck && !showCheck && !task.subtask_total" class="row-grip">
      <GripVertical :size="14" />
    </span>
    <el-checkbox
      v-if="showCheck"
      :model-value="selected"
      class="select-check"
      @click.stop
      @change="$emit('select', task)"
    />
    <span
      v-if="!hideCheck && !task.is_note"
      class="check-dot"
      :class="{ checked: task.status === 'done' }"
      @click.stop="$emit('complete', task, task.status !== 'done')"
    >
      <Check v-if="task.status === 'done'" :size="12" />
    </span>
    <!-- 笔记：无完成概念，行首显示 📔 图标（对齐主流待办应用笔记行） -->
    <BookOpen v-if="task.is_note && !hideCheck && !showCheck" :size="14" class="note-flag" />

    <span class="priority-bar" :class="`p${task.priority}`" />

    <div class="task-body">
      <div class="task-main">
        <span class="task-title">{{ task.title }}</span>
        <div v-if="noteText" class="task-note">{{ noteText }}</div>
      </div>
      <div class="task-meta">
        <el-tag v-for="tag in task.tags" :key="tag" size="small" class="task-tag">{{ tag }}</el-tag>
        <span v-if="listName" class="task-list-name">{{ listName }}</span>
        <el-tag v-if="showOwner" size="small" type="warning" effect="plain" class="owner-tag">{{ task.owner }}</el-tag>
        <span v-if="task.subtask_total" class="task-subtasks">{{ task.subtask_done }}/{{ task.subtask_total }}</span>
        <span v-if="task.due_at" class="task-due" :class="{ overdue: isOverdue }">
          <Clock :size="12" />
          {{ dueText }}
        </span>
      </div>
    </div>

    <button
      v-if="!hideCheck"
      class="row-more"
      title="更多"
      @click.stop="$emit('contextmenu', task, $event)"
      @pointerdown.stop
    >
      <MoreHorizontal :size="16" />
    </button>

    <div v-if="$slots.actions" class="task-actions" @click.stop>
      <slot name="actions" />
    </div>
    </div>

    <!-- 行内子任务区（对齐主流待办应用：父任务行箭头展开/折叠，懒加载） -->
    <div v-if="taskStore.showDetail && plainNote" class="task-desc-preview">{{ plainNote }}</div>
    <div v-if="expanded" class="sub-inline" @click.stop @contextmenu.stop>
      <div v-if="loadingSubs" class="sub-loading">加载中…</div>
      <div
        v-for="sub in subs"
        :key="sub.id"
        class="sub-inline-row"
        :class="{ done: sub.status === 'done' }"
      >
        <span class="sub-grip" title="拖动排序（暂仅样式）" @pointerdown.stop>
          <GripVertical :size="13" />
        </span>
        <span
          class="check-dot small"
          :class="{ checked: sub.status === 'done' }"
          @click.stop="toggleSub(sub)"
        >
          <Check v-if="sub.status === 'done'" :size="10" />
        </span>
        <span class="sub-title" @click.stop="$emit('open', sub)">{{ sub.title }}</span>
        <span class="sub-meta">
          <el-tag v-for="tag in sub.tags" :key="tag" size="small" class="task-tag sub-tag">{{ tag }}</el-tag>
          <span class="sub-list-name">{{ subListName(sub) }}</span>
          <span v-if="sub.due_at" class="sub-due"><Clock :size="11" />{{ subDueText(sub) }}</span>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { Check, ChevronRight, Clock, GripVertical, MoreHorizontal, BookOpen } from 'lucide-vue-next'
import dayjs from 'dayjs'
import { useAuthStore } from '@/stores/auth'
import { useTaskStore } from '@/stores/task'
import { fetchTask } from '@/api/task'

const props = defineProps({
  task: { type: Object, required: true },
  hideCheck: { type: Boolean, default: false },  // 回收站行隐藏完成圆点
  showCheck: { type: Boolean, default: false },  // 多选模式显示勾选框（16 批量操作）
  selected: { type: Boolean, default: false },
})
defineEmits(['complete', 'open', 'select', 'contextmenu'])

const authStore = useAuthStore()
const taskStore = useTaskStore()

// ---------- 行内子任务展开/折叠（对齐主流待办应用：父任务行左侧小箭头，懒加载） ----------
const expanded = ref(false)
const subs = ref([])
const loadingSubs = ref(false)
async function loadSubs() {
  loadingSubs.value = true
  try {
    const d = await fetchTask(props.task.id)
    subs.value = d.subtasks || []
  } finally {
    loadingSubs.value = false
  }
}
async function toggleExpand() {
  expanded.value = !expanded.value
  if (expanded.value) await loadSubs()
}

// 显示详细：描述纯文本预览（富文本去标签截断）
const plainNote = computed(() => {
  const html = props.task.note || ''
  const text = html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
  return text.length > 80 ? text.slice(0, 80) + '…' : text
})

// 显示检查事项：开关打开时自动展开子任务（对齐主流待办应用 ⋯「显示检查事项」）
watch(
  () => taskStore.showSubtasks,
  async (v) => {
    if (v && props.task.subtask_total && !expanded.value) {
      expanded.value = true
      await loadSubs()
    }
  }
)
async function toggleSub(sub) {
  await taskStore.complete(sub.id, sub.status !== 'done')
  await loadSubs()
}
function subDueText(s) {
  const d = dayjs(s.due_at)
  if (s.all_day) {
    if (d.isSame(dayjs(), 'day')) return '今天'
    if (d.isSame(dayjs().add(1, 'day'), 'day')) return '明天'
    return fmtDate(d)
  }
  if (d.isSame(dayjs(), 'day')) return `今天 ${d.format('HH:mm')}`
  return `${fmtDate(d)} ${d.format('HH:mm')}`
}

// 子任务所属清单名（list_id 跟随父任务）
const subListName = (s) =>
  taskStore.lists.find((l) => l.id === s.list_id)?.name || '收集箱'

// 所属清单名（list_id=null 即收集箱）
const listName = computed(
  () => taskStore.lists.find((l) => l.id === props.task.list_id)?.name || '收集箱'
)
// 共享清单中他人创建的任务显示 owner 徽标
const showOwner = computed(() => props.task.owner && props.task.owner !== authStore.userInfo?.username)

// 逾期 = todo 且 due_at < 今日 00:00（本地）
const isOverdue = computed(() => {
  if (props.task.status !== 'todo' || !props.task.due_at) return false
  return dayjs(props.task.due_at).isBefore(dayjs().startOf('day'))
})

// 备注预览（对齐主流待办应用：列表行标题下方显示一行纯文本摘要；富文本 HTML 去标签）
const noteText = computed(() =>
  (props.task.note || '').replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim()
)

const fmtDate = (d) =>
  d.isSame(dayjs(), 'year') ? d.format('M月D日') : d.format('YYYY/M/D')

const dueText = computed(() => {
  if (!props.task.due_at) return ''
  const d = dayjs(props.task.due_at)
  if (props.task.all_day) {
    if (d.isSame(dayjs(), 'day')) return '今天'
    if (d.isSame(dayjs().add(1, 'day'), 'day')) return '明天'
    return fmtDate(d)
  }
  if (d.isSame(dayjs(), 'day')) return `今天 ${d.format('HH:mm')}`
  if (d.isSame(dayjs().add(1, 'day'), 'day')) return `明天 ${d.format('HH:mm')}`
  return `${fmtDate(d)} ${d.format('HH:mm')}`
})
</script>

<style scoped>
.task-item {
  position: relative; /* 供 .sub-toggle 绝对定位 */
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  padding: 10px 12px 10px 26px; /* 左侧留出折叠箭头位（对齐主流待办应用） */
  background: #fff;
  border-radius: var(--ss-radius-sm);
  border: 1px solid var(--ss-border);
  margin-bottom: 8px;
  cursor: pointer;
  transition: box-shadow 0.2s;
}
.task-item:hover {
  box-shadow: var(--ss-shadow);
}
.task-item.selected {
  border-color: var(--ss-primary);
  background: var(--ss-primary-light);
}
.main-line {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  min-width: 0;
}
.select-check {
  flex-shrink: 0;
  height: auto;
}
.check-dot {
  width: 18px;
  height: 18px;
  border: 2px solid var(--ss-text-muted);
  /* 对齐主流待办应用：清单/详情/看板 = 正圆勾选框（四象限才是圆角方块） */
  border-radius: 50%;
  transition: border-color 0.12s, background 0.12s;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
}
.check-dot:hover {
  border-color: var(--ss-primary);
}
.check-dot.checked {
  background: var(--ss-primary);
  border-color: var(--ss-primary);
}
.note-flag {
  flex-shrink: 0;
  color: var(--ss-primary);
}
.priority-bar {
  width: 4px;
  align-self: stretch;
  border-radius: 2px;
  background: transparent;
  flex-shrink: 0;
}
.priority-bar.p3 { background: #f56c6c; }
.priority-bar.p2 { background: #e6a23c; }
.priority-bar.p1 { background: #409eff; }
.task-body {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 12px;
}
.task-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.task-note {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  color: var(--ss-text-muted);
}
.task-item.done .task-note {
  text-decoration: line-through;
}
.task-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}
.task-item.done .task-title {
  text-decoration: line-through;
  color: var(--ss-text-muted);
}
.task-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
  /* 窄窗口允许收缩（原 flex-shrink:0 会把行撑宽，task-content 出现横向滚动条）；
     装不下的 chip 在组边界整体裁掉，对齐主流待办应用行内裁切 */
  flex-shrink: 1;
  min-width: 0;
  overflow: hidden;
  font-size: 12px;
  color: var(--ss-text-secondary);
}
.task-meta > * {
  flex-shrink: 0;
}
.task-due {
  display: flex;
  align-items: center;
  gap: 4px;
}
.task-list-name {
  color: var(--ss-text-muted);
}
.task-due.overdue {
  color: #f56c6c;
}
.task-tag {
  --el-tag-bg-color: var(--ss-primary-light);
}
.task-subtasks {
  color: var(--ss-text-muted);
}
/* 主行悬停拖拽手柄：与折叠箭头同列，默认隐藏，flat 列表悬停主行时显示 */
.row-grip {
  position: absolute;
  left: 7px;
  top: 12px;
  width: 15px;
  height: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ss-text-muted);
  cursor: grab;
  opacity: 0;
  transition: opacity 0.15s;
  pointer-events: none; /* 纯视觉提示，整行拖拽仍走行本身 */
}
/* 行悬停「⋯ 更多」按钮：默认隐藏，flat 列表悬停主行时显示（对齐主流待办应用） */
.row-more {
  display: none;
  border: none;
  background: none;
  cursor: pointer;
  color: var(--ss-text-muted);
  padding: 2px;
  border-radius: 4px;
  align-items: center;
  flex-shrink: 0;
}
.row-more:hover {
  background: var(--ss-border);
  color: var(--ss-text);
}
.task-actions {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}
/* 行内子任务展开/折叠（主流待办应用同款：箭头在圆点左侧） */
.sub-toggle {
  position: absolute;
  left: 7px;
  top: 12px; /* 与首行圆点纵向对齐 */
  width: 15px;
  height: 18px;
  cursor: pointer;
  color: var(--ss-text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
}
.sub-toggle:hover {
  color: var(--ss-primary);
}
.sub-toggle .fold-arrow {
  transition: transform 0.15s;
}
.sub-toggle .fold-arrow.expanded {
  transform: rotate(90deg);
}
.sub-inline {
  flex-basis: 100%;
  margin: 2px 0 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.sub-loading {
  font-size: 12px;
  color: var(--ss-text-muted);
  padding: 4px 8px;
}
.sub-inline-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 5px 8px 5px 0;
  margin-left: -19px; /* 回退父行左内边距，使拖拽手柄与父行箭头同列 */
  border-radius: 6px;
  font-size: 13px;
}
.sub-inline-row:hover {
  background: #f5f7fa;
}
.sub-grip {
  width: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ss-text-muted);
  cursor: grab;
  flex-shrink: 0;
  opacity: 0; /* 对齐主流待办应用：拖拽手柄悬停子行才显示（占位防抖动） */
  transition: opacity 0.15s;
}
.sub-inline-row:hover .sub-grip {
  opacity: 1;
}
.check-dot.small {
  width: 15px;
  height: 15px;
  border-width: 1.5px;
  margin-left: 16px; /* 子圆点比父行圆点再右缩一级 */
}
.sub-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sub-inline-row.done .sub-title {
  text-decoration: line-through;
  color: var(--ss-text-muted);
}
.sub-meta {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.sub-tag {
  flex-shrink: 0;
}
.sub-list-name {
  font-size: 12px;
  color: var(--ss-text-muted);
  flex-shrink: 0;
}
.sub-due {
  font-size: 12px;
  color: var(--ss-text-secondary);
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.task-desc-preview {
  font-size: 12px;
  color: var(--ss-text-muted, #a8abb2);
  padding: 0 8px 4px 44px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
</style>
