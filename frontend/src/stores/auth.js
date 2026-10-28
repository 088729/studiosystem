import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('sun_access_token') || sessionStorage.getItem('sun_access_token') || null)
  const userInfo = ref(null)

  const isLoggedIn = computed(() => !!token.value)
  const perms = computed(() => userInfo.value?.perms || [])

  function setToken(newToken, rememberMe) {
    token.value = newToken
    if (rememberMe) {
      localStorage.setItem('sun_access_token', newToken)
    } else {
      sessionStorage.setItem('sun_access_token', newToken)
    }
  }

  function hasPerm(perm) {
    if (!perm) return true
    const list = perms.value
    return list.includes('*') || list.includes(perm)
  }

  async function login(username, password, rememberMe = false) {
    const res = await authApi.login({ username, password, remember_me: rememberMe })
    setToken(res.access_token, rememberMe)
    await fetchMe()
    return res
  }

  async function fetchMe() {
    userInfo.value = await authApi.getMe()
  }

  function logout(router) {
    token.value = null
    userInfo.value = null
    localStorage.removeItem('sun_access_token')
    sessionStorage.removeItem('sun_access_token')
    if (router) {
      router.push('/login')
    } else {
      window.location.href = '/login'
    }
  }

  return {
    token,
    userInfo,
    isLoggedIn,
    perms,
    hasPerm,
    setToken,
    login,
    fetchMe,
    logout,
  }
})
