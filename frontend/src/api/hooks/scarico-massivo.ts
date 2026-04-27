import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import api from '../client'

export interface ScaricoConfig {
  id: string
  client_fiscal_id: string
  client_name: string
  onboarding_mode: string
  acube_br_uuid: string | null
  acube_config_id: string | null
  delega_confirmed_at: string | null
  delega_expires_at: string | null
  status: string
  last_sync_at: string | null
  last_sync_error: string | null
  last_sync_new_count: number | null
  invoices_downloaded_total: number
  invoices_downloaded_ytd: number
  environment: string
  created_at: string
}

export interface ScaricoConfigInput {
  client_fiscal_id: string
  client_name: string
  onboarding_mode?: string
}

export interface DelegaGuide {
  acube_fiscal_id: string
  portale_ade_url: string
  steps: string[]
  services_to_delegate: string[]
}

export interface InvoiceLog {
  id: string
  codice_univoco_sdi: string
  numero_fattura: string | null
  tipo_documento: string | null
  direction: string
  data_fattura: string | null
  importo_totale: number | null
  controparte_nome: string | null
  imported_into_accounting: boolean
  downloaded_at: string
}

export function useScaricoConfigs() {
  return useQuery({
    queryKey: ['scarico-massivo', 'configs'],
    queryFn: () =>
      api.get<{ items: ScaricoConfig[]; total: number }>('/scarico-massivo/configs').then((r) => r.data),
  })
}

// ── Self-tenant single-config hooks (multi-tenant isolated model) ──

export function useMyScaricoConfig() {
  return useQuery({
    queryKey: ['scarico-massivo', 'me'],
    queryFn: () => api.get<ScaricoConfig>('/scarico-massivo/me').then((r) => r.data),
  })
}

export function useSyncMyScarico() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () =>
      api
        .post<{ new_invoices: number; total_scanned: number; errors: number; message: string }>(
          '/scarico-massivo/me/sync',
          {},
        )
        .then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scarico-massivo'] }),
  })
}

export interface AppointeeCredentialsInput {
  appointee_fiscal_id: string
  password: string
  pin: string
  username_or_fiscal_id?: string
}

export function useSaveAppointeeCredentials() {
  return useMutation({
    mutationFn: (data: AppointeeCredentialsInput) =>
      api
        .post<{ appointee_fiscal_id: string; saved: boolean; message: string }>(
          '/scarico-massivo/admin/appointee-credentials',
          data,
        )
        .then((r) => r.data),
  })
}

export interface OnboardingResult {
  config_id: string
  acube_config_id: string
  appointee_fiscal_id: string
  client_fiscal_id: string
  schedule_enabled: boolean
  backfill_archive: boolean
  message: string
}

export function useStartMyOnboarding() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (backfillArchive: boolean = true) =>
      api
        .post<OnboardingResult>(
          `/scarico-massivo/me/onboarding?backfill_archive=${backfillArchive}`,
        )
        .then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scarico-massivo'] }),
  })
}

export function useMyDownloadedInvoices() {
  return useQuery({
    queryKey: ['scarico-massivo', 'me', 'invoices'],
    queryFn: () =>
      api.get<{ items: InvoiceLog[]; total: number }>('/scarico-massivo/me/invoices').then((r) => r.data),
  })
}

export function useDelegaGuide() {
  return useQuery({
    queryKey: ['scarico-massivo', 'delega-guide'],
    queryFn: () => api.get<DelegaGuide>('/scarico-massivo/delega-guide').then((r) => r.data),
    staleTime: Infinity,
  })
}

export function useRegisterClient() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ScaricoConfigInput) =>
      api.post<ScaricoConfig>('/scarico-massivo/configs', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scarico-massivo'] }),
  })
}

export function useDeleteScaricoConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (configId: string) =>
      api.delete(`/scarico-massivo/configs/${configId}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scarico-massivo'] }),
  })
}

export function useSyncScarico() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (configId: string) =>
      api.post(`/scarico-massivo/configs/${configId}/sync`, {}).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scarico-massivo'] }),
  })
}

export function useDownloadedInvoices(configId: string | null) {
  return useQuery({
    queryKey: ['scarico-massivo', 'invoices', configId],
    queryFn: () =>
      api
        .get<{ items: InvoiceLog[]; total: number }>(`/scarico-massivo/configs/${configId}/invoices`)
        .then((r) => r.data),
    enabled: !!configId,
  })
}
