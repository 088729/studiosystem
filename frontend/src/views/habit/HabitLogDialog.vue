<template>
  <!-- 习惯「记录日志」弹窗（对齐主流待办应用）：图标+名称 / 日期 / 心情五选一 / 心得 / 取消·保存 -->
  <el-dialog
    v-model="visible"
    width="460px"
    :show-close="false"
    class="habit-log-dialog"
    align-center
    append-to-body
  >
    <template #header>
      <div class="hld-header">
        <span class="hld-icon" :style="{ background: habit?.color }"><img :src="habitIcon" class="hld-icon-img" alt="" /></span>
        <span class="hld-name">{{ habit?.name }}</span>
        <X :size="16" class="hld-close" @click="visible = false" />
      </div>
    </template>

    <div class="hld-date">{{ dateText }}</div>

    <!-- 心情五选一（twemoji SVG 本地资源）：选中放大，未选灰化 -->
    <div class="hld-moods">
      <img
        v-for="m in moods"
        :key="m.value"
        :src="m.img"
        class="hld-mood"
        :class="{ active: mood === m.value }"
        :title="m.tip"
        :alt="m.tip"
        @click="mood = mood === m.value ? null : m.value"
      />
    </div>

    <el-input
      v-model="note"
      type="textarea"
      :rows="5"
      placeholder="记录一下心得吧"
      resize="none"
      class="hld-note"
    />

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="onSave">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'
import { X } from 'lucide-vue-next'
import { useHabitStore } from '@/stores/habit'
import { habitIconOf } from '@/utils/habitIcons'
// Noto Color Emoji SVG（本地 vendor，不走 CDN；圆润苹果风，对齐主流待办应用）
import mood1 from '@/assets/moods/mood1.svg'
import mood2 from '@/assets/moods/mood2.svg'
import mood3 from '@/assets/moods/mood3.svg'
import mood4 from '@/assets/moods/mood4.svg'
import mood5 from '@/assets/moods/mood5.svg'

const habitStore = useHabitStore()

const visible = ref(false)
const saving = ref(false)
const habit = ref(null)
const note = ref('')
const mood = ref(null)
const logDate = ref('')
const metaOnly = ref(false)
// 习惯图标（habit.icon key → Noto 图标，先笠 smile）
const habitIcon = computed(() => habitIconOf(habit.value?.icon))

const moods = [
  { value: 1, img: mood1, tip: '大哭' },
  { value: 2, img: mood2, tip: '难过' },
  { value: 3, img: mood3, tip: '平静' },
  { value: 4, img: mood4, tip: '不错' },
  { value: 5, img: mood5, tip: '开心' },
]

// 「8月23日 周日」
const dateText = computed(() => {
  const d = dayjs(logDate.value || undefined)
  const weeks = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.month() + 1}月${d.date()}日 周${weeks[d.day()]}`
})

// dateStr 缺省今天；metaOnly=True 表示打卡已发生，这里只回写心情/日志（不增加 count）
function open(h, dateStr = null, meta = false) {
  habit.value = h
  metaOnly.value = meta
  const day = dateStr || dayjs().format('YYYY-MM-DD')
  logDate.value = day
  // 回填该日已有日志（覆盖式编辑）
  const log = habitStore.activeLogs.find((l) => l.date === day)
  note.value = log?.note || ''
  mood.value = log?.mood || null
  visible.value = true
}

async function onSave() {
  if (!note.value.trim() && !mood.value) {
    visible.value = false
    return
  }
  saving.value = true
  try {
    await habitStore.checkin(habit.value.id, logDate.value, note.value.trim() || undefined, mood.value, null, metaOnly.value)
    ElMessage.success(`「${habit.value.name}」日志已记录`)
    visible.value = false
  } finally {
    saving.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
.hld-header {
  display: flex;
  align-items: center;
  gap: 10px;
}
.hld-icon-img {
  width: 17px;
  height: 17px;
  display: block;
}
.hld-icon {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.hld-name {
  font-size: 16px;
  font-weight: 600;
  color: var(--ss-text);
  flex: 1;
}
.hld-close {
  color: var(--ss-text-muted);
  cursor: pointer;
}
.hld-close:hover {
  color: var(--ss-text);
}
.hld-date {
  text-align: center;
  font-size: 13px;
  color: var(--ss-text-muted);
  margin-bottom: 14px;
}
.hld-moods {
  display: flex;
  justify-content: space-between;
  padding: 0 24px;
  margin-bottom: 14px;
}
/* 对齐主流待办应用：未选灰化，选中彩色放大 */
.hld-mood {
  width: 40px;
  height: 40px;
  cursor: pointer;
  filter: grayscale(1) opacity(0.4);
  transition: transform 0.15s, filter 0.15s;
}
.hld-mood:hover {
  filter: grayscale(1) opacity(0.7);
  transform: scale(1.1);
}
.hld-mood.active {
  filter: none;
  transform: scale(1.15);
}
.hld-note :deep(.el-textarea__inner) {
  background: var(--ss-bg);
  box-shadow: none;
  border-radius: 8px;
  padding: 10px 12px;
}
</style>
