<template>
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑标签' : '添加标签'"
    width="540px"
    align-center
    :show-close="false"
    class="tag-edit-dialog"
  >
    <el-input
      ref="nameInput"
      v-model="form.name"
      placeholder="名称"
      maxlength="30"
      class="ted-name"
      @keyup.enter="submit"
    >
      <template #prefix>
        <span class="ted-prefix"><Tag :size="17" /></span>
      </template>
    </el-input>

    <div class="ted-row">
      <span class="ted-label">颜色</span>
      <div class="ted-colors">
        <div
          class="ted-dot ted-dot-none"
          :class="{ 'is-on': !form.color }"
          title="无颜色"
          @click="form.color = null"
        >
          <Ban :size="14" />
        </div>
        <div
          v-for="c in PRESET_COLORS"
          :key="c"
          class="ted-dot"
          :class="{ 'is-on': form.color === c }"
          :style="{ background: c }"
          @click="form.color = c"
        />
        <div class="ted-custom">
          <el-color-picker
            v-model="customColor"
            @change="(v) => v && (form.color = v)"
          />
        </div>
      </div>
    </div>

    <div class="ted-row">
      <span class="ted-label">上级标签</span>
      <el-select v-model="form.parent_id" placeholder="无" class="ted-parent">
        <el-option label="无" :value="null" />
        <el-option
          v-for="t in parentOptions"
          :key="t.id"
          :label="t.name"
          :value="t.id"
        />
      </el-select>
    </div>

    <template #footer>
      <div class="ted-footer">
        <el-button type="primary" class="ted-btn" :disabled="!form.name.trim()" @click="submit">保存</el-button>
        <el-button class="ted-btn" @click="visible = false">取消</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, nextTick, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Ban, Tag } from 'lucide-vue-next'
import { useTaskStore } from '@/stores/task'

const store = useTaskStore()

// 预设色板（对齐主流待办应用添加标签弹窗：红/橙/黄/黄绿/绿/蓝/紫）
const PRESET_COLORS = ['#ff4d4f', '#ff9f2e', '#ffce3d', '#c3d94e', '#3ecf8e', '#4fa3f7', '#8b7cf6']

const visible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const nameInput = ref(null)
const customColor = ref(null)
const form = reactive({ name: '', color: null, parent_id: null })

// 上级标签下拉只列顶级标签（防二级嵌套）；编辑时排除自身
const parentOptions = computed(() =>
  store.tags.filter((t) => !t.parent_id && t.id !== editingId.value)
)

function open(tag) {
  if (tag) {
    isEdit.value = true
    editingId.value = tag.id
    form.name = tag.name
    form.color = tag.color || null
    form.parent_id = tag.parent_id || null
  } else {
    isEdit.value = false
    editingId.value = null
    form.name = ''
    form.color = null
    form.parent_id = null
  }
  customColor.value = form.color
  visible.value = true
  nextTick(() => nameInput.value?.focus())
}

async function submit() {
  const name = form.name.trim()
  if (!name) return
  const payload = { name, color: form.color, parent_id: form.parent_id }
  try {
    if (isEdit.value) {
      await store.updateTag(editingId.value, payload)
    } else {
      await store.createTag(payload)
    }
    ElMessage.success('已保存')
    visible.value = false
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail?.message || '保存失败')
  }
}

defineExpose({ open })
</script>

<style scoped>
/* ---- 卡片（对齐主流待办应用：圆角 16px、内边距大、标题粗体无分隔线） ---- */
.tag-edit-dialog :deep(.el-dialog) {
  border-radius: 16px;
  padding: 28px 30px;
}
.tag-edit-dialog :deep(.el-dialog__header) {
  padding: 0 0 22px;
}
.tag-edit-dialog :deep(.el-dialog__title) {
  font-size: 18px;
  font-weight: 600;
}
.tag-edit-dialog :deep(.el-dialog__body) {
  padding: 0;
}
.tag-edit-dialog :deep(.el-dialog__footer) {
  padding: 30px 0 0;
}

/* ---- 名称输入框：高 48px、圆角 8px、图标右侧竖分隔线 ---- */
.ted-name :deep(.el-input__wrapper) {
  height: 48px;
  border-radius: 8px;
  padding: 0 14px 0 12px;
  box-shadow: 0 0 0 1px var(--ss-border, #dcdfe6) inset;
}
.ted-name :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1.5px var(--ss-primary) inset;
}
.ted-prefix {
  display: flex;
  align-items: center;
  height: 100%;
  padding-right: 10px;
  margin-right: 10px;
  border-right: 1px solid var(--ss-border, #e4e7ed);
  color: var(--ss-text-muted);
}

/* ---- 行布局：左标签右控件 ---- */
.ted-row {
  display: flex;
  align-items: center;
  margin-top: 24px;
}
.ted-label {
  font-size: 14px;
  color: var(--ss-text);
  flex-shrink: 0;
  width: 90px;
}

/* ---- 颜色行：24px 圆点 + 选中双圈 + 圆形自定义取色器 ---- */
.ted-colors {
  display: flex;
  align-items: center;
  gap: 14px;
}
.ted-dot {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ss-text-muted);
  box-sizing: border-box;
}
.ted-dot-none {
  border: 1px solid var(--ss-border, #dcdfe6);
}
.ted-dot.is-on {
  box-shadow: 0 0 0 2px #fff, 0 0 0 4px var(--ss-primary);
}
.ted-custom {
  width: 24px;
  height: 24px;
}
.ted-custom :deep(.el-color-picker__trigger) {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  border: none;
  padding: 0;
  overflow: hidden;
  /* 彩虹圈外观（对齐主流待办应用自定义取色入口） */
  background: conic-gradient(#ff4d4f, #ff9f2e, #ffce3d, #3ecf8e, #4fa3f7, #8b7cf6, #ff4d4f);
}
.ted-custom :deep(.el-color-picker__color),
.ted-custom :deep(.el-color-picker__color-inner),
.ted-custom :deep(.el-color-picker__icon),
.ted-custom :deep(.el-color-picker__empty) {
  display: none;
}

/* ---- 上级标签下拉：高 44px、圆角 8px ---- */
.ted-parent {
  flex: 1;
}
.ted-parent :deep(.el-select__wrapper) {
  min-height: 44px;
  border-radius: 8px;
}

/* ---- 底部按钮：居中、等宽 108px、保存禁用浅蓝 ---- */
.ted-footer {
  display: flex;
  justify-content: center;
  gap: 16px;
}
.ted-btn {
  min-width: 108px;
  height: 40px;
  border-radius: 8px;
  font-size: 14px;
  margin: 0;
}
</style>
