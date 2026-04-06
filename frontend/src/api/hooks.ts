import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import api from './client'

// ── Dashboard ──
export function useCrmStats() {
  return useQuery({
    queryKey: ['crm-stats'],
    queryFn: () => api.get('/dashboard/crm-stats').then((r) => r.data),
  })
}

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

export function useCreatePayrollJournal() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ costId, linee_contabili, totale_dare, totale_avere }: {
      costId: string
      linee_contabili: { account: string; description: string; debit: number; credit: number }[]
      totale_dare: number
      totale_avere: number
    }) =>
      api.post(`/payroll/${costId}/create-journal`, { linee_contabili, totale_dare, totale_avere }).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['payroll'] })
      qc.invalidateQueries({ queryKey: ['payroll-summary'] })
      qc.invalidateQueries({ queryKey: ['journal-entries'] })
    },
  })
}

// ── Home ──
export function useHomeSummary() {
  return useQuery({
    queryKey: ['home-summary'],
    queryFn: () => api.get('/home/summary').then((r) => r.data),
  })
}

// ── Completeness ──
export function useCompletenessScore() {
  return useQuery({
    queryKey: ['completeness'],
    queryFn: () => api.get('/completeness-score').then((r) => r.data),
  })
}

// ── Controller ──
export function useBudgetGenerate() {
  return useMutation({
    mutationFn: (params: { year: number; growth_rate?: number }) =>
      api
        .post(`/controller/budget/generate?year=${params.year}&growth_rate=${params.growth_rate || 0.05}`)
        .then((r) => r.data),
  })
}

export function useBudgetVsActual(year: number, month: number) {
  return useQuery({
    queryKey: ['budget-vs-actual', year, month],
    queryFn: () => api.get('/controller/budget/vs-actual', { params: { year, month } }).then((r) => r.data),
    enabled: !!year && !!month,
  })
}

export function useControllerSummary(year: number, month: number) {
  return useQuery({
    queryKey: ['controller-summary', year, month],
    queryFn: () => api.get('/controller/summary', { params: { year, month } }).then((r) => r.data),
    enabled: !!year && !!month,
  })
}

// ── Alerts ──
export function useAlertsScan() {
  return useQuery({
    queryKey: ['alerts'],
    queryFn: () => api.get('/alerts/scan').then((r) => r.data),
  })
}

// ── Corrispettivi ──
export function useCorrispettivi(year?: number, month?: number) {
  return useQuery({
    queryKey: ['corrispettivi', year, month],
    queryFn: () => api.get('/corrispettivi', { params: { year, month } }).then((r) => r.data),
  })
}

export function useImportCorrispettivo() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      return api.post('/corrispettivi/import-xml', fd).then((r) => r.data)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['corrispettivi'] }),
  })
}

// ── Import ──
export function useImportBankStatement() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ accountId, file }: { accountId: string; file: File }) => {
      const fd = new FormData()
      fd.append('file', file)
      return api.post(`/bank-accounts/${accountId}/import-statement`, fd).then((r) => r.data)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bank-transactions'] }),
  })
}

export function useImportBankCsv() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ accountId, file }: { accountId: string; file: File }) => {
      const fd = new FormData()
      fd.append('file', file)
      return api.post(`/bank-accounts/${accountId}/import-csv`, fd).then((r) => r.data)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['bank-transactions'] }),
  })
}

export function useImportBilancio() {
  return useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      return api.post('/accounting/import-bilancio', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }).then((r) => r.data)
    },
  })
}

export function useConfirmBilancio() {
  return useMutation({
    mutationFn: (data: { lines: Record<string, unknown>[]; description?: string }) =>
      api.post('/accounting/confirm-bilancio', data).then((r) => r.data),
  })
}

export function useImportF24Pdf() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      return api.post('/f24/import-pdf', fd, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }).then((r) => r.data)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['f24s'] }),
  })
}

// ── Recurring Contracts ──
export function useRecurringContracts() {
  return useQuery({
    queryKey: ['recurring'],
    queryFn: () => api.get('/recurring-contracts').then((r) => r.data),
  })
}

export function useCreateRecurring() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      api.post('/recurring-contracts', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['recurring'] }),
  })
}

export function useUpdateRecurring() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      api.put(`/recurring-contracts/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['recurring'] }),
  })
}

export function useDeleteRecurring() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/recurring-contracts/${id}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['recurring'] }),
  })
}

export function useImportRecurringPdf() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => {
      const fd = new FormData()
      fd.append('file', file)
      return api.post('/recurring-contracts/import-pdf', fd).then((r) => r.data)
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['recurring'] }),
  })
}

// ── Loans ──
export function useLoans() {
  return useQuery({
    queryKey: ['loans'],
    queryFn: () => api.get('/loans').then((r) => r.data),
  })
}

export function useCreateLoan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      api.post('/loans', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['loans'] }),
  })
}

export function useUpdateLoan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      api.put(`/loans/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['loans'] }),
  })
}

export function useDeleteLoan() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/loans/${id}`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['loans'] }),
  })
}

// ── CRM Odoo ──

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

// ── Scadenzario ──

export function useScadenzarioAttivo(stato?: string, controparte?: string) {
  const params = new URLSearchParams()
  if (stato) params.set('stato', stato)
  if (controparte) params.set('controparte', controparte)
  return useQuery({
    queryKey: ['scadenzario-attivo', stato, controparte],
    queryFn: () => api.get(`/scadenzario/attivo?${params}`).then((r) => r.data),
  })
}

export function useScadenzarioPassivo(stato?: string, controparte?: string) {
  const params = new URLSearchParams()
  if (stato) params.set('stato', stato)
  if (controparte) params.set('controparte', controparte)
  return useQuery({
    queryKey: ['scadenzario-passivo', stato, controparte],
    queryFn: () => api.get(`/scadenzario/passivo?${params}`).then((r) => r.data),
  })
}

export function useGenerateScadenze() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post('/scadenzario/generate').then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['scadenzario-attivo'] })
      qc.invalidateQueries({ queryKey: ['scadenzario-passivo'] })
    },
  })
}

export function useChiudiScadenza() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: { id: string; importo_pagato: number; data_pagamento: string }) =>
      api.post(`/scadenzario/${id}/chiudi`, data).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['scadenzario-attivo'] })
      qc.invalidateQueries({ queryKey: ['scadenzario-passivo'] })
    },
  })
}

export function useSegnaInsoluto() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.post(`/scadenzario/${id}/insoluto`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scadenzario-attivo'] }),
  })
}

export function useCashFlow(giorni: number = 30) {
  return useQuery({
    queryKey: ['cash-flow-scadenzario', giorni],
    queryFn: () => api.get(`/scadenzario/cash-flow?giorni=${giorni}`).then((r) => r.data),
  })
}

export function useCashFlowPerBanca(giorni: number = 30) {
  return useQuery({
    queryKey: ['cash-flow-per-banca', giorni],
    queryFn: () => api.get(`/scadenzario/cash-flow/per-banca?giorni=${giorni}`).then((r) => r.data),
  })
}

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

export function useSendEmail() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/email/send', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['email-sends'] }),
  })
}

export function useEmailSends(contactId?: string) {
  const params = contactId ? `?contact_id=${contactId}` : ''
  return useQuery({
    queryKey: ['email-sends', contactId],
    queryFn: () => api.get(`/email/sends${params}`).then((r) => r.data),
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

export function useFidi() {
  return useQuery({
    queryKey: ['fidi'],
    queryFn: () => api.get('/fidi').then((r) => r.data),
  })
}

export function useCreateFido() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) => api.post('/fidi', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['fidi'] }),
  })
}

export function useAnticipaFattura() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (scadenzaId: string) => api.post(`/scadenzario/${scadenzaId}/anticipa`).then((r) => r.data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['scadenzario-attivo'] })
      qc.invalidateQueries({ queryKey: ['fidi'] })
    },
  })
}

export function useConfrontaAnticipo(scadenzaId: string) {
  return useQuery({
    queryKey: ['confronta-anticipo', scadenzaId],
    queryFn: () => api.get(`/scadenzario/${scadenzaId}/confronta-anticipi`).then((r) => r.data),
    enabled: !!scadenzaId,
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

// ── User Management ──

export function useTeamUsers() {
  return useQuery({
    queryKey: ['team-users'],
    queryFn: () => api.get('/users').then((r) => r.data),
  })
}

export function useInviteUser() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: Record<string, unknown>) =>
      api.post('/users/invite', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['team-users'] }),
  })
}

export function useUpdateUserRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, role }: { userId: string; role: string }) =>
      api.patch(`/users/${userId}/role`, { role }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['team-users'] }),
  })
}

export function useUpdateUserCrmRole() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, crm_role_id }: { userId: string; crm_role_id: string | null }) =>
      api.patch(`/users/${userId}/crm-role`, { crm_role_id }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['team-users'] }),
  })
}

export function useToggleUserActive() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) =>
      api.post(`/users/${userId}/toggle-active`).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['team-users'] }),
  })
}

export function useMyPermissions() {
  return useQuery({
    queryKey: ['my-permissions'],
    queryFn: () => api.get('/users/me/permissions').then((r) => r.data),
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
    enabled: !!(contactId || dealId),
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

// ── Social Selling: Pipeline Stages ──
export function useSocialPipelineStages() {
  return useQuery({
    queryKey: ['social-pipeline-stages'],
    queryFn: () => api.get('/social/pipeline/stages').then((r) => r.data),
  })
}

// ── Calendar (US-151→US-155) ──
export function useMicrosoftCalendarStatus() {
  return useQuery({
    queryKey: ['ms-calendar-status'],
    queryFn: () => api.get('/calendar/microsoft/status').then((r) => r.data),
  })
}

export function useMicrosoftConnect() {
  return useMutation({
    mutationFn: () => api.get('/calendar/microsoft/connect').then((r) => r.data),
  })
}

export function useMicrosoftDisconnect() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => api.post('/calendar/microsoft/disconnect').then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ms-calendar-status'] }),
  })
}

export function useCalendlyUrl() {
  return useQuery({
    queryKey: ['calendly-url'],
    queryFn: () => api.get('/calendar/calendly').then((r) => r.data),
  })
}

export function useUpdateCalendlyUrl() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (url: string) => api.patch('/calendar/calendly', { calendly_url: url }).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['calendly-url'] }),
  })
}

// ── Pipeline Templates (Pivot 9) ──
export function usePipelineTemplates() {
  return useQuery({
    queryKey: ['pipeline-templates'],
    queryFn: () => api.get('/pipeline-templates').then((r) => r.data),
  })
}

// ── Resources (Pivot 9) ──
export function useResources(skill = '', seniority = '') {
  return useQuery({
    queryKey: ['resources', skill, seniority],
    queryFn: () => api.get('/resources', { params: { skill, seniority } }).then((r) => r.data),
  })
}
export function useCreateResource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: any) => api.post('/resources', data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['resources'] }),
  })
}
export function useUpdateResource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...data }: any) => api.patch(`/resources/${id}`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['resources'] }),
  })
}
export function useAddResourceSkill() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ resourceId, ...data }: any) => api.post(`/resources/${resourceId}/skills`, data).then((r) => r.data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['resources'] }),
  })
}
export function useResourceMatch(techStack = '', seniority = '') {
  return useQuery({
    queryKey: ['resource-match', techStack, seniority],
    queryFn: () => api.get('/resources/match', { params: { tech_stack: techStack, seniority } }).then((r) => r.data),
    enabled: !!techStack,
  })
}
export function useResourceBench(days = 30) {
  return useQuery({
    queryKey: ['resource-bench', days],
    queryFn: () => api.get('/resources/bench', { params: { days } }).then((r) => r.data),
  })
}

// ── Elevia (Pivot 9) ──
export function useEleviaUseCases() {
  return useQuery({
    queryKey: ['elevia-use-cases'],
    queryFn: () => api.get('/elevia/use-cases').then((r) => r.data),
  })
}
export function useEleviaScoreProspect() {
  return useMutation({
    mutationFn: (data: any) => api.post('/elevia/score-prospect', data).then((r) => r.data),
  })
}
export function useEleviaDiscoveryBrief(ateco: string) {
  return useQuery({
    queryKey: ['elevia-brief', ateco],
    queryFn: () => api.get('/elevia/discovery-brief', { params: { ateco } }).then((r) => r.data),
    enabled: !!ateco,
  })
}
export function useEleviaRoi(useCaseCount: number) {
  return useQuery({
    queryKey: ['elevia-roi', useCaseCount],
    queryFn: () => api.get('/elevia/roi', { params: { use_case_count: useCaseCount } }).then((r) => r.data),
    enabled: useCaseCount > 0,
  })
}
