<template>
  <!-- 常驻右侧详情栏（整窗三栏第三栏）：activeTaskId 非空时渲染，空时不占位 -->
  <aside v-if="store.activeTaskId" class="task-detail-panel" :class="{ 'note-expanded': noteExpanded, 'overlay-timeline': store.viewMode === 'timeline', 'overlay-board': store.viewMode === 'board' }">
    <div v-if="task" class="task-detail">
      <!-- 顶栏行：完成勾选 + 日期按钮 | 优先级旗帜 + ⋯更多(置顶) + 关闭 -->
      <div class="detail-header">
        <span
          v-if="!noteMode"
          class="check-dot"
          :class="{ checked: task.status === 'done', disabled: !canEdit }"
          @click="canEdit && store.complete(task.id, task.status !== 'done')"
        >
          <Check v-if="task.status === 'done'" :size="12" />
        </span>
        <!-- 顶栏日期按钮（对齐主流待办应用：「📅 今天, 8月22日」纯文字按钮），点击弹日期选择弹层 -->
        <TaskDatePicker
          :due-at="task.due_at"
          :all-day="task.all_day"
          :start-at="task.start_at"
          :reminders="task.reminders"
          :persistent-reminder="task.persistent_reminder"
          :recurrence="task.recurrence"
          :disabled="!canEdit"
          :task-id="task.id"
          @change="onDatePick"
        >
          <template #trigger="{ label }">
            <span class="header-date-btn" :class="{ disabled: !canEdit }">
              <Calendar :size="16" />
              <span>{{ label }}</span>
            </span>
          </template>
        </TaskDatePicker>
        <div class="header-right">
          <!-- 优先级旗帜（对齐主流待办应用：右上角为优先级；置顶在右键菜单）。笔记无优先级 -->
          <el-dropdown v-if="!noteMode" trigger="click" :disabled="!canEdit" @command="setPriority">
            <span class="flag-btn" :class="{ disabled: !canEdit }" :title="priorityTip">
              <Flag :size="15" :color="priorityColor" :fill="task.priority ? priorityColor : 'none'" />
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item v-for="opt in priorityOptions" :key="opt.value" :command="opt.value">
                  <Flag :size="13" :color="opt.color" :fill="opt.value ? opt.color : 'none'" style="margin-right: 6px; vertical-align: -2px" />
                  {{ opt.label }}
                  <Check v-if="(task.priority || 0) === opt.value" :size="13" style="margin-left: auto; color: var(--ss-primary)" />
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <!-- ⋯ 更多菜单（对齐主流待办应用：详情页右上角「···」内含置顶） -->
          <el-dropdown trigger="click" :disabled="!canEdit" @command="onMoreCmd">
            <span class="flag-btn" :class="{ disabled: !canEdit }" title="更多">
              <MoreVertical :size="15" />
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="pin">
                  <Pin :size="13" style="margin-right: 6px; vertical-align: -2px" />
                  {{ task.is_pinned ? '取消置顶' : '置顶' }}
                </el-dropdown-item>
                <el-dropdown-item v-if="noteMode" command="toTask">
                  <CheckSquare :size="13" style="margin-right: 6px; vertical-align: -2px" />转换为任务
                </el-dropdown-item>
                <el-dropdown-item v-else :command="'toNote'" :disabled="(task.subtask_total || 0) > 0" :title="(task.subtask_total || 0) > 0 ? '含子任务的任务无法转换为笔记' : ''">
                  <BookOpen :size="13" style="margin-right: 6px; vertical-align: -2px" />转换为笔记
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <X :size="16" class="panel-close" title="关闭" @click="store.closeDetail()" />
        </div>
      </div>

      <!-- 标题行：加粗 18px 行内编辑，无边框，done 划线；右侧「检查事项 ⇄ 详情」切换 -->
      <div class="title-row">
        <el-input
          v-model="titleDraft"
          class="title-input"
          :class="{ done: task.status === 'done' }"
          :disabled="!canEdit"
          @change="(v) => save({ title: v })"
        />
        <List
          :size="16"
          class="mode-toggle"
          :title="subtaskMode === 'checklist' ? '详情' : '检查事项'"
          @click="subtaskMode = subtaskMode === 'checklist' ? 'detail' : 'checklist'"
        />
      </div>

      <!-- 元信息行：所属清单（点击打开「移动到」弹窗）+ 标签（chip 增删，可输入创建；对齐主流待办应用详情标题下方） -->
      <div class="meta-row">
        <span
          v-if="task.recurrence && task.next_due"
          class="meta-nextdue"
          :title="`重复任务下次到期：${dayjs(task.next_due).format('YYYY年M月D日')}`"
        ><Repeat :size="11" />下次 {{ dayjs(task.next_due).format('M月D日') }}</span>
        <span
          class="meta-list"
          :class="{ clickable: canEdit }"
          :title="canEdit ? '移动到其它清单' : ''"
          @click="openMove"
        ><Inbox :size="12" />{{ listName }}</span>
        <el-select
          :model-value="task.tags || []"
          class="meta-tags"
          multiple
          filterable
          allow-create
          default-first-option
          collapse-tags
          collapse-tags-tooltip
          placeholder="+ 标签"
          size="small"
          :disabled="!canEdit"
          @change="(v) => save({ tags: v })"
        >
          <el-option v-for="t in store.tags" :key="t.id" :value="t.name" :label="t.name" />
        </el-select>
      </div>

      <!-- 内容滚动区：备注 / 关联用例 -->
      <div class="detail-body">
        <!-- 备注：富文本编辑器（对齐主流待办应用）：contenteditable，HTML 落库；工具栏见底部悬浮条 -->
        <div
          ref="noteEl"
          class="note-editor"
          :class="{ disabled: !canEdit }"
          :contenteditable="canEdit"
          data-placeholder="输入内容或使用 / 快速插入"
          @input="onNoteInput"
          @click="onNoteClick"
          @keydown="onNoteKeydown"
          @keyup="onNoteKeyup"
          @focus="noteFocused = true"
          @blur="onNoteBlur"
        ></div>

        <!-- “/” 快捷插入菜单（对齐主流待办应用：标题/列表/检查项/引用/分割线/子任务/标签/附件） -->
        <div v-if="slash.open" class="slash-menu" :style="{ left: slash.left + 'px', top: slash.top + 'px' }">
          <div
            v-for="(it, i) in slashItems"
            :key="it.key"
            class="slash-item"
            :class="{ active: i === slash.index }"
            @mousedown.prevent="applySlash(it)"
          >
            <component :is="it.icon" :size="14" class="slash-icon" />{{ it.label }}
          </div>
          <div v-if="!slashItems.length" class="slash-empty">无匹配项</div>
        </div>

      <!-- 子任务块：无边框 checklist，进度小字放右上角（笔记无子任务，不显示） -->
      <div v-if="!task.parent_id && !noteMode" class="subtask-block">
        <span v-if="task.subtask_total" class="subtask-progress">
          {{ task.subtask_done }}/{{ task.subtask_total }}
        </span>
        <!-- 检查事项模式（默认）：复选框 + 内联编辑 + 分隔线 -->
        <div v-if="subtaskMode === 'checklist'" class="subtask-list">
          <div
            v-for="sub in task.subtasks"
            :key="sub.id"
            class="subtask-row"
            :class="{
              'drop-before': subDropHint?.id === sub.id && subDropHint?.pos === 'before',
              'drop-after': subDropHint?.id === sub.id && subDropHint?.pos === 'after',
            }"
            @dragover.prevent="onSubDragOver(sub, $event)"
            @dragleave="onSubDragLeave(sub)"
            @drop.prevent="onSubDrop(sub)"
          >
            <span
              class="sub-check"
              :class="{ checked: sub.status === 'done', disabled: !canEdit }"
              @click="canEdit && store.completeSubtask(sub.id, sub.status !== 'done')"
            >
              <Check v-if="sub.status === 'done'" :size="10" />
            </span>
            <el-input
              :ref="(el) => setSubInputRef(sub.id, el)"
              v-model="subtaskDrafts[sub.id]"
              class="subtask-title-input"
              :class="{ done: sub.status === 'done' }"
              :disabled="!canEdit"
              size="small"
              @change="(v) => onSubtaskTitle(sub, v)"
              @keydown.enter.prevent="onSubtaskEnter(sub)"
              @blur="onSubtaskBlur(sub)"
            />
            <!-- 行尾操作（hover 显示，对齐主流待办应用）：时间/提醒 + 删除 -->
            <div class="subtask-actions">
              <TaskDatePicker
                :due-at="sub.due_at"
                :all-day="sub.all_day"
                :start-at="sub.start_at"
                :reminders="sub.reminders"
                :persistent-reminder="sub.persistent_reminder"
                :disabled="!canEdit"
                :task-id="sub.id"
                @change="(p) => onSubtaskDate(sub, p)"
              >
                <template #trigger>
                  <AlarmClock :size="14" class="subtask-action-icon" :class="{ active: sub.due_at }" title="设置时间" />
                </template>
              </TaskDatePicker>
              <span
                v-if="canEdit"
                class="subtask-action-icon sub-drag"
                title="拖动排序"
                draggable="true"
                @dragstart="onSubDragStart(sub, $event)"
                @dragend="onSubDragEnd"
              >
                <GripVertical :size="14" />
              </span>
              <Trash2 :size="14" class="subtask-action-icon" title="删除" @click="store.deleteSubtask(sub.id)" />
            </div>
          </div>
          <el-input
            ref="subtaskInput"
            v-model="newSubtask"
            v-auth="'task:create'"
            placeholder="+ 添加子任务，回车保存"
            size="small"
            @keyup.enter="addSubtask"
          />
        </div>
        <!-- 详情模式：纯文本行（无复选框/分隔线/编辑） -->
        <div v-else class="subtask-text-list">
          <div
            v-for="sub in task.subtasks"
            :key="sub.id"
            class="subtask-text-row"
            :class="{ done: sub.status === 'done' }"
          >{{ sub.title }}</div>
        </div>
      </div>

      <!-- 附件区（文件本体存资源平台，任务只存引用；点击文件名下载/预览） -->
      <div v-if="canEdit || task.attachments?.length" class="detail-section attach-section">
        <div class="section-label">
          附件<template v-if="task.attachments?.length">（{{ task.attachments.length }}）</template>
        </div>
        <div v-for="att in task.attachments" :key="att.resource_id" class="attach-row">
          <component :is="attachIcon(att)" :size="15" class="attach-icon" />
          <span class="attach-name" :title="att.name" @click="openAttachment(att)">{{ att.name }}</span>
          <span class="attach-size">{{ formatSize(att.size) }}</span>
          <Trash2
            v-if="canEdit"
            :size="13"
            class="attach-del"
            title="删除附件"
            @click="onRemoveAttachment(att)"
          />
        </div>
        <div v-if="canEdit" class="attach-add" @click="attachFileInput?.click()">
          <Paperclip :size="13" /> 添加附件
        </div>
        <input ref="attachFileInput" type="file" style="display: none" @change="onAttachFile" />
      </div>

        <!-- 关联用例（扩展区块） -->
        <div v-if="task.case_map_title" class="detail-section">
          <div class="section-label">关联用例</div>
          <div class="case-card" @click="goCase">
            <Link2 :size="16" style="flex-shrink: 0" />
            <div class="case-card-text">
              <div class="case-map-title">{{ task.case_map_title }}</div>
              <div v-if="task.case_node_text" class="case-node-text">{{ task.case_node_text }}</div>
            </div>
            <ChevronRight :size="14" class="case-jump" />
          </div>
        </div>
      </div>

      <!-- 富文本工具栏（对齐主流待办应用：备注聚焦或底栏「文本样式」开启时显示，悬浮于底栏上方） -->
      <div
        v-if="canEdit && (noteFocused || noteToolbarPinned)"
        class="note-toolbar"
        @mousedown.prevent
      >
        <!-- 放大/还原编辑区 -->
        <component :is="noteExpanded ? Minimize2 : Maximize2" :size="24" class="note-tool" :title="noteExpanded ? '还原' : '放大编辑'" @click="toggleNoteExpand" />
        <span class="note-toolbar-divider" />
        <!-- 标题大小下拉（对齐主流待办应用 H 按钮：正文 / H1 / H2 / H3） -->
        <span class="note-tool-wrap">
          <Heading :size="24" class="note-tool" title="标题大小" @click.stop="headingMenu = !headingMenu" />
          <div v-if="headingMenu" class="note-heading-menu">
            <div v-for="h in headingOptions" :key="h.tag" class="note-heading-item" :class="h.cls" @click="applyHeading(h.tag)">{{ h.label }}</div>
          </div>
        </span>
        <template v-for="(g, gi) in noteToolbar" :key="gi">
          <span class="note-toolbar-divider" />
          <template v-for="b in g">
            <!-- 高亮按钮对齐主流待办应用外观：A + 绿色底色 -->
            <span v-if="b.cmd === 'hilite'" :key="b.cmd" class="note-tool note-tool-hilite" :title="b.tip" @click="execNote(b)">A</span>
            <component
              :is="b.icon"
              v-else
              :key="b.cmd"
              :size="24"
              class="note-tool"
              :title="b.tip"
              @click="execNote(b)"
            />
          </template>
        </template>
        <span class="note-toolbar-divider" />
        <!-- 模板（对齐主流待办应用：使用/保存/删除笔记模板；popover teleport 避开工具栏 overflow 裁剪） -->
        <el-popover placement="bottom" trigger="click" :width="230" popper-class="note-template-pop">
          <template #reference>
            <LayoutTemplate :size="24" class="note-tool" title="模板" />
          </template>
          <div class="ntm-list">
            <div
              v-for="(t, i) in noteTemplates"
              :key="t.name"
              class="ntm-item"
              @click="applyNoteTemplate(t)"
            >
              {{ t.name }}
              <span class="ntm-del" title="删除模板" @click.stop="delNoteTemplate(i)">×</span>
            </div>
            <div v-if="!noteTemplates.length" class="ntm-empty">暂无模板</div>
            <div class="ntm-item ntm-save" @click="saveNoteTemplate">＋ 将当前内容保存为模板</div>
          </div>
        </el-popover>
        <!-- 插入摘要（对齐主流待办应用：笔记内摘要 icon） -->
        <ClipboardList :size="24" class="note-tool" title="插入摘要" @click="openSummaryDialog" />
      </div>

      <!-- 底栏：左侧所属清单（点击打开「移动到」弹窗，对齐主流待办应用），右侧图标按钮组（文本样式 / 专注 / 更多） -->
      <div class="detail-footer">
        <span
          class="footer-list"
          :class="{ clickable: canEdit }"
          :title="canEdit ? '移动到其它清单' : ''"
          @click="openMove"
        ><Inbox :size="14" style="vertical-align: -2px; margin-right: 4px" />{{ listName }}</span>
        <div class="footer-actions">
          <el-tooltip v-if="canEdit" content="文本样式" placement="top">
            <el-button text round size="small" :class="{ 'is-on': noteToolbarPinned }" @click="toggleNoteToolbar">
              <Type :size="15" />
            </el-button>
          </el-tooltip>
          <!-- 开始专注 ›：下拉选计时方式（对齐主流待办应用），自定义时长走 ⋯ 菜单 -->
          <el-dropdown v-auth="'task:run'" trigger="click" @command="(m) => startFocusWith(m === 'stopwatch' ? 0 : pomodoroStore.focusConfig.pomodoro_minutes || 25)">
            <el-button text round size="small"><Timer :size="15" /></el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="countdown">🍅 番茄计时 {{ pomodoroStore.focusConfig.pomodoro_minutes || 25 }} 分钟</el-dropdown-item>
                <el-dropdown-item command="stopwatch">⏱️ 正计时</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <!-- ⋯ 更多：笔记模式对齐主流待办应用笔记菜单（置顶/附件/摘要/专注｜存模板/副本/转换｜删除），任务模式仅删除 -->
          <el-dropdown trigger="click" @command="onFooterMore">
            <el-button text round size="small">
              <MoreVertical :size="15" />
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <template v-if="noteMode">
                  <el-dropdown-item command="pin">
                    <Pin :size="13" style="margin-right: 6px; vertical-align: -2px" />{{ task.is_pinned ? '取消置顶' : '置顶' }}
                  </el-dropdown-item>
                  <el-dropdown-item v-if="canEdit" command="attach">
                    <Paperclip :size="13" style="margin-right: 6px; vertical-align: -2px" />上传附件
                  </el-dropdown-item>
                  <el-dropdown-item v-if="canEdit" command="summary">
                    <ClipboardList :size="13" style="margin-right: 6px; vertical-align: -2px" />插入摘要
                  </el-dropdown-item>
                  <el-dropdown-item v-if="canEdit" v-auth="'task:run'" command="focus">
                    <Timer :size="13" style="margin-right: 6px; vertical-align: -2px" />开始专注
                  </el-dropdown-item>
                  <el-dropdown-item v-if="canEdit" command="saveTpl" divided>
                    <LayoutTemplate :size="13" style="margin-right: 6px; vertical-align: -2px" />保存为模板
                  </el-dropdown-item>
                  <el-dropdown-item v-if="canEdit" v-auth="'task:create'" command="dup">
                    <Copy :size="13" style="margin-right: 6px; vertical-align: -2px" />创建副本
                  </el-dropdown-item>
                  <el-dropdown-item command="toTask">
                    <CheckSquare :size="13" style="margin-right: 6px; vertical-align: -2px" />转换为任务
                  </el-dropdown-item>
                  <el-dropdown-item
                    v-if="canEdit && authStore.hasPerm('task:delete')"
                    command="delete"
                    divided
                    style="color: var(--el-color-danger)"
                  >
                    删除笔记
                  </el-dropdown-item>
                </template>
                <el-dropdown-item
                  v-else-if="canEdit && authStore.hasPerm('task:delete')"
                  command="delete"
                  style="color: var(--el-color-danger)"
                >
                  删除任务
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </div>

    <!-- 插入摘要弹窗（对齐主流待办应用：笔记内选范围 → 预览 → 插入光标处） -->
    <el-dialog v-model="summaryDialog" title="插入任务摘要" width="560px" append-to-body>
      <div class="nsd-bar">
        <el-select v-model="nsdRange" size="small" style="width: 120px" @change="loadNsd">
          <el-option v-for="o in NSD_RANGES" :key="o.value" :value="o.value" :label="o.label" />
        </el-select>
        <el-checkbox-group v-model="nsdShow" size="small" @change="loadNsd">
          <el-checkbox value="date">日期</el-checkbox>
          <el-checkbox value="list">清单</el-checkbox>
          <el-checkbox value="priority">优先级</el-checkbox>
        </el-checkbox-group>
      </div>
      <div v-loading="nsdLoading" class="nsd-preview">
        <template v-if="nsdResult">
          <h3 class="nsd-range">{{ nsdResult.range_label }}</h3>
          <div v-for="g in nsdResult.groups" :key="g.label" class="nsd-group">
            <div class="nsd-group-title">{{ g.label }}</div>
            <div v-for="(it, i) in g.items" :key="i" class="nsd-item">
              <span v-if="nsdShow.includes('date') && it.date_label" class="nsd-date">[{{ it.date_label }}]</span>{{ it.title }}
              <span v-if="nsdShow.includes('list')" class="nsd-list">（{{ it.list_name }}）</span>
            </div>
          </div>
          <el-empty v-if="!nsdResult.total" description="该时间段内没有任务" :image-size="60" />
        </template>
      </div>
      <template #footer>
        <el-button size="small" @click="summaryDialog = false">取消</el-button>
        <el-button size="small" type="primary" :disabled="!nsdResult || !nsdResult.total" @click="insertSummary">插入</el-button>
      </template>
    </el-dialog>
  </aside>
</template>

<script setup>
import { computed, reactive, ref, watch, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, X, Link2, MoreVertical, ChevronRight, Inbox, Timer, Flag, List, Calendar, AlarmClock, Trash2, Heading, Heading1, Heading2, Heading3, ListChecks, Minus, Tag, Bold, Copy, Italic, Underline, Strikethrough, ListOrdered, Code, Quote, Type, CheckSquare, Undo2, Redo2, Maximize2, Minimize2, Paperclip, FileText, Image as ImageIcon, Film, FileArchive, File as FileIcon, GripVertical, Pin, BookOpen, LayoutTemplate, ClipboardList, Repeat } from 'lucide-vue-next'
import DOMPurify from 'dompurify'
import dayjs from 'dayjs'
import { useRouter } from 'vue-router'
import { useTaskStore } from '@/stores/task'
import { useAuthStore } from '@/stores/auth'
import { usePomodoroStore } from '@/stores/pomodoro'
import * as taskApi from '@/api/task'
import TaskDatePicker from './TaskDatePicker.vue'
import { recomputeReminders } from './utils'

const router = useRouter()

const store = useTaskStore()
const authStore = useAuthStore()
const pomodoroStore = usePomodoroStore()
const task = computed(() => store.activeTaskDetail)
const newSubtask = ref('')
const subtaskInput = ref(null) // 「/」菜单选“子任务”时聚焦添加输入框

// 行内编辑草稿：el-input 只绑 :model-value（无 update:model-value 监听）时，组件会在每次输入后
// 用 props.modelValue 快照回弹原生值导致“打字无反应”，必须经本地 ref 中转，change 时落库
const titleDraft = ref('')
const noteDraft = ref('') // 备注 HTML（富文本编辑器内容快照）
const subtaskDrafts = ref({})

// ===== 备注富文本编辑器（对齐主流待办应用：工具栏 + HTML 落库，DOMPurify 消毒防 XSS） =====
const NOTE_PURIFY_OPTS = {
  ALLOWED_TAGS: ['h1', 'h2', 'h3', 'p', 'br', 'div', 'b', 'strong', 'i', 'em', 'u', 's', 'strike', 'span', 'font', 'ul', 'ol', 'li', 'a', 'code', 'blockquote', 'input', 'hr'],
  ALLOWED_ATTR: ['href', 'target', 'rel', 'style', 'color', 'face', 'type', 'checked', 'disabled', 'class'],
}
const noteEl = ref(null)
const noteFocused = ref(false)
const noteToolbarPinned = ref(false) // 底栏「A 文本样式」开关：固定显示工具栏
const noteExpanded = ref(false) // ⤢ 放大编辑：详情栏全宽

function toggleNoteExpand() {
  noteExpanded.value = !noteExpanded.value
  noteEl.value?.focus()
}

// 标题大小下拉（对齐主流待办应用 H 按钮：正文 / 标题 1~3）
const headingMenu = ref(false)
const headingOptions = [
  { tag: 'p', label: '正文', cls: 'is-body' },
  { tag: 'h1', label: '标题 1', cls: 'is-h1' },
  { tag: 'h2', label: '标题 2', cls: 'is-h2' },
  { tag: 'h3', label: '标题 3', cls: 'is-h3' },
]
function applyHeading(tag) {
  headingMenu.value = false
  noteEl.value?.focus()
  const current = document.queryCommandValue('formatBlock')
  document.execCommand('formatBlock', false, current === tag ? 'p' : tag)
  onNoteInput()
}

function escapeHtml(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}
// 旧数据是纯文本：含标签按 HTML 处理（消毒），否则转义后换行转 <br>
function noteToHtml(note) {
  if (!note) return ''
  if (/<\/?[a-z][\s\S]*>/i.test(note)) return DOMPurify.sanitize(note, NOTE_PURIFY_OPTS)
  return escapeHtml(note).replace(/\n/g, '<br>')
}
function setNoteHtml(html) {
  noteDraft.value = html
  if (noteEl.value) noteEl.value.innerHTML = html
}
function onNoteInput() {
  noteDraft.value = noteEl.value?.innerHTML || ''
  // “/”菜单的查询词更新放 input 事件：IME 中文在 compositionend 才提交，keyup 读不到
  if (slash.open) updateSlashQuery()
}
// 编辑器失焦前保存选区：模板/摘要插入时恢复到原光标处（对齐主流待办应用：点弹层项在原光标处插入）
let savedNoteRange = null
function saveNoteSelection() {
  const sel = window.getSelection()
  if (sel?.rangeCount && noteEl.value?.contains(sel.getRangeAt(0).commonAncestorContainer)) {
    savedNoteRange = sel.getRangeAt(0).cloneRange()
  }
}
function insertNoteHtml(html) {
  noteEl.value?.focus()
  const sel = window.getSelection()
  if (savedNoteRange && noteEl.value?.contains(savedNoteRange.commonAncestorContainer)) {
    sel.removeAllRanges()
    sel.addRange(savedNoteRange)
  }
  savedNoteRange = null
  document.execCommand('insertHTML', false, html)
  onNoteInput()
}
function onNoteBlur(e) {
  // 焦点移到编辑器内部控件（待办 checkbox）不算失焦，保持工具栏与内容
  if (e?.relatedTarget && noteEl.value?.contains(e.relatedTarget)) return
  // 焦点移向模板/摘要等笔记辅助弹层时，保留选区与工具栏（点击弹层项要在原光标处插入）
  if (e?.relatedTarget?.closest?.('.note-template-pop, .el-overlay, .el-popper')) return
  noteFocused.value = false
  saveNoteSelection()
  headingMenu.value = false
  slash.open = false
  if (!noteEl.value) return
  const text = noteEl.value.textContent.trim()
  if (!text) noteEl.value.innerHTML = '' // 清空残留 <br>，让 placeholder 生效
  const clean = DOMPurify.sanitize(noteEl.value.innerHTML, NOTE_PURIFY_OPTS)
  if (noteEl.value.innerHTML !== clean) noteEl.value.innerHTML = clean
  noteDraft.value = clean
  // 与旧值同形态比较（旧值可能是纯文本）
  const prev = task.value?.note || ''
  if (clean !== prev && clean !== noteToHtml(prev)) save({ note: clean || null })
}
function toggleNoteToolbar() {
  noteToolbarPinned.value = !noteToolbarPinned.value
  if (noteToolbarPinned.value) noteEl.value?.focus()
}
function execNoteBlock(tag) {
  const current = document.queryCommandValue('formatBlock')
  document.execCommand('formatBlock', false, current === tag ? 'p' : tag)
}
// 待办列表（对齐主流待办应用 ☑）：插入可勾选的 checkbox 行
function execNoteChecklist() {
  document.execCommand(
    'insertHTML',
    false,
    '<ul class="note-checklist"><li><input type="checkbox" />&nbsp;</li></ul><p><br></p>'
  )
}
// checkbox 的勾选态只存在于 DOM property，不同步进 innerHTML；点击时写回 attribute 以便持久化
function onNoteClick(e) {
  if (e.target.matches('input[type="checkbox"]')) {
    e.target.toggleAttribute('checked', e.target.checked)
    onNoteInput()
  }
}
function execNoteLink() {
  const url = window.prompt('链接地址', 'https://')
  if (url && url !== 'https://') document.execCommand('createLink', false, url)
}

// ===== “/” 快捷插入菜单（对齐主流待办应用：标题/无序列表/待办列表/子任务） =====
const slash = reactive({ open: false, query: '', index: 0, left: 0, top: 0, mark: null })
// 对齐主流待办应用「/」菜单：段落样式 + 检查项/引用/分割线 + 子任务/标签/附件
const SLASH_ITEMS = [
  { key: 'h1', label: '一级标题', icon: Heading1 },
  { key: 'h2', label: '二级标题', icon: Heading2 },
  { key: 'h3', label: '三级标题', icon: Heading3 },
  { key: 'ul', label: '无序列表', icon: List },
  { key: 'ol', label: '有序列表', icon: ListOrdered },
  { key: 'todo', label: '检查项', icon: CheckSquare },
  { key: 'quote', label: '引用', icon: Quote },
  { key: 'hr', label: '水平分割线', icon: Minus },
  { key: 'sub', label: '子任务', icon: ListChecks },
  { key: 'tag', label: '标签', icon: Tag },
  { key: 'attach', label: '附件', icon: Paperclip },
]
const slashItems = computed(() =>
  SLASH_ITEMS.filter((i) => !slash.query || i.label.includes(slash.query))
)

function onNoteKeydown(e) {
  if (!slash.open) return
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    if (slashItems.value.length) slash.index = (slash.index + 1) % slashItems.value.length
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    if (slashItems.value.length) slash.index = (slash.index - 1 + slashItems.value.length) % slashItems.value.length
  } else if (e.key === 'Enter') {
    e.preventDefault()
    const it = slashItems.value[slash.index]
    if (it) applySlash(it)
    else slash.open = false
  } else if (e.key === 'Escape') {
    e.preventDefault()
    slash.open = false
  }
}

function onNoteKeyup(e) {
  if (e.key === '/' && !slash.open && canEdit.value) {
    openSlash()
    return
  }
  // 导航键 keydown 已处理并 preventDefault：keyup 不再重算查询词（否则 index 被重置回 0，上下键失效）
  if (['ArrowDown', 'ArrowUp', 'Enter', 'Escape'].includes(e.key)) return
  if (slash.open) updateSlashQuery()
}

function openSlash() {
  const sel = window.getSelection()
  const node = sel.rangeCount ? sel.anchorNode : null
  if (!node || node.nodeType !== 3 || !noteEl.value?.contains(node)) return
  const rect = sel.getRangeAt(0).getBoundingClientRect()
  slash.left = rect.left
  slash.top = rect.bottom + 6
  // 标记 “/” 后的位置（文本节点+偏移），查询词 = 标记到光标的文本；节点变了即关闭
  slash.mark = { node, offset: sel.anchorOffset }
  slash.query = ''
  slash.index = 0
  slash.open = true
}

// 查询词 = “/”标记到光标的文本；光标离开该文本节点或输入空白/退格过标记则关闭
function updateSlashQuery() {
  const sel = window.getSelection()
  const m = slash.mark
  if (!m || !sel.rangeCount || sel.anchorNode !== m.node || !noteEl.value?.contains(m.node)
    || sel.anchorOffset < m.offset) {
    slash.open = false
    return
  }
  const q = m.node.textContent.slice(m.offset, sel.anchorOffset)
  if (/[\s/]/.test(q)) {
    slash.open = false
    return
  }
  slash.query = q
  slash.index = 0
}

function applySlash(it) {
  // 先删掉已输入的 “/查询词”（标记前一字符是 “/”），并把光标重设到删除点
  // （deleteContents 后原选区偏移失效，不重设会让后续 formatBlock 落空）
  const sel = window.getSelection()
  const m = slash.mark
  if (m && sel.rangeCount && sel.anchorNode === m.node && noteEl.value?.contains(m.node)) {
    const r = document.createRange()
    r.setStart(m.node, Math.max(0, m.offset - 1))
    r.setEnd(m.node, sel.anchorOffset)
    r.deleteContents()
    // 删光后编辑器无任何子节点时 Chrome 会静默拒绝 formatBlock：种 <br> 兜底
    if (!noteEl.value.innerHTML) noteEl.value.innerHTML = '<br>'
    r.collapse(true)
    sel.removeAllRanges()
    sel.addRange(r)
    // 删除可能使原节点脱离文档：选区不在编辑器内时重新锚到末尾
    if (!noteEl.value?.contains(sel.anchorNode)) {
      const r2 = document.createRange()
      r2.selectNodeContents(noteEl.value)
      r2.collapse(false)
      sel.removeAllRanges()
      sel.addRange(r2)
    }
  }
  slash.open = false
  // Enter/mousedown.prevent 路径焦点都在编辑器内，无需再 focus（focus 可能把光标重置到开头）
  if (it.key === 'h1' || it.key === 'h2' || it.key === 'h3') execNoteBlock(it.key)
  else if (it.key === 'ul') document.execCommand('insertUnorderedList')
  else if (it.key === 'ol') document.execCommand('insertOrderedList')
  else if (it.key === 'todo') execNoteChecklist()
  else if (it.key === 'quote') execNoteBlock('blockquote')
  else if (it.key === 'hr') execNoteHr()
  else if (it.key === 'sub') subtaskInput.value?.focus()
  else if (it.key === 'tag') document.execCommand('insertText', false, '#') // 续输标签名（对齐主流待办应用 # 引用标签）
  else if (it.key === 'attach') attachFileInput.value?.click() // 选文件上传后入附件区
  onNoteInput()
}
// 水平分割线（对齐主流待办应用）：插入 hr 并在其后留一个空段落继续输入
function execNoteHr() {
  document.execCommand('insertHTML', false, '<hr><p><br></p>')
}
function execNoteCode() {
  const sel = window.getSelection()
  if (!sel.rangeCount) return
  const range = sel.getRangeAt(0)
  if (range.collapsed || !noteEl.value?.contains(range.commonAncestorContainer)) return
  const code = document.createElement('code')
  try {
    range.surroundContents(code)
  } catch {
    code.appendChild(range.extractContents())
    range.insertNode(code)
  }
  sel.removeAllRanges()
}
const noteToolbar = [
  [
    { cmd: 'bold', tip: '加粗', icon: Bold, run: () => document.execCommand('bold') },
    { cmd: 'hilite', tip: '高亮', icon: null, run: () => document.execCommand('hiliteColor', false, '#fdf0a0') },
    { cmd: 'checklist', tip: '待办列表', icon: CheckSquare, run: execNoteChecklist },
    { cmd: 'ul', tip: '无序列表', icon: List, run: () => document.execCommand('insertUnorderedList') },
    { cmd: 'ol', tip: '有序列表', icon: ListOrdered, run: () => document.execCommand('insertOrderedList') },
  ],
  [
    { cmd: 'italic', tip: '斜体', icon: Italic, run: () => document.execCommand('italic') },
    { cmd: 'underline', tip: '下划线', icon: Underline, run: () => document.execCommand('underline') },
    { cmd: 'strike', tip: '删除线', icon: Strikethrough, run: () => document.execCommand('strikeThrough') },
    { cmd: 'undo', tip: '撤销', icon: Undo2, run: () => document.execCommand('undo') },
    { cmd: 'redo', tip: '重做', icon: Redo2, run: () => document.execCommand('redo') },
  ],
  [
    { cmd: 'link', tip: '链接', icon: Link2, run: execNoteLink },
    { cmd: 'code', tip: '行内代码', icon: Code, run: execNoteCode },
    { cmd: 'quote', tip: '引用', icon: Quote, run: () => execNoteBlock('blockquote') },
  ],
]
function execNote(b) {
  noteEl.value?.focus()
  b.run()
  onNoteInput()
}

// ---------- 笔记模板（对齐主流待办应用：使用/保存/删除模板；insertNoteHtml 见上，失焦前已保存选区） ----------
const noteTemplates = computed(() => store.settings?.note_templates || [])
function applyNoteTemplate(t) {
  insertNoteHtml(`${t.content_html}<p><br></p>`)
  ElMessage.success(`已插入模板「${t.name}」`)
}
async function saveNoteTemplate() {
  const html = noteEl.value?.innerHTML || ''
  if (!html.replace(/<[^>]+>/g, '').trim()) {
    ElMessage.warning('当前内容为空，无法保存模板')
    return
  }
  try {
    const { value } = await ElMessageBox.prompt('模板名称', '保存为笔记模板', {
      inputPattern: /\S+/,
      inputErrorMessage: '请输入名称',
    })
    await store.saveSettings({ note_templates: [...noteTemplates.value, { name: value.trim(), content_html: html }] })
    ElMessage.success('模板已保存')
  } catch { /* 取消 */ }
}
async function delNoteTemplate(i) {
  await store.saveSettings({ note_templates: noteTemplates.value.filter((_, idx) => idx !== i) })
}

// ---------- 插入摘要（对齐主流待办应用：笔记内摘要 icon → 选范围 → 插入光标处） ----------
const summaryDialog = ref(false)
const nsdRange = ref('this_week')
const nsdShow = ref(['date'])
const nsdResult = ref(null)
const nsdLoading = ref(false)
const NSD_RANGES = [
  { value: 'today', label: '今天' },
  { value: 'yesterday', label: '昨天' },
  { value: 'this_week', label: '本周' },
  { value: 'last_week', label: '上周' },
  { value: 'this_month', label: '本月' },
]
async function loadNsd() {
  nsdLoading.value = true
  try {
    nsdResult.value = await taskApi.previewSummary({
      range: nsdRange.value,
      show: nsdShow.value,
      group_by: 'status',
      statuses: ['done', 'todo'],
      tz_offset_minutes: -new Date().getTimezoneOffset(),
    })
  } finally {
    nsdLoading.value = false
  }
}
function openSummaryDialog() {
  headingMenu.value = false
  summaryDialog.value = true
  loadNsd()
}
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
function insertSummary() {
  if (!nsdResult.value) return
  insertNoteHtml(`${mdToHtml(nsdResult.value.markdown)}<p><br></p>`)
  summaryDialog.value = false
  ElMessage.success('摘要已插入')
}

watch(
  () => task.value?.id,
  () => {
    titleDraft.value = task.value?.title || ''
    noteToolbarPinned.value = false
    noteExpanded.value = false
    headingMenu.value = false
    nextTick(() => setNoteHtml(noteToHtml(task.value?.note)))
    subtaskDrafts.value = Object.fromEntries((task.value?.subtasks || []).map((s) => [s.id, s.title]))
  },
  { immediate: true }
)
// 外部变更（如保存后刷新详情）回填草稿；进行中的子任务输入不受新增/删除行影响
watch(() => task.value?.title, (v) => { titleDraft.value = v || '' })
// 编辑器聚焦时不回填，避免打断输入/丢光标
watch(() => task.value?.note, (v) => { if (!noteFocused.value) setNoteHtml(noteToHtml(v)) })
watch(
  () => task.value?.subtasks,
  (subs) => {
    const map = {}
    for (const s of subs || []) map[s.id] = subtaskDrafts.value[s.id] ?? s.title
    subtaskDrafts.value = map
  }
)

// 底栏所属清单名（list_id=null 即收集箱）
const listName = computed(
  () => store.lists.find((l) => l.id === task.value?.list_id)?.name || '收集箱'
)

// 底栏「清单」chip：打开「移动到」弹窗（对齐主流待办应用）
function openMove() {
  if (canEdit.value && task.value) store.openMoveDialog(task.value.id)
}

// 共享任务：任务创建者或清单 editor 可编辑；viewer 只读（保留标题 :disabled 与表单遮罩）
const listRole = computed(() => {
  const l = store.lists.find((i) => i.id === task.value?.list_id)
  if (!l) return null
  if (l.owner === authStore.userInfo?.username) return 'owner'
  return l.members?.find((m) => m.username === authStore.userInfo?.username)?.role || null
})
const canEdit = computed(() => {
  if (task.value?.owner === authStore.userInfo?.username) return true
  return listRole.value === 'owner' || listRole.value === 'editor'
})

async function startFocus() {
  let minutes
  try {
    const { value } = await ElMessageBox.prompt('专注时长（分钟），常用 15 / 25 / 45', '开始专注', {
      inputValue: '25',
      inputPattern: /^\d+$/,
      inputErrorMessage: '请输入数字分钟数',
    })
    minutes = +value
  } catch {
    return // 用户取消
  }
  if (!minutes) return
  startFocusWith(minutes)
}

// 头部 ⏱ 下拉：番茄计时（默认时长）/ 正计时
async function startFocusWith(minutes) {
  try {
    await pomodoroStore.start(task.value.id, minutes)
    pomodoroStore.openPanel()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail?.message || '开始失败')
  }
}

function save(data) {
  if (!task.value) return
  store.updateTask(task.value.id, data)
}

function onMoreCmd(cmd) {
  if (!task.value) return
  if (cmd === 'pin') {
    store.updateTask(task.value.id, { is_pinned: !task.value.is_pinned })
  } else if (cmd === 'toNote') {
    store.updateTask(task.value.id, { is_note: true }).then(() => ElMessage.success('已转换为笔记'))
  } else if (cmd === 'toTask') {
    store.updateTask(task.value.id, { is_note: false }).then(() => ElMessage.success('已转换为任务'))
  }
}

// 笔记模式：无完成概念/无优先级/无子任务（对齐主流待办应用笔记）
const noteMode = computed(() => !!task.value?.is_note)

// 顶栏优先级旗帜：颜色随当前优先级，点击下拉 PATCH（置顶能力在右键菜单）
const priorityOptions = [
  { value: 3, label: '高优先级', color: '#f56c6c' },
  { value: 2, label: '中优先级', color: '#e6a23c' },
  { value: 1, label: '低优先级', color: '#409eff' },
  { value: 0, label: '无优先级', color: '#9ca3af' },
]
const priorityColor = computed(() => priorityOptions.find((o) => o.value === (task.value?.priority || 0))?.color)
const priorityTip = computed(() => `优先级：${priorityOptions.find((o) => o.value === (task.value?.priority || 0))?.label}`)

function setPriority(priority) {
  if (!task.value) return
  store.updateTask(task.value.id, { priority })
}

// 子任务展示模式：检查事项（默认）⇄ 详情（纯文本）；切任务时重置
const subtaskMode = ref('checklist')
watch(
  () => task.value?.id,
  () => { subtaskMode.value = 'checklist' }
)

// 子任务行内改名：store 无子任务改名 action，走 taskApi 后刷新详情
async function onSubtaskTitle(sub, title) {
  const v = (title || '').trim()
  if (!v || v === sub.title) return
  await taskApi.updateTask(sub.id, { title: v })
  await store.refreshDetail()
}

// 检查事项行 input 引用（Enter 新建后聚焦新行）
const subInputRefs = {}
function setSubInputRef(id, el) {
  if (el) subInputRefs[id] = el
  else delete subInputRefs[id]
}
const blankSubId = ref(null) // 换行新建的空行 id：失焦仍空则删除（对齐主流待办应用）

// 换行即创建一条新检查事项（对齐主流待办应用）：先提交当前行，再插入其后并聚焦
async function onSubtaskEnter(sub) {
  if (!canEdit.value || !task.value) return
  const v = (subtaskDrafts.value[sub.id] || '').trim()
  if (v && v !== sub.title) await taskApi.updateTask(sub.id, { title: v })
  const created = await taskApi.createTask({ title: '', parent_id: task.value.id })
  await taskApi.sortTask(created.id, { after_task_id: sub.id })
  blankSubId.value = created.id
  await store.refreshDetail()
  nextTick(() => subInputRefs[created.id]?.focus())
}
// 换行新建的空行失焦仍未填内容 → 删除，不留空检查项
async function onSubtaskBlur(sub) {
  if (blankSubId.value === sub.id && !(subtaskDrafts.value[sub.id] || '').trim()) {
    blankSubId.value = null
    await taskApi.deleteTask(sub.id)
    await store.refreshDetail()
  }
}

// 检查事项拖动排序（对齐主流待办应用右侧「≡」）：拖到目标行上半=插其前，下半=插其后
const dragSubId = ref(null)
const subDropHint = ref(null) // { id, pos: 'before' | 'after' }
function onSubDragStart(sub, e) {
  if (!canEdit.value) {
    e.preventDefault()
    return
  }
  dragSubId.value = sub.id
  e.dataTransfer.effectAllowed = 'move'
}
function onSubDragEnd() {
  dragSubId.value = null
  subDropHint.value = null
}
function onSubDragOver(sub, e) {
  if (!dragSubId.value || dragSubId.value === sub.id) {
    subDropHint.value = null
    return
  }
  const rect = e.currentTarget.getBoundingClientRect()
  subDropHint.value = { id: sub.id, pos: e.clientY < rect.top + rect.height / 2 ? 'before' : 'after' }
}
function onSubDragLeave(sub) {
  if (subDropHint.value?.id === sub.id) subDropHint.value = null
}
async function onSubDrop(sub) {
  const dragged = dragSubId.value
  const hint = subDropHint.value
  onSubDragEnd()
  if (!dragged || dragged === sub.id || !hint) return
  await taskApi.sortTask(dragged, hint.pos === 'before' ? { before_task_id: sub.id } : { after_task_id: sub.id })
  await store.refreshDetail()
}

// 子任务时间/提醒（行尾闹钟图标，复用日期弹层）：与 onDatePick 同逻辑，写子任务后刷新详情
async function onSubtaskDate(sub, { due_at, all_day, start_at = null, reminders, persistent_reminder }) {
  const data = { due_at, all_day, start_at }
  if (reminders !== undefined) data.reminders = recomputeReminders(reminders, due_at)
  if (persistent_reminder !== undefined) data.persistent_reminder = persistent_reminder
  await taskApi.updateTask(sub.id, data)
  await store.refreshDetail()
}

async function addSubtask() {
  const title = newSubtask.value.trim()
  if (!title || !task.value) return
  await store.createSubtask(task.value.id, title)
  newSubtask.value = ''
}

// 日期选择弹层（TaskDatePicker）提交：{ due_at, all_day, start_at, reminders, persistent_reminder, recurrence }
// 改日期时同步重算相对提醒的绝对 at（§5.3/§5.4：后端只存绝对时间，相对提醒按 offset_minutes 漂移）
function onDatePick({ due_at, all_day, start_at = null, reminders, persistent_reminder, recurrence }) {
  const data = { due_at, all_day, start_at }
  if (reminders !== undefined) data.reminders = recomputeReminders(reminders, due_at)
  if (persistent_reminder !== undefined) data.persistent_reminder = persistent_reminder
  if (recurrence !== undefined) data.recurrence = recurrence
  save(data)
}

function goCase() {
  if (task.value?.case_map_id) {
    router.push(`/case/editor/${task.value.case_map_id}`)
  }
}

// ===== 附件（文件本体存资源平台，任务只存引用；url 为资源平台公开地址） =====
const attachFileInput = ref(null)

function attachIcon(att) {
  const ct = att.content_type || ''
  const ext = (att.name || '').split('.').pop().toLowerCase()
  if (ct.startsWith('image/')) return ImageIcon
  if (ct.startsWith('video/')) return Film
  if (['zip', 'rar', '7z', 'tar', 'gz'].includes(ext)) return FileArchive
  if (ct.startsWith('text/') || ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'md'].includes(ext)) return FileText
  return FileIcon
}
function formatSize(bytes) {
  if (bytes == null) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`
}
function openAttachment(att) {
  const url = att.url || taskApi.attachmentUrl(att.resource_id)
  window.open(url, '_blank')
}
async function onAttachFile(e) {
  const file = e.target.files?.[0]
  e.target.value = '' // 允许重复选同一文件
  if (!file || !task.value) return
  try {
    await taskApi.uploadAttachment(task.value.id, file)
    await store.refreshDetail()
    ElMessage.success('附件已上传')
  } catch {
    // request 拦截器已提示
  }
}
async function onRemoveAttachment(att) {
  try {
    await taskApi.removeAttachment(task.value.id, att.resource_id)
    await store.refreshDetail()
    ElMessage.success('附件已删除')
  } catch {
    // request 拦截器已提示
  }
}

// 底栏 ⋯ 更多（笔记模式对齐主流待办应用笔记菜单：置顶/附件/摘要/专注｜存模板/副本/转换｜删除；任务模式仅删除）
function onFooterMore(c) {
  if (c === 'delete') return onDelete()
  if (c === 'pin' || c === 'toTask' || c === 'toNote') return onMoreCmd(c)
  if (c === 'attach') return attachFileInput.value?.click()
  if (c === 'summary') return openSummaryDialog()
  if (c === 'focus') return startFocus()
  if (c === 'saveTpl') return saveNoteTemplate()
  if (c === 'dup') return duplicateTask()
}

// 创建副本（对齐主流待办应用：复制标题/备注/清单/优先级/标签/日期，不含子任务/提醒/重复；笔记副本保持笔记）
async function duplicateTask() {
  const t = task.value
  if (!t) return
  await store.createTask({
    title: t.title,
    note: t.note || null,
    list_id: t.list_id ?? null,
    priority: t.priority || 0,
    tags: [...(t.tags || [])],
    due_at: t.due_at || null,
    all_day: t.all_day ?? true,
    ...(t.is_note ? { is_note: true } : {}),
  })
  ElMessage.success('已创建副本')
}

function onDelete() {
  ElMessageBox.confirm('确定删除该任务？子任务将一并删除。', '删除任务', {
    type: 'warning',
    confirmButtonText: '删除',
    cancelButtonText: '取消',
  }).then(() => store.deleteTask(task.value.id)).catch(() => {})
}
</script>

<style scoped>
.task-detail-panel {
  position: relative;
  width: 35%;
  min-width: 420px;
  flex-shrink: 0;
  height: 100%;
  /* 滚动只发生在内层 .detail-body（单一滚动容器，防双滚动条）；仅 overlay-board 例外见下 */
  overflow: hidden;
  background: #fff;
  border-left: 1px solid var(--ss-border);
  padding: 16px;
}
/* 时间线视图下详情抽屉改为右侧悬浮覆盖，避免挤压时间线轨道 */
.task-detail-panel.overlay-timeline {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  height: auto;
  z-index: 30;
  box-shadow: -6px 0 18px rgba(0, 0, 0, 0.1);
}
/* 看板视图下详情改为居中悬浮卡片（对齐主流待办应用看板点卡片效果），点遮罩/✕ 关闭 */
.task-detail-panel.overlay-board {
  position: absolute;
  left: 50%;
  top: 50%;
  transform: translate(-50%, -50%);
  width: 600px;
  min-width: 0;
  max-width: 90%;
  height: auto;
  max-height: 85%;
  /* 居中卡片高度随内容：超高时由面板自身滚动（内层 flex:1 此时无高度约束，天然单一滚动条） */
  overflow-y: auto;
  z-index: 31;
  border-left: none;
  border-radius: 16px;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.16);
}
.panel-close {
  cursor: pointer;
  color: var(--ss-text-muted);
  font-size: 16px;
  padding: 4px;
  border-radius: 4px;
  flex-shrink: 0;
}
.panel-close:hover {
  background: var(--ss-bg);
  color: var(--ss-text);
}
.task-detail {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.detail-header {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 40px;
  padding-bottom: 8px;
  margin-bottom: 8px;
  border-bottom: 1px solid var(--ss-border);
}
/* 日期纯文字按钮：Calendar 图标 + 主色文字，无按钮框（对齐主流待办应用） */
.header-date-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: var(--ss-primary);
  padding: 4px 6px;
  border-radius: var(--ss-radius-sm);
  cursor: pointer;
  white-space: nowrap;
  line-height: 1;
}
.header-date-btn:hover {
  background: var(--ss-bg);
}
.header-date-btn.disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.header-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}
.flag-btn {
  display: flex;
  align-items: center;
  flex-shrink: 0;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
  line-height: 1;
}
.flag-btn:hover {
  background: var(--ss-bg);
}
.flag-btn.disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
/* 放大编辑模式：详情栏占满右侧（对齐主流待办应用 ⤢） */
.task-detail-panel.note-expanded {
  width: 100%;
  min-width: 0;
}
.check-dot {
  width: 20px;
  height: 20px;
  border: 2px solid var(--ss-text-muted);
  /* 对齐主流待办应用：清单/详情 = 正圆勾选框（四象限才是圆角方块） */
  border-radius: 50%;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
}
.check-dot.checked {
  background: var(--ss-primary);
  border-color: var(--ss-primary);
}
.check-dot.disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.check-dot.small {
  width: 16px;
  height: 16px;
}
/* 标题行：纯文本模样（无底色/底线），点击即编辑，@change 保存 */
.title-row {
  display: flex;
  align-items: flex-start;
  gap: 4px;
  margin-bottom: 4px;
}
.title-input {
  flex: 1;
}
/* 元信息行：清单 chip + 标签选择器（无边框，对齐主流待办应用详情标题下方的属性区） */
.meta-row {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}
.meta-nextdue {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: var(--el-color-primary);
  background: #eef1fe;
  border-radius: 999px;
  padding: 2px 10px;
  flex-shrink: 0;
}
.meta-list {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  color: var(--ss-text-muted);
  background: var(--ss-bg);
  border-radius: 10px;
  padding: 2px 8px;
  flex-shrink: 0;
}
.meta-list.clickable {
  cursor: pointer;
}
.meta-list.clickable:hover {
  color: var(--ss-primary);
}
.meta-tags {
  flex: 1;
  min-width: 120px;
}
.meta-tags :deep(.el-select__wrapper) {
  min-height: 24px;
  padding: 0 4px;
  background: transparent;
  box-shadow: none;
}
.meta-tags :deep(.el-select__wrapper.is-hovering),
.meta-tags :deep(.el-select__wrapper.is-focused) {
  box-shadow: none;
}
.meta-tags :deep(.el-select__placeholder) {
  font-size: 12px;
  color: var(--ss-text-muted);
}
.mode-toggle {
  flex-shrink: 0;
  margin-top: 8px;
  color: var(--ss-text-muted);
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
}
.mode-toggle:hover {
  background: var(--ss-bg);
  color: var(--ss-primary);
}
.title-input :deep(.el-input__wrapper) {
  background: transparent;
  box-shadow: none;
  padding: 4px 8px;
  border-radius: var(--ss-radius-sm);
  cursor: text;
}
.title-input :deep(.el-input__inner) {
  font-size: 18px;
  font-weight: 700;
  color: var(--ss-text);
}
.title-input.done :deep(.el-input__inner) {
  text-decoration: line-through;
  color: var(--ss-text-muted);
}
.detail-body {
  flex: 1;
  /* min-height:0：flex 子项默认可收缩到下限=内容高，会顶破外层致双滚动条；归零后由本容器独立滚动 */
  min-height: 0;
  overflow-y: auto;
  padding-top: 4px;
}
.detail-section {
  margin-bottom: 16px;
}
.section-label {
  font-size: 12px;
  color: var(--ss-text-muted);
  margin-bottom: 6px;
}
/* 附件区（对齐主流待办应用附件列表：图标 + 文件名 + 大小，hover 显删除） */
.attach-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 13px;
}
.attach-icon {
  color: var(--ss-text-muted);
  flex-shrink: 0;
}
.attach-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: pointer;
}
.attach-name:hover {
  color: var(--ss-primary);
}
.attach-size {
  font-size: 12px;
  color: var(--ss-text-muted);
  flex-shrink: 0;
}
.attach-del {
  color: var(--ss-text-muted);
  cursor: pointer;
  flex-shrink: 0;
  opacity: 0;
}
.attach-row:hover .attach-del {
  opacity: 1;
}
.attach-del:hover {
  color: var(--el-color-danger);
}
.attach-add {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
  font-size: 12px;
  color: var(--ss-text-muted);
  cursor: pointer;
}
.attach-add:hover {
  color: var(--ss-primary);
}
/* 备注：富文本编辑器（对齐主流待办应用），无框无底像正文；placeholder 由 :empty::before 提供 */
.note-editor {
  min-height: 26px;
  margin-bottom: 12px;
  font-size: 14px;
  line-height: 1.6;
  color: var(--ss-text);
  outline: none;
  white-space: pre-wrap;
  word-break: break-word;
  cursor: text;
}
.note-editor:empty::before {
  content: attr(data-placeholder);
  color: var(--ss-text-muted);
}
.note-editor.disabled {
  cursor: default;
  opacity: 0.7;
}
.note-editor :deep(h1) {
  margin: 10px 0 6px;
  font-size: 22px;
}
.note-editor :deep(h2) {
  margin: 8px 0 5px;
  font-size: 19px;
}
.note-editor :deep(h3) {
  margin: 8px 0 4px;
  font-size: 16px;
}
/* 待办列表（☑）：checkbox 与文本同行 */
.note-editor :deep(ul.note-checklist) {
  list-style: none;
  padding-left: 2px;
  margin: 4px 0;
}
.note-editor :deep(ul.note-checklist li) {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.note-editor :deep(ul.note-checklist input[type="checkbox"]) {
  width: 14px;
  height: 14px;
  accent-color: var(--ss-primary);
  cursor: pointer;
  transform: translateY(2px);
}
.note-editor :deep(ul),
.note-editor :deep(ol) {
  margin: 4px 0;
  padding-left: 20px;
}
.note-editor :deep(blockquote) {
  margin: 6px 0;
  padding: 2px 10px;
  border-left: 3px solid var(--ss-border);
  color: var(--ss-text-muted);
}
.note-editor :deep(code) {
  background: var(--ss-bg);
  border: 1px solid var(--ss-border);
  border-radius: 4px;
  padding: 0 4px;
  font-family: Consolas, Monaco, monospace;
  font-size: 13px;
}
.note-editor :deep(a) {
  color: var(--ss-primary);
}
/* 富文本工具栏：底栏上方悬浮白色胶囊（对齐主流待办应用），分组竖线分隔 */
.note-toolbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 4px 0 8px;
  padding: 8px 14px;
  background: #fff;
  border: 1px solid var(--ss-border);
  border-radius: 8px;
  box-shadow: 0 4px 16px rgb(0 0 0 / 8%);
  /* 图标放大后总宽可能超过详情栏宽度：横向滑动，隐藏滚动条 */
  overflow-x: auto;
  scrollbar-width: none;
}
.note-toolbar::-webkit-scrollbar {
  display: none;
}
.note-tool {
  color: var(--ss-text);
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
  flex-shrink: 0;
}
.note-tool:hover {
  background: var(--ss-bg);
  color: var(--ss-primary);
}
.note-toolbar-divider {
  width: 1px;
  height: 24px;
  background: var(--ss-border);
  margin: 0 8px;
  flex-shrink: 0;
}
/* 标题大小下拉（H 按钮） */
.note-tool-wrap {
  position: relative;
  display: flex;
}
/* 笔记模板弹出层 */
.ntm-list {
  max-height: 260px;
  overflow-y: auto;
}
.ntm-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 13px;
  color: #444;
  padding: 7px 10px;
  border-radius: 6px;
  cursor: pointer;
}
.ntm-item:hover {
  background: var(--ss-bg);
}
.ntm-del {
  color: #c0c4cc;
  visibility: hidden;
}
.ntm-item:hover .ntm-del {
  visibility: visible;
}
.ntm-del:hover {
  color: #e64a3b;
}
.ntm-empty {
  font-size: 12px;
  color: #b0b0b0;
  padding: 6px 10px;
}
.ntm-save {
  color: var(--ss-primary);
  border-top: 1px solid var(--ss-border);
  border-radius: 0 0 6px 6px;
}
/* 插入摘要弹窗 */
.nsd-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}
.nsd-preview {
  min-height: 180px;
  max-height: 320px;
  overflow-y: auto;
  border: 1px solid var(--ss-border);
  border-radius: 8px;
  padding: 12px 16px;
}
.nsd-range {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 700;
}
.nsd-group {
  margin-bottom: 10px;
}
.nsd-group-title {
  font-weight: 600;
  font-size: 13px;
  margin-bottom: 4px;
}
.nsd-item {
  font-size: 13px;
  color: #444;
  padding: 2px 0;
}
.nsd-date {
  color: #999;
}
.nsd-list {
  color: #aaa;
  font-size: 12px;
}
.note-heading-menu {
  position: absolute;
  bottom: calc(100% + 8px);
  left: 50%;
  transform: translateX(-50%);
  background: #fff;
  border: 1px solid var(--ss-border);
  border-radius: 8px;
  box-shadow: 0 6px 24px rgb(0 0 0 / 12%);
  padding: 4px;
  min-width: 96px;
  z-index: 10;
}
.note-heading-item {
  padding: 5px 10px;
  border-radius: 5px;
  cursor: pointer;
  color: var(--ss-text);
  white-space: nowrap;
}
.note-heading-item:hover {
  background: var(--ss-bg);
}
.note-heading-item.is-body {
  font-size: 13px;
}
.note-heading-item.is-h1 {
  font-size: 18px;
  font-weight: 700;
}
.note-heading-item.is-h2 {
  font-size: 16px;
  font-weight: 700;
}
.note-heading-item.is-h3 {
  font-size: 14px;
  font-weight: 700;
}
/* 高亮按钮：A + 绿色底色（对齐主流待办应用外观） */
.note-tool-hilite {
  font-size: 19px;
  font-weight: 700;
  line-height: 24px;
  padding: 8px 10px;
  background: linear-gradient(to top, #a7f3d0 45%, transparent 45%);
}
.subtask-block {
  position: relative;
  margin-bottom: 12px;
  padding-bottom: 4px;
}
.subtask-progress {
  position: absolute;
  top: 0;
  right: 0;
  font-size: 12px;
  color: var(--ss-text-muted);
}
.subtask-list {
  width: 100%;
  display: flex;
  flex-direction: column;
}
.subtask-row {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 36px;
  border-bottom: 1px solid var(--ss-border);
}
/* 水平分割线（「/」菜单插入） */
.note-editor hr {
  border: none;
  border-top: 1px solid var(--ss-border);
  margin: 8px 0;
}

/* “/” 快捷插入菜单（对齐主流待办应用） */
.slash-menu {
  position: fixed;
  z-index: 3000;
  min-width: 150px;
  background: #fff;
  border-radius: 8px;
  box-shadow: 0 6px 24px rgb(0 0 0 / 14%);
  padding: 4px;
}
.slash-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  font-size: 13px;
  border-radius: 5px;
  cursor: pointer;
  color: var(--ss-text);
}
.slash-item.active,
.slash-item:hover {
  background: var(--ss-bg);
}
.slash-icon {
  color: var(--ss-text-muted);
  flex-shrink: 0;
}
.slash-empty {
  padding: 8px 10px;
  font-size: 12px;
  color: var(--ss-text-muted);
}

/* 子任务标题：无边框内联输入（与标题同风格，点击即编辑） */
.subtask-title-input {
  flex: 1;
}
.subtask-title-input :deep(.el-input__wrapper) {
  background: transparent;
  box-shadow: none;
  padding: 0;
}
.subtask-title-input :deep(.el-input__inner) {
  font-size: 14px;
  color: var(--ss-text);
  height: 24px;
}
.subtask-title-input.done :deep(.el-input__inner) {
  text-decoration: line-through;
  color: var(--ss-text-muted);
}
.subtask-del {
  visibility: hidden;
  color: var(--ss-text-muted);
  cursor: pointer;
  flex-shrink: 0;
}
.subtask-row:hover .subtask-del {
  visibility: visible;
}
/* 子任务勾选框：方形（对齐主流待办应用 checklist，主任务仍为圆点） */
.sub-check {
  width: 15px;
  height: 15px;
  border: 1.5px solid var(--ss-text-muted);
  border-radius: 3px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  cursor: pointer;
}
.sub-check.checked {
  background: var(--ss-primary);
  border-color: var(--ss-primary);
}
.sub-check.disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
/* 行尾操作：时间/提醒 + 删除，hover 行时显示（已设时间的闹钟常显主色） */
.subtask-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
  visibility: hidden;
}
.subtask-row:hover .subtask-actions,
.subtask-actions:has(.subtask-action-icon.active) {
  visibility: visible;
}
.subtask-action-icon {
  color: var(--ss-text-muted);
  cursor: pointer;
  display: block;
}
.subtask-action-icon:hover {
  color: var(--ss-primary);
}
.subtask-action-icon.active {
  color: var(--ss-primary);
}
/* 拖动排序：≡ 手柄 + 落点指示线 */
.sub-drag {
  cursor: grab;
}
.subtask-row.drop-before {
  box-shadow: inset 0 2px 0 var(--ss-primary);
}
.subtask-row.drop-after {
  box-shadow: inset 0 -2px 0 var(--ss-primary);
}
/* 详情模式：纯文本行（无复选框/分隔线） */
.subtask-text-row {
  font-size: 14px;
  line-height: 1.8;
  color: var(--ss-text);
}
.subtask-text-row.done {
  color: var(--ss-text-muted);
  text-decoration: line-through;
}
/* 「+ 添加子任务」输入框无边框化 */
.subtask-block > .subtask-list > .el-input :deep(.el-input__wrapper) {
  background: transparent;
  box-shadow: none;
  padding: 0;
  height: 36px;
}
.subtask-block > .subtask-list > .el-input :deep(.el-input__inner) {
  color: var(--ss-text);
}
.subtask-block > .subtask-list > .el-input :deep(.el-input__inner::placeholder) {
  color: var(--ss-text-muted);
}
.case-card {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px;
  border: 1px solid var(--ss-border);
  border-radius: var(--ss-radius-sm);
  cursor: pointer;
}
.case-card:hover {
  box-shadow: var(--ss-shadow);
}
.case-card-text {
  flex: 1;
  min-width: 0;
}
.case-map-title {
  font-size: 14px;
}
.case-node-text {
  font-size: 12px;
  color: var(--ss-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.case-jump {
  color: var(--ss-text-muted);
}
.detail-footer {
  margin-top: auto;
  border-top: 1px solid var(--ss-border);
  padding-top: 8px;
  min-height: 40px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.footer-list {
  font-size: 13px;
  color: var(--ss-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.footer-list.clickable {
  cursor: pointer;
  padding: 3px 6px;
  margin-left: -6px;
  border-radius: 5px;
}
.footer-list.clickable:hover {
  background: var(--ss-bg);
  color: var(--ss-text);
}
.footer-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}
.footer-actions .is-on {
  color: var(--ss-primary);
  background: var(--ss-bg);
}

</style>
