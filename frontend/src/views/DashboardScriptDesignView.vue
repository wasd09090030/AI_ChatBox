<script setup lang="ts">
// 文件说明：前端页面级视图编排。
import { computed, ref, watch } from 'vue'
import type { AxiosError } from 'axios'
import { useToast } from '@/components/ui/toast'
import ScriptDesignSidebar from '@/components/script-design/ScriptDesignSidebar.vue'
import ScriptDesignSimpleOverviewForm from '@/components/script-design/ScriptDesignSimpleOverviewForm.vue'
import ScriptStructureOverviewCard from '@/components/script-design/ScriptStructureOverviewCard.vue'
import ScriptStructureDesignerDialog from '@/components/script-design/ScriptStructureDesignerDialog.vue'
import ScriptStoryBindingsPanel from '@/components/script-design/ScriptStoryBindingsPanel.vue'
import { useWorldsQuery } from '@/domains/lorebook/queries/useLorebookQueries'
import {
  useCreateScriptDesignMutation,
  useDeleteScriptDesignMutation,
  useScriptDesignBindingsQuery,
  useScriptDesignQuery,
  useScriptDesignsQuery,
  useUpdateScriptDesignMutation,
} from '@/domains/story/queries/useScriptDesignQueries'
import type {
  ForeshadowRecord,
  ScriptDesign,
  ScriptDesignUpdateInput,
  ScriptEventNode,
  ScriptStage,
} from '@/domains/story/api/scriptDesignApi'

type BeginnerTemplateKey = 'mystery' | 'adventure' | 'court'

const beginnerTemplates: Array<{
  key: BeginnerTemplateKey
  label: string
  description: string
}> = [
  { key: 'mystery', label: '悬疑模板', description: '线索递进、反转揭露、伏笔回收' },
  { key: 'adventure', label: '冒险模板', description: '目标驱动、旅途升级、终局突破' },
  { key: 'court', label: '宫廷模板', description: '权力博弈、关系试探、局势翻盘' },
]

const { toast } = useToast()
const { data: worlds, isLoading: worldsLoading } = useWorldsQuery()

// selectedWorldId 相关状态。
const selectedWorldId = ref('')
// selectedScriptDesignId 相关状态。
const selectedScriptDesignId = ref('')
// showStructureDesigner 相关状态。
const showStructureDesigner = ref(false)

watch(worlds, (list) => {
  if (list?.length && !selectedWorldId.value) {
    selectedWorldId.value = list[0]?.id ?? ''
  }
}, { immediate: true })

// selectedWorld 相关状态。
const selectedWorld = computed(() => worlds.value?.find((world) => world.id === selectedWorldId.value) ?? null)

const { data: scriptDesigns, isLoading: scriptDesignsLoading } = useScriptDesignsQuery(selectedWorldId)
const { data: currentScriptDesign, isLoading: currentScriptDesignLoading } = useScriptDesignQuery(selectedScriptDesignId)
const { data: bindingsData, isLoading: bindingsLoading } = useScriptDesignBindingsQuery(selectedScriptDesignId)

// createScriptDesignMut 相关状态。
const createScriptDesignMut = useCreateScriptDesignMutation()
// updateScriptDesignMut 相关状态。
const updateScriptDesignMut = useUpdateScriptDesignMutation()
// deleteScriptDesignMut 相关状态。
const deleteScriptDesignMut = useDeleteScriptDesignMutation()

watch(scriptDesigns, (list) => {
  if (!list?.length) {
    selectedScriptDesignId.value = ''
    return
  }
  const stillExists = list.some((item) => item.id === selectedScriptDesignId.value)
  if (!stillExists) {
    selectedScriptDesignId.value = list[0]?.id ?? ''
  }
}, { immediate: true })

/** 处理 normalizeAxiosMessage 相关逻辑。 */
function normalizeAxiosMessage(error: unknown, fallback: string): string {
  const axiosError = error as AxiosError<{ detail?: string | { message?: string; story_binding_count?: number } }>
  const detail = axiosError?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (typeof detail?.message === 'string') {
    const count = detail.story_binding_count
    return typeof count === 'number' ? `${detail.message}（${count} 个故事仍在引用）` : detail.message
  }
  return fallback
}

/** 处理 createScriptDesign 相关逻辑。 */
async function createScriptDesign() {
  if (!selectedWorldId.value) return
  try {
    const created = await createScriptDesignMut.mutateAsync({
      world_id: selectedWorldId.value,
      title: `未命名剧本 ${((scriptDesigns.value?.length ?? 0) + 1).toString()}`,
      status: 'draft',
    })
    selectedScriptDesignId.value = created.id
    toast({ title: '剧本设计已创建' })
  } catch (error) {
    toast({ title: normalizeAxiosMessage(error, '创建失败'), variant: 'destructive' })
  }
}

/** 处理 saveOverview 相关逻辑。 */
async function saveOverview(payload: ScriptDesignUpdateInput) {
  if (!selectedScriptDesignId.value) return
  try {
    await updateScriptDesignMut.mutateAsync({ id: selectedScriptDesignId.value, payload })
    toast({ title: '概览已保存' })
  } catch (error) {
    toast({ title: normalizeAxiosMessage(error, '保存失败'), variant: 'destructive' })
  }
}

/** 处理 saveSimpleStructure 相关逻辑。 */
async function saveSimpleStructure(payload: {
  stage_outlines: ScriptStage[]
  event_nodes: ScriptEventNode[]
  foreshadows: ForeshadowRecord[]
}) {
  if (!selectedScriptDesignId.value) return
  try {
    await updateScriptDesignMut.mutateAsync({
      id: selectedScriptDesignId.value,
      payload,
    })
    toast({ title: '简化结构已保存' })
  } catch (error) {
    toast({ title: normalizeAxiosMessage(error, '保存失败'), variant: 'destructive' })
  }
}

/** 处理 buildTemplatePayload 相关逻辑。 */
function buildTemplatePayload(templateKey: BeginnerTemplateKey): ScriptDesignUpdateInput {
  const stage1Id = crypto.randomUUID()
  const stage2Id = crypto.randomUUID()
  const stage3Id = crypto.randomUUID()

  if (templateKey === 'mystery') {
    const event1Id = crypto.randomUUID()
    const event2Id = crypto.randomUUID()
    const event3Id = crypto.randomUUID()
    return {
      title: '雾港疑案',
      logline: '主角为了查清港口命案，被迫卷入码头商会、巡夜队与旧贵族之间的暗战。',
      summary: '故事从一起看似普通的命案开始，主角在调查中不断发现被刻意掩埋的旧案与身份错位。随着线索推进，真正的幕后操盘者逐步浮出水面，而主角也必须在真相、同伴与代价之间作出选择。',
      theme: '真相、信任与代价',
      core_conflict: '主角想揭开真相，但每深入一步都会伤害现有同盟与秩序。',
      ending_direction: '揭露真相但失去最信任的盟友，留下苦涩收束。',
      tags: ['悬疑', '调查', '反转'],
      default_generation_policy: {
        ...(currentScriptDesign.value?.default_generation_policy ?? {
          enforce_stage_order: false,
          enforce_pending_event: false,
          enforce_foreshadow_tracking: false,
          preferred_stage_id: null,
          preferred_event_ids: [],
          writing_brief: null,
        }),
        writing_brief: '保持线索层层递进，每次推进只揭开一层真相，不要提前说破幕后身份。',
      },
      stage_outlines: [
        {
          id: stage1Id,
          title: '迷雾初现',
          order: 0,
          goal: '让主角接触案件并发现第一批异常线索。',
          tension: null,
          entry_condition: null,
          exit_condition: null,
          expected_turning_point: '发现死者与旧贵族之间的隐藏联系。',
          linked_role_ids: [],
          linked_lorebook_entry_ids: [],
          notes: null,
        },
        {
          id: stage2Id,
          title: '错位真相',
          order: 1,
          goal: '让调查对象彼此矛盾，逼主角在多方说辞中判断真假。',
          tension: null,
          entry_condition: null,
          exit_condition: null,
          expected_turning_point: '主角意识到案件背后另有目标，不只是单纯谋杀。',
          linked_role_ids: [],
          linked_lorebook_entry_ids: [],
          notes: null,
        },
        {
          id: stage3Id,
          title: '幕后现身',
          order: 2,
          goal: '推动真相揭露，并让主角承担揭露后的代价。',
          tension: null,
          entry_condition: null,
          exit_condition: null,
          expected_turning_point: '幕后操盘者被揭开，但主角失去重要同伴。',
          linked_role_ids: [],
          linked_lorebook_entry_ids: [],
          notes: null,
        },
      ],
      event_nodes: [
        {
          id: event1Id,
          stage_id: stage1Id,
          title: '码头发现第一条伪证',
          summary: '主角在案发现场附近发现一份明显被篡改的出入记录。',
          order: 0,
          status: 'pending',
          event_type: 'setup',
          trigger_condition: null,
          objective: '建立案件不简单的第一印象。',
          obstacle: '现场已经被人提前清理，线索残缺。',
          expected_outcome: '主角决定继续深挖，而不是接受表面结论。',
          failure_outcome: null,
          scene_hint: null,
          participant_role_ids: [],
          participant_lorebook_entry_ids: [],
          prerequisite_event_ids: [],
          unlocks_event_ids: [],
          foreshadow_ids: [],
          notes: null,
        },
        {
          id: event2Id,
          stage_id: stage2Id,
          title: '证词互相冲突',
          summary: '两名关键证人给出完全对立的说法，迫使主角重新判断阵营。',
          order: 0,
          status: 'pending',
          event_type: 'conflict',
          trigger_condition: null,
          objective: '让故事从单线调查转向多方博弈。',
          obstacle: '主角无法立刻分辨谁在撒谎。',
          expected_outcome: '主角找到隐藏更深的旧案切口。',
          failure_outcome: null,
          scene_hint: null,
          participant_role_ids: [],
          participant_lorebook_entry_ids: [],
          prerequisite_event_ids: [],
          unlocks_event_ids: [],
          foreshadow_ids: [],
          notes: null,
        },
        {
          id: event3Id,
          stage_id: stage3Id,
          title: '揭露幕后操盘者',
          summary: '主角在公开对峙中逼出真正的策划者，同时付出关系破裂的代价。',
          order: 0,
          status: 'pending',
          event_type: 'climax',
          trigger_condition: null,
          objective: '完成真相揭露与情感代价的双重收束。',
          obstacle: '主角缺少决定性证据，且盟友立场动摇。',
          expected_outcome: '真相公开，但主角失去关键同伴或支持。',
          failure_outcome: null,
          scene_hint: null,
          participant_role_ids: [],
          participant_lorebook_entry_ids: [],
          prerequisite_event_ids: [],
          unlocks_event_ids: [],
          foreshadow_ids: [],
          notes: null,
        },
      ],
      foreshadows: [
        {
          id: crypto.randomUUID(),
          title: '断裂怀表',
          content: '案发现场遗留的断裂怀表，指向死者与旧贵族的隐秘关系。',
          category: 'object',
          planted_stage_id: stage1Id,
          planted_event_id: null,
          expected_payoff_stage_id: stage3Id,
          expected_payoff_event_id: null,
          payoff_description: '最终证明死者身份并串起两起旧案。',
          status: 'planted',
          importance: 'high',
          notes: null,
        },
      ],
    }
  }

  if (templateKey === 'adventure') {
    return {
      title: '裂境远征',
      logline: '主角为了阻止裂境扩张，率领临时队伍踏上不断升级的危险旅程。',
      summary: '故事围绕一场目标明确但代价未知的远征展开。队伍在旅途中不断遇到新的阻碍、盟友与选择，既要面对外部危险，也要处理队伍内部的信任问题，最终在终局地点做出决定世界走向的抉择。',
      theme: '勇气、代价与成长',
      core_conflict: '主角必须不断前进，但每一次推进都会消耗队伍资源与信任。',
      ending_direction: '主角完成使命，但必须放弃最想守住的个人愿望。',
      tags: ['冒险', '远征', '成长'],
      default_generation_policy: {
        ...(currentScriptDesign.value?.default_generation_policy ?? {
          enforce_stage_order: false,
          enforce_pending_event: false,
          enforce_foreshadow_tracking: false,
          preferred_stage_id: null,
          preferred_event_ids: [],
          writing_brief: null,
        }),
        writing_brief: '突出旅途升级与队伍磨合，每个阶段都要让风险更高、选择更难。',
      },
      stage_outlines: [
        {
          id: stage1Id,
          title: '踏上征途',
          order: 0,
          goal: '建立使命与队伍，明确远征动机。',
          tension: null,
          entry_condition: null,
          exit_condition: null,
          expected_turning_point: '队伍第一次真正见识裂境威胁。',
          linked_role_ids: [],
          linked_lorebook_entry_ids: [],
          notes: null,
        },
        {
          id: stage2Id,
          title: '险境升级',
          order: 1,
          goal: '持续提高旅途风险，并让队伍产生分歧。',
          tension: null,
          entry_condition: null,
          exit_condition: null,
          expected_turning_point: '一名关键成员暴露隐藏动机。',
          linked_role_ids: [],
          linked_lorebook_entry_ids: [],
          notes: null,
        },
        {
          id: stage3Id,
          title: '终局抉择',
          order: 2,
          goal: '让主角在任务完成和个人牺牲之间二选一。',
          tension: null,
          entry_condition: null,
          exit_condition: null,
          expected_turning_point: '主角找到关闭裂境的方法，但代价极高。',
          linked_role_ids: [],
          linked_lorebook_entry_ids: [],
          notes: null,
        },
      ],
      event_nodes: [
        {
          id: crypto.randomUUID(),
          stage_id: stage1Id,
          title: '集结临时队伍',
          summary: '主角拉拢几位各怀目的的伙伴，远征正式开始。',
          order: 0,
          status: 'pending',
          event_type: 'setup',
          trigger_condition: null,
          objective: '确立队伍关系与旅途目标。',
          obstacle: '各成员立场不同，合作基础脆弱。',
          expected_outcome: '队伍达成暂时共识并出发。',
          failure_outcome: null,
          scene_hint: null,
          participant_role_ids: [],
          participant_lorebook_entry_ids: [],
          prerequisite_event_ids: [],
          unlocks_event_ids: [],
          foreshadow_ids: [],
          notes: null,
        },
        {
          id: crypto.randomUUID(),
          stage_id: stage2Id,
          title: '穿越高风险区域',
          summary: '队伍在资源、时间和信任三重压力下艰难推进。',
          order: 0,
          status: 'pending',
          event_type: 'conflict',
          trigger_condition: null,
          objective: '让旅途风险明显升级。',
          obstacle: '外部环境恶化，内部意见分裂。',
          expected_outcome: '主角被迫承担更重的领导责任。',
          failure_outcome: null,
          scene_hint: null,
          participant_role_ids: [],
          participant_lorebook_entry_ids: [],
          prerequisite_event_ids: [],
          unlocks_event_ids: [],
          foreshadow_ids: [],
          notes: null,
        },
        {
          id: crypto.randomUUID(),
          stage_id: stage3Id,
          title: '关闭裂境核心',
          summary: '主角在终点面对唯一的胜利方案和无法避免的牺牲。',
          order: 0,
          status: 'pending',
          event_type: 'climax',
          trigger_condition: null,
          objective: '完成任务并完成成长收束。',
          obstacle: '必须放弃一部分私人愿望或关系。',
          expected_outcome: '裂境关闭，但主角的人生被永久改变。',
          failure_outcome: null,
          scene_hint: null,
          participant_role_ids: [],
          participant_lorebook_entry_ids: [],
          prerequisite_event_ids: [],
          unlocks_event_ids: [],
          foreshadow_ids: [],
          notes: null,
        },
      ],
      foreshadows: [
        {
          id: crypto.randomUUID(),
          title: '失落地图残页',
          content: '一张残缺地图暗示终点不只是地点，也是代价的来源。',
          category: 'mystery',
          planted_stage_id: stage1Id,
          planted_event_id: null,
          expected_payoff_stage_id: stage3Id,
          expected_payoff_event_id: null,
          payoff_description: '最终揭示关闭裂境的代价早已写在地图提示中。',
          status: 'planted',
          importance: 'high',
          notes: null,
        },
      ],
    }
  }

  return {
    title: '深宫棋局',
    logline: '主角在风雨欲来的宫廷局势中周旋于皇权、世家与旧盟之间，试图保命也试图改局。',
    summary: '故事以宫廷内部的权力角力为核心。主角起初只是被动卷入，却在一轮轮试探、结盟和背刺中逐渐掌握主动权。最终主角必须决定自己是成为新秩序的一部分，还是亲手掀翻整张棋盘。',
    theme: '权力、忠诚与自我选择',
    core_conflict: '主角想保全自身与重要之人，但宫廷规则逼迫其不断做出牺牲与背叛。',
    ending_direction: '主角赢下局势却失去最初的天真，留下冷峻收束。',
    tags: ['宫廷', '权谋', '关系博弈'],
    default_generation_policy: {
      ...(currentScriptDesign.value?.default_generation_policy ?? {
        enforce_stage_order: false,
        enforce_pending_event: false,
        enforce_foreshadow_tracking: false,
        preferred_stage_id: null,
        preferred_event_ids: [],
        writing_brief: null,
      }),
      writing_brief: '突出试探、压迫和关系变化，用对话和局势变化推进，不要让冲突太直白。',
    },
    stage_outlines: [
      {
        id: stage1Id,
        title: '风声初起',
        order: 0,
        goal: '让主角感受到局势变化，并被迫进入权力场。',
        tension: null,
        entry_condition: null,
        exit_condition: null,
        expected_turning_point: '主角第一次意识到自己已成为棋局中的关键点。',
        linked_role_ids: [],
        linked_lorebook_entry_ids: [],
        notes: null,
      },
      {
        id: stage2Id,
        title: '暗流博弈',
        order: 1,
        goal: '让主角在多方试探和结盟中寻找站位。',
        tension: null,
        entry_condition: null,
        exit_condition: null,
        expected_turning_point: '最信任的人也显露出真实立场。',
        linked_role_ids: [],
        linked_lorebook_entry_ids: [],
        notes: null,
      },
      {
        id: stage3Id,
        title: '翻盘定局',
        order: 2,
        goal: '推动主角主动出手，重写当前权力格局。',
        tension: null,
        entry_condition: null,
        exit_condition: null,
        expected_turning_point: '主角必须亲自决定谁被保留、谁被抛弃。',
        linked_role_ids: [],
        linked_lorebook_entry_ids: [],
        notes: null,
      },
    ],
    event_nodes: [
      {
        id: crypto.randomUUID(),
        stage_id: stage1Id,
        title: '宴席上的第一次试探',
        summary: '一场看似平静的宴席上，各方通过暗示与试探把主角推上台前。',
        order: 0,
        status: 'pending',
        event_type: 'setup',
        trigger_condition: null,
        objective: '建立宫廷紧张感和角色关系。',
        obstacle: '没人会把话说透，主角难以直接判断风险。',
        expected_outcome: '主角意识到自己已无法置身事外。',
        failure_outcome: null,
        scene_hint: null,
        participant_role_ids: [],
        participant_lorebook_entry_ids: [],
        prerequisite_event_ids: [],
        unlocks_event_ids: [],
        foreshadow_ids: [],
        notes: null,
      },
      {
        id: crypto.randomUUID(),
        stage_id: stage2Id,
        title: '秘密结盟与背后拆台',
        summary: '主角试图结盟稳住局面，却发现盟约背后另有交换条件。',
        order: 0,
        status: 'pending',
        event_type: 'conflict',
        trigger_condition: null,
        objective: '推动关系复杂化，让主角看清代价。',
        obstacle: '每一方都只愿意给出有限支持。',
        expected_outcome: '主角被迫开始主动布局。',
        failure_outcome: null,
        scene_hint: null,
        participant_role_ids: [],
        participant_lorebook_entry_ids: [],
        prerequisite_event_ids: [],
        unlocks_event_ids: [],
        foreshadow_ids: [],
        notes: null,
      },
      {
        id: crypto.randomUUID(),
        stage_id: stage3Id,
        title: '朝堂翻盘',
        summary: '主角在公开局面中反制对手，决定最终站位与新秩序。',
        order: 0,
        status: 'pending',
        event_type: 'climax',
        trigger_condition: null,
        objective: '完成权力局势逆转与人物成长收束。',
        obstacle: '主角必须牺牲某段重要关系或原则。',
        expected_outcome: '主角赢下棋局，但彻底改变了自己。',
        failure_outcome: null,
        scene_hint: null,
        participant_role_ids: [],
        participant_lorebook_entry_ids: [],
        prerequisite_event_ids: [],
        unlocks_event_ids: [],
        foreshadow_ids: [],
        notes: null,
      },
    ],
    foreshadows: [
      {
        id: crypto.randomUUID(),
        title: '被篡改的密诏副本',
        content: '一份看似不起眼的密诏副本，暗示真正的继承安排早被动过手脚。',
        category: 'rule',
        planted_stage_id: stage1Id,
        planted_event_id: null,
        expected_payoff_stage_id: stage3Id,
        expected_payoff_event_id: null,
        payoff_description: '在终局对峙时成为推翻旧局的重要证据。',
        status: 'planted',
        importance: 'high',
        notes: null,
      },
    ],
  }
}

/** 处理 applyBeginnerTemplate 相关逻辑。 */
async function applyBeginnerTemplate(templateKey: BeginnerTemplateKey) {
  if (!selectedScriptDesignId.value || !currentScriptDesign.value) return

  const template = beginnerTemplates.find((item) => item.key === templateKey)
  if (!template) return

  if (!window.confirm(`确认应用${template.label}？当前基础设置内容将被模板预填覆盖。`)) return

  try {
    await updateScriptDesignMut.mutateAsync({
      id: selectedScriptDesignId.value,
      payload: buildTemplatePayload(templateKey),
    })
    toast({ title: `${template.label}已应用` })
  } catch (error) {
    toast({ title: normalizeAxiosMessage(error, '模板应用失败'), variant: 'destructive' })
  }
}

/** 处理 deleteScriptDesign 相关逻辑。 */
async function deleteScriptDesign(scriptDesign: ScriptDesign) {
  if (!window.confirm(`确认删除剧本设计「${scriptDesign.title}」？`)) return
  try {
    await deleteScriptDesignMut.mutateAsync(scriptDesign.id)
    if (selectedScriptDesignId.value === scriptDesign.id) {
      const next = scriptDesigns.value?.find((item) => item.id !== scriptDesign.id)
      selectedScriptDesignId.value = next?.id ?? ''
    }
    toast({ title: '剧本设计已删除' })
  } catch (error) {
    toast({ title: normalizeAxiosMessage(error, '删除失败'), variant: 'destructive' })
  }
}
</script>

<template>
  <div class="flex h-full bg-background">
    <ScriptDesignSidebar
      :worlds="worlds ?? []"
      :worlds-loading="worldsLoading"
      :selected-world-id="selectedWorldId"
      :script-designs="scriptDesigns ?? []"
      :script-designs-loading="scriptDesignsLoading"
      :selected-script-design-id="selectedScriptDesignId"
      :creating-disabled="createScriptDesignMut.isPending.value"
      @select-world="selectedWorldId = $event"
      @select-script="selectedScriptDesignId = $event"
      @create-script="createScriptDesign"
      @delete-script="deleteScriptDesign"
    />

    <div class="flex-1 min-w-0 overflow-hidden flex flex-col">
      <header class="h-12 shrink-0 border-b border-border px-5 flex items-center justify-between">
        <div class="min-w-0">
          <p class="text-sm font-medium truncate">{{ currentScriptDesign?.title || '剧本设计' }}</p>
          <p class="text-xs text-muted-foreground truncate">
            {{ selectedWorld?.name || '请选择世界' }}
          </p>
        </div>
        <div v-if="currentScriptDesign" class="text-xs text-muted-foreground">
          版本 {{ currentScriptDesign.version }}
        </div>
      </header>

      <div v-if="!selectedWorldId" class="flex-1 flex items-center justify-center text-sm text-muted-foreground">
        请选择一个世界后再开始管理剧本设计。
      </div>
      <div v-else-if="scriptDesignsLoading || currentScriptDesignLoading" class="flex-1 flex items-center justify-center text-sm text-muted-foreground">
        加载中…
      </div>
      <div v-else-if="!currentScriptDesign" class="flex-1 flex items-center justify-center text-sm text-muted-foreground">
        当前世界还没有剧本设计，先从左侧创建一个。
      </div>

      <div v-else class="flex-1 overflow-y-auto p-5 space-y-5">
        <div class="rounded-2xl border border-stone-200 bg-gradient-to-r from-stone-50 via-white to-amber-50/50 px-5 py-5 shadow-sm">
          <p class="text-sm font-semibold text-stone-900">剧本设计工作台</p>
          <p class="mt-1 text-sm text-slate-600">
            先完成剧本信息和主线骨架，再按需补充进阶内容。主页只保留必要信息，结构设计统一进入独立设计器。
          </p>
          <div class="mt-4 flex flex-wrap items-start gap-2">
            <button
              v-for="template in beginnerTemplates"
              :key="template.key"
              type="button"
              class="rounded-xl border border-sky-200 bg-white/80 px-3 py-2 text-left transition-colors hover:border-sky-300 hover:bg-sky-50"
              @click="applyBeginnerTemplate(template.key)"
            >
              <p class="text-sm font-medium text-slate-900">{{ template.label }}</p>
              <p class="mt-1 text-xs text-slate-600">{{ template.description }}</p>
            </button>
          </div>
        </div>

        <div class="grid gap-5 xl:grid-cols-[1.1fr_0.9fr]">
          <div class="space-y-5">
            <ScriptDesignSimpleOverviewForm
              :design="currentScriptDesign"
              :saving="updateScriptDesignMut.isPending.value"
              @save="saveOverview"
            />

          </div>

          <div class="space-y-5">
            <ScriptStructureOverviewCard
              :design="currentScriptDesign"
              @open-designer="showStructureDesigner = true"
            />
            <ScriptStoryBindingsPanel :items="bindingsData?.items ?? []" :loading="bindingsLoading" />
          </div>
        </div>
      </div>
    </div>

    <ScriptStructureDesignerDialog
      :open="showStructureDesigner"
      :design="currentScriptDesign ?? null"
      :saving="updateScriptDesignMut.isPending.value"
      @update:open="showStructureDesigner = $event"
      @save-structure="saveSimpleStructure"
    />
  </div>
</template>