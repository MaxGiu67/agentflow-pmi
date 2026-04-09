import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../client'

// ── Portal Integration (Pivot 10) ──
export function usePortalStatus() {
  return useQuery({
    queryKey: ['portal-status'],
    queryFn: () => api.get('/portal/status').then((r) => r.data),
  })
}

export function usePortalCustomers(search?: string) {
  return useQuery({
    queryKey: ['portal-customers', search],
    queryFn: () => api.get(`/portal/customers?search=${search || ''}`).then((r) => r.data),
  })
}

export function usePortalPersons(search?: string) {
  return useQuery({
    queryKey: ['portal-persons', search],
    queryFn: () => api.get(`/portal/persons?search=${search || ''}`).then((r) => r.data),
    enabled: search === undefined || search === '' || search.length >= 2,
  })
}

export function usePortalProjectTypes() {
  return useQuery({
    queryKey: ['portal-project-types'],
    queryFn: () => api.get('/portal/project-types').then((r) => r.data),
  })
}

export function usePortalLocations() {
  return useQuery({
    queryKey: ['portal-locations'],
    queryFn: () => api.get('/portal/locations').then((r) => r.data),
  })
}

export function usePortalAccountManagers() {
  return useQuery({
    queryKey: ['portal-account-managers'],
    queryFn: () => api.get('/portal/account-managers').then((r) => r.data),
  })
}

export function useMyPortalAccountManager() {
  return useQuery({
    queryKey: ['portal-my-account-manager'],
    queryFn: () => api.get('/portal/my-account-manager').then((r) => r.data),
  })
}

export function usePortalProtocolByCustomer(customerId: number | undefined) {
  return useQuery({
    queryKey: ['portal-protocol-customer', customerId],
    queryFn: () => api.get(`/portal/offers/protocol-by-customer/${customerId}`).then((r) => r.data),
    enabled: !!customerId,
  })
}

export function useCreatePortalOffer() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/portal/offers/create', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['portal-offers'] }),
  })
}

export function usePortalOfferProtocol(customerCode: string) {
  return useQuery({
    queryKey: ['portal-protocol', customerCode],
    queryFn: () => api.get(`/portal/offers/protocol/${customerCode}`).then((r) => r.data),
    enabled: !!customerCode,
  })
}

export function useCreatePortalActivity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/portal/activities/create', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['portal-deal-project'] }),
  })
}

export function useAssignPortalEmployee() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/portal/activities/assign', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['portal-deal-project'] }),
  })
}

export function useDealProject(dealId: string | undefined, portalProjectId: number | undefined) {
  return useQuery({
    queryKey: ['portal-deal-project', dealId],
    queryFn: () => api.get(`/portal/deal-project/${dealId}`).then((r) => r.data),
    enabled: !!dealId && !!portalProjectId,
  })
}

export function useDealProgress(dealId: string | undefined, portalProjectId: number | undefined) {
  return useQuery({
    queryKey: ['portal-deal-progress', dealId],
    queryFn: () => api.get(`/portal/deal-progress/${dealId}`).then((r) => r.data),
    enabled: !!dealId && !!portalProjectId,
  })
}

export function useApproveOffer() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ offerId, ...data }: { offerId: number; start_date: string; end_date: string; orderNum?: string; deal_id?: string }) =>
      api.post(`/portal/offers/${offerId}/approve`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['crm-deal'] })
      qc.invalidateQueries({ queryKey: ['crm-deals'] })
      qc.invalidateQueries({ queryKey: ['portal-deal-project'] })
    },
  })
}

export function usePortalActivityTypes() {
  return useQuery({
    queryKey: ['portal-activity-types'],
    queryFn: () => api.get('/portal/activities/types').then((r) => r.data),
  })
}

export function useCreatePortalActivityOnProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/portal/activities/create', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['portal-deal-project'] }),
  })
}

export function useAssignEmployeeToActivity() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/portal/activities/assign', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['portal-deal-project'] }),
  })
}

export function usePortalOffer(offerId: number | undefined) {
  return useQuery({
    queryKey: ['portal-offer', offerId],
    queryFn: () => api.get(`/portal/offers/${offerId}`).then((r) => r.data),
    enabled: !!offerId,
  })
}

export function usePortalOffers(customerId: number | undefined) {
  return useQuery({
    queryKey: ['portal-offers', customerId],
    queryFn: () => api.get(`/portal/offers?search=`).then((r) => r.data),
    enabled: !!customerId,
  })
}

export function useMatchCustomer() {
  return useMutation({
    mutationFn: (piva: string) => api.get(`/portal/match-customer?piva=${encodeURIComponent(piva)}`).then((r) => r.data),
  })
}

export function useBatchMatchCustomers() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post('/portal/batch-match').then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['crm-deals'] }),
  })
}

export function useLinkDealToProject() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { deal_id: string; portal_project_id: number }) =>
      api.post('/portal/link-project', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['crm-deal'] }),
  })
}
