/**
 * 文件说明：前端业务域逻辑与接口封装。
 */

export interface AnalyticsOverview {
  total_requests: number
  success_requests: number
  error_requests: number
  success_rate: number
  total_input_tokens: number
  total_output_tokens: number
  total_tokens: number
  total_tokens_est: number
  avg_input_tokens: number
  avg_output_tokens: number
  avg_total_tokens: number
  provider_usage_rate: number
  avg_generation_time: number
  avg_vector_hits: number
  avg_retrieved_context_count: number
  active_sessions: number
  active_worlds: number
  model_distribution: Record<string, number>
  event_type_distribution: Record<string, number>
  world_distribution: Record<string, number>
  token_source_distribution: Record<string, number>
}

export interface AnalyticsDailyStat {
  date: string
  requests: number
  success: number
  errors: number
  success_rate: number
  input_tokens: number
  output_tokens: number
  tokens: number
  tokens_est: number
  avg_input_tokens: number
  avg_output_tokens: number
  avg_total_tokens: number
  provider_usage_requests: number
  estimated_usage_requests: number
  vector_hits: number
  retrieved_context_count: number
  avg_retrieved_context_count: number
  generation_time_total: number
  avg_generation_time: number
}

export interface AnalyticsEvent {
  timestamp: string
  event_type: string
  session_id: string
  world_id: string
  model: string
  success: boolean
  generation_time: number
  prompt_tokens?: number
  completion_tokens?: number
  total_tokens?: number
  token_source?: 'provider_usage' | 'estimated' | string
  prompt_tokens_est: number
  completion_tokens_est: number
  total_tokens_est: number
  vector_hits: number
  retrieved_context_count: number
  error_type: string
}

export interface AnalyticsDistributionItem {
  key: string
  label: string
  value: number
}

export interface AnalyticsFilters {
  model?: string
  world_id?: string
  event_type?: string
}

export interface AnalyticsFilterOption {
  value: string
  count: number
}

export interface AnalyticsFilterOptions {
  models: AnalyticsFilterOption[]
  event_types: AnalyticsFilterOption[]
  world_ids: AnalyticsFilterOption[]
}

export interface AnalyticsMetricItem {
  key:
    | 'requests'
    | 'success'
    | 'errors'
    | 'inputTokens'
    | 'outputTokens'
    | 'avgTokens'
    | 'latency'
    | 'retrieval'
  label: string
  value: string
  caption?: string
  accent?: 'default' | 'success' | 'danger' | 'warning' | 'info'
}
