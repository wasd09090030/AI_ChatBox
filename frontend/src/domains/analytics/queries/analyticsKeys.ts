/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

export const ANALYTICS_KEYS = {
  overview: (filtersKey: string) => ['analytics', 'overview', filtersKey] as const,
  daily: (days: number, filtersKey: string) => ['analytics', 'daily', days, filtersKey] as const,
  events: (limit: number, filtersKey: string) => ['analytics', 'events', limit, filtersKey] as const,
  filterOptions: ['analytics', 'filter-options'] as const,
}
