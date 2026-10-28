import request from './request'

export const fetchHabits = (params) => request.get('/task/habits', { params })
export const createHabit = (data) => request.post('/task/habits', data)
export const updateHabit = (id, data) => request.patch(`/task/habits/${id}`, data)
export const deleteHabit = (id) => request.delete(`/task/habits/${id}`)
export const checkinHabit = (id, data, params) => request.post(`/task/habits/${id}/checkin`, data || {}, { params })
export const uncheckinHabit = (id, params) => request.delete(`/task/habits/${id}/checkin`, { params })
export const skipHabit = (id, data, params) => request.post(`/task/habits/${id}/skip`, data || {}, { params })
export const fetchHabitLogs = (id, params) => request.get(`/task/habits/${id}/logs`, { params })
export const fetchHabitWeek = (params) => request.get('/task/habits/week', { params })
export const fetchHabitStats = (id, params) => request.get(`/task/habits/${id}/stats`, { params })
