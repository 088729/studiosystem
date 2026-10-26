import request from './request'

export const fetchLists = () => request.get('/task/lists')
export const createList = (data) => request.post('/task/lists', data)
export const updateList = (id, data) => request.patch(`/task/lists/${id}`, data)
export const deleteList = (id) => request.delete(`/task/lists/${id}`)

// ---------- 看板分组（清单内自定义分组列，对齐主流待办应用看板） ----------
export const addListGroup = (listId, name, index = null) =>
  request.post(`/task/lists/${listId}/groups`, { name, ...(index != null ? { index } : {}) })
export const renameListGroup = (listId, from_name, to_name) =>
  request.patch(`/task/lists/${listId}/groups`, { from_name, to_name })
export const deleteListGroup = (listId, name) =>
  request.delete(`/task/lists/${listId}/groups/${encodeURIComponent(name)}`)
// 分组「移动到」另一清单/收集箱（对齐主流待办应用分组右键菜单）：from/to 传 null 表示收集箱
export const moveListGroup = (name, from_list_id, to_list_id) =>
  request.post('/task/lists/groups/move', { name, from_list_id, to_list_id })

// ---------- 收集箱自定义分组（存 per-user TaskSettings.inbox_board_groups，对齐主流待办应用） ----------
export const addInboxGroup = (name, index = null) =>
  request.post('/task/settings/inbox-groups', { name, ...(index != null ? { index } : {}) })
export const renameInboxGroup = (from_name, to_name) =>
  request.patch('/task/settings/inbox-groups', { from_name, to_name })
export const deleteInboxGroup = (name) =>
  request.delete(`/task/settings/inbox-groups/${encodeURIComponent(name)}`)

export const fetchTasks = (params) => request.get('/task/tasks', { params })
export const fetchTask = (id) => request.get(`/task/tasks/${id}`)
export const createTask = (data) => request.post('/task/tasks', data)
export const updateTask = (id, data) => request.patch(`/task/tasks/${id}`, data)
export const deleteTask = (id) => request.delete(`/task/tasks/${id}`)
export const restoreTask = (id) => request.post(`/task/tasks/${id}/restore`)
export const purgeTask = (id) => request.delete(`/task/tasks/${id}/purge`)
export const completeTask = (id, done) => request.post(`/task/tasks/${id}/complete`, { done })
export const skipTask = (id) => request.post(`/task/tasks/${id}/skip`)
export const moveTask = (id, data) => request.patch(`/task/tasks/${id}/move`, data)
export const sortTask = (id, data) => request.patch(`/task/tasks/${id}/sort`, data)
export const batchTasks = (data) => request.post('/task/tasks/batch', data)

export const fetchPendingReminders = () => request.get('/task/views/pending-reminders')
export const ackReminders = (id, data = {}) => request.post(`/task/tasks/${id}/reminders/ack`, data)
export const fetchCalendar = (params) => request.get('/task/views/calendar', { params })
export const fetchSummary = (params) => request.get('/task/views/summary', { params })

// ---------- 任务默认值设置 ----------
export const fetchSettings = () => request.get('/task/settings')
export const saveSettings = (data) => request.put('/task/settings', data)

// ---------- 番茄钟 ----------
export const startFocus = (data) => request.post('/task/focus', data)
export const finishFocus = (id) => request.post(`/task/focus/${id}/finish`)
export const abandonFocus = (id) => request.post(`/task/focus/${id}/abandon`)
export const pauseFocus = (id) => request.post(`/task/focus/${id}/pause`)
export const resumeFocus = (id) => request.post(`/task/focus/${id}/resume`)
export const updateFocus = (id, data) => request.patch(`/task/focus/${id}`, data)
export const addFocusRecord = (data) => request.post('/task/focus/records', data)
export const fetchFocusSessions = (params) => request.get('/task/focus', { params })
export const fetchFocusStats = (params) => request.get('/task/focus/stats', { params })
export const fetchFocusPresets = (params) => request.get('/task/focus-presets', { params })
export const createFocusPreset = (data) => request.post('/task/focus-presets', data)
export const updateFocusPreset = (id, data) => request.patch(`/task/focus-presets/${id}`, data)
export const deleteFocusPreset = (id) => request.delete(`/task/focus-presets/${id}`)
export const fetchFocusPresetStats = (id, params) => request.get(`/task/focus-presets/${id}/stats`, { params })
export const fetchFocusStatsDetail = (params) => request.get('/task/focus/stats/detail', { params })
export const deleteFocusRecords = (data) => request.delete('/task/focus/records', { data })

// ---------- 共享 ----------
export const fetchShareUsers = () => request.get('/task/share/users')
export const fetchListMembers = (listId) => request.get(`/task/share/lists/${listId}/members`)
export const addListMember = (listId, username, role = 'viewer') => request.post(`/task/share/lists/${listId}/members`, { username, role })
export const removeListMember = (listId, username) => request.delete(`/task/share/lists/${listId}/members/${username}`)
export const setMemberRole = (listId, username, role) => request.patch(`/task/share/lists/${listId}/members/${username}`, { role })
export const leaveList = (listId) => request.delete(`/task/share/lists/${listId}/members/me`)
export const transferOwner = (listId, to) => request.post(`/task/share/lists/${listId}/transfer`, { to })

// ---------- 摘要（对齐主流待办应用「摘要」智能清单） ----------
export const previewSummary = (data) => request.post('/task/summary/preview', data)

// ---------- 筛选器 / 标签 ----------
export const fetchFilters = (params) => request.get('/task/filters', { params })
export const createFilter = (data) => request.post('/task/filters', data)
export const updateFilter = (id, data) => request.patch(`/task/filters/${id}`, data)
export const deleteFilter = (id) => request.delete(`/task/filters/${id}`)
export const fetchTagCounts = () => request.get('/task/views/tags')

// ---------- 标签实体（颜色/层级/侧栏管理） ----------
export const fetchTags = () => request.get('/task/tags')
export const createTag = (data) => request.post('/task/tags', data)
export const updateTag = (id, data) => request.patch(`/task/tags/${id}`, data)
export const deleteTag = (id) => request.delete(`/task/tags/${id}`)

// ---------- 附件（文件本体存后端配置的存储后端：本地磁盘默认 /uploads，或自建文件服务） ----------
export const addAttachment = (id, data) => request.post(`/task/tasks/${id}/attachments`, data)
export const removeAttachment = (id, resourceId) => request.delete(`/task/tasks/${id}/attachments/${resourceId}`)
export const uploadAttachment = (id, file) => {
  const fd = new FormData()
  fd.append('file', file)
  return request.post(`/task/tasks/${id}/attachments/upload`, fd)
}
// 附件地址兜底：优先用记录里的 url 字段；本地存储为 /uploads/{相对路径}（同源，开发经 Vite 代理）
export const attachmentUrl = (resourceId) => `/uploads/${String(resourceId).replace(/^\//, '')}`

// ---------- 评论 ----------
export const fetchComments = (taskId) => request.get(`/task/tasks/${taskId}/comments`)
export const addComment = (taskId, content) => request.post(`/task/tasks/${taskId}/comments`, { content })
export const updateComment = (commentId, content) => request.patch(`/task/comments/${commentId}`, { content })
export const deleteComment = (commentId) => request.delete(`/task/comments/${commentId}`)
// 评论图片：文件本体存 resourceplatform（task/comments/），评论 content 内嵌 markdown 图片
export const uploadCommentImage = (file) => {
  const fd = new FormData()
  fd.append('file', file)
  return request.post('/task/comments/upload-image', fd)
}
