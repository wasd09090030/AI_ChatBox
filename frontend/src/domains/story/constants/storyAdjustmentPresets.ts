export interface StoryAdjustmentPreset {
  key: string
  label: string
  description: string
  instruction: string
}

export const STORY_ADJUSTMENT_PRESETS: StoryAdjustmentPreset[] = [
  {
    key: 'polish',
    label: '语言润色',
    description: '修正语句不顺、重复表达和口吻生硬的问题。',
    instruction: '保持原意与剧情事实不变，只优化语言流畅度、自然度和可读性。',
  },
  {
    key: 'detail',
    label: '细节增强',
    description: '增强动作、场景和感官层面的描写。',
    instruction: '在不改变剧情结论的前提下，适度增强动作描写、环境细节和感官信息。',
  },
  {
    key: 'pace',
    label: '节奏压缩',
    description: '删去冗余表达，让叙事更利落。',
    instruction: '删除冗余描述，保留关键信息，使段落更紧凑、更有推进感。',
  },
  {
    key: 'dialogue',
    label: '对白强化',
    description: '让角色对白更自然、更有张力。',
    instruction: '强化对白的角色区分、情绪张力和潜台词，但不要改变剧情事实。',
  },
  {
    key: 'tone',
    label: '文风统一',
    description: '向当前故事的叙事语气和风格靠拢。',
    instruction: '参考当前故事上下文的叙事语气与文风，让选中文本风格更统一。',
  },
]
