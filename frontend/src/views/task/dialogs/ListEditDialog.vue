<template>
  <!-- 添加/编辑清单（对齐主流待办应用样式：左侧标签 + 右侧控件，色板圆点，视图图标，底部右侧按钮） -->
  <el-dialog
    v-model="visible"
    :title="isEdit ? '编辑清单' : '添加清单'"
    width="460px"
    class="led-dialog"
  >
    <div class="led-form">
      <div class="led-row">
        <span class="led-label">名称</span>
        <el-input
          ref="nameInputRef"
          v-model="form.name"
          placeholder="名称"
          maxlength="50"
          class="led-grow led-name-input"
        >
          <template #prefix>
            <!-- 表情选择（对齐主流待办应用：输入框左侧 😊，点开面板，表情插入名称） -->
            <el-popover placement="bottom-start" trigger="click" :width="300" popper-class="led-emoji-pop">
              <template #reference>
                <span class="led-emoji-btn" title="表情"><Smile :size="16" /></span>
              </template>
              <div class="led-emoji-panel">
                <!-- 顶部横列：分类标签（点切换下方网格）+ 随机/清除（对齐主流待办应用） -->
                <div class="led-emoji-topbar">
                  <div class="led-emoji-tabs">
                    <span
                      v-for="t in EMOJI_TABS"
                      :key="t.key"
                      class="led-emoji-tab"
                      :class="{ on: activeTab === t.key }"
                      :title="t.label"
                      @click="activeTab = t.key"
                    >{{ t.icon }}</span>
                  </div>
                  <span class="led-emoji-qitem" title="随机表情" @click="insertRandomEmoji">🎲 随机</span>
                  <span class="led-emoji-qitem" title="清除名称中的表情" @click="clearEmoji">✕ 清除</span>
                </div>
                <div class="led-emoji-scroll">
                  <template v-if="activeTab === 'recent'">
                    <div v-if="!recentEmojis.length" class="led-emoji-empty">用过的表情会出现在这里</div>
                    <div class="led-emoji-grid">
                      <span v-for="e in recentEmojis" :key="`r${e}`" class="led-emoji-cell" @click="insertEmoji(e)">{{ e }}</span>
                    </div>
                  </template>
                  <template v-else>
                    <div class="led-emoji-grid">
                      <span v-for="e in currentEmojis" :key="e" class="led-emoji-cell" @click="insertEmoji(e)">{{ e }}</span>
                    </div>
                  </template>
                </div>
              </div>
            </el-popover>
          </template>
        </el-input>
      </div>
      <div class="led-row">
        <span class="led-label">颜色</span>
        <div class="led-colors">
          <span
            class="led-color-none"
            :class="{ on: !form.color }"
            title="无颜色"
            @click="form.color = null"
          >⊘</span>
          <span
            v-if="form.color && !PALETTE.includes(form.color)"
            class="led-color"
            :style="{ background: form.color }"
            :class="{ on: true }"
          />
          <span
            v-for="c in PALETTE"
            :key="c"
            class="led-color"
            :style="{ background: c }"
            :class="{ on: form.color === c }"
            @click="form.color = c"
          />
          <span class="led-color led-rainbow" :class="{ on: rainbowOn }" title="随机颜色" @click="pickRainbow" />
        </div>
      </div>
      <div class="led-row">
        <span class="led-label">视图</span>
        <div class="led-views">
          <span
            v-for="v in VIEW_OPTIONS"
            :key="v.value"
            class="led-view"
            :class="{ on: form.view === v.value, disabled: v.value === 'timeline' && form.kind === 'note' }"
            :title="v.label"
            @click="onPickView(v.value)"
          ><component :is="v.icon" :size="17" /></span>
        </div>
      </div>
      <div class="led-row">
        <span class="led-label">文件夹</span>
        <el-select v-model="form.group" class="led-grow" placeholder="无" clearable filterable allow-create default-first-option>
          <el-option v-for="g in existingGroups" :key="g" :value="g" :label="g" />
        </el-select>
      </div>
      <div class="led-row">
        <span class="led-label">类型</span>
        <el-select v-model="form.kind" class="led-grow">
          <el-option value="task" label="任务清单" />
          <el-option value="note" label="笔记清单" />
        </el-select>
      </div>
      <!-- 图标行已移除（对齐主流待办应用：清单图标 = 名称里的表情，用名称左侧 😊 选择器插入） -->
    </div>
    <template #footer>
      <div class="led-footer">
        <el-button type="primary" :disabled="!form.name.trim()" @click="submit">{{ isEdit ? '保存' : '添加' }}</el-button>
        <el-button @click="visible = false">取消</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, nextTick, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { List, SquareKanban, ChartGantt, Smile } from 'lucide-vue-next'
import { useTaskStore } from '@/stores/task'

const store = useTaskStore()

const visible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const nameInputRef = ref(null)
const PALETTE = ['#f44336', '#ff9800', '#ffc107', '#8bc34a', '#4caf50', '#4772fa', '#9c27b0']
const VIEW_OPTIONS = [
  { value: 'list', label: '列表', icon: List },
  { value: 'board', label: '看板', icon: SquareKanban },
  { value: 'timeline', label: '时间线', icon: ChartGantt },
]
const form = reactive({ name: '', color: '#4772fa', icon: null, group: null, kind: 'task', view: 'list' })

const existingGroups = computed(() => [...new Set(store.lists.map((l) => l.group).filter(Boolean))])
const rainbowOn = computed(() => !!form.color && !PALETTE.includes(form.color) && form.color !== '#4772fa')

// ---------- 名称表情（对齐主流待办应用：输入框左侧 😊 面板；最近使用 + 分类全量表情） ----------
const RECENT_KEY = 'sun_emoji_recent'
const recentEmojis = ref(JSON.parse(localStorage.getItem(RECENT_KEY) || '[]'))
// 分类标签（对齐主流待办应用：顶部横向分类栏，点标签切换下方网格）
const EMOJI_TABS = [
  { key: 'recent', icon: '🕐', label: '最近使用' },
  { key: 'faces', icon: '😀', label: '人物' },
  { key: 'gestures', icon: '🖐', label: '手势与身体' },
  { key: 'animals', icon: '🧸', label: '动物与自然' },
  { key: 'food', icon: '🍔', label: '食物与饮料' },
  { key: 'objects', icon: '💡', label: '物品' },
  { key: 'activities', icon: '⚽', label: '活动' },
  { key: 'symbols', icon: '🔣', label: '符号' },
]
const activeTab = ref('recent')
const currentEmojis = computed(() => EMOJI_CATEGORIES.find((c) => c.key === activeTab.value)?.emojis || [])
const EMOJI_CATEGORIES = [
  {
    key: 'faces',
    label: '人物',
    emojis: '😀 😃 😄 😁 😆 😅 😂 🤣 🥲 ☺️ 😊 😇 🙂 🙃 😉 😌 😍 🥰 😘 😗 😙 😚 😋 😛 😝 😜 🤪 🤨 🧐 🤓 😎 🥸 🤩 🥳 😏 😒 😞 😔 😟 😕 🙁 ☹️ 😣 😖 😫 😩 🥺 😢 😭 😤 😠 😡 🤬 🤯 😳 🥵 🥶 😱 😨 😰 😥 😓 🤗 🤔 🫡 🤭 🤫 🤥 😶 😐 😑 😬 🙄 😯 😦 😧 😮 😲 🥱 😴 🤤 😪 😵 🤐 🥴 🤢 🤮 🤧 😷 🤒 🤕 🤠 😈 👿 👹 👺 🤡 💩 👻 💀 👽 👾 🤖 🎃 😺 😸 😹 😻 😼 😽 🙀 😿 😾 🫠 🫢 🫣 🫤 🫡 🫥'.split(' '),
  },
  {
    key: 'gestures',
    label: '手势与身体',
    emojis: '👋 🤚 🖐 ✋ 🖖 👌 🤌 🤏 ✌️ 🤞 🫰 🤟 🤘 🤙 👈 👉 👆 🖕 👇 ☝️ 🫵 👍 👎 ✊ 👊 🤛 🤜 👏 🙌 🫶 👐 🤲 🤝 🙏 ✍️ 💪 🦾 🦵 🦶 👂 🦻 👃 🧠 🫀 🫁 🦷 🦴 👀 👁 👅 👄 💋 🩸'.split(' '),
  },
  {
    key: 'animals',
    label: '动物与自然',
    emojis: '🐶 🐱 🐭 🐹 🐰 🦊 🐻 🐼 🐨 🐯 🦁 🐮 🐷 🐸 🐵 🙈 🙉 🙊 🐒 🐔 🐧 🐦 🐤 🦆 🦅 🦉 🦇 🐺 🐗 🐴 🦄 🐝 🐛 🦋 🐌 🐞 🐜 🐢 🐍 🦎 🦂 🦀 🐙 🦑 🦐 🐠 🐟 🐬 🐳 🐋 🦈 🐊 🐅 🐆 🦓 🦍 🐘 🦛 🦏 🐪 🐫 🦒 🦘 🐃 🐂 🐄 🐎 🐖 🐏 🐑 🦙 🐐 🦌 🐕 🐩 🐈 🐓 🦃 🦚 🦜 🦢 🦩 🕊 🐇 🦝 🦨 🦡 🦫 🦦 🦥 🐁 🐀 🐿 🦔 🐾 🐉 🐲 🌵 🎄 🌲 🌳 🌴 🌱 🌿 ☘️ 🍀 🎍 🎋 🍃 🍂 🍁 🍄 🐚 🌾 💐 🌷 🌹 🥀 🌺 🌸 🌼 🌻 🌞 🌝 🌛 🌜 🌚 🌕 🌙 🌎 🌍 🌏 💫 ⭐ 🌟 ✨ ⚡ 🔥 🌈 ☀️ 🌤 ☁️ 🌧 ⛈ 🌩 🌨 ❄️ ☃️ ⛄️ 💨 💧 💦 ☔️ ☂️ 🌊'.split(' '),
  },
  {
    key: 'food',
    label: '食物与饮料',
    emojis: '🍏 🍎 🍐 🍊 🍋 🍌 🍉 🍇 🍓 🫐 🍈 🍒 🍑 🥭 🍍 🥥 🥝 🍅 🍆 🥑 🥦 🥬 🥒 🌶 🫑 🌽 🥕 🫒 🧄 🧅 🥔 🍠 🥐 🥯 🍞 🥖 🥨 🧀 🥚 🍳 🧈 🥞 🧇 🥓 🥩 🍗 🍖 🦴 🌭 🍔 🍟 🍕 🫓 🥪 🥙 🧆 🌮 🌯 🥗 🥘 🫕 🥫 🍝 🍜 🍲 🍛 🍣 🍱 🥟 🦪 🍤 🍙 🍚 🍘 🍥 🥠 🥮 🍢 🍡 🍧 🍨 🍦 🥧 🧁 🍰 🎂 🍮 🍭 🍬 🍫 🍿 🍩 🍪 🥛 🍼 ☕️ 🫖 🍵 🧃 🥤 🧋 🍶 🍺 🍻 🥂 🍷 🥃 🍸 🍹 🧉 🍾 🧊'.split(' '),
  },
  {
    key: 'objects',
    label: '物品',
    emojis: '⌚️ 📱 📲 💻 ⌨️ 🖥 🖨 🖱 🕹 💽 💾 💿 📀 📼 📷 📸 📹 🎥 📽 🎞 📞 ☎️ 📟 📠 📺 📻 🎙 🎚 🎛 🧭 ⏱ ⏲ ⏰ 🕰 ⌛️ ⏳ 📡 🔋 🔌 💡 🔦 🕯 🧯 🛢 💸 💵 💴 💶 💷 🪙 💰 💳 💎 ⚖️ 🪜 🧰 🪛 🔧 🔨 ⚒ 🛠 ⛏ 🪚 🔩 ⚙️ 🧱 ⛓ 🧲 💣 🧨 🪓 🔪 🗡 ⚔️ 🛡 🚬 ⚰️ 🏺 🔮 📿 🧿 💈 🔭 🔬 🕳 🩹 🩺 💊 💉 🩸 🧬 🦠 🧫 🧪 🌡 🧹 🧺 🧻 🚽 🚰 🚿 🛁 🛀 🧼 🪥 🧽 🪣 🧴 🛎 🔑 🗝 🚪 🪑 🛋 🛏 🛌 🧸 🖼 🪞 🪟 🛍 🛒 🎁 🎈 🎏 🎀 🪄 🪅 🎊 🎉 🎎 🏮 🎐 🧧 ✉️ 📩 📨 📧 💌 📥 📤 📦 🏷 📪 📫 📬 📭 📮 📯 📜 📃 📄 📑 🧾 📊 📈 📉 🗒 🗓 📆 📅 🗑 📇 🗃 🗳 🗄 📋 📁 📂 🗞 📰 📓 📔 📒 📕 📗 📘 📙 📚 📖 🔖 🧷 🔗 📎 🖇 📐 📏 🧮 📌 📍 ✂️ 🖊 🖋 ✒️ 🖌 🖍'.split(' '),
  },
  {
    key: 'activities',
    label: '活动',
    emojis: '⚽️ 🏀 🏈 ⚾️ 🥎 🎾 🏐 🏉 🥏 🎱 🏓 🏸 🏒 🏑 🥍 🏏 🥅 ⛳️ 🪁 🏹 🎣 🤿 🥊 🥋 🎽 🛹 🛼 🛷 ⛸ 🥌 🎿 ⛷ 🏂 🏋️ 🤼 🤸 ⛹️ 🤺 🤾 🏌️ 🏇 🧘 🏄 🏊 🤽 🚣 🧗 🚵 🚴 🏆 🥇 🥈 🥉 🏅 🎖 🏵 🎗 🎫 🎟 🎪 🤹 🎭 🩰 🎨 🎬 🎤 🎧 🎼 🎹 🥁 🪘 🎷 🎺 🪗 🎸 🪕 🎻 🎲 ♟ 🎯 🎳 🎮 🎰 🧩'.split(' '),
  },
  {
    key: 'symbols',
    label: '符号',
    emojis: '❤️ 🧡 💛 💚 💙 💜 🖤 🤍 🤎 💔 ❣️ 💕 💞 💓 💗 💖 💘 💝 💟 ☮️ ✝️ ☪️ 🕉 ☸️ ✡️ 🔯 🕎 ☯️ ☦️ 🛐 ⛎ ♈️ ♉️ ♊️ ♋️ ♌️ ♍️ ♎️ ♏️ ♐️ ♑️ ♒️ ♓️ 🆔 ⚛️ 🉑 ☢️ ☣️ 📴 📳 🈶 🈚️ 🈸 🈺 🈷️ ✴️ 🆚 💮 🉐 ㊙️ ㊗️ 🈴 🈵 🈹 🈲 🅰️ 🅱️ 🆎 🆑 🅾️ 🆘 ❌ ⭕️ 🛑 ⛔️ 📛 🚫 💯 💢 ♨️ 🚷 🚯 🚳 🚱 🔞 📵 🚭 ❗️ ❕ ❓ ❔ ‼️ ⁉️ 🔅 🔆 〽️ ⚠️ 🚸 🔱 ⚜️ 🔰 ♻️ ✅ 🈯️ 💹 ❇️ ✳️ ❎ 🌐 💠 Ⓜ️ 🌀 💤 🏧 🚾 ♿️ 🅿️ 🈳 🈂️ 🛂 🛃 🛄 🛅 🚹 🚺 🚼 🚻 🚮 🎦 📶 🈁 🔣 ℹ️ 🔤 🔡 🔠 🆖 🆗 🆙 🆒 🆕 🆓 0️⃣ 1️⃣ 2️⃣ 3️⃣ 4️⃣ 5️⃣ 6️⃣ 7️⃣ 8️⃣ 9️⃣ 🔟 #️⃣ *️⃣ ▶️ ⏸ ⏹ ⏺ ⏭ ⏮ ⏩ ⏪ ⏫ ⏬ ◀️ 🔼 🔽 ➡️ ⬅️ ⬆️ ⬇️ ↗️ ↘️ ↙️ ↖️ ↔️ ↩️ ↪️ 🔀 🔁 🔂 🔄 🔃 🎵 🎶 ➕ ➖ ➗ ✖️ ♾ 💲 💱 ™️ ©️ ®️ 👁‍🗨 🔚 🔙 🔛 🔝 🔜 〰️ ➰ ➿ ✔️ ☑️ 🔘 🔴 🟠 🟡 🟢 🔵 🟣 ⚫️ ⚪️ 🟤 🔺 🔻 🔸 🔹 🔶 🔷 🔳 🔲 ▪️ ▫️ ◾️ ◽️ ◼️ ◻️ 🟥 🟧 🟨 🟩 🟦 🟪 ⬛️ ⬜️ 🟫 🔈 🔇 🔉 🔊 🔔 🔕 📣 📢 💬 💭 🗯 ♠️ ♣️ ♥️ ♦️ 🃏 🎴 🀄️ 🕐 🕑 🕒 🕓 🕔 🕕 🕖 🕗 🕘 🕙 🕚 🕛'.split(' '),
  },
]
const EMOJI_RE = /[\u{1F000}-\u{1FAFF}\u{2600}-\u{27BF}\u{FE0F}\u{200D}]/gu

function nameInputEl() {
  return nameInputRef.value?.input || nameInputRef.value?.$el?.querySelector?.('input')
}
// 全部表情（随机用）
const ALL_EMOJIS = EMOJI_CATEGORIES.flatMap((c) => c.emojis)
function insertEmoji(e) {
  const el = nameInputEl()
  const s = el?.selectionStart ?? form.name.length
  const t = el?.selectionEnd ?? form.name.length
  form.name = form.name.slice(0, s) + e + form.name.slice(t)
  // 最近使用（对齐主流待办应用：面板顶部展示用过的表情，localStorage 持久化）
  recentEmojis.value = [e, ...recentEmojis.value.filter((x) => x !== e)].slice(0, 12)
  localStorage.setItem(RECENT_KEY, JSON.stringify(recentEmojis.value))
  nextTick(() => {
    el?.focus()
    el?.setSelectionRange(s + e.length, s + e.length)
  })
}
function insertRandomEmoji() {
  insertEmoji(ALL_EMOJIS[Math.floor(Math.random() * ALL_EMOJIS.length)])
}
function clearEmoji() {
  form.name = form.name.replace(EMOJI_RE, '')
  nameInputEl()?.focus()
}

function pickRainbow() {
  const hue = Math.floor(Math.random() * 360)
  form.color = hslToHex(hue, 72, 58)
}
function hslToHex(h, s, l) {
  s /= 100
  l /= 100
  const k = (n) => (n + h / 30) % 12
  const a = s * Math.min(l, 1 - l)
  const f = (n) => l - a * Math.max(-1, Math.min(k(n) - 3, Math.min(9 - k(n), 1)))
  return `#${[f(0), f(8), f(4)].map((x) => Math.round(x * 255).toString(16).padStart(2, '0')).join('')}`
}

// 笔记清单不支持时间线：选了时间线又切笔记类型 → 回退列表
function onPickView(v) {
  if (v === 'timeline' && form.kind === 'note') return
  form.view = v
}

function open(list) {
  if (list) {
    isEdit.value = true
    editingId.value = list.id
    form.name = list.name
    form.color = list.color
    form.icon = list.icon || null
    form.group = list.group || null
    form.kind = list.kind || 'task'
    const remembered = JSON.parse(localStorage.getItem('sun_task_view_modes') || '{}')[`list:${list.id}`]
    form.view = remembered || 'list'
  } else {
    isEdit.value = false
    editingId.value = null
    form.name = ''
    form.color = '#4772fa'
    form.icon = null
    form.group = null
    form.kind = 'task'
    form.view = 'list'
  }
  visible.value = true
}

async function submit() {
  const name = form.name.trim()
  if (!name) return
  const group = form.group || null
  const payload = { name, color: form.color, icon: form.icon, group, kind: form.kind }
  if (isEdit.value) {
    await store.updateList(editingId.value, payload)
    store.setViewModeFor(`list:${editingId.value}`, form.view)
  } else {
    const item = await store.createList(payload)
    store.setViewModeFor(`list:${item.id}`, form.view)
  }
  ElMessage.success('已保存')
  visible.value = false
}

defineExpose({ open })
</script>

<style scoped>
.led-form {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.led-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.led-label {
  width: 60px;
  flex-shrink: 0;
  font-size: 13px;
  color: #666;
  text-align: left;
}
.led-grow {
  flex: 1;
  min-width: 0;
}
/* 色板圆点（对齐主流待办应用） */
.led-colors {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.led-color {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  cursor: pointer;
  border: 2px solid transparent;
  flex-shrink: 0;
}
.led-color.on {
  border-color: #fff;
  box-shadow: 0 0 0 2px var(--ss-primary);
}
.led-color-none {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  border: 1.5px solid #c0c4cc;
  color: #c0c4cc;
  font-size: 12px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}
.led-color-none.on {
  border-color: var(--ss-primary);
  color: var(--ss-primary);
  box-shadow: 0 0 0 2px rgba(71, 114, 250, 0.25);
}
.led-rainbow {
  background: conic-gradient(#f44336, #ffc107, #4caf50, #4772fa, #9c27b0, #f44336);
}
/* 视图图标按钮（对齐主流待办应用） */
.led-views {
  display: flex;
  gap: 8px;
}
.led-view {
  width: 36px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  border: 1px solid var(--ss-border, #dcdfe6);
  color: var(--ss-text-secondary);
  cursor: pointer;
}
.led-view:hover {
  background: var(--ss-bg);
}
.led-view.on {
  color: var(--ss-primary);
  border-color: var(--ss-primary);
  background: rgba(71, 114, 250, 0.06);
}
.led-view.disabled {
  opacity: 0.35;
  cursor: not-allowed;
}
/* 名称输入框内表情按钮（对齐主流待办应用：悬停高亮） */
.led-emoji-btn {
  display: inline-flex;
  align-items: center;
  padding: 4px;
  border-radius: 4px;
  color: #999;
  cursor: pointer;
}
.led-emoji-btn:hover {
  background: rgba(0, 0, 0, 0.07);
  color: #666;
}
/* 顶部横列：分类标签（可横向滑动）+ 随机/清除（固定右侧，对齐主流待办应用） */
.led-emoji-topbar {
  display: flex;
  align-items: center;
  gap: 6px;
  padding-bottom: 6px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.06);
  margin-bottom: 4px;
  flex-shrink: 0;
}
.led-emoji-tabs {
  display: flex;
  align-items: center;
  gap: 2px;
  overflow-x: auto;
  scrollbar-width: none;
  flex: 1;
  min-width: 0;
}
.led-emoji-tabs::-webkit-scrollbar {
  display: none;
}
/* 分类标签（对齐主流待办应用：横向分类栏，选中高亮） */
.led-emoji-tab {
  font-size: 17px;
  width: 30px;
  height: 30px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  cursor: pointer;
  flex-shrink: 0;
  filter: grayscale(0.4);
  opacity: 0.75;
}
.led-emoji-tab:hover {
  background: rgba(0, 0, 0, 0.06);
  opacity: 1;
}
.led-emoji-tab.on {
  background: rgba(71, 114, 250, 0.12);
  filter: none;
  opacity: 1;
}
.led-emoji-empty {
  font-size: 12px;
  color: #b0b0b0;
  padding: 16px 0;
  text-align: center;
}
.led-emoji-qitem {
  font-size: 12px;
  color: #888;
  cursor: pointer;
  padding: 3px 8px;
  border-radius: 4px;
}
.led-emoji-qitem:hover {
  background: rgba(0, 0, 0, 0.06);
  color: #555;
}
.led-emoji-panel {
  display: flex;
  flex-direction: column;
}
.led-emoji-scroll {
  max-height: 300px;
  overflow-y: auto;
}
.led-emoji-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  gap: 2px;
  padding-top: 4px;
}
.led-emoji-cell {
  font-size: 18px;
  text-align: center;
  padding: 4px 0;
  border-radius: 5px;
  cursor: pointer;
  line-height: 1.2;
}
.led-emoji-cell:hover {
  background: rgba(0, 0, 0, 0.06);
}
.led-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>

<style>
/* 弹窗 teleport 到 body，标题居中需非 scoped（对齐主流待办应用添加清单） */
.led-dialog .el-dialog__header {
  text-align: center;
  justify-content: center;
}
</style>
