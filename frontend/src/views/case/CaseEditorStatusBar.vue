<template>
  <div class="editor-status-bar">
    <span v-if="draftSaved" class="draft-saved"><i class="save-dot"></i>草稿已保存</span>
    <span class="version-info">当前版本: v{{ currentVersion }}</span>
  </div>
</template>

<script setup>
defineProps({
  currentVersion: Number,
  draftSaved: Boolean,
})
</script>

<style scoped>
.editor-status-bar {
  height: 28px;
  border-top: 1px solid var(--ss-border);
  background: #fafbfc;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  font-size: 12px;
  color: var(--ss-text-muted);
}
.draft-saved {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: #16a34a;
}
.save-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
}
.version-info {
  margin-left: auto;
}
</style>
