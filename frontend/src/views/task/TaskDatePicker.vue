<template>
  <span v-if="disabled"><slot name="trigger" :label="triggerLabel" /></span>
  <!-- inline 模式：不套 el-popover，面板内容直接内联渲染（批量面板等「无弹出层」场景） -->
  <component
    :is="inline ? 'div' : ElPopover"
    v-else
    v-bind="
      inline
        ? { class: 'tdp-inline-host' }
        : {
            visible: visible,
            'onUpdate:visible': (v) => (visible = v),
            trigger: 'click',
            placement: 'bottom-start',
            width: 300,
            'popper-class': 'task-date-picker-popper',
          }
    "
  >
    <!-- 初始化放在触发器点击（capture）而不是 @show：el-popover 的 show/hide 事件在
         popper 内容重排时会成对误触发，会把用户编辑到一半的状态重置 -->
    <template v-if="!inline" #reference>
      <span class="tdp-trigger" @click.capture="initState"><slot name="trigger" :label="triggerLabel" /></span>
    </template>

    <div class="tdp">
      <!-- 顶部 Tab：日期 / 时间段 -->
      <div class="tdp-tabs">
        <span class="tdp-tab" :class="{ active: tab === 'date' }" @click="switchTab('date')">日期</span>
        <span class="tdp-tab" :class="{ active: tab === 'range' }" @click="switchTab('range')">时间段</span>
      </div>

      <!-- 日期 Tab -->
      <template v-if="tab === 'date'">
        <!-- 快捷图标：今天 / 明天 / 下周 / 下月 -->
        <div class="tdp-quick">
          <el-tooltip v-for="q in quickIcons" :key="q.tip" :content="q.tip" placement="top">
            <div class="tdp-quick-item" @click="applyQuick(q.days, q.unit)">
              <component :is="q.icon" :size="18" class="tdp-quick-icon" />
            </div>
          </el-tooltip>
        </div>

        <!-- 日历面板（周日开头） -->
        <div class="tdp-cal">
          <div class="tdp-cal-head">
            <span class="tdp-cal-title">{{ cursor.year() }}年{{ cursor.month() + 1 }}月</span>
            <div class="tdp-cal-navs">
              <ChevronLeft :size="16" class="tdp-nav" @click="shiftMonth(-1)" />
              <span class="tdp-nav tdp-today-dot" title="回到今天" @click="goToday"></span>
              <ChevronRight :size="16" class="tdp-nav" @click="shiftMonth(1)" />
            </div>
          </div>
          <div class="tdp-week" :class="{ 'tdp-cols-8': showWeekNumber }">
            <span v-if="showWeekNumber" class="tdp-wn"></span>
            <span v-for="w in weekDays" :key="w">{{ w }}</span>
          </div>
          <div class="tdp-grid" :class="{ 'tdp-grid-lunar': showLunar, 'tdp-cols-8': showWeekNumber }">
            <template v-for="row in calendarRows" :key="row.key">
              <span v-if="showWeekNumber" class="tdp-wn">{{ row.weekNum }}</span>
              <span
                v-for="cell in row.cells"
                :key="cell.key"
                class="tdp-day"
                :class="{ dim: !cell.inMonth, selected: cell.selected, today: cell.isToday }"
                @click="selectDay(cell.date)"
              ><span v-if="showHoliday && cell.holiday" class="tdp-day-hd" :class="cell.holiday === '班' ? 'work' : 'rest'">{{ cell.holiday }}</span>
                <span class="tdp-day-num">{{ cell.date.date() }}</span>
                <span v-if="showLunar" class="tdp-day-lunar" :class="{ fest: cell.lunarFest }">{{ cell.lunar }}</span>
              </span>
            </template>
          </div>
        </div>

        <!-- 时间行：不设则全天 -->
        <div class="tdp-row" @click="timeOpen = !timeOpen">
          <span class="tdp-row-label"><Clock :size="14" class="tdp-row-icon" />时间</span>
          <span class="tdp-row-value">{{ timeText }}</span>
          <ChevronRight :size="14" class="tdp-row-arrow" :class="{ open: timeOpen }" />
        </div>
        <div v-if="timeOpen" class="tdp-sub-panel" @click.stop>
          <el-time-picker
            v-model="timeValue"
            :format="elTimeFormat"
            placeholder="不设时间为全天"
            clearable
            :teleported="false"
            style="width: 100%"
          />
          <!-- 时区（设置-日期与时间-时区开启后显示）：所选时区解释上方输入的时间 -->
          <el-select v-if="showTimezone" v-model="tzOffset" size="small" class="tdp-tz" :teleported="false">
            <el-option v-for="t in TZ_OPTIONS" :key="t.value" :label="t.label" :value="t.value" />
          </el-select>
        </div>
      </template>

      <!-- 时间段 Tab（P2：开始/结束/全天开关，对齐截图：日期+时间双输入框） -->
      <!-- 时间输入框始终渲染（全天下仅禁用）：隐藏会让用户以为“少了输入框” -->
      <!-- 注意：弹层内所有 picker 必须 :teleported="false"，否则面板 teleport 到 body，
           点选日期会被 el-popover 判定为外部点击导致整个弹层关闭 -->
      <template v-else>
        <div class="tdp-range-row">
          <span class="tdp-range-label">开始</span>
          <el-date-picker
            v-model="rangeStartDate"
            type="date"
            format="M月D日"
            placeholder="日期"
            clearable
            :teleported="false"
            class="tdp-range-date"
          />
          <el-time-picker
            v-model="rangeStartTime"
            :format="elTimeFormat"
            placeholder="时间"
            clearable
            :teleported="false"
            :disabled="rangeAllDay"
            class="tdp-range-time"
          />
        </div>
        <div class="tdp-range-row">
          <span class="tdp-range-label">结束</span>
          <el-date-picker
            v-model="rangeEndDate"
            type="date"
            format="M月D日"
            placeholder="日期"
            clearable
            :teleported="false"
            class="tdp-range-date"
          />
          <el-time-picker
            v-model="rangeEndTime"
            :format="elTimeFormat"
            placeholder="时间"
            clearable
            :teleported="false"
            :disabled="rangeAllDay"
            class="tdp-range-time"
          />
        </div>
        <div class="tdp-range-row tdp-range-allday">
          <span class="tdp-range-label">全天</span>
          <el-switch v-model="rangeAllDay" />
        </div>
      </template>

      <!-- 提醒行（两个 Tab 共用）：相对提醒前端换算绝对 at 落库（§5.4）。
           选项以悬浮下拉卡片呈现（对齐主流待办应用：浮在提醒行下方、不撑高主卡片、点外部收起） -->
      <div class="tdp-reminder-wrap">
        <div class="tdp-row" :class="{ 'reminder-open': reminderOpen }" @click.stop="reminderOpen = !reminderOpen">
          <span class="tdp-row-label"><Bell :size="14" class="tdp-row-icon" />提醒</span>
          <span class="tdp-row-value">{{ reminderRowText }}</span>
          <!-- 已设提醒时显示 × 一键清除（对齐主流待办应用提醒行的 ×） -->
          <X
            v-if="localReminders.length"
            :size="13"
            class="tdp-row-clear"
            @click.stop="localReminders = []"
          />
          <ChevronRight :size="14" class="tdp-row-arrow" :class="{ open: reminderOpen }" />
        </div>
        <div v-if="reminderOpen" class="tdp-reminder-dropdown" @click.stop>
          <!-- 对齐主流待办应用：整行纵向选项列表，已选打勾，重复点击取消；可叠加多个提醒。
               点「自定义」后面板整体替换选项列表（取消返回），不与列表同屏挤高度 -->
          <div v-if="!customOpen" class="tdp-reminder-list">
            <div
              v-for="opt in reminderPresets"
              :key="opt.key"
              class="tdp-reminder-item"
              :class="{ active: isReminderSet(opt) }"
              @click="togglePresetReminder(opt)"
            >
              <span>{{ opt.label }}<span v-if="opt.sub" class="tdp-reminder-sub"> ({{ opt.sub }})</span></span>
              <Check v-if="isReminderSet(opt)" :size="15" class="tdp-reminder-check" />
            </div>
            <!-- 不匹配预设的自定义提醒也列为已选行，点击取消 -->
            <div
              v-for="r in customReminderRows"
              :key="'c-' + r.at"
              class="tdp-reminder-item active"
              @click="removeReminderAt(r.at)"
            >
              <span>{{ reminderText(r) }}</span>
              <Check :size="15" class="tdp-reminder-check" />
            </div>
            <div class="tdp-reminder-item" @click="customOpen = true">
              <span>自定义</span>
              <ChevronRight :size="14" class="tdp-row-arrow" />
            </div>
            <!-- 持续提醒（对齐主流待办应用提醒下拉底部开关行）：开启后通知被关掉但未点「知道了」时，隔几分钟再次弹出 -->
            <div class="tdp-reminder-item tdp-reminder-persistent" @click.stop>
              <span>持续提醒</span>
              <el-switch v-model="localPersistent" size="small" @click.stop />
            </div>
          </div>
          <!-- 自定义提醒（对齐主流待办应用）：全天/定时同一结构化面板——按天/按周提前 + 时间 + 预览 -->
          <div v-else class="tdp-custom-panel" @click.stop>
              <div class="tdp-custom-mode" @click="customModeOpen = !customModeOpen">
                <span>{{ customMode === 'day' ? '按天提前' : '按周提前' }}</span>
                <ChevronDown :size="14" />
                <div v-if="customModeOpen" class="tdp-custom-mode-menu">
                  <div class="tdp-custom-mode-item" :class="{ active: customMode === 'day' }" @click.stop="customMode = 'day'; customModeOpen = false">按天提前</div>
                  <div class="tdp-custom-mode-item" :class="{ active: customMode === 'week' }" @click.stop="customMode = 'week'; customModeOpen = false">按周提前</div>
                </div>
              </div>
              <div class="tdp-custom-row">
                <span>{{ customMode === 'day' ? '提前天数' : '提前周数' }}</span>
                <input v-model.number="customCount" type="number" min="1" max="99" class="tdp-custom-input" />
              </div>
              <div class="tdp-custom-row">
                <span>提醒时间</span>
                <input v-model="customTime" type="time" class="tdp-custom-input" />
              </div>
              <div class="tdp-custom-preview">提前 {{ customDays }} 天</div>
              <div class="tdp-custom-preview-time">{{ customPreviewTime }} 提醒</div>
              <div class="tdp-custom-actions">
                <el-button size="small" @click="customOpen = false">取消</el-button>
                <el-button size="small" type="primary" :disabled="!customAt" @click="confirmCustomReminder">确定</el-button>
              </div>
            </div>
        </div>
      </div>

      <!-- 重复行（两个 Tab 共用） -->
      <div class="tdp-row" @click="recurOpen = !recurOpen">
        <span class="tdp-row-label"><Repeat :size="14" class="tdp-row-icon" />重复</span>
        <span class="tdp-row-value">{{ recurSummary }}</span>
        <ChevronRight :size="14" class="tdp-row-arrow" :class="{ open: recurOpen }" />
      </div>
      <div v-if="recurOpen" class="tdp-sub-panel" @click.stop>
        <div class="tdp-recur-row">
          <el-select
            :model-value="localRecurrence?.freq || ''"
            placeholder="不重复"
            size="small"
            :teleported="false"
            style="width: 110px"
            @change="onFreqChange"
          >
            <el-option value="" label="不重复" />
            <el-option value="daily" label="每天" />
            <el-option value="weekly" label="每周" />
            <el-option value="monthly" label="每月" />
            <el-option value="yearly" label="每年" />
          </el-select>
          <template v-if="localRecurrence">
            <span class="tdp-recur-label">每</span>
            <el-input-number
              v-model="localRecurrence.interval"
              :min="1"
              :max="99"
              size="small"
              style="width: 90px"
            />
            <span class="tdp-recur-label">{{ freqUnit }}</span>
          </template>
        </div>
        <template v-if="localRecurrence?.freq === 'weekly'">
          <el-checkbox-group v-model="localRecurrence.by_weekday" size="small">
            <el-checkbox v-for="(name, i) in ['一', '二', '三', '四', '五', '六', '日']" :key="i" :value="i">
              周{{ name }}
            </el-checkbox>
          </el-checkbox-group>
        </template>
        <template v-if="localRecurrence">
          <el-radio-group v-model="localRecurrence.end_type" size="small" class="tdp-recur-end">
            <el-radio-button value="never">永不结束</el-radio-button>
            <el-radio-button value="by_date">按日期</el-radio-button>
            <el-radio-button value="after_count">按次数</el-radio-button>
          </el-radio-group>
          <el-date-picker
            v-if="localRecurrence.end_type === 'by_date'"
            v-model="recurEndDate"
            type="date"
            placeholder="结束日期"
            size="small"
            :teleported="false"
            style="width: 100%; margin-top: 8px"
          />
          <el-input-number
            v-if="localRecurrence.end_type === 'after_count'"
            v-model="localRecurrence.count"
            :min="1"
            :max="999"
            size="small"
            style="margin-top: 8px"
          />
          <div v-if="localRecurrence.occurrences_completed" class="tdp-recur-count">
            已坚持 {{ localRecurrence.occurrences_completed }} 次
          </div>
          <!-- 跳过本次：立即生效（复用 store.skip，后端已支持），不走弹层「确定」 -->
          <div v-if="canSkip" class="tdp-skip-row">
            <span class="tdp-skip-btn" :class="{ loading: skipping }" @click="onSkip">跳过本次</span>
          </div>
        </template>
      </div>

      <!-- 底部按钮 -->
      <div class="tdp-footer">
        <el-button size="small" @click="onClear">清除</el-button>
        <el-button size="small" type="primary" @click="onConfirm">确定</el-button>
      </div>
    </div>
  </component>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage, ElPopover } from 'element-plus'
import { useTaskStore } from '@/stores/task'

const store = useTaskStore()
import { ChevronLeft, ChevronRight, ChevronDown, Clock, Bell, Repeat, Sun, Sunrise, CalendarPlus, Moon, Check, X } from 'lucide-vue-next'
import dayjs from 'dayjs'
import weekOfYear from 'dayjs/plugin/weekOfYear'
import isoWeek from 'dayjs/plugin/isoWeek'
import { recurrenceSummary, allDayDefaultLabel, lunarLabel, holidayTag } from './utils'

dayjs.extend(weekOfYear)
dayjs.extend(isoWeek)

// 日期选择弹层（对齐主流待办应用）：「日期」Tab +「时间段」Tab（P2）
// 约定：不设时间 = 全天（all_day=true，due_at 存当地 00:00 对应 UTC）；
//       时间段 Tab：开始=start_at，结束=due_at；
//       提醒只存绝对 at（相对提醒带 offset_minutes，改日期时由抽屉重算）
const props = defineProps({
  disabled: { type: Boolean, default: false },
  // 传入任务 id 才启用「跳过本次」（详情栏/右键菜单的实例均传入）
  taskId: { type: [Number, String], default: null },
  dueAt: { type: String, default: null },
  allDay: { type: Boolean, default: true },
  startAt: { type: String, default: null },
  reminders: { type: Array, default: () => [] },
  persistentReminder: { type: Boolean, default: false },
  recurrence: { type: Object, default: null },
  // 内联模式：不使用弹出层，内容直接渲染在调用处（如批量操作面板）
  inline: { type: Boolean, default: false },
})
// { due_at, all_day, start_at, reminders, persistent_reminder, recurrence }
const emit = defineEmits(['change'])

const visible = ref(false)
const tab = ref('date')

// inline 模式无触发器可点，挂载即初始化状态
onMounted(() => {
  if (props.inline) initState()
})

// ---------- 日期 Tab ----------
const cursor = ref(dayjs())
const selected = ref(null)
const timeValue = ref(null)
const timeOpen = ref(false)

// ---------- 时间段 Tab ----------
const rangeStartDate = ref(null)
const rangeStartTime = ref(null)
const rangeEndDate = ref(null)
const rangeEndTime = ref(null)
const rangeAllDay = ref(false)
// 关闭全天时，为已选日期但尚未填时间的输入框补默认时间（开始 09:00 / 结束 18:00），
// 避免用户只关全天不选时间就提交出 00:00
watch(rangeAllDay, (v) => {
  if (v) return
  if (rangeStartDate.value && !rangeStartTime.value) {
    rangeStartTime.value = dayjs(rangeStartDate.value).hour(9).minute(0).second(0).toDate()
  }
  if (rangeEndDate.value && !rangeEndTime.value) {
    rangeEndTime.value = dayjs(rangeEndDate.value).hour(18).minute(0).second(0).toDate()
  }
})

// 组合日期+时间；全天或无时间时归一到当天 00:00
function combineRange(dateVal, timeVal) {
  if (!dateVal) return null
  const d = dayjs(dateVal)
  if (rangeAllDay.value || !timeVal) return d.startOf('day')
  const t = dayjs(timeVal)
  return d.hour(t.hour()).minute(t.minute()).second(0)
}

// ---------- 提醒 / 重复 ----------
const reminderOpen = ref(false)
// 提醒下拉为悬浮卡片：点卡片外任意处收起（不整个弹层）；弹层自身 clickoutside 关闭时一并复位
const onDocClickCloseReminder = (e) => {
  if (!e.target.closest?.('.tdp-reminder-wrap')) reminderOpen.value = false
}
watch(reminderOpen, (v) => {
  if (v) document.addEventListener('click', onDocClickCloseReminder, true)
  else document.removeEventListener('click', onDocClickCloseReminder, true)
})
onBeforeUnmount(() => document.removeEventListener('click', onDocClickCloseReminder, true))
const localReminders = ref([])
const localPersistent = ref(false)
const recurOpen = ref(false)
const localRecurrence = ref(null)
const recurEndDate = ref(null)

const quickIcons = [
  { icon: Sun, name: '今天', tip: '今天', days: 0, unit: 'day' },
  { icon: Sunrise, name: '明天', tip: '明天', days: 1, unit: 'day' },
  { icon: CalendarPlus, name: '下周', tip: '下周', days: 7, unit: 'day' },
  { icon: Moon, name: '下月', tip: '下月', days: 1, unit: 'month' },
]

const FREQ_UNITS = { daily: '天', weekly: '周', monthly: '月', yearly: '年' }
const freqUnit = computed(() => FREQ_UNITS[localRecurrence.value?.freq] || '')
const recurSummary = computed(() => recurrenceSummary(localRecurrence.value))

// 提醒行文案：已设提醒显示个数；全新任务（尚无日期）显示任务默认值的默认提醒预览（对齐主流待办应用）
const REMINDER_LABELS = { 0: '准时', 5: '提前 5 分钟', 30: '提前 30 分钟', 60: '提前 1 小时', 1440: '提前 1 天' }
const reminderRowText = computed(() => {
  // 已设提醒：显示友好标签（对齐主流待办应用：准时/提前N分钟/结束时），多个顿号相连
  if (localReminders.value.length) return localReminders.value.map(reminderLabel).join('、')
  if (props.dueAt || props.startAt) return '' // 已有日期的任务不预览默认值（默认值只在创建时应用）
  const s = store.settings
  if (!s) return ''
  const isAllDay = tab.value === 'range' ? rangeAllDay.value : !timeValue.value
  if (isAllDay) {
    const lbl = allDayDefaultLabel(s.default_reminder_allday)
    return lbl === '无' ? '' : `默认：${lbl}`
  }
  const m = s.default_reminder_minutes
  if (m == null) return ''
  if (m === 'end') return '默认：结束时'
  return `默认：${REMINDER_LABELS[m] ?? `提前 ${m} 分钟`}`
})
// 跳过本次：任务已保存重复规则且有日期、且调用方传入了任务 id 才可用
const canSkip = computed(() => !!(props.taskId && props.recurrence && props.dueAt))
const skipping = ref(false)

const triggerLabel = computed(() => {
  if (!props.dueAt) return '设置日期'
  const d = dayjs(props.dueAt)
  const datePart = `${d.month() + 1}月${d.date()}日`
  // 时间段：开始~结束
  if (props.startAt) {
    const s = dayjs(props.startAt)
    const timeFmt = props.allDay ? '' : ` ${s.format('HH:mm')}`
    const endTimeFmt = props.allDay ? '' : ` ${d.format('HH:mm')}`
    return `${s.format('M月D日')}${timeFmt} ~ ${datePart}${endTimeFmt}`
  }
  if (d.isSame(dayjs(), 'day')) return `今天, ${datePart}`
  if (d.isSame(dayjs().add(1, 'day'), 'day')) return `明天, ${datePart}`
  return `${datePart}${props.allDay ? '' : ' ' + d.format('HH:mm')}`
})

// 农历标签/节假日角标逻辑已抽到 utils.js（与主日历月视图共享）
const showLunar = computed(() => !!store.settings?.show_lunar)
// 节假日调休角标（设置-日期与时间-显示节假日调休）：休=法定节假日，班=调休工作日
const showHoliday = computed(() => !!store.settings?.show_holiday)

// 每周开始于（设置-日期与时间）：sunday | monday
const weekStart = computed(() => (store.settings?.week_start === 'monday' ? 1 : 0))
const weekDays = computed(() =>
  weekStart.value === 1 ? ['一', '二', '三', '四', '五', '六', '日'] : ['日', '一', '二', '三', '四', '五', '六']
)
// 显示周数（设置-日期与时间）：日历左侧周序号（周日始用 week()，周一始用 ISO 周）
const showWeekNumber = computed(() => !!store.settings?.show_week_number)

const calendarRows = computed(() => {
  const first = cursor.value.startOf('month')
  const ws = weekStart.value
  const start = first.subtract((first.day() - ws + 7) % 7, 'day')
  const last = first.endOf('month')
  const end = last.add((ws + 6 - last.day() + 7) % 7, 'day')
  const rows = []
  let row = null
  for (let d = start, i = 0; d.isBefore(end) || d.isSame(end, 'day'); d = d.add(1, 'day'), i++) {
    if (i % 7 === 0) {
      row = {
        key: d.format('YYYY-MM-DD'),
        weekNum: ws === 1 ? d.isoWeek() : d.week(),
        cells: [],
      }
      rows.push(row)
    }
    row.cells.push({
      key: d.format('YYYY-MM-DD'),
      date: d,
      inMonth: d.month() === cursor.value.month(),
      selected: selected.value && d.isSame(selected.value, 'day'),
      isToday: d.isSame(dayjs(), 'day'),
      lunar: showLunar.value ? lunarLabel(d).text : '',
      lunarFest: showLunar.value ? lunarLabel(d).fest : false,
      holiday: showHoliday.value ? holidayTag(d) : '',
    })
  }
  return rows
})

// 时间格式（设置-日期与时间）：12h 显示 上午/下午 h:mm
const timeFormat = computed(() => (store.settings?.time_format === '12h' ? '12h' : '24h'))
const elTimeFormat = computed(() => (timeFormat.value === '12h' ? 'h:mm A' : 'HH:mm'))
function fmtTime(t) {
  if (timeFormat.value !== '12h') return t.format('HH:mm')
  const h = t.hour()
  return `${h < 12 ? '上午' : '下午'}${h % 12 || 12}:${String(t.minute()).padStart(2, '0')}`
}
const timeText = computed(() => (timeValue.value ? fmtTime(dayjs(timeValue.value)) : '全天'))

// 时区（设置-日期与时间-时区）：开启后时间面板可接时区，输入时间按所选时区解释
const showTimezone = computed(() => !!store.settings?.show_timezone)
const LOCAL_TZ = -new Date().getTimezoneOffset()
function _fmtOff(min) {
  const sign = min >= 0 ? '+' : '-'
  const a = Math.abs(min)
  return `${sign}${String(Math.floor(a / 60)).padStart(2, '0')}:${String(a % 60).padStart(2, '0')}`
}
const TZ_OPTIONS = (() => {
  const list = [
    { label: '中国标准时间 (UTC+08:00)', value: 480 },
    { label: '东京/首尔 (UTC+09:00)', value: 540 },
    { label: '伦敦 (UTC+00:00)', value: 0 },
    { label: '巴黎/柏林 (UTC+01:00)', value: 60 },
    { label: '纽约 (UTC-05:00)', value: -300 },
    { label: '洛杉矶 (UTC-08:00)', value: -480 },
  ]
  if (!list.some((t) => t.value === LOCAL_TZ)) list.unshift({ label: `本地时间 (UTC${_fmtOff(LOCAL_TZ)})`, value: LOCAL_TZ })
  return list
})()
const tzOffset = ref(LOCAL_TZ)
// 输入的墙上时间按所选时区解释 → 转成本地时刻（落库仍为本地绝对时间，不改数据模型）
function applyTz(t) {
  if (!showTimezone.value || tzOffset.value === LOCAL_TZ) return t
  return t.subtract(tzOffset.value, 'minute').add(LOCAL_TZ, 'minute')
}

// 提醒快捷项的基准：当前 Tab 下的截止时刻（日期 Tab = 选中日期+时间；时间段 Tab = 结束时间）
const effectiveDue = computed(() => {
  if (tab.value === 'range') return combineRange(rangeEndDate.value, rangeEndTime.value)
  if (!selected.value) return null
  if (timeValue.value) {
    const t = dayjs(timeValue.value)
    return applyTz(selected.value.hour(t.hour()).minute(t.minute()).second(0))
  }
  return selected.value
})

function initState() {
  const d = props.dueAt ? dayjs(props.dueAt) : null
  selected.value = d ? d.startOf('day') : null
  cursor.value = d || dayjs()
  timeValue.value =
    d && !props.allDay ? new Date(d.year(), d.month(), d.date(), d.hour(), d.minute()) : null
  // 时间行默认收起（与提醒/重复同为手风琴行，点击展开）；各入口（详情栏/快速添加…）表现一致
  timeOpen.value = false

  const s = props.startAt ? dayjs(props.startAt) : null
  if (!s && !d) {
    // 全新任务（快速添加等）：时间段 Tab 预填「下一整点 ~ +默认时间段」，非全天，时间可直接改
    // （对齐主流待办应用；时长来自任务默认值 default_range_minutes）
    applyNewRangeDefaults()
  } else {
    // 无 start_at 时时间段开始默认 = 任务当前时间（对齐主流待办应用：开始时间 = 用户点击/任务的时间）
    const startBase = s || d
    rangeStartDate.value = startBase ? startBase.toDate() : null
    rangeStartTime.value = startBase && !props.allDay ? startBase.toDate() : null
    rangeEndDate.value = d ? d.toDate() : null
    rangeEndTime.value = d && !props.allDay ? d.toDate() : null
    rangeAllDay.value = props.allDay
  }
  tab.value = s ? 'range' : 'date'

  localReminders.value = (props.reminders || []).map((r) => ({ ...r }))
  localPersistent.value = !!props.persistentReminder
  customOpen.value = false
  customModeOpen.value = false
  customMode.value = 'day'
  customCount.value = 1
  customTime.value = '09:00'
  localRecurrence.value = props.recurrence ? { ...props.recurrence } : null
  recurEndDate.value = props.recurrence?.end_date ? dayjs(props.recurrence.end_date).toDate() : null
}

// 全新任务的时间段预填：开始 = 下一整点，结束 = 开始 + 默认时间段（任务默认值）
function applyNewRangeDefaults() {
  const mins = store.settings?.default_range_minutes ?? 60
  const start = dayjs().add(1, 'hour').minute(0).second(0)
  const end = start.add(mins, 'minute')
  rangeStartDate.value = start.toDate()
  rangeStartTime.value = start.toDate()
  rangeEndDate.value = end.toDate()
  rangeEndTime.value = end.toDate()
  rangeAllDay.value = false
}

// Tab 切换：进「时间段」时把「日期」Tab 已点的日期/时间带过来（开始/结束默认 = 最近点击的时间；
// 两个 Tab 视为同一份日期的两种编辑模式，跟随「日期」Tab 的最新选择覆盖）
function switchTab(t) {
  if (t === tab.value) return
  tab.value = t
  if (t !== 'range') return
  const base = selected.value
  if (!base) {
    // 未点过日期（全新任务）：预填下一整点 + 默认时间段
    applyNewRangeDefaults()
    return
  }
  const tv = timeValue.value ? dayjs(timeValue.value) : null
  const start = tv ? base.hour(tv.hour()).minute(tv.minute()).second(0) : base
  rangeStartDate.value = start.toDate()
  rangeStartTime.value = tv ? tv.toDate() : null
  rangeEndDate.value = start.toDate()
  rangeEndTime.value = tv ? tv.toDate() : null
  // 已设时间则时间段必为非全天，保证开始/结束的时间输入框可见
  rangeAllDay.value = !tv
}

function shiftMonth(n) {
  cursor.value = cursor.value.add(n, 'month')
}

function goToday() {
  cursor.value = dayjs()
}

function selectDay(d) {
  selected.value = d.startOf('day')
  cursor.value = d
}

function applyQuick(n, unit) {
  const d = dayjs().add(n, unit).startOf('day')
  selected.value = d
  cursor.value = d
}

// ---------- 提醒 ----------
function reminderText(r) {
  const base = dayjs(r.at).format('MM-DD HH:mm')
  if (r.offset_minutes == null) return base
  return r.offset_minutes === 0 ? `准时（${base}）` : `前${r.offset_minutes}分钟（${base}）`
}
// 提醒行/列表的友好标签（对齐主流待办应用）：带时间的任务与预设落点匹配则显示预设名（准时/提前N/结束时）
function reminderLabel(r) {
  if (hasTime.value) {
    const hit = reminderPresets.value.find((opt) => {
      const at = presetAt(opt)
      return at && dayjs(r.at).isSame(dayjs(at), 'minute')
    })
    if (hit) return hit.label
  }
  return reminderText(r)
}

// 是否带时间点（非全天）：时间段=结束行有时间；日期=时间行已设
const hasTime = computed(() =>
  tab.value === 'range' ? !rangeAllDay.value && !!rangeEndTime.value : !!timeValue.value
)
// 分钟档预设的锚点：时间段=开始时刻；日期+时间=该时刻（=effectiveDue）
const anchorStart = computed(() =>
  tab.value === 'range' ? combineRange(rangeStartDate.value, rangeStartTime.value) : effectiveDue.value
)
// 提醒预设（对齐主流待办应用）：全天=当天/提前1~3天/提前1周 (09:00)，落点=截止日-N 天 09:00 绝对 at；
// 带时间=准时/提前5分钟/30分钟/1小时/1天（锚开始时刻）+「结束时」（锚结束时刻）
const reminderPresets = computed(() =>
  hasTime.value
    ? [
        { key: 'ontime', label: '准时', min: 0 },
        { key: 'm5', label: '提前5分钟', min: 5 },
        { key: 'm30', label: '提前30分钟', min: 30 },
        { key: 'h1', label: '提前1小时', min: 60 },
        { key: 'd1', label: '提前1天', min: 1440 },
        { key: 'end', label: '结束时', at: 'end' },
      ]
    : [
        { key: 'd0', label: '当天', sub: '09:00', days: 0 },
        { key: 'd1', label: '提前1天', sub: '09:00', days: 1 },
        { key: 'd2', label: '提前2天', sub: '09:00', days: 2 },
        { key: 'd3', label: '提前3天', sub: '09:00', days: 3 },
        { key: 'w1', label: '提前1周', sub: '09:00', days: 7 },
      ]
)
// 预设落点：截止日-N 天的 09:00（绝对 at，不随日期漂移）；定时任务：分钟档错开始时刻/结束时=结束时刻
function presetAt(opt) {
  if (opt.at === 'end') return effectiveDue.value ? effectiveDue.value.toISOString() : null
  if (opt.min != null) {
    const base = anchorStart.value
    return base ? base.subtract(opt.min, 'minute').toISOString() : null
  }
  if (!effectiveDue.value) return null
  return effectiveDue.value.subtract(opt.days, 'day').hour(9).minute(0).second(0).toISOString()
}
function isReminderSet(opt) {
  const at = presetAt(opt)
  return !!at && localReminders.value.some((r) => dayjs(r.at).isSame(dayjs(at), 'minute'))
}
// 无日期时点提醒：自动把日期设为今天（对齐主流待办应用：设提醒隐含设日期，选项不再置灰）
function ensureDateForReminder() {
  if (tab.value === 'range') {
    // 分钟档预设错开始时刻：开始缺失时补默认（今天 09:00）
    if (!rangeStartDate.value) rangeStartDate.value = dayjs().startOf('day').toDate()
    if (!rangeStartTime.value && !rangeAllDay.value) {
      rangeStartTime.value = dayjs(rangeStartDate.value).hour(9).minute(0).second(0).toDate()
    }
    if (!rangeEndDate.value) rangeEndDate.value = dayjs().startOf('day').toDate()
  } else if (!effectiveDue.value) {
    selected.value = dayjs().startOf('day')
  }
}
function togglePresetReminder(opt) {
  ensureDateForReminder()
  const at = presetAt(opt)
  if (!at) return
  const idx = localReminders.value.findIndex((r) => dayjs(r.at).isSame(dayjs(at), 'minute'))
  if (idx >= 0) localReminders.value.splice(idx, 1)
  else localReminders.value.push({ at })
}

// 自定义提醒：「自定义」行展开 datetime 输入；已设且不匹配预设的提醒列成已选行（点击取消）
const customOpen = ref(false)
// 自定义提醒（全天，对齐主流待办应用）：按天/按周提前 + 数量 + 提醒时间 + 预览
const customMode = ref('day') // day | week
const customModeOpen = ref(false)
const customCount = ref(1)
const customTime = ref('09:00')
const customDays = computed(() => Math.max(1, customCount.value || 1) * (customMode.value === 'week' ? 7 : 1))
const customAt = computed(() => {
  if (!effectiveDue.value) return null
  const [h, m] = (customTime.value || '09:00').split(':').map(Number)
  return effectiveDue.value.subtract(customDays.value, 'day').hour(h).minute(m).second(0)
})
const customPreviewTime = computed(() => (customAt.value ? customAt.value.format('YYYY年M月D日， HH:mm') : '请先选择日期'))
function confirmCustomReminder() {
  ensureDateForReminder()
  if (!customAt.value) return
  localReminders.value.push({ at: customAt.value.toISOString() }) // 绝对 at，与全天预设一致
  customOpen.value = false
}
const customReminderRows = computed(() =>
  localReminders.value.filter(
    (r) => !reminderPresets.value.some((opt) => {
      const at = presetAt(opt)
      return at && dayjs(at).isSame(dayjs(r.at), 'minute')
    })
  )
)
function removeReminderAt(at) {
  const idx = localReminders.value.findIndex((r) => dayjs(r.at).isSame(dayjs(at), 'minute'))
  if (idx >= 0) localReminders.value.splice(idx, 1)
}

// ---------- 重复 ----------
function onFreqChange(freq) {
  if (!freq) {
    localRecurrence.value = null
    return
  }
  localRecurrence.value = {
    freq,
    interval: 1,
    by_weekday: [],
    by_monthday: [],
    end_type: 'never',
    occurrences_completed: props.recurrence?.occurrences_completed || 0,
  }
  recurEndDate.value = null
}

function buildRecurrence() {
  const r = localRecurrence.value
  if (!r) return null
  const out = { ...r }
  out.end_date = r.end_type === 'by_date' && recurEndDate.value
    ? dayjs(recurEndDate.value).endOf('day').toISOString()
    : null
  if (r.end_type !== 'after_count') out.count = null
  return out
}

// 跳过本次：立即生效，成功后关闭弹层（本地状态下次打开时由 initState 重建）
async function onSkip() {
  if (!props.taskId || skipping.value) return
  skipping.value = true
  try {
    await store.skip(props.taskId)
    ElMessage.success('已跳过本次')
    if (store.activeTaskDetail?.id === props.taskId) await store.refreshDetail()
    visible.value = false
  } catch {
    // 失败由请求拦截器统一提示
  } finally {
    skipping.value = false
  }
}

// ---------- 提交 ----------
function emitChange(patch) {
  emit('change', {
    reminders: localReminders.value,
    persistent_reminder: localPersistent.value,
    recurrence: buildRecurrence(),
    ...patch,
  })
  visible.value = false
}

function onClear() {
  // 清除：清空日期/提醒/重复（§7.5）
  localReminders.value = []
  localPersistent.value = false
  localRecurrence.value = null
  emitChange({ due_at: null, all_day: true, start_at: null })
}

function onConfirm() {
  if (tab.value === 'date') {
    if (!selected.value) {
      emitChange({ due_at: null, all_day: true, start_at: null })
      return
    }
    if (timeValue.value) {
      const t = dayjs(timeValue.value)
      const due = applyTz(selected.value.hour(t.hour()).minute(t.minute()).second(0))
      emitChange({ due_at: due.toISOString(), all_day: false, start_at: null })
    } else {
      emitChange({ due_at: selected.value.toISOString(), all_day: true, start_at: null })
    }
    return
  }
  // 时间段 Tab
  const rangeStart = combineRange(rangeStartDate.value, rangeStartTime.value)
  const rangeEnd = combineRange(rangeEndDate.value, rangeEndTime.value)
  if (!rangeStart && !rangeEnd) {
    emitChange({ due_at: null, all_day: true, start_at: null })
    return
  }
  if (!rangeEnd) {
    ElMessage.warning('请设置结束时间')
    return
  }
  if (rangeStart && rangeStart.isAfter(rangeEnd)) {
    ElMessage.warning('开始时间不能晚于结束时间')
    return
  }
  emitChange({
    due_at: rangeEnd.toISOString(),
    all_day: rangeAllDay.value,
    start_at: rangeStart ? rangeStart.toISOString() : null,
  })
}
</script>

<style scoped>
.tdp-inline-host {
  width: 100%;
}
.tdp-trigger {
  display: inline-flex;
  align-items: center;
  outline: none;
}
.tdp-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 10px;
  background: var(--ss-bg);
  border-radius: var(--ss-radius-sm);
  padding: 3px;
}
.tdp-tab {
  flex: 1;
  text-align: center;
  font-size: 13px;
  padding: 5px 0;
  border-radius: 4px;
  cursor: pointer;
  color: var(--ss-text-secondary);
}
.tdp-tab.active {
  background: #fff;
  color: var(--ss-primary);
  font-weight: 600;
  box-shadow: var(--ss-shadow);
}
.tdp-quick {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}
.tdp-quick-item {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 6px 10px;
  border-radius: var(--ss-radius-sm);
  cursor: pointer;
}
.tdp-quick-item:hover {
  background: var(--ss-primary-light);
}
.tdp-quick-icon {
  color: var(--ss-text);
}
.tdp-cal-navs {
  display: flex;
  align-items: center;
  gap: 2px;
}
.tdp-today-dot {
  width: 12px;
  height: 12px;
  border: 1.5px solid var(--ss-text-muted);
  border-radius: 50%;
  margin: 4px;
}
.tdp-today-dot:hover {
  border-color: var(--ss-primary);
}
.tdp-cal-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
}
.tdp-cal-title {
  font-size: 14px;
  font-weight: 600;
}
.tdp-nav {
  cursor: pointer;
  color: var(--ss-text-secondary);
  padding: 4px;
  border-radius: 4px;
  box-sizing: content-box;
}
.tdp-nav:hover {
  background: var(--ss-bg);
  color: var(--ss-primary);
}
.tdp-week {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr)); /* minmax(0,·) 防内容撑宽 */
  text-align: center;
  font-size: 12px;
  color: var(--ss-text-muted);
  padding: 4px 0;
}
.tdp-grid {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  text-align: center;
}
/* 显示周数：左侧加周序号列 */
.tdp-cols-8 {
  grid-template-columns: 30px repeat(7, minmax(0, 1fr));
}
.tdp-wn {
  font-size: 10px;
  color: var(--ss-text-muted);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0.8;
}
/* 节假日调休角标：休=红，班=灰 */
.tdp-day {
  position: relative;
}
.tdp-day-hd {
  position: absolute;
  top: -1px;
  right: 2px;
  font-size: 9px;
  transform: scale(0.9);
  line-height: 1;
}
.tdp-day-hd.rest {
  color: #34a853;
}
.tdp-day-hd.work {
  color: #e65d4f;
}
.tdp-day.selected .tdp-day-hd {
  color: #fff;
}
.tdp-tz {
  width: 100%;
  margin-top: 8px;
}
.tdp-day {
  height: 30px;
  line-height: 30px;
  font-size: 13px;
  border-radius: 50%;
  cursor: pointer;
  margin: 1px 2px;
}
/* 显示农历：格子变双行（阳历号数 + 农历小字），圆角改方圆 */
.tdp-grid-lunar .tdp-day {
  height: 44px;
  line-height: 1.2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
}
.tdp-day-num {
  display: block;
}
.tdp-day-lunar {
  display: block;
  font-size: 10px;
  transform: scale(0.92);
  color: var(--ss-text-muted);
  white-space: nowrap;
  max-width: 100%; /* 超长节日名不撑宽日历，省略号收尾 */
  overflow: hidden;
  text-overflow: ellipsis;
}
/* 农历节日/节气：黑色（随正文色） */
.tdp-day-lunar.fest {
  color: var(--ss-text, #303133);
}
.tdp-grid-lunar .tdp-day.selected .tdp-day-lunar,
.tdp-grid-lunar .tdp-day.today .tdp-day-lunar {
  color: inherit;
  opacity: 0.85;
}
.tdp-day:hover {
  background: var(--ss-primary-light);
}
.tdp-day.dim {
  color: var(--ss-text-muted);
  opacity: 0.5;
}
.tdp-day.today {
  color: var(--ss-primary);
  font-weight: 600;
}
.tdp-day.selected {
  background: var(--ss-primary);
  color: #fff;
  font-weight: 600;
}
.tdp-range-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.tdp-range-label {
  font-size: 13px;
  color: var(--ss-text-secondary);
  flex-shrink: 0;
}
.tdp-range-date {
  flex: 1.2;
}
.tdp-range-time {
  flex: 1;
}
.tdp-range-allday {
  justify-content: space-between;
  padding: 2px 0;
}
.tdp-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 8px 4px;
  border-top: 1px solid var(--ss-border);
  cursor: pointer;
  font-size: 13px;
}
.tdp-row-label {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 6px;
}
.tdp-row-icon {
  color: var(--ss-text-secondary);
}
.tdp-row-value {
  color: var(--ss-text-secondary);
  font-size: 12px;
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.tdp-row-clear {
  color: var(--ss-text-muted);
  cursor: pointer;
  flex-shrink: 0;
}
.tdp-row-clear:hover {
  color: var(--ss-text-primary);
}
.tdp-row-arrow {
  color: var(--ss-text-muted);
  transition: transform 0.2s;
}
.tdp-row-arrow.open {
  transform: rotate(90deg);
}
.tdp-sub-panel {
  padding: 4px 0 8px;
}
/* 提醒：悬浮下拉卡片（对齐主流待办应用）：浮在提醒行下方，不撑高主卡片 */
.tdp-reminder-wrap {
  position: relative;
}
.tdp-row.reminder-open {
  background: var(--ss-bg-hover, #f5f7fa);
  border-radius: 6px;
}
.tdp-reminder-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 20;
  margin-top: 4px;
  padding: 6px;
  background: var(--ss-bg-card, #fff);
  border: 1px solid var(--ss-border);
  border-radius: 8px;
  box-shadow: 0 6px 24px rgba(0, 0, 0, 0.12);
  max-height: 60vh; /* 自定义面板较高（预览+按钮），按视口高度自适应 */
  overflow-y: auto;
}
.tdp-reminder-list {
  display: flex;
  flex-direction: column;
}
/* 提醒选项整行（对齐主流待办应用）：纵向全宽行，hover 浅底，已选文字/打勾高亮 */
.tdp-reminder-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 10px;
  font-size: 14px;
  border-radius: 6px;
  cursor: pointer;
}
.tdp-reminder-item:hover {
  background: var(--ss-bg-hover, #f5f7fa);
}
.tdp-reminder-item.disabled {
  opacity: 0.5;
  pointer-events: none;
}
.tdp-reminder-item.active {
  color: var(--ss-primary);
}
.tdp-reminder-sub {
  color: var(--ss-text-muted);
  margin-left: 2px;
}
/* 持续提醒开关行（提醒下拉底部，对齐主流待办应用）：上方分隔线，点击不冒泡（避免收起下拉） */
.tdp-reminder-persistent {
  border-top: 1px solid var(--ss-border);
  border-radius: 0 0 6px 6px;
  margin-top: 4px;
  cursor: default;
}
.tdp-reminder-item.active .tdp-reminder-sub {
  color: var(--ss-primary);
  opacity: 0.75;
}
/* 自定义提醒结构化面板（对齐主流待办应用）：灰底输入框 + 预览 + 取消/确定 */
.tdp-custom-panel {
  margin-top: 4px;
  padding: 10px;
  border: 1px solid var(--ss-border);
  border-radius: 8px;
}
.tdp-custom-mode {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 10px;
  font-size: 13px;
  border: 1px solid var(--ss-border);
  border-radius: 6px;
  cursor: pointer;
  margin-bottom: 10px;
}
.tdp-custom-mode-menu {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 5;
  margin-top: 2px;
  background: var(--ss-bg-card, #fff);
  border: 1px solid var(--ss-border);
  border-radius: 6px;
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}
.tdp-custom-mode-item {
  padding: 7px 10px;
  cursor: pointer;
}
.tdp-custom-mode-item:hover {
  background: var(--ss-bg-hover, #f5f7fa);
}
.tdp-custom-mode-item.active {
  color: var(--ss-primary);
}
.tdp-custom-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 13px;
}
.tdp-custom-input {
  width: 130px;
  padding: 6px 8px;
  text-align: center;
  font-size: 13px;
  border: none;
  border-radius: 6px;
  background: var(--ss-bg-hover, #f5f7fa);
  color: inherit;
}
.tdp-custom-input:focus {
  outline: 1px solid var(--ss-primary);
}
.tdp-custom-preview {
  font-size: 13px;
  color: var(--ss-text-main, #303133);
  margin-bottom: 2px;
}
.tdp-custom-preview-time {
  font-size: 13px;
  color: var(--ss-primary);
  margin-bottom: 10px;
}
.tdp-custom-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.tdp-reminder-check {
  color: var(--ss-primary);
}
.tdp-recur-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.tdp-recur-label {
  font-size: 13px;
  color: var(--ss-text-secondary);
}
.tdp-recur-end {
  margin-top: 4px;
}
.tdp-recur-count {
  margin-top: 8px;
  font-size: 12px;
  color: var(--ss-text-muted);
}
.tdp-skip-row {
  margin-top: 8px;
}
.tdp-skip-btn {
  font-size: 13px;
  color: var(--ss-primary);
  cursor: pointer;
  user-select: none;
}
.tdp-skip-btn:hover {
  text-decoration: underline;
}
.tdp-skip-btn.loading {
  opacity: 0.5;
  cursor: default;
  text-decoration: none;
}
.tdp-footer {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid var(--ss-border);
}
</style>

<style>
.task-date-picker-popper {
  border-radius: 12px !important;
}
</style>
