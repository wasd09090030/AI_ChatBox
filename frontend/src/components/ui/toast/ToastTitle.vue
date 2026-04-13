<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { ToastTitleProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { ToastTitle } from "reka-ui"
import { cn } from "@/lib/utils"

// 组件输入参数。
const props = defineProps<ToastTitleProps & { class?: HTMLAttributes["class"] }>()

// 去除扩展字段后的透传参数。
const delegatedProps = reactiveOmit(props, "class")
</script>

<template>
  <ToastTitle v-bind="delegatedProps" :class="cn('text-sm font-semibold [&+div]:text-xs', props.class)">
    <slot />
  </ToastTitle>
</template>
