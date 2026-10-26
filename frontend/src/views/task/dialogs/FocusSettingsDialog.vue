<template>
  <el-dialog
    :model-value="modelValue"
    title="专注设置"
    width="400px"
    :close-on-click-modal="false"
    @update:model-value="(v) => emit('update:modelValue', v)"
    @open="onOpen"
  >
    <div class="fsd">
      <div class="fsd-field">
        <span class="fsd-label">番茄时长</span>
        <div class="fsd-dur">
          <el-input-number v-model="cfg.pomodoro_minutes" :min="1" :max="180" size="small" controls-position="right" />
          <span class="fsd-unit">分钟</span>
        </div>
      </div>
      <div class="fsd-field">
        <span class="fsd-label">短休息时长</span>
        <div class="fsd-dur">
          <el-input-number v-model="cfg.short_break_minutes" :min="1" :max="60" size="small" controls-position="right" />
          <span class="fsd-unit">分钟</span>
        </div>
      </div>
      <div class="fsd-field">
        <span class="fsd-label">长休息时长</span>
        <div class="fsd-dur">
          <el-input-number v-model="cfg.long_break_minutes" :min="1" :max="120" size="small" controls-position="right" />
          <span class="fsd-unit">分钟</span>
        </div>
      </div>
      <div class="fsd-switch">
        <span class="fsd-label">严格模式<span class="fsd-tip">切出标签页自动暂停</span></span>
        <el-switch :model-value="store.strictMode" size="small" @change="store.setStrict($event)" />
      </div>
      <div class="fsd-switch">
        <span class="fsd-label">完成提示音</span>
        <el-switch :model-value="store.soundOn" size="small" @change="store.toggleSound()" />
      </div>
    </div>
    <template #footer>
      <div class="fsd-footer">
        <el-button type="primary" round @click="save">保存</el-button>
        <el-button round @click="emit('update:modelValue', false)">取消</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { usePomodoroStore } from '@/stores/pomodoro'

const props = defineProps({
  modelValue: Boolean,
})
const emit = defineEmits(['update:modelValue', 'saved'])

const store = usePomodoroStore()
const cfg = ref({ pomodoro_minutes: 25, short_break_minutes: 5, long_break_minutes: 15 })

function onOpen() {
  cfg.value = {
    pomodoro_minutes: store.focusConfig.pomodoro_minutes,
    short_break_minutes: store.focusConfig.short_break_minutes,
    long_break_minutes: store.focusConfig.long_break_minutes,
  }
}

async function save() {
  await store
    .saveConfig({
      pomodoro_minutes: cfg.value.pomodoro_minutes,
      short_break_minutes: cfg.value.short_break_minutes,
      long_break_minutes: cfg.value.long_break_minutes,
    })
    .catch(() => {})
  emit('update:modelValue', false)
  emit('saved')
  ElMessage.success('已保存')
}
</script>

<style scoped>
.fsd {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.fsd-field {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.fsd-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--ss-text, #303133);
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.fsd-tip {
  font-size: 12px;
  font-weight: 400;
  color: var(--ss-text-muted, #a8abb2);
}
.fsd-dur {
  display: flex;
  align-items: center;
  gap: 8px;
}
.fsd-unit {
  font-size: 13px;
  color: var(--ss-text-secondary, #909399);
}
.fsd-switch {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.fsd-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
