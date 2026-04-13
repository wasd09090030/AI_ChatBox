<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { AlertDialogActionProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { AlertDialogAction } from "reka-ui"
import { cn } from "@/lib/utils"
import { buttonVariants } from '@/components/ui/button'

// 组件输入参数。
const props = defineProps<AlertDialogActionProps & { class?: HTMLAttributes["class"] }>()

// 去除扩展字段后的透传参数。
const delegatedProps = reactiveOmit(props, "class")
</script>

<template>
  <AlertDialogAction v-bind="delegatedProps" :class="cn(buttonVariants(), props.class)">
    <slot />
  </AlertDialogAction>
</template>
