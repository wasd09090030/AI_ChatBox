<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { TabsContentProps } from "reka-ui"
import type { HTMLAttributes } from "vue"
import { reactiveOmit } from "@vueuse/core"
import { TabsContent } from "reka-ui"
import { cn } from "@/lib/utils"

// 变量作用：变量 props，用于 props 相关配置或状态。
const props = defineProps<TabsContentProps & { class?: HTMLAttributes["class"] }>()

// 变量作用：变量 delegatedProps，用于 delegatedProps 相关配置或状态。
const delegatedProps = reactiveOmit(props, "class")
</script>

<template>
  <TabsContent
    :class="cn('mt-2 ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2', props.class)"
    v-bind="delegatedProps"
  >
    <slot />
  </TabsContent>
</template>
