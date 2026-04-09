import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../client'

// ── Profile ──
export function useProfile() {
  return useQuery({
    queryKey: ['profile'],
    queryFn: () => api.get('/profile').then((r) => r.data),
  })
}

export function useUpdateProfile() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      api.patch('/profile', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['profile'] })
    },
  })
}

// ── Permissions ──
export function useMyPermissions() {
  return useQuery({
    queryKey: ['my-permissions'],
    queryFn: () => api.get('/users/me/permissions').then((r) => r.data),
  })
}

// ── User Management ──
export function useTeamUsers() {
  return useQuery({
    queryKey: ['team-users'],
    queryFn: () => api.get('/users').then((r) => r.data),
  })
}

export function useInviteUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      api.post('/users/invite', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['team-users'] }),
  })
}

export function useUpdateUserRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      api.patch(`/users/${userId}/role`, { role }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['team-users'] }),
  })
}

export function useUpdateUserCrmRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, crm_role_id }: { userId: string; crm_role_id: string | null }) =>
      api.patch(`/users/${userId}/crm-role`, { crm_role_id }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['team-users'] }),
  })
}

export function useToggleUserActive() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) =>
      api.post(`/users/${userId}/toggle-active`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['team-users'] }),
  })
}
