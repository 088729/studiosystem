<template>
  <!-- 全局搜索（16）：侧栏搜索入口 / Ctrl+K 唤出（对齐主流待办应用）：大输入框 + 任务/标签/清单胶囊 + 最近搜索记录 -->
  <el-dialog
    v-model="store.searchVisible"
    width="640px"
    :show-close="false"
    class="search-dialog"
    @opened="onOpened"
  >
    <!-- 头部：放大镜 + 输入框 + ✕（对齐主流待办应用搜索弹框） -->
    <div class="sp-head">
      <Search :size="18" class="sp-head-icon" />
      <input
        ref="inputRef"
        v-model="q"
        class="sp-input"
        placeholder="搜索"
        @input="onSearch"
        @keyup.enter="onEnter"
      />
      <button class="sp-close" @click="store.searchVisible = false"><X :size="18" /></button>
    </div>

    <!-- 类型胶囊：任务 / 标签 / 清单 -->
    <div class="sp-tabs">
      <span
        v-for="t in TABS"
        :key="t.value"
        class="sp-tab"
        :class="{ active: tab === t.value }"
        @click="tab = t.value"
      >{{ t.label }}</span>
    </div>

    <!-- 最近搜索（输入为空时显示，localStorage 记录） -->
    <div v-if="!q && history.length" class="sp-history">
      <div class="sp-history-head">
        <span>最近搜索</span>
        <span class="sp-clear" @click="clearHistory">清空</span>
      </div>
      <div class="sp-chips">
        <span v-for="h in history" :key="h" class="sp-chip" @click="applyHistory(h)">{{ h }}</span>
      </div>
    </div>

    <!-- 空态：输入关键词即可搜索 -->
    <div v-else-if="!q" class="sp-empty">
      <Telescope :size="72" :stroke-width="1" class="sp-empty-icon" />
      <div class="sp-empty-text">输入关键词即可搜索</div>
    </div>

    <!-- 任务结果 -->
    <div v-else-if="tab === 'task' && results.length" class="search-results">
      <div v-for="t in results" :key="t.id" class="search-result" @click="onPick(t)">
        <span class="result-title" :class="{ done: t.status === 'done' }">{{ t.title }}</span>
        <el-tag v-if="listName(t)" size="small" effect="plain" class="result-list">{{ listName(t) }}</el-tag>
        <span v-if="t.due_at" class="result-due">{{ dayjs(t.due_at).format('MM-DD HH:mm') }}</span>
      </div>
    </div>

    <!-- 标签结果（本地过滤） -->
    <div v-else-if="tab === 'tag' && tagResults.length" class="search-results">
      <div v-for="t in tagResults" :key="t.tag" class="search-result" @click="onPickTag(t)">
        <Tag :size="14" class="result-icon" />
        <span class="result-title">{{ t.tag }}</span>
        <span class="result-due">{{ t.count }} 个任务</span>
      </div>
    </div>

    <!-- 清单结果（本地过滤） -->
    <div v-else-if="tab === 'list' && listResults.length" class="search-results">
      <div v-for="l in listResults" :key="l.id" class="search-result" @click="onPickList(l)">
        <span class="result-dot" :style="{ background: l.color }" />
        <span class="result-title">{{ l.name }}</span>
      </div>
    </div>

    <el-empty v-else-if="q && (tab !== 'task' || searched)" description="无匹配结果" :image-size="60" />
  </el-dialog>
</template>

<script setup>
import { computed, onMounted, onBeforeUnmount, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Search, X, Tag, Telescope } from 'lucide-vue-next'
import dayjs from 'dayjs'
import * as taskApi from '@/api/task'
import { useTaskStore } from '@/stores/task'

const store = useTaskStore()
const router = useRouter()

const TABS = [
  { value: 'task', label: '任务' },
  { value: 'tag', label: '标签' },
  { value: 'list', label: '清单' },
]
const HISTORY_KEY = 'sun_search_history'

const q = ref('')
const tab = ref('task')
const results = ref([])
const searched = ref(false)
const inputRef = ref(null)
const history = ref(JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]'))
let searchTimer = null

function listName(t) {
  return store.lists.find((l) => l.id === t.list_id)?.name || ''
}

// 标签/清单结果：本地按名称过滤（后端无对应搜索接口）
const tagResults = computed(() =>
  store.tagCounts.filter((t) => t.tag.toLowerCase().includes(q.value.trim().toLowerCase())).slice(0, 20)
)
const listResults = computed(() =>
  store.lists.filter((l) => l.name.toLowerCase().includes(q.value.trim().toLowerCase())).slice(0, 20)
)

function recordHistory(kw) {
  const k = kw.trim()
  if (!k) return
  history.value = [k, ...history.value.filter((h) => h !== k)].slice(0, 8)
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history.value))
}
function clearHistory() {
  history.value = []
  localStorage.removeItem(HISTORY_KEY)
}
function applyHistory(h) {
  q.value = h
  onSearch()
}

function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(async () => {
    if (!q.value) {
      results.value = []
      searched.value = false
      return
    }
    if (tab.value === 'task') {
      const res = await taskApi.fetchTasks({ q: q.value, smart: 'all', limit: 20 })
      results.value = res.items
    }
    searched.value = true
  }, 250)
}

// 回车：记录搜索词 + 选中首个结果
function onEnter() {
  recordHistory(q.value)
  if (tab.value === 'task' && results.value.length) onPick(results.value[0])
  else if (tab.value === 'tag' && tagResults.value.length) onPickTag(tagResults.value[0])
  else if (tab.value === 'list' && listResults.value.length) onPickList(listResults.value[0])
}

function onPick(t) {
  recordHistory(q.value)
  store.searchVisible = false
  router.push('/task').then(() => store.openDetail(t.id))
}
function onPickTag(t) {
  recordHistory(q.value)
  store.searchVisible = false
  router.push('/task').then(() => store.selectList(`tag:${t.tag}`))
}
function onPickList(l) {
  recordHistory(q.value)
  store.searchVisible = false
  router.push('/task').then(() => store.selectList(`list:${l.id}`))
}

function onKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    store.searchVisible = true
  }
}

function onOpened() {
  inputRef.value?.focus()
  // 标签/清单搜索依赖本地数据，兜底拉一次
  if (!store.tagCounts.length) store.fetchTagCounts()
  if (!store.lists.length) store.fetchLists()
}

watch(
  () => store.searchVisible,
  (visible) => {
    if (visible) {
      q.value = ''
      tab.value = 'task'
      results.value = []
      searched.value = false
      history.value = JSON.parse(localStorage.getItem(HISTORY_KEY) || '[]') // 每次打开重读，保持一致
    }
  }
)

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
/* 头部输入行：放大镜 + 无边框输入 + ✕（对齐主流待办应用搜索弹框） */
.sp-head {
  display: flex;
  align-items: center;
  gap: 10px;
  border-bottom: 1px solid var(--ss-border);
  padding-bottom: 10px;
}
.sp-head:focus-within {
  border-bottom-color: var(--ss-primary);
}
.sp-head-icon {
  color: var(--ss-text-muted);
  flex-shrink: 0;
}
.sp-input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 15px;
  color: var(--ss-text);
  background: transparent;
}
.sp-close {
  border: none;
  background: none;
  cursor: pointer;
  color: var(--ss-text-secondary);
  padding: 2px;
  display: inline-flex;
}
.sp-close:hover {
  color: var(--ss-text);
}
/* 类型胶囊 */
.sp-tabs {
  display: flex;
  gap: 10px;
  margin: 14px 0 4px;
}
.sp-tab {
  padding: 4px 14px;
  border-radius: 14px;
  font-size: 13px;
  color: var(--ss-text-secondary);
  background: var(--ss-bg);
  border: 1px solid var(--ss-border);
  cursor: pointer;
  user-select: none;
}
.sp-tab.active {
  color: var(--ss-primary);
  border-color: var(--ss-primary);
  background: var(--ss-primary-light);
}
/* 最近搜索 */
.sp-history {
  margin-top: 12px;
}
.sp-history-head {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--ss-text-muted);
  margin-bottom: 8px;
}
.sp-clear {
  cursor: pointer;
}
.sp-clear:hover {
  color: var(--ss-primary);
}
.sp-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.sp-chip {
  padding: 4px 12px;
  border-radius: 14px;
  font-size: 13px;
  background: var(--ss-bg);
  border: 1px solid var(--ss-border);
  color: var(--ss-text);
  cursor: pointer;
}
.sp-chip:hover {
  border-color: var(--ss-primary);
  color: var(--ss-primary);
}
/* 空态 */
.sp-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 60px 0 80px;
  color: var(--ss-text-muted);
}
.sp-empty-icon {
  color: var(--ss-border);
  margin-bottom: 16px;
}
.sp-empty-text {
  font-size: 14px;
}
/* 结果列表 */
.search-results {
  margin-top: 8px;
  max-height: 320px;
  overflow-y: auto;
}
.search-result {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: var(--ss-radius-sm);
  cursor: pointer;
}
.search-result:hover {
  background: var(--ss-primary-light);
}
.result-icon {
  color: var(--ss-text-muted);
  flex-shrink: 0;
}
.result-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.result-title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}
.result-title.done {
  text-decoration: line-through;
  color: var(--ss-text-muted);
}
.result-list {
  flex-shrink: 0;
}
.result-due {
  flex-shrink: 0;
  font-size: 12px;
  color: var(--ss-text-secondary);
}
</style>
