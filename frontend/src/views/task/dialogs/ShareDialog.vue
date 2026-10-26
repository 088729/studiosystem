<template>
  <el-dialog v-model="visible" title="共享清单" width="420px">
    <div class="share-dialog">
      <div v-if="isOwner" class="share-add">
        <el-select
          v-model="selectedUser"
          filterable
          placeholder="选择要共享给的成员"
          style="flex: 1"
        >
          <el-option
            v-for="u in candidates"
            :key="u.username"
            :label="u.full_name ? `${u.username}（${u.full_name}）` : u.username"
            :value="u.username"
          />
        </el-select>
        <el-button type="primary" :disabled="!selectedUser" @click="add">添加</el-button>
      </div>

      <div class="member-list">
        <div class="member-item owner-item">
          <User :size="14" style="vertical-align: -2px" />
          <span class="member-name">{{ list?.owner }}</span>
          <el-tag size="small" type="primary" effect="plain">所有者</el-tag>
        </div>
        <div v-for="m in members" :key="m.username" class="member-item">
          <User :size="14" style="vertical-align: -2px" />
          <span class="member-name">{{ m.username }}</span>
          <template v-if="isOwner">
            <el-select
              :model-value="m.role"
              size="small"
              style="width: 90px"
              @change="(r) => setRole(m, r)"
            >
              <el-option value="viewer" label="只读" />
              <el-option value="editor" label="可编辑" />
            </el-select>
            <el-button link type="primary" size="small" @click="transfer(m)">转让</el-button>
            <el-button link type="danger" size="small" @click="remove(m)">移除</el-button>
          </template>
          <el-tag v-else size="small" effect="plain">{{ m.role === 'editor' ? '可编辑' : '只读' }}</el-tag>
        </div>
        <el-empty v-if="!members.length" description="尚未共享给任何人" :image-size="50" />
      </div>

      <div v-if="!isOwner" class="share-footer">
        <el-button type="danger" plain @click="leave">退出共享</el-button>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User } from 'lucide-vue-next'
import { useTaskStore } from '@/stores/task'
import { useAuthStore } from '@/stores/auth'
import * as taskApi from '@/api/task'

const store = useTaskStore()
const authStore = useAuthStore()

const visible = ref(false)
const list = ref(null)
const members = ref([])
const users = ref([])
const selectedUser = ref('')

const isOwner = computed(() => list.value?.owner === authStore.userInfo?.username)

const candidates = computed(() =>
  users.value.filter(
    (u) => u.username !== list.value?.owner && !members.value.some((m) => m.username === u.username)
  )
)

async function open(taskList) {
  list.value = taskList
  visible.value = true
  selectedUser.value = ''
  // 成员视角只需成员列表；用户候选仅 owner 添加成员时需要
  const [m, u] = await Promise.all([
    taskApi.fetchListMembers(taskList.id),
    isOwner.value ? taskApi.fetchShareUsers() : Promise.resolve({ items: [] }),
  ])
  members.value = m.items
  users.value = u.items
}

async function add() {
  try {
    const res = await taskApi.addListMember(list.value.id, selectedUser.value)
    members.value = res.items
    selectedUser.value = ''
    ElMessage.success('已共享')
    store.fetchLists()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail?.message || '添加失败')
  }
}

async function remove(m) {
  const res = await taskApi.removeListMember(list.value.id, m.username)
  members.value = res.items
  store.fetchLists()
}

async function setRole(m, role) {
  const res = await taskApi.setMemberRole(list.value.id, m.username, role)
  members.value = res.items
  store.fetchLists()
}

async function transfer(m) {
  try {
    await ElMessageBox.confirm(
      `将清单「${list.value.name}」的所有权转让给 ${m.username}？转让后你将降为可编辑成员。`,
      '转让所有权',
      { type: 'warning', confirmButtonText: '转让', cancelButtonText: '取消' }
    )
  } catch {
    return // 用户取消
  }
  await taskApi.transferOwner(list.value.id, m.username)
  ElMessage.success('已转让')
  visible.value = false
  store.fetchLists()
}

async function leave() {
  try {
    await ElMessageBox.confirm(
      `退出共享清单「${list.value.name}」？退出后将不再可见该清单。`,
      '退出共享',
      { type: 'warning', confirmButtonText: '退出', cancelButtonText: '取消' }
    )
  } catch {
    return // 用户取消
  }
  await taskApi.leaveList(list.value.id)
  ElMessage.success('已退出共享')
  visible.value = false
  if (store.activeListKey === `list:${list.value.id}`) {
    await store.selectList('smart:inbox')
  }
  store.fetchLists()
}

defineExpose({ open })
</script>

<style scoped>
.share-add {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.member-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid var(--ss-border);
  font-size: 14px;
}
.member-name {
  flex: 1;
}
.owner-item {
  color: var(--ss-text-secondary);
}
.share-footer {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
