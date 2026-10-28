import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  { path: '/login', component: () => import('@/views/auth/LoginView.vue'), meta: { public: true } },
  { path: '/register', component: () => import('@/views/auth/RegisterView.vue'), meta: { public: true } },
  { path: '/profile', component: () => import('@/views/auth/UserProfile.vue'), meta: { requiredPerm: '' } },
  { path: '/platform/admin', component: () => import('@/views/platform/PlatformAdmin.vue'), meta: { requiredPerm: 'sys:manage' } },
  { path: '/case', component: () => import('@/views/case/CaseManager.vue'), meta: { requiredPerm: 'xmind:view' } },
  { path: '/wiki', component: () => import('@/views/wiki/VaultManager.vue'), meta: { requiredPerm: 'wiki:view' } },
  { path: '/wiki/s/:vaultId', component: () => import('@/views/wiki/WikiWorkspace.vue'), meta: { requiredPerm: 'wiki:view', hideSidebar: true } },
  { path: '/wiki/s/:vaultId/graph', component: () => import('@/views/wiki/components/GraphView.vue'), meta: { requiredPerm: 'wiki:view', hideSidebar: true } },
  { path: '/task', component: () => import('@/views/task/TaskManager.vue'), meta: { requiredPerm: 'task:view' } },
  // 习惯打卡已并入任务管理（侧边栏「习惯打卡」项），旧链接重定向
  { path: '/habits', redirect: '/task' },
  { path: '/case/editor/:mapId', component: () => import('@/views/case/CaseEditor.vue'), meta: { requiredPerm: 'xmind:view', hideSidebar: true } },
  { path: '/403', component: () => import('@/views/error/ForbiddenView.vue'), meta: { public: true } },
  { path: '/:pathMatch(.*)*', component: () => import('@/views/error/NotFoundView.vue'), meta: { public: true } },
  { path: '/', redirect: '/case' },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()

  // 有 token 但没有用户信息时，先拉取用户信息
  if (authStore.isLoggedIn && !authStore.userInfo) {
    try {
      await authStore.fetchMe()
    } catch (e) {
      authStore.logout(router)
      next({ path: '/login', query: { redirect: to.fullPath } })
      return
    }
  }

  if (!to.meta.public && !authStore.isLoggedIn) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  }
  if (to.meta.requiredPerm && !authStore.hasPerm(to.meta.requiredPerm)) {
    next('/403')
    return
  }
  if (to.path === '/login' && authStore.isLoggedIn) {
    next('/case')
    return
  }
  next()
})

export default router
