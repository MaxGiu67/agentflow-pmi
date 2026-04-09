import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from '../client'

// ── Deal Documents ──
export function useDealDocuments(dealId: string) {
  return useQuery({
    queryKey: ['deal-documents', dealId],
    queryFn: () => api.get(`/crm/deals/${dealId}/documents`).then((r) => r.data),
    enabled: !!dealId,
  })
}

export function useAddDealDocument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ dealId, ...data }: any) => api.post(`/crm/deals/${dealId}/documents`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['deal-documents'] }),
  })
}

export function useDeleteDealDocument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (docId: string) => api.delete(`/crm/documents/${docId}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['deal-documents'] }),
  })
}

export function useUploadDealDocument() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ dealId, formData }: { dealId: string; formData: FormData }) =>
      api.post(`/crm/deals/${dealId}/documents/upload`, formData).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['deal-documents'] }),
  })
}
