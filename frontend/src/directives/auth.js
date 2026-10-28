import { watch } from 'vue'
import { useAuthStore } from '@/stores/auth'

export default {
  mounted(el, binding) {
    const authStore = useAuthStore()
    const perm = binding.value

    const updateVisibility = () => {
      el.style.display = authStore.hasPerm(perm) ? '' : 'none'
    }

    updateVisibility()

    el.__authUnwatch = watch(
      () => authStore.perms,
      updateVisibility,
      { deep: true }
    )
  },
  unmounted(el) {
    el.__authUnwatch?.()
  },
}
