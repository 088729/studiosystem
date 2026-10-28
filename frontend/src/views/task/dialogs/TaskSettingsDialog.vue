<template>
  <el-dialog v-model="visible" width="780px" :show-close="false" class="settings-win">
    <div class="sw">
      <!-- 左：功能栏（对齐主流待办应用设置窗口；后续新设置项在此扩展） -->
      <aside class="sw-nav">
        <div class="sw-nav-title">设置</div>
        <div
          class="sw-nav-item"
          :class="{ active: nav === 'account' }"
          @click="nav = 'account'"
        >
          <CircleUserRound :size="15" class="sw-nav-icon" />账号
        </div>
        <div
          class="sw-nav-item"
          :class="{ active: nav === 'notify' }"
          @click="nav = 'notify'"
        >
          <Bell :size="15" class="sw-nav-icon" />提醒与通知
        </div>
        <div
          class="sw-nav-item"
          :class="{ active: nav === 'datetime' }"
          @click="nav = 'datetime'"
        >
          <CalendarClock :size="15" class="sw-nav-icon" />日期与时间
        </div>
        <div
          class="sw-nav-item"
          :class="{ active: nav === 'template' }"
          @click="nav = 'template'"
        >
          <LayoutTemplate :size="15" class="sw-nav-icon" />模板
        </div>
        <div
          class="sw-nav-item"
          :class="{ active: nav === 'more' }"
          @click="nav = 'more'"
        >
          <SlidersHorizontal :size="15" class="sw-nav-icon" />更多设置
        </div>
      </aside>

      <!-- 右：内容区 -->
      <section class="sw-main">
        <header class="sw-head">
          <template v-if="nav === 'more'">
            <span class="sw-head-title">
              任务默认值
              <el-tooltip content="新任务的默认属性；仅对之后创建的任务生效" placement="right">
                <CircleHelp :size="14" class="sw-help" />
              </el-tooltip>
            </span>
          </template>
          <span v-else-if="nav === 'notify'" class="sw-head-title">提醒与通知</span>
          <span v-else-if="nav === 'datetime'" class="sw-head-title">日期与时间</span>
          <span v-else-if="nav === 'template'" class="sw-head-title">笔记模板</span>
          <span v-else class="sw-head-title">账号</span>
          <X :size="16" class="sw-close" @click="visible = false" />
        </header>

        <!-- 账号 -->
        <div v-if="nav === 'account'" class="sw-account">
          <div class="sw-avatar">{{ avatarText }}</div>
          <div class="sw-account-name">{{ authStore.userInfo?.nickname || authStore.userInfo?.username }}</div>
        </div>

        <!-- 提醒与通知（对齐主流待办应用设置-提醒与通知）：分块浅灰卡片 -->
        <div v-else-if="nav === 'notify'" class="ts-rows">
          <div class="ts-group">
          <div class="ts-row ts-row-col">
            <div class="ts-row-main">
              <span class="ts-label">每日提醒</span>
              <span class="ts-desc">每天在固定时间提醒你今天的任务</span>
            </div>
            <el-switch :model-value="form.daily_reminder_enabled" @change="onSwitch('daily_reminder_enabled', $event)" />
          </div>
          <div class="ts-row">
            <span class="ts-label">每日提醒时间</span>
            <el-popover
              v-model:visible="popOpen.daily_reminder_time"
              placement="bottom-end"
              :width="240"
              trigger="click"
              popper-class="ts-pop"
              @show="pendingDailyTime = form.daily_reminder_time"
            >
              <template #reference>
                <span class="ts-value">
                  {{ form.daily_reminder_time }}
                  <ChevronsUpDown :size="13" class="ts-value-icon" />
                </span>
              </template>
              <div class="ts-custom">
                <div class="ts-custom-row">
                  <span>提醒时间</span>
                  <input v-model="pendingDailyTime" type="time" class="ts-custom-input" />
                </div>
                <div class="ts-pop-footer">
                  <el-button class="ts-pop-btn" size="small" @click="popOpen.daily_reminder_time = false">取消</el-button>
                  <el-button class="ts-pop-btn" size="small" type="primary" @click="confirmDailyTime">确定</el-button>
                </div>
              </div>
            </el-popover>
          </div>
          </div>
          <div class="ts-group">
          <div class="ts-row ts-row-col">
            <div class="ts-row-main">
              <span class="ts-label">网页提醒</span>
              <span class="ts-desc">除应用内弹窗外，同时发送浏览器系统通知（需浏览器授权）</span>
            </div>
            <div class="ts-row-actions">
              <span class="ts-test" @click="testNotify">测试</span>
              <el-switch :model-value="form.web_notification" @change="onSwitch('web_notification', $event)" />
            </div>
          </div>
          <!-- 显示通知详情（对齐主流待办应用）：关闭后系统通知不展示任务标题 -->
          <div class="ts-row ts-row-col">
            <div class="ts-row-main">
              <span class="ts-label">显示通知详情</span>
              <span class="ts-desc">收到通知提醒时将在通知中展示提醒的标题和内容</span>
            </div>
            <el-switch :model-value="form.show_notification_detail" @change="onSwitch('show_notification_detail', $event)" />
          </div>
          </div>
          <div class="ts-group">
          <div class="ts-row ts-row-col">
            <div class="ts-row-main">
              <span class="ts-label">全局持续提醒</span>
              <span class="ts-desc">启用后，所有内容将会持续提醒，直到你进行处理</span>
            </div>
            <el-switch :model-value="form.persistent_reminder_all" @change="onSwitch('persistent_reminder_all', $event)" />
          </div>
          </div>
          <div class="ts-group">
          <!-- 提醒铃声（对齐主流待办应用设置-提醒与通知-提醒铃声）：点选即存并试听 -->
          <div class="ts-row">
            <span class="ts-label">提醒铃声</span>
            <el-popover v-model:visible="popOpen.reminder_sound" placement="bottom-end" :width="240" trigger="click" popper-class="ts-pop">
              <template #reference>
                <span class="ts-value">
                  {{ reminderSoundLabel(form.reminder_sound) }}
                  <ChevronsUpDown :size="13" class="ts-value-icon" />
                </span>
              </template>
              <div
                v-for="s in REMINDER_SOUNDS"
                :key="s.value"
                class="ts-opt"
                :class="{ active: form.reminder_sound === s.value }"
                @click="pickSound(s.value)"
              >
                <span>{{ s.label }}</span>
                <Check v-if="form.reminder_sound === s.value" :size="14" class="ts-opt-check" />
              </div>
            </el-popover>
          </div>
          <!-- 完成提示音（对齐主流待办应用）：选音器（无/叮/水滴/敲击/螺旋），点选即存并试听 -->
          <div class="ts-row">
            <span class="ts-label">完成提示音</span>
            <el-popover v-model:visible="popOpen.completion_sound" placement="bottom-end" :width="240" trigger="click" popper-class="ts-pop">
              <template #reference>
                <span class="ts-value">
                  {{ completionSoundLabel(form.completion_sound) }}
                  <ChevronsUpDown :size="13" class="ts-value-icon" />
                </span>
              </template>
              <div
                v-for="s in COMPLETION_SOUNDS"
                :key="s.value"
                class="ts-opt"
                :class="{ active: form.completion_sound === s.value }"
                @click="pickCompletionSound(s.value)"
              >
                <span>{{ s.label }}</span>
                <Check v-if="form.completion_sound === s.value" :size="14" class="ts-opt-check" />
              </div>
            </el-popover>
          </div>
          <!-- 提醒音量（对齐主流待办应用滑杆）：拖动松手即存 -->
          <div class="ts-row">
            <span class="ts-label">提醒音量</span>
            <el-slider
              :model-value="form.reminder_volume"
              :min="0"
              :max="100"
              class="ts-volume"
              @update:model-value="form.reminder_volume = $event"
              @change="save('reminder_volume')"
            />
          </div>
          </div>
          <!-- 按优先级设置提醒（对齐主流待办应用）：开启后为各优先级分别选铃声，到点凭铃声分辨优先级 -->
          <div class="ts-group">
          <div class="ts-row ts-row-col">
            <div class="ts-row-main">
              <span class="ts-label">按优先级设置提醒</span>
              <span class="ts-desc">开启后，可为不同优先级的任务设置不同的提醒铃声</span>
            </div>
            <el-switch :model-value="form.priority_sound_enabled" @change="onSwitch('priority_sound_enabled', $event)" />
          </div>
          <template v-if="form.priority_sound_enabled">
            <div v-for="p in PRIORITY_ROWS" :key="p.key" class="ts-row">
              <span class="ts-label">{{ p.label }}</span>
              <el-popover v-model:visible="popOpen[p.key]" placement="bottom-end" :width="240" trigger="click" popper-class="ts-pop">
                <template #reference>
                  <span class="ts-value">
                    {{ reminderSoundLabel(form[p.key]) }}
                    <ChevronsUpDown :size="13" class="ts-value-icon" />
                  </span>
                </template>
                <div
                  v-for="s in REMINDER_SOUNDS"
                  :key="s.value"
                  class="ts-opt"
                  :class="{ active: form[p.key] === s.value }"
                  @click="pickPrioritySound(p.key, s.value)"
                >
                  <span>{{ s.label }}</span>
                  <Check v-if="form[p.key] === s.value" :size="14" class="ts-opt-check" />
                </div>
              </el-popover>
            </div>
          </template>
          </div>
        </div>

        <!-- 日期与时间（对齐主流待办应用设置-日期与时间） -->
        <div v-else-if="nav === 'datetime'" class="ts-rows">
          <div class="ts-group">
          <div class="ts-row">
            <span class="ts-label">时间格式</span>
            <el-popover v-model:visible="popOpen.time_format" placement="bottom-end" :width="240" trigger="click" popper-class="ts-pop">
              <template #reference>
                <span class="ts-value">
                  {{ form.time_format === '12h' ? '12小时制 (下午1:00)' : '24小时制 (13:00)' }}
                  <ChevronsUpDown :size="13" class="ts-value-icon" />
                </span>
              </template>
              <div class="ts-opt" :class="{ active: form.time_format === '24h' }" @click="pickSave('time_format', '24h')">
                <span>24小时制 <span class="ts-opt-sub">(13:00)</span></span>
                <Check v-if="form.time_format === '24h'" :size="14" class="ts-opt-check" />
              </div>
              <div class="ts-opt" :class="{ active: form.time_format === '12h' }" @click="pickSave('time_format', '12h')">
                <span>12小时制 <span class="ts-opt-sub">(下午1:00)</span></span>
                <Check v-if="form.time_format === '12h'" :size="14" class="ts-opt-check" />
              </div>
            </el-popover>
          </div>
          <div class="ts-row">
            <span class="ts-label">每周开始于</span>
            <el-popover v-model:visible="popOpen.week_start" placement="bottom-end" :width="240" trigger="click" popper-class="ts-pop">
              <template #reference>
                <span class="ts-value">
                  {{ form.week_start === 'monday' ? '周一' : '周日' }}
                  <ChevronsUpDown :size="13" class="ts-value-icon" />
                </span>
              </template>
              <div class="ts-opt" :class="{ active: form.week_start === 'sunday' }" @click="pickSave('week_start', 'sunday')">
                <span>周日</span>
                <Check v-if="form.week_start === 'sunday'" :size="14" class="ts-opt-check" />
              </div>
              <div class="ts-opt" :class="{ active: form.week_start === 'monday' }" @click="pickSave('week_start', 'monday')">
                <span>周一</span>
                <Check v-if="form.week_start === 'monday'" :size="14" class="ts-opt-check" />
              </div>
            </el-popover>
          </div>
          <div class="ts-row">
            <span class="ts-label">显示农历</span>
            <el-switch :model-value="form.show_lunar" @change="onSwitch('show_lunar', $event)" />
          </div>
          <div class="ts-row">
            <span class="ts-label">显示周数</span>
            <el-switch :model-value="form.show_week_number" @change="onSwitch('show_week_number', $event)" />
          </div>
          <div class="ts-row">
            <span class="ts-label">显示节假日调休</span>
            <el-switch :model-value="form.show_holiday" @change="onSwitch('show_holiday', $event)" />
          </div>
          <div class="ts-row ts-row-col">
            <div class="ts-row-main">
              <span class="ts-label">时区</span>
              <span class="ts-desc">启用后，在时间选择界面设置时间时，可以选择时区</span>
            </div>
            <el-switch :model-value="form.show_timezone" @change="onSwitch('show_timezone', $event)" />
          </div>
          </div>
        </div>

        <!-- 模板 → 笔记模板（对齐主流待办应用设置-模板-笔记模板：列表管理，可新建/编辑/删除） -->
        <div v-else-if="nav === 'template'" class="ts-rows">
          <div class="tpl-head">
            <span class="ts-desc">将常用笔记内容保存为模板，记笔记时一键调用</span>
            <el-button size="small" type="primary" plain @click="openTplEditor(-1)">新建模板</el-button>
          </div>
          <div class="ts-group">
            <div v-for="(t, i) in noteTemplates" :key="i" class="ts-row tpl-row">
              <div class="ts-row-main tpl-main">
                <span class="tpl-name">{{ t.name }}</span>
                <span class="tpl-preview">{{ tplPreview(t.content_html) }}</span>
              </div>
              <div class="ts-row-actions">
                <span class="ts-test" @click="openTplEditor(i)">编辑</span>
                <span class="tpl-del" @click="delTemplate(i)">删除</span>
              </div>
            </div>
            <div v-if="!noteTemplates.length" class="tpl-empty">
              暂无笔记模板
              <span>可在笔记编辑器工具栏「模板」或笔记「保存为模板」中创建</span>
            </div>
          </div>
        </div>

        <!-- 更多设置 → 任务默认值（行式列表，点中右侧值弹选项框，选中即生效） -->
        <template v-else>
          <div class="ts-rows">
            <div class="ts-group">
            <div v-for="row in rows" :key="row.key" class="ts-row">
              <span class="ts-label">{{ row.label }}</span>
              <el-popover
                v-model:visible="popOpen[row.key]"
                placement="bottom-end"
                :width="row.key === 'default_tags' ? 260 : 240"
                trigger="click"
                popper-class="ts-pop"
                @show="onPopShow(row.key)"
                @hide="onPopHide(row.key)"
              >
                <template #reference>
                  <span class="ts-value">
                    {{ displayValue(row.key) }}
                    <ChevronsUpDown :size="13" class="ts-value-icon" />
                  </span>
                </template>

                <!-- 默认提醒(全天)「自定义」：提前 N 天 + 提醒时间（对齐主流待办应用） -->
                <div v-if="row.key === 'default_reminder_allday' && alldayCustomOpen" class="ts-custom">
                  <div class="ts-custom-row">
                    <span>提前</span>
                    <input v-model.number="alldayCustomDays" type="number" min="0" max="99" class="ts-custom-input" />
                    <span>天</span>
                  </div>
                  <div class="ts-custom-row">
                    <span>提醒时间</span>
                    <input v-model="alldayCustomTime" type="time" class="ts-custom-input" />
                  </div>
                  <div class="ts-pop-footer">
                    <el-button class="ts-pop-btn" size="small" @click="alldayCustomOpen = false">取消</el-button>
                    <el-button class="ts-pop-btn" size="small" type="primary" @click="confirmAlldayCustom">确定</el-button>
                  </div>
                </div>
                <!-- 单选选项列表（默认提醒(有时间)选「自定义」时切换为分钟输入面板，对齐主流待办应用） -->
                <div v-else-if="row.key === 'default_reminder_minutes' && reminderCustomOpen" class="ts-custom">
                  <div class="ts-custom-row">
                    <span>提前</span>
                    <input v-model.number="customMinutes" type="number" min="0" max="9999" class="ts-custom-input" />
                    <span>分钟</span>
                  </div>
                  <div class="ts-pop-footer">
                    <el-button class="ts-pop-btn" size="small" @click="reminderCustomOpen = false">取消</el-button>
                    <el-button class="ts-pop-btn" size="small" type="primary" @click="confirmCustomMinutes">确定</el-button>
                  </div>
                </div>
                <template v-else-if="row.key !== 'default_tags'">
                  <div class="ts-opts">
                    <div
                      v-for="opt in optionsOf(row.key)"
                      :key="String(opt.value)"
                      class="ts-opt"
                      :class="{ active: isSame(pending[row.key], opt.value) }"
                      @click="pick(row.key, opt.value)"
                    >
                      <span>{{ opt.label }}<span v-if="opt.sub" class="ts-opt-sub">{{ opt.sub }}</span></span>
                      <Check v-if="isSame(pending[row.key], opt.value)" :size="14" class="ts-opt-check" />
                    </div>
                  </div>
                  <!-- 对齐主流待办应用：选项仅暂存，点「确定」才保存，「取消」丢弃 -->
                  <div class="ts-pop-footer">
                    <el-button class="ts-pop-btn" size="small" @click="popOpen[row.key] = false">取消</el-button>
                    <el-button class="ts-pop-btn" size="small" type="primary" @click="confirmPick(row.key)">确定</el-button>
                  </div>
                </template>
                <!-- 默认标签：多选 + 可新建 -->
                <el-select
                  v-else
                  v-model="form.default_tags"
                  multiple
                  filterable
                  allow-create
                  default-first-option
                  placeholder="选择或输入新标签回车"
                  style="width: 100%"
                >
                  <el-option v-for="t in tagOptions" :key="t" :label="t" :value="t" />
                </el-select>
              </el-popover>
            </div>
            </div>
          </div>

          <div class="ts-reset" @click="reset">重置任务默认值</div>
        </template>
      </section>
    </div>
  </el-dialog>

  <!-- 笔记模板编辑（对齐主流待办应用：设置-模板中可改名/改内容/新建） -->
  <el-dialog
    v-model="tplEditVisible"
    :title="tplEditIndex === -1 ? '新建笔记模板' : '编辑笔记模板'"
    width="560px"
    append-to-body
    class="tpl-editor-win"
  >
    <div class="tpl-editor">
      <input v-model="tplEditName" class="tpl-editor-name" placeholder="模板名称" maxlength="50" />
      <div ref="tplEditContentEl" class="tpl-editor-content" contenteditable="true" data-placeholder="输入模板内容，支持粘贴富文本"></div>
    </div>
    <template #footer>
      <el-button @click="tplEditVisible = false">取消</el-button>
      <el-button type="primary" :loading="tplSaving" @click="saveTplEdit">保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, nextTick, reactive, ref, watch } from 'vue'
import { Check, ChevronsUpDown, CircleHelp, CircleUserRound, SlidersHorizontal, Bell, CalendarClock, LayoutTemplate, X } from 'lucide-vue-next'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useTaskStore } from '@/stores/task'
import { useAuthStore } from '@/stores/auth'
import { parseAllDayDefault, allDayDefaultLabel } from '../utils'
import { REMINDER_SOUNDS, reminderSoundLabel, playReminderSound, COMPLETION_SOUNDS, completionSoundLabel, playCompletionSound } from '@/utils/reminderSound'

const store = useTaskStore()
const authStore = useAuthStore()

// 开关由 store.settingsVisible 驱动（入口在任务侧栏左下角「设置」）
const visible = computed({
  get: () => store.settingsVisible,
  set: (v) => { store.settingsVisible = v },
})
const nav = ref('more')
const popOpen = reactive({})

const DEFAULTS = {
  default_list_id: null,
  default_due: 'none',
  default_priority: 0,
  default_reminder_minutes: null,
  default_reminder_allday: 'none',
  default_range_minutes: 60,
  default_tags: [],
  daily_reminder_enabled: false,
  daily_reminder_time: '09:00',
  web_notification: false,
  persistent_reminder_all: false,
  reminder_sound: 'default',
  show_notification_detail: true,
  completion_sound: 'ding',
  reminder_volume: 80,
  priority_sound_enabled: false,
  priority_sound_high: 'default',
  priority_sound_medium: 'default',
  priority_sound_low: 'default',
  priority_sound_none: 'default',
  show_lunar: false,
  time_format: '24h',
  week_start: 'sunday',
  show_week_number: false,
  show_holiday: false,
  show_timezone: false,
}
const form = reactive({ ...DEFAULTS })

const avatarText = computed(() => {
  const n = authStore.userInfo?.nickname || authStore.userInfo?.username || ''
  return n.slice(0, 1).toUpperCase()
})

// 打开时加载最新设置/清单/标签
watch(visible, async (v) => {
  if (!v) return
  nav.value = 'more'
  await store.fetchSettings()
  if (!store.lists.length) store.fetchLists().catch(() => {})
  if (!store.tagCounts.length) store.fetchTagCounts().catch(() => {})
  Object.assign(form, {
    default_list_id: store.settings?.default_list_id ?? null,
    default_due: store.settings?.default_due ?? 'none',
    default_priority: store.settings?.default_priority ?? 0,
    default_reminder_minutes: store.settings?.default_reminder_minutes ?? null,
    default_reminder_allday: store.settings?.default_reminder_allday ?? 'none',
    default_range_minutes: store.settings?.default_range_minutes ?? 60,
    default_tags: [...(store.settings?.default_tags ?? [])],
    daily_reminder_enabled: store.settings?.daily_reminder_enabled ?? false,
    daily_reminder_time: store.settings?.daily_reminder_time ?? '09:00',
    web_notification: store.settings?.web_notification ?? false,
    persistent_reminder_all: store.settings?.persistent_reminder_all ?? false,
    reminder_sound: store.settings?.reminder_sound ?? 'default',
    show_notification_detail: store.settings?.show_notification_detail ?? true,
    completion_sound: store.settings?.completion_sound ?? 'ding',
    reminder_volume: store.settings?.reminder_volume ?? 80,
    priority_sound_enabled: store.settings?.priority_sound_enabled ?? false,
    priority_sound_high: store.settings?.priority_sound_high ?? 'default',
    priority_sound_medium: store.settings?.priority_sound_medium ?? 'default',
    priority_sound_low: store.settings?.priority_sound_low ?? 'default',
    priority_sound_none: store.settings?.priority_sound_none ?? 'default',
    show_lunar: store.settings?.show_lunar ?? false,
    time_format: store.settings?.time_format ?? '24h',
    week_start: store.settings?.week_start ?? 'sunday',
    show_week_number: store.settings?.show_week_number ?? false,
    show_holiday: store.settings?.show_holiday ?? false,
    show_timezone: store.settings?.show_timezone ?? false,
  })
})

// 行定义（对齐主流待办应用「设置-更多设置-任务默认值」：行式列表，点中值弹选项框，选中即保存）
const rows = [
  { key: 'default_due', label: '默认日期' },
  { key: 'default_range_minutes', label: '默认时间段' },
  { key: 'default_reminder_minutes', label: '默认提醒（有时间的任务）' },
  { key: 'default_reminder_allday', label: '默认提醒（全天任务）' },
  { key: 'default_priority', label: '默认优先级' },
  { key: 'default_tags', label: '默认标签' },
  { key: 'default_list_id', label: '默认清单' },
]

const STATIC_OPTIONS = {
  default_due: [
    { value: 'none', label: '无' },
    { value: 'today', label: '今天' },
    { value: 'tomorrow', label: '明天' },
  ],
  default_range_minutes: [
    { value: 30, label: '30 分钟' },
    { value: 60, label: '1 小时' },
    { value: 120, label: '2 小时' },
  ],
  default_priority: [
    { value: 0, label: '无优先级' },
    { value: 1, label: '低' },
    { value: 2, label: '中' },
    { value: 3, label: '高' },
  ],
  default_reminder_minutes: [
    { value: null, label: '无' },
    { value: 0, label: '准时' },
    { value: 5, label: '提前5分钟' },
    { value: 30, label: '提前30分钟' },
    { value: 60, label: '提前1小时' },
    { value: 1440, label: '提前1天' },
    { value: 'end', label: '结束时' },
    { value: '__custom', label: '自定义' },
  ],
  default_reminder_allday: [
    { value: 'none', label: '无' },
    { value: 'd0', label: '当天', sub: ' (09:00)' },
    { value: 'd1', label: '提前1天', sub: ' (09:00)' },
    { value: 'd2', label: '提前2天', sub: ' (09:00)' },
    { value: 'd3', label: '提前3天', sub: ' (09:00)' },
    { value: 'd7', label: '提前1周', sub: ' (09:00)' },
    { value: '__custom_allday', label: '自定义' },
  ],
}

function optionsOf(key) {
  if (key === 'default_list_id') {
    return [{ value: null, label: '收集箱' }, ...store.lists.map((l) => ({ value: l.id, label: l.name }))]
  }
  return STATIC_OPTIONS[key] || []
}

// 标签候选：已有标签 ∪ 当前已选（已选但已被删光的标签也能显示/移除）
const tagOptions = computed(() => {
  const set = new Set(store.tagCounts.map((t) => t.tag))
  form.default_tags.forEach((t) => set.add(t))
  return [...set]
})

function isSame(a, b) {
  return a === b || (a == null && b == null)
}

function onPopHide(key) {
  if (key === 'default_tags') save('default_tags')
  if (key === 'default_reminder_minutes') reminderCustomOpen.value = false
  if (key === 'default_reminder_allday') alldayCustomOpen.value = false
}

// 提醒与通知：开关即存；网页提醒开启时需浏览器授权，拒绝则回退
async function onSwitch(key, v) {
  if (key === 'web_notification' && v && 'Notification' in window) {
    if (Notification.permission !== 'granted') {
      const perm = await Notification.requestPermission()
      if (perm !== 'granted') {
        ElMessage.warning('浏览器未授权通知权限，请在浏览器设置中允许通知')
        return // 不落库，开关回退
      }
    }
  }
  form[key] = v
  save(key)
}

// 测试通知：走真实提醒卡片链路（ReminderPopup）+ 直接尝试发浏览器系统通知（未授权时当场请求）
async function testNotify() {
  store.showTestReminder()
  if (!('Notification' in window)) return
  let perm = Notification.permission
  if (perm === 'default') {
    perm = await Notification.requestPermission()
  }
  if (perm === 'granted') {
    try {
      new Notification('今天', { body: '这是一条测试提醒', icon: '/notify-icon.png', requireInteraction: true, tag: 'reminder-test' })
    } catch {
      // 系统通知不可用时静默
    }
  } else {
    ElMessage.warning('浏览器未授权系统通知（点地址栏左侧图标 → 网站设置 → 通知 → 允许），本次仅发送了应用内提醒卡片')
  }
}

// 每日提醒时间（暂存，确定才保存）
const pendingDailyTime = ref('09:00')
function confirmDailyTime() {
  form.daily_reminder_time = pendingDailyTime.value || '09:00'
  popOpen.daily_reminder_time = false
  save('daily_reminder_time')
}

// 日期与时间选项行：点选即存（对齐主流待办应用该分组无取消/确定）
function pickSave(key, value) {
  form[key] = value
  popOpen[key] = false
  save(key)
}

// 提醒铃声：点选即存并试听（对齐主流待办应用选铃声时播放预览）
function pickSound(value) {
  pickSave('reminder_sound', value)
  playReminderSound(value)
}

// 完成提示音：点选即存并试听
function pickCompletionSound(value) {
  pickSave('completion_sound', value)
  playCompletionSound(value, form.reminder_volume)
}

// 按优先级设置提醒：优先级行定义 + 点选即存并试听
const PRIORITY_ROWS = [
  { key: 'priority_sound_high', label: '高优先级' },
  { key: 'priority_sound_medium', label: '中优先级' },
  { key: 'priority_sound_low', label: '低优先级' },
  { key: 'priority_sound_none', label: '无优先级' },
]
function pickPrioritySound(key, value) {
  pickSave(key, value)
  playReminderSound(value, form.reminder_volume)
}

// 单项保存（对齐主流待办应用即选即存，无保存按钮）
async function save(key) {
  try {
    await store.saveSettings({ [key]: form[key] })
  } catch {
    // 失败由请求拦截器统一提示
  }
}

// 弹层打开时把当前值拷到暂存：选项点击只改暂存，点「确定」才保存（对齐主流待办应用选项弹层 取消/确定）
const pending = reactive({})
function onPopShow(key) {
  if (key !== 'default_tags') pending[key] = form[key]
}

function pick(key, value) {
  // 「自定义」不直接落值：展开自定义面板（对齐主流待办应用默认提醒自定义）
  if (key === 'default_reminder_minutes' && value === '__custom') {
    customMinutes.value = typeof form.default_reminder_minutes === 'number' && form.default_reminder_minutes > 0
      ? form.default_reminder_minutes
      : 10
    reminderCustomOpen.value = true
    return
  }
  if (key === 'default_reminder_allday' && value === '__custom_allday') {
    openAlldayCustom()
    return
  }
  pending[key] = value
}

// 默认提醒（全天任务）「自定义」：提前 N 天 + 提醒时间
const alldayCustomOpen = ref(false)
const alldayCustomDays = ref(1)
const alldayCustomTime = ref('09:00')
function openAlldayCustom() {
  const p = parseAllDayDefault(form.default_reminder_allday)
  alldayCustomDays.value = p?.days ?? 1
  alldayCustomTime.value = p?.time ?? '09:00'
  alldayCustomOpen.value = true
}
function confirmAlldayCustom() {
  const d = Math.max(0, Math.min(99, Math.floor(alldayCustomDays.value || 0)))
  form.default_reminder_allday = `c:${d}@${alldayCustomTime.value || '09:00'}`
  alldayCustomOpen.value = false
  popOpen.default_reminder_allday = false
  save('default_reminder_allday')
}

function confirmPick(key) {
  if (!isSame(pending[key], form[key])) {
    form[key] = pending[key]
    save(key)
  }
  popOpen[key] = false
}

// 默认提醒（有时间的任务）「自定义」分钟输入
const reminderCustomOpen = ref(false)
const customMinutes = ref(10)
function confirmCustomMinutes() {
  const m = Math.max(0, Math.min(9999, Math.floor(customMinutes.value || 0)))
  form.default_reminder_minutes = m
  reminderCustomOpen.value = false
  popOpen.default_reminder_minutes = false
  save('default_reminder_minutes')
}

function displayValue(key) {
  if (key === 'default_tags') {
    return form.default_tags.length ? form.default_tags.join('、') : '无'
  }
  if (key === 'default_reminder_allday') return allDayDefaultLabel(form.default_reminder_allday)
  if (key === 'default_reminder_minutes') {
    const v = form.default_reminder_minutes
    if (v === 'end') return '结束时'
    // 自定义分钟数（不在静态选项中）也正常显示
    if (typeof v === 'number' && !STATIC_OPTIONS.default_reminder_minutes.some((o) => o.value === v)) {
      return v === 0 ? '准时' : `提前${v}分钟`
    }
  }
  const opt = optionsOf(key).find((o) => isSame(o.value, form[key]))
  return opt?.label ?? '无'
}

// 模板 → 笔记模板管理（对齐主流待办应用设置-模板-笔记模板：列表 + 新建/编辑/删除；数据存 settings.note_templates）
const noteTemplates = computed(() => store.settings?.note_templates || [])

function tplPreview(html) {
  const text = (html || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
  if (!text) return '（空内容）'
  return text.length > 60 ? `${text.slice(0, 60)}…` : text
}

const tplEditVisible = ref(false)
const tplEditIndex = ref(-1)
const tplEditName = ref('')
const tplEditContentEl = ref(null)
const tplSaving = ref(false)

async function openTplEditor(i) {
  tplEditIndex.value = i
  tplEditName.value = i >= 0 ? noteTemplates.value[i].name : ''
  tplEditVisible.value = true
  await nextTick()
  if (tplEditContentEl.value) {
    tplEditContentEl.value.innerHTML = i >= 0 ? noteTemplates.value[i].content_html : ''
  }
}

async function saveTplEdit() {
  const name = tplEditName.value.trim()
  const html = tplEditContentEl.value?.innerHTML || ''
  if (!name) {
    ElMessage.warning('请输入模板名称')
    return
  }
  if (!html.replace(/<[^>]+>/g, '').trim()) {
    ElMessage.warning('模板内容为空')
    return
  }
  if (noteTemplates.value.some((t, idx) => idx !== tplEditIndex.value && t.name === name)) {
    ElMessage.warning('已存在同名模板，请换个名称')
    return
  }
  tplSaving.value = true
  try {
    const list = [...noteTemplates.value]
    if (tplEditIndex.value >= 0) list[tplEditIndex.value] = { name, content_html: html }
    else list.push({ name, content_html: html })
    await store.saveSettings({ note_templates: list })
    tplEditVisible.value = false
    ElMessage.success('模板已保存')
  } finally {
    tplSaving.value = false
  }
}

async function delTemplate(i) {
  try {
    await ElMessageBox.confirm(`删除模板「${noteTemplates.value[i].name}」？`, '删除笔记模板', {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  await store.saveSettings({ note_templates: noteTemplates.value.filter((_, idx) => idx !== i) })
  ElMessage.success('模板已删除')
}

async function reset() {
  try {
    await ElMessageBox.confirm('将所有任务默认值恢复为初始设置？', '重置任务默认值', {
      confirmButtonText: '重置',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  Object.assign(form, { ...DEFAULTS, default_tags: [] })
  await store.saveSettings({ ...form })
  ElMessage.success('已重置')
}
</script>

<style scoped>
.sw {
  display: flex;
  height: 480px;
  margin: -20px;
}
/* 左功能栏 */
.sw-nav {
  width: 160px;
  flex-shrink: 0;
  background: var(--ss-bg, #f5f7fa);
  border-radius: 6px 0 0 6px;
  padding: 0 8px;
}
.sw-nav-title {
  height: 48px;
  display: flex;
  align-items: center;
  padding: 0 10px;
  font-size: 15px;
  font-weight: 600;
  color: var(--ss-text, #303133);
}
.sw-nav-item {
  display: flex;
  align-items: center;
  gap: 7px;
  height: 36px;
  padding: 0 10px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  color: var(--ss-text, #303133);
}
.sw-nav-item:hover {
  background: rgb(0 0 0 / 4%);
}
.sw-nav-item.active {
  background: rgb(64 158 255 / 12%);
  color: var(--el-color-primary);
  font-weight: 500;
}
.sw-nav-icon {
  flex-shrink: 0;
}
/* 右内容区 */
.sw-main {
  flex: 1;
  min-width: 0;
  padding: 0 20px;
  overflow-y: auto;
}
.sw-head {
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.sw-head-title {
  font-size: 15px;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--ss-text, #303133);
}
.sw-help {
  color: var(--ss-text-muted, #909399);
}
.sw-close {
  cursor: pointer;
  color: var(--ss-text-muted, #909399);
}
.sw-close:hover {
  color: var(--ss-text, #303133);
}
.sw-account {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
}
.sw-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--el-color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}
.sw-account-name {
  font-size: 14px;
  color: var(--ss-text, #303133);
}
/* 任务默认值行式列表 */
/* 分块浅灰卡片（对齐主流待办应用设置页：每一块浅灰背景区分） */
.ts-group {
  background: var(--ss-fill, #f7f7f9);
  border-radius: 10px;
  padding: 2px 16px;
  margin-bottom: 14px;
}
.ts-group .ts-row {
  border-bottom-color: var(--ss-border-light, #ececf1);
}
.ts-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--ss-border, #f0f0f0);
  font-size: 14px;
}
.ts-row:last-child {
  border-bottom: none;
}
.ts-label {
  color: var(--ss-text, #303133);
}
.ts-value {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: var(--ss-text-muted, #909399);
  cursor: pointer;
  max-width: 240px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ts-value:hover {
  color: var(--el-color-primary);
}
.ts-value-icon {
  flex-shrink: 0;
}
.ts-opts {
  display: flex;
  flex-direction: column;
}
.ts-opt {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  font-size: 14px;
  border-radius: 6px;
  cursor: pointer;
  color: var(--ss-text, #303133);
}
.ts-opt:hover {
  background: var(--ss-bg, #f5f7fa);
}
.ts-opt.active {
  color: var(--el-color-primary);
}
.ts-opt-check {
  flex-shrink: 0;
}
.ts-opt-sub {
  color: var(--ss-text-muted, #909399);
}
.ts-opt.active .ts-opt-sub {
  color: var(--el-color-primary);
  opacity: 0.75;
}
.ts-reset {
  margin-top: 14px;
  color: var(--el-color-primary);
  font-size: 13px;
  cursor: pointer;
  user-select: none;
}
.ts-reset:hover {
  opacity: 0.8;
}
/* 模板 → 笔记模板管理页 */
.tpl-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.tpl-row {
  gap: 12px;
}
.tpl-main {
  flex: 1;
  min-width: 0;
}
.tpl-name {
  font-size: 14px;
  color: var(--ss-text, #303133);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tpl-preview {
  font-size: 12px;
  color: var(--ss-text-muted, #909399);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tpl-del {
  font-size: 13px;
  color: var(--el-color-danger);
  cursor: pointer;
  user-select: none;
}
.tpl-del:hover {
  opacity: 0.8;
}
.tpl-empty {
  padding: 28px 0;
  text-align: center;
  font-size: 14px;
  color: var(--ss-text, #303133);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.tpl-empty span {
  font-size: 12px;
  color: var(--ss-text-muted, #909399);
}
/* 模板编辑弹窗 */
.tpl-editor {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.tpl-editor-name {
  padding: 8px 12px;
  font-size: 14px;
  border: 1px solid var(--ss-border, #dcdfe6);
  border-radius: 8px;
  background: var(--ss-bg, #f5f7fa);
  color: var(--ss-text, #303133);
}
.tpl-editor-name:focus {
  outline: none;
  border-color: var(--el-color-primary);
}
.tpl-editor-content {
  min-height: 220px;
  max-height: 50vh;
  overflow-y: auto;
  padding: 10px 12px;
  font-size: 14px;
  line-height: 1.6;
  border: 1px solid var(--ss-border, #dcdfe6);
  border-radius: 8px;
  background: var(--ss-bg, #f5f7fa);
  color: var(--ss-text, #303133);
}
.tpl-editor-content:focus {
  outline: none;
  border-color: var(--el-color-primary);
}
.tpl-editor-content:empty::before {
  content: attr(data-placeholder);
  color: var(--ss-text-muted, #909399);
}
/* 提醒与通知：带描述的开关行（对齐主流待办应用） */
.ts-row-col {
  gap: 12px;
}
.ts-row-main {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}
.ts-desc {
  font-size: 12px;
  color: var(--ss-text-muted, #909399);
}
.ts-row-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.ts-test {
  font-size: 13px;
  color: var(--el-color-primary);
  cursor: pointer;
  user-select: none;
}
.ts-test:hover {
  opacity: 0.8;
}
/* 提醒音量滑杆（对齐主流待办应用设置-提醒与通知-提醒音量） */
.ts-volume {
  width: 160px;
  flex-shrink: 0;
}
/* 选项弹层底部 取消/确定（对齐主流待办应用：双按钮均分整行） */
.ts-pop-footer {
  display: flex;
  gap: 10px;
  padding: 10px 4px 2px;
}
.ts-pop-btn {
  flex: 1;
  margin: 0 !important;
}
/* 默认提醒「自定义」分钟输入面板（对齐主流待办应用：提前 N 分钟 + 取消/确定） */
.ts-custom {
  padding: 4px 2px 0;
}
.ts-custom-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 14px;
  color: var(--ss-text, #303133);
}
.ts-custom-input {
  width: 72px;
  padding: 5px 8px;
  font-size: 13px;
  border: 1px solid var(--ss-border);
  border-radius: 6px;
  background: var(--ss-bg, #f5f7fa);
  color: inherit;
}
.ts-custom-input:focus {
  outline: none;
  border-color: var(--el-color-primary);
}
</style>

<style>
/* 弹层内边距/圆角对齐主流待办应用：上下 8px 留边、列表两侧 8px 内距、圆角 10px */
.ts-pop.el-popover {
  padding: 8px !important;
  border-radius: 10px !important;
}
/* 设置窗口：隐藏 el-dialog 默认头/体边距，布局完全自绘 */
.settings-win .el-dialog__header {
  display: none;
}
.settings-win .el-dialog__body {
  padding: 20px;
}
</style>
