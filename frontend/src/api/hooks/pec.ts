import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../client'

export interface PecProviderPreset {
  code: string
  label: string
  smtp_host: string
  smtp_port: number
  imap_host: string
  imap_port: number
  docs?: string
}

export interface PecConfig {
  provider: string
  pec_address: string
  username: string
  smtp_host: string
  smtp_port: number
  imap_host: string
  imap_port: number
  verified: boolean
  last_test_at: string | null
  last_test_error: string | null
}

export interface PecConfigInput {
  provider: string
  pec_address: string
  username: string
  password: string
  smtp_host?: string
  smtp_port?: number
  imap_host?: string
  imap_port?: number
}

export interface PecTestResult {
  smtp_ok: boolean
  imap_ok: boolean
  error: string | null
}

export interface PecSendResult {
  invoice_id: string
  pec_message_id: string
  recipient: string
  filename: string
  sent_at: string
  sdi_status: string
}

export function usePecProviders() {
  return useQuery({
    queryKey: ['pec-providers'],
    queryFn: () =>
      api.get<{ providers: PecProviderPreset[] }>('/pec/providers').then((r) => r.data.providers),
    staleTime: Infinity,
  })
}

export function usePecConfig() {
  return useQuery({
    queryKey: ['pec-config'],
    queryFn: () => api.get<PecConfig | null>('/pec/config').then((r) => r.data),
  })
}

export function useSavePecConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: PecConfigInput) => api.put<PecConfig>('/pec/config', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pec-config'] }),
  })
}

export function useTestPecConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post<PecTestResult>('/pec/config/test').then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pec-config'] }),
  })
}

export function useSendInvoicePec() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      invoiceId,
      file,
      testMode = false,
    }: {
      invoiceId: string
      file: File
      testMode?: boolean
    }) => {
      const fd = new FormData()
      fd.append('file', file)
      return api
        .post<PecSendResult>(
          `/pec/invoices/${invoiceId}/send?test_mode=${testMode ? 'true' : 'false'}`,
          fd,
          { headers: { 'Content-Type': 'multipart/form-data' } },
        )
        .then((r) => r.data)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invoices'] })
      qc.invalidateQueries({ queryKey: ['active-invoices'] })
    },
  })
}

export function usePollPecReceipts() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      api
        .post<{ new_receipts: number; items: unknown[] }>('/pec/receipts/poll')
        .then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invoices'] })
      qc.invalidateQueries({ queryKey: ['active-invoices'] })
    },
  })
}

export function buildInvoiceXmlUrl(invoiceId: string): string {
  const base = import.meta.env.VITE_API_URL || ''
  return `${base}/api/v1/invoices/active/${invoiceId}/xml`
}
