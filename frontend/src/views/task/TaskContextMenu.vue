<template>
  <teleport to="body">
    <div
      v-if="visible && task"
      ref="menuEl"
      class="task-context-menu"
      :style="{ left: `${pos.x}px`, top: `${pos.y}px` }"
      @click.stop
      @contextmenu.prevent.stop
    >
      <!-- 日期行：今天 / 明天 / 下周 / 选择日期 / 清除日期 -->
      <div class="ctx-row">
        <el-tooltip v-for="d in dateActions" :key="d.tip" :content="d.tip" placement="top">
          <span class="ctx-icon-btn" :title="d.tip" @click="d.run"><component :is="d.icon" :size="15" /></span>
        </el-tooltip>
        <TaskDatePicker
          :due-at="task.due_at"
          :all-day="task.all_day"
          :start-at="task.start_at"
          :reminders="task.reminders"
          :persistent-reminder="task.persistent_reminder"
          :recurrence="task.recurrence"
          :task-id="task.id"
          @change="onPickDate"
        >
          <template #trigger>
            <span class="ctx-icon-btn" title="选择日期"><Calendar :size="15" /></span>
          </template>
        </TaskDatePicker>
        <el-tooltip content="清除日期" placement="top">
          <span class="ctx-icon-btn" @click="setDue(null)"><CalendarX :size="15" /></span>
        </el-tooltip>
      </div>

      <!-- 优先级行：高/中/低/无，当前值高亮（笔记无优先级概念，对齐主流待办应用笔记菜单不显示） -->
      <div v-if="!task.is_note" class="ctx-row">
        <el-tooltip v-for="p in priorities" :key="p.value" :content="p.tip" placement="top">
          <span
            class="ctx-icon-btn"
            :class="{ active: (task.priority || 0) === p.value }"
            @click="setPriority(p.value)"
          ><Flag :size="14" :color="p.color" :fill="p.value ? p.color : 'none'" /></span>
        </el-tooltip>
      </div>

      <div class="ctx-divider" />

      <div v-if="!task.is_note" class="ctx-item" @click="addSubtask">
        <Plus :size="14" class="ctx-item-icon" />添加子任务
      </div>
      <div class="ctx-item" @click="togglePin">
        <Pin :size="14" class="ctx-item-icon" />{{ task.is_pinned ? '取消置顶' : '置顶' }}
      </div>

      <!-- 移动到：打开带搜索的清单选择弹窗（对齐主流待办应用：可输入清单名快速搜索） -->
      <div class="ctx-item" @click="openMove">
        <FolderInput :size="14" class="ctx-item-icon" />移动到
      </div>

      <!-- 标签（hover 展开二级子菜单：已有标签勾选切换，底部新建） -->
      <div class="ctx-item ctx-submenu-trigger" v-auth="'task:edit'">
        <Tag :size="14" class="ctx-item-icon" />标签
        <ChevronRight :size="13" class="ctx-submenu-arrow" />
        <div class="ctx-submenu" :class="{ 'flip-x': flipX, 'flip-y': flipY }" @click.stop>
          <div
            v-for="t in store.tagCounts"
            :key="t.tag"
            class="ctx-item"
            @click="toggleTag(t.tag)"
          >
            <Check v-if="task.tags?.includes(t.tag)" :size="13" class="ctx-item-icon ctx-check-on" />
            <span v-else class="ctx-item-icon ctx-check-blank" />
            {{ t.tag }}
          </div>
          <div v-if="!store.tagCounts.length" class="ctx-empty">暂无标签</div>
          <div class="ctx-tag-new">
            <el-input
              v-model="newTag"
              size="small"
              placeholder="+ 新建标签，回车添加"
              @keyup.enter="addTag"
            />
          </div>
        </div>
      </div>

      <!-- 负责人：弹输入用户名，留空清除（笔记无负责人概念，对齐主流待办应用笔记菜单不显示） -->
      <div v-if="!task.is_note" class="ctx-item" v-auth="'task:edit'" @click="onAssign">
        <User :size="14" class="ctx-item-icon" />负责人
      </div>

      <!-- 开始专注 ›：子菜单选计时方式（对齐主流待办应用）；主项点击=番茄计时 -->
      <div class="ctx-item has-sub" v-auth="'task:run'" @click="onFocusCountdown">
        <Timer :size="14" class="ctx-item-icon" />开始专注
        <span class="sub-arrow">›</span>
        <div class="ctx-sub" @click.stop>
          <div class="ctx-item" @click="onFocusCountdown"><span class="sub-icon">🍅</span>番茄计时 {{ pomodoroStore.focusConfig.pomodoro_minutes || 25 }} 分钟</div>
          <div class="ctx-item" @click="onFocusStopwatch"><span class="sub-icon">⏱️</span>正计时</div>
          <div class="ctx-item" @click="onFocus()"><span class="sub-icon">✏️</span>自定义时长…</div>
        </div>
      </div>
      <!-- 上传附件（笔记菜单，对齐主流待办应用；任务行入口在详情抽屉附件区/时间线卡片） -->
      <div v-if="task.is_note" class="ctx-item" v-auth="'task:edit'" @click="onUploadClick">
        <Paperclip :size="14" class="ctx-item-icon" />上传附件
        <input ref="fileInput" type="file" style="display: none" @change="onFilePicked" />
      </div>
      <!-- 保存为模板（笔记菜单，对齐主流待办应用；与详情栏 ⋯ 同一套模板数据 note_templates） -->
      <template v-if="task.is_note">
        <div class="ctx-divider" />
        <div class="ctx-item" v-auth="'task:edit'" @click="saveAsTemplate">
          <LayoutTemplate :size="14" class="ctx-item-icon" />保存为模板
        </div>
      </template>
      <div class="ctx-item" v-auth="'task:create'" @click="duplicate">
        <Copy :size="14" class="ctx-item-icon" />创建副本
      </div>
      <!-- 复制链接（对齐主流待办应用：应用内定位链接，打开自动展开该任务） -->
      <div class="ctx-item" @click="copyTaskLink">
        <Link2 :size="14" class="ctx-item-icon" />复制链接
      </div>
      <!-- 关联主任务（对齐主流待办应用；单任务版：选择顶级任务作为父任务） -->
      <div v-if="!task.is_note" class="ctx-item" v-auth="'task:edit'" @click="openParentPicker">
        <CornerUpRight :size="14" class="ctx-item-icon" />关联主任务
      </div>
      <!-- 任务 ↔ 笔记 转换（对齐主流待办应用；有子任务不可转笔记） -->
      <div
        class="ctx-item"
        v-auth="'task:edit'"
        :class="{ 'ctx-disabled': !task.is_note && (task.subtask_total || 0) > 0 }"
        :title="!task.is_note && (task.subtask_total || 0) > 0 ? '含子任务的任务无法转换为笔记' : ''"
        @click="convertNote"
      >
        <component :is="task.is_note ? CheckSquare : BookOpen" :size="14" class="ctx-item-icon" />{{ task.is_note ? '转换为任务' : '转换为笔记' }}
      </div>

      <div class="ctx-divider" />

      <div class="ctx-item danger" v-auth="'task:delete'" @click="onDelete">
        <Trash2 :size="14" class="ctx-item-icon" />删除
      </div>
    </div>
    <!-- 关联主任务：顶级任务选择弹窗（对齐主流待办应用右键「关联主任务」） -->
    <el-dialog v-model="parentPickerOpen" title="关联主任务" width="360px" append-to-body>
      <div class="ctx-parent-picker">
        <el-input v-model="parentKw" placeholder="搜索任务" size="small" clearable @input="onParentSearch" />
        <div class="ctx-parent-list">
          <div v-for="p in parentCandidates" :key="p.id" class="ctx-parent-item" @click="pickParent(p)">
            <span class="ctx-parent-title">{{ p.title }}</span>
            <span class="ctx-parent-listname">{{ p.list_id ? store.lists.find((l) => l.id === p.list_id)?.name || '' : '收集箱' }}</span>
          </div>
          <div v-if="!parentCandidates.length" class="ctx-empty">无可用主任务</div>
        </div>
      </div>
    </el-dialog>
  </teleport>
</template>

<script setup>
import { nextTick, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import {
  Sun, Sunrise, CalendarPlus, CalendarRange, Calendar, CalendarX, Flag, Plus, Pin, FolderInput, Timer, Copy, Trash2,
  Tag, Check, ChevronRight, User, BookOpen, CheckSquare, Paperclip, LayoutTemplate, Link2, CornerUpRight,
} from 'lucide-vue-next'
import { useTaskStore } from '@/stores/task'
import { usePomodoroStore } from '@/stores/pomodoro'
import * as taskApi from '@/api/task'
import TaskDatePicker from './TaskDatePicker.vue'

// 任务行右键上下文菜单（对齐主流待办应用）：自绘固定定位菜单
// 使用：父组件 ref 调 open(clientX, clientY, task)；点击菜单外 / Esc 关闭
const store = useTaskStore()
const pomodoroStore = usePomodoroStore()

const visible = ref(false)
const newTag = ref('')
const task = ref(null)
const pos = ref({ x: 0, y: 0 })
const flipX = ref(false)
const flipY = ref(false)
const menuEl = ref(null)

const priorities = [
  { value: 3, color: '#f56c6c', tip: '高优先级' },
  { value: 2, color: '#e6a23c', tip: '中优先级' },
  { value: 1, color: '#409eff', tip: '低优先级' },
  { value: 0, color: '#9ca3af', tip: '无优先级' },
]

// 快捷日期（全天，当地 00:00 对应 UTC，对齐顺延/快捷项逻辑）
const dateActions = [
  { icon: Sun, tip: '今天', run: () => setDue(0) },
  { icon: Sunrise, tip: '明天', run: () => setDue(1) },
  { icon: CalendarPlus, tip: '下周', run: () => setDue(7) },
  { icon: CalendarRange, tip: '下月', run: setNextMonth },
]

// 下月：同日期下一个月的当天（对齐主流待办应用日期行第 4 个图标）
function setNextMonth() {
  run((t) => {
    const due = dayjs().add(1, 'month').startOf('day').toISOString()
    return store.updateTask(t.id, { due_at: due, all_day: true })
  })
}

// 复制链接：应用内定位链接（/task?open=<id>，打开应用自动展开该任务）
function copyTaskLink() {
  const t = task.value
  if (!t) return
  const url = `${location.origin}/task?open=${t.id}`
  navigator.clipboard?.writeText(url).then(
    () => ElMessage.success('链接已复制'),
    () => ElMessage.warning('复制失败')
  )
  close()
}

// 关联主任务：选择顶级任务作为父任务（对齐主流待办应用右键项）
const parentPickerOpen = ref(false)
const parentKw = ref('')
const parentCandidates = ref([])
async function openParentPicker() {
  close()
  parentKw.value = ''
  await searchParents('')
  parentPickerOpen.value = true
}
let _parentTimer = null
function onParentSearch() {
  clearTimeout(_parentTimer)
  _parentTimer = setTimeout(() => searchParents(parentKw.value), 300)
}
async function searchParents(q) {
  const res = await taskApi.fetchTasks({ q: q || undefined, limit: 50 }).catch(() => ({ items: [] }))
  parentCandidates.value = (res.items || []).filter(
    (x) => !x.is_deleted && !x.parent_id && x.id !== task.value?.id && !x.is_note
  )
}
async function pickParent(p) {
  if (!task.value) return
  await store.updateTask(task.value.id, { parent_id: p.id }).catch(() => {})
  ElMessage.success(`已关联到「${p.title}」`)
  parentPickerOpen.value = false
}

async function open(x, y, t) {
  task.value = t
  pos.value = { x, y }
  flipX.value = false
  flipY.value = false
  visible.value = true
  await nextTick()
  // 视口边缘防溢出：靠右/靠下时翻转
  const el = menuEl.value
  if (el) {
    const rect = el.getBoundingClientRect()
    if (x + rect.width > window.innerWidth - 8) {
      pos.value.x = Math.max(8, x - rect.width)
      flipX.value = true // 二级子菜单向左展开
    }
    if (y + rect.height > window.innerHeight - 8) {
      pos.value.y = Math.max(8, window.innerHeight - rect.height - 8)
      flipY.value = true // 二级子菜单向上展开
    }
  }
  document.addEventListener('click', onDocClick, true)
  document.addEventListener('contextmenu', onDocClick, true)
  document.addEventListener('keydown', onDocKeydown, true)
}

function close() {
  visible.value = false
  document.removeEventListener('click', onDocClick, true)
  document.removeEventListener('contextmenu', onDocClick, true)
  document.removeEventListener('keydown', onDocKeydown, true)
}

function onDocClick(e) {
  // 菜单内部与日期弹层（teleport 到 body）内的点击不关闭
  if (e.target.closest('.task-context-menu') || e.target.closest('.task-date-picker-popper')) return
  close()
}

function onDocKeydown(e) {
  if (e.key === 'Escape') close()
}

// ---------- 动作 ----------
async function run(action) {
  const t = task.value
  close()
  if (!t) return
  await action(t)
}

function setDue(days) {
  run((t) => {
    const due = days === null ? null : dayjs().add(days, 'day').startOf('day').toISOString()
    return store.updateTask(t.id, { due_at: due, ...(days === null ? {} : { all_day: true }) })
  })
}

function onPickDate({ due_at, all_day, start_at = null, reminders, persistent_reminder, recurrence }) {
  run((t) => {
    const data = { due_at, all_day, start_at }
    if (reminders !== undefined) data.reminders = reminders
    if (persistent_reminder !== undefined) data.persistent_reminder = persistent_reminder
    if (recurrence !== undefined) data.recurrence = recurrence
    return store.updateTask(t.id, data)
  })
}

function setPriority(priority) {
  run((t) => store.updateTask(t.id, { priority }))
}

function togglePin() {
  run((t) => store.updateTask(t.id, { is_pinned: !t.is_pinned }))
}

// 标签切换：勾选/取消（保持菜单打开可多选），本地同步勾选态
function toggleTag(tag) {
  const t = task.value
  if (!t) return
  const tags = t.tags?.includes(tag)
    ? t.tags.filter((x) => x !== tag)
    : [...(t.tags || []), tag]
  t.tags = tags // 乐观更新勾选态，失败由拦截器提示（store 局部替换会带回服务端值）
  store.updateTask(t.id, { tags }).catch(() => {})
}

function addTag() {
  const name = newTag.value.trim()
  if (!name) return
  const t = task.value
  if (t && !(t.tags || []).includes(name)) toggleTag(name)
  newTag.value = ''
}

function openMove() {
  const t = task.value
  close()
  if (t) store.openMoveDialog(t.id)
}

// 负责人：弹输入用户名，留空 = 清除负责人
async function onAssign() {
  const t = task.value
  close()
  if (!t) return
  try {
    const { value } = await ElMessageBox.prompt('输入负责人用户名，留空则清除', '负责人', {
      inputValue: t.assignee || '',
      confirmButtonText: '确定',
      cancelButtonText: '取消',
    })
    const assignee = (value || '').trim() || null
    if (assignee === (t.assignee || null)) return
    await store.updateTask(t.id, { assignee })
    ElMessage.success(assignee ? '已设置负责人' : '已清除负责人')
  } catch {
    // 取消或失败（失败由请求拦截器统一提示）
  }
}

function addSubtask() {
  run(async (t) => store.openDetail(t.id)) // 打开详情栏，在其中添加子任务
}

// 开始专注 › 子菜单（对齐主流待办应用：番茄计时 / 正计时 两种计时方式）
async function onFocus(minutes = null) {
  const t = task.value
  close()
  if (!t) return
  let mins = minutes
  if (mins === null) {
    // 主项点击 = 弹输入时长（兼容旧交互）
    try {
      const { value } = await ElMessageBox.prompt('专注时长（分钟），常用 15 / 25 / 45', '开始专注', {
        inputValue: String(pomodoroStore.focusConfig.pomodoro_minutes || 25),
        inputPattern: /^\d+$/,
        inputErrorMessage: '请输入数字分钟数',
      })
      mins = +value
    } catch {
      return // 用户取消
    }
  }
  if (mins === null) return
  try {
    await pomodoroStore.start(t.id, mins)
    pomodoroStore.openPanel()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail?.message || '开始失败')
  }
}

function onFocusCountdown() {
  onFocus(pomodoroStore.focusConfig.pomodoro_minutes || 25)
}

function onFocusStopwatch() {
  onFocus(0)
}

// 创建副本：复制标题/备注/清单/优先级/标签/日期，不含子任务/提醒/重复（对齐主流待办应用同名副本）；笔记副本保持笔记
function duplicate() {
  run(async (t) => {
    await store.createTask({
      title: t.title,
      note: t.note || null,
      list_id: t.list_id ?? null,
      priority: t.priority || 0,
      tags: [...(t.tags || [])],
      due_at: t.due_at || null,
      all_day: t.all_day ?? true,
      ...(t.is_note ? { is_note: true } : {}),
    })
    ElMessage.success('已创建副本')
  })
}

// 上传附件（笔记菜单，对齐主流待办应用）：选文件 → 一步到位上传到资源平台并登记引用
const fileInput = ref(null)
function onUploadClick() {
  if (!task.value) return
  fileInput.value?.click()
}
async function onFilePicked(e) {
  const file = e.target.files?.[0]
  e.target.value = '' // 允许重复选同一文件
  const t = task.value
  if (!file || !t) return
  close()
  try {
    await taskApi.uploadAttachment(t.id, file)
    ElMessage.success('附件已上传')
  } catch {
    // 失败由请求拦截器统一提示
  }
}

// 保存为笔记模板（对齐主流待办应用：把当前笔记内容存为模板，供快速添加 ⌄「从模板添加」复用）
async function saveAsTemplate() {
  const t = task.value
  close()
  if (!t) return
  const html = (t.note || '').trim()
  if (!html) return ElMessage.warning('笔记内容为空，无法保存模板')
  try {
    const { value } = await ElMessageBox.prompt('模板名称', '保存为笔记模板', {
      inputValue: t.title,
      confirmButtonText: '保存',
      cancelButtonText: '取消',
    })
    const name = (value || '').trim()
    if (!name) return
    const templates = store.settings?.note_templates || []
    await store.saveSettings({ note_templates: [...templates, { name, content_html: html }] })
    ElMessage.success('模板已保存')
  } catch {
    // 取消或失败（失败由请求拦截器统一提示）
  }
}

// 任务 ↔ 笔记 转换（有子任务的任务不可转笔记，对齐主流待办应用）
function convertNote() {
  run(async (t) => {
    const toNote = !t.is_note
    if (toNote && (t.subtask_total || 0) > 0) return
    await store.updateTask(t.id, { is_note: toNote })
    ElMessage.success(toNote ? '已转换为笔记' : '已转换为任务')
  })
}

// 删除：沿用现有二次确认流程
function onDelete() {
  const t = task.value
  close()
  if (!t) return
  const noun = t.is_note ? '笔记' : '任务'
  ElMessageBox.confirm(`删除${noun}「${t.title}」？`, `删除${noun}`, {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  })
    .then(() => store.deleteTask(t.id))
    .catch(() => {})
}

defineExpose({ open, close })
</script>

<style>
/* 非 scoped：组件 teleport 到 body，且需覆盖 teleported 内容 */
.task-context-menu {
  position: fixed;
  z-index: 3000;
  min-width: 180px;
  background: #fff;
  border-radius: 12px;
  box-shadow: var(--ss-shadow-lg, 0 8px 24px rgba(16, 24, 40, 0.12));
  border: 1px solid var(--ss-border, #e6e9f0);
  padding: 6px;
  font-size: 13px;
  color: var(--ss-text, #1f2937);
  user-select: none;
}
.task-context-menu .ctx-row {
  display: flex;
  gap: 4px;
  padding: 4px 6px;
}
.task-context-menu .ctx-icon-btn {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  cursor: pointer;
  flex-shrink: 0;
  color: var(--ss-text, #1f2937);
}
.task-context-menu .ctx-icon-btn:hover {
  background: var(--ss-primary-light, #eef1fe);
}
.task-context-menu .ctx-icon-btn.active {
  background: var(--ss-primary-light, #eef1fe);
  box-shadow: inset 0 0 0 1px var(--ss-primary, #4f6ef7);
}
.task-context-menu .ctx-divider {
  height: 1px;
  background: var(--ss-border, #e6e9f0);
  margin: 6px 4px;
}
.task-context-menu .ctx-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
}
.task-context-menu .ctx-item:hover {
  background: var(--ss-bg, #f3f5f9);
}
.task-context-menu .ctx-item.danger {
  color: var(--el-color-danger, #f56c6c);
}
/* 开始专注 › 子菜单（对齐主流待办应用） */
.task-context-menu .ctx-item.has-sub .sub-arrow {
  margin-left: auto;
  color: var(--ss-text-secondary, #909399);
}
.task-context-menu .ctx-sub {
  display: none;
  position: absolute;
  left: calc(100% - 4px);
  top: -6px;
  background: #fff;
  border: 1px solid var(--ss-border, #e6e9f0);
  border-radius: 10px;
  box-shadow: var(--ss-shadow-lg, 0 8px 24px rgba(16, 24, 40, 0.12));
  padding: 4px;
  min-width: 180px;
  z-index: 10;
}
.task-context-menu .ctx-item.has-sub:hover .ctx-sub {
  display: block;
}
.task-context-menu .ctx-sub .ctx-item {
  padding: 7px 10px;
}
.task-context-menu .sub-icon {
  font-size: 13px;
  width: 16px;
  text-align: center;
}
.task-context-menu .ctx-disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
.task-context-menu .ctx-item-icon {
  flex-shrink: 0;
}
.task-context-menu .ctx-submenu-arrow {
  margin-left: auto;
  color: var(--ss-text-muted, #9ca3af);
}
.task-context-menu .ctx-submenu {
  display: none;
  position: absolute;
  left: 100%;
  top: -6px;
  min-width: 160px;
  max-height: 280px;
  overflow-y: auto;
  background: #fff;
  border-radius: 12px;
  box-shadow: var(--ss-shadow-lg, 0 8px 24px rgba(16, 24, 40, 0.12));
  border: 1px solid var(--ss-border, #e6e9f0);
  padding: 6px;
}
.task-context-menu .ctx-submenu.flip-x {
  left: auto;
  right: 100%;
}
.task-context-menu .ctx-submenu.flip-y {
  top: auto;
  bottom: -6px;
}
.task-context-menu .ctx-submenu-trigger:hover .ctx-submenu {
  display: block;
}
.task-context-menu .ctx-check-on {
  color: var(--ss-primary, #4f6ef7);
}
.task-context-menu .ctx-check-blank {
  width: 13px;
  display: inline-block;
}
.task-context-menu .ctx-empty {
  padding: 8px 10px;
  color: var(--ss-text-muted, #9ca3af);
  font-size: 12px;
}
.task-context-menu .ctx-tag-new {
  padding: 4px 6px 2px;
}
.task-context-menu .ctx-color-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* 关联主任务选择弹窗 */
.ctx-parent-picker {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ctx-parent-list {
  max-height: 280px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.ctx-parent-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
}
.ctx-parent-item:hover {
  background: var(--ss-fill, #f7f7f9);
}
.ctx-parent-title {
  flex: 1;
  min-width: 0;
  font-size: 13px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.ctx-parent-listname {
  font-size: 12px;
  color: var(--ss-text-muted, #a8abb2);
  flex-shrink: 0;
}
</style>
