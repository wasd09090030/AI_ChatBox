/**
 * 文件说明：前端可复用界面组件。
 */

export type StoryMode = 'narrative' | 'choices' | 'instruction'

export interface StorySegment {
  id: string
  prompt: string
  creation_mode?: 'improv' | 'scripted' | null
  content: string
  choices: string[]
  retrieved_context: string[]
  runtime_state_snapshot?: Record<string, unknown> | null
  timestamp: string
}

export interface StoredStory {
  id: string
  world_id: string
  world_name: string
  title: string
  segments: StorySegment[]
  created_at: string
  updated_at: string
  metadata: Record<string, unknown>
}
