<template>
  <el-dialog
    :model-value="modelValue"
    title="节点标签"
    width="420px"
    @update:model-value="emit('update:modelValue', $event)"
    @close="handleClose"
  >
    <div class="tag-input-row">
      <el-input v-model="newTag" size="small" placeholder="输入标签后回车" @keyup.enter="addTag" />
      <el-button size="small" type="primary" @click="addTag">添加</el-button>
    </div>
    <div class="tag-list">
      <el-tag
        v-for="(tag, index) in localTags"
        :key="index"
        closable
        size="small"
        @close="removeTag(index)"
      >
        {{ typeof tag === 'string' ? tag : tag.text }}
      </el-tag>
    </div>
    <template #footer>
      <el-button @click="handleClose">取消</el-button>
      <el-button type="primary" @click="handleConfirm">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  tags: {
    type: Array,
    default: () => [],
  },
})
const emit = defineEmits(['update:modelValue', 'confirm'])

const newTag = ref('')
const localTags = ref([])

watch(() => props.modelValue, (visible) => {
  if (visible) {
    localTags.value = Array.isArray(props.tags) ? [...props.tags] : []
    newTag.value = ''
  }
})

function addTag() {
  const text = newTag.value.trim()
  if (!text) return
  localTags.value.push(text)
  newTag.value = ''
}

function removeTag(index) {
  localTags.value.splice(index, 1)
}

function handleClose() {
  emit('update:modelValue', false)
}

function handleConfirm() {
  emit('confirm', [...localTags.value])
  handleClose()
}
</script>

<style scoped>
.tag-input-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
