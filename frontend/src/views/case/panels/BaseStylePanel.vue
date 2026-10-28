<template>
  <div class="base-style-panel">
    <div class="panel-title">背景</div>
    <div class="style-row">
      <span>背景色</span>
      <el-color-picker v-model="themeConfig.backgroundColor" size="small" @change="applyThemeConfig" />
    </div>
    <div class="style-row">
      <span>背景图片</span>
      <el-input v-model="themeConfig.backgroundImage" size="small" placeholder="none 或 url" @change="applyThemeConfig" />
    </div>
    <div class="style-row">
      <span>图片重复</span>
      <el-select v-model="themeConfig.backgroundRepeat" size="small" @change="applyThemeConfig">
        <el-option label="不重复" value="no-repeat" />
        <el-option label="重复" value="repeat" />
        <el-option label="水平重复" value="repeat-x" />
        <el-option label="垂直重复" value="repeat-y" />
      </el-select>
    </div>
    <div class="style-row">
      <span>图片位置</span>
      <el-input v-model="themeConfig.backgroundPosition" size="small" @change="applyThemeConfig" />
    </div>
    <div class="style-row">
      <span>图片大小</span>
      <el-select v-model="themeConfig.backgroundSize" size="small" @change="applyThemeConfig">
        <el-option label="覆盖" value="cover" />
        <el-option label="包含" value="contain" />
        <el-option label="自动" value="auto" />
      </el-select>
    </div>

    <div class="panel-title">连线</div>
    <div class="style-row">
      <span>颜色</span>
      <el-color-picker v-model="themeConfig.lineColor" size="small" @change="applyThemeConfig" />
    </div>
    <div class="style-row">
      <span>宽度</span>
      <el-input-number v-model="themeConfig.lineWidth" :min="1" :max="10" size="small" @change="applyThemeConfig" />
    </div>
    <div class="style-row">
      <span>风格</span>
      <el-select v-model="themeConfig.lineStyle" size="small" @change="applyThemeConfig">
        <el-option label="直线" value="straight" />
        <el-option label="曲线" value="curve" />
        <el-option label="直连" value="direct" />
      </el-select>
    </div>
    <div class="style-row">
      <span>圆角</span>
      <el-input-number v-model="themeConfig.lineRadius" :min="0" :max="20" size="small" @change="applyThemeConfig" />
    </div>
    <div class="style-row">
      <span>虚线样式</span>
      <el-input v-model="themeConfig.lineDasharray" size="small" placeholder="none 或 5,5" @change="applyThemeConfig" />
    </div>
    <div class="style-row">
      <el-checkbox v-model="themeConfig.showLineMarker" @change="applyThemeConfig">显示箭头</el-checkbox>
    </div>

    <div class="panel-title">概要连线</div>
    <div class="style-row">
      <span>颜色</span>
      <el-color-picker v-model="themeConfig.generalizationLineColor" size="small" @change="applyThemeConfig" />
    </div>
    <div class="style-row">
      <span>宽度</span>
      <el-input-number v-model="themeConfig.generalizationLineWidth" :min="1" :max="10" size="small" @change="applyThemeConfig" />
    </div>

    <div class="panel-title">关联线</div>
    <div class="style-row">
      <span>颜色</span>
      <el-color-picker v-model="themeConfig.associativeLineColor" size="small" @change="applyThemeConfig" />
    </div>
    <div class="style-row">
      <span>宽度</span>
      <el-input-number v-model="themeConfig.associativeLineWidth" :min="1" :max="10" size="small" @change="applyThemeConfig" />
    </div>
    <div class="style-row">
      <span>激活颜色</span>
      <el-color-picker v-model="themeConfig.associativeLineActiveColor" size="small" @change="applyThemeConfig" />
    </div>
    <div class="style-row">
      <span>虚线样式</span>
      <el-input v-model="themeConfig.associativeLineDasharray" size="small" placeholder="none 或 6,4" @change="applyThemeConfig" />
    </div>
    <div class="style-row">
      <span>文字颜色</span>
      <el-color-picker v-model="themeConfig.associativeLineTextColor" size="small" @change="applyThemeConfig" />
    </div>
    <div class="style-row">
      <span>文字大小</span>
      <el-input-number v-model="themeConfig.associativeLineTextFontSize" :min="12" :max="30" size="small" @change="applyThemeConfig" />
    </div>

    <div class="panel-title">彩虹线条</div>
    <div class="style-row">
      <el-checkbox v-model="rainbowLinesConfig.open" @change="applyRainbowLines">开启彩虹线条</el-checkbox>
    </div>

    <div class="panel-title">节点</div>
    <div class="style-row">
      <el-checkbox v-model="themeConfig.nodeUseLineStyle" @change="applyThemeConfig">使用底边横线样式</el-checkbox>
    </div>
    <div class="style-row">
      <span>水平内边距</span>
      <el-input-number v-model="themeConfig.paddingX" :min="0" :max="50" size="small" @change="applyThemeConfig" />
    </div>
    <div class="style-row">
      <span>垂直内边距</span>
      <el-input-number v-model="themeConfig.paddingY" :min="0" :max="50" size="small" @change="applyThemeConfig" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  mindMap: Object,
})

const themeConfig = ref({})
const rainbowLinesConfig = ref({ open: false })

function resetThemeConfig() {
  themeConfig.value = {
    backgroundColor: '#fafafa',
    backgroundImage: 'none',
    backgroundRepeat: 'no-repeat',
    backgroundPosition: 'center center',
    backgroundSize: 'cover',
    lineColor: '#549688',
    lineWidth: 1,
    lineStyle: 'straight',
    lineRadius: 5,
    lineDasharray: 'none',
    showLineMarker: false,
    generalizationLineColor: '#549688',
    generalizationLineWidth: 1,
    associativeLineColor: 'rgb(51, 51, 51)',
    associativeLineWidth: 2,
    associativeLineActiveColor: 'rgba(2, 167, 240, 1)',
    associativeLineDasharray: '6,4',
    associativeLineTextColor: 'rgb(51, 51, 51)',
    associativeLineTextFontSize: 14,
    nodeUseLineStyle: false,
    paddingX: 15,
    paddingY: 5,
  }
}
resetThemeConfig()

watch(() => props.mindMap, (mm) => {
  if (!mm) return
  const currentConfig = mm.getThemeConfig() || {}
  Object.keys(themeConfig.value).forEach((key) => {
    if (currentConfig[key] !== undefined) {
      themeConfig.value[key] = currentConfig[key]
    }
  })
  rainbowLinesConfig.value.open = !!mm.opt?.rainbowLinesConfig?.open
})

function applyThemeConfig() {
  if (!props.mindMap) return
  // 只提交面板管理的配置项，不要用 getThemeConfig() 的全量合并结果，
  // 否则会把当前主题完整快照写入 opt.themeConfig，导致后续切换主题被覆盖失效
  props.mindMap.setThemeConfig({ ...themeConfig.value })
}

function applyRainbowLines() {
  if (!props.mindMap) return
  if (props.mindMap.rainbowLines) {
    props.mindMap.rainbowLines.updateRainLinesConfig({ ...rainbowLinesConfig.value })
  }
}
</script>

<style scoped>
.base-style-panel {
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
.style-row .el-input,
.style-row .el-select,
.style-row .el-input-number {
  width: 140px;
}
</style>
