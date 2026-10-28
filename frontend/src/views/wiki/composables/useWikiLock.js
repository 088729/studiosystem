import { ref, reactive, onBeforeUnmount } from 'vue'
import * as wikiApi from '@/api/wiki'
import { useAuthStore } from '@/stores/auth'

const HEARTBEAT_MS = 30 * 1000
const POLL_MS = 15 * 1000

/** 窗口级锁令牌：sessionStorage 按标签页隔离，重载保持、新窗口不同 */
function windowId() {
  let id = sessionStorage.getItem('wiki_win_id')
  if (!id) {
    id = crypto.randomUUID()
    sessionStorage.setItem('wiki_win_id', id)
  }
  return id
}

/**
 * 编辑锁生命周期：
 * - acquire(path)：加锁；被他人持锁 → 进入只读并轮询等待释放
 * - release(path)：释放
 * - 心跳续期（持锁期间每 30s 一次）
 */
export function useWikiLock(vaultId, { onLockedByOther, onLockFree } = {}) {
  const lockedByOther = ref('')
  const authStore = useAuthStore()
  let heartbeatTimer = null
  let pollTimer = null
  let currentPath = ''
  // 本窗口成功持有的锁：只释放自己持有的，绝不动其他窗口的锁
  const heldPaths = new Set()

  const holder = () =>
    `${authStore.userInfo?.username || ''}@${windowId()}`

  async function acquire(path) {
    const prev = currentPath
    currentPath = path
    stopTimers()
    lockedByOther.value = ''
    // 换文档时静默释放旧锁，避免旧锁挂到 TTL 过期（锁 is held per current page）
    if (prev && prev !== path && heldPaths.has(prev)) {
      heldPaths.delete(prev)
      try {
        await wikiApi.unlockPage(vaultId.value, prev, holder())
      } catch {
        /* 旧锁释放失败有过期兜底 */
      }
    }
    try {
      await wikiApi.lockPage(vaultId.value, path, holder())
      heldPaths.add(path)
      startHeartbeat()
      return true
    } catch (e) {
      if (e.response?.status === 409) {
        lockedByOther.value = e.response?.data?.detail?.lock_holder || '他人'
        startPolling()
        onLockedByOther?.(lockedByOther.value)
        return false
      }
      throw e
    }
  }

  async function release(path) {
    const target = path || currentPath
    if (target && target === currentPath) {
      stopTimers()
      currentPath = ''
    }
    lockedByOther.value = ''
    // 没持有过的锁（如只读页）不发释放请求，防止误抢其他窗口的锁
    if (!target || !heldPaths.has(target)) return
    heldPaths.delete(target)
    try {
      await wikiApi.unlockPage(vaultId.value, target, holder())
    } catch {
      /* 页面卸载时失败可忽略，锁有过期兜底 */
    }
  }

  function startHeartbeat() {
    heartbeatTimer = setInterval(async () => {
      if (!currentPath) return
      try {
        await wikiApi.lockPage(vaultId.value, currentPath, holder())
      } catch (e) {
        if (e.response?.status === 409) {
          lockedByOther.value = e.response?.data?.detail?.lock_holder || '他人'
          stopTimers()
          startPolling()
          onLockedByOther?.(lockedByOther.value)
        }
      }
    }, HEARTBEAT_MS)
  }

  function startPolling() {
    pollTimer = setInterval(async () => {
      if (!currentPath) return
      try {
        const res = await wikiApi.fetchPageContent(vaultId.value, currentPath)
        if (!res.locked_by) {
          lockedByOther.value = ''
          stopTimers()
          onLockFree?.()
        } else {
          lockedByOther.value = res.locked_by
        }
      } catch {
        /* 网络抖动忽略 */
      }
    }, POLL_MS)
  }

  function stopTimers() {
    clearInterval(heartbeatTimer)
    clearInterval(pollTimer)
    heartbeatTimer = null
    pollTimer = null
  }

  onBeforeUnmount(() => release())

  // reactive 包裹：模板中 lockState.lockedByOther 才能自动解包
  return reactive({ lockedByOther, acquire, release, currentHolder: holder })
}
