<template>
  <ErrorPage
    code="403"
    title="没有访问权限"
    desc="你的账号没有访问该页面的权限，<br />如需开通请联系管理员。"
  />
</template>

<script setup>
import ErrorPage from './ErrorPage.vue'
</script>
