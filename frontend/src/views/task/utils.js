import dayjs from 'dayjs'

// 相对提醒（带 offset_minutes）随 due_at 漂移：改日期时重算绝对 at（§5.3/§5.4 约定：后端只存绝对时间）
// 绝对时间提醒（无 offset_minutes）不随日期漂移，原样保留
export function recomputeReminders(reminders, newDue) {
  if (!newDue || !reminders) return reminders
  return reminders.map((r) =>
    r.offset_minutes != null
      ? { ...r, at: dayjs(newDue).subtract(r.offset_minutes, 'minute').toISOString() }
      : r
  )
}

// 全天任务默认提醒解析（§任务默认值，对齐主流待办应用：当天/提前N天/提前1周 (09:00)/自定义）
// 存储格式（复用原字符串字段，后端零改动）：'none'=无；'dN'=提前N天 09:00（d0=当天）；
// 'c:N@HH:mm'=自定义提前 N 天 HH:mm；旧值 same_day_9am/prev_day_8pm 兼容映射
export function parseAllDayDefault(v) {
  if (!v || v === 'none') return null
  if (v === 'same_day_9am') return { days: 0, time: '09:00' }
  if (v === 'prev_day_8pm') return { days: 1, time: '20:00' }
  if (/^d\d+$/.test(v)) return { days: Number(v.slice(1)), time: '09:00' }
  const m = v.match(/^c:(\d+)@(\d{2}:\d{2})$/)
  if (m) return { days: Number(m[1]), time: m[2] }
  return null
}

export function allDayDefaultLabel(v) {
  const p = parseAllDayDefault(v)
  if (!p) return '无'
  const dayLabel = p.days === 0 ? '当天' : p.days === 7 ? '提前1周' : `提前${p.days}天`
  return `${dayLabel} (${p.time})`
}

const FREQ_LABELS = { daily: '每天', weekly: '每周', monthly: '每月', yearly: '每年' }
const FREQ_UNITS = { daily: '天', weekly: '周', monthly: '月', yearly: '年' }

// 重复规则摘要，如「每天 · 已坚持 12 次」「每 2 周」
export function recurrenceSummary(recurrence) {
  if (!recurrence) return ''
  const label =
    recurrence.interval > 1
      ? `每 ${recurrence.interval} ${FREQ_UNITS[recurrence.freq] || ''}`
      : FREQ_LABELS[recurrence.freq] || ''
  const count = recurrence.occurrences_completed
    ? ` · 已坚持 ${recurrence.occurrences_completed} 次`
    : ''
  return label + count
}

// ---------- 农历/节假日（设置-日期与时间；lunar-javascript 换算） ----------
import { Solar, HolidayUtil } from 'lunar-javascript'

// 农历标签：节日/节气优先（fest=true 红色高亮），初一显示月份名，其余显示日名
export function lunarLabel(d) {
  const s = Solar.fromYmd(d.year(), d.month() + 1, d.date())
  const l = s.getLunar()
  const fest = l.getFestivals()[0] || ''
  if (fest) return { text: fest, fest: true }
  const jq = l.getJieQi()
  if (jq) return { text: jq, fest: true }
  const sfest = s.getFestivals()[0] || ''
  if (sfest) return { text: sfest, fest: true }
  return { text: l.getDay() === 1 ? l.getMonthInChinese() + '月' : l.getDayInChinese(), fest: false }
}

// 节假日调休角标：休=法定节假日，班=调休补班日
export function holidayTag(d) {
  const h = HolidayUtil.getHoliday(d.year(), d.month() + 1, d.date())
  if (!h) return ''
  return h.isWork() ? '班' : '休'
}
