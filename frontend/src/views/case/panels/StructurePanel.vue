<template>
  <div class="structure-panel">
    <div v-for="group in layoutGroupList" :key="group.name" class="layout-group">
      <div class="group-name">{{ group.name }}</div>
      <div class="layout-list">
        <div
          v-for="item in group.list"
          :key="item"
          class="layout-item"
          :class="{ active: currentLayout === item }"
          :title="item"
          @click="setLayout(item)"
        >
          <img :src="layoutImgMap[item]" :alt="item" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { layoutImgMap, layoutGroupList } from '@/config/layout'

const props = defineProps({
  mindMap: Object,
})

const currentLayout = ref('logicalStructure')

watch(() => props.mindMap, (mm) => {
  if (!mm) return
  currentLayout.value = mm.getLayout()
}, { immediate: true })

function setLayout(layout) {
  if (!props.mindMap) return
  currentLayout.value = layout
  props.mindMap.setLayout(layout)
}
</script>

<style scoped>
.structure-panel {
  padding: 8px;
}
.layout-group {
  margin-bottom: 16px;
}
.group-name {
  font-weight: 600;
  color: var(--ss-text);
  margin-bottom: 10px;
  font-size: 13px;
}
.layout-list {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.layout-item {
  width: 126px;
  height: 74px;
  cursor: pointer;
  border: 2px solid var(--ss-border);
  border-radius: var(--ss-radius-sm);
  overflow: hidden;
  padding: 4px;
  transition: all 0.2s;
  background: #fff;
}
.layout-item:hover {
  box-shadow: var(--ss-shadow-lg);
}
.layout-item.active {
  border-color: var(--ss-primary);
}
.layout-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
</style>
