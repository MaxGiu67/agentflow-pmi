import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from './client'

// ── Dashboard ──
export function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get('/dashboard/summary').then((r) => r.data),
  })
}

export function useAgentStatuses() {
  return useQuery({
    queryKey: ['agents-status'],
    queryFn: () => api.get('/agents/status').then((r) => r.data),
  })
}

export function useYearlyStats(year: number) {
  return useQuery({
    queryKey: ['yearly-stats', year],
    queryFn: () => api.get(`/dashboard/yearly-stats?year=${year}`).then((r) => r.data),
    enabled: !!year,
  })
}

// ── Dashboard Layout ──
export function useDashboardLayout() {
  return useQuery({
    queryKey: ['dashboard-layout'],
    queryFn: () => api.get('/dashboard/layout').then((r) => r.data),
  })
}

export function useSaveDashboardLayout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { widgets: Record<string, unknown>[]; year: number }) =>
      api.put('/dashboard/layout', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dashboard-layout'] }),
  })
}

export function useResetDashboardLayout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post('/dashboard/layout/reset').then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['dashboard-layout'] }),
  })
}

// ── Invoices ──
interface InvoiceFilters {
  date_from?: string
  date_to?: string
  type?: string
  source?: string
  status?: string
  emittente?: string
  page?: number
  page_size?: number
}

export function useInvoices(filters: InvoiceFilters = {}) {
  return useQuery({
    queryKey: ['invoices', filters],
    queryFn: () => api.get('/invoices', { params: filters }).then((r) => r.data),
  })
}

export function useInvoice(id: string) {
  return useQuery({
    queryKey: ['invoice', id],
    queryFn: () => api.get(`/invoices/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}

export function usePendingReview(page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ['pending-review', page, pageSize],
    queryFn: () =>
      api
        .get('/invoices/pending-review', { params: { page, page_size: pageSize } })
        .then((r) => r.data),
  })
}

export function useVerifyInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ invoiceId, category, confirmed }: { invoiceId: string; category?: string; confirmed: boolean }) =>
      api.patch(`/invoices/${invoiceId}/verify`, { category, confirmed }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pending-review'] })
      qc.invalidateQueries({ queryKey: ['invoices'] })
    },
  })
}

export function useSyncCassetto() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (params?: { force?: boolean; from_date?: string }) =>
      api.post('/cassetto/sync', params ?? {}).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invoices'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
    },
  })
}

export function useSyncStatus() {
  return useQuery({
    queryKey: ['sync-status'],
    queryFn: () => api.get('/cassetto/sync/status').then((r) => r.data),
  })
}

export function useCassettoStatus() {
  return useQuery({
    queryKey: ['cassetto-status'],
    queryFn: () => api.get('/cassetto/status').then((r) => r.data),
    retry: false,
  })
}

export function useUploadInvoice() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (formData: FormData) =>
      api.post('/invoices/active', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invoices'] })
    },
  })
}

// ── Journal / Contabilita ──
interface JournalFilters {
  date_from?: string
  date_to?: string
  status?: string
  page?: number
  page_size?: number
}

export function useJournalEntries(filters: JournalFilters = {}) {
  return useQuery({
    queryKey: ['journal-entries', filters],
    queryFn: () => api.get('/accounting/journal-entries', { params: filters }).then((r) => r.data),
  })
}

export function useJournalEntry(id: string) {
  return useQuery({
    queryKey: ['journal-entry', id],
    queryFn: () => api.get(`/accounting/journal-entries/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}

export function usePianoConti() {
  return useQuery({
    queryKey: ['piano-conti'],
    queryFn: () => api.get('/accounting/chart').then((r) => r.data),
  })
}

export function useBalanceSheet(year: number) {
  return useQuery({
    queryKey: ['balance-sheet', year],
    queryFn: () => api.get('/accounting/balance-sheet', { params: { year } }).then((r) => r.data),
    enabled: !!year,
  })
}

// ── Deadlines / Scadenzario ──
export function useDeadlines(year?: number) {
  return useQuery({
    queryKey: ['deadlines', year],
    queryFn: () => api.get('/deadlines', { params: { year } }).then((r) => r.data),
  })
}

export function useFiscalAlerts(year?: number) {
  return useQuery({
    queryKey: ['fiscal-alerts', year],
    queryFn: () => api.get('/deadlines/alerts', { params: { year } }).then((r) => r.data),
  })
}

// ── Banking ──
export function useBankAccounts() {
  return useQuery({
    queryKey: ['bank-accounts'],
    queryFn: () => api.get('/bank-accounts').then((r) => r.data),
  })
}

export function useBankTransactions(accountId: string) {
  return useQuery({
    queryKey: ['bank-transactions', accountId],
    queryFn: () => api.get(`/bank-accounts/${accountId}/transactions`).then((r) => r.data),
    enabled: !!accountId,
  })
}

export function useBankBalance(accountId: string) {
  return useQuery({
    queryKey: ['bank-balance', accountId],
    queryFn: () => api.get(`/bank-accounts/${accountId}/balance`).then((r) => r.data),
    enabled: !!accountId,
  })
}

export function useConnectBank() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { iban: string; bank_name: string }) =>
      api.post('/bank-accounts/connect', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bank-accounts'] })
    },
  })
}

// ── Reconciliation ──
export function usePendingReconciliation() {
  return useQuery({
    queryKey: ['reconciliation-pending'],
    queryFn: () => api.get('/reconciliation/pending').then((r) => r.data),
  })
}

export function useMatchTransaction() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ txId, ...data }: { txId: string; invoice_id: string; match_type?: string; amount?: number }) =>
      api.post(`/reconciliation/${txId}/match`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['reconciliation-pending'] })
    },
  })
}

// ── Cashflow ──
export function useCashflow(days = 90) {
  return useQuery({
    queryKey: ['cashflow', days],
    queryFn: () => api.get('/cashflow/prediction', { params: { days } }).then((r) => r.data),
  })
}

export function useCashflowAlerts() {
  return useQuery({
    queryKey: ['cashflow-alerts'],
    queryFn: () => api.get('/cashflow/alerts').then((r) => r.data),
  })
}

// ── Expenses ──
export function useExpenses() {
  return useQuery({
    queryKey: ['expenses'],
    queryFn: () => api.get('/expenses').then((r) => r.data),
  })
}

export function useCreateExpense() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      api.post('/expenses', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['expenses'] })
    },
  })
}

export function useApproveExpense() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (expenseId: string) =>
      api.patch(`/expenses/${expenseId}/approve`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['expenses'] })
    },
  })
}

export function useRejectExpense() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ expenseId, reason }: { expenseId: string; reason: string }) =>
      api.patch(`/expenses/${expenseId}/reject`, { reason }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['expenses'] })
    },
  })
}

// ── Assets ──
export function useAssets() {
  return useQuery({
    queryKey: ['assets'],
    queryFn: () => api.get('/assets').then((r) => r.data),
  })
}

export function useAsset(id: string) {
  return useQuery({
    queryKey: ['asset', id],
    queryFn: () => api.get(`/assets/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}

// ── F24 ──
export function useF24s(year?: number) {
  return useQuery({
    queryKey: ['f24s', year],
    queryFn: () => api.get('/f24', { params: { year } }).then((r) => r.data),
  })
}

export function useF24(id: string) {
  return useQuery({
    queryKey: ['f24', id],
    queryFn: () => api.get(`/f24/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useGenerateF24() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { year: number; month?: number; quarter?: number }) =>
      api.post('/f24/generate', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['f24s'] })
    },
  })
}

export function useExportF24(id: string, format = 'pdf') {
  return useQuery({
    queryKey: ['f24-export', id, format],
    queryFn: () => api.get(`/f24/${id}/export`, { params: { format } }).then((r) => r.data),
    enabled: false,
  })
}

// ── Fiscal ──
export function useVatSettlement(year: number, quarter: number) {
  return useQuery({
    queryKey: ['vat-settlement', year, quarter],
    queryFn: () => api.get('/fiscal/vat-settlement', { params: { year, quarter } }).then((r) => r.data),
    enabled: !!year && !!quarter,
  })
}

export function useComputeVatSettlement() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { year: number; quarter: number }) =>
      api.post('/fiscal/vat-settlement/compute', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['vat-settlement'] })
    },
  })
}

export function useStampDuties(year: number, quarter: number) {
  return useQuery({
    queryKey: ['stamp-duties', year, quarter],
    queryFn: () => api.get('/fiscal/stamp-duties', { params: { year, quarter } }).then((r) => r.data),
    enabled: !!year && !!quarter,
  })
}

// ── Withholding taxes ──
export function useWithholdingTaxes() {
  return useQuery({
    queryKey: ['withholding-taxes'],
    queryFn: () => api.get('/withholding-taxes').then((r) => r.data),
  })
}

// ── CU ──
export function useCUs(year: number) {
  return useQuery({
    queryKey: ['cus', year],
    queryFn: () => api.get('/cu', { params: { year } }).then((r) => r.data),
    enabled: !!year,
  })
}

export function useGenerateCU() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (year: number) =>
      api.post(`/cu/generate/${year}`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['cus'] })
    },
  })
}

// ── Preservation ──
export function usePreservation() {
  return useQuery({
    queryKey: ['preservation'],
    queryFn: () => api.get('/preservation').then((r) => r.data),
  })
}

// ── CEO ──
export function useCeoDashboard(year?: number, month?: number) {
  return useQuery({
    queryKey: ['ceo-dashboard', year, month],
    queryFn: () => api.get('/ceo/dashboard', { params: { year, month } }).then((r) => r.data),
  })
}

export function useCeoYoY(year?: number) {
  return useQuery({
    queryKey: ['ceo-yoy', year],
    queryFn: () => api.get('/ceo/dashboard/yoy', { params: { year } }).then((r) => r.data),
  })
}

export function useCeoAlerts(year?: number) {
  return useQuery({
    queryKey: ['ceo-alerts', year],
    queryFn: () => api.get('/ceo/alerts', { params: { year } }).then((r) => r.data),
  })
}

export function useBudget(year: number) {
  return useQuery({
    queryKey: ['budget', year],
    queryFn: () => api.get('/ceo/budget', { params: { year } }).then((r) => r.data),
    enabled: !!year,
  })
}

export function useBudgetProjection(year: number) {
  return useQuery({
    queryKey: ['budget-projection', year],
    queryFn: () => api.get('/ceo/budget/projection', { params: { year } }).then((r) => r.data),
    enabled: !!year,
  })
}

export function useCreateBudget() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { year: number; month: number; entries: Record<string, unknown>[] }) =>
      api.post('/ceo/budget', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['budget'] })
    },
  })
}

// ── Reports ──
export function useReport(period: string, format: string) {
  return useQuery({
    queryKey: ['report', period, format],
    queryFn: () =>
      api.get('/reports/commercialista', { params: { period, format } }).then((r) => r.data),
    enabled: false,
  })
}

// ── Profile ──
export function useProfile() {
  return useQuery({
    queryKey: ['profile'],
    queryFn: () => api.get('/profile').then((r) => r.data),
  })
}

export function useUpdateProfile() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      api.patch('/profile', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['profile'] })
    },
  })
}

// ── Notifications ──
export function useNotificationConfigs() {
  return useQuery({
    queryKey: ['notification-configs'],
    queryFn: () => api.get('/notifications/config').then((r) => r.data),
  })
}

export function useCreateNotificationConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { channel: string; chat_id?: string; phone?: string; enabled: boolean }) =>
      api.post('/notifications/config', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['notification-configs'] })
    },
  })
}

// ── Chat ──
export function useConversations() {
  return useQuery({
    queryKey: ['conversations'],
    queryFn: () => api.get('/chat/conversations').then((r) => r.data),
  })
}

export function useConversation(id: string) {
  return useQuery({
    queryKey: ['conversation', id],
    queryFn: () => api.get(`/chat/conversations/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}

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

export function useCreateConversation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post('/chat/conversations/new').then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['conversations'] })
    },
  })
}

export function useDeleteConversation() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/chat/conversations/${id}`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['conversations'] })
    },
  })
}

// ── Agent Config ──
export function useAgentConfigs() {
  return useQuery({
    queryKey: ['agent-configs'],
    queryFn: () => api.get('/agents/config').then((r) => r.data),
  })
}

export function useUpdateAgentConfig() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ agentType, data }: { agentType: string; data: Record<string, unknown> }) =>
      api.patch(`/agents/config/${agentType}`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agent-configs'] })
    },
  })
}

export function useResetAgentConfigs() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post('/agents/config/reset').then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['agent-configs'] })
    },
  })
}

// ── LLM Settings ──
export interface LLMModel {
  id: string
  name: string
  context: number
  max_output: number
  price_input: number
  price_output: number
}

export interface LLMProvider {
  id: string
  name: string
  configured: boolean
  default_model: string
  models: LLMModel[]
}

export interface LLMSettings {
  current_provider: string
  current_model: string
  available_providers: LLMProvider[]
}

export function useLLMSettings() {
  return useQuery<LLMSettings>({
    queryKey: ['llm-settings'],
    queryFn: () => api.get('/agents/llm-settings').then((r) => r.data),
  })
}

export function useUpdateLLMSettings() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: { provider: string; model: string }) =>
      api.patch('/agents/llm-settings', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['llm-settings'] })
    },
  })
}

// ── Onboarding ──
export function useOnboardingStatus() {
  return useQuery({
    queryKey: ['onboarding-status'],
    queryFn: () => api.get('/onboarding/status').then((r) => r.data),
  })
}

export function useCompleteOnboardingStep() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ step, data }: { step: number; data?: Record<string, unknown> }) =>
      api.post(`/onboarding/step/${step}`, { data }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['onboarding-status'] })
    },
  })
}

// ── Payroll / Costi Personale ──
export function usePayrollCosts(year?: number, month?: number) {
  return useQuery({
    queryKey: ['payroll', year, month],
    queryFn: () => api.get('/payroll', { params: { year, month } }).then((r) => r.data),
  })
}

export function usePayrollSummary(year: number) {
  return useQuery({
    queryKey: ['payroll-summary', year],
    queryFn: () => api.get('/payroll/summary', { params: { year } }).then((r) => r.data),
    enabled: !!year,
  })
}

export function useCreatePayrollCost() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      api.post('/payroll', data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['payroll'] })
      qc.invalidateQueries({ queryKey: ['payroll-summary'] })
    },
  })
}

export function useImportPayrollPdf() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ file, createJournal }: { file: File; createJournal: boolean }) => {
      const formData = new FormData()
      formData.append('file', file)
      return api.post(`/payroll/import-pdf?create_journal=${createJournal}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }).then((r) => r.data)
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['payroll'] })
      qc.invalidateQueries({ queryKey: ['payroll-summary'] })
    },
  })
}

export function useDeletePayrollCost() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/payroll/${id}`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['payroll'] })
      qc.invalidateQueries({ queryKey: ['payroll-summary'] })
    },
  })
}
