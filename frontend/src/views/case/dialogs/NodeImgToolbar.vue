<template>
  <div
    v-if="visible"
    class="img-toolbar"
    :style="{ left: `${x}px`, top: `${y}px` }"
    @click.stop
  >
    <el-button size="small" text @click="handleChange">更换</el-button>
    <el-button size="small" text @click="handleUpload">上传</el-button>
    <el-button size="small" text type="danger" @click="handleRemove">删除</el-button>
    <el-button size="small" text @click="hide">关闭</el-button>
  </div>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  mindMap: Object,
})
const emit = defineEmits(['change', 'upload', 'remove'])

const visible = ref(false)
const x = ref(0)
const y = ref(0)
const activeNode = ref(null)

function show(node, clientX, clientY) {
  activeNode.value = node
  x.value = clientX
  y.value = clientY - 40
  visible.value = true
}

function hide() {
  visible.value = false
}

function handleChange() {
  emit('change', activeNode.value)
  hide()
}

function handleUpload() {
  emit('upload', activeNode.value)
  hide()
}

function handleRemove() {
  if (!activeNode.value) return
  activeNode.value.setData('image', '')
  props.mindMap?.render()
  emit('remove', activeNode.value)
  hide()
}

defineExpose({ show, hide })
</script>

<style scoped>
.img-toolbar {
  position: fixed;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  padding: 6px 10px;
  z-index: 2000;
  display: flex;
  gap: 4px;
}
</style>
