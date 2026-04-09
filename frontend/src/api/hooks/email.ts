import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../client'

// ── Email Marketing ──

export function useEmailTemplates() {
  return useQuery({
    queryKey: ['email-templates'],
    queryFn: () => api.get('/email/templates').then((r) => r.data),
  })
}

export function useEmailTemplate(id: string) {
  return useQuery({
    queryKey: ['email-template', id],
    queryFn: () => api.get(`/email/templates/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useCreateEmailTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/email/templates', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['email-templates'] }),
  })
}

export function useUpdateEmailTemplate() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Record<string, unknown>) =>
      api.patch(`/email/templates/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['email-templates'] }),
  })
}

export function usePreviewTemplate() {
  return useMutation({
    mutationFn: ({ id, params }: { id: string; params: Record<string, string> }) =>
      api.post(`/email/templates/${id}/preview`, { params }).then((r) => r.data),
  })
}

export function useEmailSends(contactId?: string) {
  const params = contactId ? `?contact_id=${contactId}` : ''
  return useQuery({
    queryKey: ['email-sends', contactId],
    queryFn: () => api.get(`/email/sends${params}`).then((r) => r.data),
  })
}

export function useSendEmail() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/email/send', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['email-sends'] }),
  })
}

export function useEmailAnalytics() {
  return useQuery({
    queryKey: ['email-analytics'],
    queryFn: () => api.get('/email/analytics').then((r) => r.data),
  })
}

export function useEmailSequences() {
  return useQuery({
    queryKey: ['email-sequences'],
    queryFn: () => api.get('/email/sequences').then((r) => r.data).catch(() => []),
  })
}

export function useCreateSequence() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/email/sequences', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['email-sequences'] }),
  })
}

// ── AI Email Generator ──

export function useGenerateEmail() {
  return useMutation({
    mutationFn: (data: { prompt: string; tone?: string; contact_name?: string; deal_name?: string }) =>
      api.post('/email/generate', data).then((r) => r.data),
  })
}

export function useRefineEmail() {
  return useMutation({
    mutationFn: (data: { html_body: string; instruction: string }) =>
      api.post('/email/refine', data).then((r) => r.data),
  })
}

// ── Chat (useSendMessage) ──
export function useSendMessage() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ message, conversationId, context }: { message: string; conversationId?: string; context?: { page: string; year: number } }) =>
      api.post('/chat/send', {
        message,
        conversation_id: conversationId ?? null,
        context: context ?? null,
      }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['conversations'] })
    },
  })
}
