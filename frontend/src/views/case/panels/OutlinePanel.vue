<template>
  <div class="outline-panel">
    <el-tree
      v-if="treeData.length > 0"
      ref="treeRef"
      class="outline-tree"
      node-key="uid"
      draggable
      default-expand-all
      :data="treeData"
      :props="{ label: 'label', children: 'children' }"
      :highlight-current="true"
      :expand-on-click-node="false"
      :allow-drag="checkAllowDrag"
      @node-drop="onNodeDrop"
      @current-change="onCurrentChange"
      @mouseenter="isInTreeArea = true"
      @mouseleave="isInTreeArea = false"
    >
      <template #default="{ data }">
        <span class="custom-node" :data-id="data.uid" @click="onClick(data)">
          <span
            :key="data.uid + data.label"
            class="node-edit"
            contenteditable
            @keydown.stop="onNodeInputKeydown($event, data)"
            @keyup.stop
            @blur="onBlur($event, data)"
            @paste="onPaste"
            v-html="data.label"
          ></span>
        </span>
      </template>
    </el-tree>
    <div v-else class="empty">暂无数据</div>
  </div>
</template>

<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import {
  nodeRichTextToTextWithWrap,
  textToNodeRichTextWithWrap,
  createUid,
  htmlEscape,
  handleInputPasteText,
} from 'simple-mind-map/src/utils/index.js'

const props = defineProps({
  mindMap: Object,
})

const treeRef = ref(null)
const treeData = ref([])
const currentData = ref(null)
const isInTreeArea = ref(false)

// 在大纲里操作节点时跳过下一次 data_change 刷新，避免树被重建打断编辑
let notHandleDataChange = false
// 插入新节点后需要聚焦的 uid
let pendingFocusUid = ''

watch(() => props.mindMap, (mm) => {
  if (!mm) return
  mm.on('data_change', handleDataChange)
  refresh()
}, { immediate: true })

onBeforeUnmount(() => {
  props.mindMap?.off('data_change', handleDataChange)
  window.removeEventListener('keydown', onKeyDown)
})
window.addEventListener('keydown', onKeyDown)

function handleDataChange() {
  if (notHandleDataChange) {
    notHandleDataChange = false
    return
  }
  refresh()
}

// 刷新树数据（参考官方 demo：富文本转纯文本、转义 HTML、换行转 <br>）
function refresh() {
  if (!props.mindMap) return
  const data = props.mindMap.getData()
  if (!data) return
  data.root = true // 标记根节点，禁止拖拽
  const walk = (node) => {
    let text = node.data.richText
      ? nodeRichTextToTextWithWrap(node.data.text)
      : node.data.text
    text = htmlEscape(text || '')
    text = text.replace(/\n/g, '<br>')
    node.textCache = text // 保存修改前的数据，用于对比是否修改了
    node.label = text
    node.uid = node.data.uid
    ;(node.children || []).forEach(walk)
  }
  walk(data)
  treeData.value = [data]
  focusPendingNode()
}

// 插入新节点后高亮、定位并聚焦编辑框
function focusPendingNode() {
  if (!pendingFocusUid) return
  const uid = pendingFocusUid
  pendingFocusUid = ''
  setTimeout(() => {
    try {
      treeRef.value?.setCurrentKey(uid)
      const el = document.querySelector(`.custom-node[data-id="${uid}"] .node-edit`)
      if (el) {
        const selection = window.getSelection()
        const range = document.createRange()
        range.selectNodeContents(el)
        selection.removeAllRanges()
        selection.addRange(range)
      }
    } catch (e) {
      // ignore
    }
  }, 50)
}

// 根节点不允许拖拽
function checkAllowDrag(node) {
  return !node.data.root
}

// 失去焦点更新节点文本
function onBlur(e, data) {
  if (data.textCache === e.target.innerHTML) return
  const richText = data.data.richText
  const text = richText ? e.target.innerHTML : e.target.innerText
  const targetNode = props.mindMap?.renderer.findNodeByUid(data.uid)
  if (!targetNode) return
  notHandleDataChange = true
  if (richText) {
    targetNode.setText(textToNodeRichTextWithWrap(text), true)
  } else {
    targetNode.setText(text)
  }
}

// 拦截粘贴事件，只粘贴纯文本
function onPaste(e) {
  handleInputPasteText(e)
}

// 节点输入区域按键：Enter 插入兄弟节点，Tab 插入子节点，Shift+Tab 上升一级
function onNodeInputKeydown(e, data) {
  if (e.keyCode === 13 && !e.shiftKey) {
    e.preventDefault()
    e.target.blur()
    insertNode('INSERT_NODE')
  } else if (e.keyCode === 9) {
    e.preventDefault()
    e.target.blur()
    if (e.shiftKey) {
      props.mindMap?.execCommand('MOVE_UP_ONE_LEVEL')
    } else {
      insertNode('INSERT_CHILD_NODE')
    }
  }
}

function insertNode(command) {
  if (!props.mindMap) return
  pendingFocusUid = createUid()
  props.mindMap.execCommand(command, false, [], { uid: pendingFocusUid })
}

// 激活节点并移动到画布中间
function onClick(data) {
  if (!props.mindMap) return
  const targetNode = props.mindMap.renderer.findNodeByUid(data.uid)
  if (targetNode && targetNode.nodeData.data.isActive) return
  notHandleDataChange = true
  props.mindMap.execCommand('GO_TARGET_NODE', data.uid, () => {
    notHandleDataChange = false
  })
}

// 拖拽结束：移动到目标节点前/后/内部
function onNodeDrop(draggingNode, dropNode, position) {
  const node = props.mindMap?.renderer.findNodeByUid(draggingNode.data.uid)
  const targetNode = props.mindMap?.renderer.findNodeByUid(dropNode.data.uid)
  if (!node || !targetNode) return
  notHandleDataChange = true
  switch (position) {
    case 'before':
      props.mindMap.execCommand('INSERT_BEFORE', node, targetNode)
      break
    case 'after':
      props.mindMap.execCommand('INSERT_AFTER', node, targetNode)
      break
    case 'inner':
      props.mindMap.execCommand('MOVE_NODE_TO', node, targetNode)
      break
  }
}

function onCurrentChange(data) {
  currentData.value = data
}

// 在树区域内按 Delete/Backspace 删除节点
function onKeyDown(e) {
  if (!isInTreeArea.value || !currentData.value) return
  if ([46, 8].includes(e.keyCode)) {
    // 编辑中不响应
    if (document.activeElement?.classList?.contains('node-edit')) return
    e.stopPropagation()
    const node = props.mindMap?.renderer.findNodeByUid(currentData.value.uid)
    if (node && !node.isRoot) {
      notHandleDataChange = true
      props.mindMap.execCommand('REMOVE_NODE', [node])
    }
  }
}
</script>

<style scoped>
.outline-panel {
  padding: 8px 4px;
}
.outline-tree {
  --el-tree-node-hover-bg-color: var(--ss-primary-light);
  background: transparent;
}
.outline-tree :deep(.el-tree-node__content) {
  height: auto;
  min-height: 32px;
  border-radius: var(--ss-radius-sm);
}
.outline-tree :deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: var(--ss-primary-light);
  color: var(--ss-primary);
}
.custom-node {
  width: 100%;
  color: var(--ss-text);
  font-size: 13px;
}
.node-edit {
  outline: none;
  white-space: normal;
  word-break: break-all;
  padding-right: 12px;
}
.empty {
  color: var(--ss-text-muted);
  text-align: center;
  padding: 20px 0;
  font-size: 13px;
}
</style>
