import { computed, ref, watch } from 'vue'
import { useQueryClient } from '@tanstack/vue-query'
import { useToast } from '@/components/ui/toast'
import { LOREBOOK_KEYS, useWorldsQuery } from '@/domains/lorebook/queries/useLorebookQueries'
import { lorebookManagementApi } from '@/domains/lorebook/api/lorebookManagementApi'
import type { World, WorldCreate } from '@/services/lorebookService'

export function useLorebookWorldManagement() {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const { data: worlds, isLoading: worldsLoading } = useWorldsQuery()

  const selectedWorldId = ref('')
  const worldDialogOpen = ref(false)
  const editingWorld = ref<World | null>(null)

  const selectedWorld = computed(() => {
    return worlds.value?.find((world) => world.id === selectedWorldId.value) ?? null
  })

  watch(worlds, (list) => {
    if (list?.length && !selectedWorldId.value) {
      selectedWorldId.value = list[0]?.id ?? ''
    }
  }, { immediate: true })

  function openNewWorld() {
    editingWorld.value = null
    worldDialogOpen.value = true
  }

  function openEditWorld(world: World) {
    editingWorld.value = world
    worldDialogOpen.value = true
  }

  async function saveWorld(payload: WorldCreate) {
    try {
      const savedWorld = editingWorld.value
        ? await lorebookManagementApi.updateWorld(editingWorld.value.id, payload)
        : await lorebookManagementApi.createWorld(payload)
      await queryClient.invalidateQueries({ queryKey: LOREBOOK_KEYS.worlds })
      if (!editingWorld.value) {
        selectedWorldId.value = savedWorld.id
      }
      worldDialogOpen.value = false
      toast({ title: editingWorld.value ? '世界已更新' : '世界已创建' })
    } catch {
      toast({ title: '保存失败', variant: 'destructive' })
    }
  }

  async function deleteWorld(world: World) {
    try {
      await lorebookManagementApi.deleteWorld(world.id)
      await queryClient.invalidateQueries({ queryKey: LOREBOOK_KEYS.worlds })
      if (selectedWorldId.value === world.id) {
        selectedWorldId.value = worlds.value?.find((item) => item.id !== world.id)?.id ?? ''
      }
      toast({ title: '已删除', description: `"${world.name}" 已删除` })
    } catch {
      toast({ title: '删除失败', variant: 'destructive' })
    }
  }

  return {
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
  }
}