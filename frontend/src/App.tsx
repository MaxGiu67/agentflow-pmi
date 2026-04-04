import { lazy } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import ProtectedRoute from './components/ui/ProtectedRoute'
import AppLayout from './components/layout/AppLayout'
import InstallPrompt from './components/pwa/InstallPrompt'
import OfflineIndicator from './components/pwa/OfflineIndicator'

// Public pages (eagerly loaded)
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage'
import ResetPasswordPage from './pages/auth/ResetPasswordPage'
import VerifyEmailPage from './pages/auth/VerifyEmailPage'

// Lazy-loaded pages (code splitting)
const OnboardingPage = lazy(() => import('./pages/onboarding/OnboardingPage'))
const DashboardPage = lazy(() => import('./pages/DashboardPage'))
const HomePage = lazy(() => import('./pages/HomePage'))
const ScadenzarioPage = lazy(() => import('./pages/ScadenzarioPage'))
const ReportPage = lazy(() => import('./pages/ReportPage'))
const ImpostazioniPage = lazy(() => import('./pages/ImpostazioniPage'))
const PuzzleDashboard = lazy(() => import('./pages/PuzzleDashboard'))
const CompletenessPage = lazy(() => import('./pages/onboarding/CompletenessPage'))
const ImportWizardPage = lazy(() => import('./pages/import/ImportWizardPage'))
const ControllerPage = lazy(() => import('./pages/controller/ControllerPage'))
const AlertsPage = lazy(() => import('./pages/alerts/AlertsPage'))
const CorrispettiviPage = lazy(() => import('./pages/corrispettivi/CorrispettiviPage'))
const RecurringPage = lazy(() => import('./pages/recurring/RecurringPage'))
const LoansPage = lazy(() => import('./pages/loans/LoansPage'))
const FattureListPage = lazy(() => import('./pages/fatture/FattureListPage'))
const FatturaDetailPage = lazy(() => import('./pages/fatture/FatturaDetailPage'))
const CreateInvoicePage = lazy(() => import('./pages/fatture/CreateInvoicePage'))
const VerificaPage = lazy(() => import('./pages/fatture/VerificaPage'))
const UploadPage = lazy(() => import('./pages/fatture/UploadPage'))
const ScrittureListPage = lazy(() => import('./pages/contabilita/ScrittureListPage'))
const ScritturaDetailPage = lazy(() => import('./pages/contabilita/ScritturaDetailPage'))
const PianoContiPage = lazy(() => import('./pages/contabilita/PianoContiPage'))
const BilancioPage = lazy(() => import('./pages/contabilita/BilancioPage'))
const FiscoIndexPage = lazy(() => import('./pages/fisco/FiscoIndexPage'))
const F24Page = lazy(() => import('./pages/fisco/F24Page'))
const LiquidazionePage = lazy(() => import('./pages/fisco/LiquidazionePage'))
const RitenutePage = lazy(() => import('./pages/fisco/RitenutePage'))
const CUPage = lazy(() => import('./pages/fisco/CUPage'))
const ConservazionePage = lazy(() => import('./pages/fisco/ConservazionePage'))
const BolloPage = lazy(() => import('./pages/fisco/BolloPage'))
const BankAccountsPage = lazy(() => import('./pages/banca/BankAccountsPage'))
const MovimentiPage = lazy(() => import('./pages/banca/MovimentiPage'))
const RiconciliazionePage = lazy(() => import('./pages/banca/RiconciliazionePage'))
const CashFlowPage = lazy(() => import('./pages/banca/CashFlowPage'))
const SpesePage = lazy(() => import('./pages/spese/SpesePage'))
const CespitiPage = lazy(() => import('./pages/cespiti/CespitiPage'))
const CeoDashboardPage = lazy(() => import('./pages/ceo/CeoDashboardPage'))
const BudgetPage = lazy(() => import('./pages/ceo/BudgetPage'))
const BudgetListPage = lazy(() => import('./pages/budget/BudgetListPage'))
const BudgetWizardPage = lazy(() => import('./pages/budget/BudgetWizardPage'))
const ChatPage = lazy(() => import('./pages/chat/ChatPage'))
const AgentConfigPage = lazy(() => import('./pages/impostazioni/AgentConfigPage'))
const PayrollPage = lazy(() => import('./pages/payroll/PayrollPage'))
const GestioneImportPage = lazy(() => import('./pages/payroll/GestioneImportPage'))
const CrmPipelinePage = lazy(() => import('./pages/crm/CrmPipelinePage'))
const CrmDealDetailPage = lazy(() => import('./pages/crm/CrmDealDetailPage'))
const CrmContactsPage = lazy(() => import('./pages/crm/CrmContactsPage'))
const EmailTemplatesPage = lazy(() => import('./pages/email/EmailTemplatesPage'))
const EmailAnalyticsPage = lazy(() => import('./pages/email/EmailAnalyticsPage'))
const EmailSequencesPage = lazy(() => import('./pages/email/EmailSequencesPage'))
const FidiPage = lazy(() => import('./pages/banca/FidiPage'))
const UsersPage = lazy(() => import('./pages/impostazioni/UsersPage'))
const IntegrazioniPage = lazy(() => import('./pages/impostazioni/IntegrazioniPage'))
const ChatTestPage = lazy(() => import('./pages/ChatTestPage'))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <OfflineIndicator />
      <InstallPrompt />
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/reset-password" element={<ResetPasswordPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />

          {/* Protected routes */}
          <Route element={<ProtectedRoute />}>
            {/* Onboarding (no sidebar layout) */}
            <Route path="/onboarding" element={<OnboardingPage />} />

            {/* Main app layout */}
            <Route element={<AppLayout />}>
              <Route path="/home" element={<HomePage />} />
              <Route path="/dashboard" element={<DashboardPage />} />

              {/* Chat */}
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/chat/:conversationId" element={<ChatPage />} />

              {/* Fatture */}
              <Route path="/fatture" element={<FattureListPage />} />
              <Route path="/fatture/nuova" element={<CreateInvoicePage />} />
              <Route path="/fatture/verifica" element={<VerificaPage />} />
              <Route path="/fatture/upload" element={<UploadPage />} />
              <Route path="/fatture/:id" element={<FatturaDetailPage />} />

              {/* Contabilita */}
              <Route path="/contabilita" element={<ScrittureListPage />} />
              <Route path="/contabilita/piano-conti" element={<PianoContiPage />} />
              <Route path="/contabilita/bilancio" element={<BilancioPage />} />
              <Route path="/contabilita/:id" element={<ScritturaDetailPage />} />

              {/* Spese */}
              <Route path="/spese" element={<SpesePage />} />

              {/* Cespiti */}
              <Route path="/cespiti" element={<CespitiPage />} />

              {/* Banca */}
              <Route path="/banca" element={<BankAccountsPage />} />
              <Route path="/banca/movimenti/:accountId" element={<MovimentiPage />} />
              <Route path="/banca/riconciliazione" element={<RiconciliazionePage />} />
              <Route path="/banca/cashflow" element={<CashFlowPage />} />
              <Route path="/banca/fidi" element={<FidiPage />} />

              {/* Scadenzario */}
              <Route path="/scadenze" element={<ScadenzarioPage />} />

              {/* Fisco */}
              <Route path="/fisco" element={<FiscoIndexPage />} />
              <Route path="/fisco/f24" element={<F24Page />} />
              <Route path="/fisco/liquidazione" element={<LiquidazionePage />} />
              <Route path="/fisco/ritenute" element={<RitenutePage />} />
              <Route path="/fisco/cu" element={<CUPage />} />
              <Route path="/fisco/conservazione" element={<ConservazionePage />} />
              <Route path="/fisco/bollo" element={<BolloPage />} />

              {/* CEO */}
              <Route path="/ceo" element={<CeoDashboardPage />} />
              <Route path="/ceo/budget" element={<BudgetPage />} />
              <Route path="/budgets" element={<BudgetListPage />} />
              <Route path="/budget/wizard" element={<BudgetWizardPage />} />

              {/* Report */}
              <Route path="/report" element={<ReportPage />} />

              {/* Impostazioni */}
              <Route path="/impostazioni" element={<ImpostazioniPage />} />
              <Route path="/impostazioni/agenti" element={<AgentConfigPage />} />
              <Route path="/impostazioni/utenti" element={<UsersPage />} />
              <Route path="/impostazioni/integrazioni" element={<IntegrazioniPage />} />

              {/* Payroll */}
              <Route path="/personale" element={<PayrollPage />} />
              <Route path="/personale/gestione-import" element={<GestioneImportPage />} />

              {/* Pivot 5 */}
              <Route path="/setup" element={<PuzzleDashboard />} />
              <Route path="/setup/completeness" element={<CompletenessPage />} />
              <Route path="/import" element={<ImportWizardPage />} />
              <Route path="/controller" element={<ControllerPage />} />
              <Route path="/alert" element={<AlertsPage />} />
              <Route path="/corrispettivi" element={<CorrispettiviPage />} />
              <Route path="/contratti" element={<RecurringPage />} />
              <Route path="/finanziamenti" element={<LoansPage />} />

              {/* CRM */}
              <Route path="/crm" element={<CrmPipelinePage />} />
              <Route path="/crm/deals/:dealId" element={<CrmDealDetailPage />} />
              <Route path="/crm/contatti" element={<CrmContactsPage />} />

              {/* Email Marketing */}
              <Route path="/email/templates" element={<EmailTemplatesPage />} />
              <Route path="/email/analytics" element={<EmailAnalyticsPage />} />
              <Route path="/email/sequenze" element={<EmailSequencesPage />} />

              {/* Test */}
              <Route path="/test/chatbot" element={<ChatTestPage />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
