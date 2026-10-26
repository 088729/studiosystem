import request from './request'

export const fetchFolderTree = () => request.get('/case/folders/tree')
export const createFolder = (data) => request.post('/case/folders', data)
export const renameFolder = (id, data) => request.patch(`/case/folders/${id}`, data)
export const moveFolder = (id, data) => request.patch(`/case/folders/${id}/parent`, data)
export const deleteFolder = (id) => request.delete(`/case/folders/${id}`)

export const fetchMaps = (params) => request.get('/case/maps', { params })
export const fetchMap = (id) => request.get(`/case/maps/${id}`)
export const createMap = (data) => request.post('/case/maps', data)
export const importMaps = (data) => request.post('/case/maps/import', data)
export const saveDraft = (id, data) => request.patch(`/case/maps/${id}`, data)
export const renameMap = (id, data) => request.patch(`/case/maps/${id}`, data)
export const deleteMap = (id) => request.delete(`/case/maps/${id}`)
export const moveMap = (id, data) => request.patch(`/case/maps/${id}/folder`, data)
export const copyMap = (id, data) => request.post(`/case/maps/${id}/copy`, data)
export const lockMap = (id) => request.post(`/case/maps/${id}/lock`)
export const unlockMap = (id) => request.delete(`/case/maps/${id}/lock`)

export const fetchVersions = (id, params) => request.get(`/case/maps/${id}/versions`, { params })
export const fetchVersion = (id, versionNo) => request.get(`/case/maps/${id}/versions/${versionNo}`)
export const createSnapshot = (id, data) => request.post(`/case/maps/${id}/snapshot`, data)
export const rollbackVersion = (id, data) => request.post(`/case/maps/${id}/rollback`, data)

export const checkHash = (data) => request.post('/case/assets/check_hash', data)
export const uploadAsset = (data) => request.post('/case/assets/upload', data)
export const deleteAsset = (id) => request.delete(`/case/assets/${id}`)
