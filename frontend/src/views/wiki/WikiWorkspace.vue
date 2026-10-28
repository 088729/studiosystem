<template>
  <div class="wiki-workspace">
    <!-- 顶栏 -->
    <header class="ws-topbar">
      <div class="ws-topbar-left">
        <el-button link @click="goBack">
          <el-icon><Back /></el-icon>&nbsp;返回库列表
        </el-button>
        <el-divider direction="vertical" />
        <span class="vault-title">{{ wikiStore.currentVault?.name || '…' }}</span>
        <el-tag v-if="uncommittedCount" size="small" type="warning" effect="plain" class="dirty-tag">
          {{ uncommittedCount }} 个未提交
        </el-tag>
      </div>
      <div class="ws-topbar-right">
        <span class="save-status" :class="{ dirty: activeTab?.dirty }">
          {{ saveStatusText }}
        </span>
        <el-tooltip v-if="lockState.lockedByOther" :content="`${lockState.lockedByOther} 正在编辑，当前只读`" placement="bottom">
          <el-tag size="small" type="danger" effect="plain">只读</el-tag>
        </el-tooltip>
        <el-tooltip content="搜索 (Ctrl+K)" placement="bottom">
          <el-icon class="topbar-icon" @click="searchVisible = true"><Search /></el-icon>
        </el-tooltip>
        <el-button v-auth="'wiki:edit'" size="small" :disabled="!activeTab || isReadonly" @click="openCommit">
          提交
        </el-button>
        <el-button v-auth="'wiki:view'" size="small" :disabled="!activeTab" @click="historyVisible = true">
          历史
        </el-button>
        <el-button v-auth="'wiki:view'" size="small" @click="openGraph">
          图谱
        </el-button>
        <el-button v-auth="'wiki:manage'" size="small" text @click="rebuildIndex">
          重建索引
        </el-button>
      </div>
    </header>

    <div class="ws-body">
      <!-- 左侧文档树 -->
      <aside class="ws-side" :style="{ width: sidebarWidth + 'px' }">
        <WikiSidebar
          :tree="wikiStore.tree"
          :active-path="activeTabPath"
          @open="openPage"
          @refresh="wikiStore.refreshTree(vaultId)"
          @create="openCreateDialog"
          @create-folder="openCreateFolderDialog"
          @rename="openRenameDialog"
          @delete="confirmDelete"
        />
        <div class="ws-resizer" @mousedown="startResize" />
      </aside>

      <!-- 中部编辑区 -->
      <main class="ws-main">
        <el-tabs
          v-model="activeTabPath"
          type="card"
          closable
          class="ws-tabs"
          @tab-remove="closeTab"
          @tab-change="onTabChange"
        >
          <el-tab-pane
            v-for="tab in tabs"
            :key="tab.path"
            :name="tab.path"
            :label="tab.title"
          />
        </el-tabs>

        <div v-if="!activeTab" class="ws-empty">
          <el-empty description="从左侧选择或新建一篇文档" />
        </div>
        <div v-show="activeTab" class="ws-editor-wrap">
          <WikiEditor
            ref="editorRef"
            :content="activeTab?.content || ''"
            :readonly="isReadonly"
            :pages="flatPages"
            :vault-id="vaultId"
            @input="onEditorInput"
            @ready="onEditorReady"
            @navigate="openPage"
            @create-request="onCreateFromLink"
          />
        </div>
        <div class="ws-statusbar">
          <span>{{ activeTab?.path || '' }}</span>
          <span v-if="activeTab?.savedAt">已保存 {{ formatTime(activeTab.savedAt) }}</span>
        </div>
      </main>

      <!-- 右侧面板 -->
      <aside class="ws-right">
        <el-tabs v-model="rightPanel" class="ws-right-tabs">
          <el-tab-pane label="大纲" name="outline">
            <div class="panel-body">
              <div
                v-for="h in outline"
                :key="h.text + h.level"
                class="outline-item"
                :style="{ paddingLeft: (h.level - 1) * 14 + 'px' }"
                @click="scrollToHeading(h)"
              >{{ h.text }}</div>
              <el-empty v-if="!outline.length" description="暂无标题" :image-size="50" />
            </div>
          </el-tab-pane>
          <el-tab-pane label="反链" name="backlinks">
            <div class="panel-body">
              <div
                v-for="bl in wikiStore.backlinks"
                :key="bl.path"
                class="backlink-item"
                @click="openPage(bl.path)"
              >
                <div class="bl-title">{{ bl.title }}</div>
                <div class="bl-path">{{ bl.path }}</div>
              </div>
              <el-empty v-if="!wikiStore.backlinks.length" description="暂无反链" :image-size="50" />
            </div>
          </el-tab-pane>
          <el-tab-pane label="标签" name="tags">
            <div class="panel-body">
              <el-tag
                v-for="t in currentTags"
                :key="t"
                class="tag-item"
                @click="searchByTag(t)"
              >#{{ t }}</el-tag>
              <el-empty v-if="!currentTags.length" description="本文暂无标签" :image-size="50" />
            </div>
          </el-tab-pane>
        </el-tabs>
      </aside>
    </div>

    <!-- 新建文档 -->
    <el-dialog v-model="createVisible" :title="createMode === 'folder' ? '新建目录' : '新建文档'" width="460px">
      <el-form label-width="80px">
        <el-form-item label="所在目录">
          <el-input :model-value="createBase || '（根目录）'" disabled />
        </el-form-item>
        <el-form-item :label="createMode === 'folder' ? '目录名' : '文件名'" required>
          <el-input v-model="createName" :placeholder="createMode === 'folder' ? '如：设计文档' : '如：会议纪要.md'" @keyup.enter="submitCreate" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="opLoading" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 重命名 / 移动 -->
    <el-dialog v-model="renameVisible" title="重命名 / 移动" width="460px">
      <el-form label-width="80px">
        <el-form-item label="当前路径">
          <el-input :model-value="renameSrc" disabled />
        </el-form-item>
        <el-form-item label="新路径" required>
          <el-input v-model="renameDst" placeholder="如：docs/新名称.md" @keyup.enter="submitRename" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="renameVisible = false">取消</el-button>
        <el-button type="primary" :loading="opLoading" @click="submitRename">确定</el-button>
      </template>
    </el-dialog>

    <!-- 提交 -->
    <el-dialog v-model="commitVisible" title="提交变更" width="460px">
      <p class="commit-tip">将提交该库当前所有未提交的变更（{{ uncommittedCount }} 项）。</p>
      <el-input v-model="commitMessage" type="textarea" :rows="3" placeholder="提交说明（可选），如：补充接口设计" />
      <template #footer>
        <el-button @click="commitVisible = false">取消</el-button>
        <el-button type="primary" :loading="opLoading" @click="submitCommit">提交</el-button>
      </template>
    </el-dialog>

    <!-- 历史 -->
    <HistoryDrawer
      v-model:visible="historyVisible"
      :vault-id="vaultId"
      :path="activeTabPath"
      :can-edit="authStore.hasPerm('wiki:edit')"
      @reverted="onReverted"
    />

    <!-- 搜索 -->
    <el-dialog v-model="searchVisible" width="560px" :show-close="false" class="wiki-search-dialog" @opened="focusSearch">
      <el-input
        ref="searchInputRef"
        v-model="searchQuery"
        placeholder="搜索标题 / 正文 / 标签…"
        clearable
        @input="debouncedSearch"
        @keyup.enter="openFirstResult"
      />
      <div class="search-results">
        <div
          v-for="(r, i) in searchResults"
          :key="r.path + r.kind"
          class="search-item"
          :class="{ active: i === 0 }"
          @click="openSearchResult(r)"
        >
          <el-tag size="small" :type="r.kind === 'title' ? 'primary' : r.kind === 'tag' ? 'success' : 'info'" effect="plain" class="sk">
            {{ { title: '标题', body: '正文', tag: '标签' }[r.kind] }}
          </el-tag>
          <span class="sr-title">{{ r.title }}</span>
          <span v-if="r.snippet" class="sr-snippet">{{ r.snippet }}</span>
        </div>
        <el-empty v-if="searchVisible && !searchResults.length" description="无匹配结果" :image-size="60" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import * as wikiApi from '@/api/wiki'
import { useWikiStore } from '@/stores/wiki'
import { useAuthStore } from '@/stores/auth'
import WikiSidebar from './components/WikiSidebar.vue'
import WikiEditor from './components/WikiEditor.vue'
import HistoryDrawer from './components/HistoryDrawer.vue'
import { useWikiLock } from './composables/useWikiLock'

const SAVE_DEBOUNCE_MS = 30 * 1000

const route = useRoute()
const router = useRouter()
const wikiStore = useWikiStore()
const authStore = useAuthStore()

const vaultId = route.params.vaultId

// ---- 标签页 ----
const tabs = ref([])
const activeTabPath = ref('')
const editorRef = ref(null)
const saveTimer = ref(null)
const sidebarWidth = ref(240)
const rightPanel = ref('outline')

const activeTab = computed(() => tabs.value.find((t) => t.path === activeTabPath.value) || null)
const uncommittedCount = computed(() => wikiStore.currentVault?.changes?.length || 0)
const isReadonly = computed(() =>
  !!lockState.lockedByOther || !authStore.hasPerm('wiki:edit')
)
const saveStatusText = computed(() => {
  if (!activeTab.value) return ''
  if (activeTab.value.dirty) return '有未保存修改'
  return activeTab.value.savedAt ? '已保存' : ''
})

// ---- 编辑锁 ----
const lockState = useWikiLock(ref(vaultId), {
  onLockedByOther: (holder) => ElMessage.warning(
    holder && holder === authStore.userInfo?.username
      ? `「${activeTabPath.value}」正由本账号的另一窗口编辑，当前为只读`
      : `他人正在编辑「${activeTabPath.value}」，当前为只读`
  ),
  onLockFree: async () => {
    // 锁释放后自动恢复编辑权
    if (activeTabPath.value && authStore.hasPerm('wiki:edit')) {
      await lockState.acquire(activeTabPath.value)
    }
  },
})

// ---- 大纲 / 标签 / 补全候选 ----
const flatPages = computed(() => {
  const out = []
  const stack = [...wikiStore.tree]
  while (stack.length) {
    const node = stack.pop()
    if (node.type === 'page') out.push({ path: node.path, title: node.name })
    if (node.children) stack.push(...node.children)
  }
  return out
})

const outline = computed(() => {
  if (!activeTab.value) return []
  const result = []
  const re = /^(#{1,3})\s+(.+)$/gm
  let m
  while ((m = re.exec(activeTab.value.content || '')) !== null) {
    result.push({ level: m[1].length, text: m[2].replace(/[*`]/g, '').trim() })
  }
  return result
})

const currentTags = computed(() => {
  if (!activeTab.value) return []
  const tags = []
  const re = /(?<![\w/])#([A-Za-z0-9_\-/\u4e00-\u9fa5]+)/g
  let m
  while ((m = re.exec(activeTab.value.content || '')) !== null) {
    const t = m[1].replace(/\/$/, '')
    if (t && !tags.includes(t)) tags.push(t)
  }
  return tags
})

// ---- 生命周期 ----
onMounted(async () => {
  await wikiStore.loadVault(vaultId)
  await wikiStore.refreshTree(vaultId)
  const initial = route.query.path
  if (initial) openPage(String(initial))

  window.addEventListener('beforeunload', onBeforeUnload)
  window.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', onBeforeUnload)
  window.removeEventListener('keydown', onKeydown)
  clearTimeout(saveTimer.value)
  lockState.release()
  flushSave()
})

function onBeforeUnload(e) {
  if (tabs.value.some((t) => t.dirty)) {
    e.preventDefault()
    e.returnValue = ''
  }
}

function onKeydown(e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    searchVisible.value = true
  } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 's') {
    e.preventDefault()
    if (!activeTab.value || isReadonly.value) return
    flushSave().then(() => openCommit())
  }
}

function goBack() {
  router.push('/wiki')
}

function openGraph() {
  const q = activeTabPath.value ? { path: activeTabPath.value } : {}
  router.push({ path: `/wiki/s/${vaultId}/graph`, query: q })
}

function formatTime(t) {
  return dayjs(t).format('HH:mm:ss')
}

// ---- 打开 / 切换 / 关闭标签 ----
// 注意：element-plus 2.9 的 el-tabs 只在用户点击时触发 tab-change（源码 setCurrentName 的
// trigger 参数），程序化改 v-model 不会触发——不存在"程序化切换后的重复事件"需要去重。

async function openPage(path) {
  if (path === activeTabPath.value) return
  await flushSave() // 设计约定：切换文档立即保存当前标签
  let tab = tabs.value.find((t) => t.path === path)
  if (!tab) {
    tab = { path, title: titleFromTree(path), content: '', dirty: false, savedAt: null }
    tabs.value.push(tab)
  } else {
    tab.title = titleFromTree(path)
  }
  activeTabPath.value = path
  router.replace({ query: { path } })

  const res = await wikiApi.fetchPageContent(vaultId, path)
  tab.content = res.content
  tab.savedAt = null
  tab.dirty = false
  syncEditorState()
  await nextTick()
  editorRef.value?.setValue(res.content)
  if (authStore.hasPerm('wiki:edit')) {
    // 统一走 acquire：后端按窗口令牌判锁，同用户其他窗口持锁 → 409 → 只读+轮询等待。
    // 不能先看 res.locked_by === 用户名就跳过——窗口级锁下那可能是别的窗口持有。
    const ok = await lockState.acquire(path)
    if (!ok) {
      tab.lockedBy = lockState.lockedByOther
    }
  } else if (res.locked_by) {
    lockState.lockedByOther = res.locked_by
  }
  await wikiStore.loadBacklinks(vaultId, path)
  editorRef.value?.focus()
}

function titleFromPath(path) {
  const name = path.split('/').pop()
  return name.endsWith('.md') ? name.slice(0, -3) : name
}

function titleFromTree(path) {
  const stack = [...wikiStore.tree]
  while (stack.length) {
    const node = stack.pop()
    if (node.type === 'page' && node.path === path) return node.name
    if (node.children) stack.push(...node.children)
  }
  return titleFromPath(path)
}

// 点击不存在的 [[双链]]：询问后创建并打开
async function onCreateFromLink(raw) {
  let target = (raw || '').split('|')[0].split('#')[0].trim()
  if (!target) return
  if (!target.endsWith('.md')) target += '.md'
  if (!authStore.hasPerm('wiki:edit')) {
    ElMessage.warning(`文档「${target}」不存在，且无创建权限`)
    return
  }
  try {
    await ElMessageBox.confirm(`文档「${target}」不存在，是否创建？`, '创建文档', {
      type: 'info',
      confirmButtonText: '创建',
      cancelButtonText: '取消',
    })
  } catch {
    return
  }
  try {
    await wikiApi.createPage(vaultId, target)
    ElMessage.success('已创建')
  } catch {
    /* 已存在等场景：直接打开 */
  }
  await wikiStore.refreshTree(vaultId)
  await openPage(target)
}

async function onTabChange(path) {
  await switchToTab(path)
}

// 切到指定标签的实际工作（closeTab 直接调用，不经 suppress 标志，
// 否则标志会被直接调用自己吃掉，URL 与内容刷新全部跳过）
async function switchToTab(path) {
  await flushSave()
  activeTabPath.value = path
  router.replace({ query: { path } })
  const tab = tabs.value.find((t) => t.path === path)
  if (tab) {
    const res = await wikiApi.fetchPageContent(vaultId, path)
    tab.content = res.content
    tab.dirty = false
    syncEditorState()
    await nextTick()
    editorRef.value?.setValue(res.content)
    await wikiStore.loadBacklinks(vaultId, path)
    if (authStore.hasPerm('wiki:edit')) {
      // 统一走 acquire：后端按窗口令牌判锁，同用户其他窗口持锁 → 409 → 只读+轮询等待
      await lockState.acquire(path)
    } else if (res.locked_by) {
      lockState.lockedByOther = res.locked_by
    }
  }
}

async function closeTab(path) {
  const tab = tabs.value.find((t) => t.path === path)
  if (tab?.dirty) {
    try {
      await ElMessageBox.confirm(`「${tab.title}」有未保存的修改，关闭前保存？`, '关闭确认', {
        type: 'warning',
        confirmButtonText: '保存并关闭',
        cancelButtonText: '取消',
        distinguishCancelAndClose: true,
      })
    } catch {
      return
    }
    await doSave(tab)
  }
  lockState.release(path) // 每个被关的标签都释放锁；useWikiLock 只会停当前页心跳
  if (activeTabPath.value === path) {
    const idx = tabs.value.findIndex((t) => t.path === path)
    const next = tabs.value[idx + 1] || tabs.value[idx - 1]
    activeTabPath.value = next ? next.path : ''
    if (next) await switchToTab(next.path)
  }
  tabs.value = tabs.value.filter((t) => t.path !== path)
  if (!tabs.value.length) router.replace({ query: {} })
}

// 文件/文件夹已不存在时的强制关闭：不弹保存（保存会重建已删文件），直接移除并切走
function forceCloseTab(path) {
  lockState.release(path)
  const wasActive = activeTabPath.value === path
  tabs.value = tabs.value.filter((t) => t.path !== path)
  if (!wasActive) return
  const next = tabs.value[0]
  activeTabPath.value = next ? next.path : ''
  if (next) onTabChange(next.path)
  if (!tabs.value.length) router.replace({ query: {} })
}

// ---- 保存 ----
function onEditorInput(value) {
  const tab = activeTab.value
  if (!tab) return
  tab.content = value
  tab.dirty = true
  clearTimeout(saveTimer.value)
  saveTimer.value = setTimeout(() => doSave(tab), SAVE_DEBOUNCE_MS)
  syncEditorState()
}

async function doSave(tab) {
  if (!tab || !tab.dirty) return
  try {
    const res = await wikiApi.savePage(vaultId, tab.path, tab.content, lockState.currentHolder())
    tab.dirty = false
    tab.savedAt = res.saved_at ? new Date(res.saved_at) : new Date()
    tab.title = res.title || tab.title
    syncEditorState()
  } catch {
    /* request.js 已统一提示 */
  }
}

async function flushSave() {
  clearTimeout(saveTimer.value)
  await doSave(activeTab.value)
}

function onEditorReady() {
  syncEditorState()
}

function syncEditorState() {
  const tab = activeTab.value
  window.__wikiEditorState = {
    vaultId,
    path: tab?.path || '',
    savedAt: tab?.savedAt?.toISOString() || null,
    dirty: !!tab?.dirty,
    lockedBy: lockState.lockedByOther || null,
  }
}

// ---- 树操作 ----
const createVisible = ref(false)
const createMode = ref('page') // page / folder
const createBase = ref('')
const createName = ref('')
const opLoading = ref(false)

function openCreateDialog(folder) {
  createMode.value = 'page'
  createBase.value = folder || ''
  createName.value = ''
  createVisible.value = true
}

function openCreateFolderDialog(folder) {
  createMode.value = 'folder'
  createBase.value = folder || ''
  createName.value = ''
  createVisible.value = true
}

async function submitCreate() {
  const name = createName.value.trim()
  if (!name) {
    ElMessage.warning('请填写名称')
    return
  }
  const path = createBase.value ? `${createBase.value}/${name}` : name
  const finalPath = createMode.value === 'folder' ? `${path}/.gitkeep` : (name.endsWith('.md') ? path : `${path}.md`)
  opLoading.value = true
  try {
    if (createMode.value === 'folder') {
      // 目录通过占位文件创建
      await wikiApi.createPage(vaultId, finalPath, '')
      await wikiApi.deletePage(vaultId, finalPath, false)
    } else {
      await wikiApi.createPage(vaultId, finalPath, `# ${name.replace(/\.md$/, '')}\n`)
    }
    ElMessage.success('创建成功')
    createVisible.value = false
    await wikiStore.refreshTree(vaultId)
    if (createMode.value === 'page') openPage(finalPath)
  } finally {
    opLoading.value = false
  }
}

const renameVisible = ref(false)
const renameSrc = ref('')
const renameDst = ref('')

function openRenameDialog(data) {
  renameSrc.value = data.path
  renameDst.value = data.path
  renameVisible.value = true
}

async function submitRename() {
  const dst = renameDst.value.trim()
  if (!dst || dst === renameSrc.value) {
    renameVisible.value = false
    return
  }
  opLoading.value = true
  try {
    await wikiApi.movePage(vaultId, renameSrc.value, dst)
    ElMessage.success('已移动')
    renameVisible.value = false
    await wikiStore.refreshTree(vaultId)
    // 目录被移动时，其下所有已打开标签要同步改前缀。
    // 树里文件夹节点的 path 是不带 .gitkeep 的目录路径，兼容旧的占位文件写法
    const moveDir = !renameSrc.value.endsWith('.md')
    const srcDir = renameSrc.value.replace(/\/\.gitkeep$/, '')
    for (const tab of tabs.value) {
      let newPath = null
      if (tab.path === renameSrc.value) {
        newPath = dst
      } else if (moveDir && tab.path.startsWith(srcDir + '/')) {
        newPath = dst + tab.path.slice(srcDir.length)
      }
      if (newPath) {
        tab.path = newPath
        tab.title = titleFromTree(newPath)
      }
    }
    if (activeTabPath.value === renameSrc.value) activeTabPath.value = dst
    else if (moveDir && activeTabPath.value.startsWith(srcDir + '/')) {
      activeTabPath.value = dst + activeTabPath.value.slice(srcDir.length)
    }
    // 程序化改 v-model 不会触发 el-tabs 的 tab-change：手动同步 URL 与调试状态，
    // 否则刷新后会按旧路径打开（文件已不存在）
    if (activeTabPath.value) router.replace({ query: { path: activeTabPath.value } })
    syncEditorState()
  } finally {
    opLoading.value = false
  }
}

function confirmDelete(data) {
  const isFolder = data.type === 'folder'
  // 预先统计受影响标签：目录删除会带走全部子文件，其中有未保存修改的要明确告知将被丢弃
  const affected = tabs.value.filter(
    (t) => t.path === data.path || t.path.startsWith(data.path + '/')
  )
  const dirtyCount = affected.filter((t) => t.dirty).length
  let message = isFolder
    ? `删除目录「${data.name}」及其全部内容？`
    : `删除「${data.name}」？`
  if (dirtyCount) message += `（其中 ${dirtyCount} 篇有未保存修改，删除后将无法恢复）`
  ElMessageBox.confirm(
    message,
    '删除确认',
    { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
  ).then(async () => {
    await wikiApi.deletePage(vaultId, data.path, isFolder)
    ElMessage.success('已删除')
    // 目录删除会带走全部子文件，所有受影响标签强制关闭（不能走 closeTab 的保存提示，会重建已删文件）
    const affected = tabs.value.filter(
      (t) => t.path === data.path || t.path.startsWith(data.path + '/')
    )
    for (const t of [...affected]) forceCloseTab(t.path)
    await wikiStore.refreshTree(vaultId)
  }).catch(() => {})
}

// ---- 提交 / 历史 / 回滚 ----
const commitVisible = ref(false)
const commitMessage = ref('')
const historyVisible = ref(false)

function openCommit() {
  flushSave().then(async () => {
    // 弹窗里的未提交数取自 currentVault.changes，保存后不刷新会一直显示过期值
    try {
      await wikiStore.refreshStatus(vaultId)
    } catch {
      /* 状态拉取失败不阻塞提交 */
    }
    commitMessage.value = ''
    commitVisible.value = true
  })
}

async function submitCommit() {
  opLoading.value = true
  try {
    const res = await wikiApi.commitVault(vaultId, commitMessage.value.trim() || undefined)
    commitVisible.value = false
    if (res.committed) {
      ElMessage.success(`已提交 ${res.files.length} 个文件`)
    } else {
      ElMessage.info(res.message)
    }
    await wikiStore.refreshStatus(vaultId)
  } finally {
    opLoading.value = false
  }
}

async function onReverted() {
  const tab = activeTab.value
  if (!tab) return
  const res = await wikiApi.fetchPageContent(vaultId, tab.path)
  tab.content = res.content
  tab.dirty = false
  editorRef.value?.setValue(res.content)
  syncEditorState()
}

async function rebuildIndex() {
  try {
    await wikiApi.rebuildIndex(vaultId)
    ElMessage.success('重建任务已启动')
    pollRebuild()
  } catch (e) {
    if (e.response?.status === 409) pollRebuild()
  }
}

async function pollRebuild() {
  const timer = setInterval(async () => {
    try {
      const detail = await wikiApi.fetchVault(vaultId)
      if (!detail.rebuild || detail.rebuild.status !== 'running') {
        clearInterval(timer)
        if (detail.rebuild?.status === 'done') {
          ElMessage.success(`索引重建完成：${detail.rebuild.result.pages} 篇文档`)
        } else if (detail.rebuild?.status === 'error') {
          ElMessage.error(`索引重建失败：${detail.rebuild.error}`)
        }
        await wikiStore.refreshTree(vaultId)
      }
    } catch {
      clearInterval(timer)
    }
  }, 2000)
}

// ---- 搜索 ----
const searchVisible = ref(false)
const searchQuery = ref('')
const searchResults = ref([])
const searchInputRef = ref(null)
let searchTimer = null

function focusSearch() {
  searchInputRef.value?.focus()
}

function debouncedSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(runSearch, 300)
}

async function runSearch() {
  const q = searchQuery.value.trim()
  if (!q) {
    searchResults.value = []
    return
  }
  // # / ＃ 前缀 → 标签搜索（大小写不敏感由后端处理）
  const tagMatch = q.match(/^[#＃]\s*(.+)$/)
  if (tagMatch) {
    searchResults.value = await wikiApi.searchPages(vaultId, '', tagMatch[1].trim())
    return
  }
  searchResults.value = await wikiApi.searchPages(vaultId, q)
}

function openSearchResult(r) {
  searchVisible.value = false
  openPage(r.path)
}

function openFirstResult() {
  if (searchResults.value.length) openSearchResult(searchResults.value[0])
}

function searchByTag(tag) {
  searchVisible.value = true
  searchQuery.value = `#${tag}`
  runSearch()
}

// ---- 大纲跳转 ----
function scrollToHeading(h) {
  const el = editorRef.value
  if (!el) return
  const editorEl = document.querySelector('.wiki-editor')
  if (!editorEl) return
  const heads = editorEl.querySelectorAll('h1, h2, h3')
  for (const head of heads) {
    if (head.textContent.trim() === h.text) {
      head.scrollIntoView({ behavior: 'smooth', block: 'start' })
      break
    }
  }
}

// ---- 侧栏拖拽 ----
function startResize(e) {
  e.preventDefault()
  const startX = e.clientX
  const startW = sidebarWidth.value
  const onMove = (ev) => {
    sidebarWidth.value = Math.min(480, Math.max(160, startW + ev.clientX - startX))
  }
  const onUp = () => {
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
  }
  document.addEventListener('mousemove', onMove)
  document.addEventListener('mouseup', onUp)
}
</script>

<style scoped>
.wiki-workspace {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--ss-bg);
}
.ws-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 12px;
  background: #fff;
  border-bottom: 1px solid var(--ss-border);
  flex-shrink: 0;
}
.ws-topbar-left {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}
.vault-title {
  font-weight: 600;
  color: var(--ss-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.dirty-tag {
  margin-left: 8px;
}
.ws-topbar-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.topbar-icon {
  cursor: pointer;
  color: var(--ss-text-secondary);
  font-size: 18px;
}
.topbar-icon:hover {
  color: var(--ss-primary);
}
.save-status {
  font-size: 12px;
  color: var(--ss-text-muted);
}
.save-status.dirty {
  color: #e6a23c;
}
.ws-body {
  flex: 1;
  display: flex;
  min-height: 0;
}
.ws-side {
  position: relative;
  flex-shrink: 0;
  background: #fff;
}
.ws-resizer {
  position: absolute;
  top: 0;
  right: -3px;
  width: 6px;
  height: 100%;
  cursor: col-resize;
  z-index: 10;
}
.ws-resizer:hover {
  background: var(--ss-primary-light);
}
.ws-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: #fff;
}
.ws-tabs {
  flex-shrink: 0;
  padding: 6px 8px 0;
}
.ws-tabs :deep(.el-tabs__header) {
  margin-bottom: 0;
}
.ws-empty {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
.ws-editor-wrap {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.ws-statusbar {
  display: flex;
  justify-content: space-between;
  padding: 4px 12px;
  font-size: 12px;
  color: var(--ss-text-muted);
  border-top: 1px solid var(--ss-border);
  flex-shrink: 0;
}
.ws-right {
  width: 240px;
  flex-shrink: 0;
  background: #fff;
  border-left: 1px solid var(--ss-border);
  display: flex;
  flex-direction: column;
}
.ws-right-tabs {
  display: flex;
  flex-direction: column;
  height: 100%;
}
.ws-right-tabs :deep(.el-tabs__content) {
  flex: 1;
  overflow-y: auto;
}
.panel-body {
  padding: 8px 12px;
}
.outline-item {
  font-size: 13px;
  color: var(--ss-text-secondary);
  padding: 4px 6px;
  cursor: pointer;
  border-radius: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.outline-item:hover {
  background: var(--ss-primary-light);
  color: var(--ss-primary);
}
.backlink-item {
  padding: 8px;
  border-radius: var(--ss-radius-sm);
  cursor: pointer;
  margin-bottom: 4px;
}
.backlink-item:hover {
  background: var(--ss-bg);
}
.bl-title {
  font-size: 13px;
  color: var(--ss-text);
  font-weight: 500;
}
.bl-path {
  font-size: 11px;
  color: var(--ss-text-muted);
  margin-top: 2px;
}
.tag-item {
  margin: 0 6px 6px 0;
  cursor: pointer;
}
.commit-tip {
  font-size: 13px;
  color: var(--ss-text-secondary);
  margin: 0 0 10px;
}
.search-results {
  margin-top: 10px;
  max-height: 50vh;
  overflow-y: auto;
}
.search-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 10px;
  border-radius: var(--ss-radius-sm);
  cursor: pointer;
}
.search-item:hover,
.search-item.active {
  background: var(--ss-primary-light);
}
.sk {
  flex-shrink: 0;
}
.sr-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--ss-text);
  flex-shrink: 0;
  max-width: 40%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sr-snippet {
  font-size: 12px;
  color: var(--ss-text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
