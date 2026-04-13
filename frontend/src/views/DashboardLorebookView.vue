<script setup lang="ts">
// 文件说明：前端页面级视图编排。
import { computed, ref } from 'vue'
import {
  Library, Plus, Pencil, Trash2, User, MapPin, Zap,
  Upload, ChevronDown, ChevronRight,
} from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog'
import { useToast } from '@/components/ui/toast'
import PersonasTab from '@/components/characters/PersonasTab.vue'
import WorldSidebar from '@/components/lorebook/WorldSidebar.vue'
import WorldDialog from '@/components/lorebook/WorldDialog.vue'
import EntrySheet from '@/components/lorebook/EntrySheet.vue'
import BulkImportDialog from '@/components/lorebook/BulkImportDialog.vue'
import { useLorebookWorldManagement } from '@/domains/lorebook/composables/useLorebookWorldManagement'
import { useLorebookEntrySheet } from '@/domains/lorebook/composables/useLorebookEntrySheet'
import { useLorebookBulkImport } from '@/domains/lorebook/composables/useLorebookBulkImport'
import type { EntrySheetType } from '@/domains/lorebook/types'
import type { LorebookEntry } from '@/services/lorebookService'
import {
  useCreatePersonaMutation,
  useDeletePersonaMutation,
  usePersonasQuery,
  useUpdatePersonaMutation,
} from '@/domains/roleplay/queries/useRoleplayQueries'
import type { PersonaCreate, PersonaProfile } from '@/services/roleplayService'

const { toast } = useToast()

const {
  worlds,
  worldsLoading,
  selectedWorldId,
  selectedWorld,
  worldDialogOpen,
  editingWorld,
  openNewWorld,
  openEditWorld,
  saveWorld,
  deleteWorld,
} = useLorebookWorldManagement()

const {
  entries,
  entriesLoading,
  entrySheetOpen,
  entrySheetType,
  editingEntry,
  savingEntry,
  filteredByType,
  openAddSheet,
  openEditSheet,
  closeEntrySheet,
  submitEntry,
  deleteEntry,
} = useLorebookEntrySheet(selectedWorldId)

const {
  bulkImportOpen,
  importing,
  importResult,
  openBulkImport,
  closeBulkImport,
  importEntries,
} = useLorebookBulkImport(selectedWorldId)

const { data: personas, isLoading: personasLoading } = usePersonasQuery()
// createPersonaMut 相关状态。
const createPersonaMut = useCreatePersonaMutation()
// updatePersonaMut 相关状态。
const updatePersonaMut = useUpdatePersonaMutation()
// deletePersonaMut 相关状态。
const deletePersonaMut = useDeletePersonaMutation()

// expandedIds 相关状态。
const expandedIds = ref<Set<string>>(new Set())
// activeTab 相关状态。
const activeTab = ref<'principal' | EntrySheetType | 'persona'>('principal')
// defaultCharacterRoleTier 相关状态。
const defaultCharacterRoleTier = ref<'npc' | 'principal'>('npc')

/** 处理 toggleExpand 相关逻辑。 */
function toggleExpand(id: string) {
  if (expandedIds.value.has(id)) expandedIds.value.delete(id)
  else expandedIds.value.add(id)
}

const ENTRY_ICONS: Record<EntrySheetType, typeof User> = {
  character: User,
  location: MapPin,
  event: Zap,
}
const ENTRY_LABELS: Record<EntrySheetType, string> = {
  character: '角色',
  location: '地点',
  event: '事件',
}

/** 处理 isPrincipalCharacter 相关逻辑。 */
function isPrincipalCharacter(entry: LorebookEntry): boolean {
  return entry.type === 'character' && entry.metadata?.role_tier === 'principal'
}

/** 处理 isDialogueEnabled 相关逻辑。 */
function isDialogueEnabled(entry: LorebookEntry): boolean {
  return entry.type === 'character' && entry.metadata?.dialogue_enabled === true
}

// principalCharacters 相关状态。
const principalCharacters = computed(() =>
  filteredByType('character').filter((entry) => isPrincipalCharacter(entry as LorebookEntry)),
)

// npcCharacters 相关状态。
const npcCharacters = computed(() =>
  filteredByType('character').filter((entry) => !isPrincipalCharacter(entry as LorebookEntry)),
)

/** 处理 openAddCharacterSheet 相关逻辑。 */
function openAddCharacterSheet() {
  defaultCharacterRoleTier.value = 'npc'
  openAddSheet('character')
}

/** 处理 openAddPrincipalSheet 相关逻辑。 */
function openAddPrincipalSheet() {
  defaultCharacterRoleTier.value = 'principal'
  openAddSheet('character')
}

interface PersonaForm {
  name: string
  description: string
  title: string
  traits: string[]
  metadata: Record<string, unknown>
}

// showPersonaDialog 相关状态。
const showPersonaDialog = ref(false)
// editingPersona 相关状态。
const editingPersona = ref<PersonaProfile | null>(null)
// newTrait 相关状态。
const newTrait = ref('')
// personaSaving 相关状态。
const personaSaving = ref(false)
// personaForm 相关状态。
const personaForm = ref<PersonaForm>({
  name: '',
  description: '',
  title: '',
  traits: [],
  metadata: {},
})

/** 处理 openNewPersona 相关逻辑。 */
function openNewPersona() {
  editingPersona.value = null
  personaForm.value = { name: '', description: '', title: '', traits: [], metadata: {} }
  newTrait.value = ''
  showPersonaDialog.value = true
}

/** 处理 openEditPersona 相关逻辑。 */
function openEditPersona(persona: PersonaProfile) {
  editingPersona.value = persona
  personaForm.value = {
    name: persona.name,
    description: persona.description,
    title: persona.title ?? '',
    traits: [...persona.traits],
    metadata: { ...persona.metadata },
  }
  newTrait.value = ''
  showPersonaDialog.value = true
}

/** 处理 addTrait 相关逻辑。 */
function addTrait() {
  const trait = newTrait.value.trim()
  if (trait && !personaForm.value.traits.includes(trait)) {
    personaForm.value.traits.push(trait)
  }
  newTrait.value = ''
}

/** 处理 removeTrait 相关逻辑。 */
function removeTrait(trait: string) {
  personaForm.value.traits = personaForm.value.traits.filter((item) => item !== trait)
}

/** 处理 savePersona 相关逻辑。 */
async function savePersona() {
  if (!personaForm.value.name.trim()) return
  personaSaving.value = true
  try {
    const payload: PersonaCreate = {
      name: personaForm.value.name.trim(),
      description: personaForm.value.description.trim(),
      title: personaForm.value.title.trim() || null,
      traits: personaForm.value.traits,
      metadata: personaForm.value.metadata,
    }
    if (editingPersona.value) {
      await updatePersonaMut.mutateAsync({ id: editingPersona.value.id, data: payload })
      toast({ title: '人设已更新' })
    } else {
      await createPersonaMut.mutateAsync(payload)
      toast({ title: '人设已创建' })
    }
    showPersonaDialog.value = false
  } catch {
    toast({ title: '保存失败', variant: 'destructive' })
  } finally {
    personaSaving.value = false
  }
}

/** 处理 deletePersona 相关逻辑。 */
async function deletePersona(persona: PersonaProfile) {
  try {
    await deletePersonaMut.mutateAsync(persona.id)
    toast({ title: '已删除', description: `"${persona.name}" 已删除` })
  } catch {
    toast({ title: '删除失败', variant: 'destructive' })
  }
}
</script>

<template>
  <div class="flex h-full bg-background">
    <!-- Left Sidebar -->
    <WorldSidebar
      :worlds="worlds"
      :loading="worldsLoading"
      :selected-id="selectedWorldId"
      @select="selectedWorldId = $event"
      @add="openNewWorld"
      @edit="openEditWorld"
      @delete="deleteWorld"
    />

    <!-- Right Content -->
    <div class="flex-1 flex flex-col min-w-0 overflow-hidden">
      <!-- Header -->
      <header class="h-12 flex items-center justify-between px-5 border-b border-border shrink-0">
        <div class="flex items-center gap-2 min-w-0">
          <Library class="h-4 w-4 text-muted-foreground shrink-0" />
          <span class="font-medium text-sm truncate">
            {{ selectedWorld?.name ?? 'Lorebook' }}
          </span>
          <Badge v-if="selectedWorld" variant="secondary" class="text-[11px]">
            {{ entries.length }} 条
          </Badge>
        </div>
        <div v-if="selectedWorld" class="flex gap-1.5">
          <Button size="sm" variant="ghost" class="h-7 gap-1 text-xs" @click="activeTab = 'persona'">
            <User class="h-3.5 w-3.5" />主角人设
          </Button>
          <Button size="sm" variant="ghost" class="h-7 gap-1 text-xs" @click="openBulkImport">
            <Upload class="h-3.5 w-3.5" />批量导入
          </Button>
          <Separator orientation="vertical" class="h-5 self-center" />
          <Button size="sm" variant="outline" class="h-7 gap-1 text-xs" @click="openAddPrincipalSheet">
            <User class="h-3.5 w-3.5" />关键角色
          </Button>
          <Button size="sm" variant="outline" class="h-7 gap-1 text-xs" @click="openAddCharacterSheet">
            <User class="h-3.5 w-3.5" />角色
          </Button>
          <Button size="sm" variant="outline" class="h-7 gap-1 text-xs" @click="openAddSheet('location')">
            <MapPin class="h-3.5 w-3.5" />地点
          </Button>
          <Button size="sm" variant="outline" class="h-7 gap-1 text-xs" @click="openAddSheet('event')">
            <Zap class="h-3.5 w-3.5" />事件
          </Button>
        </div>
      </header>

      <!-- World summary bar -->
      <div v-if="selectedWorld" class="px-5 py-2.5 border-b border-border bg-muted/20 shrink-0">
        <p class="text-xs text-muted-foreground line-clamp-1">
          <span v-if="selectedWorld.genre" class="mr-3">
            <span class="font-medium text-foreground">类型：</span>{{ selectedWorld.genre }}
          </span>
          <span v-if="selectedWorld.narrative_tone" class="mr-3">
            <span class="font-medium text-foreground">叙事基调：</span>{{ selectedWorld.narrative_tone }}
          </span>
          <span v-if="!selectedWorld.genre && !selectedWorld.narrative_tone" class="italic">
            {{ selectedWorld.description || '（无描述）' }}
          </span>
        </p>
        <div v-if="selectedWorld.style_tags?.length" class="flex flex-wrap gap-1 mt-1">
          <Badge
            v-for="tag in selectedWorld.style_tags"
            :key="tag"
            variant="secondary"
            class="text-[11px]"
          >
            {{ tag }}
          </Badge>
        </div>
      </div>

      <!-- Empty state -->
      <div
        v-if="!selectedWorld"
        class="flex-1 flex items-center justify-center text-center text-muted-foreground"
      >
        <div>
          <Library class="h-12 w-12 mx-auto mb-3 opacity-20" />
          <p class="text-sm">请先选择或创建一个世界</p>
        </div>
      </div>

      <!-- Tabs -->
      <div v-else class="flex-1 overflow-hidden">
        <Tabs v-model="activeTab" class="h-full flex flex-col">
          <div class="px-5 pt-3 border-b border-border shrink-0">
            <TabsList class="h-8">
              <TabsTrigger value="principal" class="text-xs h-7 gap-1.5">
                <User class="h-3.5 w-3.5" />
                关键角色 ({{ principalCharacters.length }})
              </TabsTrigger>
              <TabsTrigger
                v-for="type in ['character', 'location', 'event'] as EntrySheetType[]"
                :key="type"
                :value="type"
                class="text-xs h-7 gap-1.5"
              >
                <component :is="ENTRY_ICONS[type]" class="h-3.5 w-3.5" />
                {{ ENTRY_LABELS[type] }} ({{ type === 'character' ? npcCharacters.length : filteredByType(type).length }})
              </TabsTrigger>
              <TabsTrigger value="persona" class="text-xs h-7 gap-1.5">
                <User class="h-3.5 w-3.5" />
                主角人设 ({{ personas?.length ?? 0 }})
              </TabsTrigger>
            </TabsList>
          </div>

          <TabsContent value="principal" class="flex-1 overflow-y-auto p-4 m-0 space-y-4">
            <div class="rounded-xl border border-amber-200/80 bg-amber-50/60 p-4">
              <div class="flex items-start justify-between gap-4">
                <div>
                  <p class="text-sm font-medium text-amber-950">关键角色</p>
                  <p class="mt-1 text-xs text-amber-900/80">关键角色服务于故事创作中的重点对白、关系推进和情节触发。普通 NPC 保留在“角色”标签中。</p>
                </div>
                <Button size="sm" class="h-8 text-xs" @click="openAddPrincipalSheet">
                  <Plus class="h-3.5 w-3.5 mr-1" />添加关键角色
                </Button>
              </div>
            </div>

            <div v-if="entriesLoading" class="py-8 text-center text-sm text-muted-foreground">加载中…</div>
            <div v-else-if="!principalCharacters.length" class="py-16 text-center text-muted-foreground border border-dashed border-border rounded-xl">
              <User class="h-10 w-10 mx-auto mb-3 opacity-20" />
              <p class="text-sm">当前世界暂无关键角色</p>
              <Button size="sm" variant="ghost" class="mt-3 gap-1.5" @click="openAddPrincipalSheet">
                <Plus class="h-3.5 w-3.5" /> 添加关键角色
              </Button>
            </div>
            <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              <div
                v-for="entry in principalCharacters"
                :key="entry.id ?? entry.name"
                class="border border-amber-200/80 rounded-xl p-3.5 space-y-2 bg-amber-50/40 hover:bg-amber-50/70 transition-colors group"
              >
                <div class="flex items-start justify-between gap-2">
                  <div class="min-w-0">
                    <div class="flex items-center gap-1.5">
                      <User class="h-3.5 w-3.5 text-amber-700 shrink-0" />
                      <p class="font-medium text-sm truncate">{{ entry.name }}</p>
                    </div>
                    <div class="mt-2 flex flex-wrap gap-1">
                      <Badge variant="secondary" class="text-[10px] text-amber-700">关键角色</Badge>
                      <Badge v-if="isDialogueEnabled(entry)" variant="secondary" class="text-[10px] text-sky-700">对话特化</Badge>
                    </div>
                  </div>
                  <div class="flex gap-0.5 opacity-0 group-hover:opacity-100 shrink-0">
                    <Button size="icon" variant="ghost" class="h-6 w-6 text-muted-foreground hover:text-foreground" @click="openEditSheet(entry)">
                      <Pencil class="h-3 w-3" />
                    </Button>
                    <AlertDialog>
                      <AlertDialogTrigger as-child>
                        <Button size="icon" variant="ghost" class="h-6 w-6 text-muted-foreground hover:text-destructive">
                          <Trash2 class="h-3 w-3" />
                        </Button>
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>删除关键角色</AlertDialogTitle>
                          <AlertDialogDescription>确定要删除 "{{ entry.name }}"？</AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>取消</AlertDialogCancel>
                          <AlertDialogAction variant="destructive" @click="deleteEntry(entry)">删除</AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </div>
                </div>
                <p class="text-xs text-muted-foreground leading-relaxed whitespace-pre-line line-clamp-4">{{ entry.description || '（无描述）' }}</p>
                <div v-if="entry.metadata?.story_function || entry.metadata?.opening_line" class="space-y-1 rounded-md border border-amber-200/70 bg-white/70 p-2">
                  <p v-if="entry.metadata?.story_function" class="text-[11px] text-foreground"><span class="font-medium">剧情功能：</span>{{ entry.metadata.story_function }}</p>
                  <p v-if="entry.metadata?.opening_line" class="text-[11px] text-muted-foreground"><span class="font-medium text-foreground">开场白：</span>{{ entry.metadata.opening_line }}</p>
                </div>
              </div>
            </div>
          </TabsContent>

          <template v-for="type in ['character', 'location', 'event'] as EntrySheetType[]" :key="type">
            <TabsContent :value="type" class="flex-1 overflow-y-auto p-4 m-0">
              <div v-if="entriesLoading" class="py-8 text-center text-sm text-muted-foreground">
                加载中…
              </div>

              <div
                v-else-if="!(type === 'character' ? npcCharacters.length : filteredByType(type).length)"
                class="py-16 text-center text-muted-foreground border border-dashed border-border rounded-xl"
              >
                <component :is="ENTRY_ICONS[type]" class="h-10 w-10 mx-auto mb-3 opacity-20" />
                <p class="text-sm">暂无 {{ ENTRY_LABELS[type] }} 条目</p>
                <Button size="sm" variant="ghost" class="mt-3 gap-1.5" @click="type === 'character' ? openAddCharacterSheet() : openAddSheet(type)">
                  <Plus class="h-3.5 w-3.5" /> 添加{{ ENTRY_LABELS[type] }}
                </Button>
              </div>

              <!-- Entry Cards -->
              <div v-else class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                <div
                  v-for="entry in (type === 'character' ? npcCharacters : filteredByType(type))"
                  :key="entry.id ?? entry.name"
                  class="border border-border rounded-xl p-3.5 space-y-2 hover:bg-muted/30 transition-colors group"
                >
                  <!-- Card header -->
                  <div class="flex items-start justify-between gap-2">
                    <div class="flex items-center gap-1.5 min-w-0">
                      <component :is="ENTRY_ICONS[type]" class="h-3.5 w-3.5 text-muted-foreground shrink-0" />
                      <p class="font-medium text-sm truncate">{{ entry.name }}</p>
                    </div>
                    <div class="flex gap-0.5 opacity-0 group-hover:opacity-100 shrink-0">
                      <!-- Edit -->
                      <Button
                        size="icon"
                        variant="ghost"
                        class="h-6 w-6 text-muted-foreground hover:text-foreground"
                        @click="openEditSheet(entry)"
                      >
                        <Pencil class="h-3 w-3" />
                      </Button>
                      <!-- Delete -->
                      <AlertDialog>
                        <AlertDialogTrigger as-child>
                          <Button
                            size="icon"
                            variant="ghost"
                            class="h-6 w-6 text-muted-foreground hover:text-destructive"
                          >
                            <Trash2 class="h-3 w-3" />
                          </Button>
                        </AlertDialogTrigger>
                        <AlertDialogContent>
                          <AlertDialogHeader>
                            <AlertDialogTitle>删除条目</AlertDialogTitle>
                            <AlertDialogDescription>
                              确定要删除 "{{ entry.name }}"？
                            </AlertDialogDescription>
                          </AlertDialogHeader>
                          <AlertDialogFooter>
                            <AlertDialogCancel>取消</AlertDialogCancel>
                            <AlertDialogAction variant="destructive" @click="deleteEntry(entry)">
                              删除
                            </AlertDialogAction>
                          </AlertDialogFooter>
                        </AlertDialogContent>
                      </AlertDialog>
                    </div>
                  </div>

                  <div v-if="type === 'character'" class="flex flex-wrap gap-1">
                    <Badge v-if="isPrincipalCharacter(entry)" variant="secondary" class="text-[10px] text-amber-700">
                      关键角色
                    </Badge>
                    <Badge v-if="isDialogueEnabled(entry)" variant="secondary" class="text-[10px] text-sky-700">
                      对话特化
                    </Badge>
                  </div>

                  <!-- Description - expandable -->
                  <div>
                    <p
                      class="text-xs text-muted-foreground leading-relaxed whitespace-pre-line"
                      :class="expandedIds.has(entry.id ?? entry.name) ? '' : 'line-clamp-3'"
                    >
                      {{ entry.description || '（无描述）' }}
                    </p>
                    <button
                      v-if="(entry.description ?? '').length > 120"
                      class="mt-1 flex items-center gap-0.5 text-[11px] text-muted-foreground hover:text-foreground transition-colors"
                      @click.stop="toggleExpand(entry.id ?? entry.name)"
                    >
                      <component
                        :is="expandedIds.has(entry.id ?? entry.name) ? ChevronDown : ChevronRight"
                        class="h-3 w-3"
                      />
                      {{ expandedIds.has(entry.id ?? entry.name) ? '收起' : '展开详情' }}
                    </button>
                  </div>

                  <!-- Keywords -->
                  <div v-if="entry.keywords?.length" class="flex flex-wrap gap-1">
                    <Badge
                      v-for="kw in entry.keywords.slice(0, 4)"
                      :key="kw"
                      variant="outline"
                      class="text-[10px] px-1.5 py-0"
                    >
                      {{ kw }}
                    </Badge>
                    <span
                      v-if="entry.keywords.length > 4"
                      class="text-[10px] text-muted-foreground self-center"
                    >
                      +{{ entry.keywords.length - 4 }}
                    </span>
                  </div>
                </div>
              </div>
            </TabsContent>
          </template>

          <TabsContent value="persona" class="flex-1 overflow-y-auto p-4 m-0">
            <div class="rounded-xl border border-border bg-muted/10 p-4">
              <p class="text-sm font-medium text-foreground">主角人设</p>
              <p class="mt-1 text-xs text-muted-foreground">主角人设是全局资源，不绑定单个世界；故事创作页中的主角人设选择直接读取这里的数据。</p>
            </div>
            <div class="mt-4">
              <PersonasTab
                :personas="personas"
                :personas-loading="personasLoading"
                @new-persona="openNewPersona"
                @edit-persona="openEditPersona"
                @delete-persona="deletePersona"
              />
            </div>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  </div>

  <!-- World Dialog -->
  <WorldDialog
    v-model:open="worldDialogOpen"
    :editing="editingWorld"
    @save="saveWorld"
  />

  <!-- Entry Add / Edit Sheet -->
  <EntrySheet
    v-model:open="entrySheetOpen"
    :type="entrySheetType"
    :editing="editingEntry"
    :world-id="selectedWorldId"
    :saving="savingEntry"
    :default-character-role-tier="defaultCharacterRoleTier"
    @submit="submitEntry"
    @update:open="(open) => { if (!open) closeEntrySheet() }"
  />

  <!-- Bulk Import Dialog -->
  <BulkImportDialog
    v-model:open="bulkImportOpen"
    :world-id="selectedWorldId"
    :importing="importing"
    :result="importResult"
    @import="importEntries"
    @update:open="(open) => { if (!open) closeBulkImport() }"
  />

  <Dialog v-model:open="showPersonaDialog">
    <DialogContent class="sm:max-w-lg">
      <DialogHeader>
        <DialogTitle>{{ editingPersona ? '编辑人设' : '新建人设' }}</DialogTitle>
      </DialogHeader>
      <div class="space-y-4 py-2">
        <div class="grid grid-cols-2 gap-4">
          <div class="space-y-2">
            <Label for="persona-name">名称 <span class="text-destructive">*</span></Label>
            <Input id="persona-name" v-model="personaForm.name" placeholder="人设名称" />
          </div>
          <div class="space-y-2">
            <Label for="persona-title">称号/职业</Label>
            <Input id="persona-title" v-model="personaForm.title" placeholder="例：神秘冒险者" />
          </div>
        </div>
        <div class="space-y-2">
          <Label for="persona-desc">描述</Label>
          <Textarea id="persona-desc" v-model="personaForm.description" placeholder="这个主角人设的核心设定…" class="min-h-[90px] resize-y text-sm" />
        </div>
        <div class="space-y-2">
          <Label>特质</Label>
          <div class="flex flex-wrap gap-1.5 mb-2">
            <Badge v-for="trait in personaForm.traits" :key="trait" variant="secondary" class="gap-1 pr-1">
              {{ trait }}
              <button class="hover:text-foreground ml-0.5" @click="removeTrait(trait)">
                ×
              </button>
            </Badge>
          </div>
          <div class="flex gap-2">
            <Input v-model="newTrait" placeholder="添加特质…" class="h-8 text-sm" @keydown.enter.prevent="addTrait" />
            <Button size="sm" variant="outline" @click="addTrait">添加</Button>
          </div>
        </div>
      </div>
      <DialogFooter>
        <Button variant="outline" @click="showPersonaDialog = false">取消</Button>
        <Button :disabled="!personaForm.name.trim() || personaSaving" @click="savePersona">
          {{ personaSaving ? '保存中…' : '保存' }}
        </Button>
      </DialogFooter>
    </DialogContent>
  </Dialog>
</template>
