<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { ToastDescriptionProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { ToastDescription } from "reka-ui"
import { cn } from "@/lib/utils"

// 组件输入参数。
const props = defineProps<ToastDescriptionProps & { class?: HTMLAttributes["class"] }>()

// 去除扩展字段后的透传参数。
const delegatedProps = reactiveOmit(props, "class")
</script>

<template>
  <ToastDescription :class="cn('text-sm opacity-90', props.class)" v-bind="delegatedProps">
    <slot />
  </ToastDescription>
</template>
