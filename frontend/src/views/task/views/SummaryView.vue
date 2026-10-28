<template>
  <div class="summary-view">
    <!-- 左：生成结果（对齐主流待办应用摘要页） -->
    <div class="sum-result-pane">
      <div v-if="loading && !result" class="sum-loading">生成中…</div>
      <template v-else-if="result">
        <h2 class="sum-range">{{ result.range_label }}</h2>
        <div v-for="g in result.groups" :key="g.label" class="sum-group">
          <h3 class="sum-group-title">{{ g.label }}</h3>
          <ul class="sum-items">
            <li v-for="(it, i) in g.items" :key="i" class="sum-item">
              <span v-if="cfg.show.includes('date') && it.date_label" class="sum-date">[{{ it.date_label }}]</span>
              <span class="sum-title">{{ it.title }}</span>
              <span v-if="cfg.show.includes('priority') && it.priority" class="sum-prio" :style="{ color: ['', '#409eff', '#e6a23c', '#f56c6c'][it.priority] }">
                {{ ['', '低', '中', '高'][it.priority] }}
              </span>
              <span v-if="cfg.show.includes('list')" class="sum-list">（{{ it.list_name }}）</span>
            </li>
          </ul>
        </div>
        <el-empty v-if="!result.total" description="该时间段内没有任务" />
      </template>
      <div class="sum-actions">
        <el-button :disabled="!result" @click="saveDialog = true">
          <Save :size="14" style="margin-right: 4px; vertical-align: -2px" />保存为
        </el-button>
        <el-button :disabled="!result" @click="copyMarkdown">
          <Copy :size="14" style="margin-right: 4px; vertical-align: -2px" />复制
        </el-button>
      </div>
    </div>

    <!-- 右：模板 + 筛选 + 显示设置（对齐主流待办应用配置面板） -->
    <div class="sum-config-pane">
      <div class="sum-sec">
        <div class="sum-sec-head">
          <span class="sum-sec-title">模板</span>
          <span class="sum-sec-add" title="将当前配置保存为模板" @click="saveTemplate">
            <Plus :size="15" />
          </span>
        </div>
        <div v-for="(t, i) in templates" :key="t.name" class="sum-template" @click="applyTemplate(t)">
          <FileText :size="13" class="sum-template-icon" />{{ t.name }}
          <span class="sum-template-del" title="删除模板" @click.stop="delTemplate(i)">×</span>
        </div>
        <div v-if="!templates.length" class="sum-empty">无模板，点 + 保存当前配置</div>
      </div>

      <div class="sum-sec">
        <div class="sum-sec-head"><span class="sum-sec-title">筛选</span></div>
        <div class="sum-row">
          <span class="sum-label">日期</span>
          <el-select v-model="cfg.range" size="small" class="sum-val" @change="onConfigChange">
            <el-option v-for="o in RANGE_OPTIONS" :key="o.value" :value="o.value" :label="o.label" />
          </el-select>
        </div>
        <div v-if="cfg.range === 'custom'" class="sum-row">
          <span class="sum-label">区间</span>
          <el-date-picker
            v-model="customRange"
            type="daterange"
            size="small"
            class="sum-val"
            value-format="YYYY-MM-DD"
            range-separator="-"
            start-placeholder="开始"
            end-placeholder="结束"
            @change="onConfigChange"
          />
        </div>
        <div class="sum-row">
          <span class="sum-label">清单</span>
          <el-select v-model="cfg.list_ids" multiple collapse-tags size="small" class="sum-val" placeholder="所有清单" @change="onConfigChange">
            <el-option value="inbox" label="收集箱" />
            <el-option v-for="l in store.lists" :key="l.id" :value="l.id" :label="l.name" />
          </el-select>
        </div>
        <div class="sum-row">
          <span class="sum-label">状态</span>
          <el-checkbox-group v-model="cfg.statuses" size="small" @change="onConfigChange">
            <el-checkbox value="done">已完成</el-checkbox>
            <el-checkbox value="todo">未完成</el-checkbox>
          </el-checkbox-group>
        </div>
        <div class="sum-row">
          <span class="sum-label">标签</span>
          <el-select v-model="cfg.tags" multiple filterable size="small" class="sum-val" placeholder="不限" @change="onConfigChange">
            <el-option v-for="t in store.tags" :key="t.id" :value="t.name" :label="t.name" />
          </el-select>
        </div>
        <div class="sum-row">
          <span class="sum-label">优先级</span>
          <el-checkbox-group v-model="prioDraft" size="small" @change="onPrioChange">
            <el-checkbox :value="3"><span style="color: #f56c6c">高</span></el-checkbox>
            <el-checkbox :value="2"><span style="color: #e6a23c">中</span></el-checkbox>
            <el-checkbox :value="1"><span style="color: #409eff">低</span></el-checkbox>
          </el-checkbox-group>
        </div>
        <div class="sum-row">
          <span class="sum-label">负责人</span>
          <el-select v-model="cfg.assignees" multiple filterable allow-create default-first-option size="small" class="sum-val" placeholder="不限" @change="onConfigChange">
            <el-option v-for="a in cfg.assignees" :key="a" :value="a" :label="a" />
          </el-select>
        </div>
      </div>

      <div class="sum-sec">
        <div class="sum-sec-head"><span class="sum-sec-title">显示设置</span></div>
        <div class="sum-row">
          <span class="sum-label">分组</span>
          <el-select v-model="cfg.group_by" size="small" class="sum-val" @change="onConfigChange">
            <el-option value="status" label="按完成状态" />
            <el-option value="list" label="按清单" />
          </el-select>
        </div>
        <div class="sum-row">
          <span class="sum-label">显示内容</span>
          <el-checkbox-group v-model="cfg.show" size="small" @change="onConfigChange">
            <el-checkbox value="date">日期</el-checkbox>
            <el-checkbox value="list">清单</el-checkbox>
            <el-checkbox value="priority">优先级</el-checkbox>
          </el-checkbox-group>
        </div>
      </div>
    </div>

    <!-- 保存为笔记 -->
    <el-dialog v-model="saveDialog" title="保存为笔记" width="380px">
      <div class="sum-save-tip">将摘要保存为一条笔记，可在笔记清单中继续编辑。</div>
      <el-select v-model="saveListId" size="small" style="width: 100%">
        <el-option value="__inbox" label="收集箱" />
        <el-option v-for="l in noteLists" :key="l.id" :value="l.id" :label="`📔 ${l.name}`" />
        <el-option v-for="l in taskLists" :key="l.id" :value="l.id" :label="l.name" />
      </el-select>
      <template #footer>
        <el-button size="small" @click="saveDialog = false">取消</el-button>
        <el-button size="small" type="primary" :disabled="!result" @click="saveAsNote">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Save, Copy, FileText } from 'lucide-vue-next'
import { useTaskStore } from '@/stores/task'
import * as taskApi from '@/api/task'

const store = useTaskStore()

const RANGE_OPTIONS = [
  { value: 'today', label: '今天' },
  { value: 'yesterday', label: '昨天' },
  { value: 'this_week', label: '本周' },
  { value: 'last_week', label: '上周' },
  { value: 'this_month', label: '本月' },
  { value: 'custom', label: '自定义' },
]

const tz = -new Date().getTimezoneOffset()
const DEFAULT_CFG = {
  range: 'this_week',
  start: null,
  end: null,
  list_ids: [],
  statuses: ['done', 'todo'],
  tags: [],
  priorities: [],
  assignees: [],
  group_by: 'status',
  show: ['date'],
  tz_offset_minutes: tz,
}

const cfg = reactive({ ...DEFAULT_CFG })
const prioDraft = ref([])
const customRange = ref(null)
const result = ref(null)
const loading = ref(false)
const saveDialog = ref(false)
const saveListId = ref('__inbox')
let timer = null

const templates = computed(() => store.settings?.summary_templates || [])
const noteLists = computed(() => store.lists.filter((l) => l.kind === 'note'))
const taskLists = computed(() => store.lists.filter((l) => l.kind !== 'note'))

onMounted(async () => {
  if (!store.settings) await store.fetchSettings().catch(() => {})
  const saved = store.settings?.summary_config || {}
  Object.assign(cfg, DEFAULT_CFG, saved, { tz_offset_minutes: tz })
  prioDraft.value = [...(cfg.priorities || [])]
  if (cfg.range === 'custom' && cfg.start && cfg.end) {
    customRange.value = [String(cfg.start).slice(0, 10), String(cfg.end).slice(0, 10)]
  }
  refresh()
})

function payload() {
  const p = { ...cfg, tz_offset_minutes: tz }
  if (cfg.range === 'custom' && customRange.value?.length === 2) {
    p.start = `${customRange.value[0]}T00:00:00`
    p.end = `${customRange.value[1]}T00:00:00`
    // end 开区间 → 次日 00:00 包含结束日当天
    const d = new Date(`${customRange.value[1]}T00:00:00`)
    d.setDate(d.getDate() + 1)
    p.end = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}T00:00:00`
  } else {
    p.start = null
    p.end = null
  }
  return p
}

async function refresh() {
  loading.value = true
  try {
    result.value = await taskApi.previewSummary(payload())
  } catch {
    ElMessage.error('摘要生成失败')
  } finally {
    loading.value = false
  }
}

// 配置变更：防抖重新生成 + 记住配置（对齐主流待办应用：上次配置自动保留）
function onConfigChange() {
  clearTimeout(timer)
  timer = setTimeout(async () => {
    await refresh()
    store.saveSettings({ summary_config: payload() }).catch(() => {})
  }, 300)
}
function onPrioChange(v) {
  cfg.priorities = [...v]
  onConfigChange()
}

// ---------- 模板 ----------
async function saveTemplate() {
  try {
    const { value } = await ElMessageBox.prompt('模板名称', '保存为模板', {
      inputPattern: /\S+/,
      inputErrorMessage: '请输入名称',
    })
    const name = value.trim()
    const list = [...templates.value, { name, config: payload() }]
    await store.saveSettings({ summary_templates: list })
    ElMessage.success('模板已保存')
  } catch { /* 取消 */ }
}
function applyTemplate(t) {
  Object.assign(cfg, DEFAULT_CFG, t.config, { tz_offset_minutes: tz })
  prioDraft.value = [...(cfg.priorities || [])]
  if (cfg.range === 'custom' && t.config.start && t.config.end) {
    customRange.value = [String(t.config.start).slice(0, 10), String(t.config.end).slice(0, 10)]
  }
  onConfigChange()
}
async function delTemplate(i) {
  const list = templates.value.filter((_, idx) => idx !== i)
  await store.saveSettings({ summary_templates: list })
}

// ---------- 保存为笔记 / 复制 ----------
function mdToHtml(md) {
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  return md
    .split('\n')
    .map((l) => {
      const t = esc(l)
      if (t.startsWith('## ')) return `<h3>${t.slice(3)}</h3>`
      if (t.startsWith('# ')) return `<h2>${t.slice(2)}</h2>`
      if (!t.trim()) return '<br/>'
      return `<div>${t}</div>`
    })
    .join('')
}

async function saveAsNote() {
  if (!result.value) return
  const listId = saveListId.value === '__inbox' ? null : saveListId.value
  const list = store.lists.find((l) => l.id === listId)
  await store.createTask({
    title: `${result.value.range_label} 摘要`,
    note: mdToHtml(result.value.markdown),
    list_id: listId,
    is_note: list ? list.kind === 'note' : false,
  })
  ElMessage.success('已保存为笔记')
  saveDialog.value = false
}

async function copyMarkdown() {
  try {
    await navigator.clipboard.writeText(result.value?.markdown || '')
    ElMessage.success('已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}
</script>

<style scoped>
.summary-view {
  display: flex;
  height: 100%;
  overflow: hidden;
}
/* 左：结果区 */
.sum-result-pane {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  padding: 20px 32px 60px;
  position: relative;
}
.sum-range {
  font-size: 20px;
  font-weight: 700;
  margin: 0 0 12px;
  color: #333;
}
.sum-group {
  margin-bottom: 18px;
}
.sum-group-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 6px;
  color: #333;
}
.sum-items {
  margin: 0;
  padding-left: 4px;
  list-style: none;
}
.sum-item {
  padding: 4px 0;
  font-size: 14px;
  color: #444;
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.sum-date {
  color: #999;
  flex-shrink: 0;
}
.sum-prio {
  font-size: 12px;
  flex-shrink: 0;
}
.sum-list {
  color: #aaa;
  font-size: 12px;
}
.sum-loading {
  color: #999;
  padding: 40px 0;
  text-align: center;
}
.sum-actions {
  position: absolute;
  bottom: 16px;
  left: 32px;
  display: flex;
  gap: 8px;
}
/* 右：配置面板 */
.sum-config-pane {
  width: 300px;
  flex-shrink: 0;
  border-left: 1px solid var(--ss-border, #ebeef5);
  overflow-y: auto;
  padding: 16px;
  background: #fafbfc;
}
.sum-sec {
  margin-bottom: 20px;
}
.sum-sec-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}
.sum-sec-title {
  font-size: 13px;
  font-weight: 600;
  color: #666;
}
.sum-sec-add {
  cursor: pointer;
  color: #999;
  padding: 2px;
  border-radius: 4px;
  display: inline-flex;
}
.sum-sec-add:hover {
  background: rgba(0, 0, 0, 0.06);
  color: #666;
}
.sum-template {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  color: #444;
  padding: 6px 8px;
  border-radius: 6px;
  cursor: pointer;
}
.sum-template:hover {
  background: rgba(0, 0, 0, 0.05);
}
.sum-template-icon {
  color: #999;
  flex-shrink: 0;
}
.sum-template-del {
  margin-left: auto;
  color: #c0c4cc;
  visibility: hidden;
}
.sum-template:hover .sum-template-del {
  visibility: visible;
}
.sum-template-del:hover {
  color: #e64a3b;
}
.sum-empty {
  font-size: 12px;
  color: #b0b0b0;
  padding: 4px 8px;
}
.sum-row {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 5px 0;
}
.sum-label {
  width: 56px;
  flex-shrink: 0;
  font-size: 13px;
  color: #666;
  line-height: 24px;
}
.sum-val {
  flex: 1;
  min-width: 0;
}
.sum-save-tip {
  font-size: 13px;
  color: #888;
  margin-bottom: 10px;
}
</style>
