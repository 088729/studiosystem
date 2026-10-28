<template>
  <div>
    <div class="toolbar">
      <el-input v-model="newKey" placeholder="权限 key" style="width: 240px" />
      <el-button type="success" @click="createPermission">新增权限</el-button>
    </div>
    <el-table :data="permissions" v-loading="loading" style="width: 100%">
      <el-table-column prop="key" label="权限 key" />
      <el-table-column prop="builtin" label="内置">
        <template #default="{ row }">
          <el-tag :type="row.builtin ? 'info' : 'success'">{{ row.builtin ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="120">
        <template #default="{ row }">
          <el-button link type="danger" :disabled="row.builtin" @click="deletePermission(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as authApi from '@/api/auth'

const permissions = ref([])
const loading = ref(false)
const newKey = ref('')

async function loadData() {
  loading.value = true
  try {
    const res = await authApi.getPlatformPermissions()
    permissions.value = res.items || []
  } finally {
    loading.value = false
  }
}

async function createPermission() {
  if (!newKey.value) return
  await authApi.createPermission({ key: newKey.value })
  ElMessage.success('创建成功')
  newKey.value = ''
  loadData()
}

async function deletePermission(row) {
  await ElMessageBox.confirm('确认删除该权限 key？', '提示', { type: 'warning' })
  await authApi.deletePermission(row.key)
  ElMessage.success('删除成功')
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
  display: flex;
  gap: 8px;
}
</style>
