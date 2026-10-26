<template>
  <el-dialog
    :model-value="modelValue"
    title="节点图标"
    width="400px"
    @update:model-value="emit('update:modelValue', $event)"
    @close="handleClose"
  >
    <div class="icon-grid">
      <div
        v-for="icon in icons"
        :key="icon"
        :class="['icon-item', { active: localIcon === icon }]"
        @click="localIcon = icon"
      >
        {{ icon }}
      </div>
    </div>
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="danger" plain @click="handleRemove">移除</el-button>
      <el-button type="primary" @click="handleConfirm">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  icon: {
    type: String,
    default: '',
  },
})
const emit = defineEmits(['update:modelValue', 'confirm'])

const icons = [
  'priority_1',
  'priority_2',
  'priority_3',
  'smiley',
  'task_done',
  'task_wait',
  'task_pause',
]

const localIcon = ref(props.icon)

watch(() => props.modelValue, (visible) => {
  if (visible) {
    localIcon.value = props.icon || ''
  }
})

function handleClose() {
  emit('update:modelValue', false)
}

function handleConfirm() {
  emit('confirm', localIcon.value)
  handleClose()
}

function handleRemove() {
  localIcon.value = ''
  emit('confirm', '')
  handleClose()
}
</script>

<style scoped>
.icon-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.icon-item {
  padding: 8px 12px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
}
.icon-item:hover,
.icon-item.active {
  border-color: #409eff;
  color: #409eff;
}
</style>
