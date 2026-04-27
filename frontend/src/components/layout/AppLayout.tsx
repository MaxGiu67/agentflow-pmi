import { useState, useEffect, Suspense } from 'react'
import { Outlet, useLocation } from 'react-router-dom'
import { Menu, LogOut, User, Building2 } from 'lucide-react'
import Sidebar from '../ui/Sidebar'
import BottomNav from '../ui/BottomNav'
import ErrorBoundary from '../ui/ErrorBoundary'
import { SkeletonPage } from '../ui/Skeleton'
import ChatbotFloating from '../chat/ChatbotFloating'
import { useAuthStore } from '../../store/auth'

// ChatbotFloating visible on all main app routes
const CHATBOT_ROUTES = ['/dashboard', '/chat', '/', '/crm', '/fatture', '/banca', '/contabilita', '/scadenzario', '/fisco', '/ceo', '/report', '/spese', '/cespiti', '/personale', '/budget', '/impostazioni', '/email', '/elevia']

export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { user, logout, loadProfile } = useAuthStore()
  const location = useLocation()

  const showChatbot = CHATBOT_ROUTES.some(
    (r) => location.pathname === r || location.pathname.startsWith('/chat')
  )

  useEffect(() => {
    loadProfile().catch(() => {})
  }, [loadProfile])

  return (
    <div className="flex h-[100dvh] bg-gray-50">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header
          className="flex h-14 items-center justify-between border-b border-gray-200 bg-white px-4 lg:h-16 lg:px-6"
          style={{ paddingTop: 'env(safe-area-inset-top, 0px)' }}
        >
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-gray-500 hover:text-gray-700 lg:hidden"
            aria-label="Apri menu"
          >
            <Menu className="h-5 w-5" />
          </button>

          {/* Company info — visible across all pages */}
          {user?.azienda_nome ? (
            <div className="hidden items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 md:flex">
              <Building2 className="h-4 w-4 text-purple-600" />
              <div className="leading-tight">
                <div className="text-sm font-semibold text-gray-900">
                  {user.azienda_nome}
                  {user.tipo_azienda && (
                    <span className="ml-1 text-xs font-normal uppercase text-gray-500">
                      {user.tipo_azienda}
                    </span>
                  )}
                </div>
                {user.piva && (
                  <div className="text-[10px] uppercase tracking-wide text-gray-500">
                    P.IVA {user.piva}
                  </div>
                )}
              </div>
            </div>
          ) : (
            <span className="text-sm font-semibold text-gray-800">AgentFlow</span>
          )}

          <span className="text-sm font-semibold text-gray-800 md:hidden">
            {user?.azienda_nome || 'AgentFlow'}
          </span>

          <div className="flex items-center gap-3">
            <div className="hidden items-center gap-2 text-sm text-gray-600 sm:flex">
              <User className="h-4 w-4" />
              <span className="max-w-32 truncate">{user?.name ?? user?.email ?? 'Utente'}</span>
            </div>
            <button
              onClick={logout}
              className="flex items-center gap-1 rounded-lg px-2 py-1.5 text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-900"
              aria-label="Esci"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Esci</span>
            </button>
          </div>
        </header>

        {/* Main content — extra padding bottom for bottom nav on mobile */}
        <main className={`flex-1 overflow-y-auto p-3 sm:p-4 lg:p-6 ${
          showChatbot ? 'pb-36 lg:pb-28' : 'pb-20 lg:pb-6'
        }`}>
          <ErrorBoundary>
            <Suspense fallback={<SkeletonPage />}>
              <Outlet />
            </Suspense>
          </ErrorBoundary>
        </main>
      </div>

      {/* Bottom navigation — mobile only */}
      <BottomNav onMenuOpen={() => setSidebarOpen(true)} />

      {/* Floating chatbot — only on Dashboard and Chat */}
      {showChatbot && <ChatbotFloating />}
    </div>
  )
}
