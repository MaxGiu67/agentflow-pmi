import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../client'

// ── CRM Pipeline ──
export function useCrmPipeline() {
  return useQuery({
    queryKey: ['crm-pipeline'],
    queryFn: () => api.get('/crm/pipeline/summary').then((r) => r.data),
  })
}

export function useCrmStages() {
  return useQuery({
    queryKey: ['crm-stages'],
    queryFn: () => api.get('/crm/pipeline/stages').then((r) => r.data),
  })
}

export function useCrmDeals(stage?: string, dealType?: string) {
  return useQuery({
    queryKey: ['crm-deals', stage, dealType],
    queryFn: () => {
      const params = new URLSearchParams()
      if (stage) params.set('stage', stage)
      if (dealType) params.set('deal_type', dealType)
      return api.get(`/crm/deals?${params}`).then((r) => r.data)
    },
  })
}

export function useCrmDeal(dealId: string) {
  return useQuery({
    queryKey: ['crm-deal', dealId],
    queryFn: () => api.get(`/crm/deals/${dealId}`).then((r) => r.data),
    enabled: !!dealId && dealId !== '0',
  })
}

export function useCrmWonDeals() {
  return useQuery({
    queryKey: ['crm-won'],
    queryFn: () => api.get('/crm/deals/won').then((r) => r.data),
  })
}

export function useCrmPendingOrders() {
  return useQuery({
    queryKey: ['crm-pending-orders'],
    queryFn: () => api.get('/crm/orders/pending').then((r) => r.data),
  })
}

export function useCrmContacts(search?: string) {
  return useQuery({
    queryKey: ['crm-contacts', search],
    queryFn: () => api.get(`/crm/contacts?search=${search || ''}`).then((r) => r.data),
  })
}

export function useCreateCrmDeal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/crm/deals', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['crm-deals'] })
      qc.invalidateQueries({ queryKey: ['crm-pipeline'] })
    },
  })
}

export function useCreateCrmContact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/crm/contacts', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['crm-contacts'] }),
  })
}

export function useUpdateCrmContact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: any) => api.patch(`/crm/contacts/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['crm-contacts'] }),
  })
}
export function useDeleteCrmContact() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/crm/contacts/${id}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['crm-contacts'] }),
  })
}

export function useRegisterOrder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ dealId, ...data }: { dealId: string } & Record<string, unknown>) =>
      api.post(`/crm/deals/${dealId}/order`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['crm-deals'] })
      qc.invalidateQueries({ queryKey: ['crm-pending-orders'] })
    },
  })
}

export function useConfirmOrder() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (dealId: string) => api.post(`/crm/deals/${dealId}/order/confirm`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['crm-deals'] })
      qc.invalidateQueries({ queryKey: ['crm-pipeline'] })
      qc.invalidateQueries({ queryKey: ['crm-won'] })
      qc.invalidateQueries({ queryKey: ['crm-pending-orders'] })
    },
  })
}

export function useCrmAnalytics() {
  return useQuery({
    queryKey: ['crm-analytics'],
    queryFn: () => api.get('/crm/pipeline/analytics').then((r) => r.data),
  })
}

export function useUpdateCrmDeal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ dealId, ...data }: { dealId: string } & Record<string, unknown>) =>
      api.patch(`/crm/deals/${dealId}`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['crm-deals'] })
      qc.invalidateQueries({ queryKey: ['crm-pipeline'] })
      qc.invalidateQueries({ queryKey: ['crm-analytics'] })
    },
  })
}

// ── CRM Activities ──
export function useCrmActivities(contactId?: string, dealId?: string) {
  return useQuery({
    queryKey: ['crm-activities', contactId, dealId],
    queryFn: () => {
      const params = new URLSearchParams()
      if (contactId) params.set('contact_id', contactId)
      if (dealId) params.set('deal_id', dealId)
      return api.get(`/crm/activities?${params}`).then((r) => r.data)
    },
  })
}

export function useCreateCrmActivity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      api.post('/crm/activities', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['crm-activities'] })
      qc.invalidateQueries({ queryKey: ['crm-stats'] })
    },
  })
}

export function useUpdateCrmActivity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ activityId, ...data }: any) =>
      api.patch(`/crm/activities/${activityId}`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['crm-activities'] })
      qc.invalidateQueries({ queryKey: ['crm-stats'] })
    },
  })
}

// ── CRM Companies ──
export function useCrmCompanies(search = '') {
  return useQuery({
    queryKey: ['crm-companies', search],
    queryFn: () => api.get(`/crm/companies?search=${search}`).then((r) => r.data),
  })
}

export function useCreateCrmCompany() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      api.post('/crm/companies', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['crm-companies'] }),
  })
}

export function useCrmCompany(companyId: string) {
  return useQuery({
    queryKey: ['crm-company', companyId],
    queryFn: () => api.get(`/crm/companies/${companyId}`).then((r) => r.data),
    enabled: !!companyId,
  })
}
