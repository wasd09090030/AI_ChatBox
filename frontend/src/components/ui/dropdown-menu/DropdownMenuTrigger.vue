<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { DropdownMenuTriggerProps } from "reka-ui"
import { DropdownMenuTrigger, useForwardProps } from "reka-ui"

// 组件输入参数。
const props = defineProps<DropdownMenuTriggerProps>()

// 透传到基础组件的参数。
const forwardedProps = useForwardProps(props)
</script>

<template>
  <DropdownMenuTrigger class="outline-none" v-bind="forwardedProps">
    <slot />
  </DropdownMenuTrigger>
</template>
