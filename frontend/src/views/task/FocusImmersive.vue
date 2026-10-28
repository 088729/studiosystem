<template>
  <!-- 沉浸模式（对齐主流待办应用：全屏纯黑 + 居中超大时钟，点击屏幕循环 简约数字→翻页钟→像素时钟） -->
  <div class="immersive" @click="cycleStyle">
    <div class="imm-top">
      <span class="imm-name">{{ title }}</span>
      <span v-if="store.phase === 'rest'" class="imm-phase">休息中</span>
    </div>

    <div class="imm-clock" :class="styleKey" @click.stop>
      <!-- 简约数字 -->
      <template v-if="styleKey === 'digital'">
        <div class="imm-digital">{{ clockText }}</div>
      </template>
      <!-- 翻页钟 -->
      <div v-else-if="styleKey === 'flip'" class="imm-flip">
        <template v-for="(ch, i) in clockText" :key="i">
          <span v-if="ch === ':'" class="imm-flip-sep">:</span>
          <span v-else class="imm-flip-digit">
            <Transition name="flip" mode="out-in">
              <span :key="ch">{{ ch }}</span>
            </Transition>
          </span>
        </template>
      </div>
      <!-- 像素时钟 -->
      <div v-else class="imm-pixel">{{ clockText }}</div>
    </div>

    <div class="imm-hint">点击屏幕切换样式 · {{ styleName }}</div>

    <!-- 当前关联（对齐主流待办应用沉浸中操作菜单：显示关联的预设/任务） -->
    <div class="imm-link" @click.stop>
      <span class="imm-link-chip">{{ linkTitle }}</span>
    </div>

    <div class="imm-controls" @click.stop>
      <el-button v-if="store.isRunning" round @click="store.togglePause()">
        {{ store.paused ? '继续' : '暂停' }}
      </el-button>
      <!-- 白噪音快捷切换（对齐主流待办应用沉浸中操作菜单） -->
      <el-button round @click="cycleAmbient()">
        {{ store.ambient === 'none' ? '🔇 白噪音' : `${ambientIcon} ${ambientName}` }}
      </el-button>
      <el-button round @click="emit('close')">退出沉浸</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { usePomodoroStore } from '@/stores/pomodoro'
import { useTaskStore } from '@/stores/task'
import { useHabitStore } from '@/stores/habit'

const emit = defineEmits(['close'])
const store = usePomodoroStore()
const taskStore = useTaskStore()
const habitStore = useHabitStore()

const STYLES = [
  { key: 'digital', name: '简约数字' },
  { key: 'flip', name: '翻页钟' },
  { key: 'pixel', name: '像素时钟' },
]
const styleIdx = ref(0)
const styleKey = computed(() => STYLES[styleIdx.value].key)
const styleName = computed(() => STYLES[styleIdx.value].name)

// 当前关联（预设/任务），对齐主流待办应用沉浸中操作菜单的「关联任务」项
const linkTitle = computed(() => {
  if (store.currentPreset?.name) return `${store.currentPreset.icon} ${store.currentPreset.name}`
  const t = taskStore.tasks.find((x) => x.id === store.current?.task_id)
  if (t) return t.title
  if (store.pendingTask && store.current?.task_id === store.pendingTask.id) return store.pendingTask.title
  if (store.current?.habit_id) {
    const h = habitStore.habits.find((x) => x.id === store.current.habit_id)
    if (h) return `${h.icon} ${h.name}`
  }
  return '🍅 专注'
})
const ambientIcon = computed(() => store.AMBIENT_TYPES.find((a) => a.key === store.ambient)?.icon || '🔇')
const ambientName = computed(() => store.AMBIENT_TYPES.find((a) => a.key === store.ambient)?.name || '')
function cycleAmbient() {
  const keys = store.AMBIENT_TYPES.map((a) => a.key)
  const next = keys[(keys.indexOf(store.ambient) + 1) % keys.length]
  store.setAmbient(next)
}

function cycleStyle() {
  styleIdx.value = (styleIdx.value + 1) % STYLES.length
}

const clockText = computed(() => {
  if (store.isRunning) return store.displayText
  if (store.phase === 'rest') return store.restText
  return '--:--'
})
const title = computed(() => store.currentPreset?.name || (store.current?.task_id ? '专注中' : '番茄专注'))

function onKey(e) {
  if (e.key === 'Escape') emit('close')
  if (e.key === ' ') {
    e.preventDefault()
    cycleStyle()
  }
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<style scoped>
.immersive {
  position: fixed;
  inset: 0;
  background: #0a0a0c;
  z-index: 3000;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  user-select: none;
  cursor: pointer;
}
.imm-top {
  position: absolute;
  top: 28px;
  left: 0;
  right: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  pointer-events: none;
}
.imm-name {
  color: rgba(255, 255, 255, 0.55);
  font-size: 15px;
  letter-spacing: 1px;
}
.imm-phase {
  color: rgba(255, 255, 255, 0.35);
  font-size: 12px;
}
.imm-clock {
  pointer-events: none;
}
/* 简约数字 */
.imm-digital {
  font-size: 22vw;
  line-height: 1;
  font-weight: 200;
  color: #f5f5f7;
  font-variant-numeric: tabular-nums;
  letter-spacing: 2px;
}
/* 翻页钟 */
.imm-flip {
  display: flex;
  align-items: center;
  gap: 1.2vw;
  perspective: 1200px;
}
.imm-flip-digit {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 11vw;
  height: 16vw;
  background: linear-gradient(180deg, #2a2a30 0%, #1b1b20 50%, #17171b 50%, #101014 100%);
  border-radius: 1.2vw;
  color: #f5f5f7;
  font-size: 10vw;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}
.imm-flip-sep {
  color: rgba(255, 255, 255, 0.4);
  font-size: 8vw;
  animation: blink 2s infinite;
}
@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.25; }
}
.flip-enter-active,
.flip-leave-active {
  transition: transform 0.22s ease, opacity 0.22s ease;
}
.flip-enter-from {
  transform: rotateX(90deg);
  opacity: 0;
}
.flip-leave-to {
  transform: rotateX(-90deg);
  opacity: 0;
}
/* 像素时钟 */
.imm-pixel {
  font-family: 'Courier New', monospace;
  font-weight: 700;
  font-size: 17vw;
  line-height: 1;
  color: #57ff9a;
  text-shadow:
    0 0 12px rgba(87, 255, 154, 0.55),
    0 0 42px rgba(87, 255, 154, 0.25);
  font-variant-numeric: tabular-nums;
  letter-spacing: 4px;
}
.imm-hint {
  position: absolute;
  bottom: 96px;
  color: rgba(255, 255, 255, 0.3);
  font-size: 12px;
  letter-spacing: 1px;
  pointer-events: none;
}
.imm-controls {
  position: absolute;
  bottom: 32px;
  display: flex;
  gap: 12px;
}
.imm-controls .el-button {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.15);
  color: rgba(255, 255, 255, 0.8);
}
.imm-controls .el-button:hover {
  background: rgba(255, 255, 255, 0.16);
  color: #fff;
}
/* 沉浸中顶部关联 chip（对齐主流待办应用操作菜单的「关联任务」项） */
.imm-link {
  position: absolute;
  top: clamp(20px, 4vh, 44px);
  left: 50%;
  transform: translateX(-50%);
}
.imm-link-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 4px 14px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
  background: rgba(255, 255, 255, 0.12);
  border-radius: 999px;
  max-width: 60vw;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
</style>
