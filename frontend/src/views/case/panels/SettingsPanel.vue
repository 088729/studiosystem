<template>
  <div class="settings-panel">
    <div class="panel-title">画布设置</div>
    <div class="setting-row">
      <el-checkbox v-model="settings.enableAutoEnterTextEditWhenKeydown" @change="apply">键盘输入自动进入编辑</el-checkbox>
    </div>
    <div class="setting-row">
      <el-checkbox v-model="settings.alwaysShowExpandBtn" @change="applyAndRender">一直显示展开收起按钮</el-checkbox>
    </div>
    <div class="setting-row">
      <el-checkbox v-model="settings.enableDblclickBackToRootNode" @change="apply">双击回到根节点</el-checkbox>
    </div>
    <div class="setting-row">
      <el-checkbox v-model="settings.isDisableDrag" @change="apply">禁止拖动画布</el-checkbox>
    </div>

    <div class="panel-title">鼠标滚轮</div>
    <div class="setting-row">
      <span>滚轮行为</span>
      <el-select v-model="settings.mousewheelAction" size="small" @change="apply">
        <el-option label="移动画布" value="move" />
        <el-option label="缩放画布" value="zoom" />
      </el-select>
    </div>
    <div class="setting-row">
      <span>移动步长</span>
      <el-input-number v-model="settings.mousewheelMoveStep" :min="20" :max="300" size="small" @change="apply" />
    </div>
    <div class="setting-row">
      <el-checkbox v-model="settings.mousewheelZoomActionReverse" @change="apply">缩放方向反转</el-checkbox>
    </div>

    <div class="panel-title">新建节点</div>
    <div class="setting-row">
      <span>创建行为</span>
      <el-select v-model="settings.createNewNodeBehavior" size="small" @change="apply">
        <el-option label="默认（激活并进入编辑）" value="default" />
        <el-option label="不激活" value="notActive" />
        <el-option label="仅激活" value="activeOnly" />
      </el-select>
    </div>

    <div class="panel-title">间距</div>
    <div class="setting-row">
      <span>图片文字间距</span>
      <el-input-number v-model="settings.imgTextMargin" :min="0" :max="20" size="small" @change="applyAndRender" />
    </div>
    <div class="setting-row">
      <span>内容间距</span>
      <el-input-number v-model="settings.textContentMargin" :min="0" :max="20" size="small" @change="applyAndRender" />
    </div>

    <div class="panel-title">水印</div>
    <div class="setting-row">
      <span>水印文字</span>
      <el-input v-model="watermark.text" size="small" class="wm-input" placeholder="留空 = 不显示水印" @input="applyWatermark" />
    </div>
    <div class="setting-row">
      <span>仅导出时显示</span>
      <el-checkbox v-model="watermark.onlyExport" @change="applyWatermark" />
    </div>
    <div class="setting-row">
      <span>旋转角度</span>
      <el-input-number v-model="watermark.angle" :min="0" :max="90" size="small" @change="applyWatermark" />
    </div>
    <div class="setting-row">
      <span>字号</span>
      <el-input-number v-model="watermark.fontSize" :min="10" :max="40" size="small" @change="applyWatermark" />
    </div>
    <div class="setting-row">
      <span>不透明度</span>
      <el-slider v-model="watermark.opacity" :min="0.1" :max="1" :step="0.1" size="small" class="wm-slider" @change="applyWatermark" />
    </div>
    <div class="setting-row">
      <span>文字颜色</span>
      <el-color-picker v-model="watermark.color" size="small" @change="applyWatermark" />
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  mindMap: Object,
})

const defaultSettings = {
  enableAutoEnterTextEditWhenKeydown: false,
  alwaysShowExpandBtn: false,
  enableDblclickBackToRootNode: false,
  isDisableDrag: false,
  mousewheelAction: 'move',
  mousewheelMoveStep: 100,
  mousewheelZoomActionReverse: true,
  createNewNodeBehavior: 'default',
  imgTextMargin: 5,
  textContentMargin: 2,
}

const settings = ref({ ...defaultSettings })

// 水印配置（Watermark 插件 watermarkConfig）
const watermarkDefaults = {
  text: '',
  onlyExport: false,
  angle: 30,
  fontSize: 14,
  opacity: 0.5,
  color: '#999999',
  lineSpacing: 100,
  textSpacing: 100,
  belowNode: false,
}
const watermark = ref({ ...watermarkDefaults })

watch(() => props.mindMap, (mm) => {
  if (!mm) return
  const opt = mm.opt || {}
  Object.keys(defaultSettings).forEach((key) => {
    if (opt[key] !== undefined) {
      settings.value[key] = opt[key]
    }
  })
  const wc = opt.watermarkConfig || {}
  watermark.value = {
    ...watermark.value,
    text: wc.text ?? '',
    onlyExport: !!wc.onlyExport,
    angle: wc.angle ?? 30,
    fontSize: wc.textStyle?.fontSize ?? 14,
    opacity: wc.textStyle?.opacity ?? 0.5,
    color: wc.textStyle?.color ?? '#999999',
  }
}, { immediate: true })

function apply() {
  if (!props.mindMap) return
  props.mindMap.updateConfig({ ...settings.value })
}

function applyAndRender() {
  apply()
  props.mindMap?.reRender()
}

// 水印：updateConfig 落 opt，再显式触发水印重绘
function applyWatermark() {
  const mm = props.mindMap
  if (!mm) return
  const wc = {
    text: watermark.value.text || '',
    onlyExport: watermark.value.onlyExport,
    angle: watermark.value.angle,
    lineSpacing: 100,
    textSpacing: 100,
    belowNode: false,
    textStyle: {
      color: watermark.value.color,
      opacity: watermark.value.opacity,
      fontSize: watermark.value.fontSize,
    },
  }
  mm.updateConfig({ watermarkConfig: wc })
  mm.watermark?.updateWatermark(wc)
}
</script>

<style scoped>
.settings-panel {
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
.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
  font-size: 13px;
  gap: 8px;
}
.setting-row .el-select,
.setting-row .el-input-number {
  width: 140px;
}
</style>
