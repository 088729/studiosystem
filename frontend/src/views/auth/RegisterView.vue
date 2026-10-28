<template>
  <div class="auth-container">
    <AuthBrandPanel hero-title="加入<br />Studio System" hero-desc="注册账号，开启你的<br />一站式创作与工作台。" />

    <!-- 右侧表单面板 -->
    <div class="form-panel">
      <div class="form-card">
        <div class="form-header">
          <div class="logo-mark small">S</div>
          <h2>创建账号</h2>
          <p>填写以下信息完成注册</p>
        </div>

        <el-form :model="form" size="large" @keyup.enter="handleRegister">
          <el-form-item>
            <el-input
              v-model="form.username"
              placeholder="用户名"
              :prefix-icon="User"
              clearable
            />
          </el-form-item>
          <el-form-item>
            <el-input
              v-model="form.password"
              type="password"
              placeholder="密码（至少 6 位）"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>
          <el-form-item>
            <el-input
              v-model="form.confirmPassword"
              type="password"
              placeholder="确认密码"
              :prefix-icon="Lock"
              show-password
            />
          </el-form-item>

          <el-divider class="optional-divider">选填信息</el-divider>

          <el-form-item>
            <el-input v-model="form.full_name" placeholder="姓名" :prefix-icon="Postcard" clearable />
          </el-form-item>
          <el-form-item>
            <el-input v-model="form.email" placeholder="邮箱" :prefix-icon="Message" clearable />
          </el-form-item>
          <el-form-item>
            <el-input v-model="form.department" placeholder="部门" :prefix-icon="OfficeBuilding" clearable />
          </el-form-item>

          <el-button
            class="submit-btn"
            type="primary"
            size="large"
            :loading="loading"
            @click="handleRegister"
          >
            注 册
          </el-button>
        </el-form>

        <div class="form-footer">
          <span>已有账号？</span>
          <el-button link type="primary" @click="goLogin">返回登录</el-button>
        </div>
      </div>
      <div class="copyright">Studio System · 内部部署</div>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock, Postcard, Message, OfficeBuilding } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import * as authApi from '@/api/auth'
import AuthBrandPanel from './AuthBrandPanel.vue'

const router = useRouter()

const form = reactive({
  username: '',
  password: '',
  confirmPassword: '',
  full_name: '',
  email: '',
  department: '',
})
const loading = ref(false)

async function handleRegister() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  if (form.password !== form.confirmPassword) {
    ElMessage.warning('两次输入的密码不一致')
    return
  }
  if (form.password.length < 6) {
    ElMessage.warning('密码长度不能少于 6 位')
    return
  }
  loading.value = true
  try {
    await authApi.register({
      username: form.username,
      password: form.password,
      full_name: form.full_name || null,
      email: form.email || null,
      department: form.department || null,
    })
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (e) {
    // error handled by interceptor
  } finally {
    loading.value = false
  }
}

function goLogin() {
  router.push('/login')
}
</script>

<style scoped>
.auth-container {
  height: 100vh;
  display: flex;
  background: var(--ss-bg);
  overflow: hidden;
}

/* ---------- 右侧表单面板 ---------- */
.form-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px 24px;
  position: relative;
  overflow-y: auto;
}
.form-card {
  width: 100%;
  max-width: 400px;
  background: #fff;
  border-radius: 16px;
  box-shadow: var(--ss-shadow-lg);
  border: 1px solid var(--ss-border);
  padding: 36px 40px 28px;
  animation: rise 0.6s 0.08s ease both;
}
@keyframes rise {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: translateY(0); }
}

.form-header {
  text-align: center;
  margin-bottom: 24px;
}
.logo-mark {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 26px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(135deg, #6b85f8, #4f6ef7);
  box-shadow: 0 6px 16px rgba(79, 110, 247, 0.3);
  margin: 0 auto 20px;
}
.form-header h2 {
  font-size: 24px;
  font-weight: 700;
  color: var(--ss-text);
  margin-bottom: 8px;
}
.form-header p {
  font-size: 14px;
  color: var(--ss-text-secondary);
}

.optional-divider {
  margin: 4px 0 20px;
  --el-border-color: var(--ss-border);
}
.optional-divider :deep(.el-divider__text) {
  font-size: 12px;
  color: var(--ss-text-muted);
}

.submit-btn {
  width: 100%;
  height: 46px;
  font-size: 16px;
  letter-spacing: 6px;
  font-weight: 600;
  border-radius: 10px;
  background: linear-gradient(135deg, #6b85f8, #4f6ef7);
  border: none;
  box-shadow: 0 6px 16px rgba(79, 110, 247, 0.35);
  transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
}
.submit-btn:hover {
  opacity: 0.94;
  transform: translateY(-1px);
  box-shadow: 0 10px 22px rgba(79, 110, 247, 0.42);
  background: linear-gradient(135deg, #6b85f8, #4f6ef7);
}
.submit-btn:active {
  transform: translateY(0);
}

.form-footer {
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid var(--ss-border);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  font-size: 14px;
  color: var(--ss-text-secondary);
}

.copyright {
  position: absolute;
  bottom: 18px;
  font-size: 12px;
  color: var(--ss-text-muted);
}

/* ---------- 输入框细节 ---------- */
:deep(.el-input__wrapper) {
  border-radius: 10px;
  padding: 4px 14px;
  min-height: 46px;
  box-shadow: 0 0 0 1px var(--ss-border) inset;
  background: #f8fafc;
}
:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #c7d2fe inset;
}
:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px var(--ss-primary) inset, 0 0 0 4px rgba(79, 110, 247, 0.08);
  background: #fff;
}

/* 覆盖浏览器自动填充的默认底色 */
:deep(input:-webkit-autofill),
:deep(input:-webkit-autofill:hover),
:deep(input:-webkit-autofill:focus),
:deep(input:-webkit-autofill:active) {
  -webkit-box-shadow: 0 0 0 1000px #f8fafc inset !important;
  -webkit-text-fill-color: #606266 !important;
  transition: background-color 5000s ease-in-out 0s !important;
}

/* ---------- 响应式 ---------- */
@media (max-width: 900px) {
  .form-panel {
    background: linear-gradient(145deg, #4f6ef7 0%, #2f3fa8 100%);
  }
  .copyright {
    color: rgba(255, 255, 255, 0.6);
  }
}
</style>
