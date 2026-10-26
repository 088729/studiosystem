import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as wikiApi from '@/api/wiki'

export const useWikiStore = defineStore('wiki', () => {
  const vaults = ref([])
  const currentVault = ref(null)   // { detail, changes, doc_count }
  const tree = ref([])
  const backlinks = ref([])
  const loading = ref(false)

  async function fetchVaults() {
    const res = await wikiApi.fetchVaults()
    vaults.value = res.items || []
    return vaults.value
  }

  async function loadVault(vid) {
    loading.value = true
    try {
      currentVault.value = await wikiApi.fetchVault(vid)
      return currentVault.value
    } finally {
      loading.value = false
    }
  }

  async function refreshTree(vid) {
    tree.value = await wikiApi.fetchPageTree(vid)
    return tree.value
  }

  async function refreshStatus(vid) {
    const detail = await wikiApi.fetchVault(vid)
    currentVault.value = detail
    return detail
  }

  async function loadBacklinks(vid, path) {
    backlinks.value = await wikiApi.fetchBacklinks(vid, path)
    return backlinks.value
  }

  function reset() {
    vaults.value = []
    currentVault.value = null
    tree.value = []
    backlinks.value = []
  }

  return {
    vaults,
    currentVault,
    tree,
    backlinks,
    loading,
    fetchVaults,
    loadVault,
    refreshTree,
    refreshStatus,
    loadBacklinks,
    reset,
  }
})
