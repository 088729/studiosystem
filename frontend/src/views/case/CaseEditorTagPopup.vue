<template>
  <div
    v-if="visible"
    class="tag-popup"
    :style="{ left: `${x}px`, top: `${y}px` }"
    @click.stop
  >
    <div class="tag-input">
      <el-input v-model="tagText" size="small" placeholder="输入标签" @keyup.enter="addTag" />
      <el-button size="small" type="primary" @click="addTag">添加</el-button>
    </div>
    <div class="tag-list">
      <el-tag
        v-for="(tag, index) in tags"
        :key="index"
        closable
        size="small"
        @close="removeTag(index)"
      >
        {{ typeof tag === 'string' ? tag : tag.text }}
      </el-tag>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'

const props = defineProps({
  mindMap: Object,
})

const visible = ref(false)
const x = ref(0)
const y = ref(0)
const activeNode = ref(null)
const tagText = ref('')
const tags = ref([])

watch(() => props.mindMap, (mm) => {
  if (!mm) return
  mm.on('node_tag_click', (node, e) => {
    e.stopPropagation()
    activeNode.value = node
    tags.value = node.getData('tag') || []
    x.value = e.clientX
    y.value = e.clientY - 40
    visible.value = true
  })
})

function addTag() {
  if (!tagText.value || !activeNode.value) return
  const current = activeNode.value.getData('tag') || []
  current.push(tagText.value)
  activeNode.value.setData('tag', current)
  tags.value = current
  props.mindMap.render()
  tagText.value = ''
}

function removeTag(index) {
  if (!activeNode.value) return
  const current = activeNode.value.getData('tag') || []
  current.splice(index, 1)
  activeNode.value.setData('tag', current)
  tags.value = current
  props.mindMap.render()
}

function hide() {
  visible.value = false
}

defineExpose({ hide })
</script>

<style scoped>
.tag-popup {
  position: fixed;
  background: #fff;
  border: 1px solid #e4e7ed;
  border-radius: 4px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  padding: 10px;
  z-index: 2000;
  min-width: 200px;
}
.tag-input {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
</style>
