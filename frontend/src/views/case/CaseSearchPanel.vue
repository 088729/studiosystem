<template>
  <div class="search-panel" @click.stop @contextmenu.stop.prevent>
    <div class="sp-row">
      <el-input
        ref="keywordInput"
        v-model="keyword"
        size="small"
        placeholder="查找节点文本"
        clearable
        @input="onKeywordInput"
        @keydown.enter.stop.prevent="goNext"
        @keydown.esc.stop.prevent="close"
      />
      <span class="sp-count">{{ countText }}</span>
    </div>
    <div class="sp-row sp-actions">
      <el-button size="small" title="上一个" :disabled="!info.total" @click="goPrev">
        <el-icon><ArrowUp /></el-icon>
      </el-button>
      <el-button size="small" title="下一个" :disabled="!info.total" @click="goNext">
        <el-icon><ArrowDown /></el-icon>
      </el-button>
      <el-input v-model="replaceText" size="small" class="sp-replace" placeholder="替换为" @keydown.enter.stop.prevent="replaceOne" />
    </div>
    <div class="sp-row sp-footer">
      <el-button size="small" text :disabled="!info.total" @click="replaceOne">替换</el-button>
      <el-button size="small" text type="primary" :disabled="!info.total" @click="replaceAll">全部替换</el-button>
      <el-button size="small" text @click="close">关闭</el-button>
    </div>
  </div>
</template>

<script setup>
// 查找替换面板：包装 simple-mind-map Search 插件
// search(文本) 同关键词连调=定位下一个；事件 search_info_change 返回 {currentIndex,total}
import { computed, nextTick, ref, watch } from 'vue'
import { ArrowDown, ArrowUp } from '@element-plus/icons-vue'

const props = defineProps({
  mindMap: Object,
})
const emit = defineEmits(['close'])

const keyword = ref('')
const replaceText = ref('')
const info = ref({ currentIndex: 0, total: 0 })
const keywordInput = ref(null)

const countText = computed(() =>
  info.value.total > 0 ? `${info.value.currentIndex + 1} / ${info.value.total}` : '0 项'
)

watch(
  () => props.mindMap,
  (mm, old) => {
    if (old) old.off('search_info_change', onInfoChange)
    if (!mm) return
    mm.on('search_info_change', onInfoChange)
    nextTick(() => keywordInput.value?.focus())
  },
  { immediate: true }
)

function onInfoChange(data) {
  info.value = data || { currentIndex: 0, total: 0 }
}

function onKeywordInput() {
  // 清空关键词 = 结束搜索；输入新词即开始搜索
  if (!keyword.value.trim()) {
    props.mindMap?.search.endSearch()
    info.value = { currentIndex: 0, total: 0 }
    return
  }
  props.mindMap?.search.search(keyword.value)
}

function goNext() {
  if (!keyword.value.trim()) return
  props.mindMap?.search.search(keyword.value)
}

function goPrev() {
  // 插件无独立 goPrev：用 searchNext 指定索引向前跳
  const mm = props.mindMap
  if (!mm || !info.value.total) return
  const idx = (info.value.currentIndex - 1 + info.value.total) % info.value.total
  mm.search.searchNext(() => {}, idx)
}

function replaceOne() {
  props.mindMap?.search.replace(replaceText.value, true)
}

function replaceAll() {
  props.mindMap?.search.replaceAll(replaceText.value)
}

function close() {
  props.mindMap?.search.endSearch()
  emit('close')
}

defineExpose({ focus: () => keywordInput.value?.focus() })
</script>

<style scoped>
.search-panel {
  position: absolute;
  top: 10px;
  right: 16px;
  z-index: 30;
  width: 320px;
  background: #fff;
  border: 1px solid var(--ss-border, #e6e9f0);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(16, 24, 40, 0.14);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.sp-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.sp-count {
  font-size: 12px;
  color: var(--ss-text-muted, #9ca3af);
  white-space: nowrap;
}
.sp-replace {
  flex: 1;
}
.sp-footer {
  justify-content: flex-end;
}
</style>
