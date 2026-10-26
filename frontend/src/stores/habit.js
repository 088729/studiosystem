import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as habitApi from '@/api/habit'

const tzOffsetMinutes = -new Date().getTimezoneOffset()

export const useHabitStore = defineStore('habit', () => {
  const habits = ref([])
  const loading = ref(false)
  // 习惯详情面板（对齐主流待办应用：今天视图点习惯行 → 右侧详情）：当前习惯 + 全部打卡日志
  const activeHabitId = ref(null)
  const activeLogs = ref([])
  // 习惯是否显示在智能清单「今天/最近7天」（HabitManager 菜单开关；缺省显示）
  const inSmart = ref(localStorage.getItem('habit_in_smart') !== '0')
  function setInSmart(v) {
    inSmart.value = v
    localStorage.setItem('habit_in_smart', v ? '1' : '0')
  }

  // date（YYYY-MM-DD）缺省今天：返回各习惯该日达标状态
  async function fetchHabits(date = null) {
    loading.value = true
    try {
      const params = { tz_offset_minutes: tzOffsetMinutes }
      if (date) params.date = date
      const res = await habitApi.fetchHabits(params)
      habits.value = res.items
    } finally {
      loading.value = false
    }
  }

  async function create(data) {
    await habitApi.createHabit(data)
    await fetchHabits()
  }

  async function update(id, data) {
    await habitApi.updateHabit(id, data)
    await fetchHabits()
  }

  async function remove(id) {
    await habitApi.deleteHabit(id)
    habits.value = habits.value.filter((h) => h.id !== id)
  }

  // date 默认今天；note 为打卡日志文本（「记录日志」入口）；mood 1~5 心情；amount 手动记录量；meta_only 只写心情日志
  async function checkin(id, date, note, mood, amount = null, metaOnly = false) {
    const body = {}
    if (date) body.date = date
    if (note) body.note = note
    if (mood) body.mood = mood
    if (amount) body.amount = amount
    if (metaOnly) body.meta_only = true
    await habitApi.checkinHabit(id, body, { tz_offset_minutes: tzOffsetMinutes })
    await fetchHabits()
    if (activeHabitId.value === id) activeLogs.value = await fetchLogs(id)
  }

  // 本周概览（周环条）：周一~周日每天达标习惯数/总数
  async function fetchWeek() {
    const res = await habitApi.fetchHabitWeek({ tz_offset_minutes: tzOffsetMinutes })
    return res.days || []
  }

  // 详情统计：四卡 + 月历打卡表 + 月度概览
  async function fetchStats(id, month = null) {
    const params = { tz_offset_minutes: tzOffsetMinutes }
    if (month) params.month = month
    return await habitApi.fetchHabitStats(id, params)
  }

  async function uncheckin(id, date) {
    const params = { tz_offset_minutes: tzOffsetMinutes }
    if (date) params.date = date
    await habitApi.uncheckinHabit(id, params)
    await fetchHabits()
    if (activeHabitId.value === id) activeLogs.value = await fetchLogs(id)
  }

  async function openHabit(id) {
    activeHabitId.value = id
    activeLogs.value = await fetchLogs(id)
  }

  function closeHabit() {
    activeHabitId.value = null
    activeLogs.value = []
  }

  // 跳过打卡：当天不算打卡也不打断 streak（后端置 skipped 标记）
  async function skipHabit(id, date) {
    await habitApi.skipHabit(id, date ? { date } : {}, { tz_offset_minutes: tzOffsetMinutes })
    await fetchHabits()
    if (activeHabitId.value === id) activeLogs.value = await fetchLogs(id)
  }

  // 月历点日期切换打卡：已打则取消一次（count-1），未打则补打该日
  async function toggleDate(id, date) {
    const log = activeLogs.value.find((l) => l.date === date)
    if (log) await uncheckin(id, date)
    else await checkin(id, date)
  }

  async function fetchLogs(id, params = {}) {
    const res = await habitApi.fetchHabitLogs(id, params)
    return res.items
  }

  return { habits, loading, activeHabitId, activeLogs, inSmart, setInSmart, fetchHabits, create, update, remove, checkin, uncheckin, skipHabit, openHabit, closeHabit, toggleDate, fetchLogs, fetchWeek, fetchStats }
})
