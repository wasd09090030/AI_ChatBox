<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { AlertDialogDescriptionProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import {
  AlertDialogDescription,
} from "reka-ui"
import { cn } from "@/lib/utils"

// 组件输入参数。
const props = defineProps<AlertDialogDescriptionProps & { class?: HTMLAttributes["class"] }>()

// 去除扩展字段后的透传参数。
const delegatedProps = reactiveOmit(props, "class")
</script>

<template>
  <AlertDialogDescription
    v-bind="delegatedProps"
    :class="cn('text-sm text-muted-foreground', props.class)"
  >
    <slot />
  </AlertDialogDescription>
</template>
