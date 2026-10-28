<template>
  <div class="brand-panel">
    <div class="brand-blob blob-1"></div>
    <div class="brand-blob blob-2"></div>
    <div class="brand-content">
      <div class="brand-logo">
        <div class="logo-mark">S</div>
        <span class="logo-text">Studio System</span>
      </div>
      <div class="brand-hero">
        <h1 v-html="heroTitle"></h1>
        <p v-html="heroDesc"></p>
      </div>
      <ul class="brand-features">
        <li v-for="f in features" :key="f.title">
          <span class="feature-dot"></span>
          <div>
            <strong>{{ f.title }}</strong>
            <span>{{ f.desc }}</span>
          </div>
        </li>
      </ul>
    </div>
  </div>
</template>

<script setup>
defineProps({
  heroTitle: { type: String, default: '一站式创作<br />与工作台' },
  heroDesc: {
    type: String,
    default: '图谱 · 任务 · 番茄钟 · 习惯打卡 · 知识库，<br />把你的工作室装进口袋。',
  },
})

const features = [
  { title: '图谱创作', desc: '中心主题 · 分支梳理 · 文档沉淀' },
  { title: '任务管理', desc: '四象限 · 时间线 · 日历多视图' },
  { title: 'Wiki 知识库', desc: '双链笔记 · 关系图谱 · 版本历史' },
  { title: '专注与习惯', desc: '番茄钟 · 沉浸专注 · 习惯打卡' },
]
</script>

<style scoped>
.brand-panel {
  position: relative;
  flex: 1.1;
  display: flex;
  align-items: center;
  padding: 64px;
  background: linear-gradient(145deg, #4f6ef7 0%, #3f5be0 45%, #2f3fa8 100%);
  overflow: hidden;
  color: #fff;
}
.brand-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.45;
  pointer-events: none;
}
.blob-1 {
  width: 480px;
  height: 480px;
  right: -140px;
  top: -120px;
  background: #8fa3ff;
  animation: drift 14s ease-in-out infinite alternate;
}
.blob-2 {
  width: 380px;
  height: 380px;
  left: -120px;
  bottom: -140px;
  background: #6ee7d8;
  opacity: 0.25;
  animation: drift 18s ease-in-out infinite alternate-reverse;
}
@keyframes drift {
  from { transform: translate(0, 0) scale(1); }
  to { transform: translate(40px, 30px) scale(1.12); }
}

.brand-content {
  position: relative;
  z-index: 1;
  max-width: 460px;
  animation: rise 0.6s ease both;
}

.brand-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 72px;
}
.logo-mark {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  font-weight: 800;
  color: #fff;
  background: linear-gradient(135deg, #6b85f8, #4f6ef7);
  box-shadow: 0 6px 16px rgba(38, 58, 150, 0.35);
}
.logo-text {
  font-size: 20px;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.brand-hero h1 {
  font-size: 40px;
  line-height: 1.25;
  font-weight: 800;
  margin-bottom: 16px;
  letter-spacing: 1px;
}
.brand-hero p {
  font-size: 15px;
  line-height: 1.9;
  opacity: 0.82;
}

.brand-features {
  list-style: none;
  margin-top: 56px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px 28px;
}
.brand-features li {
  display: flex;
  gap: 10px;
  align-items: flex-start;
}
.feature-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #6ee7d8;
  margin-top: 7px;
  flex-shrink: 0;
  box-shadow: 0 0 0 4px rgba(110, 231, 216, 0.18);
}
.brand-features strong {
  display: block;
  font-size: 14px;
  margin-bottom: 3px;
}
.brand-features span {
  font-size: 12px;
  opacity: 0.72;
}

@keyframes rise {
  from { opacity: 0; transform: translateY(14px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 900px) {
  .brand-panel {
    display: none;
  }
}
</style>
