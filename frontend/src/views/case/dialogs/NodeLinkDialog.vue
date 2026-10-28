<template>
  <el-dialog
    :model-value="modelValue"
    title="超链接"
    width="420px"
    @update:model-value="emit('update:modelValue', $event)"
    @close="handleClose"
  >
    <el-form label-width="80px">
      <el-form-item label="链接地址">
        <el-input v-model="localUrl" placeholder="https://..." />
      </el-form-item>
      <el-form-item label="链接标题">
        <el-input v-model="localTitle" placeholder="可选标题" />
      </el-form-item>
    </el-form>
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
  url: {
    type: String,
    default: '',
  },
  title: {
    type: String,
    default: '',
  },
})
const emit = defineEmits(['update:modelValue', 'confirm'])

const localUrl = ref(props.url)
const localTitle = ref(props.title)

watch(() => props.modelValue, (visible) => {
  if (visible) {
    localUrl.value = props.url || ''
    localTitle.value = props.title || ''
  }
})

function handleClose() {
  emit('update:modelValue', false)
}

function handleConfirm() {
  emit('confirm', { url: localUrl.value, title: localTitle.value })
  handleClose()
}

function handleRemove() {
  localUrl.value = ''
  localTitle.value = ''
  emit('confirm', { url: '', title: '' })
  handleClose()
}
</script>
