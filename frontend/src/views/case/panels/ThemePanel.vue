<template>
  <div class="theme-panel">
    <el-tabs v-model="activeGroup" class="theme-tabs">
      <el-tab-pane
        v-for="group in groupList"
        :key="group.name"
        :label="group.name"
        :name="group.name"
      />
    </el-tabs>
    <div class="theme-list">
      <div
        v-for="item in currentList"
        :key="item.value"
        class="theme-item"
        :class="{ active: currentTheme === item.value }"
        @click="useTheme(item)"
      >
        <div class="img-box">
          <img :src="themeImgMap[item.value]" :alt="item.name" />
        </div>
        <div class="name">{{ item.name }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { ElMessageBox } from 'element-plus'
import Themes from 'simple-mind-map-plugin-themes'
import themeList from 'simple-mind-map-plugin-themes/themeList'
import themeImgMap from 'simple-mind-map-plugin-themes/themeImgMap'

const props = defineProps({
  mindMap: Object,
})

const currentTheme = ref('default')
const activeGroup = ref('经典')

// 分组逻辑参考官方 demo
const groupList = computed(() => {
  const all = [{ name: '默认主题', value: 'default', dark: false }, ...themeList]
  const baiduThemes = [
    'default', 'skyGreen', 'classic2', 'classic3', 'classicGreen',
    'classicBlue', 'blueSky', 'brainImpairedPink', 'earthYellow',
    'freshGreen', 'freshRed', 'romanticPurple', 'pinkGrape', 'mint',
  ]
  return [
    { name: '经典', list: all.filter(item => !item.dark && !baiduThemes.includes(item.value)) },
    { name: '暗黑', list: all.filter(item => item.dark) },
    { name: '简约', list: all.filter(item => baiduThemes.includes(item.value)) },
  ]
})

const currentList = computed(() => {
  return groupList.value.find(g => g.name === activeGroup.value)?.list || []
})

watch(() => props.mindMap, (mm) => {
  if (!mm) return
  currentTheme.value = mm.getTheme()
  mm.on('view_theme_change', handleViewThemeChange)
}, { immediate: true })

onBeforeUnmount(() => {
  props.mindMap?.off('view_theme_change', handleViewThemeChange)
})

function handleViewThemeChange(theme) {
  currentTheme.value = theme
}

function useTheme(theme) {
  if (!props.mindMap || theme.value === currentTheme.value) return
  const customThemeConfig = props.mindMap.getCustomThemeConfig()
  const hasCustomThemeConfig = Object.keys(customThemeConfig).length > 0
  if (hasCustomThemeConfig) {
    // 存在自定义主题配置时，询问是否覆盖（参考官方 demo）
    ElMessageBox.confirm('你当前自定义过主题样式，切换主题会覆盖这些样式，是否覆盖？', '提示', {
      confirmButtonText: '覆盖',
      cancelButtonText: '保留',
      type: 'warning',
      distinguishCancelAndClose: true,
      callback: (action) => {
        if (action === 'confirm') {
          props.mindMap.setThemeConfig({}, true)
        }
        if (action === 'confirm' || action === 'cancel') {
          props.mindMap.setTheme(theme.value)
        }
      },
    })
  } else {
    props.mindMap.setTheme(theme.value)
  }
}
</script>

<style scoped>
.theme-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
.theme-tabs {
  flex-shrink: 0;
  padding: 0 8px;
}
.theme-tabs :deep(.el-tabs__nav-wrap) {
  display: flex;
  justify-content: center;
}
.theme-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px 8px;
}
.theme-item {
  width: 100%;
  cursor: pointer;
  margin-bottom: 16px;
  border: 3px solid transparent;
  border-radius: var(--ss-radius);
  overflow: hidden;
  transition: box-shadow 0.2s;
}
.theme-item:hover {
  box-shadow: var(--ss-shadow-lg);
}
.theme-item.active {
  border-color: var(--ss-primary);
}
.img-box {
  width: 100%;
  border-radius: 4px;
  overflow: hidden;
  background: #f4f6fb;
}
.img-box img {
  width: 100%;
  display: block;
}
.name {
  text-align: center;
  font-size: 13px;
  color: var(--ss-text);
  padding: 6px 0 2px;
}
</style>
