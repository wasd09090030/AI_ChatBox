<script setup lang="ts">
import { Settings } from 'lucide-vue-next'
</script>

<template>
  <div>
    <h1 class="flex items-center gap-2 text-xl font-semibold">
      <Settings class="h-5 w-5 text-muted-foreground" />
      配置
    </h1>
    <p class="mt-1 text-sm text-muted-foreground">管理 API Key、提供商与生成参数</p>
  </div>
</template>
