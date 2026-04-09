import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../client'

// ── Deal Resources (Sprint A) ──
export function useDealResources(dealId: string | undefined) {
  return useQuery({
    queryKey: ['deal-resources', dealId],
    queryFn: () => api.get(`/crm/deals/${dealId}/resources`).then((r) => r.data),
    enabled: !!dealId,
  })
}

export function useAddDealResource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ dealId, ...data }: any) =>
      api.post(`/crm/deals/${dealId}/resources`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['deal-resources'] }),
  })
}

export function useUpdateDealResource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ dealId, resourceId, ...data }: any) =>
      api.patch(`/crm/deals/${dealId}/resources/${resourceId}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['deal-resources'] }),
  })
}

export function useRemoveDealResource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ dealId, resourceId }: any) =>
      api.delete(`/crm/deals/${dealId}/resources/${resourceId}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['deal-resources'] }),
  })
}

export function useDealRequiresResources(dealId: string | undefined) {
  return useQuery({
    queryKey: ['deal-requires-resources', dealId],
    queryFn: () => api.get(`/crm/deals/${dealId}/resources/requires`).then((r) => r.data),
    enabled: !!dealId,
  })
}

export function useCreateOfferFromDeal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ dealId, ...data }: any) =>
      api.post(`/portal/offers/create-from-deal/${dealId}`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['crm-deal'] })
      qc.invalidateQueries({ queryKey: ['crm-deals'] })
    },
  })
}

export function useCreateProjectFromDeal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ dealId, ...data }: any) =>
      api.post(`/portal/projects/create-from-deal/${dealId}`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['crm-deal'] })
      qc.invalidateQueries({ queryKey: ['crm-deals'] })
    },
  })
}
