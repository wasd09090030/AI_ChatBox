<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { DropdownMenuGroupProps } from "reka-ui"
import { DropdownMenuGroup } from "reka-ui"

// 组件输入参数。
const props = defineProps<DropdownMenuGroupProps>()
</script>

<template>
  <DropdownMenuGroup v-bind="props">
    <slot />
  </DropdownMenuGroup>
</template>
