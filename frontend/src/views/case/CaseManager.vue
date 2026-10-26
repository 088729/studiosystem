<template>
  <div class="case-manager">
    <div
      class="tree-panel"
      :class="{ 'node-drag-over-blank': isNodeDragOverBlank, 'file-drag-over': isFileDragOver }"
      @contextmenu="handlePanelContextMenu"
      @dragover="handlePanelDragOver"
      @dragleave="handlePanelDragLeave"
      @drop="handlePanelDrop"
      @click="handlePanelClick"
    >
      <div class="tree-toolbar">
        <div class="toolbar-title">
          <el-icon class="title-icon"><Collection /></el-icon>
          <span>用例库</span>
        </div>
        <div class="toolbar-actions">
          <el-button v-auth="'xmind:manage'" link type="primary" title="新建文件夹" @click="createFolder()">
            <el-icon><FolderAdd /></el-icon>
          </el-button>
          <el-button v-auth="'xmind:edit'" link type="primary" title="新建导图" @click="createMap()">
            <el-icon><DocumentAdd /></el-icon>
          </el-button>
        </div>
      </div>

      <el-input
        v-model="search"
        placeholder="搜索文件夹/导图"
        clearable
        size="small"
        class="tree-search"
        @input="filterTree"
      />

      <el-tree
        ref="treeRef"
        :data="treeData"
        :props="{ label: 'name', children: 'children' }"
        node-key="id"
        highlight-current
        :default-expanded-keys="expandedKeys"
        :filter-node-method="filterNode"
        :draggable="true"
        :allow-drop="allowDrop"
        @node-click="handleNodeClick"
        @node-drop="handleNodeDrop"
        @node-drag-start="handleTreeDragStart"
        @node-drag-end="handleTreeDragEnd"
        @node-expand="handleExpand"
        @node-collapse="handleCollapse"
        @node-contextmenu="handleContextMenu"
      >
        <template #default="{ node, data }">
          <div
            class="tree-node"
            :class="{
              'is-map': data.type === 'map',
              'is-selected': selectedIdSet.has(data.id),
              'is-cut': clipboard && clipboard.action === 'cut' && clipboard.items?.some(i => i.id === data.id),
            }"
            :data-node-id="data.id"
            :data-node-type="data.type"
            @dblclick="handleNodeDblClick(data)"
          >
            <el-icon v-if="data.type === 'folder'" class="node-icon folder-icon">
              <FolderOpened v-if="node.expanded" />
              <Folder v-else />
            </el-icon>
            <el-icon v-else class="node-icon map-icon">
              <Document />
            </el-icon>
            <span class="node-label" :title="data.name">{{ data.name }}</span>
            <span v-if="data.type === 'map' && data.current_version" class="node-meta">v{{ data.current_version }}</span>
          </div>
        </template>
      </el-tree>
    </div>

    <div
      class="preview-panel"
      :class="{ 'drag-over': isDragOver }"
      @dragover.prevent="isDragOver = true"
      @dragleave="isDragOver = false"
      @drop.prevent="handleDrop"
    >
      <div v-if="selectedMap" class="preview-card">
        <div class="preview-header">
          <div class="preview-title">
            <h3>{{ selectedMap.title }}</h3>
            <span v-if="selectedMap.current_version" class="version-badge">v{{ selectedMap.current_version }}</span>
          </div>
          <div class="header-actions">
            <el-button type="primary" @click="openEditor(selectedMap.id)">
              <el-icon><Edit /></el-icon>&nbsp;打开编辑器
            </el-button>
          </div>
        </div>
        <div class="meta-grid">
          <div class="meta-item">
            <span class="meta-label">负责人</span>
            <span class="meta-value">{{ selectedMap.owner }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">当前版本</span>
            <span class="meta-value">v{{ selectedMap.current_version }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">创建时间</span>
            <span class="meta-value">{{ formatTime(selectedMap.created_at) }}</span>
          </div>
          <div class="meta-item">
            <span class="meta-label">最后修改</span>
            <span class="meta-value">{{ formatTime(selectedMap.last_modified_at) }}</span>
          </div>
        </div>
        <el-alert v-if="selectedMap.has_draft" title="该导图有未保存的草稿" type="warning" :closable="false" class="draft-alert" />
        <div ref="previewContainer" class="preview-mind-map"></div>
      </div>
      <div v-else class="empty">
        <el-empty description="在左侧选择文件夹或导图">
          <template #description>
            <p>在左侧选择文件夹或导图</p>
            <p class="empty-tip">也可以把 .xmind / .md / .json 文件拖到这里导入</p>
          </template>
        </el-empty>
      </div>
    </div>

    <Teleport to="body">
      <div
        v-if="contextMenu.visible"
        class="context-menu"
        :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
      >
        <!-- 空白区域右键 -->
        <div v-if="!contextMenu.data">
          <div v-auth="'xmind:manage'" class="menu-item" @click="createFolderAtRoot">
            <el-icon><FolderAdd /></el-icon> 新建文件夹
          </div>
          <div v-auth="'xmind:edit'" class="menu-item" @click="createMapAtRoot">
            <el-icon><DocumentAdd /></el-icon> 新建导图
          </div>
        </div>
        <!-- 文件夹右键 -->
        <div v-else-if="contextMenu.data?.type === 'folder'">
          <div class="menu-item" @click="createMapInFolder(contextMenu.data)">
            <el-icon><DocumentAdd /></el-icon> 新建导图
          </div>
          <div class="menu-item" @click="createFolderIn(contextMenu.data)">
            <el-icon><FolderAdd /></el-icon> 新建子文件夹
          </div>
          <div v-auth="'xmind:manage'" class="menu-item" @click="renameFolder(contextMenu.data)">
            <el-icon><EditPen /></el-icon> 重命名
          </div>
          <div v-auth="'xmind:manage'" class="menu-item danger" @click="handleDeleteMenuClick(contextMenu.data)">
            <el-icon><Delete /></el-icon> 删除
          </div>
        </div>
        <!-- 导图右键 -->
        <div v-else>
          <div class="menu-item" @click="openEditor(contextMenu.data.id)">
            <el-icon><Edit /></el-icon> 打开
          </div>
          <div v-auth="'xmind:edit'" class="menu-item" @click="renameMapItem(contextMenu.data)">
            <el-icon><EditPen /></el-icon> 重命名
          </div>
          <div v-auth="'xmind:edit'" class="menu-item" @click="copyMap(contextMenu.data.id)">
            <el-icon><CopyDocument /></el-icon> 复制
          </div>
          <div v-auth="'xmind:delete'" class="menu-item danger" @click="handleDeleteMenuClick(contextMenu.data)">
            <el-icon><Delete /></el-icon> 删除
          </div>
        </div>
      </div>
    </Teleport>

    <!-- 新建文件夹 / 新建导图 弹窗 -->
    <CaseCreateDialog ref="createDialog" :folders="folders" @created="onCreated" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import MindMap from 'simple-mind-map'
import dayjs from 'dayjs'
import {
  Folder,
  FolderOpened,
  FolderAdd,
  Document,
  DocumentAdd,
  Collection,
  EditPen,
  Edit,
  Delete,
  CopyDocument,
} from '@element-plus/icons-vue'
import * as caseApi from '@/api/case'
import CaseCreateDialog from './dialogs/CaseCreateDialog.vue'

const router = useRouter()
const treeRef = ref(null)
const folders = ref([])
const maps = ref([])
const search = ref('')
const selectedMap = ref(null)
const isDragOver = ref(false)
const previewContainer = ref(null)
const previewMindMap = ref(null)
const expandedKeys = ref([])
const createDialog = ref(null)
// 内部剪贴板：{ action: 'copy' | 'cut', items: 节点数据数组 }
const clipboard = ref(null)
// 多选：当前选中的节点数组 + Shift 范围选的锚点
const selectedNodes = ref([])
const anchorId = ref(null)
const selectedIdSet = computed(() => new Set(selectedNodes.value.map(n => n.id)))
const contextMenu = ref({ visible: false, x: 0, y: 0, data: null })

const treeData = computed(() => {
  const map = {}
  folders.value.forEach(f => {
    map[f.id] = {
      id: f.id,
      name: f.name,
      type: 'folder',
      parent_id: f.parent_id,
      children: [],
    }
  })
  const roots = []
  folders.value.forEach(f => {
    const node = map[f.id]
    if (f.parent_id && map[f.parent_id]) {
      map[f.parent_id].children.push(node)
    } else {
      roots.push(node)
    }
  })
  maps.value.forEach(m => {
    const mapNode = {
      id: m.id,
      name: m.title,
      type: 'map',
      folder_id: m.folder_id,
      owner: m.owner,
      current_version: m.current_version,
      created_at: m.created_at,
      last_modified_at: m.last_modified_at,
      has_draft: m.has_draft,
    }
    if (m.folder_id && map[m.folder_id]) {
      map[m.folder_id].children.push(mapNode)
    } else {
      roots.push(mapNode)
    }
  })
  return roots
})

async function loadFolders() {
  const res = await caseApi.fetchFolderTree()
  folders.value = res.items
}

async function loadMaps() {
  const res = await caseApi.fetchMaps({ list_all: true })
  maps.value = res.items.map(m => ({ ...m, has_draft: false }))
}

async function loadAll() {
  await Promise.all([loadFolders(), loadMaps()])
  if (expandedKeys.value.length === 0) {
    expandedKeys.value = folders.value.filter(f => !f.parent_id).map(f => f.id)
  }
}

function filterNode(value, data) {
  if (!value) return true
  return data.name.toLowerCase().includes(value.toLowerCase())
}

function filterTree() {
  treeRef.value?.filter(search.value)
}

function isSelected(data) {
  return selectedIdSet.value.has(data.id)
}

// 按可见顺序展开树（文件夹未展开时其子节点不可见，与 Windows 资源管理器一致）
function flattenVisible() {
  const result = []
  const walk = (nodes) => {
    nodes.forEach(n => {
      result.push(n)
      if (n.type === 'folder' && expandedKeys.value.includes(n.id)) walk(n.children || [])
    })
  }
  walk(treeData.value)
  return result
}

// 点击选中：普通点击单选，Ctrl+点击切换选中，Shift+点击从锚点范围选择
function handleNodeClick(data, node, comp, e) {
  hideContextMenu()
  if (e?.ctrlKey || e?.metaKey) {
    if (isSelected(data)) {
      selectedNodes.value = selectedNodes.value.filter(n => n.id !== data.id)
    } else {
      selectedNodes.value = [...selectedNodes.value, data]
      anchorId.value = data.id
    }
  } else if (e?.shiftKey && anchorId.value) {
    const flat = flattenVisible()
    const a = flat.findIndex(n => n.id === anchorId.value)
    const b = flat.findIndex(n => n.id === data.id)
    if (a !== -1 && b !== -1) {
      const [s, t] = a < b ? [a, b] : [b, a]
      selectedNodes.value = flat.slice(s, t + 1)
    } else {
      selectedNodes.value = [data]
      anchorId.value = data.id
    }
  } else {
    selectedNodes.value = [data]
    anchorId.value = data.id
  }
  // 仅单个导图被选中时显示预览
  const single = selectedNodes.value.length === 1 ? selectedNodes.value[0] : null
  if (single?.type === 'map') {
    selectedMap.value = single
    nextTick(() => renderPreview(single.id))
  }
}

// 点击面板空白区域清空选择
function handlePanelClick(e) {
  if (e.target.closest('.el-tree-node__content')) return
  selectedNodes.value = []
  anchorId.value = null
}

function handleNodeDblClick(data) {
  if (data.type === 'map') {
    openEditor(data.id)
  }
}

function handleExpand(data) {
  if (!expandedKeys.value.includes(data.id)) {
    expandedKeys.value.push(data.id)
  }
}

function handleCollapse(data) {
  expandedKeys.value = expandedKeys.value.filter(id => id !== data.id)
}

async function renderPreview(mapId) {
  if (previewMindMap.value) {
    previewMindMap.value.destroy()
    previewMindMap.value = null
  }
  try {
    const detail = await caseApi.fetchMap(mapId)
    selectedMap.value = {
      ...selectedMap.value,
      ...detail,
      has_draft: !!detail.temp_content,
    }
    if (!detail.latest_root || !previewContainer.value) return
    const options = {
      el: previewContainer.value,
      data: detail.latest_root.root,
      layout: detail.latest_root.layout || 'logicalStructure',
      theme: detail.latest_root.theme?.template || 'default',
      themeConfig: sanitizeThemeConfig(detail.latest_root.theme?.config),
      readonly: true,
      fit: true,
    }
    if (detail.latest_root.view?.transform) {
      options.viewData = detail.latest_root.view
    }
    previewMindMap.value = new MindMap(options)
  } catch (e) {
    console.error('preview error', e)
  }
}

function formatTime(time) {
  return time ? dayjs(time).format('YYYY-MM-DD HH:mm') : '-'
}

// 历史版本/草稿的 theme.config 可能是全量主题快照（包含 root/second/node 等完整结构），
// 加载时需要剔除，否则会覆盖所选主题导致切换主题无效
function sanitizeThemeConfig(config) {
  if (!config || typeof config !== 'object') return {}
  if (config.root || config.second || config.node) return {}
  return config
}

async function renameMapItem(map) {
  hideContextMenu()
  try {
    const { value: title } = await ElMessageBox.prompt('请输入新标题', '重命名导图', {
      inputValue: map.name,
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValidator: (val) => {
        if (!val || !val.trim()) return '标题不能为空'
        return true
      },
    })
    await caseApi.renameMap(map.id, { title: title.trim() })
    ElMessage.success('重命名成功')
    if (selectedMap.value?.id === map.id) {
      selectedMap.value = { ...selectedMap.value, title: title.trim() }
    }
    loadAll()
  } catch (e) {
    // 取消
  }
}

async function copyMap(id) {
  await caseApi.copyMap(id, {})
  ElMessage.success('复制成功')
  loadAll()
}

async function deleteMap(id) {
  await ElMessageBox.confirm('确认删除该导图？', '提示', { type: 'warning' })
  await caseApi.deleteMap(id)
  ElMessage.success('删除成功')
  selectedMap.value = null
  if (previewMindMap.value) {
    previewMindMap.value.destroy()
    previewMindMap.value = null
  }
  loadAll()
}

async function handleDrop(e) {
  isDragOver.value = false
  await importFiles(Array.from(e.dataTransfer.files), selectedMap.value?.folder_id || null)
}

// 批量导入文件，支持 .xmind / .md / .json，与编辑器内导入的格式一致
async function importFiles(files, targetFolder) {
  const xmindFiles = files.filter(f => f.name.endsWith('.xmind'))
  const mdFiles = files.filter(f => /\.(md|markdown)$/i.test(f.name))
  const jsonFiles = files.filter(f => f.name.endsWith('.json'))

  if (xmindFiles.length) {
    const formData = new FormData()
    xmindFiles.forEach(file => formData.append('files', file))
    if (targetFolder) formData.append('folder_id', targetFolder)
    const res = await caseApi.importMaps(formData)
    const successCount = res.results.filter(r => r.map_id).length
    ElMessage.success(`成功导入 ${successCount} 个 xmind 导图`)
    loadAll()
  }

  if (mdFiles.length) {
    // 与编辑器内导入使用同一个解析器
    const { default: markdown } = await import('simple-mind-map/src/parse/markdown.js')
    for (const file of mdFiles) {
      try {
        const text = await file.text()
        const rootNode = markdown.transformMarkdownTo(text)
        const fullData = buildFullData(rootNode)
        await caseApi.createMap({ title: rootNode.data.text || file.name, folder_id: targetFolder, root: fullData })
      } catch (e) {
        console.error('md import error', e)
        ElMessage.error(`${file.name} 解析失败`)
      }
    }
    ElMessage.success(`成功导入 ${mdFiles.length} 个 Markdown 导图`)
    loadAll()
  }

  if (jsonFiles.length) {
    for (const file of jsonFiles) {
      const text = await file.text()
      let data
      try {
        data = JSON.parse(text)
      } catch {
        ElMessage.error(`${file.name} 不是合法 JSON`)
        continue
      }
      if (!data.root) {
        ElMessage.error(`${file.name} 缺少 root 字段`)
        continue
      }
      const title = data.root?.data?.text || file.name
      await caseApi.createMap({ title, folder_id: targetFolder, root: data })
    }
    ElMessage.success(`成功导入 ${jsonFiles.length} 个 JSON 导图`)
    loadAll()
  }

  if (!xmindFiles.length && !mdFiles.length && !jsonFiles.length) {
    ElMessage.warning('请拖入 .xmind / .md / .json 文件')
  }
}

function buildFullData(rootNode) {
  return {
    root: rootNode,
    layout: 'logicalStructure',
    theme: { template: 'default', config: {} },
    view: { transform: { scale: 1, x: 0, y: 0 } },
  }
}

// ---------- 新建文件夹 / 新建导图（弹窗见 CaseCreateDialog） ----------
// 位置语义：显式传 null = 根目录（空白处右键）；undefined = 跟随当前选中文件夹；传对象 = 该文件夹内
function resolveDefaultFolderId(explicit) {
  if (explicit !== undefined) return explicit
  const selectedNode = treeRef.value?.getCurrentNode()
  return selectedNode?.type === 'folder' ? selectedNode.id : null
}

function createFolder(parentId) {
  createDialog.value?.open({ kind: 'folder', folderId: resolveDefaultFolderId(parentId) })
}

function createFolderIn(folder) {
  hideContextMenu()
  createDialog.value?.open({ kind: 'folder', folderId: folder.id })
}

function createMap(folder) {
  createDialog.value?.open({ kind: 'map', folderId: resolveDefaultFolderId(folder?.id) })
}

function createMapInFolder(folder) {
  hideContextMenu()
  createDialog.value?.open({ kind: 'map', folderId: folder.id })
}

// 创建成功：刷新树；导图直接打开编辑器（对齐原行为）
function onCreated(item, kind) {
  loadAll()
  if (kind === 'map' && item?.id) {
    openEditor(item.id)
  }
}

async function renameFolder(folder) {
  hideContextMenu()
  try {
    const { value: name } = await ElMessageBox.prompt('请输入新名称', '重命名文件夹', {
      inputValue: folder.name,
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      inputValidator: (val) => {
        if (!val || !val.trim()) return '名称不能为空'
        return true
      },
    })
    await caseApi.renameFolder(folder.id, { name: name.trim() })
    ElMessage.success('重命名成功')
    loadAll()
  } catch (e) {
    // 取消
  }
}

async function deleteFolder(folder) {
  hideContextMenu()
  try {
    await ElMessageBox.confirm(`确认删除文件夹「${folder.name}」？其下所有导图将被软删除。`, '提示', { type: 'warning' })
    await caseApi.deleteFolder(folder.id)
    ElMessage.success('删除成功')
    loadAll()
  } catch (e) {
    // 取消
  }
}

function openEditor(id) {
  if (previewMindMap.value) {
    previewMindMap.value.destroy()
    previewMindMap.value = null
  }
  router.push(`/case/editor/${id}`)
}

// 当前被拖拽的树节点数据（el-tree 内部拖拽）
const draggedNodeData = ref(null)
const isNodeDragOverBlank = ref(false)
// 外部文件拖入面板
const isFileDragOver = ref(false)

function isFileDrag(e) {
  return e.dataTransfer?.types?.includes('Files')
}

function handleTreeDragStart(node) {
  draggedNodeData.value = node.data
}

function handleTreeDragEnd() {
  draggedNodeData.value = null
  isNodeDragOverBlank.value = false
}

// 与 Windows 一致：只允许拖到文件夹内部；文件夹不能拖到自己或自己的子孙里
function allowDrop(draggingNode, dropNode, type) {
  const d = draggingNode.data
  const t = dropNode.data
  if (type !== 'inner') return false
  if (t.type !== 'folder') return false
  if (d.type === 'map') return true
  if (d.type === 'folder') {
    if (d.id === t.id) return false
    let p = dropNode
    while (p) {
      if (p.data.id === d.id) return false
      p = p.parent
    }
    return true
  }
  return false
}

// 过滤掉祖先文件夹也在选中集里的项（移动/删除父文件夹时已包含其子项）
function effectiveItems(items) {
  const folderIds = new Set(items.filter(i => i.type === 'folder').map(i => i.id))
  return items.filter(item => {
    let pid = item.type === 'folder' ? item.parent_id : item.folder_id
    while (pid) {
      if (folderIds.has(pid)) return false
      pid = folders.value.find(f => f.id === pid)?.parent_id
    }
    return true
  })
}

// 批量移动一批节点到目标文件夹（targetFolderId 为 null 表示根目录）
async function moveItemsTo(items, targetFolderId) {
  const list = effectiveItems(items).filter(item => {
    if (item.type === 'map') return (item.folder_id || null) !== targetFolderId
    if (item.id === targetFolderId) return false
    if ((item.parent_id || null) === targetFolderId) return false
    // 文件夹不能移到自己的子孙里
    const anc = findNodeInTree(treeData.value, item.id)
    return !(targetFolderId && anc && findNodeInTree(anc.children || [], targetFolderId))
  })
  if (!list.length) return false
  for (const item of list) {
    if (item.type === 'map') {
      await caseApi.moveMap(item.id, { folder_id: targetFolderId })
    } else {
      await caseApi.moveFolder(item.id, { parent_id: targetFolderId })
    }
  }
  ElMessage.success('移动成功')
  loadAll()
  return true
}

// 拖拽放置：若拖的是多选中的一项，则移动整个选择集（与 Windows 一致）
async function handleNodeDrop(draggingNode, dropNode) {
  const d = draggingNode.data
  const items = isSelected(d) && selectedNodes.value.length > 1 ? selectedNodes.value : [d]
  await moveItemsTo(items, dropNode.data.id)
}

// 拖到面板空白区域 = 移动到根目录（与 Windows 一致）；外部文件拖入 = 导入
function handlePanelDragOver(e) {
  if (isFileDrag(e)) {
    e.preventDefault()
    isFileDragOver.value = true
    return
  }
  if (!draggedNodeData.value) return
  if (e.target.closest('.el-tree-node__content')) return
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'move'
  isNodeDragOverBlank.value = true
}

function handlePanelDragLeave(e) {
  isFileDragOver.value = false
  if (e.target.closest('.el-tree-node__content')) return
  isNodeDragOverBlank.value = false
}

async function handlePanelDrop(e) {
  // 外部文件拖入：拖到文件夹节点上导入到该文件夹，空白处导入到根目录
  if (isFileDrag(e)) {
    isFileDragOver.value = false
    e.preventDefault()
    const nodeEl = e.target.closest('.tree-node')
    const targetFolderId = nodeEl?.dataset?.nodeType === 'folder' ? nodeEl.dataset.nodeId : null
    await importFiles(Array.from(e.dataTransfer.files), targetFolderId)
    return
  }
  isNodeDragOverBlank.value = false
  const d = draggedNodeData.value
  if (!d) return
  if (e.target.closest('.el-tree-node__content')) return
  e.preventDefault()
  const items = isSelected(d) && selectedNodes.value.length > 1 ? selectedNodes.value : [d]
  await moveItemsTo(items, null)
}

// 右键未选中的节点时先选中它（与 Windows 一致）
function handleContextMenu(e, data) {
  e.preventDefault()
  if (!isSelected(data)) {
    selectedNodes.value = [data]
    anchorId.value = data.id
  }
  contextMenu.value = { visible: true, x: e.clientX, y: e.clientY, data }
}

// 面板空白区域右键：新建根级文件夹/导图（点在树节点上时交给节点右键处理）
function handlePanelContextMenu(e) {
  if (e.target.closest('.el-tree-node__content')) return
  e.preventDefault()
  contextMenu.value = { visible: true, x: e.clientX, y: e.clientY, data: null }
}

function createFolderAtRoot() {
  hideContextMenu()
  createFolder(null)
}

function createMapAtRoot() {
  hideContextMenu()
  createMap(null)
}

function hideContextMenu() {
  contextMenu.value.visible = false
}

// 右键菜单“删除”：目标在多选集合中时批量删除，否则仅删除目标本身
function handleDeleteMenuClick(data) {
  hideContextMenu()
  if (selectedNodes.value.length > 1 && isSelected(data)) {
    deleteSelected()
  } else if (data.type === 'folder') {
    deleteFolder(data)
  } else {
    deleteMap(data.id)
  }
}

// ===== Windows 风格快捷键：F2 重命名 / Delete 删除 / Ctrl+C 复制 / Ctrl+X 剪切 / Ctrl+V 粘贴 =====
function isEditingTarget(e) {
  return !!e.target.closest?.('input, textarea, [contenteditable="true"]')
}

function onKeyDown(e) {
  if (isEditingTarget(e)) return
  const selection = selectedNodes.value
  const lastNode = selection[selection.length - 1]

  if (e.key === 'F2') {
    if (!lastNode) return
    e.preventDefault()
    if (lastNode.type === 'folder') renameFolder(lastNode)
    else renameMapItem(lastNode)
    return
  }
  if (e.key === 'Delete') {
    if (!selection.length) return
    e.preventDefault()
    deleteSelected()
    return
  }
  if (!(e.ctrlKey || e.metaKey)) return
  const key = e.key.toLowerCase()
  if (key === 'c') {
    if (!selection.length) return
    e.preventDefault()
    const maps = selection.filter(i => i.type === 'map')
    if (!maps.length) {
      ElMessage.info('文件夹暂不支持复制，可用 Ctrl+X 剪切后 Ctrl+V 粘贴移动')
      return
    }
    clipboard.value = { action: 'copy', items: maps }
    ElMessage.success(`已复制 ${maps.length} 个导图，Ctrl+V 粘贴到目标文件夹`)
  } else if (key === 'x') {
    if (!selection.length) return
    e.preventDefault()
    const items = effectiveItems(selection)
    clipboard.value = { action: 'cut', items }
    ElMessage.success(`已剪切 ${items.length} 项，Ctrl+V 粘贴到目标文件夹`)
  } else if (key === 'v') {
    if (!clipboard.value) return
    e.preventDefault()
    // 粘贴目标：仅选中一个文件夹时进该文件夹，否则粘贴到根目录
    const target = selection.length === 1 && selection[0].type === 'folder' ? selection[0] : null
    pasteClipboard(target)
  }
}

// 批量删除选中项（祖先文件夹被选中时其子项不重复删除）
async function deleteSelected() {
  const items = effectiveItems(selectedNodes.value)
  if (!items.length) return
  const hasFolder = items.some(i => i.type === 'folder')
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${items.length} 项？${hasFolder ? '文件夹内所有导图将被软删除。' : ''}`,
      '提示',
      { type: 'warning' }
    )
  } catch {
    return
  }
  let failed = 0
  for (const item of items) {
    try {
      if (item.type === 'folder') await caseApi.deleteFolder(item.id)
      else await caseApi.deleteMap(item.id)
    } catch {
      failed++
    }
  }
  if (items.some(i => i.id === selectedMap.value?.id)) {
    selectedMap.value = null
    if (previewMindMap.value) {
      previewMindMap.value.destroy()
      previewMindMap.value = null
    }
  }
  if (failed) {
    ElMessage.warning(`已删除 ${items.length - failed} 项，${failed} 项删除失败`)
  } else {
    ElMessage.success('删除成功')
  }
  selectedNodes.value = []
  anchorId.value = null
  loadAll()
}

function findNodeInTree(nodes, id) {
  for (const n of nodes) {
    if (n.id === id) return n
    const r = findNodeInTree(n.children || [], id)
    if (r) return r
  }
  return null
}

async function pasteClipboard(targetNode) {
  const clip = clipboard.value
  if (!clip) return
  const targetFolderId = targetNode?.type === 'folder' ? targetNode.id : null
  if (clip.action === 'copy') {
    for (const item of clip.items.filter(i => i.type === 'map')) {
      await caseApi.copyMap(item.id, { folder_id: targetFolderId })
    }
    ElMessage.success('粘贴成功')
    loadAll()
  } else {
    // 剪切粘贴 = 批量移动（moveItemsTo 内部会处理自身/子孙防护）
    const moved = await moveItemsTo(clip.items, targetFolderId)
    if (moved) clipboard.value = null
  }
}

function onDocumentClick() {
  hideContextMenu()
}

onMounted(() => {
  loadAll()
  document.addEventListener('click', onDocumentClick)
  document.addEventListener('keydown', onKeyDown)
})

onBeforeUnmount(() => {
  document.removeEventListener('click', onDocumentClick)
  document.removeEventListener('keydown', onKeyDown)
  if (previewMindMap.value) {
    previewMindMap.value.destroy()
  }
})
</script>

<style scoped>
.case-manager {
  display: flex;
  gap: 16px;
  height: 100vh;
  background: var(--ss-bg);
  padding: 16px;
}
.tree-panel {
  width: 300px;
  background: #fff;
  border-radius: var(--ss-radius);
  box-shadow: var(--ss-shadow);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow: hidden;
  transition: box-shadow 0.2s;
}
.tree-panel.node-drag-over-blank {
  box-shadow: 0 0 0 2px var(--ss-primary) inset;
}
.tree-panel.file-drag-over {
  outline: 2px dashed var(--ss-primary);
  outline-offset: -6px;
  background: var(--ss-primary-light);
}
.tree-toolbar {
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid var(--ss-border);
}
.toolbar-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 15px;
  color: var(--ss-text);
}
.title-icon {
  color: var(--ss-primary);
  font-size: 18px;
}
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: 4px;
}
.toolbar-actions :deep(.el-button) {
  padding: 6px;
  border-radius: var(--ss-radius-sm);
}
.toolbar-actions :deep(.el-button:hover) {
  background: var(--ss-primary-light);
}
.tree-search {
  margin: 12px;
  width: calc(100% - 24px);
}
.tree-search :deep(.el-input__wrapper) {
  border-radius: var(--ss-radius-sm);
  background: #f7f8fa;
  box-shadow: 0 0 0 1px var(--ss-border) inset;
}
.tree-search :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--ss-primary) inset;
  background: #fff;
}
:deep(.el-tree) {
  padding: 0 8px 12px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  --el-tree-node-hover-bg-color: #f4f6fb;
  --el-tree-node-content-height: 36px;
}
:deep(.el-tree-node__content) {
  height: 36px;
  border-radius: var(--ss-radius-sm);
}
:deep(.el-tree-node.is-current > .el-tree-node__content) {
  background: var(--ss-primary-light);
  color: var(--ss-primary);
  font-weight: 500;
}
.tree-node {
  display: flex;
  align-items: center;
  flex: 1;
  gap: 8px;
  padding-right: 8px;
}
.tree-node.is-map {
  padding-left: 2px;
}
.tree-node.is-cut {
  opacity: 0.5;
}
:deep(.el-tree-node__content:has(.tree-node.is-selected)) {
  background: var(--ss-primary-light);
}
:deep(.el-tree-node__content:has(.tree-node.is-selected)) .node-label,
:deep(.el-tree-node__content:has(.tree-node.is-selected)) .node-icon {
  color: var(--ss-primary);
}
.node-icon {
  font-size: 16px;
  flex-shrink: 0;
}
.node-icon.folder-icon {
  color: #f59e0b;
}
.node-icon.map-icon {
  color: var(--ss-primary);
}
.node-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}
.node-meta {
  color: var(--ss-primary);
  background: var(--ss-primary-light);
  font-size: 11px;
  line-height: 1;
  padding: 3px 6px;
  border-radius: 4px;
  flex-shrink: 0;
}
.preview-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: background 0.2s;
  min-width: 0;
}
.preview-panel.drag-over {
  background: var(--ss-primary-light);
  outline: 2px dashed var(--ss-primary);
  outline-offset: -4px;
  border-radius: var(--ss-radius);
}
.preview-card {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: var(--ss-radius);
  padding: 24px;
  box-shadow: var(--ss-shadow);
  min-height: 0;
}
.preview-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 20px;
}
.preview-title {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.preview-title h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
  color: var(--ss-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.version-badge {
  flex-shrink: 0;
  font-size: 12px;
  font-weight: 500;
  color: var(--ss-primary);
  background: var(--ss-primary-light);
  padding: 3px 8px;
  border-radius: 10px;
}
.header-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}
.header-actions :deep(.el-button) {
  border-radius: var(--ss-radius-sm);
}
.meta-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}
.meta-item {
  background: #f8f9fc;
  border: 1px solid var(--ss-border);
  border-radius: var(--ss-radius-sm);
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.meta-label {
  font-size: 12px;
  color: var(--ss-text-muted);
}
.meta-value {
  font-size: 14px;
  color: var(--ss-text);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.draft-alert {
  margin-top: 16px;
  border-radius: var(--ss-radius-sm);
}
.preview-mind-map {
  flex: 1;
  border: 1px solid var(--ss-border);
  border-radius: var(--ss-radius);
  background: #fbfcfe;
  min-height: 200px;
  margin-top: 16px;
  overflow: hidden;
}
.empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: var(--ss-radius);
  box-shadow: var(--ss-shadow);
}
.empty-tip {
  color: var(--ss-text-muted);
  font-size: 13px;
  margin-top: 8px;
}
.context-menu {
  position: fixed;
  background: #fff;
  border: 1px solid var(--ss-border);
  border-radius: var(--ss-radius);
  box-shadow: var(--ss-shadow-lg);
  z-index: 2000;
  min-width: 150px;
  padding: 6px;
}
.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 14px;
  border-radius: var(--ss-radius-sm);
  color: var(--ss-text);
}
.menu-item:hover {
  background: var(--ss-primary-light);
  color: var(--ss-primary);
}
.menu-item.danger {
  color: #f56c6c;
}
.menu-item.danger:hover {
  color: #fff;
  background: #f56c6c;
}
</style>
