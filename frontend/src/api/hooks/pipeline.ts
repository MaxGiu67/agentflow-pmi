import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../client'

// ── Pipeline Templates (Pivot 9) ──
export function usePipelineTemplates() {
  return useQuery({
    queryKey: ['pipeline-templates'],
    queryFn: () => api.get('/pipeline-templates').then((r) => r.data),
  })
}

export function useCreatePipelineTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/pipeline-templates', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline-templates'] }),
  })
}
export function useUpdatePipelineTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: any) => api.patch(`/pipeline-templates/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline-templates'] }),
  })
}
export function useDeletePipelineTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/pipeline-templates/${id}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline-templates'] }),
  })
}
export function useAddTemplateStage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ templateId, ...data }: any) => api.post(`/pipeline-templates/${templateId}/stages`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline-templates'] }),
  })
}
export function useUpdateTemplateStage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: any) => api.patch(`/pipeline-templates/stages/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline-templates'] }),
  })
}
export function useDeleteTemplateStage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/pipeline-templates/stages/${id}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pipeline-templates'] }),
  })
}
