<template>
  <div class="left-sidebar">
    <div
      v-for="item in tabs"
      :key="item.name"
      :class="['sidebar-item', { active: modelValue === item.name }]"
      :title="item.label"
      @click="$emit('update:modelValue', item.name)"
    >
      <el-icon :size="20">
        <component :is="item.icon" />
      </el-icon>
      <span class="item-label">{{ item.label }}</span>
    </div>
  </div>
</template>

<script setup>
import {
  Brush,
  SetUp,
  MagicStick,
  Share,
  List,
  Notebook,
  Picture,
  Clock,
  Setting,
} from '@element-plus/icons-vue'

defineProps({
  modelValue: String,
})

defineEmits(['update:modelValue'])

const tabs = [
  { name: 'node', label: '节点样式', icon: Brush },
  { name: 'base', label: '基础样式', icon: SetUp },
  { name: 'theme', label: '主题', icon: MagicStick },
  { name: 'structure', label: '结构', icon: Share },
  { name: 'outline', label: '大纲', icon: List },
  { name: 'note', label: '备注', icon: Notebook },
  { name: 'icon', label: '图标', icon: Picture },
  { name: 'versions', label: '版本', icon: Clock },
  { name: 'settings', label: '设置', icon: Setting },
]
</script>

<style scoped>
.left-sidebar {
  width: 64px;
  background: #fff;
  border-right: 1px solid var(--ss-border);
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 0;
  flex-shrink: 0;
}
.sidebar-item {
  width: 52px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 8px 0 7px;
  margin-bottom: 6px;
  border-radius: var(--ss-radius);
  cursor: pointer;
  color: var(--ss-text-secondary);
  transition: all 0.2s;
}
.sidebar-item:hover {
  background: #f4f6fb;
  color: var(--ss-primary);
}
.sidebar-item.active {
  background: var(--ss-primary-light);
  color: var(--ss-primary);
  font-weight: 500;
  box-shadow: inset 0 0 0 1px rgba(79, 110, 247, 0.15);
}
.item-label {
  font-size: 11px;
  margin-top: 4px;
  transform: scale(0.9);
  white-space: nowrap;
}
</style>
