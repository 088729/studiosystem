<template>
  <!-- 习惯行右键菜单（对齐主流待办应用）：开始专注› / 记录日志 / 跳过打卡 / 未完成 -->
  <teleport to="body">
    <div
      v-if="visible"
      class="habit-context-menu"
      :style="{ left: pos.x + 'px', top: pos.y + 'px' }"
      @click.stop
      @contextmenu.stop.prevent
    >
      <!-- 开始专注（悬停展开子菜单）：番茄专注 / 正计时 -->
      <div class="hcm-item hcm-sub-trigger" @mouseenter="focusSub = true" @mouseleave="focusSub = false">
        <CircleDot :size="15" class="hcm-icon" />开始专注
        <ChevronRight :size="13" class="hcm-arrow" />
        <div v-if="focusSub" class="hcm-sub">
          <div class="hcm-item" @click="onFocusPomodoro">开始番茄专注</div>
          <div class="hcm-item" @click="onFocusStopwatch">开始正计时</div>
        </div>
      </div>

      <div class="hcm-item" @click="onLog">
        <NotebookPen :size="15" class="hcm-icon" />记录日志
      </div>
      <!-- 跳过打卡常驻显示（对齐主流待办应用右键菜单四项同显）；已打卡时后端会 400 提示 -->
      <div v-if="habit && !habit.today_skipped" class="hcm-item" @click="onSkip">
        <CalendarX :size="15" class="hcm-icon" />跳过打卡
      </div>
      <div v-if="habit && !habit.today_checked && habit.today_skipped" class="hcm-item" @click="onUnskip">
        <CalendarCheck :size="15" class="hcm-icon" />取消跳过
      </div>
      <div v-if="habit?.today_checked" class="hcm-item" @click="onUndo">
        <X :size="15" class="hcm-icon" />未完成
      </div>
    </div>
  </teleport>

  <!-- 记录日志弹窗（心情+心得，对齐主流待办应用） -->
  <HabitLogDialog ref="logDialog" />
</template>

<script setup>
import { onBeforeUnmount, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleDot, ChevronRight, NotebookPen, CalendarX, CalendarCheck, X } from 'lucide-vue-next'
import { useHabitStore } from '@/stores/habit'
import { usePomodoroStore } from '@/stores/pomodoro'
import HabitLogDialog from './HabitLogDialog.vue'

const habitStore = useHabitStore()
const pomodoroStore = usePomodoroStore()
const logDialog = ref(null)

const visible = ref(false)
const focusSub = ref(false)
const pos = reactive({ x: 0, y: 0 })
const habit = ref(null)

function open(event, h) {
  habit.value = h
  focusSub.value = false
  // 边缘防溢出：菜单约 180px 宽、每项 34px 高
  pos.x = Math.min(event.clientX, window.innerWidth - 190)
  pos.y = Math.min(event.clientY, window.innerHeight - 170)
  visible.value = true
}

function close() {
  visible.value = false
  focusSub.value = false
}

function onDocClick() {
  close()
}
function onDocKeydown(e) {
  if (e.key === 'Escape') close()
}

// 与 TaskContextMenu 同款全局监听：外点 / Esc 关闭
watch(visible, (v) => {
  if (v) {
    document.addEventListener('click', onDocClick, true)
    document.addEventListener('contextmenu', onDocClick, true)
    document.addEventListener('keydown', onDocKeydown, true)
  } else {
    document.removeEventListener('click', onDocClick, true)
    document.removeEventListener('contextmenu', onDocClick, true)
    document.removeEventListener('keydown', onDocKeydown, true)
  }
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onDocClick, true)
  document.removeEventListener('contextmenu', onDocClick, true)
  document.removeEventListener('keydown', onDocKeydown, true)
})

// ---------- 菜单动作 ----------
async function onFocusPomodoro() {
  close()
  let minutes
  try {
    const { value } = await ElMessageBox.prompt('专注时长（分钟），常用 15 / 25 / 45', '开始番茄专注', {
      inputValue: '25',
      inputPattern: /^\d+$/,
      inputErrorMessage: '请输入数字分钟数',
    })
    minutes = +value
  } catch {
    return // 用户取消
  }
  if (!minutes) return
  try {
    pomodoroStore.mode = 'countdown'
    await pomodoroStore.start(null, minutes)
    pomodoroStore.openPanel()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail?.message || '开始失败')
  }
}

async function onFocusStopwatch() {
  close()
  try {
    pomodoroStore.mode = 'stopwatch'
    await pomodoroStore.start(null, 0)
    pomodoroStore.openPanel()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail?.message || '开始失败')
  }
}

function onLog() {
  close()
  logDialog.value?.open(habit.value)
}

async function onSkip() {
  close()
  try {
    await habitStore.skipHabit(habit.value.id)
    ElMessage.success(`「${habit.value.name}」今日已跳过`)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail?.message || '操作失败')
  }
}

async function onUnskip() {
  close()
  await habitStore.uncheckin(habit.value.id) // 纯跳过记录 count=0，uncheckin 即删除记录=取消跳过
  ElMessage.success(`「${habit.value.name}」已取消跳过`)
}

async function onUndo() {
  close()
  await habitStore.uncheckin(habit.value.id)
  ElMessage.success(`「${habit.value.name}」已标记为未完成`)
}

defineExpose({ open, close })
</script>

<style>
/* teleport 到 body，用全局样式（hcm 前缀避免污染） */
.habit-context-menu {
  position: fixed;
  z-index: 3000;
  min-width: 160px;
  background: #fff;
  border: 1px solid var(--ss-border, #e5e7eb);
  border-radius: 8px;
  box-shadow: 0 6px 24px rgb(0 0 0 / 12%);
  padding: 4px;
}
.hcm-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  font-size: 13px;
  color: var(--ss-text, #1f2329);
  border-radius: 5px;
  cursor: pointer;
  white-space: nowrap;
}
.hcm-item:hover {
  background: var(--ss-bg, #f5f6f7);
}
.hcm-icon {
  color: var(--ss-text-muted, #8f959e);
  flex-shrink: 0;
}
.hcm-arrow {
  margin-left: auto;
  color: var(--ss-text-muted, #8f959e);
}
.hcm-sub {
  position: absolute;
  left: 100%;
  top: -5px;
  margin-left: 2px;
  min-width: 130px;
  background: #fff;
  border: 1px solid var(--ss-border, #e5e7eb);
  border-radius: 8px;
  box-shadow: 0 6px 24px rgb(0 0 0 / 12%);
  padding: 4px;
}
</style>
