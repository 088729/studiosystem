import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
})

request.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('sun_access_token') || sessionStorage.getItem('sun_access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const detail = error.response?.data?.detail
    const message = detail?.message || error.message || '请求失败'
    if (status === 401) {
      localStorage.removeItem('sun_access_token')
      sessionStorage.removeItem('sun_access_token')
      const isLoginRequest = error.config?.url?.includes('/auth/login')
      if (isLoginRequest || window.location.pathname === '/login') {
        // 登录请求本身的 401（如密码错误）或已在登录页时，不硬跳转刷新，直接提示
        ElMessage.error(message)
      } else {
        window.location.href = '/login'
      }
    } else {
      ElMessage.error(message)
    }
    return Promise.reject(error)
  }
)

export default request
