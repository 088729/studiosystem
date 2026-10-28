<template>
  <div class="error-page">
    <div class="error-blob blob-1"></div>
    <div class="error-blob blob-2"></div>
    <div class="error-card">
      <div class="logo-mark">S</div>
      <div class="error-code">{{ code }}</div>
      <h2 class="error-title">{{ title }}</h2>
      <p class="error-desc">{{ desc }}</p>
      <div class="error-actions">
        <el-button class="primary-btn" type="primary" size="large" @click="goHome">
          返回首页
        </el-button>
        <el-button v-if="showBack" size="large" @click="goBack">上一页</el-button>
      </div>
    </div>
    <div class="copyright">Studio System · 内部部署</div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'

defineProps({
  code: { type: String, required: true },
  title: { type: String, required: true },
  desc: { type: String, default: '' },
  showBack: { type: Boolean, default: true },
})

const router = useRouter()

function goHome() {
  router.push('/case')
}
function goBack() {
  router.back()
}
</script>

<style scoped>
.error-page {
  height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(145deg, #4f6ef7 0%, #3f5be0 45%, #2f3fa8 100%);
  overflow: hidden;
  position: relative;
  color: #fff;
}
.error-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
}
.blob-1 {
  width: 480px;
  height: 480px;
  right: -140px;
  top: -120px;
  background: #8fa3ff;
  opacity: 0.4;
  animation: drift 14s ease-in-out infinite alternate;
}
.blob-2 {
  width: 380px;
  height: 380px;
  left: -120px;
  bottom: -140px;
  background: #6ee7d8;
  opacity: 0.22;
  animation: drift 18s ease-in-out infinite alternate-reverse;
}
@keyframes drift {
  from { transform: translate(0, 0) scale(1); }
  to { transform: translate(40px, 30px) scale(1.12); }
}

.error-card {
  position: relative;
  z-index: 1;
  text-align: center;
  animation: rise 0.6s ease both;
}
@keyframes rise {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: translateY(0); }
}

.logo-mark {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 800;
  color: #fff;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(6px);
  margin: 0 auto 28px;
}

.error-code {
  font-size: 96px;
  font-weight: 800;
  line-height: 1;
  letter-spacing: 4px;
  text-shadow: 0 12px 32px rgba(23, 30, 44, 0.35);
}
.error-title {
  font-size: 22px;
  font-weight: 600;
  margin: 18px 0 10px;
}
.error-desc {
  font-size: 14px;
  opacity: 0.78;
  line-height: 1.8;
}

.error-actions {
  margin-top: 32px;
  display: flex;
  gap: 12px;
  justify-content: center;
}
.primary-btn {
  min-width: 120px;
  border-radius: 10px;
  font-weight: 600;
  background: #fff;
  border: none;
  color: var(--ss-primary);
  box-shadow: 0 8px 20px rgba(23, 30, 44, 0.25);
}
.primary-btn:hover {
  background: #f4f6ff;
  color: var(--ss-primary);
}
.error-actions :deep(.el-button:not(.primary-btn)) {
  background: rgba(255, 255, 255, 0.12);
  border: 1px solid rgba(255, 255, 255, 0.3);
  color: #fff;
}
.error-actions :deep(.el-button:not(.primary-btn)):hover {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

.copyright {
  position: absolute;
  bottom: 18px;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.55);
}
</style>
