<template>
  <!-- Mini 模式小浮窗（对齐主流待办应用 ⋯ 菜单：桌面端画中画小窗，任何页面悬浮） -->
  <teleport to="body">
    <div v-if="store.miniOpen" class="fmw">
      <span class="fmw-emoji">🍅</span>
      <div class="fmw-mid">
        <div class="fmw-title">{{ title }}</div>
        <div class="fmw-time">{{ store.isRunning ? store.displayText : idleTime }}</div>
      </div>
      <template v-if="!store.isRunning">
        <span class="fmw-btn primary" title="开始专注" @click="onStart">
          <Play :size="13" fill="currentColor" />
        </span>
      </template>
      <template v-else>
        <span class="fmw-btn" :title="store.paused ? '继续' : '暂停'" @click="store.togglePause()">
          <Play v-if="store.paused" :size="13" fill="currentColor" />
          <Pause v-else :size="13" />
        </span>
        <span class="fmw-btn success" title="完成" @click="store.finish()">
          <Check :size="13" />
        </span>
      </template>
      <span class="fmw-btn" title="关闭 Mini 模式" @click="store.setMini(false)">
        <X :size="13" />
      </span>
    </div>
  </teleport>
</template>

<script setup>
import { computed } from 'vue'
import { Play, Pause, Check, X } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { usePomodoroStore } from '@/stores/pomodoro'
import { useTaskStore } from '@/stores/task'

const store = usePomodoroStore()
const taskStore = useTaskStore()

const title = computed(() => {
  if (!store.isRunning) return '准备做什么？'
  return store.currentPreset?.name || taskStore.tasks.find((t) => t.id === store.current?.task_id)?.title || '专注中'
})
const idleTime = computed(() =>
  store.mode === 'stopwatch' ? '00:00' : `${String(store.focusConfig.pomodoro_minutes || 25).padStart(2, '0')}:00`
)

async function onStart() {
  try {
    await store.start(null, store.mode === 'stopwatch' ? 0 : store.focusConfig.pomodoro_minutes || 25)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail?.message || '开始失败')
  }
}
</script>

<style scoped>
.fmw {
  position: fixed;
  right: 24px;
  bottom: 24px;
  z-index: 3000;
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--ss-card-bg, #fff);
  border: 1px solid var(--ss-border-light, #f0f0f0);
  border-radius: 14px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.12);
  padding: 10px 12px;
  min-width: 220px;
}
.fmw-emoji {
  font-size: 22px;
}
.fmw-mid {
  flex: 1;
  min-width: 0;
}
.fmw-title {
  font-size: 12px;
  color: var(--ss-text-secondary, #909399);
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.fmw-time {
  font-size: 17px;
  font-weight: 600;
  color: var(--ss-text, #303133);
  font-variant-numeric: tabular-nums;
}
.fmw-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  color: var(--ss-text-secondary, #909399);
  flex-shrink: 0;
}
.fmw-btn:hover {
  background: var(--ss-fill, #f7f7f9);
  color: var(--el-color-primary);
}
.fmw-btn.primary {
  background: var(--el-color-primary);
  color: #fff;
}
.fmw-btn.success:hover {
  background: var(--el-color-success-light-9);
  color: var(--el-color-success);
}
</style>
