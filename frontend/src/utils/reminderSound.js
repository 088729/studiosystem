// 提醒铃声（对齐主流待办应用「设置-提醒与通知-提醒铃声」）：WebAudio 合成，无需音频素材。
// 选项与主流待办应用一致：无/默认/八音盒/非洲鼓/蜂鸣/砖块/钟声/水晶/阶梯。
// 完成提示音选项（对齐主流待办应用：无/叮/水滴/敲击/螺旋）
export const COMPLETION_SOUNDS = [
  { value: 'none', label: '无' },
  { value: 'ding', label: '叮' },
  { value: 'waterdrop', label: '水滴' },
  { value: 'knock', label: '敲击' },
  { value: 'spiral', label: '螺旋' },
]

export function completionSoundLabel(v) {
  if (v === true) return '叮' // 旧版布尔缓存兼容
  if (v === false) return '无'
  return COMPLETION_SOUNDS.find((s) => s.value === v)?.label || '叮'
}
export const REMINDER_SOUNDS = [
  { value: 'none', label: '无' },
  { value: 'default', label: '默认' },
  { value: 'music_box', label: '八音盒' },
  { value: 'african_drum', label: '非洲鼓' },
  { value: 'beep', label: '蜂鸣' },
  { value: 'brick', label: '砖块' },
  { value: 'bell', label: '钟声' },
  { value: 'crystal', label: '水晶' },
  { value: 'ladder', label: '阶梯' },
]

export function reminderSoundLabel(v) {
  return REMINDER_SOUNDS.find((s) => s.value === v)?.label || '默认'
}

let _ctx = null
function ctx() {
  if (!_ctx) _ctx = new (window.AudioContext || window.webkitAudioContext)()
  if (_ctx.state === 'suspended') _ctx.resume().catch(() => {})
  return _ctx
}

// 单音：type 波形、freq→freqEnd 滑音、起止时间、衰减；dest=输出节点（音量主增益）
function tone(c, dest, { type = 'sine', freq, freqEnd, at = 0, dur = 0.3, vol = 0.25 }) {
  const t0 = c.currentTime + at
  const osc = c.createOscillator()
  const g = c.createGain()
  osc.type = type
  osc.frequency.setValueAtTime(freq, t0)
  if (freqEnd) osc.frequency.exponentialRampToValueAtTime(freqEnd, t0 + dur)
  g.gain.setValueAtTime(0.0001, t0)
  g.gain.exponentialRampToValueAtTime(vol, t0 + 0.015)
  g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur)
  osc.connect(g).connect(dest)
  osc.start(t0)
  osc.stop(t0 + dur + 0.05)
}

// 短噪声敲击（砖块/鼓的质感）
function knock(c, dest, { at = 0, dur = 0.12, vol = 0.3, freq = 1800, q = 1 }) {
  const t0 = c.currentTime + at
  const len = Math.ceil(c.sampleRate * dur)
  const buf = c.createBuffer(1, len, c.sampleRate)
  const data = buf.getChannelData(0)
  for (let i = 0; i < len; i++) data[i] = (Math.random() * 2 - 1) * (1 - i / len)
  const src = c.createBufferSource()
  src.buffer = buf
  const f = c.createBiquadFilter()
  f.type = 'bandpass'
  f.frequency.value = freq
  f.Q.value = q
  const g = c.createGain()
  g.gain.value = vol
  src.connect(f).connect(g).connect(dest)
  src.start(t0)
}

const RECIPES = {
  // 默认：叮咚双音
  default: (c, d) => {
    tone(c, d, { freq: 880, dur: 0.25 })
    tone(c, d, { freq: 660, at: 0.22, dur: 0.4 })
  },
  // 八音盒：高音分解和弦，快衰减
  music_box: (c, d) => {
    ;[1047, 1319, 1568, 2093].forEach((f, i) => tone(c, d, { freq: f, at: i * 0.16, dur: 0.5, vol: 0.18 }))
  },
  // 非洲鼓：低频膜音下坠 ×2 + 噪声
  african_drum: (c, d) => {
    tone(c, d, { type: 'triangle', freq: 160, freqEnd: 55, dur: 0.28, vol: 0.5 })
    knock(c, d, { freq: 300, dur: 0.08, vol: 0.2 })
    tone(c, d, { type: 'triangle', freq: 140, freqEnd: 50, at: 0.3, dur: 0.32, vol: 0.5 })
    knock(c, d, { at: 0.3, freq: 260, dur: 0.08, vol: 0.2 })
  },
  // 蜂鸣：方波哔-哔
  beep: (c, d) => {
    tone(c, d, { type: 'square', freq: 988, dur: 0.16, vol: 0.12 })
    tone(c, d, { type: 'square', freq: 988, at: 0.24, dur: 0.16, vol: 0.12 })
  },
  // 砖块：短促敲击 ×2
  brick: (c, d) => {
    knock(c, d, { freq: 2000, dur: 0.07, vol: 0.4 })
    tone(c, d, { type: 'sawtooth', freq: 220, freqEnd: 110, dur: 0.08, vol: 0.15 })
    knock(c, d, { at: 0.18, freq: 1600, dur: 0.09, vol: 0.4 })
    tone(c, d, { type: 'sawtooth', freq: 180, freqEnd: 90, at: 0.18, dur: 0.1, vol: 0.15 })
  },
  // 钟声：基音+泛音长衰减
  bell: (c, d) => {
    tone(c, d, { freq: 523, dur: 1.2, vol: 0.28 })
    tone(c, d, { freq: 523 * 2.76, dur: 0.7, vol: 0.1 })
  },
  // 水晶：高音上滑 + 闪烁尾音
  crystal: (c, d) => {
    tone(c, d, { freq: 1568, freqEnd: 2093, dur: 0.35, vol: 0.2 })
    tone(c, d, { freq: 2637, at: 0.3, dur: 0.5, vol: 0.12 })
  },
  // 阶梯：上行阶梯音阶
  ladder: (c, d) => {
    ;[523, 587, 659, 784].forEach((f, i) => tone(c, d, { type: 'triangle', freq: f, at: i * 0.13, dur: 0.2, vol: 0.25 }))
  },
}

// 音量主增益（提醒音量 0-100 → 0-1）
function _master(c, volume) {
  const g = c.createGain()
  g.gain.value = Math.max(0, Math.min(100, volume ?? 80)) / 100
  g.connect(c.destination)
  return g
}

// 播放提醒铃声；key 为空/'none' 时不发声。window.__lastReminderSound/__lastReminderVolume 供 e2e 断言。
export function playReminderSound(key, volume = 80) {
  if (typeof window !== 'undefined') {
    window.__lastReminderSound = key || 'default'
    window.__lastReminderVolume = volume
  }
  if (!key || key === 'none') return
  const recipe = RECIPES[key] || RECIPES.default
  try {
    const c = ctx()
    recipe(c, _master(c, volume))
  } catch {
    // 音频不可用（无 AudioContext/自动播放限制）时静默
  }
}

// 完成提示音音色（对齐主流待办应用）
const COMPLETION_RECIPES = {
  // 叮：轻快上行两音
  ding: (c, d) => {
    tone(c, d, { freq: 1047, dur: 0.18, vol: 0.22 })
    tone(c, d, { freq: 1568, at: 0.14, dur: 0.4, vol: 0.2 })
  },
  // 水滴：高频快速下坠 + 小尾音
  waterdrop: (c, d) => {
    tone(c, d, { freq: 1200, freqEnd: 500, dur: 0.16, vol: 0.25 })
    tone(c, d, { freq: 800, freqEnd: 420, at: 0.14, dur: 0.2, vol: 0.12 })
  },
  // 敲击：干脆一击
  knock: (c, d) => {
    knock(c, d, { freq: 1400, dur: 0.09, vol: 0.4 })
    tone(c, d, { type: 'triangle', freq: 320, freqEnd: 160, dur: 0.1, vol: 0.2 })
  },
  // 螺旋：快速盘旋音阶
  spiral: (c, d) => {
    ;[660, 880, 660, 990, 880, 1175].forEach((f, i) => tone(c, d, { type: 'triangle', freq: f, at: i * 0.07, dur: 0.1, vol: 0.18 }))
  },
}

// 完成提示音（对齐主流待办应用「完成提示音」）。window.__lastCompletionSound 供 e2e 断言。
export function playCompletionSound(key, volume = 80) {
  if (key === true) key = 'ding' // 旧版布尔缓存兼容
  if (typeof window !== 'undefined') window.__lastCompletionSound = key || 'ding'
  if (!key || key === 'none' || key === false) return
  const recipe = COMPLETION_RECIPES[key] || COMPLETION_RECIPES.ding
  try {
    const c = ctx()
    recipe(c, _master(c, volume))
  } catch {
    // 静默
  }
}
