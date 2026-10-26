<template>
  <el-dialog
    v-model="visible"
    title="移动到"
    width="340px"
    append-to-body
    @closed="onClosed"
  >
    <!-- 搜索清单名（对齐主流待办应用：输入清单名快速搜索清单），回车选第一项 -->
    <el-input
      ref="searchInput"
      v-model="keyword"
      placeholder="搜索清单"
      clearable
      @keydown.enter.prevent="pickFirst"
    >
      <template #prefix><Search :size="14" /></template>
    </el-input>
    <div class="tm-list">
      <div
        v-if="showInbox"
        class="tm-item"
        :class="{ current: currentListId == null }"
        @click="pick(null)"
      >
        <Inbox :size="15" class="tm-icon" style="color: var(--ss-text-muted)" />收集箱
        <Check v-if="currentListId == null" :size="14" class="tm-check" />
      </div>
      <div
        v-for="l in filtered"
        :key="l.id"
        class="tm-item"
        :class="{ current: currentListId === l.id }"
        @click="pick(l.id)"
      >
        <component
          v-if="listIconOf(l.icon)"
          :is="listIconOf(l.icon)"
          :size="15"
          class="tm-icon"
          :style="{ color: l.color }"
        />
        <span v-else class="tm-dot" :style="{ background: l.color }" />
        {{ l.name }}
        <Check v-if="currentListId === l.id" :size="14" class="tm-check" />
      </div>
      <div v-if="!filtered.length && !showInbox" class="tm-empty">无匹配清单</div>
    </div>
  </el-dialog>
</template>

<script setup>
// 「移动到」弹窗（对齐主流待办应用：右键菜单「移动到」/ 详情栏底栏「清单」共用）：
// 搜索清单名快速过滤，点击或回车移动；store.moveDialogTaskId 驱动打开。
import { computed, nextTick, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Inbox, Search } from 'lucide-vue-next'
import { useTaskStore } from '@/stores/task'
import { listIconOf } from '@/utils/listIcons'

const store = useTaskStore()
const visible = ref(false)
const keyword = ref('')
const searchInput = ref(null)

const taskId = computed(() => store.moveDialogTaskId)
// 当前所属清单：优先取详情（右键任务与详情可能不是同一任务时以被右键的为准）
const currentListId = computed(() => {
  const id = taskId.value
  if (!id) return undefined
  const t = store.tasks.find((x) => x.id === id)
    || (store.activeTaskDetail?.id === id ? store.activeTaskDetail : null)
  return t?.list_id ?? null
})

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return store.lists
  return store.lists.filter((l) => l.name.toLowerCase().includes(kw))
})
// 无关键词时收集箱常驻；有关键词时「收集箱」也参与过滤
const showInbox = computed(() => {
  const kw = keyword.value.trim()
  return !kw || '收集箱'.includes(kw)
})

watch(taskId, async (id) => {
  if (!id) return
  keyword.value = ''
  visible.value = true
  nextTick(() => searchInput.value?.focus())
})

function onClosed() {
  store.moveDialogTaskId = null
}

async function pick(listId) {
  const id = taskId.value
  if (!id) return
  visible.value = false
  if (listId === currentListId.value) return
  await store.move(id, listId)
  ElMessage.success('已移动')
}

function pickFirst() {
  const first = showInbox.value ? null : filtered.value[0]?.id
  if (first === undefined) return
  pick(first)
}
</script>

<style scoped>
.tm-list {
  margin-top: 8px;
  max-height: 300px;
  overflow-y: auto;
}
.tm-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  font-size: 13px;
  color: var(--ss-text);
  border-radius: 6px;
  cursor: pointer;
  white-space: nowrap;
  overflow: hidden;
}
.tm-item:hover {
  background: var(--ss-bg);
}
.tm-item.current {
  color: var(--ss-primary);
}
.tm-icon,
.tm-dot {
  flex-shrink: 0;
}
.tm-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}
.tm-check {
  margin-left: auto;
  color: var(--ss-primary);
}
.tm-empty {
  padding: 16px;
  text-align: center;
  font-size: 12px;
  color: var(--ss-text-muted);
}
</style>
