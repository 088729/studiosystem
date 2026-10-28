<template>
  <div class="versions-panel">
    <el-timeline>
      <el-timeline-item
        v-for="v in versions"
        :key="v.version_no"
        :type="v.version_no === currentVersion ? 'primary' : ''"
      >
        <div class="version-item">
          <div @click="emit('preview-version', v.version_no)">v{{ v.version_no }} {{ v.changelog }}</div>
          <div class="version-meta">{{ v.operator_id }}</div>
          <div v-if="v.version_no !== currentVersion" class="version-actions">
            <el-button link type="primary" size="small" @click="emit('rollback', v.version_no)">回滚</el-button>
          </div>
        </div>
      </el-timeline-item>
    </el-timeline>
  </div>
</template>

<script setup>
defineProps({
  versions: Array,
  currentVersion: Number,
})
const emit = defineEmits(['preview-version', 'rollback'])
</script>

<style scoped>
.versions-panel {
  padding: 8px;
}
.version-item {
  font-size: 13px;
}
.version-item > div:first-child {
  cursor: pointer;
}
.version-item > div:first-child:hover {
  color: #409eff;
}
.version-meta {
  color: #909399;
  font-size: 12px;
}
.version-actions {
  margin-top: 4px;
}
</style>
