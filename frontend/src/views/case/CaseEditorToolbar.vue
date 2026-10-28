<template>
  <div class="editor-toolbar">
    <div class="toolbar-left">
      <el-button link @click="emit('back')">
        <el-icon><ArrowLeft /></el-icon>
      </el-button>
      <span class="title">{{ title }}</span>
    </div>

    <div class="toolbar-center">
      <el-tooltip content="撤销" placement="bottom">
        <el-button link :disabled="!canEdit" @click="exec('BACK')">
          <el-icon><Back /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="重做" placement="bottom">
        <el-button link :disabled="!canEdit" @click="exec('FORWARD')">
          <el-icon><Right /></el-icon>
        </el-button>
      </el-tooltip>
      <el-divider direction="vertical" />
      <el-tooltip content="插入同级节点" placement="bottom">
        <el-button link :disabled="!canEdit" @click="exec('INSERT_NODE')">
          <el-icon><Plus /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="插入子节点" placement="bottom">
        <el-button link :disabled="!canEdit" @click="exec('INSERT_CHILD_NODE')">
          <el-icon><BottomRight /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="删除节点" placement="bottom">
        <el-button link :disabled="!canEdit" @click="exec('REMOVE_NODE')">
          <el-icon><Delete /></el-icon>
        </el-button>
      </el-tooltip>
      <el-divider direction="vertical" />
      <el-tooltip content="图片" placement="bottom">
        <el-button link :disabled="!canEdit" @click="setImage">
          <el-icon><Picture /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="图标" placement="bottom">
        <el-button link :disabled="!canEdit" @click="setIcon">
          <el-icon><Star /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="超链接" placement="bottom">
        <el-button link :disabled="!canEdit" @click="setHyperlink">
          <el-icon><Link /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="备注" placement="bottom">
        <el-button link :disabled="!canEdit" @click="setNote">
          <el-icon><Document /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="标签" placement="bottom">
        <el-button link :disabled="!canEdit" @click="setTag">
          <el-icon><PriceTag /></el-icon>
        </el-button>
      </el-tooltip>
      <el-divider direction="vertical" />
      <el-tooltip content="概要" placement="bottom">
        <el-button link :disabled="!canEdit" @click="exec('ADD_GENERALIZATION')">
          <el-icon><Memo /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="关联线" placement="bottom">
        <el-button link :disabled="!canEdit" @click="exec('ADD_ASSOCIATIVE_LINE')">
          <el-icon><Share /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="外框" placement="bottom">
        <el-button link :disabled="!canEdit" @click="exec('ADD_OUTER_FRAME')">
          <el-icon><FullScreen /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="公式" placement="bottom">
        <el-button link :disabled="!canEdit" @click="exec('INSERT_FORMULA')">
          <el-icon><Collection /></el-icon>
        </el-button>
      </el-tooltip>
      <el-divider direction="vertical" />
      <el-tooltip content="查找替换（Ctrl+F）" placement="bottom">
        <el-button link @click="emit('search')">
          <el-icon><Search /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="格式刷（把选中节点样式刷到下一个点击的节点）" placement="bottom">
        <el-button link :disabled="!canEdit" @click="startFormatPainter">
          <el-icon><Brush /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="小地图" placement="bottom">
        <el-button link @click="emit('minimap')">
          <el-icon><MapLocation /></el-icon>
        </el-button>
      </el-tooltip>
    </div>

    <div class="toolbar-right">
      <!-- 视图切换：导图画布 / 层级文本大纲（按地图记忆） -->
      <el-radio-group
        class="view-toggle"
        :model-value="viewMode"
        size="small"
        @update:model-value="(v) => emit('update:viewMode', v)"
      >
        <el-radio-button value="map">
          <el-icon><Share /></el-icon>导图
        </el-radio-button>
        <el-radio-button value="outline">
          <el-icon><List /></el-icon>大纲
        </el-radio-button>
      </el-radio-group>
      <span v-if="lockedByOther" class="status-badge locked"><i class="status-dot"></i>被 {{ lockedByName }} 锁定</span>
      <span v-else-if="canEdit" class="status-badge editing"><i class="status-dot"></i>编辑中</span>
      <el-button v-auth="'xmind:edit'" type="primary" :disabled="!canEdit" @click="emit('save')">保存版本</el-button>
      <el-dropdown v-auth="'xmind:edit'" :disabled="!canEdit" @command="(type) => emit('import', type)">
        <el-button :disabled="!canEdit">
          导入<el-icon class="el-icon--right"><ArrowDown /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="xmind">XMind（.xmind）</el-dropdown-item>
            <el-dropdown-item command="md">Markdown（.md）</el-dropdown-item>
            <el-dropdown-item command="json">JSON（.json）</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <el-dropdown v-auth="'xmind:edit'" :disabled="!canEdit" @command="(type) => emit('export', type)">
        <el-button :disabled="!canEdit">
          导出<el-icon class="el-icon--right"><ArrowDown /></el-icon>
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="png">PNG 图片（.png）</el-dropdown-item>
            <el-dropdown-item command="svg">SVG 矢量图（.svg）</el-dropdown-item>
            <el-dropdown-item command="pdf">PDF（.pdf）</el-dropdown-item>
            <el-dropdown-item command="md">Markdown（.md）</el-dropdown-item>
            <el-dropdown-item command="xmind">XMind（.xmind）</el-dropdown-item>
            <el-dropdown-item command="txt">纯文本（.txt）</el-dropdown-item>
            <el-dropdown-item command="json">JSON（.json）</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowLeft,
  ArrowDown,
  Back,
  Right,
  Plus,
  BottomRight,
  Delete,
  Picture,
  Star,
  Link,
  Document,
  PriceTag,
  Memo,
  Share,
  FullScreen,
  Collection,
  List,
  Search,
  Brush,
  MapLocation,
} from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'

const props = defineProps({
  mindMap: Object,
  title: String,
  lockedByOther: Boolean,
  lockedByName: String,
  viewMode: { type: String, default: 'map' },
})
const emit = defineEmits(['back', 'save', 'export', 'import', 'update:viewMode', 'search', 'format-painter', 'minimap'])

const authStore = useAuthStore()
const canEdit = computed(() => !props.lockedByOther && authStore.hasPerm('xmind:edit'))

function exec(command) {
  if (!props.mindMap) return
  props.mindMap.execCommand(command)
}

function activeNodes() {
  return props.mindMap?.renderer?.activeNodeList || []
}

// 格式刷：需先选中样式源节点
function startFormatPainter() {
  if (!activeNodes().length) {
    ElMessage.warning('请先选择节点')
    return
  }
  emit('format-painter')
}

function setImage() {
  const nodes = activeNodes()
  if (nodes.length === 0) {
    ElMessage.warning('请先选择节点')
    return
  }
  ElMessageBox.prompt('请输入图片 URL', '设置图片', { inputValue: '' }).then(({ value }) => {
    nodes.forEach((node) => node.setData('image', value))
    props.mindMap.render()
  }).catch(() => {})
}

function setIcon() {
  const nodes = activeNodes()
  if (nodes.length === 0) {
    ElMessage.warning('请先选择节点')
    return
  }
  ElMessageBox.prompt('请输入图标 key', '设置图标', { inputValue: 'priority_1' }).then(({ value }) => {
    nodes.forEach((node) => node.setData('icon', [value]))
    props.mindMap.render()
  }).catch(() => {})
}

function setHyperlink() {
  const nodes = activeNodes()
  if (nodes.length === 0) {
    ElMessage.warning('请先选择节点')
    return
  }
  ElMessageBox.prompt('请输入超链接 URL', '设置超链接', { inputValue: '' }).then(({ value }) => {
    nodes.forEach((node) => node.setData('hyperlink', value))
    props.mindMap.render()
  }).catch(() => {})
}

function setNote() {
  const nodes = activeNodes()
  if (nodes.length === 0) {
    ElMessage.warning('请先选择节点')
    return
  }
  const current = nodes[0].getData('note') || ''
  ElMessageBox.prompt('请输入备注', '设置备注', { inputValue: current, type: 'textarea' }).then(({ value }) => {
    nodes.forEach((node) => node.setData('note', value))
    props.mindMap.render()
  }).catch(() => {})
}

function setTag() {
  const nodes = activeNodes()
  if (nodes.length === 0) {
    ElMessage.warning('请先选择节点')
    return
  }
  ElMessageBox.prompt('请输入标签，多个用逗号分隔', '设置标签', { inputValue: '' }).then(({ value }) => {
    const tags = value.split(',').map((t) => t.trim()).filter(Boolean)
    nodes.forEach((node) => node.setData('tag', tags))
    props.mindMap.render()
  }).catch(() => {})
}
</script>

<style scoped>
.editor-toolbar {
  height: 52px;
  border-bottom: 1px solid var(--ss-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: #fff;
  box-shadow: 0 1px 4px rgba(16, 24, 40, 0.05);
  position: relative;
  z-index: 10;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  min-width: 0;
}
.toolbar-left :deep(.el-button) {
  width: 32px;
  height: 32px;
  border-radius: var(--ss-radius-sm);
  color: var(--ss-text-secondary);
}
.toolbar-left :deep(.el-button:hover) {
  background: #f4f6fb;
  color: var(--ss-primary);
}
.title {
  font-weight: 600;
  font-size: 15px;
  color: var(--ss-text);
  max-width: 320px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.toolbar-center {
  display: flex;
  align-items: center;
  gap: 2px;
  flex: 1;
  justify-content: center;
  overflow: hidden;
}
.toolbar-center :deep(.el-button) {
  width: 32px;
  height: 32px;
  margin-left: 0;
  border-radius: var(--ss-radius-sm);
  color: var(--ss-text-secondary);
  font-size: 16px;
}
.toolbar-center :deep(.el-button:hover:not(.is-disabled)) {
  background: var(--ss-primary-light);
  color: var(--ss-primary);
}
.toolbar-center :deep(.el-divider--vertical) {
  height: 18px;
  margin: 0 8px;
  border-left-color: var(--ss-border);
}
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
/* 导图/大纲切换器 */
.view-toggle :deep(.el-radio-button__inner) {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 12px;
}
.toolbar-right :deep(.el-button) {
  border-radius: var(--ss-radius-sm);
  margin-left: 0;
}
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  padding: 4px 10px;
  border-radius: 12px;
  white-space: nowrap;
}
.status-badge .status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.status-badge.editing {
  color: #16a34a;
  background: #f0fdf4;
}
.status-badge.editing .status-dot {
  background: #22c55e;
}
.status-badge.locked {
  color: #dc2626;
  background: #fef2f2;
}
.status-badge.locked .status-dot {
  background: #ef4444;
}
</style>
