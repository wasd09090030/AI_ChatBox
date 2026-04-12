<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { SelectRootEmits, SelectRootProps } from "reka-ui"
import { SelectRoot, useForwardPropsEmits } from "reka-ui"

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<SelectRootProps>()
// 变量作用：变量 emits，用于 emits 相关配置或状态。
const emits = defineEmits<SelectRootEmits>()

// 变量作用：变量 forwarded，用于 forwarded 相关配置或状态。
const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <SelectRoot v-bind="forwarded">
    <slot />
  </SelectRoot>
</template>
