<template>
  <div class="profile-page">
    <div class="profile-wrap">
      <!-- 头部身份卡 -->
      <div class="hero-card">
        <div class="hero-bg"></div>
        <div class="hero-main">
          <div class="hero-avatar">{{ avatarInitial }}</div>
          <div class="hero-meta">
            <h2>{{ user.full_name || user.username }}</h2>
            <div class="hero-sub">
              <el-tag class="role-tag" size="small" effect="dark">{{ user.role_name || '用户' }}</el-tag>
              <span v-if="user.department" class="meta-item">{{ user.department }}</span>
              <span v-if="user.email" class="meta-item">{{ user.email }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 账号信息卡 -->
      <div class="info-card">
        <div class="info-title">账号信息</div>
        <div class="info-grid">
          <div class="info-row">
            <span class="info-label">用户名</span>
            <span class="info-value">{{ user.username }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">姓名</span>
            <span class="info-value">{{ user.full_name || '-' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">邮箱</span>
            <span class="info-value">{{ user.email || '-' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">部门</span>
            <span class="info-value">{{ user.department || '-' }}</span>
          </div>
        </div>

        <el-divider class="section-divider" />

        <div class="info-title">工作职能</div>
        <div v-if="canEditJobScope" class="jobscope-edit">
          <el-input
            v-model="jobScope"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="填写你的工作职能，方便同事了解你负责的方向"
          />
          <div class="jobscope-actions">
            <el-button type="primary" :loading="saving" @click="saveJobScope">保存</el-button>
          </div>
        </div>
        <p v-else class="jobscope-text">{{ user.job_scope || '未填写' }}</p>

        <el-divider class="section-divider" />

        <div class="info-title">权限</div>
        <div class="perm-list">
          <el-tag
            v-for="perm in user.perms"
            :key="perm"
            class="perm-tag"
            size="small"
          >
            {{ perm }}
          </el-tag>
          <span v-if="!user.perms?.length" class="info-value">-</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import * as authApi from '@/api/auth'

const authStore = useAuthStore()
const user = computed(() => authStore.userInfo || {})
const jobScope = ref(user.value.job_scope || '')
const saving = ref(false)
const canEditJobScope = computed(() => authStore.userInfo?.username === user.value.username)

const avatarInitial = computed(() => {
  const name = user.value.username || '?'
  return name.trim().charAt(0).toUpperCase()
})

async function saveJobScope() {
  saving.value = true
  try {
    await authApi.updateJobScope(user.value.username, { job_scope: jobScope.value })
    await authStore.fetchMe()
    ElMessage.success('保存成功')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.profile-page {
  height: 100%;
  overflow-y: auto;
  background: var(--ss-bg);
  padding: 32px 24px 48px;
}
.profile-wrap {
  max-width: 720px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ---------- 头部身份卡 ---------- */
.hero-card {
  position: relative;
  border-radius: 16px;
  overflow: hidden;
  background: #fff;
  border: 1px solid var(--ss-border);
  box-shadow: var(--ss-shadow);
}
.hero-bg {
  height: 96px;
  background: linear-gradient(120deg, #4f6ef7 0%, #6b85f8 55%, #8fa3ff 100%);
}
.hero-main {
  display: flex;
  align-items: flex-end;
  gap: 20px;
  padding: 0 28px 22px;
  margin-top: -36px;
  position: relative;
}
.hero-avatar {
  width: 88px;
  height: 88px;
  border-radius: 24px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(135deg, #6b85f8, #4f6ef7);
  border: 4px solid #fff;
  box-shadow: 0 8px 20px rgba(79, 110, 247, 0.35);
}
.hero-meta {
  padding-bottom: 4px;
  min-width: 0;
}
.hero-meta h2 {
  font-size: 22px;
  font-weight: 700;
  color: var(--ss-text);
  margin-bottom: 8px;
}
.hero-sub {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 13px;
  color: var(--ss-text-secondary);
}
.role-tag {
  border: none;
  background: linear-gradient(135deg, #6b85f8, #4f6ef7);
}
.meta-item + .meta-item::before {
  content: '·';
  margin-right: 10px;
  color: var(--ss-text-muted);
}

/* ---------- 信息卡 ---------- */
.info-card {
  background: #fff;
  border-radius: 16px;
  border: 1px solid var(--ss-border);
  box-shadow: var(--ss-shadow);
  padding: 26px 28px;
}
.info-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--ss-text);
  margin-bottom: 16px;
  padding-left: 10px;
  border-left: 3px solid var(--ss-primary);
  line-height: 1.2;
}
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px 24px;
}
.info-row {
  display: flex;
  align-items: center;
  gap: 14px;
  font-size: 14px;
}
.info-label {
  width: 56px;
  flex-shrink: 0;
  color: var(--ss-text-muted);
}
.info-value {
  color: var(--ss-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.section-divider {
  margin: 22px 0;
  --el-border-color: var(--ss-border);
}

/* 工作职能 */
.jobscope-actions {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}
.jobscope-text {
  font-size: 14px;
  color: var(--ss-text-secondary);
  line-height: 1.8;
  white-space: pre-wrap;
}

/* 权限标签 */
.perm-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.perm-tag {
  border-radius: 6px;
  border-color: #c7d2fe;
  background: var(--ss-primary-light);
  color: var(--ss-primary);
}

/* ---------- 响应式 ---------- */
@media (max-width: 640px) {
  .info-grid {
    grid-template-columns: 1fr;
  }
  .hero-main {
    padding: 0 20px 18px;
  }
}
</style>
