<template>
  <teleport to="body">
    <div v-if="visible" class="gqa-mask" @click.self="close">
      <div class="gqa-panel">
        <TaskQuickAdd ref="qa" global @created="close" />
        <div class="gqa-hint">{{ isMac ? '⌘ ⌥ A' : 'Ctrl + Alt + A' }} 唤起 · Esc 关闭</div>
      </div>
    </div>
  </teleport>
</template>

<script setup>
// 全局添加条（对齐主流待办应用桌面端「全局添加」）：Ctrl/Cmd+Alt+A 在系统任意页面唤起，
// 一键创建任务落收集箱（快捷语法/优先级/清单/标签/日历均可用）。App.vue 全局挂载。
// 注意：浏览器网页无法注册操作系统级全局热键，本组件覆盖本系统内的所有页面。
import { nextTick, onBeforeUnmount, onMounted, ref } from 'vue'
import TaskQuickAdd from './TaskQuickAdd.vue'
import { useTaskStore } from '@/stores/task'

const store = useTaskStore()
const visible = ref(false)
const qa = ref(null)
const isMac = /Mac/.test(navigator.platform)

async function open() {
  if (visible.value) return
  visible.value = true
  // 未进过任务页时数据可能未拉取：清单/标签/默认值补齐，保证下拉菜单和 applyDefaults 可用
  if (!store.lists.length) store.fetchLists()
  if (!store.tagCounts.length) store.fetchTagCounts()
  if (!store.settings) store.fetchSettings()
  nextTick(() => qa.value?.$el.querySelector('.qa-input')?.focus())
}

function close() {
  visible.value = false
}

function onKeydown(e) {
  // Ctrl/Cmd+Alt+A：唤起/关闭；Esc：关闭（输入框内的 Esc 已由 TaskQuickAdd 自行处理展开态）
  if (e.altKey && (e.ctrlKey || e.metaKey) && e.code === 'KeyA') {
    e.preventDefault()
    visible.value ? close() : open()
  } else if (e.key === 'Escape' && visible.value) {
    // capture 阶段拦截：即使焦点在输入框内也直接关闭添加条（对齐主流待办应用 Esc 收起）
    close()
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown, true))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown, true))
</script>

<style scoped>
.gqa-mask {
  position: fixed;
  inset: 0;
  background: rgb(15 23 42 / 35%);
  z-index: 3000;
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding-top: 18vh;
}
.gqa-panel {
  width: 520px;
  max-width: calc(100vw - 48px);
  background: #fff;
  border-radius: 10px;
  padding: 12px 14px 10px;
  box-shadow: 0 12px 40px rgb(0 0 0 / 18%);
}
.gqa-hint {
  margin-top: 8px;
  text-align: center;
  font-size: 12px;
  color: var(--ss-text-muted);
}
</style>
