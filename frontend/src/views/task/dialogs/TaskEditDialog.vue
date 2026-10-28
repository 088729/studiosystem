<template>
  <el-dialog v-model="visible" title="编辑任务" width="480px">
    <el-form v-if="form" label-position="top">
      <el-form-item label="标题">
        <el-input v-model="form.title" maxlength="100" />
      </el-form-item>
      <el-form-item label="备注">
        <el-input v-model="form.note" type="textarea" :rows="3" />
      </el-form-item>
      <el-form-item label="标签">
        <el-select
          v-model="form.tags"
          multiple
          filterable
          allow-create
          default-first-option
          placeholder="输入后回车创建标签"
          style="width: 100%"
        />
      </el-form-item>
      <el-form-item label="优先级">
        <el-select v-model="form.priority" style="width: 100%">
          <el-option :value="3" label="高"><Flag :size="13" color="#f56c6c" fill="#f56c6c" /> 高</el-option>
          <el-option :value="2" label="中"><Flag :size="13" color="#e6a23c" fill="#e6a23c" /> 中</el-option>
          <el-option :value="1" label="低"><Flag :size="13" color="#409eff" fill="#409eff" /> 低</el-option>
          <el-option :value="0" label="无"><Flag :size="13" color="#9ca3af" /> 无</el-option>
        </el-select>
      </el-form-item>
      <el-form-item label="日期">
        <!-- 复用统一日期选择弹层（日期/时间段/提醒/重复，与详情栏/右键菜单一致） -->
        <TaskDatePicker
          :due-at="form.due_at"
          :all-day="form.all_day"
          :start-at="form.start_at"
          :reminders="form.reminders"
          :persistent-reminder="form.persistent_reminder"
          :recurrence="form.recurrence"
          :task-id="editingId"
          @change="onDateChange"
        >
          <template #trigger="{ label }">
            <div class="ted-date-btn"><Calendar :size="14" />{{ label }}</div>
          </template>
        </TaskDatePicker>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :disabled="!form?.title.trim()" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'
import { Calendar, Flag } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { useTaskStore } from '@/stores/task'
import TaskDatePicker from '../TaskDatePicker.vue'
import { recomputeReminders } from '../utils'

const store = useTaskStore()

const visible = ref(false)
const editingId = ref(null)
const form = ref(null)

function open(task) {
  editingId.value = task.id
  form.value = {
    title: task.title,
    note: task.note || '',
    tags: [...(task.tags || [])],
    priority: task.priority,
    due_at: task.due_at,
    all_day: task.all_day,
    start_at: task.start_at || null,
    reminders: (task.reminders || []).map((r) => ({ ...r })),
    persistent_reminder: !!task.persistent_reminder,
    recurrence: task.recurrence ? { ...task.recurrence } : null,
  }
  visible.value = true
}

// 日期弹层提交：{ due_at, all_day, start_at, reminders, recurrence }（相对提醒随日期重算）
function onDateChange({ due_at, all_day, start_at = null, reminders, persistent_reminder, recurrence }) {
  form.value.due_at = due_at
  form.value.all_day = all_day
  form.value.start_at = start_at
  if (reminders !== undefined) form.value.reminders = recomputeReminders(reminders, due_at)
  if (persistent_reminder !== undefined) form.value.persistent_reminder = persistent_reminder
  if (recurrence !== undefined) form.value.recurrence = recurrence
}

async function submit() {
  const f = form.value
  if (!f.title.trim()) return
  await store.updateTask(editingId.value, {
    title: f.title.trim(),
    note: f.note || null,
    tags: f.tags,
    priority: f.priority,
    // 日期弹层已归一化（全天=当地 00:00 UTC；相对提醒已重算绝对 at）
    due_at: f.due_at,
    all_day: f.all_day,
    start_at: f.start_at,
    reminders: f.reminders,
    persistent_reminder: f.persistent_reminder,
    recurrence: f.recurrence,
  })
  ElMessage.success('已保存')
  visible.value = false
}

defineExpose({ open })
</script>

<style scoped>
/* 日期弹层触发按钮：仿输入框全宽 */
.ted-date-btn {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 10px;
  border: 1px solid var(--ss-border);
  border-radius: 6px;
  font-size: 13px;
  color: var(--ss-text);
  cursor: pointer;
  box-sizing: border-box;
}
.ted-date-btn:hover {
  border-color: var(--ss-primary);
}
</style>
