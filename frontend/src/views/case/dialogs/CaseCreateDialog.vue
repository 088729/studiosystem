<template>
  <el-dialog
    v-model="visible"
    :title="kind === 'folder' ? '新建文件夹' : '新建导图'"
    width="440px"
    align-center
    :show-close="false"
    class="case-create-dialog"
  >
    <el-input
      ref="nameInput"
      v-model="form.name"
      :placeholder="kind === 'folder' ? '文件夹名称' : '导图标题'"
      maxlength="30"
      class="ccd-name"
      @keyup.enter="submit"
    >
      <template #prefix>
        <span class="ccd-prefix">
          <Folder v-if="kind === 'folder'" :size="17" />
          <FileText v-else :size="17" />
        </span>
      </template>
    </el-input>

    <div class="ccd-row">
      <span class="ccd-label">位置</span>
      <el-tree-select
        v-model="form.folderId"
        :data="folderTree"
        :props="{ label: 'label', children: 'children' }"
        node-key="value"
        check-strictly
        default-expand-all
        :render-after-expand="false"
        class="ccd-position"
      />
    </div>

    <template #footer>
      <div class="ccd-footer">
        <el-button class="ccd-btn" @click="visible = false">取消</el-button>
        <el-button
          type="primary"
          class="ccd-btn"
          :loading="submitting"
          :disabled="!form.name.trim()"
          @click="submit"
        >创建</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
// 用例库「新建文件夹 / 新建导图」弹窗（对齐项目清单应用风对话框：圆角卡片、大输入框、居中底部按钮）。
// 位置选择支持任意层级文件夹，替代原先只能落根目录/跟随选中的隐性规则。
import { computed, nextTick, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { FileText, Folder } from 'lucide-vue-next'
import * as caseApi from '@/api/case'

const props = defineProps({
  folders: { type: Array, default: () => [] },
})
const emit = defineEmits(['created'])

// 根目录哨兵值（el-tree-select 需要 string value，提交时映射回 null）
const ROOT_ID = '__root__'

const visible = ref(false)
const kind = ref('folder')
const nameInput = ref(null)
const submitting = ref(false)
const form = reactive({ name: '', folderId: ROOT_ID })

// 文件夹树（仅文件夹层级；地图不能作为容器）
const folderTree = computed(() => {
  const map = {}
  const roots = []
  for (const f of props.folders) {
    map[f.id] = { value: f.id, label: f.name, children: [] }
  }
  for (const f of props.folders) {
    if (f.parent_id && map[f.parent_id]) map[f.parent_id].children.push(map[f.id])
    else roots.push(map[f.id])
  }
  return [{ value: ROOT_ID, label: '用例库（根目录）', children: roots }]
})

// opts: { kind: 'folder' | 'map', folderId: 初始位置（null=根目录，undefined=根目录） }
function open(opts = {}) {
  kind.value = opts.kind || 'folder'
  form.name = ''
  form.folderId = opts.folderId || ROOT_ID
  visible.value = true
  // 动画期间聚焦可能被吞，延迟补一次
  nextTick(() => nameInput.value?.focus())
  setTimeout(() => nameInput.value?.focus(), 200)
}

async function submit() {
  const name = form.name.trim()
  if (!name || submitting.value) return
  submitting.value = true
  try {
    const folderId = form.folderId === ROOT_ID ? null : form.folderId
    const res =
      kind.value === 'folder'
        ? await caseApi.createFolder({ name, parent_id: folderId })
        : await caseApi.createMap({ title: name, folder_id: folderId })
    ElMessage.success('创建成功')
    visible.value = false
    emit('created', res, kind.value)
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail?.message || '创建失败')
  } finally {
    submitting.value = false
  }
}

defineExpose({ open })
</script>

<style scoped>
/* ---- 卡片（对齐项目清单应用风对话框：圆角 16px、大内边距、粗体标题） ---- */
.case-create-dialog :deep(.el-dialog) {
  border-radius: 16px;
  padding: 28px 30px;
}
.case-create-dialog :deep(.el-dialog__header) {
  padding: 0 0 22px;
}
.case-create-dialog :deep(.el-dialog__title) {
  font-size: 18px;
  font-weight: 600;
}
.case-create-dialog :deep(.el-dialog__body) {
  padding: 0;
}
.case-create-dialog :deep(.el-dialog__footer) {
  padding: 30px 0 0;
}

/* ---- 名称输入框：高 48px、圆角 8px、图标右侧竖分隔线 ---- */
.ccd-name :deep(.el-input__wrapper) {
  height: 48px;
  border-radius: 8px;
  padding: 0 14px 0 12px;
  box-shadow: 0 0 0 1px var(--ss-border, #dcdfe6) inset;
}
.ccd-name :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1.5px var(--ss-primary) inset;
}
.ccd-prefix {
  display: flex;
  align-items: center;
  height: 100%;
  padding-right: 10px;
  margin-right: 10px;
  border-right: 1px solid var(--ss-border, #e4e7ed);
  color: var(--ss-text-muted);
}

/* ---- 位置行：左标签右树形下拉 ---- */
.ccd-row {
  display: flex;
  align-items: center;
  margin-top: 24px;
}
.ccd-label {
  font-size: 14px;
  color: var(--ss-text);
  flex-shrink: 0;
  width: 90px;
}
.ccd-position {
  flex: 1;
}
.ccd-position :deep(.el-select__wrapper) {
  min-height: 44px;
  border-radius: 8px;
}

/* ---- 底部按钮：居中、等宽 ---- */
.ccd-footer {
  display: flex;
  justify-content: center;
  gap: 16px;
}
.ccd-btn {
  min-width: 108px;
  height: 40px;
  border-radius: 8px;
  font-size: 14px;
  margin: 0;
}
</style>
