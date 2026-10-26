import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
      stream: resolve(__dirname, 'node_modules/stream-browserify'),
      events: resolve(__dirname, 'node_modules/events'),
      buffer: resolve(__dirname, 'node_modules/buffer'),
    },
  },
  define: {
    global: 'globalThis',
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8302',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://127.0.0.1:8302',
        changeOrigin: true,
      },
      // 本地文件存储的静态访问（STORAGE_BACKEND=local）
      '/uploads': {
        target: 'http://127.0.0.1:8302',
        changeOrigin: true,
      },
    },
  },
})
