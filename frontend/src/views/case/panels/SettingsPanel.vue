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

watch(() => props.mindMap, (mm) => {
  if (!mm) return
  const opt = mm.opt || {}
  Object.keys(defaultSettings).forEach((key) => {
    if (opt[key] !== undefined) {
      settings.value[key] = opt[key]
    }
  })
})

function apply() {
  if (!props.mindMap) return
  props.mindMap.updateConfig({ ...settings.value })
}

function applyAndRender() {
  apply()
  props.mindMap?.reRender()
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
