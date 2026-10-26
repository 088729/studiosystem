import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { ElNotification } from 'element-plus'
import dayjs from 'dayjs'
import * as taskApi from '@/api/task'
import { useTaskStore } from '@/stores/task'

// tz_offset_minutes = 本地 - UTC 的分钟数（东八区 +480）
const tzOffsetMinutes = -new Date().getTimezoneOffset()

const DEFAULT_CONFIG = { pomodoro_minutes: 25, short_break_minutes: 5, long_break_minutes: 15 }

export const usePomodoroStore = defineStore('pomodoro', () => {
  const taskStore = useTaskStore()

  // ---------- State ----------
  const current = ref(null) // running 会话
  const remainingSeconds = ref(0)
  const elapsedSeconds = ref(0)
  const mode = ref('countdown') // countdown 倒计时 | stopwatch 正计时
  const paused = ref(false)
  const soundOn = ref(localStorage.getItem('pomodoro_sound') !== 'off')
  const stats = ref({ today_completed: 0, today_minutes: 0, total_completed: 0, total_minutes: 0 })
  const focusWeek = ref([0, 0, 0, 0, 0, 0, 0]) // 近 7 天每天专注分钟（旧→新）
  const history = ref([])
  const panelVisible = ref(false)
  const lastEnded = ref(null) // 结束页 { session, extra }（额外时间可点 +MM:SS 计入）
  const phase = ref('idle') // idle | focusing | rest
  const restSeconds = ref(0)

  let _timer = null
  let _restTimer = null
  let _extraTimer = null
  let _baseMs = 0      // 计时起点（暂停恢复时后移，保证暂停不计时）
  let _pauseStartMs = 0

  // ---------- 专注设置（settings.focus_config，对齐主流待办应用专注设置） ----------
  const focusConfig = computed(() => ({
    ...DEFAULT_CONFIG,
    ...(taskStore.settings?.focus_config || {}),
  }))
  async function ensureConfig() {
    if (!taskStore.settings) await taskStore.fetchSettings().catch(() => {})
  }
  async function saveConfig(patch) {
    await ensureConfig()
    await taskStore.saveSettings({ focus_config: { ...focusConfig.value, ...patch } })
  }

  // ---------- 白噪音（第四期：WebAudio 合成，无需音频文件） ----------
  const AMBIENT_TYPES = [
    { key: 'none', name: '无声音', icon: '🔇' },
    { key: 'white', name: '白噪音', icon: '🌫️' },
    { key: 'rain', name: '雨声', icon: '🌧️' },
    { key: 'waves', name: '海浪', icon: '🌊' },
    { key: 'fire', name: '篝火', icon: '🔥' },
    { key: 'wind', name: '风声', icon: '💨' },
  ]
  const ambient = ref(localStorage.getItem('focus_ambient') || 'none')
  const ambientPlaying = ref(false)
  let _audioCtx = null
  let _ambientNodes = []

  function _noiseBuffer(seconds, color) {
    const ctx = _audioCtx
    const buf = ctx.createBuffer(1, ctx.sampleRate * seconds, ctx.sampleRate)
    const data = buf.getChannelData(0)
    let lastBrown = 0
    for (let i = 0; i < data.length; i++) {
      const w = Math.random() * 2 - 1
      if (color === 'brown') {
        lastBrown = (lastBrown + 0.02 * w) / 1.02
        data[i] = lastBrown * 3.5
      } else if (color === 'pink') {
        // 简易粉噪：滑动平均
        lastBrown = 0.98 * lastBrown + 0.02 * w
        data[i] = (lastBrown * 8 + w * 0.3) * 0.7
      } else {
        data[i] = w
      }
    }
    return buf
  }

  function _crackleBuffer(seconds) {
    const ctx = _audioCtx
    const buf = ctx.createBuffer(1, ctx.sampleRate * seconds, ctx.sampleRate)
    const data = buf.getChannelData(0)
    for (let i = 0; i < data.length; i++) {
      data[i] = Math.random() < 0.0012 ? (Math.random() * 2 - 1) * (0.4 + Math.random() * 0.6) : 0
    }
    return buf
  }

  function _stopAmbient() {
    for (const n of _ambientNodes) {
      try { n.stop?.() } catch { /* 未启动 */ }
      try { n.disconnect() } catch { /* 已断开 */ }
    }
    _ambientNodes = []
    ambientPlaying.value = false
  }

  function _chain(buffer, build) {
    const ctx = _audioCtx
    const src = ctx.createBufferSource()
    src.buffer = buffer
    src.loop = true
    const nodes = build()
    if (nodes.length) {
      src.connect(nodes[0])
      let prev = nodes[0]
      for (const n of nodes.slice(1)) {
        prev.connect(n)
        prev = n
      }
      prev.connect(ctx.destination)
    } else {
      src.connect(ctx.destination)
    }
    src.start()
    _ambientNodes.push(src, ...nodes)
  }

  async function setAmbient(key) {
    ambient.value = key
    localStorage.setItem('focus_ambient', key)
    _stopAmbient()
    if (key === 'none') return
    try {
      if (!_audioCtx) _audioCtx = new (window.AudioContext || window.webkitAudioContext)()
      await _audioCtx.resume()
      const ctx = _audioCtx
      if (key === 'white') {
        _chain(_noiseBuffer(4, 'white'), () => {
          const g = ctx.createGain()
          g.gain.value = 0.28
          return [g]
        })
      } else if (key === 'rain') {
        _chain(_noiseBuffer(4, 'white'), () => {
          const bp = ctx.createBiquadFilter()
          bp.type = 'bandpass'
          bp.frequency.value = 1100
          bp.Q.value = 0.4
          const g = ctx.createGain()
          g.gain.value = 0.5
          return [bp, g]
        })
      } else if (key === 'waves') {
        _chain(_noiseBuffer(6, 'brown'), () => {
          const lp = ctx.createBiquadFilter()
          lp.type = 'lowpass'
          lp.frequency.value = 480
          const g = ctx.createGain()
          g.gain.value = 0.32
          const lfo = ctx.createOscillator()
          lfo.frequency.value = 0.09
          const lfoGain = ctx.createGain()
          lfoGain.gain.value = 0.2
          lfo.connect(lfoGain)
          lfoGain.connect(g.gain)
          lfo.start()
          _ambientNodes.push(lfo, lfoGain)
          return [lp, g]
        })
      } else if (key === 'fire') {
        _chain(_noiseBuffer(4, 'brown'), () => {
          const lp = ctx.createBiquadFilter()
          lp.type = 'lowpass'
          lp.frequency.value = 380
          const g = ctx.createGain()
          g.gain.value = 0.22
          return [lp, g]
        })
        _chain(_crackleBuffer(6), () => {
          const hp = ctx.createBiquadFilter()
          hp.type = 'highpass'
          hp.frequency.value = 1600
          const g = ctx.createGain()
          g.gain.value = 0.55
          return [hp, g]
        })
      } else if (key === 'wind') {
        _chain(_noiseBuffer(5, 'pink'), () => {
          const bp = ctx.createBiquadFilter()
          bp.type = 'bandpass'
          bp.frequency.value = 420
          bp.Q.value = 1.6
          const g = ctx.createGain()
          g.gain.value = 0.35
          const lfo = ctx.createOscillator()
          lfo.frequency.value = 0.06
          const lfoGain = ctx.createGain()
          lfoGain.gain.value = 240
          lfo.connect(lfoGain)
          lfoGain.connect(bp.frequency)
          lfo.start()
          _ambientNodes.push(lfo, lfoGain)
          return [bp, g]
        })
      }
      ambientPlaying.value = true
    } catch { /* AudioContext 不可用（如无用户手势前）则静默失败 */ }
  }

  // ---------- 严格模式（第四期：切出标签页自动暂停，对齐主流待办应用 Web 端简化） ----------
  const strictMode = ref(localStorage.getItem('focus_strict') === '1')
  function setStrict(v) {
    strictMode.value = !!v
    localStorage.setItem('focus_strict', v ? '1' : '0')
  }
  if (typeof document !== 'undefined') {
    document.addEventListener('visibilitychange', () => {
      if (document.hidden && strictMode.value && current.value && !paused.value) {
        togglePause()
        ElNotification({ title: '严格模式', message: '切出标签页，专注已自动暂停', type: 'warning' })
      }
    })
  }

  // ---------- Getters ----------
  const isRunning = computed(() => !!current.value)
  const progress = computed(() => {
    if (!current.value) return 0
    const total = current.value.planned_minutes * 60
    return total > 0 ? Math.round(((total - remainingSeconds.value) / total) * 100) : 0
  })
  // 倒计时显示剩余，正计时显示已计时
  const displayText = computed(() => {
    const sec = mode.value === 'countdown' ? remainingSeconds.value : elapsedSeconds.value
    const m = Math.floor(sec / 60)
    const s = sec % 60
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  })
  // 正计时无固定进度，环按当分钟内秒数转动
  const displayProgress = computed(() => {
    if (mode.value === 'countdown') return progress.value
    return Math.round(((elapsedSeconds.value % 60) / 60) * 100)
  })
  const restText = computed(() => {
    const m = Math.floor(restSeconds.value / 60)
    const s = restSeconds.value % 60
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  })
  // 笔记编辑目标：进行中的会话，或结束页会话
  const noteTargetId = computed(() => current.value?.id || lastEnded.value?.session?.id || null)

  // ---------- 计时 ----------
  function _startTick() {
    _stopTick()
    _updateRemaining()
    _timer = setInterval(() => {
      _updateRemaining()
      if (mode.value === 'countdown' && remainingSeconds.value <= 0) {
        _onTimeUp()
      }
    }, 1000)
  }

  function _stopTick() {
    if (_timer) {
      clearInterval(_timer)
      _timer = null
    }
  }

  function _updateRemaining() {
    if (!current.value) return
    let elapsed = Math.max(0, Math.floor((Date.now() - _baseMs) / 1000))
    if (paused.value) elapsed -= Math.max(0, Math.floor((Date.now() - _pauseStartMs) / 1000))
    elapsed = Math.max(0, elapsed)
    elapsedSeconds.value = elapsed
    if (mode.value === 'countdown') {
      remainingSeconds.value = Math.max(0, current.value.planned_minutes * 60 - elapsed)
    }
  }

  // 提示音：WebAudio 蜂鸣，无需音频资源文件
  function _playDoneSound() {
    if (!soundOn.value) return
    try {
      const ctx = new (window.AudioContext || window.webkitAudioContext)()
      const osc = ctx.createOscillator()
      const gain = ctx.createGain()
      osc.connect(gain)
      gain.connect(ctx.destination)
      osc.frequency.value = 880
      gain.gain.setValueAtTime(0.2, ctx.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 1)
      osc.start()
      osc.stop(ctx.currentTime + 1)
      osc.onended = () => ctx.close()
    } catch {
      // 音频不可用时静默
    }
  }

  // 结束页：额外时间每秒累计，可点 +MM:SS 计入记录
  function _startExtraTick() {
    _stopExtraTick()
    _extraTimer = setInterval(() => {
      if (lastEnded.value) lastEnded.value.extra += 1
    }, 1000)
  }
  function _stopExtraTick() {
    if (_extraTimer) {
      clearInterval(_extraTimer)
      _extraTimer = null
    }
  }

  async function _enterEndedView(session) {
    lastEnded.value = { session, extra: 0 }
    phase.value = 'idle'
    _startExtraTick()
  }

  async function _onTimeUp() {
    _stopTick()
    if (!current.value) return
    const id = current.value.id
    current.value = null
    paused.value = false
    _playDoneSound()
    const updated = await taskApi.finishFocus(id).catch(() => null)
    ElNotification({ title: '番茄钟完成', message: '本次专注结束，休息一下吧 ☕', type: 'success' })
    await fetchStats()
    if (updated) await _enterEndedView(updated)
  }

  async function togglePause() {
    if (!current.value) return
    if (paused.value) {
      taskApi.resumeFocus(current.value.id).catch(() => {})
      _baseMs += Date.now() - _pauseStartMs // 暂停时长不计入计时
      paused.value = false
    } else {
      taskApi.pauseFocus(current.value.id).catch(() => {})
      _pauseStartMs = Date.now()
      paused.value = true
    }
    _updateRemaining()
  }

  // 专注中 ± 调时：改 planned_minutes（对齐主流待办应用 hover 时间区加减）
  async function adjust(deltaMinutes) {
    if (!current.value) return
    const next = Math.min(600, Math.max(1, current.value.planned_minutes + deltaMinutes))
    if (next === current.value.planned_minutes) return
    current.value = { ...current.value, planned_minutes: next }
    await taskApi.updateFocus(current.value.id, { planned_minutes: next }).catch(() => {})
    _updateRemaining()
  }

  // 专注笔记（进行中/结束页均可写，防抖由调用方控制）
  async function saveNote(note) {
    const id = noteTargetId.value
    if (!id) return
    if (current.value) current.value = { ...current.value, note }
    else if (lastEnded.value) lastEnded.value = { ...lastEnded.value, session: { ...lastEnded.value.session, note } }
    await taskApi.updateFocus(id, { note }).catch(() => {})
  }

  // 结束页：把额外时间计入记录
  async function claimExtra() {
    const sess = lastEnded.value?.session
    if (!sess || lastEnded.value.extra <= 0) return
    const add = lastEnded.value.extra
    const next = sess.actual_seconds + add
    const updated = await taskApi
      .updateFocus(sess.id, { actual_seconds: next })
      .catch(() => null)
    // 回包可能晚于「跳过休息/退出」：仅当结束页仍挂在同一会话时才回写
    if (updated && lastEnded.value?.session?.id === sess.id) {
      lastEnded.value = { session: updated, extra: 0 }
      await fetchStats()
      await fetchHistory()
    }
  }

  // 结束页 ⋯：手动编辑专注时长（分钟）
  async function editLastDuration(minutes) {
    if (!lastEnded.value) return
    const next = Math.max(1, Math.min(600, Math.round(minutes))) * 60
    const updated = await taskApi
      .updateFocus(lastEnded.value.session.id, { actual_seconds: next })
      .catch(() => null)
    if (updated) {
      lastEnded.value = { ...lastEnded.value, session: updated }
      await fetchStats()
      await fetchHistory()
    }
  }

  function toggleSound() {
    soundOn.value = !soundOn.value
    localStorage.setItem('pomodoro_sound', soundOn.value ? 'on' : 'off')
  }

  // ---------- 休息（结束页 → 开始休息：短休倒计时，本地计时） ----------
  async function startRest() {
    if (!lastEnded.value) return
    await claimExtra() // 离开结束页先把待计入时间落库
    if (!lastEnded.value) return // 落库期间被退出
    _stopExtraTick()
    phase.value = 'rest'
    restSeconds.value = focusConfig.value.short_break_minutes * 60
    _restTimer = setInterval(() => {
      restSeconds.value -= 1
      if (restSeconds.value <= 0) {
        endRest()
        _playDoneSound()
        ElNotification({ title: '休息结束', message: '该开始下一个番茄了 🍅', type: 'success' })
      }
    }, 1000)
  }
  function endRest() {
    if (_restTimer) {
      clearInterval(_restTimer)
      _restTimer = null
    }
    phase.value = 'idle'
  }

  // 退出结束页
  function dismissEnded() {
    if (phase.value === 'rest') endRest()
    claimExtra()
    _stopExtraTick()
    lastEnded.value = null
  }

  // ---------- Actions ----------
  async function start(taskId, plannedMinutes = null, presetId = null) {
    await ensureConfig()
    const minutes = plannedMinutes ?? focusConfig.value.pomodoro_minutes
    // 0 = 不限时正计时：同步 UI 模式（右键/抽屉等入口不经过模式 radio，靠这里归一）
    mode.value = minutes === 0 ? 'stopwatch' : 'countdown'
    lastEnded.value = null
    _stopExtraTick()
    const session = await taskApi.startFocus({ task_id: taskId || null, planned_minutes: minutes, preset_id: presetId || null })
    current.value = session
    paused.value = false
    phase.value = 'focusing'
    _baseMs = new Date(session.started_at).getTime()
    _startTick()
    return session
  }

  // ---------- 常用专注预设 ----------
  const presets = ref([]) // 坚持中
  const presetsArchived = ref([]) // 已归档
  const currentPreset = computed(() => {
    const pid = current.value?.preset_id
    if (!pid) return null
    return presets.value.find((p) => p.id === pid) || null
  })

  async function loadPresets() {
    const [active, archived] = await Promise.all([
      taskApi.fetchFocusPresets({ archived: false }).catch(() => ({ items: [] })),
      taskApi.fetchFocusPresets({ archived: true }).catch(() => ({ items: [] })),
    ])
    presets.value = active.items || []
    presetsArchived.value = archived.items || []
  }

  async function savePreset(data, id = null) {
    if (id) await taskApi.updateFocusPreset(id, data)
    else await taskApi.createFocusPreset(data)
    await loadPresets()
  }

  async function removePreset(id) {
    await taskApi.deleteFocusPreset(id)
    await loadPresets()
  }

  // 行 ▶ 一键按预设开始（正计时传 0）
  async function startPreset(preset) {
    if (current.value) return
    if (preset.mode === 'stopwatch') mode.value = 'stopwatch'
    await start(preset.task_id, preset.mode === 'stopwatch' ? 0 : preset.duration_minutes, preset.id)
  }

  async function finish() {
    if (!current.value) return
    _stopTick()
    const res = await taskApi.finishFocus(current.value.id)
    current.value = null
    paused.value = false
    await fetchStats()
    await _enterEndedView(res)
    return res
  }

  async function abandon() {
    if (!current.value) return
    _stopTick()
    const res = await taskApi.abandonFocus(current.value.id)
    current.value = null
    paused.value = false
    await fetchStats()
    return res
  }

  // 补记专注记录
  async function addRecord(data) {
    const session = await taskApi.addFocusRecord(data)
    await fetchStats()
    await fetchHistory()
    return session
  }

  // 页面刷新后恢复 running 会话（含暂停态）
  async function restore() {
    const res = await taskApi.fetchFocusSessions({ running_only: true })
    const session = res.items?.[0]
    if (!session) return
    current.value = session
    phase.value = 'focusing'
    mode.value = session.planned_minutes === 0 ? 'stopwatch' : mode.value // 刷新后按会话归一模式，防正计时被当倒计时自动结束
    if (session.paused_at) {
      // 暂停中：冻结在暂停时刻的有效专注时长
      const startedMs = new Date(session.started_at).getTime()
      const pausedAtMs = new Date(session.paused_at).getTime()
      const effElapsed = Math.max(0, Math.floor((pausedAtMs - startedMs) / 1000) - (session.paused_seconds || 0))
      _baseMs = Date.now() - effElapsed * 1000
      _pauseStartMs = Date.now()
      paused.value = true
    } else {
      _baseMs = new Date(session.started_at).getTime()
      paused.value = false
    }
    _startTick()
  }

  async function fetchStats() {
    stats.value = await taskApi.fetchFocusStats({ tz_offset_minutes: tzOffsetMinutes })
  }

  // 近 7 天专注趋势：取区间会话后按天聚合分钟数
  async function fetchFocusWeek() {
    const weekStart = dayjs().subtract(6, 'day').startOf('day')
    const res = await taskApi.fetchFocusSessions({ start: weekStart.toISOString() })
    const minutes = [0, 0, 0, 0, 0, 0, 0]
    for (const s of res.items || []) {
      if (s.status !== 'completed') continue
      const idx = dayjs(s.started_at).diff(weekStart, 'day')
      if (idx >= 0 && idx < 7) minutes[idx] += Math.round(s.actual_seconds / 60)
    }
    focusWeek.value = minutes
  }

  async function fetchHistory() {
    const res = await taskApi.fetchFocusSessions({})
    history.value = res.items.filter((s) => s.status !== 'running').slice(0, 20)
  }

  // 打开番茄专注=切到内容页（侧栏「专注」/任务「开始专注」等入口统一走这里）
  function openPanel() {
    ensureConfig()
    fetchStats()
    fetchHistory()
    loadPresets()
    if (taskStore.activeListKey !== 'focus') taskStore.selectList('focus')
  }

  function closePanel() {
    panelVisible.value = false
  }

  // ---------- Mini 模式小浮窗（对齐主流待办应用 ⋯ 菜单：桌面端画中画小窗） ----------
  const miniOpen = ref(false)
  function setMini(v) {
    miniOpen.value = v
  }
  // 沉浸模式全屏覆盖层（挂 TaskManager 全局，列表视图/主页 ⋯ 均可进入）
  const immersiveOpen = ref(false)
  function setImmersive(v) {
    immersiveOpen.value = v
  }
  // 待开始的关联任务（主页 chip 选择器设置，开始专注时作为 task_id；也是运行中标题的 fallback）
  const pendingTask = ref(null)
  function setPendingTask(t) {
    pendingTask.value = t
  }

  return {
    current,
    remainingSeconds,
    elapsedSeconds,
    mode,
    paused,
    soundOn,
    stats,
    focusWeek,
    history,
    panelVisible,
    lastEnded,
    phase,
    restSeconds,
    focusConfig,
    isRunning,
    progress,
    remainingText: displayText,
    displayText,
    displayProgress,
    restText,
    noteTargetId,
    presets,
    presetsArchived,
    currentPreset,
    loadPresets,
    savePreset,
    removePreset,
    startPreset,
    AMBIENT_TYPES,
    ambient,
    ambientPlaying,
    setAmbient,
    strictMode,
    setStrict,
    miniOpen,
    setMini,
    immersiveOpen,
    setImmersive,
    pendingTask,
    setPendingTask,
    ensureConfig,
    saveConfig,
    start,
    finish,
    abandon,
    togglePause,
    toggleSound,
    adjust,
    saveNote,
    claimExtra,
    editLastDuration,
    startRest,
    endRest,
    dismissEnded,
    addRecord,
    restore,
    fetchStats,
    fetchFocusWeek,
    fetchHistory,
    openPanel,
    closePanel,
  }
})
