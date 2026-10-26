<template>
  <div class="vault-manager">
    <div class="vm-header">
      <h2 class="vm-title">知识库</h2>
      <div class="vm-header-actions">
        <el-button v-auth="'wiki:manage'" @click="openImport">
          <el-icon><Upload /></el-icon>&nbsp;导入本地库
        </el-button>
        <el-button v-auth="'wiki:manage'" type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>&nbsp;新建文档库
        </el-button>
      </div>
    </div>

    <div v-if="loading" class="vm-loading" v-loading="true" element-loading-text="加载中" />

    <el-empty v-else-if="!vaults.length" description="还没有文档库">
      <el-button v-auth="'wiki:manage'" type="primary" @click="openCreate">新建文档库</el-button>
    </el-empty>

    <div v-else class="vm-grid">
      <div
        v-for="vault in vaults"
        :key="vault.id"
        class="vault-card"
        :class="{ 'is-busy': isBusy(vault), 'is-error': vault.status === 'error' }"
        @click="enterVault(vault)"
      >
        <div class="vault-card-header">
          <el-icon class="vault-icon"><Notebook /></el-icon>
          <span class="vault-name">{{ vault.name }}</span>
          <el-tag v-if="vault.status === 'error'" type="danger" size="small" effect="light">失败</el-tag>
          <el-dropdown
            trigger="click"
            class="vault-actions"
            @command="(cmd) => handleCommand(cmd, vault)"
            @click.stop
          >
            <el-icon class="more-icon" @click.stop><MoreFilled /></el-icon>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="settings" v-auth="'wiki:manage'">设置</el-dropdown-item>
                <el-dropdown-item command="pull" v-auth="'wiki:manage'" :disabled="!vault.remote_url || isBusy(vault)">拉取远程</el-dropdown-item>
                <el-dropdown-item command="push" v-auth="'wiki:manage'" :disabled="!vault.remote_url || isBusy(vault)">推送远程</el-dropdown-item>
                <el-dropdown-item command="delete" v-auth="'wiki:manage'" divided>删除</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
        <div class="vault-desc">{{ vault.description || '暂无描述' }}</div>
        <div class="vault-meta">
          <span class="meta-item">
            <el-icon><Document /></el-icon>{{ docCountMap[vault.id] ?? '…' }}
          </span>
          <span class="meta-item" v-if="vault.remote_url" title="已配置远程仓库">
            <el-icon><Connection /></el-icon>远程
          </span>
          <span class="meta-item">
            <el-icon><Clock /></el-icon>{{ formatTime(vault.updated_at) }}
          </span>
        </div>
        <div v-if="changeCountMap[vault.id]" class="vault-dirty" :title="`${changeCountMap[vault.id]} 个未提交变更`">
          {{ changeCountMap[vault.id] }} 个未提交
        </div>
        <!-- 克隆/导入/索引中：遮罩进度 -->
        <div v-if="isBusy(vault)" class="vault-busy">
          <el-progress :percentage="100" :indeterminate="true" :stroke-width="6" style="width: 80%" />
          <div class="busy-label">{{ statusLabel(vault.status) }}</div>
        </div>
        <!-- 失败原因 -->
        <div v-else-if="vault.status === 'error'" class="vault-error" :title="vault.status_message">
          {{ vault.status_message || '初始化失败' }}
        </div>
      </div>
    </div>

    <!-- 新建库 -->
    <el-dialog v-model="createVisible" title="新建文档库" width="480px">
      <el-form label-width="90px">
        <el-form-item label="库名" required>
          <el-input v-model="createForm.name" placeholder="如：团队知识库" maxlength="50" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="createForm.description" type="textarea" :rows="2" maxlength="200" />
        </el-form-item>
        <el-form-item label="远程地址">
          <el-input v-model="createForm.remote_url" placeholder="https/ssh 地址，留空创建空库" />
        </el-form-item>
        <el-form-item label="自动提交">
          <el-input-number v-model="createForm.auto_commit_interval" :min="0" :step="60" />
          <span class="form-hint">秒，0 表示关闭</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 导入本地库 -->
    <el-dialog v-model="importVisible" title="导入本地库" width="520px">
      <el-form label-width="90px">
        <el-form-item label="导入方式">
          <el-radio-group v-model="importForm.mode">
            <el-radio value="zip">上传 zip 压缩包</el-radio>
            <el-radio value="dir">服务器本地目录</el-radio>
          </el-radio-group>
        </el-form-item>
        <template v-if="importForm.mode === 'zip'">
          <el-form-item label="压缩包" required>
            <el-upload
              drag
              :auto-upload="false"
              :limit="1"
              accept=".zip"
              :on-change="(f) => { importForm.file = f.raw }"
              :on-remove="() => { importForm.file = null }"
              style="width: 100%"
            >
              <el-icon size="40" color="var(--ss-text-muted)"><UploadFilled /></el-icon>
              <div class="el-upload__text">拖拽 zip 到此处，或 <em>点击选择</em></div>
            </el-upload>
          </el-form-item>
        </template>
        <template v-else>
          <el-form-item label="目录路径" required>
            <el-input v-model="importForm.dirPath" placeholder="服务器上的绝对路径，如 D:\notes" />
          </el-form-item>
        </template>
        <el-form-item label="库名">
          <el-input v-model="importForm.name" placeholder="留空则按压缩包/目录名自动命名" maxlength="50" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" :loading="importing" @click="submitImport">开始导入</el-button>
      </template>
    </el-dialog>

    <!-- 库设置 -->
    <el-dialog v-model="settingsVisible" title="库设置" width="480px">
      <el-form label-width="90px">
        <el-form-item label="库名">
          <el-input v-model="settingsForm.name" maxlength="50" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="settingsForm.description" type="textarea" :rows="2" maxlength="200" />
        </el-form-item>
        <el-form-item label="远程地址">
          <el-input v-model="settingsForm.remote_url" placeholder="https/ssh 地址" />
        </el-form-item>
        <el-form-item label="自动提交">
          <el-input-number v-model="settingsForm.auto_commit_interval" :min="0" :step="60" />
          <span class="form-hint">秒，0 表示关闭</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="settingsVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="submitSettings">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import dayjs from 'dayjs'
import * as wikiApi from '@/api/wiki'
import { useWikiStore } from '@/stores/wiki'

const router = useRouter()
const wikiStore = useWikiStore()

const loading = ref(false)
const creating = ref(false)
const importing = ref(false)
const vaults = ref([])
const docCountMap = ref({})
const changeCountMap = ref({})

const createVisible = ref(false)
const createForm = reactive({ name: '', description: '', remote_url: '', auto_commit_interval: 300 })

const importVisible = ref(false)
const importForm = reactive({ mode: 'zip', file: null, dirPath: '', name: '' })

// ---- 克隆/导入状态轮询 ----
const BUSY_STATUSES = ['cloning', 'indexing', 'importing']
const STATUS_LABELS = {
  cloning: '正在克隆远程仓库…',
  indexing: '正在构建索引…',
  importing: '正在导入…',
}
const pollers = {} // vaultId -> timer

function isBusy(vault) {
  return BUSY_STATUSES.includes(vault.status)
}

function statusLabel(status) {
  return STATUS_LABELS[status] || '处理中…'
}

function stopPoller(vid) {
  if (pollers[vid]) {
    clearTimeout(pollers[vid])
    delete pollers[vid]
  }
}

function pollVault(vid) {
  stopPoller(vid)
  const tick = async () => {
    try {
      const detail = await wikiApi.fetchVault(vid)
      if (detail.status === 'ready') {
        ElMessage.success('文档库已就绪')
        await loadAll()
        return
      }
      if (detail.status === 'error') {
        ElMessage.error(detail.status_message || '初始化失败')
        await loadAll()
        return
      }
      pollers[vid] = setTimeout(tick, 1500)
    } catch {
      pollers[vid] = setTimeout(tick, 3000)
    }
  }
  pollers[vid] = setTimeout(tick, 1500)
}

function ensurePollers() {
  for (const v of vaults.value) {
    if (isBusy(v) && !pollers[v.id]) pollVault(v.id)
    if (!isBusy(v) && v.status !== 'error') stopPoller(v.id)
  }
}

const settingsVisible = ref(false)
const settingsForm = reactive({ id: '', name: '', description: '', remote_url: '', auto_commit_interval: 300 })

async function loadAll() {
  loading.value = true
  try {
    await wikiStore.fetchVaults()
    vaults.value = wikiStore.vaults
    // 批量概览接口一次拿全部库的文档数/未提交数，避免 per-vault N+1
    try {
      const res = await wikiApi.fetchVaultsOverview()
      for (const o of res.items || []) {
        docCountMap.value[o.id] = o.doc_count
        changeCountMap.value[o.id] = o.change_count
        // 列表接口可能滞后，用概览状态校准 busy 标记
        const v = vaults.value.find((x) => x.id === o.id)
        if (v) {
          if (v.status !== o.status) v.status = o.status
          if (o.status_message) v.status_message = o.status_message
        }
      }
    } catch {
      /* 概览失败不阻塞列表 */
    }
    ensurePollers()
  } finally {
    loading.value = false
  }
}

function formatTime(t) {
  return t ? dayjs(t).format('MM-DD HH:mm') : '-'
}

function enterVault(vault) {
  if (isBusy(vault)) {
    ElMessage.info(statusLabel(vault.status))
    return
  }
  if (vault.status === 'error') {
    ElMessage.error(vault.status_message || '该库初始化失败，可在设置中检查或删除重建')
    return
  }
  router.push(`/wiki/s/${vault.id}`)
}

function openCreate() {
  Object.assign(createForm, { name: '', description: '', remote_url: '', auto_commit_interval: 300 })
  createVisible.value = true
}

async function submitCreate() {
  if (!createForm.name.trim()) {
    ElMessage.warning('请填写库名')
    return
  }
  creating.value = true
  try {
    const vault = await wikiApi.createVault({ ...createForm, name: createForm.name.trim() })
    ElMessage.success(createForm.remote_url ? '创建成功，正在克隆远程仓库' : '创建成功')
    createVisible.value = false
    await loadAll()
    if (isBusy(vault)) pollVault(vault.id)
  } finally {
    creating.value = false
  }
}

function openImport() {
  Object.assign(importForm, { mode: 'zip', file: null, dirPath: '', name: '' })
  importVisible.value = true
}

async function submitImport() {
  if (importForm.mode === 'zip' && !importForm.file) {
    ElMessage.warning('请选择 zip 压缩包')
    return
  }
  if (importForm.mode === 'dir' && !importForm.dirPath.trim()) {
    ElMessage.warning('请填写服务器目录路径')
    return
  }
  importing.value = true
  try {
    const vault = importForm.mode === 'zip'
      ? await wikiApi.importVaultZip(importForm.file, importForm.name.trim())
      : await wikiApi.importVaultDir(importForm.dirPath.trim(), importForm.name.trim())
    ElMessage.success('导入已开始')
    importVisible.value = false
    await loadAll()
    if (isBusy(vault)) pollVault(vault.id)
  } finally {
    importing.value = false
  }
}

function handleCommand(cmd, vault) {
  if (cmd === 'settings') {
    Object.assign(settingsForm, {
      id: vault.id,
      name: vault.name,
      description: vault.description,
      remote_url: vault.remote_url || '',
      auto_commit_interval: vault.auto_commit_interval,
    })
    settingsVisible.value = true
  } else if (cmd === 'delete') {
    ElMessageBox.confirm(
      `删除「${vault.name}」？默认软删除，磁盘数据保留 30 天。`,
      '删除确认',
      { type: 'warning', confirmButtonText: '删除', cancelButtonText: '取消' }
    ).then(async () => {
      await wikiApi.deleteVault(vault.id)
      ElMessage.success('已删除')
      await loadAll()
    }).catch(() => {})
  } else if (cmd === 'pull' || cmd === 'push') {
    const fn = cmd === 'pull' ? wikiApi.pullVault : wikiApi.pushVault
    fn(vault.id).then(() => {
      ElMessage.success(cmd === 'pull' ? '拉取完成' : '推送完成')
      loadAll()
    }).catch((e) => {
      const detail = e?.response?.data?.detail
      const code = typeof detail === 'object' ? detail?.code : ''
      if (code === 'wiki_pull_conflict') {
        const files = detail?.files || []
        ElMessageBox.alert(
          files.length ? files.join('\n') : detail?.message || '存在冲突文件',
          '拉取冲突：以下文件本地有改动，请先提交或还原',
          { confirmButtonText: '知道了' }
        )
      } else if (code === 'wiki_push_rejected') {
        ElMessageBox.alert(detail?.message || '远端有新提交，请先拉取合并后再推送', '推送被拒绝', {
          confirmButtonText: '知道了',
        })
      } else {
        ElMessage.error(detail?.message || (cmd === 'pull' ? '拉取失败' : '推送失败'))
      }
    })
  }
}

async function submitSettings() {
  creating.value = true
  try {
    await wikiApi.updateVault(settingsForm.id, {
      name: settingsForm.name.trim(),
      description: settingsForm.description,
      remote_url: settingsForm.remote_url || null,
      auto_commit_interval: settingsForm.auto_commit_interval,
    })
    ElMessage.success('已保存')
    settingsVisible.value = false
    await loadAll()
  } finally {
    creating.value = false
  }
}

onMounted(loadAll)
onBeforeUnmount(() => {
  Object.keys(pollers).forEach(stopPoller)
})
</script>

<style scoped>
.vault-manager {
  padding: 20px 24px;
  height: 100%;
  overflow-y: auto;
}
.vm-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.vm-header-actions {
  display: flex;
  gap: 10px;
}
.vm-title {
  margin: 0;
  font-size: 18px;
  color: var(--ss-text);
}
.vm-loading {
  height: 300px;
}
.vm-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}
.vault-card {
  position: relative;
  background: #fff;
  border-radius: var(--ss-radius);
  box-shadow: var(--ss-shadow);
  padding: 16px;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.2s;
}
.vault-card:hover {
  box-shadow: var(--ss-shadow-lg);
  transform: translateY(-2px);
}
.vault-card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.vault-icon {
  color: var(--ss-primary);
  font-size: 20px;
}
.vault-name {
  font-weight: 600;
  color: var(--ss-text);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.vault-actions {
  flex-shrink: 0;
}
.more-icon {
  color: var(--ss-text-muted);
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
}
.more-icon:hover {
  color: var(--ss-primary);
  background: var(--ss-primary-light);
}
.vault-desc {
  font-size: 13px;
  color: var(--ss-text-secondary);
  height: 36px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  margin-bottom: 10px;
}
.vault-meta {
  display: flex;
  gap: 14px;
  font-size: 12px;
  color: var(--ss-text-muted);
}
.meta-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.vault-dirty {
  position: absolute;
  top: 12px;
  right: 36px;
  background: var(--ss-primary-light);
  color: var(--ss-primary);
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 10px;
}
.vault-card.is-busy {
  cursor: wait;
}
.vault-card.is-error {
  border: 1px solid var(--el-color-danger-light-5, #f89898);
}
.vault-busy {
  position: absolute;
  inset: 0;
  background: rgba(255, 255, 255, 0.88);
  border-radius: var(--ss-radius);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
}
.busy-label {
  font-size: 13px;
  color: var(--ss-text-secondary);
}
.vault-error {
  position: absolute;
  left: 16px;
  right: 16px;
  bottom: 12px;
  font-size: 12px;
  color: var(--el-color-danger);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.form-hint {
  margin-left: 8px;
  font-size: 12px;
  color: var(--ss-text-muted);
}
</style>
