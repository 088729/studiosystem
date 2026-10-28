<template>
  <aside class="task-list-sidebar">
    <!-- 搜索入口（原顶栏按钮移入侧栏，对齐主流待办应用）：点击/Ctrl+K 唤出全局搜索弹框 -->
    <div class="side-item side-search" @click="store.searchVisible = true">
      <Search :size="16" class="side-icon" />
      <span class="side-name">搜索</span>
      <span class="side-kbd">Ctrl K</span>
    </div>

    <!-- 顶部固定三项智能清单：今天（含逾期，计数红色强调）/ 最近7天 / 收集箱 -->
    <div class="smart-section">
      <div
        v-for="item in topSmartLists"
        :key="item.key"
        class="side-item"
        :class="{ active: store.activeListKey === item.key }"
        @click="store.selectList(item.key)"
      >
        <component :is="iconOf(item.icon)" :size="16" class="side-icon" />
        <span class="side-name">{{ item.name }}</span>
        <span v-if="countOf(item.key)" class="side-count" :class="{ overdue: item.key === 'smart:today' }">
          {{ countOf(item.key) }}
        </span>
      </div>
      <!-- 摘要（对齐主流待办应用：收集箱下方、清单上方的智能入口） -->
      <div
        class="side-item"
        :class="{ active: store.activeListKey === 'summary' }"
        @click="store.selectList('summary')"
      >
        <ClipboardList :size="16" class="side-icon" />
        <span class="side-name">摘要</span>
      </div>
    </div>

    <el-divider class="side-divider" />

    <!-- 视图分组：次级入口（全部/日历/统计/习惯打卡） -->
    <div class="custom-section">
      <div class="section-title">视图</div>
      <div
        v-for="item in viewSmartLists"
        :key="item.key"
        class="side-item"
        :class="{ active: store.activeListKey === item.key }"
        @click="store.selectList(item.key)"
      >
        <component :is="iconOf(item.icon)" :size="16" class="side-icon" />
        <span class="side-name">{{ item.name }}</span>
        <span v-if="countOf(item.key)" class="side-count">{{ countOf(item.key) }}</span>
      </div>
      <div
        class="side-item"
        :class="{ active: store.activeListKey === 'calendar' }"
        @click="store.selectList('calendar')"
      >
        <Calendar :size="16" class="side-icon" />
        <span class="side-name">日历</span>
      </div>
      <div
        class="side-item"
        :class="{ active: store.activeListKey === 'stats' }"
        @click="store.selectList('stats')"
      >
        <TrendingUp :size="16" class="side-icon" />
        <span class="side-name">统计</span>
      </div>
      <div
        class="side-item"
        :class="{ active: store.activeListKey === 'habits' }"
        @click="store.selectList('habits')"
      >
        <AlarmClock :size="16" class="side-icon" />
        <span class="side-name">习惯打卡</span>
      </div>
      <!-- 专注（内容页，对齐主流待办应用：侧栏进入整页番茄专注；运行中显示计时） -->
      <div
        class="side-item"
        v-auth="'task:run'"
        :class="{ active: store.activeListKey === 'focus' }"
        @click="store.selectList('focus')"
      >
        <Timer :size="16" class="side-icon" />
        <span class="side-name">专注</span>
        <span v-if="pomodoroStore.isRunning" class="side-count">{{ pomodoroStore.displayText }}</span>
      </div>
      <div
        class="side-item"
        :class="{ active: store.viewMode === 'quadrant' }"
        @click="openQuadrant"
      >
        <LayoutGrid :size="16" class="side-icon" />
        <span class="side-name">四象限</span>
      </div>
    </div>

    <el-divider class="side-divider" />

    <div class="custom-section tag-section">
      <div class="section-title tag-title">
        <span>清单</span>
        <span class="tag-title-actions">
          <Plus :size="14" class="more-icon" v-auth="'task:create'" @click.stop="listDialog.open()" />
        </span>
      </div>
      <template v-for="row in ownListRows" :key="row.key">
        <div v-if="row.group" class="side-item group-header" @click="toggleGroup(row.group)">
          <ChevronRight :size="14" class="side-icon group-arrow" :class="{ collapsed: collapsedGroups[row.group] }" />
          <span class="side-name">{{ row.group }}</span>
          <span class="side-count">{{ row.lists.length }}</span>
        </div>
        <div
          v-for="list in row.lists"
          v-show="!row.group || !collapsedGroups[row.group]"
          :key="list.id"
          class="side-item"
          :class="{ active: store.activeListKey === `list:${list.id}`, 'group-child': !!row.group }"
          @click="store.selectList(`list:${list.id}`)"
        >
          <component
            v-if="list.kind === 'note'"
            :is="BookOpen"
            :size="15"
            class="side-list-icon"
            :style="{ color: list.color }"
          />
          <component
            v-else-if="listIconOf(list.icon)"
            :is="listIconOf(list.icon)"
            :size="15"
            class="side-list-icon"
            :style="{ color: list.color }"
          />
          <List v-else :size="16" class="side-icon" />
          <span class="side-name">{{ list.name }}</span>
          <span class="color-dot" :style="{ background: list.color }" />
          <span v-if="countOf(`list:${list.id}`)" class="side-count">{{ countOf(`list:${list.id}`) }}</span>
          <el-dropdown
            trigger="click"
            class="side-more"
            @command="(cmd) => handleListCommand(cmd, list)"
          >
            <MoreVertical :size="14" class="more-icon" @click.stop />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="rename" v-if="authStore.hasPerm('task:manage')">重命名 / 改色</el-dropdown-item>
                <el-dropdown-item command="share" v-if="authStore.hasPerm('task:share')">共享</el-dropdown-item>
                <el-dropdown-item command="delete" v-if="authStore.hasPerm('task:delete')">删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </template>

      <div v-if="!ownLists.length" class="guide-text">
        用清单来分类收集、组织和管理你的任务和笔记
      </div>
    </div>

    <el-divider class="side-divider" />

    <div class="custom-section tag-section">
      <div class="section-title tag-title">
        <span>标签</span>
        <span class="tag-title-actions">
          <el-dropdown trigger="click" @command="(cmd) => cmd === 'create' && tagDialog.open()">
            <MoreVertical :size="14" class="more-icon" @click.stop />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="create" v-if="authStore.hasPerm('task:create')">新建标签</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <Plus :size="14" class="more-icon" v-auth="'task:create'" @click.stop="tagDialog.open()" />
        </span>
      </div>
      <div v-if="!store.sidebarTags.length" class="guide-text">
        以标签的维度展示不同清单的任务，在添加任务时输入"#"可快速选择标签
      </div>
      <template v-for="t in store.sidebarTags" :key="t.name">
        <div
          class="side-item"
          :class="{ active: store.activeListKey === `tag:${t.name}` }"
          @click="store.selectList(`tag:${t.name}`)"
        >
          <Tag :size="16" class="side-icon" />
          <span class="side-name">{{ t.name }}</span>
          <span v-if="t.color" class="color-dot" :style="{ background: t.color }" />
          <span v-if="t.count" class="side-count">{{ t.count }}</span>
          <el-dropdown
            v-if="t.id"
            trigger="click"
            class="side-more"
            @command="(cmd) => handleTagCommand(cmd, t)"
          >
            <MoreVertical :size="14" class="more-icon" @click.stop />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit" v-if="authStore.hasPerm('task:edit')">编辑</el-dropdown-item>
                <el-dropdown-item command="delete" v-if="authStore.hasPerm('task:delete')">删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <div
          v-for="c in t.children"
          :key="c.name"
          class="side-item tag-child"
          :class="{ active: store.activeListKey === `tag:${c.name}` }"
          @click="store.selectList(`tag:${c.name}`)"
        >
          <Tag :size="16" class="side-icon" />
          <span class="side-name">{{ c.name }}</span>
          <span v-if="c.color" class="color-dot" :style="{ background: c.color }" />
          <span v-if="c.count" class="side-count">{{ c.count }}</span>
          <el-dropdown
            v-if="c.id"
            trigger="click"
            class="side-more"
            @command="(cmd) => handleTagCommand(cmd, c)"
          >
            <MoreVertical :size="14" class="more-icon" @click.stop />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="edit" v-if="authStore.hasPerm('task:edit')">编辑</el-dropdown-item>
                <el-dropdown-item command="delete" v-if="authStore.hasPerm('task:delete')">删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </template>
    </div>

    <template v-if="sharedLists.length">
      <el-divider class="side-divider" />
      <div class="custom-section">
        <div class="section-title">共享给我</div>
        <div
          v-for="list in sharedLists"
          :key="list.id"
          class="side-item"
          :class="{ active: store.activeListKey === `list:${list.id}` }"
          @click="store.selectList(`list:${list.id}`)"
        >
          <span class="color-dot" :style="{ background: list.color }" />
          <span class="side-name">{{ list.name }}</span>
          <el-tooltip :content="`来自 ${list.owner}`" placement="top">
            <Users :size="14" class="side-icon share-icon" />
          </el-tooltip>
          <el-dropdown
            trigger="click"
            class="side-more"
            @command="(cmd) => cmd === 'share' && shareDialog.open(list)"
          >
            <MoreVertical :size="14" class="more-icon" @click.stop />
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="share">成员 / 退出共享</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </template>

    <el-divider class="side-divider" />

    <div class="custom-section tag-section">
      <div class="section-title tag-title">
        <span>过滤器</span>
        <span class="tag-title-actions">
          <Plus :size="14" class="more-icon" v-auth="'task:create'" @click.stop="filterDialog.open()" />
        </span>
      </div>
      <div
        v-for="f in store.filters"
        :key="f.id"
        class="side-item"
        :class="{ active: store.activeListKey === `filter:${f.id}` }"
        @click="store.selectList(`filter:${f.id}`)"
      >
        <ListFilter :size="16" class="side-icon" />
        <span class="side-name">{{ f.name }}</span>
        <span v-if="f.count" class="side-count">{{ f.count }}</span>
        <el-dropdown
          trigger="click"
          class="side-more"
          @command="(cmd) => handleFilterCommand(cmd, f)"
        >
          <MoreVertical :size="14" class="more-icon" @click.stop />
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="edit" v-if="authStore.hasPerm('task:edit')">编辑</el-dropdown-item>
              <el-dropdown-item command="delete" v-if="authStore.hasPerm('task:delete')">删除</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 底部固定：已完成 / 回收站 / 设置（沉底；设置对齐主流待办应用左下角入口） -->
    <div class="bottom-section">
      <el-divider class="side-divider" />
      <div
        v-for="item in bottomSmartLists"
        :key="item.key"
        class="side-item"
        :class="{ active: store.activeListKey === item.key }"
        @click="store.selectList(item.key)"
      >
        <component :is="iconOf(item.icon)" :size="16" class="side-icon" />
        <span class="side-name">{{ item.name }}</span>
        <span v-if="countOf(item.key)" class="side-count">{{ countOf(item.key) }}</span>
      </div>
      <div class="side-item side-settings" v-auth="'task:edit'" @click="store.settingsVisible = true">
        <Settings :size="16" class="side-icon" />
        <span class="side-name">设置</span>
      </div>
    </div>

    <ListEditDialog ref="listDialog" />
    <ShareDialog ref="shareDialog" />
    <TaskFilterDialog ref="filterDialog" />
    <TagEditDialog ref="tagDialog" />
  </aside>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import {
  Sun,
  Sunrise,
  Calendar,
  Search,
  TrendingUp,
  AlarmClock,
  Timer,
  LayoutGrid,
  Inbox,
  CircleCheck,
  Trash2,
  List,
  Plus,
  MoreVertical,
  Users,
  ListFilter,
  Tag,
  ChevronRight,
  Settings,
  BookOpen,
  ClipboardList,
} from 'lucide-vue-next'
import { useTaskStore } from '@/stores/task'
import { useAuthStore } from '@/stores/auth'
import { usePomodoroStore } from '@/stores/pomodoro'
import ListEditDialog from './dialogs/ListEditDialog.vue'
import ShareDialog from './dialogs/ShareDialog.vue'
import TaskFilterDialog from './dialogs/TaskFilterDialog.vue'
import TagEditDialog from './dialogs/TagEditDialog.vue'
import { listIconOf } from '@/utils/listIcons'

const store = useTaskStore()
const authStore = useAuthStore()
const pomodoroStore = usePomodoroStore()

// 四象限入口：独立内容页（对齐主流待办应用桌面端：整页四象限卡片，无清单头部/快速添加/详情栏）
function openQuadrant() {
  store.selectList('quadrant')
}

const listDialog = ref(null)
const shareDialog = ref(null)
const filterDialog = ref(null)
const tagDialog = ref(null)

onMounted(() => {
  store.fetchFilters()
  store.fetchTagCounts()
  store.fetchTags()
})

const ownLists = computed(() => store.lists.filter((l) => !l.is_shared))
const sharedLists = computed(() => store.lists.filter((l) => l.is_shared))

// 清单分组（05-P3）：无 group 的平铺在前，有 group 的按组名折叠展示
const collapsedGroups = ref({})
const ownListRows = computed(() => {
  const rows = []
  const groups = {}
  for (const l of ownLists.value) {
    if (!l.group) rows.push({ key: `list:${l.id}`, group: null, lists: [l] })
    else (groups[l.group] ||= []).push(l)
  }
  for (const name of Object.keys(groups).sort()) {
    rows.push({ key: `group:${name}`, group: name, lists: groups[name] })
  }
  return rows
})

function toggleGroup(name) {
  collapsedGroups.value = { ...collapsedGroups.value, [name]: !collapsedGroups.value[name] }
}

const iconMap = { Sunny: Sun, Sunrise, Calendar, Box: Inbox, CircleCheck, Delete: Trash2, List }
const iconOf = (name) => iconMap[name] || List

// 侧栏结构（对齐主流待办应用）：顶部固定三项 / 视图分组 / 底部沉底两项
const TOP_SMART_KEYS = ['smart:today', 'smart:next7', 'smart:inbox']
const VIEW_SMART_KEYS = ['smart:all']
const BOTTOM_SMART_KEYS = ['smart:completed', 'smart:trash']
const topSmartLists = computed(() => store.smartLists.filter((i) => TOP_SMART_KEYS.includes(i.key)))
const viewSmartLists = computed(() => store.smartLists.filter((i) => VIEW_SMART_KEYS.includes(i.key)))
const bottomSmartLists = computed(() => store.smartLists.filter((i) => BOTTOM_SMART_KEYS.includes(i.key)))

// 计数从 summary 聚合读取（by_smart/by_list），所有清单/智能清单都有 badge
const countOf = (key) => store.countFor(key) || ''

function handleFilterCommand(cmd, filter) {
  if (cmd === 'edit') {
    filterDialog.value.open(filter)
  } else if (cmd === 'delete') {
    ElMessageBox.confirm(
      `删除筛选「${filter.name}」不会删除任何任务。`,
      '删除筛选',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    ).then(() => store.deleteFilter(filter.id)).catch(() => {})
  }
}

function handleTagCommand(cmd, tag) {
  if (cmd === 'edit') {
    tagDialog.value.open(tag)
  } else if (cmd === 'delete') {
    const hasChildren = store.sidebarTags.some((t) => t.id === tag.id && t.children.length)
    ElMessageBox.confirm(
      `删除标签「${tag.name}」后，${hasChildren ? '其下级标签将一并删除，' : ''}标签将从所有任务上移除（任务不会被删除）。`,
      '删除标签',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    ).then(() => store.deleteTag(tag.id)).catch(() => {})
  }
}

function handleListCommand(cmd, list) {
  if (cmd === 'rename') {
    listDialog.value.open(list)
  } else if (cmd === 'share') {
    shareDialog.value.open(list)
  } else if (cmd === 'delete') {
    ElMessageBox.confirm(
      `删除清单「${list.name}」后，其下任务将落入收集箱，不会被删除。`,
      '删除清单',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    ).then(() => store.deleteList(list.id)).catch(() => {})
  }
}
</script>

<style scoped>
.task-list-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow-y: auto;
  padding: 12px 8px;
}
.side-search {
  color: var(--ss-text-secondary);
  margin-bottom: 4px;
}
.side-kbd {
  font-size: 12px;
  color: var(--ss-text-muted);
}
.side-divider {
  margin: 8px 0;
}
.section-title {
  font-size: 12px;
  color: var(--ss-text-muted);
  padding: 4px 12px;
}
.tag-title {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.tag-title-actions {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  visibility: hidden;
}
.tag-section:hover .tag-title-actions {
  visibility: visible;
}
.tag-child {
  padding-left: 24px;
}
.side-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: var(--ss-radius-sm);
  cursor: pointer;
  font-size: 14px;
  color: var(--ss-text);
}
.side-item:hover {
  background: var(--ss-bg);
}
.side-item.active {
  background: var(--ss-primary-light);
  color: var(--ss-primary);
  font-weight: 500;
}
.side-icon {
  flex-shrink: 0;
}
.side-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.side-count {
  font-size: 12px;
  color: var(--ss-text-muted);
}
.side-count.overdue {
  color: #f56c6c;
}
.color-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}
.side-list-icon {
  flex-shrink: 0;
}
.group-header {
  color: var(--ss-text-secondary);
  font-weight: 500;
}
.group-arrow {
  transition: transform 0.2s;
  transform: rotate(90deg);
}
.group-arrow.collapsed {
  transform: rotate(0deg);
}
.group-child {
  padding-left: 24px;
}
.side-more {
  visibility: hidden;
}
.side-item:hover .side-more {
  visibility: visible;
}
.more-icon {
  color: var(--ss-text-muted);
  flex-shrink: 0;
}
.new-list {
  color: var(--ss-text-secondary);
}
.guide-text {
  font-size: 12px;
  color: var(--ss-text-muted);
  padding: 4px 12px 8px;
  line-height: 1.6;
}
.share-icon {
  color: var(--ss-text-muted);
}
.bottom-section {
  margin-top: auto;
}
</style>
