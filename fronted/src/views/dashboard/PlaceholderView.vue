<script setup>
import { Document } from '@element-plus/icons-vue'
</script>

<template>
  <div class="empty-state">
    <el-icon :size="44"><Document /></el-icon>
    <p>{{ $route.meta.title }}页面正在建设中</p>
  </div>
</template>
