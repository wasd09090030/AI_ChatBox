/**
 * 文件说明：故事详情查询 hooks。
 */

import { computed, unref, type MaybeRef } from 'vue'
import { useQuery } from '@tanstack/vue-query'
import { storyLibraryApi } from '@/domains/story/api/storyLibraryApi'

export const STORY_QUERY_KEYS = {
  detail: (storyId?: string) => ['stories', 'detail', storyId ?? 'none'] as const,
}

/** 处理 useStoryQuery 相关逻辑。 */
export function useStoryQuery(storyId?: MaybeRef<string | null | undefined>) {
  return useQuery({
    queryKey: computed(() => STORY_QUERY_KEYS.detail(unref(storyId) || undefined)),
    queryFn: () => storyLibraryApi.get(unref(storyId) || ''),
    enabled: computed(() => !!unref(storyId)),
    staleTime: 30_000,
  })
}
