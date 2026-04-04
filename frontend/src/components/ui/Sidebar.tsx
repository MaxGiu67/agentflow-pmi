import { NavLink } from 'react-router-dom'
import type { LucideIcon } from 'lucide-react'
import {
  LayoutDashboard,
  MessageSquare,
  FileText,
  Receipt,
  Landmark,
  CalendarClock,
  Calculator,
  BarChart3,
  Settings,
  Users,
  X,
  Upload,
  Puzzle,
  Target,
  CreditCard,
  Briefcase,
  Mail,
  Zap,
  Shield,
} from 'lucide-react'
import { cn } from '../../lib/utils'

interface SidebarProps {
  open: boolean
  onClose: () => void
}

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
}

interface NavSection {
  title: string
  items: NavItem[]
}

const navSections: NavSection[] = [
  {
    title: 'Principale',
    items: [
      { to: '/setup', label: 'Setup', icon: Puzzle },
      { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/budgets', label: 'Budget', icon: Target },
    ],
  },
  {
    title: 'Operativo',
    items: [
      { to: '/fatture', label: 'Fatture', icon: FileText },
      { to: '/banca', label: 'Banca', icon: Landmark },
      { to: '/personale', label: 'Personale', icon: Users },
      { to: '/spese', label: 'Spese', icon: CreditCard },
      { to: '/corrispettivi', label: 'Corrispettivi', icon: Receipt },
    ],
  },
  {
    title: 'Commerciale',
    items: [
      { to: '/crm', label: 'Pipeline CRM', icon: Briefcase },
      { to: '/crm/contatti', label: 'Contatti', icon: Users },
      { to: '/email/templates', label: 'Email Template', icon: Mail },
      { to: '/email/sequenze', label: 'Sequenze', icon: Zap },
      { to: '/email/analytics', label: 'Email Stats', icon: BarChart3 },
    ],
  },
  {
    title: 'Gestione',
    items: [
      { to: '/import', label: 'Import', icon: Upload },
      { to: '/scadenze', label: 'Scadenzario', icon: CalendarClock },
      { to: '/banca/fidi', label: 'Fidi Bancari', icon: Shield },
      { to: '/fisco', label: 'Fisco', icon: Calculator },
    ],
  },
  {
    title: 'Sistema',
    items: [
      { to: '/chat', label: 'Chat', icon: MessageSquare },
      { to: '/report', label: 'Report', icon: BarChart3 },
      { to: '/impostazioni/utenti', label: 'Utenti', icon: Users },
      { to: '/impostazioni/integrazioni', label: 'Integrazioni', icon: Settings },
    ],
  },
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
          open ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        {/* Header */}
        <div className="flex h-16 items-center justify-between border-b border-gray-200 px-4">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 text-sm font-bold text-white">
              AF
            </div>
            <span className="text-lg font-semibold text-gray-900">AgentFlow</span>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 lg:hidden">
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 overflow-y-auto px-3 py-4">
          {navSections.map((section) => (
            <div key={section.title} className="mb-4">
              <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-wider text-gray-400">
                {section.title}
              </p>
              <ul className="space-y-0.5">
                {section.items.map((item) => (
                  <li key={item.to}>
                    <NavLink
                      to={item.to}
                      onClick={onClose}
                      className={({ isActive }) =>
                        cn(
                          'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                          isActive
                            ? 'bg-blue-50 text-blue-700'
                            : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900',
                        )
                      }
                    >
                      <item.icon className="h-4.5 w-4.5 shrink-0" />
                      {item.label}
                    </NavLink>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </nav>

        {/* Footer */}
        <div className="border-t border-gray-200 p-4">
          <p className="text-xs text-gray-400">AgentFlow PMI v0.1.0</p>
        </div>
      </aside>
    </>
  )
}
