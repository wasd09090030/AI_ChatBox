<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { AlertDialogCancelProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { AlertDialogCancel } from "reka-ui"
import { cn } from "@/lib/utils"
import { buttonVariants } from '@/components/ui/button'

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<AlertDialogCancelProps & { class?: HTMLAttributes["class"] }>()

// 变量作用：变量 delegatedProps，用于 delegatedProps 相关配置或状态。
const delegatedProps = reactiveOmit(props, "class")
</script>

<template>
  <AlertDialogCancel
    v-bind="delegatedProps"
    :class="cn(
      buttonVariants({ variant: 'outline' }),
      'mt-2 sm:mt-0',
      props.class,
    )"
  >
    <slot />
  </AlertDialogCancel>
</template>
