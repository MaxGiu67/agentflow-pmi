import { NavLink } from 'react-router-dom'
import { LayoutDashboard, FileText, Briefcase, MessageSquare, Menu } from 'lucide-react'
import { cn } from '../../lib/utils'
import { useMyPermissions } from '../../api/hooks'

interface BottomNavProps {
  onMenuOpen: () => void
}

interface BottomTab {
  to: string
  label: string
  icon: typeof LayoutDashboard
  roles?: string[]
}

const allTabs: BottomTab[] = [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/fatture', label: 'Fatture', icon: FileText, roles: ['owner', 'admin'] },
  { to: '/crm', label: 'CRM', icon: Briefcase, roles: ['owner', 'admin', 'commerciale', 'viewer'] },
  { to: '/chat', label: 'Chat', icon: MessageSquare },
]

export default function BottomNav({ onMenuOpen }: BottomNavProps) {
  const { data: perms } = useMyPermissions()
  const userRole = perms?.role || 'viewer'

  const tabs = allTabs.filter(
    (tab) => !tab.roles || tab.roles.length === 0 || tab.roles.includes(userRole),
  )

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 border-t border-gray-200 bg-white/95 backdrop-blur-md lg:hidden"
      style={{ paddingBottom: 'env(safe-area-inset-bottom, 0px)' }}
    >
      <div className="flex items-center justify-around px-2 py-1">
        {tabs.map((tab) => (
          <NavLink
            key={tab.to}
            to={tab.to}
            className={({ isActive }) =>
              cn(
                'flex flex-col items-center gap-0.5 rounded-lg px-3 py-1.5 text-[10px] font-medium transition-colors',
                isActive
                  ? 'text-purple-600'
                  : 'text-gray-400 active:text-gray-600',
              )
            }
          >
            {({ isActive }) => (
              <>
                <tab.icon className={cn('h-5 w-5', isActive && 'stroke-[2.5]')} />
                <span>{tab.label}</span>
              </>
            )}
          </NavLink>
        ))}
        <button
          onClick={onMenuOpen}
          className="flex flex-col items-center gap-0.5 rounded-lg px-3 py-1.5 text-[10px] font-medium text-gray-400 active:text-gray-600"
        >
          <Menu className="h-5 w-5" />
          <span>Menu</span>
        </button>
      </div>
    </nav>
  )
}
