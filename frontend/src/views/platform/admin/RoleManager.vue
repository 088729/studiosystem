<template>
  <div>
    <div class="toolbar">
      <el-button type="success" @click="openCreateDialog">新建角色</el-button>
    </div>
    <el-table :data="roles" v-loading="loading" style="width: 100%">
      <el-table-column prop="name" label="角色名" />
      <el-table-column prop="description" label="描述" />
      <el-table-column prop="permissions" label="权限" show-overflow-tooltip>
        <template #default="{ row }">
          {{ row.permissions.join(', ') }}
        </template>
      </el-table-column>
      <el-table-column label="操作" width="180">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
          <el-button link type="danger" @click="deleteRole(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑角色' : '新建角色'" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="角色名">
          <el-input v-model="form.name" :disabled="isEdit" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" />
        </el-form-item>
        <el-form-item label="权限">
          <el-select v-model="form.permissions" multiple placeholder="选择权限" style="width: 100%">
            <el-option v-for="p in permissions" :key="p.key" :label="p.key" :value="p.key" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveRole">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as authApi from '@/api/auth'

const roles = ref([])
const permissions = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const form = reactive({ name: '', description: '', permissions: [] })

async function loadData() {
  loading.value = true
  try {
    const [rolesRes, permsRes] = await Promise.all([
      authApi.getRoles(),
      authApi.getPlatformPermissions(),
    ])
    roles.value = rolesRes
    permissions.value = permsRes.items || []
  } finally {
    loading.value = false
  }
}

function openCreateDialog() {
  isEdit.value = false
  form.name = ''
  form.description = ''
  form.permissions = []
  dialogVisible.value = true
}

function openEditDialog(row) {
  isEdit.value = true
  form.name = row.name
  form.description = row.description || ''
  form.permissions = row.permissions || []
  dialogVisible.value = true
}

async function saveRole() {
  if (isEdit.value) {
    await authApi.updateRole(form.name, {
      name: form.name,
      description: form.description,
      permissions: form.permissions,
    })
  } else {
    await authApi.createRole({
      name: form.name,
      description: form.description,
      permissions: form.permissions,
    })
  }
  ElMessage.success('保存成功')
  dialogVisible.value = false
  loadData()
}

async function deleteRole(row) {
  await ElMessageBox.confirm('确认删除该角色？', '提示', { type: 'warning' })
  await authApi.deleteRole(row.name)
  ElMessage.success('删除成功')
  loadData()
}

onMounted(loadData)
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
}
</style>
