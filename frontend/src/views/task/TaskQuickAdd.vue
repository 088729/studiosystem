<template>
  <div class="task-quick-add" v-auth="'task:create'">
    <div class="qa-box" :class="{ expanded }">
      <!-- 标题行：回车创建 / Shift+回车展开描述 / Ctrl+回车创建 -->
      <div class="qa-title-row">
        <input
          ref="titleInput"
          v-model="title"
          class="qa-input"
          :placeholder="placeholder"
          @keydown.enter.exact.prevent="submit"
          @keydown.enter.shift.prevent="expandBox"
          @keydown.enter.ctrl.prevent="submit"
          @keydown.enter.meta.prevent="submit"
          @keydown.esc="onEsc"
        />
        <!-- 待创建的优先级/标签指示 -->
        <Flag
          v-if="pendingPriority"
          :size="14"
          :color="prioColorOf(pendingPriority)"
          :fill="prioColorOf(pendingPriority)"
          class="qa-indicator"
          title="已设优先级，点右侧下拉修改"
        />
        <span v-if="pendingTags.length" class="qa-indicator qa-tag-ind" :title="pendingTags.map((t) => '~' + t).join(' ')">
          <Tag :size="13" />{{ pendingTags.length }}
        </span>
        <!-- 日历：设置待创建任务的日期/提醒/重复（对齐主流待办应用输入框右侧日历图标） -->
        <TaskDatePicker
          :due-at="pendingDue?.due_at"
          :all-day="pendingDue?.all_day ?? true"
          :start-at="pendingDue?.start_at"
          :reminders="pendingDue?.reminders || []"
          :persistent-reminder="pendingDue?.persistent_reminder"
          :recurrence="pendingDue?.recurrence"
          @change="onDatePick"
        >
          <template #trigger>
            <Calendar
              :size="18"
              class="qa-cal"
              :class="{ active: !!pendingDue?.due_at }"
              :title="pendingDue?.due_at ? '已设日期，点击修改' : '设置日期'"
            />
          </template>
        </TaskDatePicker>
        <ChevronDown :size="15" class="qa-chev" :class="{ open: menuOpen }" title="快速设置" @click.stop="menuOpen = !menuOpen" />
      </div>

      <!-- 描述（Shift+回车或完整输入框模式展开） -->
      <!-- 语法实时预览条（对齐主流待办应用：输入时即时展示解析出的清单/优先级/日期/标签） -->
      <div v-if="hasPreview && !expanded" class="qa-preview">
        <span v-if="preview.listName" class="qa-pv-chip qa-pv-list">#{{ preview.listName }}</span>
        <span v-if="preview.unknownList" class="qa-pv-chip qa-pv-newlist" :title="`将新建清单「${preview.unknownList}」`">＋新建清单 "{{ preview.unknownList }}"</span>
        <span v-if="preview.priority" class="qa-pv-chip" :style="{ color: prioColorOf(preview.priority) }">
          <Flag :size="12" :color="prioColorOf(preview.priority)" :fill="prioColorOf(preview.priority)" />{{ { 3: '高优先级', 2: '中优先级', 1: '低优先级' }[preview.priority] }}
        </span>
        <span v-if="previewDueText" class="qa-pv-chip qa-pv-due">📅 {{ previewDueText }}</span>
        <span v-for="tg in preview.tags || []" :key="tg" class="qa-pv-chip qa-pv-tag">~{{ tg }}</span>
      </div>
      <textarea
        v-if="expanded"
        ref="descInput"
        v-model="desc"
        class="qa-desc"
        placeholder="描述"
        rows="3"
        @keydown.enter.ctrl.prevent="submit"
        @keydown.enter.meta.prevent="submit"
        @keydown.esc="onEsc"
      />
      <div v-if="expanded" class="qa-footer">
        <el-button type="primary" size="small" :disabled="!title.trim()" @click="submit">添加</el-button>
        <span class="qa-hint">{{ isMac ? 'Command' : 'Ctrl' }}+Enter 添加</span>
      </div>

      <!-- 右侧下拉菜单（对齐主流待办应用）：优先级 / 清单› / 标签› / 从模板添加›（笔记清单）/ 输入框设置 -->
      <div v-if="menuOpen" class="qa-menu" @click.stop @contextmenu.stop.prevent>
        <div class="qa-menu-label">优先级</div>
        <div class="qa-prios">
          <Flag
            v-for="p in prioOptions"
            :key="p.value"
            :size="20"
            :color="p.color"
            :fill="p.value ? p.color : 'none'"
            class="qa-prio"
            :class="{ active: pendingPriority === p.value }"
            :title="p.label"
            @click="pickPriority(p.value)"
          />
        </div>
        <div class="qa-menu-item" @mouseenter="sub = 'list'" @mouseleave="sub = null">
          <Inbox :size="14" class="qa-menu-icon" />{{ pendingListName }}
          <ChevronRight :size="13" class="qa-menu-arrow" />
          <div v-if="sub === 'list'" class="qa-sub">
            <div class="qa-menu-item" @click="pickList(null)">
              跟随当前视图<Check v-if="!pendingListId" :size="14" class="qa-check" />
            </div>
            <div v-for="l in store.lists" :key="l.id" class="qa-menu-item" @click="pickList(l.id)">
              <component v-if="listIconOf(l.icon)" :is="listIconOf(l.icon)" :size="14" :style="{ color: l.color, flexShrink: 0 }" />
              <span v-else class="qa-dot" :style="{ background: l.color }" />{{ l.name }}
              <Check v-if="pendingListId === l.id" :size="14" class="qa-check" />
            </div>
          </div>
        </div>
        <div class="qa-menu-item" @mouseenter="sub = 'tag'" @mouseleave="sub = null">
          <Tag :size="14" class="qa-menu-icon" />标签
          <ChevronRight :size="13" class="qa-menu-arrow" />
          <div v-if="sub === 'tag'" class="qa-sub">
            <div v-if="!store.tagCounts.length" class="qa-menu-empty">暂无标签，输入 ~标签 创建</div>
            <div v-for="t in store.tagCounts" :key="t.tag" class="qa-menu-item" @click="toggleTag(t.tag)">
              ~{{ t.tag }}
              <Check v-if="pendingTags.includes(t.tag)" :size="14" class="qa-check" />
            </div>
          </div>
        </div>
        <!-- 从模板添加（对齐主流待办应用笔记模板：仅创建目标为笔记清单时出现，选中即建笔记） -->
        <div v-if="noteTargetList" class="qa-menu-item" @mouseenter="sub = 'tpl'" @mouseleave="sub = null">
          <LayoutTemplate :size="14" class="qa-menu-icon" />从模板添加
          <ChevronRight :size="13" class="qa-menu-arrow" />
          <div v-if="sub === 'tpl'" class="qa-sub">
            <div v-if="!noteTemplates.length" class="qa-menu-empty">暂无模板，可在设置「模板」或笔记编辑器工具栏「模板」中保存</div>
            <div v-for="(t, i) in noteTemplates" :key="i" class="qa-menu-item" :title="t.name" @click="pickTemplate(t)">
              <span class="qa-tpl-name">{{ t.name }}</span>
            </div>
          </div>
        </div>
        <div class="qa-menu-item" @click="toggleFullMode">
          <Settings2 :size="14" class="qa-menu-icon" />完整输入框
          <Check v-if="fullMode" :size="14" class="qa-check" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Calendar, ChevronDown, ChevronRight, Check, Flag, Inbox, LayoutTemplate, Tag, Settings2 } from 'lucide-vue-next'
import dayjs from 'dayjs'
import TaskDatePicker from './TaskDatePicker.vue'
import { recomputeReminders } from './utils'
import { listIconOf } from '@/utils/listIcons'
import { useTaskStore } from '@/stores/task'

const store = useTaskStore()
// 尽早预拉任务默认值：日历弹层「时间段」预填时长/提醒默认值预览都依赖它，
// 不能等 TaskManager onMounted 串行拉完清单/任务/统计才轮到（数据量大时太晚）
if (!store.settings) store.fetchSettings().catch(() => {})
// global=true：全局添加条（Ctrl/Cmd+Alt+A 唤起，对齐主流待办应用「全局添加」）
// ——不受当前视图影响：不注入智能清单自动日期、不继承当前清单，默认落收集箱
const props = defineProps({ global: { type: Boolean, default: false } })
const emit = defineEmits(['created'])
const title = ref('')
const desc = ref('')
const titleInput = ref(null)
const descInput = ref(null)
const isMac = /Mac/.test(navigator.platform)

// 展开态：完整输入框模式（localStorage 持久，「输入框设置」切换）或 Shift+回车临时展开
const fullMode = ref(localStorage.getItem('qa-full-input') === '1')
const tempExpanded = ref(false)
const expanded = computed(() => fullMode.value || tempExpanded.value)

// 待创建属性：右侧下拉设置，创建时并入
const pendingPriority = ref(0)
const pendingListId = ref(null) // null=跟随当前视图/默认规则
const pendingTags = ref([])
// 待创建日期：日历弹层提交 { due_at, all_day, start_at, reminders, recurrence }；清除后归 null
const pendingDue = ref(null)
function onDatePick(p) {
  pendingDue.value = p.due_at
    ? { ...p, reminders: recomputeReminders(p.reminders || [], p.due_at) }
    : null
}

// 下拉菜单
const menuOpen = ref(false)
const sub = ref(null)
function closeMenu() {
  menuOpen.value = false
  sub.value = null
}
const onDocClick = () => closeMenu()
watch(menuOpen, (v) => {
  if (v) document.addEventListener('click', onDocClick, true)
  else document.removeEventListener('click', onDocClick, true)
})
onBeforeUnmount(() => document.removeEventListener('click', onDocClick, true))

const prioOptions = [
  { value: 3, label: '高优先级', color: '#ef4444' },
  { value: 2, label: '中优先级', color: '#f59e0b' },
  { value: 1, label: '低优先级', color: '#3b82f6' },
  { value: 0, label: '无优先级', color: '#8f959e' },
]
const prioColorOf = (v) => prioOptions.find((p) => p.value === v)?.color || '#8f959e'

const pendingListName = computed(() =>
  pendingListId.value ? store.lists.find((l) => l.id === pendingListId.value)?.name || '收集箱' : '收集箱'
)

// 「从模板添加」（对齐主流待办应用笔记模板）：仅当创建目标为笔记清单时出现（全局添加条落收集箱=任务，不显示）
const noteTemplates = computed(() => store.settings?.note_templates || [])
const noteTargetList = computed(() => {
  if (props.global) return null
  if (pendingListId.value) return store.lists.find((l) => l.id === pendingListId.value) || null
  return store.activeList?.kind === 'note' ? store.activeList : null
})

function pickPriority(v) {
  pendingPriority.value = v
  closeMenu()
  titleInput.value?.focus()
}
function pickList(id) {
  pendingListId.value = id
  closeMenu()
  titleInput.value?.focus()
}
function toggleTag(tag) {
  const i = pendingTags.value.indexOf(tag)
  if (i >= 0) pendingTags.value.splice(i, 1)
  else pendingTags.value.push(tag)
}
function toggleFullMode() {
  fullMode.value = !fullMode.value
  localStorage.setItem('qa-full-input', fullMode.value ? '1' : '0')
  closeMenu()
}

// 从模板添加（对齐主流待办应用：选中即建笔记——标题=输入框标题（空则取模板名），正文=模板内容）
async function pickTemplate(t) {
  const data = parseQuickAdd(title.value)
  data.title = data.title || t.name
  data.note = t.content_html
  data.is_note = true
  if (pendingPriority.value) data.priority = pendingPriority.value
  if (pendingTags.value.length) data.tags = [...new Set([...(data.tags || []), ...pendingTags.value])]
  // 日历弹层已设日期时并入（模板只负责正文，不注入智能清单自动日期/任务默认值）
  if (pendingDue.value?.due_at) {
    data.due_at = pendingDue.value.due_at
    data.all_day = pendingDue.value.all_day
    if (pendingDue.value.start_at) data.start_at = pendingDue.value.start_at
  }
  data.list_id = noteTargetList.value?.id || null
  closeMenu()
  await store.createTask(data)
  title.value = ''
  desc.value = ''
  pendingPriority.value = 0
  pendingListId.value = null
  pendingTags.value = []
  pendingDue.value = null
  if (!fullMode.value) tempExpanded.value = false
  ElMessage.success(`已按模板「${t.name}」创建笔记`)
  emit('created')
  nextTick(() => titleInput.value?.focus())
}

// Shift+回车：展开描述并聚焦（对齐主流待办应用）
function expandBox() {
  if (expanded.value) return
  tempExpanded.value = true
  nextTick(() => descInput.value?.focus())
}

function onEsc() {
  if (menuOpen.value) return closeMenu()
  if (tempExpanded.value && !fullMode.value) tempExpanded.value = false
}

// 占位文案随当前清单变化（对齐主流待办应用：「添加任务至“收集箱”」；全局添加条固定落收集箱；笔记清单说「添加笔记」）
const placeholder = computed(() => {
  if (expanded.value) return store.activeList?.kind === 'note' ? '笔记标题' : '任务标题'
  const noun = store.activeList?.kind === 'note' ? '笔记' : '任务'
  return props.global
    ? `+ 添加${noun}至“收集箱”，回车保存（支持 #清单 !优先级 @日期 ~标签）`
    : `+ 添加${noun}至“${store.activeTitle || '收集箱'}”，回车保存（支持 #清单 !优先级 @日期 ~标签）`
})

const WEEKDAY = { 一: 1, 二: 2, 三: 3, 四: 4, 五: 5, 六: 6, 日: 0 }

// 智能清单快速添加时自动带日期（对齐主流待办应用）：今天→今天18:00、明天→明天18:00，其余不注入
function defaultDueForSmart(key) {
  if (key === 'smart:today') return dayjs().hour(18).minute(0).second(0).toISOString()
  if (key === 'smart:tomorrow') return dayjs().add(1, 'day').hour(18).minute(0).second(0).toISOString()
  return null
}

// 快捷语法解析（纯语法层，供提交与实时预览共用）：# 清单、! 优先级、@ 日期时间、~ 标签
// unknownList = # 后的名称未命中任何清单（预览提示「将新建清单」，提交时自动创建）
function parseSyntax(input) {
  const data = {}
  const tags = []
  let text = input

  text = text.replace(/~([^\s#@!~]+)/g, (_, t) => { tags.push(t); return '' })

  text = text.replace(/!(高|中|低|[123])/g, (_, p) => {
    data.priority = { 高: 3, 中: 2, 低: 1, '3': 3, '2': 2, '1': 1 }[p]
    return ''
  })

  // @日期时间：今天/明天/下周/下周三/周三/3天后/MM-DD/YYYY-MM-DD，可叠加 18:00
  // 未指定时刻 = 全天（all_day=true）；无法解析的片段保留在标题中
  text = text.replace(/@([^\s#@!~]+)/g, (raw, token) => {
    let day = dayjs()
    let hm = null
    const tm = token.match(/(\d{1,2}):(\d{2})/)
    if (tm) { hm = { h: +tm[1], m: +tm[2] }; token = token.replace(tm[0], '').trim() }
    let matched = true
    if (token === '今天') day = dayjs()
    else if (token === '明天') day = dayjs().add(1, 'day')
    else if (token === '下周') day = dayjs().add(7, 'day')
    else if (/^下周[一二三四五六日]$/.test(token)) day = dayjs().add(7 - dayjs().day() + WEEKDAY[token[2]], 'day')
    else if (/^周?[一二三四五六日]$/.test(token)) {
      const d = (WEEKDAY[token[token.length - 1]] - dayjs().day() + 7) % 7 || 7
      day = dayjs().add(d, 'day')
    } else if (/^(\d+)天后$/.test(token)) day = dayjs().add(+RegExp.$1, 'day')
    else {
      const parsed = dayjs(token.length <= 5 ? `${dayjs().year()}-${token}` : token)
      if (parsed.isValid()) day = parsed
      else matched = false
    }
    if (!matched) return raw // 保留在标题
    if (hm) {
      data.due_at = day.hour(hm.h).minute(hm.m).second(0).toISOString()
      data.all_day = false
    } else {
      data.due_at = day.startOf('day').toISOString()
      data.all_day = true
    }
    return ''
  })

  // #清单：精确 → includes → startsWith 三级模糊；未命中返回 unknownList（不静默丢弃）
  text = text.replace(/#([^\s#@!~]+)/g, (raw, name) => {
    const hit = store.lists.find((l) => l.name === name)
      || store.lists.find((l) => l.name.includes(name))
      || store.lists.find((l) => l.name.startsWith(name))
    if (hit) {
      data.list_id = hit.id
      data.listName = hit.name
      return ''
    }
    data.unknownList = name
    return ''
  })

  data.title = text.replace(/\s+/g, ' ').trim()
  if (tags.length) data.tags = tags
  return data
}

function parseQuickAdd(input) {
  const data = parseSyntax(input)
  delete data.listName
  delete data.unknownList
  return data
}

// 实时预览条：输入时即时展示语法解析结果（对齐主流待办应用：解析结果在输入框下方实时预览）
const preview = computed(() => {
  const t = title.value.trim()
  if (!t) return null
  return parseSyntax(t)
})
const previewDueText = computed(() => {
  const p = preview.value
  if (!p?.due_at) return ''
  const d = dayjs(p.due_at)
  const date = d.format('M月D日')
  return p.all_day ? date : `${date} ${d.format('HH:mm')}`
})
const hasPreview = computed(() => {
  const p = preview.value
  return !!p && !!(p.due_at || p.priority || p.listName || p.unknownList || (p.tags && p.tags.length))
})

async function submit() {
  const syntax = parseSyntax(title.value)
  const data = parseQuickAdd(title.value)
  if (!data.title) return

  // #清单 未命中：自动创建新清单（对齐主流待办应用「新建清单」）
  if (syntax.unknownList) {
    try {
      const created = await store.createList({ name: syntax.unknownList })
      data.list_id = created.id
      if (!data.tags) data.tags = []
      ElMessage.success(`已新建清单「${syntax.unknownList}」`)
    } catch {
      ElMessage.warning(`清单「${syntax.unknownList}」创建失败，任务将落收集箱`)
    }
  }

  // 下拉设置的待创建属性并入（快捷语法显式写的优先）
  if (!data.priority && pendingPriority.value) data.priority = pendingPriority.value
  if (pendingTags.value.length) data.tags = [...new Set([...(data.tags || []), ...pendingTags.value])]
  if (desc.value.trim()) data.note = desc.value.trim()

  // 未写 @ 时用日历弹层设置的日期（快捷语法显式写的优先）
  if (!data.due_at && pendingDue.value?.due_at) {
    data.due_at = pendingDue.value.due_at
    data.all_day = pendingDue.value.all_day
    if (pendingDue.value.start_at) data.start_at = pendingDue.value.start_at
    if (pendingDue.value.reminders?.length) data.reminders = pendingDue.value.reminders
    if (pendingDue.value.persistent_reminder) data.persistent_reminder = true
    if (pendingDue.value.recurrence) data.recurrence = pendingDue.value.recurrence
  }
  // 未写 @ 且当前是「今天/明天」智能清单 → 自动带日期，避免任务落收集箱后"消失"（01，优先级高于默认值）
  // 全局添加条不受当前视图影响，跳过此注入
  if (!props.global && !data.due_at && store.activeListKey.startsWith('smart:')) {
    data.due_at = defaultDueForSmart(store.activeListKey)
  }
  // 清单：下拉显式选择 > 快捷语法 # > 当前自定义清单视图（全局添加条不继承）> 默认值/收集箱
  if (pendingListId.value) {
    data.list_id = pendingListId.value
  } else if (!props.global && !data.list_id && store.activeListKey.startsWith('list:')) {
    data.list_id = store.activeListKey.replace('list:', '')
  }
  store.applyDefaults(data)

  await store.createTask(data)
  // 今天/明天/最近7天视图创建后重拉，确保新任务即时可见
  if (['smart:today', 'smart:tomorrow', 'smart:next7'].includes(store.activeListKey)) {
    await store.fetchTasks()
  }
  title.value = ''
  desc.value = ''
  pendingPriority.value = 0
  pendingListId.value = null
  pendingTags.value = []
  pendingDue.value = null
  if (!fullMode.value) tempExpanded.value = false
  ElMessage.success('已创建')
  emit('created')
  nextTick(() => titleInput.value?.focus())
}
</script>

<style scoped>
.task-quick-add {
  flex-shrink: 0;
  position: relative;
}
/* 输入框卡片（对齐主流待办应用：白底圆角，展开带描述） */
.qa-box {
  position: relative;
  background: #fff;
  border: 1px solid var(--ss-border);
  border-radius: 8px;
  padding: 0 10px;
}
.qa-box:focus-within {
  border-color: var(--ss-primary);
}
.qa-title-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.qa-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 14px;
  padding: 10px 0;
  background: transparent;
  color: var(--ss-text);
}
.qa-input::placeholder {
  color: var(--ss-text-muted);
}
/* 语法实时预览条（对齐主流待办应用：输入框下方即时展示解析结果） */
.qa-preview {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  padding: 0 0 8px;
}
.qa-pv-chip {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--ss-fill, #f7f7f9);
  color: var(--ss-text-secondary, #909399);
  max-width: 200px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.qa-pv-list {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
}
.qa-pv-newlist {
  color: #b8860b;
  background: #fdf6ec;
}
.qa-pv-due {
  color: var(--ss-text, #303133);
}
.qa-pv-tag {
  color: var(--ss-text-secondary, #909399);
}
.qa-indicator {
  flex-shrink: 0;
  color: var(--ss-text-muted);
  display: flex;
  align-items: center;
  gap: 2px;
  font-size: 12px;
}
.qa-chev {
  flex-shrink: 0;
  color: var(--ss-text-muted);
  cursor: pointer;
  border-radius: 4px;
  padding: 2px;
  transition: transform 0.15s;
}
.qa-cal {
  flex-shrink: 0;
  color: var(--ss-text-muted);
  cursor: pointer;
  border-radius: 4px;
  padding: 2px;
  box-sizing: content-box;
}
.qa-cal:hover {
  background: var(--ss-bg);
  color: var(--ss-text);
}
.qa-cal.active {
  color: var(--ss-primary);
}
/* 日历弹层触发器去掉聚焦 outline */
.qa-box :deep(.el-tooltip__trigger) {
  outline: none;
  display: flex;
  align-items: center;
}
.qa-chev:hover {
  background: var(--ss-bg);
  color: var(--ss-text);
}
.qa-chev.open {
  transform: rotate(180deg);
}
.qa-desc {
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  font-size: 13px;
  font-family: inherit;
  color: var(--ss-text);
  background: transparent;
  border-top: 1px solid var(--ss-border);
  padding: 8px 0;
  box-sizing: border-box;
}
.qa-desc::placeholder {
  color: var(--ss-text-muted);
}
.qa-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  padding-bottom: 8px;
}
.qa-hint {
  font-size: 12px;
  color: var(--ss-text-muted);
}
/* 右侧下拉菜单 */
.qa-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 168px;
  background: #fff;
  border: 1px solid var(--ss-border);
  border-radius: 8px;
  box-shadow: 0 6px 24px rgb(0 0 0 / 12%);
  padding: 6px;
  z-index: 30;
}
.qa-menu-label {
  font-size: 12px;
  color: var(--ss-text-muted);
  padding: 2px 8px 6px;
}
.qa-prios {
  display: flex;
  gap: 8px;
  padding: 2px 8px 10px;
  border-bottom: 1px solid var(--ss-border);
  margin-bottom: 4px;
}
.qa-prio {
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
}
.qa-prio:hover,
.qa-prio.active {
  background: var(--ss-bg);
}
.qa-menu-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 8px;
  font-size: 13px;
  color: var(--ss-text);
  border-radius: 5px;
  cursor: pointer;
  white-space: nowrap;
}
.qa-menu-item:hover {
  background: var(--ss-bg);
}
.qa-menu-icon {
  color: var(--ss-text-muted);
  flex-shrink: 0;
}
.qa-menu-arrow {
  margin-left: auto;
  color: var(--ss-text-muted);
}
.qa-check {
  margin-left: auto;
  color: var(--ss-primary);
}
.qa-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.qa-menu-empty {
  padding: 7px 8px;
  font-size: 12px;
  color: var(--ss-text-muted);
}
/* 模板名超长省略（qa-menu-item 为 flex，子项需 min-width:0 才能 ellipsis） */
.qa-tpl-name {
  min-width: 0;
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* 子菜单向左展开（对齐主流待办应用） */
.qa-sub {
  position: absolute;
  right: 100%;
  top: -6px;
  margin-right: 2px;
  min-width: 140px;
  max-height: 260px;
  overflow-y: auto;
  background: #fff;
  border: 1px solid var(--ss-border);
  border-radius: 8px;
  box-shadow: 0 6px 24px rgb(0 0 0 / 12%);
  padding: 4px;
}
</style>
