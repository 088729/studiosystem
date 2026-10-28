<template>
  <div v-if="canEdit" class="editor-sidebar">
    <div class="sidebar-header">
      <span class="sidebar-title">{{ title }}</span>
      <el-icon class="close-btn" @click="$emit('close')"><Close /></el-icon>
    </div>
    <div class="sidebar-body">
      <NodeStylePanel v-if="activeTab === 'node'" :mind-map="mindMap" />
      <BaseStylePanel v-else-if="activeTab === 'base'" :mind-map="mindMap" />
      <ThemePanel v-else-if="activeTab === 'theme'" :mind-map="mindMap" />
      <StructurePanel v-else-if="activeTab === 'structure'" :mind-map="mindMap" />
      <OutlinePanel v-else-if="activeTab === 'outline'" :mind-map="mindMap" />
      <NotePanel v-else-if="activeTab === 'note'" :mind-map="mindMap" />
      <IconPanel v-else-if="activeTab === 'icon'" :mind-map="mindMap" />
      <VersionsPanel
        v-else-if="activeTab === 'versions'"
        :versions="versions"
        :current-version="currentVersion"
        @preview-version="$emit('preview-version', $event)"
        @rollback="$emit('rollback', $event)"
      />
      <SettingsPanel v-else-if="activeTab === 'settings'" :mind-map="mindMap" />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Close } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import OutlinePanel from './panels/OutlinePanel.vue'
import NodeStylePanel from './panels/NodeStylePanel.vue'
import BaseStylePanel from './panels/BaseStylePanel.vue'
import ThemePanel from './panels/ThemePanel.vue'
import StructurePanel from './panels/StructurePanel.vue'
import NotePanel from './panels/NotePanel.vue'
import IconPanel from './panels/IconPanel.vue'
import SettingsPanel from './panels/SettingsPanel.vue'
import VersionsPanel from './VersionsPanel.vue'

const props = defineProps({
  mindMap: Object,
  activeTab: String,
  versions: Array,
  currentVersion: Number,
})

defineEmits(['close', 'preview-version', 'rollback'])

const authStore = useAuthStore()
const canEdit = computed(() => authStore.hasPerm('xmind:edit'))

const titles = {
  node: '节点样式',
  base: '基础样式',
  theme: '主题',
  structure: '结构',
  outline: '大纲',
  note: '备注',
  icon: '图标',
  versions: '版本历史',
  settings: '设置',
}

const title = computed(() => titles[props.activeTab] || '')
</script>

<style scoped>
.editor-sidebar {
  width: 320px;
  background: #fff;
  border-left: 1px solid var(--ss-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}
.sidebar-header {
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  border-bottom: 1px solid var(--ss-border);
}
.sidebar-title {
  font-weight: 600;
  font-size: 15px;
  color: var(--ss-text);
}
.close-btn {
  cursor: pointer;
  color: var(--ss-text-muted);
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.close-btn:hover {
  color: var(--ss-primary);
  background: var(--ss-primary-light);
}
.sidebar-body {
  flex: 1;
  overflow: auto;
  padding: 12px;
}
</style>
