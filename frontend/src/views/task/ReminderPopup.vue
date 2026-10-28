<template>
  <!-- 任务提醒弹窗（复刻主流待办应用网页版）：居中卡片——蓝色日期 + 标题 + ◎专注/✕关闭 + 稍后提醒(下拉)/完成 -->
  <div class="rp-card" @click.stop>
    <div class="rp-head">
      <span class="rp-date">{{ dateText }}</span>
      <span class="rp-icons">
        <button class="rp-icon" title="开始专注" @click="$emit('focus')"><Target :size="18" /></button>
        <button class="rp-icon" title="关闭" @click="$emit('dismiss')"><X :size="18" /></button>
      </span>
    </div>
    <div class="rp-title">{{ item.title }}</div>
    <div class="rp-foot">
      <div class="rp-snooze-wrap">
        <el-button class="rp-btn" @click="snoozeOpen = !snoozeOpen; customOpen = false">稍后提醒</el-button>
        <!-- 稍后提醒下拉（对齐主流待办应用，向下展开）：15分钟/30分钟/1小时/3小时/明天/明天早上/自定义 -->
        <div v-if="snoozeOpen && !customOpen" class="rp-snooze-menu">
          <div
            v-for="o in snoozeOptions"
            :key="o.label"
            class="rp-snooze-item"
            :class="{ 'rp-snooze-item--divided': o.key === 'custom' }"
            @click="pick(o)"
          >{{ o.label }}</div>
        </div>
        <!-- 自定义（对齐主流待办应用）：小时+分钟输入框 + 蓝色预览 + 取消/确定均分整行 -->
        <div v-if="snoozeOpen && customOpen" class="rp-custom" @click.stop>
          <div class="rp-custom-row">
            <input v-model.number="cHours" type="number" min="0" max="99" class="rp-custom-input" />
            <span class="rp-custom-label">小时</span>
            <input v-model.number="cMinutes" type="number" min="0" max="59" class="rp-custom-input" />
            <span class="rp-custom-label">分钟</span>
          </div>
          <div class="rp-custom-preview">{{ customPreview }} 提醒</div>
          <div class="rp-custom-actions">
            <el-button class="rp-custom-btn" @click="customOpen = false">取消</el-button>
            <el-button class="rp-custom-btn" type="primary" @click="confirmCustom">确定</el-button>
          </div>
        </div>
      </div>
      <el-button class="rp-btn" type="primary" @click="$emit('complete')">完成</el-button>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { Target, X } from 'lucide-vue-next'
import dayjs from 'dayjs'

const props = defineProps({
  item: { type: Object, required: true }, // { task_id, title, due_at }
})
const emit = defineEmits(['dismiss', 'focus', 'complete', 'snooze'])

// 头部日期文案（对齐主流待办应用）：今天/明天/M月D日
const dateText = computed(() => {
  const d = props.item.due_at ? dayjs(props.item.due_at) : dayjs()
  if (d.isSame(dayjs(), 'day')) return '今天'
  if (d.isSame(dayjs().add(1, 'day'), 'day')) return '明天'
  return `${d.month() + 1}月${d.date()}日`
})

const snoozeOpen = ref(false)
const customOpen = ref(false)
const cHours = ref(0)
const cMinutes = ref(5)

const snoozeOptions = [
  { label: '15分钟', minutes: 15 },
  { label: '30分钟', minutes: 30 },
  { label: '1小时', minutes: 60 },
  { label: '3小时', minutes: 180 },
  { label: '明天', key: 'tomorrow' },
  { label: '明天早上', key: 'tomorrow9' },
  { label: '自定义', key: 'custom' },
]

function pick(o) {
  if (o.key === 'custom') {
    customOpen.value = true
    return
  }
  let minutes = o.minutes
  if (o.key === 'tomorrow') minutes = Math.max(1, Math.round(dayjs().add(1, 'day').diff(dayjs(), 'minute', true)))
  if (o.key === 'tomorrow9') minutes = Math.max(1, Math.round(dayjs().add(1, 'day').hour(9).minute(0).second(0).diff(dayjs(), 'minute', true)))
  snoozeOpen.value = false
  emit('snooze', minutes)
}

const customTotal = computed(() => Math.max(1, (cHours.value || 0) * 60 + (cMinutes.value || 0)))
const customPreview = computed(() => dayjs().add(customTotal.value, 'minute').format('M月D日， HH:mm'))
function confirmCustom() {
  customOpen.value = false
  snoozeOpen.value = false
  emit('snooze', customTotal.value)
}
</script>

<style scoped>
.rp-card {
  width: 480px;
  padding: 28px 30px 26px;
  background: var(--ss-bg-card, #fff);
  border-radius: 12px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.18);
  pointer-events: auto;
  --el-color-primary: var(--ss-primary, #4f6ef7); /* 卡片内主色对齐主流待办应用蓝 */
}
.rp-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.rp-date {
  font-size: 15px;
  color: var(--ss-primary, #4f6ef7);
}
.rp-icons {
  display: flex;
  gap: 8px;
}
.rp-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 6px;
  background: transparent;
  color: var(--ss-text-muted, #909399);
  cursor: pointer;
}
.rp-icon:hover {
  background: var(--ss-bg-hover, #f5f7fa);
  color: var(--ss-text, #303133);
}
.rp-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--ss-text, #303133);
  margin-bottom: 64px;
  word-break: break-all;
}
.rp-foot {
  display: flex;
  justify-content: flex-end;
  gap: 14px;
}
.rp-btn {
  height: 46px;
  padding: 0 32px;
  font-size: 15px;
  border-radius: 8px;
  margin: 0;
}
.rp-snooze-wrap {
  position: relative;
}
/* 稍后提醒下拉：向下展开、右对齐按钮 */
.rp-snooze-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 176px;
  padding: 8px;
  background: var(--ss-bg-card, #fff);
  border: 1px solid var(--ss-border);
  border-radius: 10px;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.14);
  z-index: 10;
}
.rp-snooze-item {
  padding: 10px 14px;
  font-size: 15px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--ss-text, #303133);
}
.rp-snooze-item:hover {
  background: var(--ss-bg-hover, #f5f7fa);
}
.rp-snooze-item--divided {
  border-top: 1px solid var(--ss-border);
  border-radius: 0 0 6px 6px;
  margin-top: 6px;
  padding-top: 12px;
}
/* 自定义面板：独立宽卡片，向下展开 */
.rp-custom {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  width: 330px;
  padding: 20px;
  background: var(--ss-bg-card, #fff);
  border: 1px solid var(--ss-border);
  border-radius: 10px;
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.14);
  z-index: 10;
}
.rp-custom-row {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--ss-text, #303133);
}
.rp-custom-input {
  width: 76px;
  height: 40px;
  padding: 0 8px;
  font-size: 15px;
  text-align: center;
  border: 1px solid var(--ss-border);
  border-radius: 8px;
  background: var(--ss-bg-card, #fff);
  color: inherit;
}
.rp-custom-input:focus {
  outline: none;
  border-color: var(--el-color-primary);
}
.rp-custom-label {
  font-size: 14px;
  white-space: nowrap;
}
.rp-custom-preview {
  margin-top: 14px;
  font-size: 14px;
  color: var(--el-color-primary);
}
.rp-custom-actions {
  display: flex;
  gap: 12px;
  margin-top: 18px;
}
.rp-custom-btn {
  flex: 1;
  height: 40px;
  font-size: 15px;
  border-radius: 8px;
  margin: 0;
}
.rp-custom-btn + .rp-custom-btn {
  margin-left: 0;
}
</style>
