<template>
  <el-dialog
    :model-value="modelValue"
    title="节点备注"
    width="520px"
    @update:model-value="emit('update:modelValue', $event)"
    @close="handleClose"
  >
    <el-input
      v-model="localNote"
      type="textarea"
      :rows="6"
      placeholder="请输入备注内容..."
    />
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="danger" plain @click="handleRemove">清空</el-button>
      <el-button type="primary" @click="handleConfirm">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  note: {
    type: String,
    default: '',
  },
})
const emit = defineEmits(['update:modelValue', 'confirm'])

const localNote = ref(props.note)

watch(() => props.modelValue, (visible) => {
  if (visible) {
    localNote.value = props.note || ''
  }
})

function handleClose() {
  emit('update:modelValue', false)
}

function handleConfirm() {
  emit('confirm', localNote.value)
  handleClose()
}

function handleRemove() {
  localNote.value = ''
  emit('confirm', '')
  handleClose()
}
</script>
