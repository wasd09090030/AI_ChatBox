<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { ToastTitleProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { ToastTitle } from "reka-ui"
import { cn } from "@/lib/utils"

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<ToastTitleProps & { class?: HTMLAttributes["class"] }>()

// 变量作用：变量 delegatedProps，用于 delegatedProps 相关配置或状态。
const delegatedProps = reactiveOmit(props, "class")
</script>

<template>
  <ToastTitle v-bind="delegatedProps" :class="cn('text-sm font-semibold [&+div]:text-xs', props.class)">
    <slot />
  </ToastTitle>
</template>
