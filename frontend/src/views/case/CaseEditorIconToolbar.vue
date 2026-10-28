<template>
  <div
    v-if="visible"
    class="icon-toolbar"
    :style="{ left: `${x}px`, top: `${y}px` }"
    @click.stop
  >
    <div class="icon-group">
      <span
        v-for="icon in icons"
        :key="icon"
        class="icon-item"
        @click="setIcon(icon)"
      >
        {{ icon }}
      </span>
      <span class="icon-item remove" @click="removeIcon">×</span>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  mindMap: Object,
})

const visible = ref(false)
const x = ref(0)
const y = ref(0)
const activeNode = ref(null)

const icons = ['priority_1', 'priority_2', 'priority_3', 'smiley', 'task_done']

watch(() => props.mindMap, (mm) => {
  if (!mm) return
  mm.on('node_icon_click', (node, e) => {
    e.stopPropagation()
    activeNode.value = node
    x.value = e.clientX
    y.value = e.clientY - 40
    visible.value = true
  })
})

function setIcon(icon) {
  if (!activeNode.value) return
  activeNode.value.setData('icon', [icon])
  props.mindMap.render()
  hide()
}

function removeIcon() {
  if (!activeNode.value) return
  activeNode.value.setData('icon', [])
  props.mindMap.render()
  hide()
}

function hide() {
  visible.value = false
}

defineExpose({ hide })
</script>

<style scoped>
.icon-toolbar {
  position: fixed;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  padding: 6px 10px;
  z-index: 2000;
}
.icon-group {
  display: flex;
  gap: 8px;
  align-items: center;
}
.icon-item {
  cursor: pointer;
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 4px;
}
.icon-item:hover {
  background: #f5f7fa;
}
.icon-item.remove {
  color: #f56c6c;
  font-size: 16px;
}
</style>
