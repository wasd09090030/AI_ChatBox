<script setup lang="ts">
const props = withDefaults(defineProps<{
  title: string
  description?: string
  loading?: boolean
  hasData?: boolean
  heightClass?: string
  emptyText?: string
}>(), {
  description: '',
  loading: false,
  hasData: false,
  heightClass: 'h-[240px]',
  emptyText: '暂无数据',
})
</script>

<template>
  <section class="rounded-2xl border border-border bg-card/80 p-4 shadow-sm shadow-black/5">
    <div class="mb-3 flex items-start justify-between gap-3">
      <div class="space-y-1">
        <h3 class="text-sm font-semibold text-foreground">{{ props.title }}</h3>
        <p v-if="props.description" class="text-xs leading-5 text-muted-foreground">{{ props.description }}</p>
      </div>
      <slot name="meta" />
    </div>

    <div v-if="props.loading" :class="['flex items-center justify-center text-xs text-muted-foreground', props.heightClass]">
      加载中…
    </div>
    <div v-else-if="!props.hasData" :class="['flex items-center justify-center text-xs text-muted-foreground', props.heightClass]">
      {{ props.emptyText }}
    </div>
    <div v-else>
      <slot />
    </div>
  </section>
</template>
