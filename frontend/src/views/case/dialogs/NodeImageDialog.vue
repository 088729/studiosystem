<template>
  <el-dialog
    :model-value="modelValue"
    title="节点图片"
    width="480px"
    @update:model-value="emit('update:modelValue', $event)"
    @close="handleClose"
  >
    <el-form label-width="80px">
      <el-form-item label="图片 URL">
        <el-input v-model="localUrl" placeholder="支持网络地址或 Base64" />
      </el-form-item>
      <el-form-item label="预览">
        <img v-if="localUrl" :src="localUrl" class="img-preview" alt="预览" />
        <span v-else class="empty-text">暂无图片</span>
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
})
const emit = defineEmits(['update:modelValue', 'confirm'])

const localUrl = ref(props.url)

watch(() => props.modelValue, (visible) => {
  if (visible) {
    localUrl.value = props.url || ''
  }
})

function handleClose() {
  emit('update:modelValue', false)
}

function handleConfirm() {
  emit('confirm', localUrl.value)
  handleClose()
}

function handleRemove() {
  localUrl.value = ''
  emit('confirm', '')
  handleClose()
}
</script>

<style scoped>
.img-preview {
  max-width: 100%;
  max-height: 200px;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
}
.empty-text {
  color: #909399;
  font-size: 13px;
}
</style>
