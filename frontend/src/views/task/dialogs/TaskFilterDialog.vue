<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑筛选' : '新建筛选'"
    width="420px"
  >
    <el-form label-position="top">
      <el-form-item label="名称">
        <el-input v-model="form.name" placeholder="筛选名称" maxlength="50" />
      </el-form-item>
      <el-form-item label="清单（空 = 全部）">
        <el-select v-model="form.lists" multiple filterable style="width: 100%">
          <el-option v-for="l in store.lists" :key="l.id" :label="l.name" :value="l.id" />
        </el-select>
      </el-form-item>
      <el-form-item label="标签（任一命中）">
        <el-select
          v-model="form.tags"
          multiple
          filterable
          allow-create
          default-first-option
          style="width: 100%"
        >
          <el-option v-for="t in store.tagCounts" :key="t.tag" :label="t.tag" :value="t.tag" />
        </el-select>
      </el-form-item>
      <el-form-item label="优先级（任一命中）">
        <el-select v-model="form.priorities" multiple style="width: 100%">
          <el-option :value="3" label="高"><Flag :size="13" color="#f56c6c" fill="#f56c6c" /> 高</el-option>
          <el-option :value="2" label="中"><Flag :size="13" color="#e6a23c" fill="#e6a23c" /> 中</el-option>
          <el-option :value="1" label="低"><Flag :size="13" color="#409eff" fill="#409eff" /> 低</el-option>
          <el-option :value="0" label="无"><Flag :size="13" color="#9ca3af" /> 无</el-option>
        </el-select>
      </el-form-item>
      <el-form-item label="日期">
        <el-radio-group v-model="form.due_range">
          <el-radio-button value="any">不限</el-radio-button>
          <el-radio-button value="overdue">已逾期</el-radio-button>
          <el-radio-button value="today">今天</el-radio-button>
          <el-radio-button value="next7">最近7天</el-radio-button>
          <el-radio-button value="no_date">无日期</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="状态">
        <el-radio-group v-model="form.status">
          <el-radio-button value="todo">未完成</el-radio-button>
          <el-radio-button value="done">已完成</el-radio-button>
          <el-radio-button value="any">全部</el-radio-button>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="关键词">
        <el-input v-model="form.keyword" placeholder="标题包含…" maxlength="50" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :disabled="!form.name.trim()" @click="submit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { Flag } from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import { useTaskStore } from '@/stores/task'

const store = useTaskStore()

const visible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const defaultForm = () => ({
  name: '',
  lists: [],
  tags: [],
  priorities: [],
  due_range: 'any',
  status: 'todo',
  keyword: '',
})
const form = reactive(defaultForm())

function open(filter) {
  Object.assign(form, defaultForm())
  if (filter) {
    isEdit.value = true
    editingId.value = filter.id
    Object.assign(form, {
      name: filter.name,
      lists: [...(filter.lists || [])],
      tags: [...(filter.tags || [])],
      priorities: [...(filter.priorities || [])],
      due_range: filter.due_range,
      status: filter.status,
      keyword: filter.keyword,
    })
  } else {
    isEdit.value = false
    editingId.value = null
  }
  visible.value = true
}

async function submit() {
  const name = form.name.trim()
  if (!name) return
  const payload = { ...form, name }
  if (isEdit.value) {
    await store.updateFilter(editingId.value, payload)
  } else {
    await store.createFilter(payload)
  }
  ElMessage.success('已保存')
  visible.value = false
}

defineExpose({ open })
</script>
