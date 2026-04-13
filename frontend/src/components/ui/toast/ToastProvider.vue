<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { ToastProviderProps } from "reka-ui"
import { ToastProvider } from "reka-ui"

// 组件输入参数。
const props = defineProps<ToastProviderProps>()
</script>

<template>
  <ToastProvider v-bind="props">
    <slot />
  </ToastProvider>
</template>
