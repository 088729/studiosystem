<template>
  <div class="wiki-editor-wrap">
    <div ref="editorEl" class="wiki-editor"></div>
    <!-- [[ 双链补全弹层（放在 Vditor 容器外，避免被其 DOM 操作清掉） -->
    <div
      v-if="linkHint.visible"
      class="link-hint"
      :style="{ left: linkHint.x + 'px', top: linkHint.y + 'px' }"
    >
      <div
        v-for="(p, i) in linkHint.candidates"
        :key="p.path"
        class="lh-item"
        :class="{ active: i === linkHint.index }"
        @mousedown.prevent="pickLink(p)"
      >
        <span class="lh-title">{{ p.title }}</span>
        <span class="lh-path">{{ p.path }}</span>
      </div>
      <div v-if="!linkHint.candidates.length" class="lh-empty">无匹配文档</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import Vditor from 'vditor'
import 'vditor/dist/index.css'
import 'katex/dist/katex.min.css'
import katex from 'katex'
import { uploadAttachment, attachmentUrl } from '@/api/wiki'

// Vditor 数学公式引擎使用本地 KaTeX（不走 CDN）
window.katex = window.katex || katex

const props = defineProps({
  content: { type: String, default: '' },
  readonly: { type: Boolean, default: false },
  pages: { type: Array, default: () => [] }, // [{path,title}] 补全候选
  vaultId: { type: String, default: '' }, // 附件上传/渲染用
})
const emit = defineEmits(['input', 'ready', 'navigate', 'create-request'])

const editorEl = ref(null)
let editor = null
let ready = false
let pending = null // 就绪前到达的内容，就绪后回放

function applyContent() {
  if (!editor || !ready) return
  const v = pending !== null ? pending : (props.content || '')
  pending = null
  if (v !== editor.getValue()) {
    editor.setValue(v)
  }
}

function buildToolbar() {
  if (props.readonly) return []
  return [
    'emoji', 'headings', 'bold', 'italic', 'strike', '|',
    'line', 'quote', 'list', 'ordered-list', 'check', '|',
    'code', 'inline-code', 'link', 'table', '|',
    'undo', 'redo', '|', 'edit-mode', 'preview', 'fullscreen', 'outline',
  ]
}

// ---------- [[ 双链补全 ----------
const linkHint = ref({ visible: false, x: 0, y: 0, candidates: [], index: 0, query: '', len: 0 })

function currentBlock() {
  const sel = window.getSelection()
  if (!sel.rangeCount) return null
  const range = sel.getRangeAt(0)
  let el = range.startContainer.nodeType === Node.ELEMENT_NODE
    ? range.startContainer
    : range.startContainer.parentElement
  if (!el) return null
  // data-block="0" 是 Vditor IR 所有块级元素的通用标记，优先用它快速定位块
  const byAttr = el.closest?.('[data-block="0"]')
  if (byAttr) return byAttr
  while (el && !el.classList?.contains('vditor-reset')) {
    if (/^(H1|H2|H3|H4|H5|H6|P|BLOCKQUOTE|OL|UL)$/.test(el.tagName)) return el
    el = el.parentElement
  }
  return null
}

/** 光标前文本与 [[ 触发检测 */
function detectLinkTrigger() {
  const sel = window.getSelection()
  if (!sel.rangeCount) return null
  const range = sel.getRangeAt(0)
  const block = currentBlock()
  if (!block) return null
  // 代码块 / 行内代码内不触发补全（Vditor 对代码的渲染都含 <code>/<pre>；
  // 注意 data-block="0" 是 IR 模式所有块级元素的通用标记，不能用来识别代码块）
  let el = range.startContainer.nodeType === Node.ELEMENT_NODE
    ? range.startContainer
    : range.startContainer.parentElement
  while (el && el !== block) {
    if (el.tagName === 'CODE' || el.tagName === 'PRE') return null
    el = el.parentElement
  }
  const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT)
  let before = ''
  let node = null
  let matched = false
  while ((node = walker.nextNode())) {
    if (node === range.startContainer) {
      before += node.textContent.slice(0, range.startOffset)
      matched = true
      break
    }
    before += node.textContent
  }
  if (!matched) return null
  const m = before.match(/\[\[([^\[\]\n]{0,50})$/)
  if (!m) return null
  return { query: m[1], len: m[0].length }
}

function updateLinkHint() {
  if (props.readonly || !ready) return hideLinkHint()
  const hit = detectLinkTrigger()
  if (!hit) return hideLinkHint()
  const q = hit.query.toLowerCase()
  const candidates = props.pages
    .filter((p) => !q || p.title.toLowerCase().includes(q) || p.path.toLowerCase().includes(q))
    .slice(0, 8)
  const sel = window.getSelection()
  const rect = sel.rangeCount ? sel.getRangeAt(0).getBoundingClientRect() : null
  const host = editorEl.value.getBoundingClientRect()
  // 候选列表未变化时保留当前选中位置，避免按键后 keyup 重建弹层把 index 重置回 0
  const prev = linkHint.value
  const sameList =
    prev.visible &&
    prev.candidates.length === candidates.length &&
    prev.candidates.every((p, i) => p.path === candidates[i].path)
  const index = sameList ? Math.min(prev.index, Math.max(0, candidates.length - 1)) : 0
  linkHint.value = {
    visible: true,
    x: Math.max(4, (rect ? rect.left : 40) - host.left),
    y: (rect ? rect.bottom : 80) - host.top + 6,
    candidates,
    index,
    query: hit.query,
    len: hit.len,
  }
}

function hideLinkHint() {
  linkHint.value.visible = false
}

// ---------- 双链点击跳转 ----------
const BLOCK_TAGS = /^(H1|H2|H3|H4|H5|H6|P|LI|BLOCKQUOTE|TD)$/

/** 把 [[目标|别名]] / [[目标#锚点]] / [[路径.md]] 解析为库内文档路径 */
function resolveWikiTarget(raw) {
  let target = (raw || '').split('|')[0].split('#')[0].trim()
  if (!target) return null
  if (!target.endsWith('.md')) target += '.md'
  const stem = target.slice(0, -3)
  const pages = props.pages
  return (
    pages.find((p) => p.path === target)?.path ||
    pages.find((p) => p.title === stem)?.path ||
    pages.find((p) => p.path.toLowerCase() === target.toLowerCase())?.path ||
    pages.find((p) => p.title.toLowerCase() === stem.toLowerCase())?.path ||
    null
  )
}

/** 命中测试：鼠标位置是否落在 [[...]] / ![[...]] 文本内，落在则返回目标路径 */
function hitTestWikiLink(e) {
  if (e.button !== 0 || e.ctrlKey || e.metaKey || e.altKey || e.shiftKey) return null
  const host = editorEl.value
  if (!host) return null
  let range = null
  if (document.caretRangeFromPoint) {
    range = document.caretRangeFromPoint(e.clientX, e.clientY)
  } else if (document.caretPositionFromPoint) {
    const pos = document.caretPositionFromPoint(e.clientX, e.clientY)
    if (pos) {
      range = document.createRange()
      range.setStart(pos.offsetNode, pos.offset)
      range.collapse(true)
    }
  }
  if (!range) return null
  const node = range.startContainer
  if (node.nodeType !== 3 || !host.contains(node)) return null
  let block = node.parentElement
  while (block && block !== host && !BLOCK_TAGS.test(block.tagName)) {
    block = block.parentElement
  }
  if (!block || block === host) return null

  // 汇总块内纯文本，计算鼠标位置的绝对偏移，再匹配双链区间
  const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT)
  let text = ''
  let abs = -1
  let n = null
  while ((n = walker.nextNode())) {
    if (n === node) abs = text.length + range.startOffset
    text += n.textContent
  }
  if (abs < 0) return null
  const re = /!?\[\[([^\[\]\n]+)\]\]/g
  let m = null
  while ((m = re.exec(text))) {
    if (abs >= m.index && abs <= m.index + m[0].length) {
      return { path: resolveWikiTarget(m[1]), raw: m[1] }
    }
  }
  return null
}

function onEditorMouseDown(e) {
  const hit = hitTestWikiLink(e)
  if (!hit) return
  e.preventDefault()
  e.stopPropagation()
  if (hit.path) {
    emit('navigate', hit.path)
  } else {
    emit('create-request', hit.raw)
  }
}

/** 删除光标前 len 个字符并插入文本（保持 Vditor 感知） */
function replaceBeforeCaret(len, insert) {
  const sel = window.getSelection()
  if (!sel.rangeCount) return
  const range = sel.getRangeAt(0)
  const block = currentBlock()
  if (!block) return
  const walker = document.createTreeWalker(block, NodeFilter.SHOW_TEXT)
  const spans = [] // [textNode, 已用长度(从节点头算起)]
  let node = null
  let found = false
  while ((node = walker.nextNode())) {
    if (node === range.startContainer) {
      spans.push([node, range.startOffset])
      found = true
      break
    }
    spans.push([node, node.textContent.length])
  }
  if (!found) return
  let remaining = len
  let startNode = null
  let startOffset = 0
  for (let i = spans.length - 1; i >= 0 && remaining > 0; i--) {
    const [t, off] = spans[i]
    const take = Math.min(remaining, off)
    startNode = t
    startOffset = off - take
    remaining -= take
  }
  if (remaining > 0) return
  const r = document.createRange()
  r.setStart(startNode, startOffset)
  r.setEnd(range.startContainer, range.startOffset)
  sel.removeAllRanges()
  sel.addRange(r)
  document.execCommand('delete', false)
  document.execCommand('insertText', false, insert)
}

function pickLink(page) {
  replaceBeforeCaret(linkHint.value.len, `[[${page.title}]]`)
  hideLinkHint()
}

function onKeydown(e) {
  if (!linkHint.value.visible) return
  const { candidates, index } = linkHint.value
  if (e.key === 'Escape') {
    hideLinkHint()
  } else if (e.key === 'ArrowDown') {
    e.preventDefault()
    linkHint.value.index = (index + 1) % Math.max(1, candidates.length)
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    linkHint.value.index = (index - 1 + Math.max(1, candidates.length)) % Math.max(1, candidates.length)
  } else if ((e.key === 'Enter' || e.key === 'Tab') && candidates.length) {
    e.preventDefault()
    e.stopPropagation()
    pickLink(candidates[linkHint.value.index])
  }
}

function bindLinkHint() {
  const ir = editor?.vditor?.ir?.element
  if (!ir) return
  ir.addEventListener('keyup', updateLinkHint)
  ir.addEventListener('click', () => setTimeout(updateLinkHint, 0))
  ir.addEventListener('compositionend', () => setTimeout(updateLinkHint, 0))
  ir.addEventListener('keydown', onKeydown, true)
  document.addEventListener('mousedown', onDocMouseDown)
}

function onDocMouseDown(e) {
  if (linkHint.value.visible && !e.target.closest('.link-hint')) hideLinkHint()
}

// ---------- 附件上传（粘贴/拖拽触发，Vditor 自定义 handler） ----------
const MAX_UPLOAD = 20 * 1024 * 1024
const IMAGE_RE = /\.(png|jpe?g|gif|webp|bmp|svg|ico|apng)$/i

async function uploadFiles(files) {
  if (!props.vaultId) return '当前页面缺少库上下文，无法上传附件'
  // 上传是异步的，期间编辑器可能失焦/重排，先记住插入位置
  const sel = window.getSelection()
  const caret = sel.rangeCount ? sel.getRangeAt(0).cloneRange() : null
  const parts = []
  let tip = null
  for (const file of files) {
    if (file.size > MAX_UPLOAD) {
      tip = `${file.name} 超过 20MB 上限`
      continue
    }
    try {
      const res = await uploadAttachment(props.vaultId, file)
      parts.push(IMAGE_RE.test(file.name)
        ? `![${file.name}](${res.path})`
        : `[${file.name}](${res.path})`)
    } catch {
      tip = `${file.name} 上传失败`
    }
  }
  if (parts.length) {
    if (caret) {
      const s = window.getSelection()
      s.removeAllRanges()
      s.addRange(caret)
    }
    editor?.insertValue(`\n${parts.join('\n')}\n`)
  }
  return tip || undefined // Vditor：返回字符串则作为提示展示
}

// ---------- 附件地址重写 ----------
// 正文里写的是仓库相对路径（attachments/xxx.png），渲染时改写为接口 URL
function rewriteMediaSrc() {
  if (!editorEl.value || !props.vaultId) return
  editorEl.value
    .querySelectorAll('img[src], audio[src], video[src], a[href]')
    .forEach((el) => {
      const isLink = el.tagName === 'A'
      const raw = el.getAttribute(isLink ? 'href' : 'src') || ''
      if (!raw || el.dataset.wikiRewritten) return
      if (/^(https?:|data:|blob:|mailto:|#|\/)/i.test(raw)) return
      if (!raw.startsWith('attachments/')) return
      el.setAttribute(isLink ? 'href' : 'src', attachmentUrl(props.vaultId, raw))
      el.dataset.wikiRewritten = '1'
    })
}

let mediaObserver = null
function bindMediaRewrite() {
  rewriteMediaSrc() // 首刷（只读预览模式内容已在 DOM 里）
  mediaObserver = new MutationObserver(() => rewriteMediaSrc())
  mediaObserver.observe(editorEl.value, { childList: true, subtree: true })
}

onMounted(() => {
  editor = new Vditor(editorEl.value, {
    mode: props.readonly ? 'preview' : 'ir',
    cache: { enable: false },
    toolbar: buildToolbar(),
    preview: {
      markdown: { mark: true },
      math: { engine: 'KaTeX' },
    },
    counter: { enable: true },
    lang: 'zh_CN',
    input: (value) => emit('input', value),
    upload: {
      max: MAX_UPLOAD,
      handler: uploadFiles,
    },
    after: () => {
      ready = true
      applyContent()
      bindLinkHint()
      bindMediaRewrite()
      // 双链点击跳转：委托在容器上，IR / 预览两种模式都覆盖
      editorEl.value?.addEventListener('mousedown', onEditorMouseDown)
      emit('ready')
    },
  })
})

const api = {
  getValue() {
    return editor && ready ? editor.getValue() : (pending ?? props.content ?? '')
  },
  setValue(v) {
    pending = v || ''
    applyContent()
  },
  focus() {
    editor?.focus()
  },
}

function switchReadonly(readonly) {
  if (!editor || !ready) return
  if (readonly) {
    editor.setPreviewMode('preview')
    editorEl.value?.classList.add('is-readonly')
  } else {
    editor.setPreviewMode('ir')
    editorEl.value?.classList.remove('is-readonly')
  }
}

watch(() => props.readonly, switchReadonly)
// 异步内容到达 / 标签页切换时回放
watch(() => props.content, applyContent)

onBeforeUnmount(() => {
  ready = false
  pending = null
  document.removeEventListener('mousedown', onDocMouseDown)
  editorEl.value?.removeEventListener('mousedown', onEditorMouseDown)
  mediaObserver?.disconnect()
  mediaObserver = null
  try {
    editor?.destroy()
  } catch {
    /* ignore */
  }
  editor = null
})

defineExpose({ ...api, switchReadonly })
</script>

<style scoped>
.wiki-editor-wrap {
  position: relative;
  height: 100%;
  width: 100%;
}
.wiki-editor {
  height: 100%;
  width: 100%;
}
/* 只读模式隐藏工具栏与编辑提示 */
.wiki-editor.is-readonly :deep(.vditor-toolbar) {
  display: none;
}
.link-hint {
  position: absolute;
  z-index: 2000;
  min-width: 240px;
  max-width: 360px;
  background: #fff;
  border: 1px solid var(--ss-border);
  border-radius: var(--ss-radius-sm);
  box-shadow: var(--ss-shadow-lg);
  padding: 4px;
  max-height: 280px;
  overflow-y: auto;
}
.lh-item {
  display: flex;
  flex-direction: column;
  padding: 6px 10px;
  border-radius: 4px;
  cursor: pointer;
}
.lh-item.active {
  background: var(--ss-primary-light);
}
.lh-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--ss-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.lh-path {
  font-size: 11px;
  color: var(--ss-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.lh-empty {
  padding: 10px;
  font-size: 12px;
  color: var(--ss-text-muted);
  text-align: center;
}
</style>
