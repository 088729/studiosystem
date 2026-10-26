<template>
  <el-dialog
    :model-value="modelValue"
    :title="preset ? '编辑常用专注' : '添加常用专注'"
    width="480px"
    :close-on-click-modal="false"
    @update:model-value="(v) => emit('update:modelValue', v)"
    @open="onOpen"
  >
    <div class="fpd">
      <!-- 名称行（对齐主流待办应用桌面版：彩圆图标+铅笔角标 ｜ 名称输入内嵌链条按钮） -->
      <div class="fpd-name-row">
        <el-popover
          v-model:visible="iconPopVisible"
          placement="bottom-start"
          :width="348"
          trigger="click"
          popper-class="fpd-icon-popper"
        >
          <template #reference>
            <span class="fpd-icobtn" :style="{ background: form.color }" title="选择图标">
              {{ iconPreview }}
              <span class="fpd-icoedit"><Pencil :size="10" /></span>
            </span>
          </template>
          <!-- 图标选择面板（图标/文字双态，对齐主流待办应用移动端宫格收进选择器） -->
          <div class="fpd-iconpop">
            <div class="fpd-preview-pair">
              <div class="fpd-pv" :class="{ on: iconTab === 'icon' }" @click="iconTab = 'icon'">
                <span class="fpd-pv-circle" :style="{ background: form.color }">{{ form.icon }}</span>
                <span class="fpd-pv-label">图标</span>
              </div>
              <div class="fpd-pv" :class="{ on: iconTab === 'text' }" @click="iconTab = 'text'">
                <span class="fpd-pv-circle" :style="{ background: form.color }">{{ textPreview }}</span>
                <span class="fpd-pv-label">文字</span>
              </div>
            </div>
            <div v-if="iconTab === 'icon'" class="fpd-grid">
              <span
                v-for="ic in ICONS"
                :key="ic.e"
                class="fpd-cell"
                :class="{ on: form.icon === ic.e && form.color === ic.c }"
                :style="{ background: ic.c }"
                @click="pickIcon(ic)"
              >{{ ic.e }}</span>
            </div>
            <div v-else class="fpd-textmode">
              <el-input v-model="textChar" placeholder="一个字" maxlength="1" class="fpd-char" />
              <div class="fpd-colors">
                <span
                  v-for="c in COLORS"
                  :key="c"
                  class="fpd-dot"
                  :class="{ on: form.color === c }"
                  :style="{ background: c }"
                  @click="form.color = c"
                ></span>
              </div>
            </div>
          </div>
        </el-popover>
        <el-input v-model="form.name" placeholder="名称" maxlength="50" class="fpd-name">
          <template #suffix>
            <!-- 关联任务选择器（链条按钮弹出，对齐主流待办应用：内嵌输入框右侧） -->
            <el-popover
              v-model:visible="pickerVisible"
              placement="bottom-end"
              :width="360"
              trigger="click"
              popper-class="fpd-picker-popper"
              @show="onPickerShow"
            >
              <template #reference>
                <span class="fpd-link-btn" :class="{ on: !!form.task_id }" :title="linkedTask ? `已关联：${linkedTask.title}` : '关联任务'">
                  <Link2 :size="15" />
                </span>
              </template>
              <div class="fpd-picker">
                <!-- 任务 / 习惯 两个 tab（对齐主流待办应用 165cc645） -->
                <el-radio-group v-model="pickerTab" size="small" class="fpd-pick-tabs">
                  <el-radio-button value="task">任务</el-radio-button>
                  <el-radio-button value="habit">习惯</el-radio-button>
                </el-radio-group>
                <template v-if="pickerTab === 'task'">
                  <el-input v-model="kw" placeholder="搜索任务" size="small" clearable @input="onSearchInput" />
                  <div class="fpd-picker-body">
                    <template v-if="groupedCandidates.length">
                      <div v-for="g in groupedCandidates" :key="g.key" class="fpd-pg">
                        <div class="fpd-pg-head">
                          <span class="fpd-pg-name">{{ g.name }}</span>
                          <span class="fpd-pg-count">{{ g.tasks.length }}</span>
                        </div>
                        <div
                          v-for="t in g.tasks"
                          :key="t.id"
                          class="fpd-picker-item"
                          @click="chooseTask(t)"
                        >
                          <span class="fpd-pick-radio" :class="{ on: form.task_id === t.id }"></span>
                          <span class="fpd-picker-title">{{ t.title }}</span>
                          <span v-if="dueText(t)" class="fpd-picker-due">{{ dueText(t) }}</span>
                        </div>
                      </div>
                    </template>
                    <div v-else class="fpd-picker-empty">{{ kw ? '无匹配任务' : '暂无任务' }}</div>
                  </div>
                </template>
                <template v-else>
                  <div class="fpd-picker-body">
                    <div v-for="h in habitCandidates" :key="h.id" class="fpd-picker-item" @click="chooseHabit(h)">
                      <span class="fpd-pick-radio" :class="{ on: form.habit_id === h.id }"></span>
                      <span class="fpd-habit-ico">{{ h.icon }}</span>
                      <span class="fpd-picker-title">{{ h.name }}</span>
                      <span v-if="h.today_checked" class="fpd-picker-due">✓ 今日已达标</span>
                    </div>
                    <div v-if="!habitCandidates.length" class="fpd-picker-empty">暂无习惯</div>
                  </div>
                </template>
              </div>
            </el-popover>
          </template>
        </el-input>
      </div>
      <!-- 关联 chip：任务 or 习惯 -->
      <div v-if="linkedTask" class="fpd-link-chip">
        {{ linkedTask.title }}
        <span class="fpd-link-x" @click="clearLink"><X :size="12" /></span>
      </div>
      <div v-else-if="linkedHabit" class="fpd-link-chip">
        {{ linkedHabit.icon }} {{ linkedHabit.name }}
        <span class="fpd-link-x" @click="clearLink"><X :size="12" /></span>
      </div>

      <!-- 计时模式（对齐主流待办应用桌面版：纯行式 radio，选中行内嵌时长输入） -->
      <div class="fpd-sec">
        <div class="fpd-sec-title">计时模式</div>
        <div class="fpd-mode-line" :class="{ on: form.mode === 'countdown' }" @click="form.mode = 'countdown'">
          <span class="fpd-radio" :class="{ on: form.mode === 'countdown' }"></span>
          <span class="fpd-mode-name">番茄计时</span>
          <span v-if="form.mode === 'countdown'" class="fpd-dur-inline" @click.stop>
            <el-input-number
              v-model="form.duration_minutes"
              :min="1"
              :max="180"
              size="small"
              controls-position="right"
            />
            <span class="fpd-dur-unit">分钟</span>
          </span>
        </div>
        <div class="fpd-mode-line" :class="{ on: form.mode === 'stopwatch' }" @click="form.mode = 'stopwatch'">
          <span class="fpd-radio" :class="{ on: form.mode === 'stopwatch' }"></span>
          <span class="fpd-mode-name">正计时</span>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="fpd-footer">
        <el-button type="primary" round :disabled="!form.name.trim()" @click="save">保存</el-button>
        <el-button round @click="emit('update:modelValue', false)">取消</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Link2, X, Pencil } from 'lucide-vue-next'
import dayjs from 'dayjs'
import { fetchTasks, fetchTask } from '@/api/task'
import { fetchHabits } from '@/api/habit'
import { useTaskStore } from '@/stores/task'
import { usePomodoroStore } from '@/stores/pomodoro'

const props = defineProps({
  modelValue: Boolean,
  preset: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'saved'])

const store = usePomodoroStore()
const taskStore = useTaskStore()

// 对齐主流待办应用图标宫格：彩圆 emoji（e=emoji，c=底色）
const ICONS = [
  { e: '😊', c: '#a3e635' }, { e: '🐱', c: '#fb923c' }, { e: '🧠', c: '#f87171' },
  { e: '📖', c: '#38bdf8' }, { e: '🏃', c: '#4ade80' }, { e: '🍌', c: '#facc15' },
  { e: '☀️', c: '#fbbf24' }, { e: '🧊', c: '#67e8f9' }, { e: '🐧', c: '#a5b4fc' },
  { e: '💬', c: '#4ade80' }, { e: '✏️', c: '#fbbf24' }, { e: '🧘', c: '#e879f9' },
  { e: '📰', c: '#93c5fd' }, { e: '🌙', c: '#818cf8' }, { e: '🍳', c: '#fda4af' },
  { e: '📄', c: '#7dd3fc' }, { e: '📋', c: '#60a5fa' }, { e: '☕', c: '#fcd34d' },
  { e: '📷', c: '#5eead4' }, { e: '🔤', c: '#a78bfa' }, { e: '🎧', c: '#86efac' },
  { e: '🍙', c: '#fca5a5' }, { e: '⭐', c: '#f0abfc' }, { e: '🏓', c: '#fdba74' },
  { e: '🍅', c: '#f87171' },
]
const COLORS = ['#4f6ef7', '#22c55e', '#f97316', '#eab308', '#ef4444', '#8b5cf6', '#ec4899', '#14b8a6']

const form = ref({
  name: '',
  icon: '🍅',
  color: '#f87171',
  mode: 'countdown',
  duration_minutes: 25,
  task_id: null,
  habit_id: null,
})
const iconTab = ref('icon')
const textChar = ref('')
const linkedTask = ref(null)
const linkedHabit = ref(null)
const kw = ref('')
const candidates = ref([])
const pickerVisible = ref(false)
const iconPopVisible = ref(false)
const pickerTab = ref('task')
const habitCandidates = ref([])

const textPreview = computed(() => (textChar.value ? textChar.value : '文'))
// 图标按钮预览：文字态显示单字，图标态显示 emoji
const iconPreview = computed(() => (iconTab.value === 'text' ? textPreview.value : form.value.icon))
const isEmoji = (s) => /(\u00a9|\u00ae|[\u2000-\u3300]|\ud83c[\ud000-\udfff]|\ud83d[\ud000-\udfff]|\ud83e[\ud000-\udfff])/.test(s)

watch(textChar, (ch) => {
  if (iconTab.value === 'text' && ch) form.value.icon = ch
})

async function onOpen() {
  const p = props.preset
  form.value = {
    name: p?.name || '',
    icon: p?.icon || '🍅',
    color: p?.color || '#f87171',
    mode: p?.mode || 'countdown',
    duration_minutes: p?.duration_minutes || 25,
    task_id: p?.task_id || null,
    habit_id: p?.habit_id || null,
  }
  iconTab.value = p && !isEmoji(p.icon) ? 'text' : 'icon'
  textChar.value = iconTab.value === 'text' ? p.icon : ''
  linkedTask.value = null
  linkedHabit.value = null
  kw.value = ''
  candidates.value = []
  pickerVisible.value = false
  iconPopVisible.value = false
  pickerTab.value = 'task'
  if (p?.task_id) {
    const t = await fetchTask(p.task_id).catch(() => null)
    linkedTask.value = t || null
  }
  if (p?.habit_id) {
    await loadHabits()
    linkedHabit.value = habitCandidates.value.find((h) => h.id === p.habit_id) || null
  }
}

// 习惯 tab 数据（关联习惯：完成专注自动打卡）
async function loadHabits() {
  const res = await fetchHabits({ tz_offset_minutes: -new Date().getTimezoneOffset() }).catch(() => ({ items: [] }))
  habitCandidates.value = (res.items || []).filter((h) => !h.is_archived)
}

function pickIcon(ic) {
  form.value.icon = ic.e
  form.value.color = ic.c
}

// ---------- 关联任务选择器（对齐主流待办应用：搜索 + 按清单分组 + 单选圈 + 右侧截止） ----------
function onPickerShow() {
  kw.value = ''
  searchTasks('')
  loadHabits()
}

let _searchTimer = null
function onSearchInput() {
  clearTimeout(_searchTimer)
  _searchTimer = setTimeout(() => searchTasks(kw.value), 300)
}

async function searchTasks(q) {
  const res = await fetchTasks({ q: q || undefined, limit: 100 }).catch(() => ({ items: [] }))
  candidates.value = (res.items || []).filter((t) => !t.is_deleted && t.status !== 'done').slice(0, 60)
}

const groupedCandidates = computed(() => {
  const groups = []
  const byList = new Map()
  for (const t of candidates.value) {
    const key = t.list_id || '__inbox__'
    if (!byList.has(key)) byList.set(key, [])
    byList.get(key).push(t)
  }
  const listName = (id) => (id ? taskStore.lists.find((l) => l.id === id)?.name || '其他' : '收集箱')
  // 有清单的按清单顺序排，收集箱垫后
  const ordered = [...byList.entries()].sort((a, b) => {
    if (a[0] === '__inbox__') return 1
    if (b[0] === '__inbox__') return -1
    const ia = taskStore.lists.findIndex((l) => l.id === a[0])
    const ib = taskStore.lists.findIndex((l) => l.id === b[0])
    return (ia === -1 ? 999 : ia) - (ib === -1 ? 999 : ib)
  })
  for (const [id, tasks] of ordered) groups.push({ key: id, name: listName(id), tasks })
  return groups
})

function dueText(t) {
  if (!t.due_at) return ''
  const d = dayjs(t.due_at)
  const today = dayjs().startOf('day')
  const diff = d.startOf('day').diff(today, 'day')
  if (diff === 0) return d.format('HH:mm')
  if (diff > 0 && diff <= 7) return d.format('M月D日')
  return d.format('M月D日')
}

function chooseTask(t) {
  linkedTask.value = t
  linkedHabit.value = null
  form.value.task_id = t.id
  form.value.habit_id = null
  pickerVisible.value = false
}

function chooseHabit(h) {
  linkedHabit.value = h
  linkedTask.value = null
  form.value.habit_id = h.id
  form.value.task_id = null
  pickerVisible.value = false
}

function clearLink() {
  linkedTask.value = null
  linkedHabit.value = null
  form.value.task_id = null
  form.value.habit_id = null
}

async function save() {
  if (!form.value.name.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  const icon = iconTab.value === 'text' ? textChar.value || '文' : form.value.icon
  await store.savePreset({ ...form.value, icon, name: form.value.name.trim() }, props.preset?.id || null)
  emit('update:modelValue', false)
  emit('saved')
  ElMessage.success(props.preset ? '已保存' : '已创建')
}
</script>

<style scoped>
.fpd {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
/* 名称行：输入框 + 右侧链条按钮（对齐主流待办应用） */
.fpd-name-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.fpd-name {
  flex: 1;
}
.fpd-name :deep(.el-input__wrapper) {
  border-radius: 10px;
}
/* 链条按钮（对齐主流待办应用：输入框 suffix 内小 icon，关联后高亮） */
.fpd-link-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--ss-text-secondary, #909399);
  cursor: pointer;
  transition: color 0.15s;
}
.fpd-link-btn:hover {
  color: var(--el-color-primary);
}
.fpd-link-btn.on {
  color: var(--el-color-primary);
}
.fpd-link-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-radius: 999px;
  padding: 3px 10px;
  width: fit-content;
}
.fpd-link-x {
  display: inline-flex;
  cursor: pointer;
  opacity: 0.7;
}
.fpd-link-x:hover {
  opacity: 1;
}
.fpd-sec-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--ss-text, #303133);
  margin-bottom: 10px;
}
/* 图标/文字双预览圆 */
.fpd-preview-pair {
  display: flex;
  gap: 18px;
  margin-bottom: 12px;
}
.fpd-pv {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  cursor: pointer;
}
.fpd-pv-circle {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 19px;
  color: #fff;
  border: 2px solid transparent;
  transition: transform 0.1s;
}
.fpd-pv:hover .fpd-pv-circle {
  transform: scale(1.06);
}
.fpd-pv.on .fpd-pv-circle {
  border-color: var(--ss-text, #303133);
}
.fpd-pv-label {
  font-size: 12px;
  color: var(--ss-text-secondary, #909399);
  padding: 1px 10px;
  border-radius: 999px;
}
.fpd-pv.on .fpd-pv-label {
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  font-weight: 500;
}
.fpd-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 8px;
}
.fpd-cell {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  color: #fff;
  cursor: pointer;
  border: 2px solid transparent;
  transition: transform 0.1s;
}
.fpd-cell:hover {
  transform: scale(1.1);
}
.fpd-cell.on {
  border-color: var(--ss-text, #303133);
}
.fpd-textmode {
  display: flex;
  align-items: center;
  gap: 12px;
}
.fpd-char {
  width: 90px;
}
.fpd-colors {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.fpd-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;
}
.fpd-dot.on {
  border-color: var(--ss-text, #303133);
}
/* 计时模式（对齐主流待办应用桌面版：纯行式，选中行高亮，时长内嵌） */
.fpd-modes {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.fpd-mode-line {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 9px 10px;
  border-radius: 10px;
  cursor: pointer;
}
.fpd-mode-line:hover {
  background: var(--ss-fill, #f7f7f9);
}
.fpd-mode-line.on {
  background: var(--el-color-primary-light-9);
}
.fpd-radio {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 1.5px solid var(--ss-border-dark, #c0c4cc);
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.fpd-radio.on {
  border-color: var(--el-color-primary);
}
.fpd-radio.on::after {
  content: '';
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--el-color-primary);
}
.fpd-mode-name {
  font-size: 14px;
  color: var(--ss-text, #303133);
}
.fpd-dur-inline {
  margin-left: 12px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.fpd-dur-unit {
  font-size: 13px;
  color: var(--ss-text-secondary, #909399);
}
/* 名称行图标按钮（对齐主流待办应用：彩圆 + 铅笔角标） */
.fpd-icobtn {
  position: relative;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 19px;
  color: #fff;
  cursor: pointer;
  flex-shrink: 0;
  transition: transform 0.1s;
}
.fpd-icobtn:hover {
  transform: scale(1.05);
}
.fpd-icoedit {
  position: absolute;
  right: -2px;
  bottom: -2px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--ss-text, #303133);
  color: #fff;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #fff;
}
.fpd-iconpop {
  display: flex;
  flex-direction: column;
}
.fpd-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
/* 选择器（分组 + 单选圈） */
.fpd-pick-tabs {
  display: flex;
  justify-content: center;
}
.fpd-picker {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.fpd-habit-ico {
  font-size: 14px;
  flex-shrink: 0;
}
.fpd-picker-body {
  max-height: 300px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.fpd-pg-head {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px 4px;
  font-size: 12px;
  color: var(--ss-text-secondary, #909399);
}
.fpd-pg-name {
  font-weight: 600;
}
.fpd-picker-item {
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
}
.fpd-picker-item:hover {
  background: var(--ss-fill, #f7f7f9);
}
.fpd-pick-radio {
  width: 15px;
  height: 15px;
  border-radius: 50%;
  border: 1.5px solid var(--ss-border-dark, #c0c4cc);
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.fpd-pick-radio.on {
  border-color: var(--el-color-primary);
}
.fpd-pick-radio.on::after {
  content: '';
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--el-color-primary);
}
.fpd-picker-title {
  font-size: 13px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  flex: 1;
}
.fpd-picker-due {
  font-size: 12px;
  color: var(--ss-text-muted, #a8abb2);
  font-variant-numeric: tabular-nums;
}
.fpd-picker-empty {
  padding: 24px 0;
  text-align: center;
  font-size: 12px;
  color: var(--ss-text-secondary, #909399);
}
</style>
