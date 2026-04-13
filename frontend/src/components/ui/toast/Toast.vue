<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { ToastRootEmits } from "reka-ui"
import type { ToastProps } from "."
import { reactiveOmit } from "@vueuse/core"
import { ToastRoot, useForwardPropsEmits } from "reka-ui"
import { cn } from "@/lib/utils"
import { toastVariants } from "."

// 组件输入参数。
const props = defineProps<ToastProps>()

// 组件事件声明。
const emits = defineEmits<ToastRootEmits>()

// 去除扩展字段后的透传参数。
const delegatedProps = reactiveOmit(props, "class")

// 透传到基础组件的参数与事件。
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
