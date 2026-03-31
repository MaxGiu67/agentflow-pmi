import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

import ProtectedRoute from './components/ui/ProtectedRoute'
import AppLayout from './components/layout/AppLayout'

// Auth pages
import LoginPage from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'
import ForgotPasswordPage from './pages/auth/ForgotPasswordPage'
import VerifyEmailPage from './pages/auth/VerifyEmailPage'

// Onboarding
import OnboardingPage from './pages/onboarding/OnboardingPage'

// Main pages
import DashboardPage from './pages/DashboardPage'
import HomePage from './pages/HomePage'
import ScadenzarioPage from './pages/ScadenzarioPage'
import ReportPage from './pages/ReportPage'
import ImpostazioniPage from './pages/ImpostazioniPage'

// Puzzle Dashboard
import PuzzleDashboard from './pages/PuzzleDashboard'

// Pivot 5 pages
import CompletenessPage from './pages/onboarding/CompletenessPage'
import ImportWizardPage from './pages/import/ImportWizardPage'
import ControllerPage from './pages/controller/ControllerPage'
import AlertsPage from './pages/alerts/AlertsPage'
import CorrispettiviPage from './pages/corrispettivi/CorrispettiviPage'
import RecurringPage from './pages/recurring/RecurringPage'
import LoansPage from './pages/loans/LoansPage'

// Fatture
import FattureListPage from './pages/fatture/FattureListPage'
import FatturaDetailPage from './pages/fatture/FatturaDetailPage'
import VerificaPage from './pages/fatture/VerificaPage'
import UploadPage from './pages/fatture/UploadPage'

// Contabilita
import ScrittureListPage from './pages/contabilita/ScrittureListPage'
import ScritturaDetailPage from './pages/contabilita/ScritturaDetailPage'
import PianoContiPage from './pages/contabilita/PianoContiPage'
import BilancioPage from './pages/contabilita/BilancioPage'

// Fisco
import FiscoIndexPage from './pages/fisco/FiscoIndexPage'
import F24Page from './pages/fisco/F24Page'
import LiquidazionePage from './pages/fisco/LiquidazionePage'
import RitenutePage from './pages/fisco/RitenutePage'
import CUPage from './pages/fisco/CUPage'
import ConservazionePage from './pages/fisco/ConservazionePage'
import BolloPage from './pages/fisco/BolloPage'

// Banca
import BankAccountsPage from './pages/banca/BankAccountsPage'
import MovimentiPage from './pages/banca/MovimentiPage'
import RiconciliazionePage from './pages/banca/RiconciliazionePage'
import CashFlowPage from './pages/banca/CashFlowPage'

// Spese
import SpesePage from './pages/spese/SpesePage'

// Cespiti
import CespitiPage from './pages/cespiti/CespitiPage'

// CEO
import CeoDashboardPage from './pages/ceo/CeoDashboardPage'
import BudgetPage from './pages/ceo/BudgetPage'

// Budget Wizard
import BudgetWizardPage from './pages/budget/BudgetWizardPage'

// Chat
import ChatPage from './pages/chat/ChatPage'

// Agent Config
import AgentConfigPage from './pages/impostazioni/AgentConfigPage'

// Payroll
import PayrollPage from './pages/payroll/PayrollPage'
import GestioneImportPage from './pages/payroll/GestioneImportPage'

// Test
import ChatTestPage from './pages/ChatTestPage'

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
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/forgot-password" element={<ForgotPasswordPage />} />
          <Route path="/verify-email" element={<VerifyEmailPage />} />

          {/* Protected routes */}
          <Route element={<ProtectedRoute />}>
            {/* Onboarding (no sidebar layout) */}
            <Route path="/onboarding" element={<OnboardingPage />} />

            {/* Main app layout */}
            <Route element={<AppLayout />}>
              <Route path="/" element={<HomePage />} />
              <Route path="/dashboard" element={<DashboardPage />} />

              {/* Chat */}
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/chat/:conversationId" element={<ChatPage />} />

              {/* Fatture */}
              <Route path="/fatture" element={<FattureListPage />} />
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
              <Route path="/budget/wizard" element={<BudgetWizardPage />} />

              {/* Report */}
              <Route path="/report" element={<ReportPage />} />

              {/* Impostazioni */}
              <Route path="/impostazioni" element={<ImpostazioniPage />} />
              <Route path="/impostazioni/agenti" element={<AgentConfigPage />} />

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

              {/* Test */}
              <Route path="/test/chatbot" element={<ChatTestPage />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
