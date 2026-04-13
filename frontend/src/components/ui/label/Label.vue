<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { LabelProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { Label } from "reka-ui"
import { cn } from "@/lib/utils"

// 组件输入参数。
const props = defineProps<LabelProps & { class?: HTMLAttributes["class"] }>()

// 去除扩展字段后的透传参数。
const delegatedProps = reactiveOmit(props, "class")
</script>

<template>
  <Label
    v-bind="delegatedProps"
    :class="
      cn(
        'text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70',
        props.class,
      )
    "
  >
    <slot />
  </Label>
</template>
