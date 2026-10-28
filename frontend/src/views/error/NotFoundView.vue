<template>
  <ErrorPage
    code="404"
    title="页面不存在"
    desc="你访问的页面可能已被移除、更名，<br />或输入的地址有误。"
  />
</template>

<script setup>
import ErrorPage from './ErrorPage.vue'
</script>
