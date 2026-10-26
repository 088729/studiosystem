<template>
  <!-- 底部迷你专注条（对齐主流待办应用：🍅 + 「准备做什么？」输入框回车开始 + 时间 + ▶/状态），专注主页与常用专注列表共用 -->
  <div class="mini-bar" @click="emit('bar-click')">
    <span class="mb-emoji">🍅</span>
    <div class="mb-mid">
      <template v-if="store.isRunning">
        <div class="mb-title">{{ miniTitle }}</div>
      </template>
      <template v-else>
        <!-- 对齐主流待办应用：输入任务名回车直接开始（匹配已有任务则关联） -->
        <input
          v-model="draft"
          class="mb-input"
          placeholder="准备做什么？"
          @keyup.enter="onEnter"
          @click.stop
        />
      </template>
      <div class="mb-time">{{ miniTime }}</div>
    </div>
    <span v-if="!store.isRunning" class="mb-play" title="开始专注" @click.stop="onMiniPlay">
      <Play :size="15" fill="currentColor" />
    </span>
    <span v-else class="mb-state">{{ store.paused ? '已暂停' : '专注中' }}</span>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Play } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { fetchTasks } from '@/api/task'
import { usePomodoroStore } from '@/stores/pomodoro'
import { useTaskStore } from '@/stores/task'
import { useHabitStore } from '@/stores/habit'

const emit = defineEmits(['bar-click'])
const store = usePomodoroStore()
const taskStore = useTaskStore()
const habitStore = useHabitStore()

const miniTitle = computed(() => {
  if (store.isRunning) {
    return store.currentPreset?.name || taskTitleOf(store.current?.task_id) || (store.current?.habit_id ? habitNameOf(store.current.habit_id) : '') || '专注中'
  }
  return '准备做什么？'
})
function habitNameOf(id) {
  return habitStore.habits.find((h) => h.id === id)?.name || ''
}
const miniTime = computed(() => {
  if (store.isRunning) return store.displayText
  return store.mode === 'stopwatch' ? '00:00' : `${String(store.focusConfig.pomodoro_minutes || 25).padStart(2, '0')}:00`
})

function taskTitleOf(taskId) {
  if (!taskId) return ''
  return taskStore.tasks.find((t) => t.id === taskId)?.title || ''
}

async function onMiniPlay() {
  try {
    await store.start(null, store.mode === 'stopwatch' ? 0 : store.focusConfig.pomodoro_minutes || 25)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail?.message || '开始失败')
  }
}

// 输入任务名回车：精确/前缀匹配已有任务则关联，否则纯计时
const draft = ref('')
async function onEnter() {
  const q = draft.value.trim()
  let taskId = null
  if (q) {
    const pool = (list) => list.filter((t) => !t.is_deleted && t.status !== 'done')
    let hit = pool(taskStore.tasks).find((t) => t.title === q) || pool(taskStore.tasks).find((t) => t.title.startsWith(q))
    if (!hit) {
      // 本地未加载该任务时回源搜索
      const res = await fetchTasks({ q, limit: 10 }).catch(() => ({ items: [] }))
      const remote = pool(res.items || [])
      hit = remote.find((t) => t.title === q) || remote.find((t) => t.title.startsWith(q))
    }
    taskId = hit?.id || null
  }
  try {
    await store.start(taskId, store.mode === 'stopwatch' ? 0 : store.focusConfig.pomodoro_minutes || 25)
    draft.value = ''
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail?.message || '开始失败')
  }
}
</script>

<style scoped>
.mini-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--ss-card-bg, #fff);
  border: 1px solid var(--ss-border-light, #f0f0f0);
  border-radius: 12px;
  padding: 8px 14px;
  cursor: pointer;
  flex-shrink: 0;
}
.mb-emoji {
  font-size: 20px;
}
.mb-mid {
  flex: 1;
  min-width: 0;
}
.mb-title {
  font-size: 12px;
  color: var(--ss-text-secondary, #909399);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.mb-input {
  width: 100%;
  border: none;
  outline: none;
  background: transparent;
  padding: 0;
  font-size: 12px;
  color: var(--ss-text, #303133);
}
.mb-input::placeholder {
  color: var(--ss-text-secondary, #909399);
}
.mb-time {
  font-size: 15px;
  font-weight: 600;
  color: var(--ss-text, #303133);
  font-variant-numeric: tabular-nums;
}
.mb-play {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--el-color-primary);
  color: #fff;
  flex-shrink: 0;
}
.mb-state {
  font-size: 12px;
  color: var(--el-color-primary);
  flex-shrink: 0;
}
</style>
