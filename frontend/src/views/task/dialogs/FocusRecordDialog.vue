<template>
  <el-dialog
    :model-value="modelValue"
    title="添加专注记录"
    width="420px"
    :close-on-click-modal="false"
    @update:model-value="(v) => emit('update:modelValue', v)"
    @open="onOpen"
  >
    <div class="frd">
      <div v-if="linkTitle" class="frd-link">已关联：{{ linkTitle }}</div>
      <div class="frd-field">
        <span class="frd-label">专注时长</span>
        <div class="frd-dur">
          <el-input-number v-model="minutes" :min="1" :max="600" size="small" controls-position="right" />
          <span class="frd-unit">分钟</span>
        </div>
      </div>
      <div class="frd-field">
        <span class="frd-label">开始时间</span>
        <el-date-picker
          v-model="startedAt"
          type="datetime"
          format="YYYY-MM-DD HH:mm"
          value-format="YYYY-MM-DDTHH:mm:ssZ"
          :clearable="false"
          class="frd-time"
        />
      </div>
      <div class="frd-field">
        <span class="frd-label">专注笔记</span>
        <el-input v-model="note" placeholder="（可选）" maxlength="200" class="frd-note" />
      </div>
    </div>
    <template #footer>
      <el-button @click="emit('update:modelValue', false)">取消</el-button>
      <el-button type="primary" @click="save">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import dayjs from 'dayjs'
import { ElMessage } from 'element-plus'
import { usePomodoroStore } from '@/stores/pomodoro'

const props = defineProps({
  modelValue: Boolean,
  preset: { type: Object, default: null },
})
const emit = defineEmits(['update:modelValue', 'saved'])

const store = usePomodoroStore()

const minutes = ref(25)
const startedAt = ref('')
const note = ref('')
const linkTitle = ref('')

function onOpen() {
  minutes.value = 25
  // 默认开始时间 = 25 分钟前
  startedAt.value = dayjs().subtract(25, 'minute').toISOString()
  note.value = ''
  linkTitle.value = props.preset?.name || ''
}

async function save() {
  if (!minutes.value || minutes.value < 1) {
    ElMessage.warning('请输入有效时长')
    return
  }
  if (!startedAt.value) {
    ElMessage.warning('请选择开始时间')
    return
  }
  await store.addRecord({
    preset_id: props.preset?.id || null,
    task_id: props.preset?.task_id || store.current?.task_id || null,
    planned_minutes: minutes.value,
    actual_seconds: minutes.value * 60,
    started_at: startedAt.value,
    note: note.value.trim(),
  })
  emit('update:modelValue', false)
  emit('saved')
  ElMessage.success('已补记')
}
</script>

<style scoped>
.frd {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.frd-link {
  font-size: 12px;
  color: var(--el-color-primary);
  background: var(--el-color-primary-light-9);
  border-radius: 999px;
  padding: 4px 12px;
  width: fit-content;
  max-width: 100%;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
}
.frd-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.frd-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ss-text, #303133);
}
.frd-dur {
  display: flex;
  align-items: center;
  gap: 8px;
}
.frd-unit {
  font-size: 13px;
  color: var(--ss-text-secondary, #909399);
}
.frd-time {
  width: 100%;
}
</style>
