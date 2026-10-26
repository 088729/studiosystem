<template>
  <div class="graph-view">
    <header class="gv-topbar">
      <div class="gv-left">
        <el-button link @click="goWorkspace">
          <el-icon><Back /></el-icon>&nbsp;返回工作区
        </el-button>
        <el-divider direction="vertical" />
        <span class="gv-title">{{ wikiStore.currentVault?.name || '…' }} · 关系图谱</span>
      </div>
      <div class="gv-right">
        <el-radio-group v-model="scope" size="small" @change="render">
          <el-radio-button value="all">全库</el-radio-button>
          <el-radio-button value="local" :disabled="!centerPath">当前文档邻域</el-radio-button>
        </el-radio-group>
        <el-input
          v-model="locateQuery"
          size="small"
          placeholder="定位节点…"
          clearable
          class="gv-locate"
          @input="locate"
        />
      </div>
    </header>
    <div ref="chartEl" class="gv-chart" v-loading="loading" />
    <div class="gv-hint">拖拽移动节点 · 滚轮缩放 · 点击节点打开文档{{ nodeCountHint }}{{ isolatedHint }}</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import * as echarts from 'echarts/core'
import { GraphChart } from 'echarts/charts'
import { TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

// 按需注册：只带 graph 系列 + tooltip，避免整包 echarts 进 chunk
echarts.use([GraphChart, TooltipComponent, CanvasRenderer])
import * as wikiApi from '@/api/wiki'
import { useWikiStore } from '@/stores/wiki'

const route = useRoute()
const router = useRouter()
const wikiStore = useWikiStore()

const vaultId = route.params.vaultId
const centerPath = ref(route.query.path ? String(route.query.path) : '')

const chartEl = ref(null)
const loading = ref(false)
const scope = ref(centerPath.value ? 'local' : 'all')
const locateQuery = ref('')
let chart = null
let graphData = { nodes: [], edges: [] }

const nodeCountHint = computed(() => {
  const n = graphData.nodes.length
  return n >= 500 ? ` · 节点较多，仅显示前 500 个高度数节点` : ''
})

// 邻域视图下中心文档无任何链接时的提示
const isolatedHint = computed(() => {
  if (scope.value !== 'local' || !centerPath.value) return ''
  const linked = graphData.edges.some(
    (e) => e.src === centerPath.value || e.dst === centerPath.value
  )
  return linked ? '' : ' · 该文档暂无入链 / 出链，仅显示自身'
})

const TAG_COLORS = [
  '#4f6ef7', '#36a3f7', '#2eb85a', '#f7a236', '#f7636e',
  '#9b59f7', '#18c2c8', '#e85f9e', '#8a9a5b', '#d98324',
]

function colorOf(node) {
  const tag = (node.tags || [])[0]
  if (!tag) return '#9aa4b8'
  let h = 0
  for (const ch of tag) h = (h * 31 + ch.charCodeAt(0)) >>> 0
  return TAG_COLORS[h % TAG_COLORS.length]
}

function neighborhoodSubset() {
  const keep = new Set([centerPath.value])
  for (const e of graphData.edges) {
    if (e.src === centerPath.value) keep.add(e.dst)
    if (e.dst === centerPath.value) keep.add(e.src)
  }
  const nodes = graphData.nodes.filter((n) => keep.has(n.path))
  if (!nodes.some((n) => n.path === centerPath.value)) {
    // 中心文档在图中孤立（无入链/出链，图谱接口不会返回它）：补一个节点，
    // 否则邻域视图没有任何数据，echarts 画空白页
    const name = centerPath.value.split('/').pop().replace(/\.md$/, '')
    nodes.push({ path: centerPath.value, title: name, tags: [] })
  }
  const edges = graphData.edges.filter((e) => keep.has(e.src) && keep.has(e.dst))
  return { nodes, edges }
}

function render() {
  if (!chart) return
  const data = scope.value === 'local' && centerPath.value ? neighborhoodSubset() : graphData
  const nodeByPath = new Map(data.nodes.map((n) => [n.path, n]))
  chart.setOption({
    tooltip: {
      formatter: (p) => (p.dataType === 'node' ? `${p.data.title}<br/><small>${p.data.path}</small>` : ''),
    },
    series: [{
      type: 'graph',
      layout: 'force',
      roam: true,
      draggable: true,
      focusNodeAdjacency: true,
      force: {
        repulsion: 220,
        edgeLength: [60, 140],
        gravity: 0.08,
      },
      label: { show: true, position: 'right', fontSize: 12, color: '#4b5563' },
      edgeSymbol: ['none', 'arrow'],
      edgeSymbolSize: 6,
      lineStyle: { color: '#c3cad9', width: 1.4, curveness: 0.08 },
      emphasis: { lineStyle: { width: 3 } },
      data: data.nodes.map((n) => ({
        ...n,
        name: n.path,
        symbolSize: n.path === centerPath.value ? 34 : 18,
        itemStyle: { color: colorOf(n) },
      })),
      links: data.edges
        .filter((e) => nodeByPath.has(e.src) && nodeByPath.has(e.dst))
        .map((e) => ({
          source: e.src,
          target: e.dst,
          lineStyle: e.type === 'embed' ? { type: 'dashed' } : undefined,
        })),
    }],
  }, true)
}

function locate() {
  const q = locateQuery.value.trim().toLowerCase()
  if (!q || !chart) return
  const hit = graphData.nodes.find(
    (n) => n.title.toLowerCase().includes(q) || n.path.toLowerCase().includes(q)
  )
  if (hit) {
    dispatch({ type: 'highlight', seriesIndex: 0, name: hit.path })
    dispatch({ type: 'showTip', seriesIndex: 0, name: hit.path })
  }
}

function dispatch(payload) {
  try {
    chart.dispatchAction(payload)
  } catch { /* ignore */ }
}

function goWorkspace() {
  router.push(`/wiki/s/${vaultId}`)
}

function onResize() {
  chart?.resize()
}

onMounted(async () => {
  loading.value = true
  try {
    if (!wikiStore.currentVault || wikiStore.currentVault.id !== vaultId) {
      await wikiStore.loadVault(vaultId)
    }
    graphData = await wikiApi.fetchGraph(vaultId)
    await nextTick()
    chart = echarts.init(chartEl.value)
    render()
    chart.on('click', (params) => {
      if (params.dataType === 'node' && params.data?.path) {
        router.push({
          path: `/wiki/s/${vaultId}`,
          query: { path: params.data.path },
        })
      }
    })
    window.addEventListener('resize', onResize)
  } finally {
    loading.value = false
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', onResize)
  chart?.dispose()
  chart = null
})
</script>

<style scoped>
.graph-view {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #fff;
}
.gv-topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 48px;
  padding: 0 12px;
  border-bottom: 1px solid var(--ss-border);
  flex-shrink: 0;
}
.gv-left {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 0;
}
.gv-title {
  font-weight: 600;
  color: var(--ss-text);
}
.gv-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.gv-locate {
  width: 180px;
}
.gv-chart {
  flex: 1;
  min-height: 0;
}
.gv-hint {
  padding: 5px 14px;
  font-size: 12px;
  color: var(--ss-text-muted);
  border-top: 1px solid var(--ss-border);
  flex-shrink: 0;
}
</style>
