import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../client'

// ── Resources (Pivot 9) ──
export function useResources(skill = '', seniority = '') {
  return useQuery({
    queryKey: ['resources', skill, seniority],
    queryFn: () => api.get('/resources', { params: { skill, seniority } }).then((r) => r.data),
  })
}
export function useCreateResource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: any) => api.post('/resources', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['resources'] }),
  })
}
export function useUpdateResource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: any) => api.patch(`/resources/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['resources'] }),
  })
}
export function useAddResourceSkill() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ resourceId, ...data }: any) => api.post(`/resources/${resourceId}/skills`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['resources'] }),
  })
}
export function useResourceMatch(techStack = '', seniority = '') {
  return useQuery({
    queryKey: ['resource-match', techStack, seniority],
    queryFn: () => api.get('/resources/match', { params: { tech_stack: techStack, seniority } }).then((r) => r.data),
    enabled: !!techStack,
  })
}
export function useResourceBench(days = 30) {
  return useQuery({
    queryKey: ['resource-bench', days],
    queryFn: () => api.get('/resources/bench', { params: { days } }).then((r) => r.data),
  })
}
