<template>
  <div class="icon-panel">
    <div v-for="group in nodeIconList" :key="group.type" class="icon-group">
      <div class="panel-title">{{ group.name }}</div>
      <div class="icon-list">
        <div
          v-for="item in group.list"
          :key="group.type + '_' + item.name"
          class="icon-item"
          :class="{ selected: iconList.includes(group.type + '_' + item.name) }"
          :title="group.type + '_' + item.name"
          @click="setIcon(group.type, item.name)"
        >
          <span class="icon-svg" v-html="getHtml(item.icon)"></span>
        </div>
      </div>
    </div>
    <div class="actions">
      <el-button size="small" type="danger" plain @click="removeIcon">移除图标</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { nodeIconList } from 'simple-mind-map/src/svg/icons.js'

const props = defineProps({
  mindMap: Object,
})

// 当前激活节点（可能多选）
const activeNodes = ref([])
// 单选时回显该节点的图标列表
const iconList = ref([])

watch(() => props.mindMap, (mm) => {
  if (!mm) return
  mm.on('node_active', (node, list) => {
    syncActiveNodes(list)
  })
  // 面板可能是节点已激活后才打开的（如切换页签），初始化时同步当前激活节点
  syncActiveNodes(mm.renderer.activeNodeList)
}, { immediate: true })

function syncActiveNodes(list) {
  activeNodes.value = [...(list || [])]
  if (activeNodes.value.length === 1) {
    iconList.value = activeNodes.value[0].getData('icon') || []
  } else {
    iconList.value = []
  }
}

// 图标可能是 svg 字符串，也可能是图片 url
function getHtml(icon) {
  return /^<svg/.test(icon) ? icon : `<img src="${icon}" />`
}

// 参考官方 demo：同类图标替换、再次点击取消、不同类可共存
function setIcon(type, name) {
  if (activeNodes.value.length === 0) return
  activeNodes.value.forEach(node => {
    const list = [...(node.getData('icon') || [])]
    const key = type + '_' + name
    const index = list.findIndex(item => item === key)
    if (index !== -1) {
      // 删除 icon
      list.splice(index, 1)
    } else {
      const typeIndex = list.findIndex(item => item.split('_')[0] === type)
      if (typeIndex !== -1) {
        // 替换同类 icon
        list.splice(typeIndex, 1, key)
      } else {
        // 新增 icon
        list.push(key)
      }
    }
    node.setIcon(list)
    if (activeNodes.value.length === 1) {
      iconList.value = list
    }
  })
}

function removeIcon() {
  if (activeNodes.value.length === 0) return
  activeNodes.value.forEach(node => {
    node.setIcon([])
  })
  iconList.value = []
}
</script>

<style scoped>
.icon-panel {
  padding: 8px;
}
.icon-group {
  margin-bottom: 16px;
}
.panel-title {
  font-weight: 600;
  margin-bottom: 10px;
  font-size: 13px;
  color: var(--ss-text-secondary);
}
.icon-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.icon-item {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  border-radius: 6px;
  transition: background 0.15s;
}
.icon-item:hover {
  background: var(--ss-primary-light);
}
.icon-item.selected::after {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 50%;
  border: 2px solid var(--ss-primary);
}
.icon-svg {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
}
.icon-svg :deep(svg),
.icon-svg :deep(img) {
  width: 100%;
  height: 100%;
}
.actions {
  display: flex;
  justify-content: flex-end;
}
</style>
