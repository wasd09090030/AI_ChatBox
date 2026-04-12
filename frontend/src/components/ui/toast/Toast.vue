<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { ToastRootEmits } from "reka-ui"
import type { ToastProps } from "."
import { reactiveOmit } from "@vueuse/core"
import { ToastRoot, useForwardPropsEmits } from "reka-ui"
import { cn } from "@/lib/utils"
import { toastVariants } from "."

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<ToastProps>()

// 变量作用：变量 emits，用于 emits 相关配置或状态。
const emits = defineEmits<ToastRootEmits>()

// 变量作用：变量 delegatedProps，用于 delegatedProps 相关配置或状态。
const delegatedProps = reactiveOmit(props, "class")

// 变量作用：变量 forwarded，用于 forwarded 相关配置或状态。
const forwarded = useForwardPropsEmits(delegatedProps, emits)
</script>

<template>
  <ToastRoot
    v-bind="forwarded"
    :class="cn(toastVariants({ variant }), props.class)"
    @update:open="onOpenChange"
  >
    <slot />
  </ToastRoot>
</template>
