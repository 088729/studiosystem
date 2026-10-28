import request from './request'

const base = (vid) => `/wiki/vaults/${vid}`

// ---- Vault ----
export const fetchVaults = () => request.get('/wiki/vaults')
export const fetchVaultsOverview = () => request.get('/wiki/vaults/overview')
export const createVault = (data) => request.post('/wiki/vaults', data)
export const fetchVault = (vid) => request.get(base(vid))
export const updateVault = (vid, data) => request.patch(base(vid), data)
export const deleteVault = (vid, hard = false) => request.delete(base(vid), { params: { hard } })
export const pullVault = (vid) => request.post(`${base(vid)}/pull`)
export const pushVault = (vid) => request.post(`${base(vid)}/push`)

// ---- 本地导入 ----
export const importVaultZip = (file, name = '') => {
  const form = new FormData()
  form.append('file', file)
  if (name) form.append('name', name)
  return request.post('/wiki/vaults/import-zip', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
export const importVaultDir = (path, name = '') =>
  request.post('/wiki/vaults/import-dir', { path, name: name || null })

// ---- 页面 ----
export const fetchPageTree = (vid) => request.get(`${base(vid)}/pages/tree`)
export const fetchPageContent = (vid, path) =>
  request.get(`${base(vid)}/pages/content`, { params: { path } })
export const createPage = (vid, path, content = '') =>
  request.post(`${base(vid)}/pages`, { path, content })
export const savePage = (vid, path, content, holder) =>
  request.put(`${base(vid)}/pages/content`, { path, content, holder })
export const deletePage = (vid, path, recursive = false) =>
  request.delete(`${base(vid)}/pages`, { params: { path, recursive } })
export const movePage = (vid, src, dst) => request.post(`${base(vid)}/pages/move`, { src, dst })
export const commitVault = (vid, message) =>
  request.post(`${base(vid)}/pages/commit`, { message })
export const lockPage = (vid, path, holder) =>
  request.post(`${base(vid)}/pages/lock`, { path, holder })
export const unlockPage = (vid, path, holder) =>
  request.delete(`${base(vid)}/pages/lock`, { params: { path, holder } })

// ---- 历史 ----
export const fetchHistory = (vid, path, limit = 50) =>
  request.get(`${base(vid)}/history`, { params: { path, limit } })
export const fetchDiff = (vid, path, commit, compare = null) =>
  request.get(`${base(vid)}/history/diff`, { params: { path, commit, compare } })
export const revertPage = (vid, path, commit) =>
  request.post(`${base(vid)}/history/revert`, { path, commit })

// ---- 探索 ----
export const searchPages = (vid, q = '', tag = null) =>
  request.get(`${base(vid)}/explore/search`, { params: { q, tag } })
export const fetchBacklinks = (vid, path) =>
  request.get(`${base(vid)}/explore/backlinks`, { params: { path } })
export const fetchGraph = (vid) => request.get(`${base(vid)}/explore/graph`)
export const rebuildIndex = (vid) => request.post(`${base(vid)}/explore/rebuild-index`)

// ---- 附件 ----
export const uploadAttachment = (vid, file) => {
  const form = new FormData()
  form.append('file', file)
  return request.post(`${base(vid)}/attachments`, form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}
/** 附件原始内容 URL（img/audio/video src 用），带鉴权同域，无需签名 */
export const attachmentUrl = (vid, path) =>
  `/api/v1${base(vid)}/attachments/content?path=${encodeURIComponent(path)}`
