<template>
  <el-drawer
    :model-value="visible"
    title="版本历史"
    size="560px"
    @update:model-value="$emit('update:visible', $event)"
    @open="loadHistory"
  >
    <div v-if="!history.length" class="hd-empty">
      <el-empty description="暂无提交历史" :image-size="80" />
    </div>
    <template v-else>
      <div class="hd-list">
        <div
          v-for="(h, idx) in history"
          :key="h.commit"
          class="hd-item"
          :class="{ active: currentCommit === h.commit }"
          @click="selectVersion(h, idx)"
        >
          <div class="hd-msg">{{ h.message || '（无描述）' }}</div>
          <div class="hd-meta">
            <span>{{ h.author }}</span>
            <span>{{ formatDate(h.date) }}</span>
            <span class="hd-sha">{{ h.commit.slice(0, 7) }}</span>
          </div>
          <el-button
            v-if="idx !== 0 && canEdit"
            size="small"
            text
            type="primary"
            class="hd-revert"
            @click.stop="confirmRevert(h)"
          >回滚到此版本</el-button>
        </div>
      </div>
      <div v-if="diff" class="hd-diff">
        <div class="hd-diff-title">{{ diffTitle }}</div>
        <pre class="hd-diff-body"><template v-for="(line, i) in diffLines" :key="i"><span :class="diffClass(line)">{{ line }}<br /></span></template></pre>
      </div>
    </template>
  </el-drawer>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import * as wikiApi from '@/api/wiki'

const props = defineProps({
  visible: Boolean,
  vaultId: String,
  path: String,
  canEdit: Boolean,
})
const emit = defineEmits(['update:visible', 'reverted'])

const history = ref([])
const diff = ref('')
const diffTitle = ref('')
const currentCommit = ref('')

async function loadHistory() {
  history.value = []
  diff.value = ''
  if (!props.vaultId || !props.path) return
  history.value = await wikiApi.fetchHistory(props.vaultId, props.path)
}

async function selectVersion(h, idx) {
  currentCommit.value = h.commit
  const res = await wikiApi.fetchDiff(props.vaultId, props.path, h.commit, null)
  diff.value = res.diff
  diffTitle.value = `版本 ${h.commit.slice(0, 7)} 与上一版本的对比${res.truncated ? '（已截断）' : ''}`
}

const diffLines = computed(() => diff.value.split('\n'))

function diffClass(line) {
  if (line.startsWith('+')) return 'dl-add'
  if (line.startsWith('-')) return 'dl-del'
  if (line.startsWith('@@')) return 'dl-hunk'
  return ''
}

async function confirmRevert(h) {
  try {
    await ElMessageBox.confirm(
      `回滚「${props.path}」到 ${h.commit.slice(0, 7)}？将产生一个新提交，不改写历史。`,
      '回滚确认',
      { type: 'warning' }
    )
  } catch {
    return
  }
  await wikiApi.revertPage(props.vaultId, props.path, h.commit)
  ElMessage.success('已回滚')
  emit('reverted')
  await loadHistory()
}

function formatDate(d) {
  return d ? dayjs(d).format('YYYY-MM-DD HH:mm') : '-'
}
</script>

<style scoped>
.hd-empty {
  padding-top: 60px;
}
.hd-list {
  max-height: 40vh;
  overflow-y: auto;
  border: 1px solid var(--ss-border);
  border-radius: var(--ss-radius-sm);
  margin-bottom: 12px;
}
.hd-item {
  position: relative;
  padding: 10px 14px;
  cursor: pointer;
  border-bottom: 1px solid var(--ss-border);
}
.hd-item:last-child {
  border-bottom: none;
}
.hd-item:hover {
  background: var(--ss-bg);
}
.hd-item.active {
  background: var(--ss-primary-light);
}
.hd-msg {
  font-size: 13px;
  font-weight: 500;
  color: var(--ss-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.hd-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: var(--ss-text-muted);
  margin-top: 3px;
}
.hd-revert {
  position: absolute;
  right: 8px;
  top: 12px;
}
.hd-diff-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--ss-text);
  margin-bottom: 6px;
}
.hd-diff-body {
  background: #f8f9fb;
  border: 1px solid var(--ss-border);
  border-radius: var(--ss-radius-sm);
  padding: 10px;
  font-size: 12px;
  line-height: 1.6;
  overflow-x: auto;
  max-height: 45vh;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-all;
}
.dl-add {
  color: #2e7d32;
  background: #e8f5e9;
}
.dl-del {
  color: #c62828;
  background: #ffebee;
}
.dl-hunk {
  color: var(--ss-text-muted);
}
</style>
