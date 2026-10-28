<template>
  <div class="platform-admin">
    <el-tabs v-model="activeTab" type="border-card">
      <el-tab-pane label="用户管理" name="users">
        <UserManager />
      </el-tab-pane>
      <el-tab-pane label="角色管理" name="roles">
        <RoleManager />
      </el-tab-pane>
      <el-tab-pane label="权限管理" name="permissions">
        <PermissionManager />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import UserManager from './admin/UserManager.vue'
import RoleManager from './admin/RoleManager.vue'
import PermissionManager from './admin/PermissionManager.vue'

const activeTab = ref('users')
</script>

<style scoped>
.platform-admin {
  padding: 20px;
  height: 100%;
  box-sizing: border-box;
  overflow-y: auto;
  background: #f5f7fa;
}
</style>
