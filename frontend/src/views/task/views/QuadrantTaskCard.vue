<template>
  <!-- 四象限快速任务卡片（对齐主流待办应用：日期与提醒+旗标 / 准备做什么 / 收集箱+⋯；回车保存；新增与编辑共用） -->
  <div class="qac">
    <div class="qac-top">
      <CalendarClock :size="15" class="qac-icon" />
      <el-date-picker
        :model-value="due"
        type="date"
        placeholder="日期与提醒"
        value-format="YYYY-MM-DD"
        class="qac-date"
        @update:model-value="emit('update:due', $event)"
      />
      <span
        class="qac-flag"
        :data-priority="priority"
        :style="{ color: FLAG_COLORS[priority] }"
        :title="`优先级：${['无', '低', '中', '高'][priority]}（点击切换）`"
        @click="emit('cyclePriority')"
      >
        <Flag :size="15" fill="currentColor" />
      </span>
    </div>
    <el-input
      :model-value="text"
      type="textarea"
      :rows="3"
      placeholder="准备做什么？"
      class="qac-text"
      @update:model-value="emit('update:text', $event)"
      @keydown.enter.prevent="emit('enter')"
    />
    <div class="qac-bottom">
      <Inbox :size="15" class="qac-icon" />
      <el-select
        :model-value="listId"
        class="qac-list"
        placeholder="收集箱"
        @update:model-value="emit('update:listId', $event)"
      >
        <el-option :value="null" label="收集箱" />
        <el-option v-for="l in lists" :key="l.id" :value="l.id" :label="l.name" />
      </el-select>
      <el-dropdown trigger="click" @command="(c) => emit('more', c)">
        <span class="qac-more" @click.stop><MoreHorizontal :size="15" /></span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="tag"># 添加标签</el-dropdown-item>
            <el-dropdown-item command="clearDue">清除日期</el-dropdown-item>
            <el-dropdown-item v-if="deletable" command="delete">🗑 删除任务</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<script setup>
import { CalendarClock, Inbox, MoreHorizontal, Flag } from 'lucide-vue-next'

defineProps({
  text: { type: String, default: '' },
  due: { type: String, default: '' },
  priority: { type: Number, default: 0 },
  listId: { type: String, default: null },
  lists: { type: Array, default: () => [] },
  deletable: Boolean,
})
const emit = defineEmits(['update:text', 'update:due', 'update:priority', 'update:listId', 'cyclePriority', 'enter', 'more'])

const FLAG_COLORS = ['#c8cdd8', '#409eff', '#e6a23c', '#f56c6c']
</script>

<style scoped>
.qac {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.qac-top {
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid var(--ss-border-light, #f0f0f0);
  padding-bottom: 8px;
}
.qac-icon {
  color: var(--ss-text-secondary);
  flex-shrink: 0;
}
.qac-date {
  flex: 1;
}
.qac-date :deep(.el-input__wrapper) {
  box-shadow: none !important;
  padding: 0;
}
.qac-flag {
  margin-left: auto;
  cursor: pointer;
  display: inline-flex;
  padding: 4px;
  border-radius: 6px;
}
.qac-flag:hover {
  background: var(--ss-fill, #f7f7f9);
}
.qac-text :deep(.el-textarea__inner) {
  box-shadow: none !important;
  padding: 4px 0;
  font-size: 14px;
}
.qac-bottom {
  display: flex;
  align-items: center;
  gap: 8px;
  border-top: 1px solid var(--ss-border-light, #f0f0f0);
  padding-top: 8px;
}
.qac-list {
  flex: 1;
}
.qac-list :deep(.el-select__wrapper) {
  box-shadow: none !important;
  padding: 0;
}
.qac-more {
  margin-left: auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--ss-text-secondary);
}
.qac-more:hover {
  background: var(--ss-fill, #f7f7f9);
  color: var(--el-color-primary);
}
</style>
