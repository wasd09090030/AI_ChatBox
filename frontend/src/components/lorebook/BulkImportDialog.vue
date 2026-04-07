<script setup lang="ts">
/**
 * BulkImportDialog — Accept JSON input and batch-import lorebook entries.
 *
 * Expected JSON format (array of objects):
 * [
 *   { "entry_type": "character", "data": { "name": "艾莉亚", "age": 22, ... } },
 *   { "entry_type": "location",  "data": { "name": "迷雾森林", "description": "..." } },
 *   { "entry_type": "event",     "data": { "name": "暗影降临", "description": "..." } }
 * ]
 */
import { ref, computed } from 'vue'
import { Upload, CheckCircle2, XCircle } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import type { BulkImportEntry } from '@/services/lorebookService'
import type { BulkImportResult } from '@/domains/lorebook/types'

const EXAMPLE_JSON = `[
  {
    "entry_type": "character",
    "data": {
      "name": "艾莉亚",
      "age": 22,
      "gender": "女",
      "appearance": "银色长发，翠绿色眼睛",
      "personality": "勇敢、善良",
      "background": "来自北方王国的年轻冒险者",
      "speaking_style": "直率和善，少用修辞"
    }
  },
  {
    "entry_type": "location",
    "data": {
      "name": "迷雾森林",
      "description": "充满神秘气息的古老森林，阳光难以透出",
      "region": "北方边境",
      "climate": "温带湿润",
      "mood": "神秘、岁月沉沉"
    }
  },
  {
    "entry_type": "event",
    "data": {
      "name": "暗影降临",
      "description": "三个月前，森林深处突然出现黑雾，村民目击怪物出没",
      "time": "当前多有三个月前",
      "location": "迷雾森林深处",
      "importance": 3
    }
  }
]`

const props = defineProps<{
  open: boolean
  worldId: string
  importing: boolean
  result: BulkImportResult | null
}>()

const emit = defineEmits<{
  'update:open': [v: boolean]
  import: [entries: BulkImportEntry[]]
}>()

const jsonText = ref('')

const parseError = computed(() => {
  if (!jsonText.value.trim()) return null
  try {
    const parsed = JSON.parse(jsonText.value)
    if (!Array.isArray(parsed)) return '必须是 JSON 数组'
    for (const item of parsed) {
      if (!item.entry_type || !item.data) return '每个条目需要 entry_type 和 data 字段'
      if (!['character', 'location', 'event'].includes(item.entry_type))
        return `未知 entry_type: ${item.entry_type}（只支持 character / location / event）`
    }
    return null
  } catch (e) {
    return `JSON 解析错误: ${(e as Error).message}`
  }
})

const parsedEntries = computed<BulkImportEntry[] | null>(() => {
  if (parseError.value !== null || !jsonText.value.trim()) return null
  try {
    return JSON.parse(jsonText.value) as BulkImportEntry[]
  } catch {
    return null
  }
})

async function doImport() {
  if (!parsedEntries.value || !props.worldId) return
  emit('import', parsedEntries.value)
}

function handleClose() {
  jsonText.value = ''
  emit('update:open', false)
}

function loadExample() {
  jsonText.value = EXAMPLE_JSON
}
</script>

<template>
  <Dialog :open="open" @update:open="handleClose">
    <DialogContent class="sm:max-w-2xl max-h-[90vh] overflow-y-auto">
      <DialogHeader>
        <DialogTitle class="flex items-center gap-2">
          <Upload class="h-4 w-4" />
          批量导入 Lorebook 条目
        </DialogTitle>
        <DialogDescription>
          粘贴 JSON 数组，每个元素需包含 <code class="font-mono text-xs bg-muted px-1 rounded">entry_type</code>（character / location / event）和 <code class="font-mono text-xs bg-muted px-1 rounded">data</code> 字段。
        </DialogDescription>
      </DialogHeader>

      <div class="space-y-3 py-2">
        <!-- Textarea -->
        <Textarea
          v-model="jsonText"
          placeholder="粘贴 JSON 数组…"
          class="min-h-[220px] font-mono text-xs resize-y"
        />

        <!-- Parse hint -->
        <div v-if="parseError" class="text-xs text-destructive flex items-center gap-1">
          <XCircle class="h-3.5 w-3.5 shrink-0" />
          {{ parseError }}
        </div>
        <div
          v-else-if="parsedEntries"
          class="text-xs text-green-600 dark:text-green-400 flex items-center gap-1"
        >
          <CheckCircle2 class="h-3.5 w-3.5 shrink-0" />
          解析成功：{{ parsedEntries.length }} 条条目
        </div>

        <!-- Result summary -->
        <div v-if="props.result" class="rounded-lg border border-border p-3 space-y-2">
          <p class="text-sm font-medium">
            导入结果：
            <Badge variant="secondary" class="ml-1">成功 {{ props.result.imported }}</Badge>
            <Badge v-if="props.result.failed > 0" variant="destructive" class="ml-1">失败 {{ props.result.failed }}</Badge>
          </p>
          <ul v-if="props.result.details.failed.length" class="text-xs text-destructive space-y-0.5 list-disc pl-4">
            <li v-for="f in props.result.details.failed" :key="f.name">
              <span class="font-medium">{{ f.name }}</span>：{{ f.reason }}
            </li>
          </ul>
        </div>

        <!-- Example hint -->
        <div class="text-xs text-muted-foreground">
          <button class="underline hover:text-foreground" @click="loadExample">载入示例 JSON</button>
        </div>
      </div>

      <DialogFooter>
        <Button variant="outline" @click="handleClose">关闭</Button>
        <Button
          :disabled="!parsedEntries || props.importing"
          @click="doImport"
        >
          {{ props.importing ? '导入中…' : `导入 ${parsedEntries?.length ?? 0} 条` }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
