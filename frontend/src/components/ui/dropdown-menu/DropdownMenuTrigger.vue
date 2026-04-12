<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { DropdownMenuTriggerProps } from "reka-ui"
import { DropdownMenuTrigger, useForwardProps } from "reka-ui"

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<DropdownMenuTriggerProps>()

// 变量作用：变量 forwardedProps，用于 forwardedProps 相关配置或状态。
const forwardedProps = useForwardProps(props)
</script>

<template>
  <DropdownMenuTrigger class="outline-none" v-bind="forwardedProps">
    <slot />
  </DropdownMenuTrigger>
</template>
