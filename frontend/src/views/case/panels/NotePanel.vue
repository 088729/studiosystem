<template>
  <div class="note-panel">
    <div class="panel-title">备注</div>
    <el-input
      v-model="note"
      type="textarea"
      :rows="6"
      placeholder="选中节点后在此编辑备注"
      @change="apply"
    />
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  mindMap: Object,
})

const note = ref('')

watch(() => props.mindMap, (mm) => {
  if (!mm) return
  mm.on('node_active', () => {
    syncNote()
  })
  // 面板可能是节点已激活后才打开的（如切换页签），初始化时同步一次
  syncNote()
}, { immediate: true })

function syncNote() {
  const node = props.mindMap?.renderer.activeNodeList[0]
  if (!node) return
  note.value = node.getData('note') || ''
}

function apply() {
  if (!props.mindMap) return
  const activeNodes = props.mindMap.renderer.activeNodeList
  if (activeNodes.length === 0) return
  activeNodes.forEach(node => {
    node.setData('note', note.value)
  })
  props.mindMap.render()
}
</script>

<style scoped>
.note-panel {
  padding: 8px;
}
.panel-title {
  font-weight: bold;
  margin-bottom: 8px;
  font-size: 14px;
}
</style>
