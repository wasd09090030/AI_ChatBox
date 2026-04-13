/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

import api from '@/services/api'
import { getUserId } from '@/domains/user/api/userIdentity'

/** 处理 getStoryHeaders 相关逻辑。 */
function getStoryHeaders(): Record<string, string> {
  return {
    'Content-Type': 'application/json',
    'X-User-ID': getUserId(),
  }
}

export interface StoryAdjustmentPolishRequest {
  story_id: string
  session_id: string
  segment_id: string
  selected_text: string
  before_context?: string
  after_context?: string
  preset_key: string
  preset_instruction: string
  custom_instruction?: string
  world_id?: string
  model?: string
  provider?: string
  base_url?: string
  temperature?: number
}

export interface StoryAdjustmentPolishResponse {
  story_id: string
  segment_id: string
  original_text: string
  polished_text: string
  model: string
  generation_time: number
}

// storyAdjustmentApi 相关状态。
export const storyAdjustmentApi = {
  polish(payload: StoryAdjustmentPolishRequest) {
    return api
      .post<StoryAdjustmentPolishResponse>('/story/adjustments/polish', payload, {
        headers: getStoryHeaders(),
      })
      .then((response) => response.data)
  },
}
