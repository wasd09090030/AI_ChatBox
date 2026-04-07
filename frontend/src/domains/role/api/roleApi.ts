import api from '@/services/api'
import type { Role } from '@/utils/types'

export const roleApi = {
  async getRoles(): Promise<Role[]> {
    const response = await api.get<Role[]>('/roles')
    return response.data
  },

  async getRole(roleId: string): Promise<Role> {
    const response = await api.get<Role>(`/roles/${roleId}`)
    return response.data
  },

  async createRole(role: Omit<Role, 'id'>): Promise<Role> {
    const response = await api.post<Role>('/roles', role)
    return response.data
  },

  async updateRole(roleId: string, role: Partial<Role>): Promise<Role> {
    const response = await api.put<Role>(`/roles/${roleId}`, role)
    return response.data
  },

  async deleteRole(roleId: string): Promise<void> {
    await api.delete(`/roles/${roleId}`)
  },

  async getDefaultRoles(): Promise<Role[]> {
    const response = await api.get<Role[]>('/roles/defaults')
    return response.data
  },
}