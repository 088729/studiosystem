<template>
  <div>
    <div class="toolbar">
      <el-input v-model="search" placeholder="搜索用户名/姓名" clearable style="width: 240px" />
      <el-button type="primary" @click="loadUsers">搜索</el-button>
      <el-button type="success" @click="openCreateDialog">新建用户</el-button>
    </div>
    <el-table :data="users" v-loading="loading" style="width: 100%">
      <el-table-column prop="username" label="用户名" />
      <el-table-column prop="full_name" label="姓名" />
      <el-table-column prop="department" label="部门" />
      <el-table-column prop="role_name" label="角色" />
      <el-table-column prop="is_active" label="在职">
        <template #default="{ row }">
          <el-tag :type="row.is_active ? 'success' : 'danger'">{{ row.is_active ? '是' : '否' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="240">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEditDialog(row)">编辑权限</el-button>
          <el-button link :type="row.is_active ? 'danger' : 'success'" @click="toggleActive(row)">
            {{ row.is_active ? '禁用' : '启用' }}
          </el-button>
          <el-button link type="danger" @click="deleteUser(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dialogVisible" title="编辑权限" width="500px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="角色">
          <el-select v-model="form.role_name" placeholder="选择角色" style="width: 100%">
            <el-option v-for="role in roles" :key="role.name" :label="role.name" :value="role.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="追加权限">
          <el-select v-model="form.extra" multiple placeholder="选择权限" style="width: 100%">
            <el-option v-for="p in permissions" :key="p.key" :label="p.key" :value="p.key" />
          </el-select>
        </el-form-item>
        <el-form-item label="禁止权限">
          <el-select v-model="form.denied" multiple placeholder="选择权限" style="width: 100%">
            <el-option v-for="p in permissions" :key="p.key" :label="p.key" :value="p.key" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="savePermissions">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="createDialogVisible" title="新建用户" width="500px">
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="用户名">
          <el-input v-model="createForm.username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="createForm.password" type="password" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="createForm.role_name" placeholder="选择角色" style="width: 100%">
            <el-option v-for="role in roles" :key="role.name" :label="role.name" :value="role.name" />
          </el-select>
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="createForm.full_name" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createUser">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import * as authApi from '@/api/auth'

const users = ref([])
const roles = ref([])
const permissions = ref([])
const loading = ref(false)
const search = ref('')

const dialogVisible = ref(false)
const currentUser = ref(null)
const form = reactive({ role_name: '', extra: [], denied: [] })

const createDialogVisible = ref(false)
const createForm = reactive({ username: '', password: '', role_name: 'viewer', full_name: '' })

async function loadUsers() {
  loading.value = true
  try {
    users.value = await authApi.getUsers({ q: search.value })
  } finally {
    loading.value = false
  }
}

async function loadRolesAndPermissions() {
  const [rolesRes, permsRes] = await Promise.all([
    authApi.getRoles(),
    authApi.getPermissions(),
  ])
  roles.value = rolesRes
  permissions.value = permsRes.items || []
}

function openEditDialog(row) {
  currentUser.value = row
  form.role_name = row.role_name
  form.extra = row.perms.filter(p => {
    const role = roles.value.find(r => r.name === row.role_name)
    return role ? !role.permissions.includes(p) : true
  })
  form.denied = []
  dialogVisible.value = true
}

async function savePermissions() {
  await authApi.updateUserPermissions(currentUser.value.username, {
    role_name: form.role_name,
    extra: form.extra,
    denied: form.denied,
  })
  ElMessage.success('保存成功')
  dialogVisible.value = false
  loadUsers()
}

async function toggleActive(row) {
  await authApi.setUserActive(row.username, { is_active: !row.is_active })
  ElMessage.success('操作成功')
  loadUsers()
}

async function deleteUser(row) {
  await ElMessageBox.confirm('确认删除该用户？', '提示', { type: 'warning' })
  await authApi.deleteUser(row.username)
  ElMessage.success('删除成功')
  loadUsers()
}

function openCreateDialog() {
  createForm.username = ''
  createForm.password = ''
  createForm.role_name = 'viewer'
  createForm.full_name = ''
  createDialogVisible.value = true
}

async function createUser() {
  await authApi.createUser(createForm)
  ElMessage.success('创建成功')
  createDialogVisible.value = false
  loadUsers()
}

onMounted(() => {
  loadUsers()
  loadRolesAndPermissions()
})
</script>

<style scoped>
.toolbar {
  margin-bottom: 16px;
  display: flex;
  gap: 8px;
}
</style>
