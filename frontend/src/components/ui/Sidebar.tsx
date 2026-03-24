import { NavLink } from 'react-router-dom'
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  BookOpen,
  Receipt,
  Landmark,
  CalendarClock,
  Calculator,
  BarChart3,
  PieChart,
  Settings,
  Package,
  X,
} from 'lucide-react'
import { cn } from '../../lib/utils'

interface SidebarProps {
  open: boolean
  onClose: () => void
}

const navItems = [
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/fatture', label: 'Fatture', icon: FileText },
  { to: '/contabilita', label: 'Contabilita', icon: BookOpen },
  { to: '/spese', label: 'Note Spese', icon: Receipt },
  { to: '/cespiti', label: 'Cespiti', icon: Package },
  { to: '/banca', label: 'Banca', icon: Landmark },
  { to: '/scadenze', label: 'Scadenzario', icon: CalendarClock },
  { to: '/fisco', label: 'Fisco', icon: Calculator },
  { to: '/ceo', label: 'Cruscotto CEO', icon: PieChart },
  { to: '/report', label: 'Report', icon: BarChart3 },
  { to: '/impostazioni', label: 'Impostazioni', icon: Settings },
]

export default function Sidebar({ open, onClose }: SidebarProps) {
  return (
    <>
      {/* Mobile overlay */}
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/30 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-gray-200 bg-white transition-transform lg:static lg:translate-x-0',
          open ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Header */}
        <div className="flex h-16 items-center justify-between border-b border-gray-200 px-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white">
              CB
            </div>
            <span className="text-lg font-semibold text-gray-900">AgentFlow</span>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 lg:hidden">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-4">
          <ul className="space-y-1">
            {navItems.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === '/'}
                  onClick={onClose}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-blue-50 text-blue-700'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                    )
                  }
                >
                  <item.icon className="h-5 w-5 shrink-0" />
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>

        {/* Footer */}
        <div className="border-t border-gray-200 p-4">
          <p className="text-xs text-gray-400">AgentFlow PMI v0.1.0</p>
        </div>
      </aside>
    </>
  )
}
