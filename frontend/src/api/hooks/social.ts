import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../client'

// ── Social Selling: Products ──
export function useProducts(activeOnly = false) {
  return useQuery({
    queryKey: ['products', activeOnly],
    queryFn: () => api.get(`/social/products?active_only=${activeOnly}`).then((r) => r.data),
  })
}
export function useCreateProduct() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      api.post('/social/products', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }),
  })
}
export function useUpdateProduct() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string } & Record<string, unknown>) =>
      api.patch(`/social/products/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['products'] }),
  })
}

// ── Social Selling: Roles ──
export function useRoles() {
  return useQuery({
    queryKey: ['crm-roles'],
    queryFn: () => api.get('/social/roles').then((r) => r.data),
  })
}
export function useCreateRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { name: string; description?: string; permissions?: Record<string, string[]> }) =>
      api.post('/social/roles', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['crm-roles'] }),
  })
}
export function useDeleteRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/social/roles/${id}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['crm-roles'] }),
  })
}

// ── Social Selling: Origins ──
export function useOrigins(activeOnly = false) {
  return useQuery({
    queryKey: ['origins', activeOnly],
    queryFn: () => api.get(`/social/origins?active_only=${activeOnly}`).then((r) => r.data),
  })
}
export function useCreateOrigin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { code: string; label: string; parent_channel?: string }) =>
      api.post('/social/origins', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['origins'] }),
  })
}
export function useUpdateOrigin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string; label?: string; is_active?: boolean }) =>
      api.patch(`/social/origins/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['origins'] }),
  })
}
export function useDeleteOrigin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/social/origins/${id}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['origins'] }),
  })
}

// ── Social Selling: Activity Types ──
export function useActivityTypes(activeOnly = false) {
  return useQuery({
    queryKey: ['activity-types', activeOnly],
    queryFn: () => api.get(`/social/activity-types?active_only=${activeOnly}`).then((r) => r.data),
  })
}
export function useCreateActivityType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { code: string; label: string; category?: string; counts_as_last_contact?: boolean }) =>
      api.post('/social/activity-types', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['activity-types'] }),
  })
}
export function useUpdateActivityType() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string; label?: string; is_active?: boolean; category?: string }) =>
      api.patch(`/social/activity-types/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['activity-types'] }),
  })
}

// ── Social Selling: Pipeline Stages ──
export function useSocialPipelineStages() {
  return useQuery({
    queryKey: ['social-pipeline-stages'],
    queryFn: () => api.get('/social/pipeline/stages').then((r) => r.data),
  })
}

// ── Social Selling: Deal Products ──
export function useDealProducts(dealId: string) {
  return useQuery({
    queryKey: ['deal-products', dealId],
    queryFn: () => api.get(`/social/deals/${dealId}/products`).then((r) => r.data),
    enabled: !!dealId,
  })
}
export function useAddDealProduct() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ dealId, ...data }: { dealId: string; product_id: string; quantity?: number; price_override?: number }) =>
      api.post(`/social/deals/${dealId}/products`, data).then((r) => r.data),
    onSuccess: (_d, v) => qc.invalidateQueries({ queryKey: ['deal-products', v.dealId] }),
  })
}
export function useRemoveDealProduct() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ dealId, lineId }: { dealId: string; lineId: string }) =>
      api.delete(`/social/deals/${dealId}/products/${lineId}`).then((r) => r.data),
    onSuccess: (_d, v) => qc.invalidateQueries({ queryKey: ['deal-products', v.dealId] }),
  })
}

// ── Social Selling: Audit Log ──
export function useAuditLog(params: { action?: string; limit?: number; offset?: number } = {}) {
  return useQuery({
    queryKey: ['audit-log', params],
    queryFn: () => {
      const q = new URLSearchParams()
      if (params.action) q.set('action', params.action)
      if (params.limit) q.set('limit', String(params.limit))
      if (params.offset) q.set('offset', String(params.offset))
      return api.get(`/social/audit-log?${q}`).then((r) => r.data)
    },
  })
}

// ── Social Selling: Scorecard ──
export function useScorecard(userId: string, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ['scorecard', userId, startDate, endDate],
    queryFn: () => {
      const q = new URLSearchParams()
      if (startDate) q.set('start_date', startDate)
      if (endDate) q.set('end_date', endDate)
      return api.get(`/social/scorecard/${userId}?${q}`).then((r) => r.data)
    },
    enabled: !!userId,
  })
}

// ── Social Selling: Compensation ──
export function useCompensationRules() {
  return useQuery({
    queryKey: ['compensation-rules'],
    queryFn: () => api.get('/social/compensation-rules').then((r) => r.data),
  })
}
export function useCreateCompensationRule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      api.post('/social/compensation-rules', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['compensation-rules'] }),
  })
}
export function useMonthlyCompensation(month?: string) {
  return useQuery({
    queryKey: ['compensation-monthly', month],
    queryFn: () => api.get(`/social/compensation/monthly?month=${month || ''}`).then((r) => r.data),
  })
}
export function useCalculateCompensation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (month: string) =>
      api.post(`/social/compensation/calculate?month=${month}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['compensation-monthly'] }),
  })
}
export function useConfirmCompensation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (entryId: string) =>
      api.patch(`/social/compensation/monthly/${entryId}/confirm`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['compensation-monthly'] }),
  })
}
export function useMarkPaidCompensation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (entryId: string) =>
      api.patch(`/social/compensation/monthly/${entryId}/paid`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['compensation-monthly'] }),
  })
}

// ── Social Selling: Dashboards ──
export function useSocialDashboards() {
  return useQuery({
    queryKey: ['social-dashboards'],
    queryFn: () => api.get('/social/dashboards').then((r) => r.data),
  })
}
