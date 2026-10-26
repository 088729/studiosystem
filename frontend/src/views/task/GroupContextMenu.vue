<template>
  <teleport to="body">
    <div
      v-if="visible && group"
      ref="menuEl"
      class="task-context-menu"
      :style="{ left: `${pos.x}px`, top: `${pos.y}px` }"
      @click.stop
      @contextmenu.prevent.stop
    >
      <div class="ctx-item" @click="rename">
        <Pencil :size="14" class="ctx-item-icon" />重命名
      </div>
      <div class="ctx-item" @click="addGroup(true)">
        <ListStart :size="14" class="ctx-item-icon" />在上方添加分组
      </div>
      <div class="ctx-item" @click="addGroup(false)">
        <ListEnd :size="14" class="ctx-item-icon" />在下方添加分组
      </div>

      <!-- 移动到：hover 展开二级子菜单（收集箱 + 清单，可搜索，当前清单打勾不可选） -->
      <div class="ctx-item ctx-submenu-trigger">
        <FolderInput :size="14" class="ctx-item-icon" />移动到
        <ChevronRight :size="13" class="ctx-submenu-arrow" />
        <div class="ctx-submenu" :class="{ 'flip-x': flipX }" @click.stop>
          <div class="ctx-move-search">
            <el-input v-model="moveKw" size="small" placeholder="搜索" :prefix-icon="Search" clearable />
          </div>
          <div v-for="t in moveItems" :key="String(t.id)" class="ctx-item" :class="{ 'ctx-disabled': t.current }" @click="moveTo(t)">
            <Inbox v-if="t.id === null" :size="14" class="ctx-item-icon" />
            <component
              v-else-if="listIconOf(t.icon)"
              :is="listIconOf(t.icon)"
              :size="14"
              :style="{ color: t.color, flexShrink: 0 }"
            />
            <span v-else class="ctx-color-dot" :style="{ background: t.color }" />
            {{ t.name }}
            <Check v-if="t.current" :size="13" class="ctx-check-on" />
          </div>
          <div v-if="!moveItems.length" class="ctx-empty">无匹配清单</div>
        </div>
      </div>

      <div class="ctx-divider" />

      <div class="ctx-item danger" @click="remove">
        <Trash2 :size="14" class="ctx-item-icon" />删除
      </div>
    </div>
  </teleport>
</template>

<script setup>
import { computed, nextTick, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, ChevronRight, FolderInput, Inbox, ListEnd, ListStart, Pencil, Search, Trash2 } from 'lucide-vue-next'
import { listIconOf } from '@/utils/listIcons'
import { useTaskStore } from '@/stores/task'

// 分组头右键/⋯ 上下文菜单（对齐主流待办应用分组菜单）：自绘固定定位菜单
// 使用：父组件 ref 调 open(x, y, { key, label })；点击菜单外 / Esc 关闭
const store = useTaskStore()

const visible = ref(false)
const group = ref(null)
const pos = ref({ x: 0, y: 0 })
const flipX = ref(false)
const menuEl = ref(null)
const moveKw = ref('')

const isInboxSource = computed(() => store.activeListKey === 'smart:inbox')

// 移动目标：收集箱（清单分组才有）+ 全部清单；当前清单打勾置灰；按关键字过滤
const moveItems = computed(() => {
  const kw = moveKw.value.trim().toLowerCase()
  const hit = (s) => !kw || s.toLowerCase().includes(kw)
  const items = []
  if (!isInboxSource.value && hit('收集箱')) items.push({ id: null, name: '收集箱' })
  for (const l of store.lists) {
    if (hit(l.name)) items.push({ id: l.id, name: l.name, icon: l.icon, color: l.color, current: l.id === store.activeList?.id })
  }
  return items
})

async function open(x, y, g) {
  // 兼容列表视图分组对象（label）与看板列对象（name）
  group.value = g && g.key != null ? { ...g, label: g.label ?? g.name ?? "" } : g
  moveKw.value = ''
  pos.value = { x, y }
  flipX.value = false
  visible.value = true
  await nextTick()
  // 视口边缘防溢出：靠右/靠下时翻转（二级子菜单随之向左展开）
  const el = menuEl.value
  if (el) {
    const rect = el.getBoundingClientRect()
    if (x + rect.width > window.innerWidth - 8) {
      pos.value.x = Math.max(8, x - rect.width)
      flipX.value = true
    }
    if (y + rect.height > window.innerHeight - 8) {
      pos.value.y = Math.max(8, window.innerHeight - rect.height - 8)
    }
  }
  document.addEventListener('click', onDocClick, true)
  document.addEventListener('contextmenu', onDocClick, true)
  document.addEventListener('keydown', onDocKeydown, true)
}

function close() {
  visible.value = false
  document.removeEventListener('click', onDocClick, true)
  document.removeEventListener('contextmenu', onDocClick, true)
  document.removeEventListener('keydown', onDocKeydown, true)
}

function onDocClick(e) {
  if (e.target.closest('.task-context-menu')) return
  close()
}

function onDocKeydown(e) {
  if (e.key === 'Escape') close()
}

// 当前分组在源容器分组序中的位置（addAbove/addBelow 需要插入下标）
function sourceIndexOf(g) {
  const bgs = store.activeListKey === 'smart:inbox' ? store.inboxGroups : store.activeList?.board_groups || []
  return bgs.indexOf(g.key)
}

async function rename() {
  close()
  const g = group.value
  if (!g) return
  try {
    const { value } = await ElMessageBox.prompt('分组名称', '重命名分组', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputValue: g.label,
      inputPattern: /\S+/,
      inputErrorMessage: '分组名不能为空',
    })
    await store.renameBoardGroup(g.key, value.trim())
  } catch {
    // 取消
  }
}

async function addGroup(above) {
  close()
  const g = group.value
  if (!g) return
  const idx = sourceIndexOf(g)
  if (idx === -1) return
  try {
    const { value } = await ElMessageBox.prompt('分组名称', '添加分组', {
      confirmButtonText: '保存',
      cancelButtonText: '取消',
      inputPattern: /\S+/,
      inputErrorMessage: '分组名不能为空',
    })
    await store.addBoardGroup(value.trim(), above ? idx : idx + 1)
  } catch {
    // 取消
  }
}

async function moveTo(target) {
  close()
  const g = group.value
  if (!g || target.current) return // 当前清单 = 仅展示勾选
  try {
    await store.moveBoardGroup(g.key, target.id)
    ElMessage.success(`分组「${g.label}」已移动到「${target.name}」`)
  } catch {
    // 失败由请求拦截器统一提示
  }
}

async function remove() {
  close()
  const g = group.value
  if (!g) return
  try {
    await ElMessageBox.confirm(`删除分组「${g.label}」后，组内任务将回落到未分组，不会被删除。`, '删除分组', {
      type: 'warning',
      confirmButtonText: '删除',
      cancelButtonText: '取消',
    })
    await store.deleteBoardGroup(g.key)
  } catch {
    // 取消
  }
}

defineExpose({ open, close })
</script>

<style>
/* 复用 TaskContextMenu 的全局 .task-context-menu 样式；此处只补分组菜单独有部分 */
.task-context-menu .ctx-move-search {
  padding: 2px 4px 6px;
  border-bottom: 1px solid var(--ss-border, #e6e9f0);
  margin-bottom: 4px;
}
.task-context-menu .ctx-color-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.task-context-menu .ctx-check-on {
  margin-left: auto;
  color: var(--ss-primary, #4f6ef7);
}
</style>
