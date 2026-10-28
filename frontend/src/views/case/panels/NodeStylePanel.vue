<template>
  <div class="node-style-panel">
    <div v-if="!hasActiveNode" class="empty-tip">
      <el-icon :size="28" class="empty-icon"><Pointer /></el-icon>
      <p>请选中一个节点</p>
    </div>
    <template v-else>
      <div class="panel-title">文字</div>
      <div class="style-row">
        <span>字体</span>
        <el-select v-model="style.fontFamily" size="small" @change="update('fontFamily')">
          <el-option label="微软雅黑" value="微软雅黑, Microsoft YaHei" />
          <el-option label="宋体" value="宋体, SimSun" />
          <el-option label="黑体" value="黑体, SimHei" />
          <el-option label="Arial" value="Arial" />
        </el-select>
      </div>
      <div class="style-row">
        <span>字号</span>
        <el-input-number v-model="style.fontSize" :min="12" :max="30" size="small" @change="update('fontSize')" />
      </div>
      <div class="style-row">
        <span>颜色</span>
        <el-color-picker v-model="style.color" size="small" @change="update('color')" />
      </div>
      <div class="style-row">
        <span>对齐</span>
        <el-select v-model="style.textAlign" size="small" @change="update('textAlign')">
          <el-option label="左对齐" value="left" />
          <el-option label="居中" value="center" />
          <el-option label="右对齐" value="right" />
          <el-option label="两端对齐" value="justify" />
        </el-select>
      </div>
      <div class="style-row">
        <el-checkbox v-model="isBold" @change="updateFontWeight">加粗</el-checkbox>
        <el-checkbox v-model="isItalic" @change="updateFontStyle">斜体</el-checkbox>
        <el-checkbox v-model="isUnderline" @change="updateTextDecoration">下划线</el-checkbox>
      </div>

      <div class="panel-title">边框</div>
      <div class="style-row">
        <span>颜色</span>
        <el-color-picker v-model="style.borderColor" size="small" @change="update('borderColor')" />
      </div>
      <div class="style-row">
        <span>宽度</span>
        <el-input-number v-model="style.borderWidth" :min="0" :max="10" size="small" @change="update('borderWidth')" />
      </div>
      <div class="style-row">
        <span>样式</span>
        <el-select v-model="style.borderDasharray" size="small" @change="update('borderDasharray')">
          <el-option label="实线" value="none" />
          <el-option label="虚线" value="5,5" />
          <el-option label="点线" value="2,2" />
        </el-select>
      </div>
      <div class="style-row">
        <span>圆角</span>
        <el-input-number v-model="style.borderRadius" :min="0" :max="20" size="small" @change="update('borderRadius')" />
      </div>

      <div class="panel-title">背景</div>
      <div class="style-row">
        <span>颜色</span>
        <el-color-picker v-model="style.fillColor" size="small" @change="update('fillColor')" />
      </div>
      <div class="style-row">
        <el-checkbox v-model="style.gradientStyle" @change="update('gradientStyle')">渐变</el-checkbox>
      </div>
      <div v-if="style.gradientStyle" class="style-row">
        <span>起始色</span>
        <el-color-picker v-model="style.startColor" size="small" @change="update('startColor')" />
      </div>
      <div v-if="style.gradientStyle" class="style-row">
        <span>结束色</span>
        <el-color-picker v-model="style.endColor" size="small" @change="update('endColor')" />
      </div>

      <div class="panel-title">形状</div>
      <div class="style-row">
        <span>形状</span>
        <el-select v-model="style.shape" size="small" @change="update('shape')">
          <el-option label="矩形" value="rectangle" />
          <el-option label="圆角矩形" value="roundedRectangle" />
          <el-option label="菱形" value="diamond" />
          <el-option label="平行四边形" value="parallelogram" />
          <el-option label="椭圆形" value="ellipse" />
          <el-option label="圆形" value="circle" />
        </el-select>
      </div>

      <div class="panel-title">图片与标签</div>
      <div class="style-row">
        <span>图片位置</span>
        <el-select v-model="style.imgPlacement" size="small" @change="update('imgPlacement')">
          <el-option label="上" value="top" />
          <el-option label="下" value="bottom" />
          <el-option label="左" value="left" />
          <el-option label="右" value="right" />
        </el-select>
      </div>
      <div class="style-row">
        <span>标签位置</span>
        <el-select v-model="style.tagPlacement" size="small" @change="update('tagPlacement')">
          <el-option label="右侧" value="right" />
          <el-option label="下方" value="bottom" />
        </el-select>
      </div>

      <div class="panel-title">内边距</div>
      <div class="style-row">
        <span>水平</span>
        <el-input-number v-model="style.paddingX" :min="0" :max="50" size="small" @change="update('paddingX')" />
      </div>
      <div class="style-row">
        <span>垂直</span>
        <el-input-number v-model="style.paddingY" :min="0" :max="50" size="small" @change="update('paddingY')" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, watch, computed } from 'vue'

const props = defineProps({
  mindMap: Object,
})

const defaultStyle = {
  fontFamily: '微软雅黑, Microsoft YaHei',
  fontSize: 14,
  color: '#333333',
  textAlign: 'left',
  fontWeight: 'normal',
  fontStyle: 'normal',
  textDecoration: 'none',
  borderColor: '#549688',
  borderWidth: 1,
  borderDasharray: 'none',
  borderRadius: 5,
  fillColor: '#ffffff',
  gradientStyle: false,
  startColor: '#549688',
  endColor: '#fff',
  shape: 'rectangle',
  imgPlacement: 'top',
  tagPlacement: 'right',
  paddingX: 15,
  paddingY: 5,
}

const style = ref({ ...defaultStyle })
const activeNodes = ref([])
const hasActiveNode = computed(() => activeNodes.value.length > 0)

const isBold = computed({
  get: () => style.value.fontWeight === 'bold',
  set: (val) => { style.value.fontWeight = val ? 'bold' : 'normal' },
})
const isItalic = computed({
  get: () => style.value.fontStyle === 'italic',
  set: (val) => { style.value.fontStyle = val ? 'italic' : 'normal' },
})
const isUnderline = computed({
  get: () => style.value.textDecoration === 'underline',
  set: (val) => { style.value.textDecoration = val ? 'underline' : 'none' },
})

function initNodeStyle() {
  if (activeNodes.value.length === 0) return
  const node = activeNodes.value[0]
  Object.keys(defaultStyle).forEach((key) => {
    const v = node.getStyle(key, false)
    style.value[key] = v !== undefined ? v : defaultStyle[key]
  })
}

watch(() => props.mindMap, (mm) => {
  if (!mm) return
  mm.on('node_active', (...args) => {
    activeNodes.value = args[1] || []
    initNodeStyle()
  })
  // 面板可能是节点已激活后才打开的（如切换页签），初始化时同步当前激活节点
  activeNodes.value = mm.renderer.activeNodeList || []
  initNodeStyle()
}, { immediate: true })

function update(prop) {
  if (!props.mindMap || activeNodes.value.length === 0) return
  activeNodes.value.forEach((node) => {
    node.setStyle(prop, style.value[prop])
  })
}

function updateFontWeight() {
  update('fontWeight')
}
function updateFontStyle() {
  update('fontStyle')
}
function updateTextDecoration() {
  update('textDecoration')
}
</script>

<style scoped>
.node-style-panel {
  padding: 8px;
}
.panel-title {
  font-weight: bold;
  margin: 16px 0 8px;
  font-size: 14px;
}
.panel-title:first-child {
  margin-top: 0;
}
.style-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 13px;
  gap: 8px;
}
.style-row > span {
  flex-shrink: 0;
}
.style-row .el-select,
.style-row .el-input-number {
  width: 140px;
}
.empty-tip {
  color: var(--ss-text-muted);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 48px 0;
  font-size: 13px;
}
.empty-icon {
  color: #c7cbd4;
}
.empty-tip p {
  margin: 0;
}
</style>
