import request from './request'

export const login = (data) => request.post('/common/auth/login', data)
export const register = (data) => request.post('/common/auth/register', data)
export const getMe = () => request.get('/common/auth/me')
export const getUser = (username) => request.get(`/common/auth/user/${username}`)
export const verifyToken = (token) => request.post('/common/auth/verify', { token })

export const getUsers = (params) => request.get('/common/auth/users', { params })
export const createUser = (data) => request.post('/common/auth/users', data)
export const updateUserPermissions = (username, data) => request.patch(`/common/auth/users/${username}/permissions`, data)
export const batchUpdatePermissions = (data) => request.post('/common/auth/users/batch-permissions', data)
export const setUserActive = (username, data) => request.patch(`/common/auth/users/${username}/active`, data)
export const updateJobScope = (username, data) => request.patch(`/common/auth/users/${username}/job-scope`, data)
export const deleteUser = (username) => request.delete(`/common/auth/users/${username}`)

export const getRoles = () => request.get('/common/auth/roles')
export const createRole = (data) => request.post('/common/auth/roles', data)
export const updateRole = (name, data) => request.patch(`/common/auth/roles/${name}`, data)
export const deleteRole = (name) => request.delete(`/common/auth/roles/${name}`)

export const getPermissions = () => request.get('/common/auth/permissions')
export const getPlatformPermissions = () => request.get('/common/platform/permissions')
export const createPermission = (data) => request.post('/common/platform/permissions', data)
export const deletePermission = (key) => request.delete(`/common/platform/permissions/${key}`)
