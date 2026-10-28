<template>
  <div
    v-if="visible"
    class="context-menu"
    :style="{ left: `${x}px`, top: `${y}px` }"
    @click.stop
  >
    <div class="menu-item" @click="insertChild">插入子节点</div>
    <div class="menu-item" @click="insertSibling">插入兄弟节点</div>
    <div v-if="activeNode" v-auth="'task:create'" class="menu-item" @click="createTaskFromNode">创建任务</div>
    <div class="menu-divider"></div>
    <div class="menu-item danger" @click="deleteNode">删除节点</div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { createTask } from '@/api/task'

const props = defineProps({
  mindMap: Object,
})

const visible = ref(false)
const x = ref(0)
const y = ref(0)
const activeNode = ref(null)

watch(() => props.mindMap, (mm) => {
  if (!mm) return
  mm.on('node_contextmenu', (node, e) => {
    e.preventDefault()
    activeNode.value = node
    x.value = e.clientX
    y.value = e.clientY
    visible.value = true
  })
  mm.on('contextmenu', (e) => {
    e.preventDefault()
    activeNode.value = null
    x.value = e.clientX
    y.value = e.clientY
    visible.value = true
  })
})

const route = useRoute()

function hide() {
  visible.value = false
}

function insertChild() {
  if (activeNode.value) {
    activeNode.value.insertChild()
  } else {
    props.mindMap.execCommand('INSERT_CHILD_NODE')
  }
  hide()
}

function insertSibling() {
  if (activeNode.value) {
    activeNode.value.insertBrotherNode('down')
  } else {
    props.mindMap.execCommand('INSERT_NODE')
  }
  hide()
}

function deleteNode() {
  if (activeNode.value) {
    activeNode.value.remove()
  } else {
    props.mindMap.execCommand('REMOVE_NODE')
  }
  hide()
}

// 节点 → 任务：写入 case_map_id / case_node_id（§九 用例联动）
async function createTaskFromNode() {
  const node = activeNode.value
  hide()
  if (!node) return
  const nodeData = node.nodeData?.data || {}
  const mapId = route.params.mapId
  if (!mapId) return
  try {
    const { value } = await ElMessageBox.prompt('任务标题', '从节点创建任务', {
      confirmButtonText: '创建',
      cancelButtonText: '取消',
      inputValue: nodeData.text || '',
      inputValidator: (v) => !!v?.trim() || '标题不能为空',
    })
    await createTask({
      title: value.trim(),
      case_map_id: mapId,
      case_node_id: nodeData.uid || null,
    })
    ElMessage.success('任务已创建，可在「任务管理」中查看')
  } catch {
    // 取消或失败（失败已由 request 拦截器提示）
  }
}

defineExpose({ hide })
</script>

<style scoped>
.context-menu {
  position: fixed;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  padding: 6px 0;
  z-index: 2000;
  min-width: 140px;
}
.menu-item {
  padding: 8px 16px;
  font-size: 13px;
  cursor: pointer;
  position: relative;
}
.menu-item:hover {
  background: #f5f7fa;
}
.menu-item.danger {
  color: #f56c6c;
}
.menu-divider {
  height: 1px;
  background: #e4e7ed;
  margin: 4px 0;
}
</style>
