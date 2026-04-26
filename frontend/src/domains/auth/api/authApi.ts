import api from '@/services/api'

export interface AuthenticatedUser {
  user_id: string
  login_identifier: string
  display_name: string
  status: string
  created_at: string
  last_login_at?: string | null
}

interface AuthSessionResponse {
  user: AuthenticatedUser
}

export interface LoginRequest {
  login_identifier: string
  password: string
}

export interface RegisterRequest extends LoginRequest {
  display_name?: string
}

export interface LegacyClaimRequest {
  legacy_user_id: string
  claim_unowned_data?: boolean
}

export interface LegacyClaimResponse {
  success: boolean
  migrated_user_settings: boolean
  migrated_worlds: number
  migrated_stories: number
  migrated_script_designs: number
  migrated_story_sessions: number
  migrated_lorebook_entries: number
  migrated_runtime_states: number
  migrated_memory_events: number
  migrated_entity_events: number
  claimed_unowned_resources: boolean
  warnings: string[]
}

export async function login(payload: LoginRequest): Promise<AuthenticatedUser> {
  const response = await api.post<AuthSessionResponse>('/auth/login', payload)
  return response.data.user
}

export async function register(payload: RegisterRequest): Promise<AuthenticatedUser> {
  const response = await api.post<AuthSessionResponse>('/auth/register', payload)
  return response.data.user
}

export async function logout(): Promise<void> {
  await api.post('/auth/logout')
}

export async function fetchCurrentUser(): Promise<AuthenticatedUser> {
  const response = await api.get<AuthenticatedUser>('/auth/me')
  return response.data
}

export async function claimLegacyIdentity(
  payload: LegacyClaimRequest,
): Promise<LegacyClaimResponse> {
  const response = await api.post<LegacyClaimResponse>('/auth/claim-legacy', payload)
  return response.data
}
