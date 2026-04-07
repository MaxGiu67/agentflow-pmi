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
  Globe,
  Activity,
  Package,
  ShieldCheck,
  FileSearch,
  Trophy,
  DollarSign,
  UserCircle,
  Link2,
} from 'lucide-react'
import { cn } from '../../lib/utils'
import { useMyPermissions } from '../../api/hooks'

interface SidebarProps {
  open: boolean
  onClose: () => void
}

interface NavItem {
  to: string
  label: string
  icon: LucideIcon
  /** Roles that can see this item. Empty = everyone. */
  roles?: string[]
}

interface NavSection {
  title: string
  items: NavItem[]
}

/**
 * Role visibility rules:
 * - owner/admin: see everything
 * - commerciale: CRM, email, chat, dashboard
 * - viewer: dashboard, CRM (read), report, chat
 *
 * If `roles` is omitted or empty, item is visible to ALL roles.
 * If `roles` is specified, only those roles see it.
 */
const navSections: NavSection[] = [
  {
    title: 'Principale',
    items: [
      { to: '/setup', label: 'Setup', icon: Puzzle, roles: ['owner', 'admin'] },
      { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/budgets', label: 'Budget', icon: Target, roles: ['owner', 'admin'] },
    ],
  },
  {
    title: 'Operativo',
    items: [
      { to: '/fatture', label: 'Fatture', icon: FileText, roles: ['owner', 'admin'] },
      { to: '/banca', label: 'Banca', icon: Landmark, roles: ['owner', 'admin'] },
      { to: '/personale', label: 'Personale', icon: Users, roles: ['owner', 'admin'] },
      { to: '/spese', label: 'Spese', icon: CreditCard, roles: ['owner', 'admin'] },
      { to: '/corrispettivi', label: 'Corrispettivi', icon: Receipt, roles: ['owner', 'admin'] },
    ],
  },
  {
    title: 'Commerciale',
    items: [
      { to: '/crm', label: 'Pipeline CRM', icon: Briefcase, roles: ['owner', 'admin', 'commerciale', 'viewer'] },
      { to: '/crm/contatti', label: 'Contatti', icon: Users, roles: ['owner', 'admin', 'commerciale', 'viewer'] },
      { to: '/crm/calendario', label: 'Calendario', icon: CalendarClock, roles: ['owner', 'admin', 'commerciale'] },
      { to: '/email/templates', label: 'Email Template', icon: Mail, roles: ['owner', 'admin', 'commerciale'] },
      { to: '/email/sequenze', label: 'Sequenze', icon: Zap, roles: ['owner', 'admin', 'commerciale'] },
      { to: '/email/analytics', label: 'Email Stats', icon: BarChart3, roles: ['owner', 'admin', 'commerciale'] },
      { to: '/risorse', label: 'Risorse', icon: Users, roles: ['owner', 'admin', 'commerciale'] },
      { to: '/elevia/use-cases', label: 'Use Case Elevia', icon: Target, roles: ['owner', 'admin', 'commerciale'] },
      { to: '/crm/scorecard', label: 'Scorecard', icon: Trophy, roles: ['owner', 'admin', 'commerciale'] },
      { to: '/crm/compensi', label: 'Compensi', icon: DollarSign, roles: ['owner', 'admin'] },
    ],
  },
  {
    title: 'Gestione',
    items: [
      { to: '/import', label: 'Import', icon: Upload, roles: ['owner', 'admin'] },
      { to: '/scadenze', label: 'Scadenzario', icon: CalendarClock, roles: ['owner', 'admin'] },
      { to: '/banca/fidi', label: 'Fidi Bancari', icon: Shield, roles: ['owner', 'admin'] },
      { to: '/fisco', label: 'Fisco', icon: Calculator, roles: ['owner', 'admin'] },
    ],
  },
  {
    title: 'Sistema',
    items: [
      { to: '/profilo', label: 'Il mio profilo', icon: UserCircle },
      { to: '/chat', label: 'Chat', icon: MessageSquare },
      { to: '/report', label: 'Report', icon: BarChart3, roles: ['owner', 'admin', 'viewer'] },
      { to: '/impostazioni/utenti', label: 'Utenti', icon: Users, roles: ['owner', 'admin'] },
      { to: '/impostazioni/ruoli', label: 'Ruoli', icon: ShieldCheck, roles: ['owner', 'admin'] },
      { to: '/impostazioni/pipeline-templates', label: 'Pipeline Templates', icon: Target, roles: ['owner', 'admin'] },
      { to: '/impostazioni/origini', label: 'Origini', icon: Globe, roles: ['owner', 'admin'] },
      { to: '/impostazioni/tipi-attivita', label: 'Tipi Attivita', icon: Activity, roles: ['owner', 'admin'] },
      { to: '/impostazioni/prodotti', label: 'Prodotti', icon: Package, roles: ['owner', 'admin'] },
      { to: '/impostazioni/portal', label: 'Portal', icon: Link2, roles: ['owner', 'admin'] },
      { to: '/impostazioni/audit', label: 'Audit Log', icon: FileSearch, roles: ['owner', 'admin'] },
    ],
  },
]

export default function Sidebar({ open, onClose }: SidebarProps) {
  const { data: perms } = useMyPermissions()
  const userRole = perms?.role || 'viewer'

  // Filter sections: keep only items visible to the current role
  const filteredSections = navSections
    .map((section) => ({
      ...section,
      items: section.items.filter(
        (item) => !item.roles || item.roles.length === 0 || item.roles.includes(userRole),
      ),
    }))
    .filter((section) => section.items.length > 0)

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
          {filteredSections.map((section) => (
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
