<template>
  <!-- 习惯新建/编辑对话框（对齐主流待办应用「添加习惯」：图标+名称 / 频率 / 目标 / 打卡时 / 所属分组 / 提醒 / 自动弹出打卡日志 / 鼓励语） -->
  <el-dialog v-model="visible" :title="editing ? '编辑习惯' : '添加习惯'" width="440px" append-to-body>
    <el-form label-width="96px">
      <el-form-item label="图标">
        <div class="icon-head">
          <span class="icon-preview" :style="{ background: form.color }">
            <img :src="habitIconOf(form.icon)" alt="" />
          </span>
          <el-color-picker v-model="form.color" />
        </div>
        <div class="icon-picker">
          <span
            v-for="ic in HABIT_ICONS"
            :key="ic.key"
            class="icon-opt"
            :class="{ active: form.icon === ic.key }"
            :title="ic.label"
            @click="form.icon = ic.key"
          >
            <img :src="ic.src" :alt="ic.label" />
          </span>
        </div>
      </el-form-item>
      <el-form-item label="名称">
        <el-input v-model="form.name" maxlength="30" placeholder="每天进步一点点" />
      </el-form-item>
      <el-form-item label="频率">
        <div class="freq-row">
          <el-select v-model="form.freq" style="width: 130px">
            <el-option value="daily" label="每天" />
            <el-option value="weekly" label="每周" />
          </el-select>
          <template v-if="form.freq === 'weekly'">
            <span class="form-hint">每周完成</span>
            <el-input-number v-model="form.target_per_week" :min="1" :max="7" size="small" />
            <span class="form-hint">天</span>
          </template>
        </div>
      </el-form-item>
      <el-form-item label="目标">
        <div class="freq-row">
          <el-select v-model="form.goal_type" style="width: 170px">
            <el-option value="check" label="当天完成打卡" />
            <el-option value="amount" label="当天完成一定量" />
          </el-select>
          <template v-if="form.goal_type === 'amount'">
            <el-input-number v-model="form.target_per_day" :min="1" :max="99" size="small" />
            <span class="form-hint">次/天</span>
          </template>
        </div>
      </el-form-item>
      <el-form-item label="打卡时">
        <el-select v-model="form.checkin_mode" style="width: 100%">
          <el-option value="auto" label="自动记录（每打卡一次 +1）" />
          <el-option value="manual" label="手动记录（每次输入完成量）" />
          <el-option value="all" label="完成全部（一次完成目标）" />
        </el-select>
      </el-form-item>
      <el-form-item label="所属分组">
        <el-select v-model="form.group" filterable allow-create default-first-option clearable placeholder="选择或输入新分组" style="width: 100%">
          <el-option v-for="g in existingGroups" :key="g" :value="g" :label="g" />
        </el-select>
      </el-form-item>
      <el-form-item label="提醒">
        <div class="remind-row">
          <el-time-picker
            v-model="remindInput"
            format="HH:mm"
            value-format="HH:mm"
            placeholder="添加提醒"
            style="width: 120px"
          />
          <el-button size="small" text type="primary" :disabled="!remindInput" @click="addReminder">＋ 添加</el-button>
        </div>
        <div v-if="form.reminders.length" class="remind-chips">
          <span v-for="t in form.reminders" :key="t" class="remind-chip">
            {{ t }}
            <span class="remind-x" @click="form.reminders = form.reminders.filter((x) => x !== t)">×</span>
          </span>
        </div>
      </el-form-item>
      <el-form-item label="鼓励语">
        <el-input v-model="form.motto" maxlength="50" placeholder="写点鼓励自己的话（可选）" />
      </el-form-item>
      <el-form-item label="打卡日志">
        <span class="form-hint">打卡后自动弹出心情/日志弹层</span>
        <el-switch v-model="form.auto_log" style="margin-left: 10px" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :disabled="!form.name.trim()" @click="submit">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useHabitStore } from '@/stores/habit'
import { HABIT_ICONS, habitIconOf } from '@/utils/habitIcons'

const store = useHabitStore()

const defaultForm = () => ({
  name: '',
  color: '#4f6ef7',
  icon: 'smile',
  freq: 'daily',
  target_per_day: 1,
  target_per_week: 7,
  start_date: null,
  group: '',
  goal_type: 'check',
  checkin_mode: 'auto',
  reminders: [],
  auto_log: true,
  motto: '',
})

const visible = ref(false)
const editing = ref(null)
const form = ref(defaultForm())
const remindInput = ref(null)

const existingGroups = computed(() => {
  const s = new Set()
  for (const h of store.habits) if (h.group) s.add(h.group)
  return [...s]
})

function addReminder() {
  const t = remindInput.value
  if (!t || form.value.reminders.includes(t)) return
  form.value.reminders = [...form.value.reminders, t].sort()
  remindInput.value = null
}

// open(null)=新建；open(habit)=编辑回填
function open(habit) {
  editing.value = habit || null
  form.value = habit
    ? {
        name: habit.name,
        color: habit.color,
        icon: habit.icon || 'smile',
        freq: habit.freq || 'daily',
        target_per_day: habit.target_per_day || 1,
        target_per_week: habit.target_per_week || 7,
        start_date: habit.start_date || null,
        group: habit.group || '',
        goal_type: habit.goal_type || 'check',
        checkin_mode: habit.checkin_mode || 'auto',
        reminders: [...(habit.reminders || [])],
        auto_log: habit.auto_log !== false,
        motto: habit.motto || '',
      }
    : defaultForm()
  remindInput.value = null
  visible.value = true
}

async function submit() {
  const payload = {
    name: form.value.name.trim(),
    color: form.value.color,
    icon: form.value.icon,
    freq: form.value.freq,
    target_per_day: form.value.goal_type === 'amount' ? form.value.target_per_day : 1,
    target_per_week: form.value.target_per_week,
    start_date: form.value.start_date || null,
    group: form.value.group?.trim() || null,
    goal_type: form.value.goal_type,
    checkin_mode: form.value.checkin_mode,
    reminders: form.value.reminders,
    auto_log: form.value.auto_log,
    motto: form.value.motto.trim(),
  }
  if (editing.value) {
    await store.update(editing.value.id, payload)
  } else {
    await store.create(payload)
  }
  visible.value = false
}

defineExpose({ open })
</script>

<style scoped>
.form-hint {
  margin-left: 8px;
  margin-right: 4px;
  font-size: 12px;
  color: var(--ss-text-muted);
}
.icon-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
}
.icon-preview {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.icon-preview img {
  width: 22px;
  height: 22px;
}
.freq-row {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
}
.remind-row {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}
.remind-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 6px;
  width: 100%;
}
.remind-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  background: var(--ss-fill, #f7f7f9);
  border-radius: 999px;
  padding: 2px 10px;
}
.remind-x {
  cursor: pointer;
  color: var(--ss-text-muted);
}
.remind-x:hover {
  color: var(--el-color-danger);
}
/* 图标选择器：网格排列，选中高亮（对齐主流待办应用习惯图标库） */
.icon-picker {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
  width: 100%;
}
.icon-opt {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 4px;
  border-radius: 6px;
  border: 1px solid transparent;
  cursor: pointer;
}
.icon-opt img {
  width: 22px;
  height: 22px;
  display: block;
}
.icon-opt:hover {
  background: var(--ss-bg);
}
.icon-opt.active {
  border-color: var(--ss-primary);
  background: #e8f0ff;
}
</style>
