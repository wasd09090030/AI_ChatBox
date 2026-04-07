import type { Role } from '@/utils/types'

export interface PromptFocusTemplate {
  id: string
  label: string
  description: string
  instruction: string
}

export const DEFAULT_ROLES: Role[] = [
  {
    id: 'default',
    name: 'Default Assistant',
    description: 'A helpful AI assistant',
    systemPrompt: 'You are a helpful AI assistant.',
    icon: '🤖',
  },
  {
    id: 'code',
    name: 'Code Assistant',
    description: 'Expert in programming and software development',
    systemPrompt: 'You are an expert programmer and software developer. Help users with coding questions, debugging, and best practices.',
    icon: '💻',
  },
  {
    id: 'writer',
    name: 'Creative Writer',
    description: 'Helps with creative writing and content creation',
    systemPrompt: 'You are a creative writing assistant. Help users with storytelling, content creation, and writing improvement.',
    icon: '✍️',
  },
]

export const STORY_PROMPT_FOCUS_TEMPLATES: PromptFocusTemplate[] = [
  {
    id: 'advance-conflict',
    label: '推进冲突',
    description: '本轮让主要矛盾明显升级，但不要直接收束主线。',
    instruction: '请将本轮故事重点放在推进当前主要冲突，制造新的压力或阻碍，但不要直接结束主线。',
  },
  {
    id: 'relationship-tension',
    label: '人物张力',
    description: '强化角色之间的关系变化、猜疑或默契。',
    instruction: '请将本轮故事重点放在角色关系变化与情绪张力，通过对白和细节显出彼此态度变化。',
  },
  {
    id: 'clue-reveal',
    label: '抛出线索',
    description: '给出关键但不完整的新线索，推动探索。',
    instruction: '请将本轮故事重点放在抛出一个与当前情节直接相关的新线索，但保留部分未知信息，继续留出探索空间。',
  },
  {
    id: 'scene-immersion',
    label: '场景沉浸',
    description: '强化环境、感官与氛围，让场景更立体。',
    instruction: '请将本轮故事重点放在场景沉浸感，通过环境变化、五感细节和人物反应让画面更具体。',
  },
]