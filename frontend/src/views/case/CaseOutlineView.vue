<template>
  <div class="case-outline-view" @mouseenter="isInArea = true" @mouseleave="isInArea = false">
    <el-tree
      v-if="treeData.length > 0"
      ref="treeRef"
      class="outline-tree"
      node-key="uid"
      :draggable="!readonly"
      default-expand-all
      :data="treeData"
      :props="{ label: 'label', children: 'children' }"
      :highlight-current="true"
      :expand-on-click-node="false"
      :allow-drag="checkAllowDrag"
      @node-drop="onNodeDrop"
      @current-change="onCurrentChange"
    >
      <template #default="{ data }">
        <span
          class="outline-node"
          :data-id="data.uid"
          :class="{ 'is-root': data.root }"
          @click="onClick(data)"
        >
          <span
            :key="data.uid + data.label"
            class="node-edit"
            :class="{ 'is-readonly': readonly }"
            :contenteditable="!readonly"
            :spellcheck="false"
            @keydown.stop="onNodeInputKeydown($event, data)"
            @keyup.stop
            @blur="onBlur($event, data)"
            @paste="onPaste"
            v-html="data.label"
          ></span>
          <!-- 节点附属信息（与画布一致：备注 / 标签） -->
          <span v-if="data.hasNote" class="node-note" title="含备注">📄</span>
          <span v-if="data.tags && data.tags.length" class="node-tags">
            <span v-for="tg in data.tags" :key="tg" class="node-tag">{{ tg }}</span>
          </span>
        </span>
      </template>
    </el-tree>
    <div v-else class="empty">暂无内容</div>
  </div>
</template>

<script setup>
// 层级文本视图（大纲）：占据画布区域的可编辑层级文本树，与导图画布双向同步。
// 同步机制与 panels/OutlinePanel.vue 一致（data_change 刷新 + notHandleDataChange 防回环 + execCommand 编辑），
// 差异在于全屏排版、节点附属信息（备注/标签）与只读模式支持。
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
  readonly: { type: Boolean, default: false },
})

const treeRef = ref(null)
const treeData = ref([])
const currentData = ref(null)
const isInArea = ref(false)

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

// 刷新树数据：富文本转纯文本、转义 HTML、换行转 <br>；附带备注/标签供行内展示
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
    node.hasNote = !!node.data.note
    node.tags = node.data.tag || []
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
      const el = document.querySelector(`.outline-node[data-id="${uid}"] .node-edit`)
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

// 失去焦点更新节点文本（同步回画布数据）
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
  if (props.readonly) return
  handleInputPasteText(e)
}

// 节点输入区域按键：Enter 插入兄弟节点，Tab 插入子节点，Shift+Tab 上升一级
function onNodeInputKeydown(e, data) {
  if (props.readonly) return
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
  if (!props.mindMap || props.readonly) return
  pendingFocusUid = createUid()
  props.mindMap.execCommand(command, false, [], { uid: pendingFocusUid })
}

// 拖拽结束：移动到目标节点前/后/内部
function onNodeDrop(draggingNode, dropNode, position) {
  if (props.readonly) return
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

// 点击行：激活画布对应节点（Enter/Tab 插入等 execCommand 依赖激活节点）
function onClick(data) {
  if (!props.mindMap) return
  const targetNode = props.mindMap.renderer.findNodeByUid(data.uid)
  if (targetNode && targetNode.nodeData.data.isActive) return
  notHandleDataChange = true
  props.mindMap.execCommand('GO_TARGET_NODE', data.uid, () => {
    notHandleDataChange = false
  })
}

// 在大纲区域内按 Delete/Backspace 删除选中节点
function onKeyDown(e) {
  if (props.readonly || !isInArea.value || !currentData.value) return
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
.case-outline-view {
  width: 100%;
  height: 100%;
  overflow: auto;
  background: #fff;
  padding: 28px 40px;
  box-sizing: border-box;
}
.outline-tree {
  --el-tree-node-hover-bg-color: var(--ss-primary-light, #eef1fe);
  background: transparent;
  max-width: 980px;
}
.outline-tree :deep(.el-tree-node__content) {
  height: auto;
  min-height: 36px;
  border-radius: var(--ss-radius-sm, 6px);
  padding-right: 16px;
}
.outline-tree :deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: var(--ss-primary-light, #eef1fe);
}
.outline-node {
  display: inline-flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 4px 8px;
  width: 100%;
  padding: 4px 0;
  color: var(--ss-text, #1f2937);
}
.outline-node.is-root > .node-edit {
  font-size: 17px;
  font-weight: 600;
}
.node-edit {
  outline: none;
  font-size: 14px;
  line-height: 1.6;
  white-space: normal;
  word-break: break-all;
  max-width: 100%;
  border-radius: 4px;
}
.node-edit:hover {
  background: rgba(0, 0, 0, 0.04);
}
.node-edit:focus {
  background: var(--ss-primary-light, #eef1fe);
  box-shadow: 0 0 0 1.5px var(--ss-primary, #4f6ef7) inset;
}
.node-edit.is-readonly {
  cursor: default;
}
.node-edit.is-readonly:hover {
  background: transparent;
}
.node-note {
  font-size: 12px;
  flex-shrink: 0;
}
.node-tags {
  display: inline-flex;
  flex-wrap: wrap;
  gap: 4px;
}
.node-tag {
  font-size: 11px;
  line-height: 1;
  padding: 3px 8px;
  border-radius: 999px;
  background: var(--ss-fill, #f7f7f9);
  color: var(--ss-text-secondary, #909399);
  white-space: nowrap;
}
.empty {
  color: var(--ss-text-muted, #9ca3af);
  text-align: center;
  padding: 40px 0;
  font-size: 14px;
}
</style>
