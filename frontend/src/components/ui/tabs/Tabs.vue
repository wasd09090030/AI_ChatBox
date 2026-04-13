<script setup lang="ts">
// 文件说明：前端可复用界面组件。
import type { TabsRootEmits, TabsRootProps } from "reka-ui"
import { TabsRoot, useForwardPropsEmits } from "reka-ui"

// 组件输入参数。
const props = defineProps<TabsRootProps>()
// 组件事件声明。
const emits = defineEmits<TabsRootEmits>()

// 透传到基础组件的参数与事件。
const forwarded = useForwardPropsEmits(props, emits)
</script>

<template>
  <TabsRoot v-bind="forwarded">
    <slot />
  </TabsRoot>
</template>
