<template>
  <!-- 时间线：点击已有任务条弹出的迷你任务卡片（对齐主流待办应用）。定位由父组件算好（内容坐标） -->
  <div class="tl-view" :style="{ left: left + 'px', top: top + 'px' }" @click.stop @pointerdown.stop>
    <div v-if="detail" class="tl-view-card">
      <!-- 头部：日期（过期红色 延期N天）+ 优先级旗 -->
      <div class="tl-view-head">
        <TaskDatePicker
          :task-id="detail.id"
          :due-at="detail.due_at"
          :all-day="detail.all_day"
          :start-at="detail.start_at"
          :reminders="detail.reminders"
          :persistent-reminder="detail.persistent_reminder"
          :recurrence="detail.recurrence"
          :disabled="!canEdit"
          @change="onDateChange"
        >
          <template #trigger="{ label }">
            <span class="tl-view-date" :class="{ overdue: overdueDays > 0 }">
              <Calendar :size="14" />
              {{ label || '无日期' }}<template v-if="overdueDays > 0">, 延期{{ overdueDays }}天</template>
            </span>
          </template>
        </TaskDatePicker>
        <el-dropdown trigger="click" :disabled="!canEdit" @command="onPriority">
          <span class="tl-view-flag" :title="'优先级：' + prioLabel(detail.priority || 0)">
            <Flag :size="15" :color="prioColor(detail.priority || 0)" :fill="detail.priority ? prioColor(detail.priority) : 'none'" />
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-for="o in prioOptions" :key="o.value" :command="o.value">
                <Flag :size="12" :color="o.color" :fill="o.value ? o.color : 'none'" style="margin-right: 6px; vertical-align: -1px" />{{ o.label }}
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>

      <!-- 标题（单行，回车 → 焦点进详情，失焦保存） -->
      <div class="tl-view-title-row">
        <input
          v-model="titleDraft"
          class="tl-view-title"
          :readonly="!canEdit"
          @keydown.enter.prevent="focusNote"
          @blur="saveTitle"
          @keydown.esc.stop="$event.target.value = detail.title; $event.target.blur()"
        />
      </div>

      <!-- 详情（时间线无详情页，备注在卡片内直接编辑，对齐主流待办应用） -->
      <textarea
        ref="noteRef"
        v-model="noteDraft"
        class="tl-view-note-edit"
        @input="autoGrow"
        placeholder="添加详情"
        :readonly="!canEdit"
        @blur="saveNote"
        @keydown.esc.stop="$event.target.blur()"
      />

      <!-- 子任务清单（复选框勾选完成） -->
      <div v-if="detail.subtasks?.length" class="tl-view-subs">
        <div v-for="s in detail.subtasks" :key="s.id" class="tl-view-sub" :class="{ done: s.status === 'done' }">
          <span class="tl-view-cb" @click="canEdit && toggleSub(s)">
            <Check v-if="s.status === 'done'" :size="11" />
          </span>
          <span class="tl-view-sub-title">{{ s.title }}</span>
        </div>
      </div>

      <!-- 标签编辑行（⋯ → 标签 展开，change 即保存，收起下拉时隐藏） -->
      <div v-if="showTagRow" class="tl-view-tags">
        <el-select
          v-model="tagsDraft"
          multiple
          filterable
          allow-create
          default-first-option
          collapse-tags
          size="small"
          placeholder="+ 标签"
          @change="saveTags"
          @visible-change="(v) => !v && (showTagRow = false)"
        >
          <el-option v-for="t in store.tags" :key="t.id" :value="t.name" :label="t.name" />
        </el-select>
      </div>

      <!-- 评论区（常驻，对齐主流待办应用：输入框总在底部，带表情/图片按钮；content 支持 markdown 图片） -->
      <div v-if="comments.length" class="tl-view-comments">
        <div class="tl-view-comments-head">评论 {{ comments.length }}</div>
        <div v-for="c in comments" :key="c.id" class="tl-view-comment">
          <span class="tl-view-avatar"><User :size="14" /></span>
          <div class="tl-view-comment-main">
            <div class="tl-view-comment-meta">
              <span class="tl-view-comment-author">{{ c.author }}</span>
              <span class="tl-view-comment-time">{{ fmtRelative(c.created_at) }}</span>
              <span v-if="c.author === authStore.userInfo?.username" class="tl-view-comment-ops">
                <span class="tl-view-comment-op" title="编辑" @click="startEdit(c)"><PenLine :size="13" /></span>
                <span class="tl-view-comment-op" title="删除" @click="delComment(c)"><Trash2 :size="13" /></span>
              </span>
            </div>
            <input
              v-if="editId === c.id"
              v-model="editDraft"
              class="tl-view-comment-edit"
              @keydown.enter="saveEdit(c)"
              @keydown.esc.stop="editId = null"
              @blur="saveEdit(c)"
            />
            <div v-else class="tl-view-comment-content">
              <template v-for="(seg, i) in parseContent(c.content)" :key="i">
                <img v-if="seg.img" :src="seg.img" class="tl-view-comment-img" @click="openImage(seg.img)" />
                <span v-else>{{ seg.text }}</span>
              </template>
            </div>
          </div>
        </div>
      </div>
      <!-- 待发图片缩略图（可移除） -->
      <div v-if="draftImages.length" class="tl-view-draft-imgs">
        <span v-for="(u, i) in draftImages" :key="u" class="tl-view-draft-img">
          <img :src="u" />
          <span class="tl-view-draft-img-x" @click="draftImages.splice(i, 1)">×</span>
        </span>
      </div>
      <div class="tl-view-comment-input">
        <input
          ref="commentInputRef"
          v-model="commentDraft"
          placeholder="添加评论"
          @keydown.enter="sendComment"
        />
        <el-popover placement="top-end" trigger="click" :width="284" popper-class="tl-emoji-pop">
          <template #reference>
            <span class="tl-view-ci-btn" title="表情"><Smile :size="16" /></span>
          </template>
          <div class="tl-emoji-grid">
            <span v-for="e in EMOJIS" :key="e" class="tl-emoji-cell" @click="insertEmoji(e)">{{ e }}</span>
          </div>
        </el-popover>
        <span class="tl-view-ci-btn" title="图片" @click="imgInputRef?.click()"><Image :size="16" /></span>
        <input ref="imgInputRef" type="file" accept="image/*" style="display: none" @change="onPickImage" />
      </div>

      <!-- 底部：所在清单（点击移动）+ 更多 -->
      <div class="tl-view-foot">
        <span class="tl-view-list" title="移动到" @click="canEdit && store.openMoveDialog(detail.id)">
          <Inbox v-if="!detail.list_id" :size="14" />
          <span v-else class="tl-view-list-dot" :style="{ background: listColor }" />
          {{ listName }}
        </span>
        <div class="tl-view-foot-actions">
          <span class="tl-view-icon" title="评论" @click="focusComment">
            <MessageSquare :size="15" />
          </span>
          <el-dropdown trigger="click" @command="onMore">
          <span class="tl-view-icon"><MoreHorizontal :size="16" /></span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item v-if="canEdit" command="pin">
                <Pin :size="13" style="margin-right: 6px; vertical-align: -2px" />{{ detail.is_pinned ? '取消置顶' : '置顶' }}
              </el-dropdown-item>
              <el-dropdown-item v-if="canEdit" command="tags">
                <Tag :size="13" style="margin-right: 6px; vertical-align: -2px" />标签
              </el-dropdown-item>
              <el-dropdown-item v-if="canEdit" command="attach">
                <Paperclip :size="13" style="margin-right: 6px; vertical-align: -2px" />上传附件
              </el-dropdown-item>
              <el-dropdown-item v-if="authStore.hasPerm('task:run')" command="focus">
                <Timer :size="13" style="margin-right: 6px; vertical-align: -2px" />开始专注
              </el-dropdown-item>
              <el-dropdown-item v-if="canEdit" command="duplicate" divided>
                <Copy :size="13" style="margin-right: 6px; vertical-align: -2px" />创建副本
              </el-dropdown-item>
              <el-dropdown-item v-if="canEdit" command="delete"><span style="color: #e64a3b">删除任务</span></el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
        <input ref="attachInputRef" type="file" style="display: none" @change="onAttachFile" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import dayjs from 'dayjs'
import { Calendar, Flag, Inbox, Check, MoreHorizontal, MessageSquare, Trash2, PenLine, User, Smile, Image, Pin, Tag, Paperclip, Timer, Copy } from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'
import { usePomodoroStore } from '@/stores/pomodoro'
import { useTaskStore } from '@/stores/task'
import { useAuthStore } from '@/stores/auth'
import * as taskApi from '@/api/task'
import TaskDatePicker from '../TaskDatePicker.vue'

// 附件图片地址兜底：与 api/task.js 的 attachmentUrl 一致（本地存储为 /uploads 相对路径）
const attachmentUrl = (resourceId) => `/uploads/${String(resourceId).replace(/^\//, '')}`

const props = defineProps({
  taskId: { type: [Number, String], required: true },
  left: { type: Number, default: 0 },
  top: { type: Number, default: 0 },
})
const emit = defineEmits(['close'])

const store = useTaskStore()
const authStore = useAuthStore()
const pomodoroStore = usePomodoroStore()

const prioOptions = [
  { value: 3, label: '高优先级', color: '#f56c6c' },
  { value: 2, label: '中优先级', color: '#e6a23c' },
  { value: 1, label: '低优先级', color: '#409eff' },
  { value: 0, label: '无优先级', color: '#9ca3af' },
]
const prioColor = (p) => prioOptions.find((o) => o.value === p)?.color
const prioLabel = (p) => prioOptions.find((o) => o.value === p)?.label

const detail = ref(null)
const titleDraft = ref('')
const noteDraft = ref('')
const noteRef = ref(null)
// 详情为自适应高度 textarea：输入时按内容撑高（回车即换行）
function autoGrow(e) {
  const el = e.target
  el.style.height = 'auto'
  el.style.height = el.scrollHeight + 'px'
}
function growNote() {
  nextTick(() => {
    const el = noteRef.value
    if (!el) return
    el.style.height = 'auto'
    el.style.height = el.scrollHeight + 'px'
  })
}
// 标题回车 → 焦点进详情（详情多行编辑）
function focusNote() {
  noteRef.value?.focus()
}
// 备注存的是 HTML（详情栏富文本），卡片内按纯文本编辑：取出文本，保存时还原纯文本
function htmlToText(html) {
  if (!html) return ''
  const el = document.createElement('div')
  el.innerHTML = html
  return (el.innerText || '').trim()
}
async function load() {
  detail.value = await taskApi.fetchTask(props.taskId)
  titleDraft.value = detail.value?.title || ''
  noteDraft.value = htmlToText(detail.value?.note)
  growNote()
  loadComments()
}
onMounted(() => {
  load()
  window.addEventListener('pointerdown', onGlobalDown, true)
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => {
  window.removeEventListener('pointerdown', onGlobalDown, true)
  window.removeEventListener('keydown', onKey)
})

// 点卡片/弹层外部关闭（日期弹层等是 teleport 的）
function onGlobalDown(e) {
  if (e.target.closest('.tl-view, .el-popper, .el-select-dropdown, .el-overlay')) return
  emit('close')
}
function onKey(e) {
  if (e.key === 'Escape' && !e.target.closest('.el-popper')) emit('close')
}

const canEdit = computed(() => {
  if (!detail.value) return false
  if (detail.value.owner === authStore.userInfo?.username) return true
  return authStore.hasPerm('task:update')
})

// 截止日期已过 → 红色「延期N天」（对齐主流待办应用）
const overdueDays = computed(() => {
  if (!detail.value?.due_at || detail.value.status === 'done') return 0
  return Math.max(0, dayjs().startOf('day').diff(dayjs(detail.value.due_at).startOf('day'), 'day'))
})

const listName = computed(() => {
  if (!detail.value?.list_id) return '收集箱'
  return store.lists.find((l) => l.id === detail.value.list_id)?.name || '收集箱'
})
const listColor = computed(() => store.lists.find((l) => l.id === detail.value?.list_id)?.color || '#4772fa')

async function saveTitle() {
  const v = titleDraft.value.trim()
  if (!detail.value || !v || v === detail.value.title) {
    titleDraft.value = detail.value?.title || ''
    return
  }
  await store.updateTask(detail.value.id, { title: v })
  await load()
}
async function saveNote() {
  if (!detail.value || !canEdit.value) return
  const v = noteDraft.value.trim()
  if (v === htmlToText(detail.value.note)) return
  await store.updateTask(detail.value.id, { note: v || null })
  await load()
}
async function onDateChange(payload) {
  if (!detail.value) return
  await store.updateTask(detail.value.id, payload)
  await load()
}
async function onPriority(p) {
  if (!detail.value) return
  await store.updateTask(detail.value.id, { priority: p })
  await load()
}
async function toggleSub(s) {
  await taskApi.completeTask(s.id, s.status !== 'done')
  await load()
}

// ---------- 评论（常驻，对齐主流待办应用：输入框带表情/图片，content 支持 markdown 图片） ----------
const comments = ref([])
const commentDraft = ref('')
const commentInputRef = ref(null)
const imgInputRef = ref(null)
const draftImages = ref([]) // 待发送的图片 url（上传已完成）
async function loadComments() {
  const res = await taskApi.fetchComments(props.taskId)
  comments.value = res?.items || []
}
// 底部 💬 → 滚动并聚焦评论输入框
function focusComment() {
  nextTick(() => {
    const el = commentInputRef.value
    el?.scrollIntoView({ block: 'nearest' })
    el?.focus()
  })
}
// 表情：光标处插入
const EMOJIS = [
  '😀', '😁', '😂', '🤣', '😃', '😄', '😅', '😉', '😊', '😋', '😎', '😍', '😘', '🥰', '🤗', '🤔',
  '😐', '😑', '🙄', '😏', '😮', '😪', '😴', '😌', '😛', '😜', '🤤', '😒', '🙃', '😲', '😖', '😞',
  '😤', '😢', '😭', '😱', '😳', '🤪', '😵', '😡', '🤬', '😷', '🤒', '🤕', '🤢', '🤮', '🥴', '😇',
  '🥳', '🥺', '🤠', '🤡', '🤫', '🤭', '🧐', '🤓', '👍', '👎', '👏', '🙏', '💪', '🤝', '✌️', '👌',
  '❤️', '💔', '💯', '🎉', '🔥', '✨', '⭐', '✅', '❌', '⚠️', '📌', '💡', '⏰', '🚀', '🎯', '🏆',
]
function insertEmoji(e) {
  const el = commentInputRef.value
  if (!el) {
    commentDraft.value += e
    return
  }
  const s = el.selectionStart ?? commentDraft.value.length
  const t = el.selectionEnd ?? commentDraft.value.length
  commentDraft.value = commentDraft.value.slice(0, s) + e + commentDraft.value.slice(t)
  nextTick(() => {
    el.focus()
    el.setSelectionRange(s + e.length, s + e.length)
  })
}
// 图片：上传到配置的存储后端，成功加入待发列表
async function onPickImage(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  if (file.size > 5 * 1024 * 1024) {
    ElMessage.warning('图片大小不能超过 5MB')
    return
  }
  try {
    const res = await taskApi.uploadCommentImage(file)
    draftImages.value.push(res.url || attachmentUrl(res.path))
  } catch {
    ElMessage.error('图片上传失败')
  }
}
// content 里的 markdown 图片 → 渲染缩略图，其余按文本
function parseContent(content) {
  const segs = []
  const re = /!\[[^\]]*\]\(([^)\s]+)\)/g
  let last = 0
  let m
  const text = content || ''
  while ((m = re.exec(text))) {
    if (m.index > last) segs.push({ text: text.slice(last, m.index) })
    segs.push({ img: m[1] })
    last = m.index + m[0].length
  }
  if (last < text.length) segs.push({ text: text.slice(last) })
  return segs
}
function openImage(url) {
  window.open(url, '_blank')
}
async function sendComment() {
  const v = commentDraft.value.trim()
  const imgs = draftImages.value
  if (!v && !imgs.length) return
  commentDraft.value = ''
  draftImages.value = []
  let content = v
  for (const u of imgs) content += `${content ? '\n' : ''}![](${u})`
  await taskApi.addComment(props.taskId, content)
  await loadComments()
}
async function delComment(c) {
  await taskApi.deleteComment(c.id)
  await loadComments()
}
// 行内编辑（仅自己的评论显示编辑入口，后端同限作者本人）
const editId = ref(null)
const editDraft = ref('')
function startEdit(c) {
  editId.value = c.id
  editDraft.value = c.content
}
async function saveEdit(c) {
  if (editId.value !== c.id) return
  const v = editDraft.value.trim()
  editId.value = null
  if (!v || v === c.content) return
  await taskApi.updateComment(c.id, v)
  await loadComments()
}
// 相对时间（对齐主流待办应用：刚刚 / N分钟前 / N小时前 / 昨天 HH:mm / M月D日）
function fmtRelative(t) {
  if (!t) return ''
  const d = dayjs(t)
  const mins = dayjs().diff(d, 'minute')
  if (mins < 1) return '刚刚'
  if (mins < 60) return `${mins}分钟前`
  const hours = dayjs().diff(d, 'hour')
  if (hours < 24 && d.isSame(dayjs(), 'day')) return `${hours}小时前`
  if (d.isSame(dayjs().subtract(1, 'day'), 'day')) return `昨天 ${d.format('HH:mm')}`
  return d.format('M月D日')
}

async function onMore(cmd) {
  if (!detail.value) return
  if (cmd === 'delete') {
    await store.deleteTask(detail.value.id)
    emit('close')
  } else if (cmd === 'pin') {
    await store.updateTask(detail.value.id, { is_pinned: !detail.value.is_pinned })
    await load()
  } else if (cmd === 'tags') {
    tagsDraft.value = [...(detail.value.tags || [])]
    showTagRow.value = true
  } else if (cmd === 'attach') {
    attachInputRef.value?.click()
  } else if (cmd === 'focus') {
    startFocus()
  } else if (cmd === 'duplicate') {
    duplicateTask()
  }
}

// ---------- ⋯ 菜单：标签 / 附件 / 专注 / 副本（复用详情抽屉同款逻辑） ----------
const attachInputRef = ref(null)
const showTagRow = ref(false)
const tagsDraft = ref([])
async function saveTags(v) {
  if (!detail.value) return
  await store.updateTask(detail.value.id, { tags: v })
  await load()
}
async function onAttachFile(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file || !detail.value) return
  try {
    await taskApi.uploadAttachment(detail.value.id, file)
    ElMessage.success('附件已上传')
  } catch {
    ElMessage.error('附件上传失败')
  }
}
async function startFocus() {
  try {
    const { value } = await ElMessageBox.prompt('专注时长（分钟），常用 15 / 25 / 45', '开始专注', {
      inputValue: '25',
      inputPattern: /^\d+$/,
      inputErrorMessage: '请输入数字分钟数',
    })
    await pomodoroStore.start(detail.value.id, +value)
    pomodoroStore.openPanel()
  } catch {
    /* 用户取消 */
  }
}
// 对齐主流待办应用：复制标题/备注/清单/优先级/标签/日期，不含子任务/提醒/重复
async function duplicateTask() {
  const t = detail.value
  if (!t) return
  await store.createTask({
    title: t.title,
    note: t.note || null,
    list_id: t.list_id ?? null,
    priority: t.priority || 0,
    tags: [...(t.tags || [])],
    due_at: t.due_at || null,
    all_day: t.all_day ?? true,
  })
  ElMessage.success('已创建副本')
}
</script>

<style scoped>
.tl-view {
  position: absolute;
  z-index: 10;
}
.tl-view-card {
  width: 400px;
  max-height: min(560px, 70vh);
  overflow-y: auto;
  background: #fff;
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.16);
  border: 1px solid rgba(0, 0, 0, 0.06);
}
.tl-view-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 11px 16px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  position: sticky;
  top: 0;
  background: #fff;
  z-index: 1;
}
.tl-view-date {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: var(--ss-primary);
  cursor: pointer;
}
.tl-view-date.overdue {
  color: #e64a3b;
}
.tl-view-flag {
  display: inline-flex;
  align-items: center;
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
}
.tl-view-flag:hover {
  background: rgba(0, 0, 0, 0.05);
}
.tl-view-title-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 16px 4px;
}
.tl-view-title {
  flex: 1;
  border: none;
  outline: none;
  font-size: 15px;
  font-weight: 600;
  color: #333;
  background: transparent;
  font-family: inherit;
  padding: 0;
}
.tl-view-icon {
  display: inline-flex;
  align-items: center;
  color: #999;
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  flex-shrink: 0;
}
.tl-view-icon:hover {
  background: rgba(0, 0, 0, 0.05);
  color: #666;
}
.tl-view-note-edit {
  display: block;
  width: 100%;
  box-sizing: border-box;
  border: none;
  outline: none;
  resize: none;
  font-size: 13px;
  font-family: inherit;
  line-height: 1.6;
  color: #555;
  background: transparent;
  padding: 4px 16px 4px;
  min-height: 60px;
  overflow: hidden;
}
.tl-view-note-edit::placeholder {
  color: #c5c5c5;
}
.tl-view-subs {
  margin: 8px 16px 0;
}
.tl-view-sub {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  font-size: 13px;
  color: #333;
}
.tl-view-sub.done .tl-view-sub-title {
  color: #b0b0b0;
  text-decoration: line-through;
}
.tl-view-cb {
  width: 15px;
  height: 15px;
  border: 1.5px solid #c0c4cc;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #fff;
  flex-shrink: 0;
}
.tl-view-sub.done .tl-view-cb {
  background: var(--ss-primary);
  border-color: var(--ss-primary);
}
.tl-view-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px 12px;
  position: sticky;
  bottom: 0;
  background: #fff;
}
.tl-view-list {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #333;
  cursor: pointer;
  padding: 3px 6px;
  margin-left: -6px;
  border-radius: 5px;
}
.tl-view-list:hover {
  background: rgba(0, 0, 0, 0.04);
}
.tl-view-foot-actions {
  display: inline-flex;
  align-items: center;
  gap: 10px;
}
.tl-view-icon.active {
  color: var(--ss-primary);
}
/* 评论区（对齐主流待办应用） */
.tl-view-comments {
  margin: 4px 16px 0;
  max-height: 180px;
  overflow-y: auto;
}
.tl-view-comments-head {
  font-size: 12px;
  color: #999;
  padding: 6px 0 4px;
}
.tl-view-comment {
  display: flex;
  gap: 8px;
  padding: 8px 0;
}
.tl-view-avatar {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #e8e8e8;
  color: #b0b0b0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.tl-view-comment-main {
  flex: 1;
  min-width: 0;
}
.tl-view-comment-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}
.tl-view-comment-author {
  font-size: 12px;
  font-weight: 600;
  color: #555;
}
.tl-view-comment-time {
  font-size: 11px;
  color: #b0b0b0;
}
.tl-view-comment-ops {
  margin-left: auto;
  display: none;
  gap: 8px;
}
.tl-view-comment:hover .tl-view-comment-ops {
  display: inline-flex;
}
.tl-view-comment-op {
  color: #c0c4cc;
  cursor: pointer;
  display: inline-flex;
}
.tl-view-comment-op:hover {
  color: #666;
}
.tl-view-comment-content {
  font-size: 13px;
  color: #333;
  line-height: 1.5;
  margin-top: 2px;
  white-space: pre-wrap;
  word-break: break-word;
}
.tl-view-comment-edit {
  width: 100%;
  margin-top: 2px;
  height: 26px;
  padding: 0 8px;
  font-size: 13px;
  border: 1px solid var(--ss-primary);
  border-radius: 5px;
  outline: none;
  box-sizing: border-box;
  font-family: inherit;
}
.tl-view-comment-input {
  display: flex;
  align-items: center;
  gap: 4px;
  margin: 8px 16px 0;
  background: rgba(0, 0, 0, 0.04);
  border: 1px solid transparent;
  border-radius: 6px;
  padding-right: 6px;
  transition: border-color 0.15s, background 0.15s;
}
.tl-view-comment-input:focus-within {
  background: #fff;
  border-color: var(--ss-primary);
}
.tl-view-comment-input input {
  flex: 1;
  min-width: 0;
  height: 34px;
  padding: 0 10px;
  font-size: 13px;
  border: none;
  outline: none;
  box-sizing: border-box;
  font-family: inherit;
  background: transparent;
}
/* 输入框右侧表情/图片按钮（对齐主流待办应用） */
.tl-view-ci-btn {
  display: inline-flex;
  align-items: center;
  color: #999;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  flex-shrink: 0;
}
.tl-view-ci-btn:hover {
  background: rgba(0, 0, 0, 0.06);
  color: #666;
}
/* 表情选择面板 */
.tl-emoji-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 2px;
}
.tl-emoji-cell {
  font-size: 18px;
  text-align: center;
  padding: 4px 0;
  border-radius: 5px;
  cursor: pointer;
  line-height: 1.2;
}
.tl-emoji-cell:hover {
  background: rgba(0, 0, 0, 0.06);
}
/* 评论里的图片缩略图（点击新窗口看原图） */
.tl-view-comment-img {
  display: block;
  max-width: 140px;
  max-height: 100px;
  border-radius: 6px;
  margin-top: 4px;
  cursor: zoom-in;
  border: 1px solid rgba(0, 0, 0, 0.08);
}
/* 待发图片缩略图 */
.tl-view-draft-imgs {
  display: flex;
  gap: 8px;
  margin: 8px 16px 0;
  flex-wrap: wrap;
}
.tl-view-draft-img {
  position: relative;
  display: inline-block;
}
.tl-view-draft-img img {
  width: 44px;
  height: 44px;
  object-fit: cover;
  border-radius: 6px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  display: block;
}
.tl-view-draft-img-x {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.55);
  color: #fff;
  font-size: 11px;
  line-height: 16px;
  text-align: center;
  cursor: pointer;
}
.tl-view-list-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
/* ⋯ → 标签 编辑行 */
.tl-view-tags {
  padding: 6px 16px 0;
}
.tl-view-tags .el-select {
  width: 100%;
}
</style>
