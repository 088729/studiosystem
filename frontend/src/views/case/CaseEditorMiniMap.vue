<template>
  <div class="mini-map-box" @click.stop @mousedown.stop>
    <div class="mm-head">
      <span class="mm-title">小地图</span>
      <el-icon class="mm-close" title="关闭" @click="emit('close')"><Close /></el-icon>
    </div>
    <div
      ref="mmBody"
      class="mm-body"
      @mousedown="onMousedown"
      @mousemove="onMousemove"
      @mouseup="onMouseup"
      @mouseleave="onMouseup"
    >
      <!-- 缩略图（插件生成） -->
      <div ref="svgContainer" class="mm-svg" v-html="svgHTML"></div>
      <!-- 当前视口框：拖动 = 平移画布 -->
      <div
        v-if="viewBoxStyle"
        class="mm-viewbox"
        :style="viewBoxStyle"
        @mousedown.stop="onViewBoxMousedown"
        @mousemove="onViewBoxMousemove"
        @mouseup="onMouseup"
      ></div>
    </div>
  </div>
</template>

<script setup>
// 小地图浮动组件：包装 simple-mind-map MiniMap 插件。
// - 缩略图拖动空白区 = 整体平移画布（插件 onMousedown/onMousemove，灵敏度 5）
// - 拖动视口框 = 移动可视区域（插件 onViewBoxMousedown/onViewBoxMousemove）
// - 画布视图 / 数据变化时按节流重新计算
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { Close } from '@element-plus/icons-vue'

const BOX_W = 232
const BOX_H = 156

const props = defineProps({
  mindMap: Object,
})
const emit = defineEmits(['close'])

const mmBody = ref(null)
const svgContainer = ref(null)
const svgHTML = ref('')
const viewBoxStyle = ref(null)

let throttleTimer = null
let pendingRecalc = false

function calc() {
  const mm = props.mindMap
  const body = mmBody.value
  if (!mm || !body) return
  try {
    const { svgHTML: html, viewBoxStyle: style } = mm.miniMap.calculationMiniMap(BOX_W, BOX_H)
    svgHTML.value = html
    viewBoxStyle.value = style
  } catch (e) {
    // 空图 / 初始化中，忽略
  }
}

function recalcThrottled() {
  if (throttleTimer) {
    pendingRecalc = true
    return
  }
  calc()
  throttleTimer = setTimeout(() => {
    throttleTimer = null
    if (pendingRecalc) {
      pendingRecalc = false
      recalcThrottled()
    }
  }, 300)
}

function bind(mm, old) {
  if (old) {
    old.off('view_data_change', recalcThrottled)
    old.off('data_change', recalcThrottled)
  }
  if (!mm) return
  mm.on('view_data_change', recalcThrottled)
  mm.on('data_change', recalcThrottled)
  // 视口框被拖动时，插件只发位置事件，DOM 位置由插件外接管（本组件的 viewBoxStyle 绑定）
  mm.on('mini_map_view_box_position_change', (style) => {
    viewBoxStyle.value = style
  })
  onMountedHook()
}

function onMountedHook() {
  // 挂载后下一帧计算（等待容器有实际尺寸）
  setTimeout(calc, 60)
}

onMounted(() => bind(props.mindMap))
watch(
  () => [props.mindMap],
  ([mm], [old]) => bind(mm, old)
)
onBeforeUnmount(() => {
  props.mindMap?.off('view_data_change', recalcThrottled)
  props.mindMap?.off('data_change', recalcThrottled)
  props.mindMap?.off('mini_map_view_box_position_change')
})

// ===== 交互转发到插件 =====
function onMousedown(e) {
  props.mindMap?.miniMap.onMousedown(e)
}
function onMousemove(e) {
  props.mindMap?.miniMap.onMousemove(e)
}
function onMouseup() {
  props.mindMap?.miniMap.onMouseup()
}
function onViewBoxMousedown(e) {
  props.mindMap?.miniMap.onViewBoxMousedown(e)
}
function onViewBoxMousemove(e) {
  props.mindMap?.miniMap.onViewBoxMousemove(e)
}
</script>

<style scoped>
.mini-map-box {
  position: absolute;
  right: 16px;
  bottom: 16px;
  z-index: 30;
  width: 248px;
  background: #fff;
  border: 1px solid var(--ss-border, #e6e9f0);
  border-radius: 10px;
  box-shadow: 0 8px 24px rgba(16, 24, 40, 0.16);
  overflow: hidden;
}
.mm-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-bottom: 1px solid var(--ss-border, #e6e9f0);
}
.mm-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--ss-text, #1f2937);
}
.mm-close {
  cursor: pointer;
  color: var(--ss-text-muted, #9ca3af);
}
.mm-close:hover {
  color: var(--ss-text, #1f2937);
}
.mm-body {
  position: relative;
  width: 232px;
  height: 156px;
  overflow: hidden;
  background: #fbfcfe;
  cursor: move;
}
.mm-svg {
  position: absolute;
  left: 0;
  top: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.mm-svg :deep(svg) {
  width: 100%;
  height: 100%;
}
.mm-viewbox {
  position: absolute;
  border: 1.5px solid var(--ss-primary, #4f6ef7);
  background: rgba(79, 110, 247, 0.08);
  cursor: grab;
  border-radius: 2px;
}
.mm-viewbox:active {
  cursor: grabbing;
}
</style>
