import { useState, useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { Menu, LogOut, User } from 'lucide-react'
import Sidebar from '../ui/Sidebar'
import ChatbotFloating from '../chat/ChatbotFloating'
import { useAuthStore } from '../../store/auth'

export default function AppLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const { user, logout, loadProfile } = useAuthStore()

  useEffect(() => {
    loadProfile().catch(() => {
      // Profile load failed - user might need to complete onboarding
    })
  }, [loadProfile])

  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top bar */}
        <header className="flex h-16 items-center justify-between border-b border-gray-200 bg-white px-4 lg:px-6">
          <button
            onClick={() => setSidebarOpen(true)}
            className="text-gray-500 hover:text-gray-700 lg:hidden"
          >
            <Menu className="h-6 w-6" />
          </button>

          <div className="hidden lg:block" />

          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <User className="h-4 w-4" />
              <span>{user?.name ?? user?.email ?? 'Utente'}</span>
            </div>
            <button
              onClick={logout}
              className="flex items-center gap-1 rounded-lg px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 hover:text-gray-900"
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Esci</span>
            </button>
          </div>
        </header>

        {/* Main content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>

      {/* Floating chatbot */}
      <ChatbotFloating />
    </div>
  )
}
