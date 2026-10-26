<template>
  <div class="wiki-sidebar">
    <div class="ws-toolbar">
      <span class="toolbar-title">
        <el-icon><Folder /></el-icon>文档
      </span>
      <span class="ws-toolbar-actions">
        <el-tooltip content="新建文档" placement="bottom">
          <el-icon v-auth="'wiki:edit'" class="ws-icon" @click="emitCreate('root')"><DocumentAdd /></el-icon>
        </el-tooltip>
        <el-tooltip content="新建目录" placement="bottom">
          <el-icon v-auth="'wiki:edit'" class="ws-icon" @click="emitCreateFolder('root')"><FolderAdd /></el-icon>
        </el-tooltip>
        <el-tooltip content="刷新" placement="bottom">
          <el-icon class="ws-icon" @click="$emit('refresh')"><Refresh /></el-icon>
        </el-tooltip>
      </span>
    </div>

    <el-input
      v-model="filterText"
      size="small"
      placeholder="过滤文档…"
      clearable
      class="ws-filter"
    />

    <div class="ws-tree">
      <el-tree
        ref="treeRef"
        :data="tree"
        :props="{ label: 'name', children: 'children' }"
        node-key="path"
        :default-expanded-keys="expandedKeys"
        :expand-on-click-node="true"
        :highlight-current="true"
        :filter-node-method="filterNode"
        :current-node-key="activePath"
        @node-click="onNodeClick"
        @node-contextmenu="onContextMenu"
      >
        <template #default="{ data }">
          <el-icon v-if="data.type === 'folder'" class="node-icon folder"><Folder /></el-icon>
          <el-icon v-else class="node-icon page"><Document /></el-icon>
          <span class="node-label">{{ data.name }}</span>
        </template>
      </el-tree>
      <el-empty v-if="!tree.length" description="空库，点击右上角新建文档" :image-size="60" />
    </div>

    <!-- 右键菜单 -->
    <div
      v-if="ctxMenu.visible"
      class="ctx-menu"
      :style="{ top: ctxMenu.y + 'px', left: ctxMenu.x + 'px' }"
      @click.stop
    >
      <div v-if="ctxMenu.data?.type === 'folder'" class="ctx-item" v-auth="'wiki:edit'" @click="ctxAction('new-page')">新建文档</div>
      <div v-if="ctxMenu.data?.type === 'folder'" class="ctx-item" v-auth="'wiki:edit'" @click="ctxAction('new-folder')">新建子目录</div>
      <div class="ctx-item" v-auth="'wiki:edit'" @click="ctxAction('rename')">重命名 / 移动</div>
      <div class="ctx-item" v-auth="'wiki:delete'" @click="ctxAction('delete')">删除</div>
    </div>
    <div v-if="ctxMenu.visible" class="ctx-mask" @click="closeCtx" @contextmenu.prevent="closeCtx" />
  </div>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'

const props = defineProps({
  tree: { type: Array, default: () => [] },
  activePath: { type: String, default: '' },
})
const emit = defineEmits(['open', 'refresh', 'create', 'create-folder', 'rename', 'delete'])

const treeRef = ref(null)
const filterText = ref('')
const expandedKeys = ref([])

watch(filterText, (val) => {
  treeRef.value?.filter(val)
})

function filterNode(value, data) {
  if (!value) return true
  return data.name.toLowerCase().includes(value.toLowerCase())
}

function onNodeClick(data) {
  if (data.type === 'page') {
    emit('open', data.path)
  }
}

const ctxMenu = reactive({ visible: false, x: 0, y: 0, data: null })

function onContextMenu(e, data) {
  e.preventDefault()
  ctxMenu.visible = true
  ctxMenu.x = e.clientX
  ctxMenu.y = e.clientY
  ctxMenu.data = data
}

function closeCtx() {
  ctxMenu.visible = false
  ctxMenu.data = null
}

function ctxAction(action) {
  const data = ctxMenu.data
  closeCtx()
  if (!data) return
  if (action === 'new-page') emit('create', data.path)
  else if (action === 'new-folder') emit('create-folder', data.path)
  else if (action === 'rename') emit('rename', data)
  else if (action === 'delete') emit('delete', data)
}

function emitCreate(folder) {
  emit('create', folder === 'root' ? '' : folder)
}

function emitCreateFolder(folder) {
  emit('create-folder', folder === 'root' ? '' : folder)
}
</script>

<style scoped>
.wiki-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fff;
  border-right: 1px solid var(--ss-border);
}
.ws-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-bottom: 1px solid var(--ss-border);
}
.toolbar-title {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-weight: 600;
  font-size: 13px;
  color: var(--ss-text);
}
.ws-toolbar-actions {
  display: inline-flex;
  gap: 8px;
}
.ws-icon {
  cursor: pointer;
  color: var(--ss-text-secondary);
  padding: 3px;
  border-radius: 4px;
}
.ws-icon:hover {
  color: var(--ss-primary);
  background: var(--ss-primary-light);
}
.ws-filter {
  padding: 8px 10px;
}
.ws-tree {
  flex: 1;
  overflow-y: auto;
  padding: 0 6px 12px;
}
.node-icon {
  margin-right: 5px;
  font-size: 14px;
}
.node-icon.folder {
  color: #e6a23c;
}
.node-icon.page {
  color: var(--ss-text-secondary);
}
.node-label {
  font-size: 13px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ctx-menu {
  position: fixed;
  z-index: 3000;
  background: #fff;
  border-radius: var(--ss-radius-sm);
  box-shadow: var(--ss-shadow-lg);
  border: 1px solid var(--ss-border);
  padding: 4px;
  min-width: 130px;
}
.ctx-item {
  padding: 7px 14px;
  font-size: 13px;
  color: var(--ss-text);
  cursor: pointer;
  border-radius: 4px;
}
.ctx-item:hover {
  background: var(--ss-primary-light);
  color: var(--ss-primary);
}
.ctx-mask {
  position: fixed;
  inset: 0;
  z-index: 2999;
}
</style>
