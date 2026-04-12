<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { SelectValueProps } from "reka-ui"
import { SelectValue } from "reka-ui"

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<SelectValueProps>()
</script>

<template>
  <SelectValue v-bind="props">
    <slot />
  </SelectValue>
</template>
