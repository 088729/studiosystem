<template>
  <div class="case-editor">
    <CaseEditorToolbar
      :mind-map="mindMap"
      :title="title"
      :locked-by-other="lockedByOther"
      :locked-by-name="lockedByName"
      :view-mode="viewMode"
      @back="goBack"
      @save="saveVersion"
      @export="exportFile"
      @import="importFile"
      @update:view-mode="viewMode = $event"
      @search="openSearchPanel"
      @format-painter="startFormatPainter"
      @minimap="miniMapVisible = !miniMapVisible"
    />
    <div class="editor-main">
      <CaseEditorLeftSidebar v-model="activeTab" />
      <div class="editor-workspace">
        <div class="editor-body">
          <!-- 导图画布常驻保活（MindMap 实例/撤销历史不能销毁）；大纲模式下用 visibility+absolute 隐藏，
               不能用 display:none —— simple-mind-map 创建/渲染要求容器有真实宽高 -->
          <div
            ref="mindMapContainer"
            class="mind-map-container"
            :class="{ 'is-hidden': viewMode === 'outline' }"
          ></div>
          <CaseSearchPanel
            v-if="searchPanelVisible"
            :mind-map="mindMap"
            @close="searchPanelVisible = false"
          />
          <CaseEditorMiniMap
            v-if="miniMapVisible"
            :mind-map="mindMap"
            @close="miniMapVisible = false"
          />
          <CaseOutlineView
            v-if="viewMode === 'outline'"
            :mind-map="mindMap"
            :readonly="isReadonly"
            class="outline-container"
          />
        </div>
        <CaseEditorStatusBar
          :current-version="currentVersion"
          :draft-saved="draftSaved"
        />
      </div>
      <CaseEditorSidebar
        v-if="showRightPanel"
        :mind-map="mindMap"
        :active-tab="activeTab"
        :versions="versions"
        :current-version="currentVersion"
        @close="activeTab = ''"
        @preview-version="previewVersion"
        @rollback="rollback"
      />
    </div>
    <CaseEditorContextMenu ref="contextMenu" :mind-map="mindMap" />
    <CaseEditorIconToolbar ref="iconToolbar" :mind-map="mindMap" />
    <CaseEditorTagPopup ref="tagPopup" :mind-map="mindMap" />
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, computed, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import MindMap from 'simple-mind-map'
import Drag from 'simple-mind-map/src/plugins/Drag.js'
import Select from 'simple-mind-map/src/plugins/Select.js'
import KeyboardNavigation from 'simple-mind-map/src/plugins/KeyboardNavigation.js'
import MiniMap from 'simple-mind-map/src/plugins/MiniMap.js'
import Export from 'simple-mind-map/src/plugins/Export.js'
import ExportPDF from 'simple-mind-map/src/plugins/ExportPDF.js'
import ExportXMind from 'simple-mind-map/src/plugins/ExportXMind.js'
import NodeBase64ImageStorage from 'simple-mind-map/src/plugins/NodeBase64ImageStorage.js'
import RichText from 'simple-mind-map/src/plugins/RichText.js'
import AssociativeLine from 'simple-mind-map/src/plugins/AssociativeLine.js'
import OuterFrame from 'simple-mind-map/src/plugins/OuterFrame.js'
import Formula from 'simple-mind-map/src/plugins/Formula.js'
import RainbowLines from 'simple-mind-map/src/plugins/RainbowLines.js'
import Watermark from 'simple-mind-map/src/plugins/Watermark.js'
import NodeImgAdjust from 'simple-mind-map/src/plugins/NodeImgAdjust.js'
import SearchPlugin from 'simple-mind-map/src/plugins/Search.js'
import Painter from 'simple-mind-map/src/plugins/Painter.js'
import ScrollbarPlugin from 'simple-mind-map/src/plugins/Scrollbar.js'
import TouchEvent from 'simple-mind-map/src/plugins/TouchEvent.js'
import MindMapLayoutPro from 'simple-mind-map/src/plugins/MindMapLayoutPro.js'
import Themes from 'simple-mind-map-plugin-themes'

import { useAuthStore } from '@/stores/auth'
import * as caseApi from '@/api/case'
import { uploadImgMapAndClean } from '@/utils/imgClipboard'
import CaseEditorToolbar from './CaseEditorToolbar.vue'
import CaseEditorLeftSidebar from './CaseEditorLeftSidebar.vue'
import CaseEditorSidebar from './CaseEditorSidebar.vue'
import CaseEditorStatusBar from './CaseEditorStatusBar.vue'
import CaseEditorContextMenu from './CaseEditorContextMenu.vue'
import CaseEditorIconToolbar from './CaseEditorIconToolbar.vue'
import CaseEditorTagPopup from './CaseEditorTagPopup.vue'
import CaseOutlineView from './CaseOutlineView.vue'
import CaseSearchPanel from './CaseSearchPanel.vue'
import CaseEditorMiniMap from './CaseEditorMiniMap.vue'

MindMap.usePlugin(Drag)
  .usePlugin(Select)
  .usePlugin(KeyboardNavigation)
  .usePlugin(MiniMap)
  .usePlugin(Export)
  .usePlugin(ExportPDF)
  .usePlugin(ExportXMind)
  .usePlugin(NodeBase64ImageStorage)
  .usePlugin(RichText)
  .usePlugin(AssociativeLine)
  .usePlugin(OuterFrame)
  .usePlugin(Formula)
  .usePlugin(RainbowLines)
  .usePlugin(Watermark)
  .usePlugin(NodeImgAdjust)
  .usePlugin(SearchPlugin)
  .usePlugin(Painter)
  .usePlugin(ScrollbarPlugin)
  .usePlugin(TouchEvent)
  .usePlugin(MindMapLayoutPro)

Themes.init(MindMap)

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const mapId = route.params.mapId
const versionNo = route.query.version ? Number(route.query.version) : null

const mindMapContainer = ref(null)
const mindMap = ref(null)
const contextMenu = ref(null)
const iconToolbar = ref(null)
const tagPopup = ref(null)
const title = ref('')
const lockedByOther = ref(false)
const lockedByName = ref('')
const isReadonly = computed(() => !authStore.hasPerm('xmind:edit') || versionNo !== null || lockedByOther.value)
const canEdit = computed(() => !isReadonly.value)
const versions = ref([])
const currentVersion = ref(1)
const draftSaved = ref(false)
const activeTab = ref('node')
const showRightPanel = computed(() => !!activeTab.value)
const isInitializing = ref(true)

// ---------- 视图模式（导图 / 层级文本大纲）：按地图记忆到 localStorage ----------
const VIEW_MODE_KEY = 'sun_case_view_modes'
const viewModeMap = ref(JSON.parse(localStorage.getItem(VIEW_MODE_KEY) || '{}'))
const viewMode = ref(viewModeMap.value[mapId] === 'outline' ? 'outline' : 'map')
// 查找替换面板 / 小地图 显隐
const searchPanelVisible = ref(false)
const miniMapVisible = ref(false)
watch(viewMode, (mode) => {
  viewModeMap.value = { ...viewModeMap.value, [mapId]: mode }
  localStorage.setItem(VIEW_MODE_KEY, JSON.stringify(viewModeMap.value))
  // 切回导图：容器此前 display:none，重算画布尺寸
  if (mode === 'map') nextTick(() => mindMap.value?.resize?.())
})

let draftTimer = null
let lockTimer = null
let lockPollTimer = null
let draftSavedTimer = null

async function init() {
  if (canEdit.value) {
    try {
      await caseApi.lockMap(mapId)
      startLockHeartbeat()
    } catch (e) {
      if (e.response?.status === 423) {
        lockedByOther.value = true
        lockedByName.value = e.response?.data?.detail?.locked_by || '他人'
      }
    }
  }
  if (isReadonly.value) {
    startLockPoll()
  }

  let rootData
  if (versionNo) {
    const version = await caseApi.fetchVersion(mapId, versionNo)
    title.value = `版本 v${versionNo}`
    rootData = version.root
  } else {
    const detail = await caseApi.fetchMap(mapId)
    title.value = detail.title
    currentVersion.value = detail.current_version
    if (detail.temp_content && canEdit.value) {
      const keep = await ElMessageBox.confirm('检测到未保存的草稿，是否恢复？', '提示', {
        confirmButtonText: '恢复',
        cancelButtonText: '放弃',
        type: 'warning',
      }).catch(() => false)
      rootData = keep ? detail.temp_content : detail.latest_root
    } else {
      rootData = detail.latest_root
    }
  }

  if (!rootData) {
    rootData = {
      root: {
        data: { text: title.value || '未命名', uid: 'root', expand: true },
        children: [],
      },
      layout: 'logicalStructure',
      theme: { template: 'default', config: {} },
      view: null,
    }
  }

  mindMap.value = new MindMap({
    el: mindMapContainer.value,
    data: rootData.root,
    layout: rootData.layout || 'logicalStructure',
    theme: rootData.theme?.template || 'default',
    themeConfig: sanitizeThemeConfig(rootData.theme?.config),
    viewData: normalizeView(rootData.view),
    readonly: !canEdit.value,
    fit: true,
    isUseCustomScrollbar: true,  // 自定义滚动条（内容超出画布时显示，替代无限拖拽）
  })

  mindMap.value.on('svg_mousedown', () => {
    contextMenu.value?.hide()
    iconToolbar.value?.hide()
    tagPopup.value?.hide()
  })

  mindMap.value.on('painter_start', () => {
    ElMessage.info('格式刷已开启：点击要应用样式的节点')
  })
  mindMap.value.on('painter_end', () => {
    ElMessage.success('格式刷完成')
  })

  mindMap.value.on('data_change', (data) => {
    if (!isInitializing.value) {
      if (draftTimer) clearTimeout(draftTimer)
      draftTimer = setTimeout(() => {
        saveDraft(data)
      }, 2000)
    }
  })

  try {
    await loadVersions()
  } catch (e) {
    // 后端未启动时忽略
  }

  isInitializing.value = false
}

async function saveDraft(data) {
  if (!canEdit.value) return
  const fullData = buildFullData(data)
  await caseApi.saveDraft(mapId, { temp_content: fullData })
  draftSaved.value = true
  if (draftSavedTimer) clearTimeout(draftSavedTimer)
  draftSavedTimer = setTimeout(() => { draftSaved.value = false }, 2000)
}

async function saveVersion() {
  if (!canEdit.value) return
  await uploadImgMapAndClean(mindMap.value, mapId)
  const cleaned = mindMap.value.getData(true)
  const fullData = buildFullData(cleaned.root ? cleaned.root : cleaned)
  await caseApi.createSnapshot(mapId, {
    root: fullData,
    changelog: '手动保存',
    overwrite: false,
  })
  ElMessage.success('保存成功')
  loadVersions()
}

function buildFullData(rootData) {
  return {
    root: rootData,
    layout: mindMap.value.getLayout(),
    theme: {
      template: mindMap.value.getTheme(),
      // 只保存用户自定义的主题覆盖项，而不是 getThemeConfig() 的全量合并结果，
      // 否则保存后旧主题的完整快照会覆盖新主题，导致切换主题无效
      config: mindMap.value.getCustomThemeConfig(),
    },
    view: mindMap.value.view.getTransformData(),
  }
}

// 历史版本/草稿的 theme.config 可能是全量主题快照（包含 root/second/node 等完整结构），
// 加载时需要剔除，否则会覆盖所选主题导致切换主题无效
function sanitizeThemeConfig(config) {
  if (!config || typeof config !== 'object') return {}
  if (config.root || config.second || config.node) return {}
  return config
}

// 打开查找替换面板（Ctrl+F / 工具栏按钮）
function openSearchPanel() {
  searchPanelVisible.value = true
}

// 格式刷：把当前选中节点的样式刷到下一个点击的节点（点击空白处结束）
function startFormatPainter() {
  const mm = mindMap.value
  if (!mm) return
  if (!(mm.renderer?.activeNodeList || []).length) {
    ElMessage.warning('请先选择节点')
    return
  }
  mm.painter.startPainter()
}

function normalizeView(view) {
  if (!view) return null
  if (view.state && view.transform) return view
  // 兼容旧版/错误格式：{ transform: { transform, state } }
  if (view.transform?.state && view.transform?.transform) {
    return view.transform
  }
  return null
}

async function loadVersions() {
  const res = await caseApi.fetchVersions(mapId, { offset: 0, limit: 20 })
  versions.value = res.items
}

function previewVersion(vn) {
  router.push(`/case/editor/${mapId}?version=${vn}`)
}

async function rollback(vn) {
  if (!canEdit.value) return
  await caseApi.rollbackVersion(mapId, { version_no: vn })
  ElMessage.success('回滚成功')
  router.push(`/case/editor/${mapId}`)
}

function exportFile(type) {
  if (!mindMap.value) return
  const name = title.value || '导图'
  switch (type) {
    case 'png':
      // 参数：不透明、无自定义样式、背景铺满
      mindMap.value.export('png', true, name, false, null, true)
      break
    case 'pdf':
      mindMap.value.export('pdf', true, name, false, true)
      break
    case 'json':
      // 导出包含布局/主题/视图配置，可用于再次导入
      mindMap.value.export('json', true, name, true)
      break
    default:
      // svg / md / txt / xmind
      mindMap.value.export(type, true, name)
  }
}

const importAcceptMap = {
  xmind: '.xmind',
  md: '.md,.markdown',
  json: '.json,.smm',
}

async function importFile(type) {
  if (!mindMap.value || !canEdit.value) return
  try {
    await ElMessageBox.confirm('导入将覆盖当前画布内容，是否继续？', '导入', {
      confirmButtonText: '选择文件',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = importAcceptMap[type]
  input.onchange = async () => {
    const file = input.files[0]
    if (!file) return
    try {
      if (type === 'json') {
        const text = await file.text()
        const data = JSON.parse(text)
        if (typeof data !== 'object' || !data) throw new Error('invalid json')
        // 含配置（root/theme/layout/view）的用 setFullData，否则只设置节点数据
        if (data.root) {
          data.theme = data.theme || {}
          data.theme.config = sanitizeThemeConfig(data.theme.config)
          mindMap.value.setFullData(data)
        } else {
          mindMap.value.setData(data)
        }
      } else if (type === 'xmind') {
        const { default: xmind } = await import('simple-mind-map/src/parse/xmind.js')
        // 多画布时默认取第一个
        const data = await xmind.parseXmindFile(file, (content) => Promise.resolve(content[0]))
        mindMap.value.setData(data)
      } else if (type === 'md') {
        const { default: markdown } = await import('simple-mind-map/src/parse/markdown.js')
        const text = await file.text()
        const data = markdown.transformMarkdownTo(text)
        mindMap.value.setData(data)
      }
      ElMessage.success('导入成功')
    } catch (e) {
      console.error('import error', e)
      ElMessage.error('文件解析失败，请检查文件格式')
    }
  }
  input.click()
}

function startLockHeartbeat() {
  lockTimer = setInterval(async () => {
    try {
      await caseApi.lockMap(mapId)
    } catch (e) {
      // ignore
    }
  }, 30000)
}

function startLockPoll() {
  lockPollTimer = setInterval(async () => {
    try {
      const detail = await caseApi.fetchMap(mapId)
      if (detail.locked_by && detail.locked_by !== authStore.userInfo?.username) {
        lockedByOther.value = true
        lockedByName.value = detail.locked_by
      } else {
        lockedByOther.value = false
        lockedByName.value = ''
      }
    } catch (e) {
      // ignore
    }
  }, 15000)
}

function releaseLockSync() {
  if (versionNo) return
  if (!authStore.hasPerm('xmind:edit')) return
  // 尽力发送释放锁请求；beforeunload 中无法使用异步 axios
  const token = localStorage.getItem('sun_access_token') || sessionStorage.getItem('sun_access_token')
  try {
    const xhr = new XMLHttpRequest()
    xhr.open('DELETE', `/api/v1/case/maps/${mapId}/lock`, false)
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    }
    xhr.send()
  } catch (e) {
    // ignore
  }
}

function goBack() {
  router.push('/case')
}

function onGlobalKeydown(e) {
  // Ctrl/Cmd + F：打开查找替换面板（仅导图视图；大纲/详情有各自焦点处理）
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'f' && viewMode.value === 'map') {
    e.preventDefault()
    openSearchPanel()
  }
}

onMounted(() => {
  window.addEventListener('beforeunload', releaseLockSync)
  window.addEventListener('keydown', onGlobalKeydown)
  init()
})

onBeforeUnmount(async () => {
  window.removeEventListener('beforeunload', releaseLockSync)
  window.removeEventListener('keydown', onGlobalKeydown)
  if (draftTimer) clearTimeout(draftTimer)
  if (lockTimer) clearInterval(lockTimer)
  if (lockPollTimer) clearInterval(lockPollTimer)
  if (draftSavedTimer) clearTimeout(draftSavedTimer)
  if (mindMap.value) {
    mindMap.value.destroy()
  }
  if (canEdit.value && !versionNo) {
    try {
      await caseApi.unlockMap(mapId)
    } catch (e) {
      // ignore
    }
  }
})
</script>

<style scoped>
.case-editor {
  display: flex;
  flex-direction: column;
  height: 100vh;
}
.editor-main {
  flex: 1;
  display: flex;
  overflow: hidden;
}
.editor-workspace {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.editor-body {
  flex: 1;
  overflow: hidden;
  background: #fbfcfe;
  position: relative;
}
.mind-map-container {
  width: 100%;
  height: 100%;
}
/* 大纲模式下隐藏画布：保持真实宽高（visibility），脱离文档流（absolute）不挤压大纲 */
.mind-map-container.is-hidden {
  visibility: hidden;
  position: absolute;
  left: 0;
  top: 0;
  pointer-events: none;
}
.outline-container {
  width: 100%;
  height: 100%;
}
</style>
