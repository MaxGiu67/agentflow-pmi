import {
  AlertTriangle,
  AlertCircle,
  Info,
  Send,
  Search,
  Bell,
} from 'lucide-react'
import { useAlertsScan } from '../../api/hooks'
import PageHeader from '../../components/ui/PageHeader'
import Card from '../../components/ui/Card'
import LoadingSpinner from '../../components/ui/LoadingSpinner'
import EmptyState from '../../components/ui/EmptyState'

interface AlertItem {
  id: string
  title: string
  description: string
  severity: 'critical' | 'warning' | 'info'
  action_label?: string
  action_route?: string
  action_type?: string
  created_at: string
}

const severityConfig = {
  critical: {
    border: 'border-red-300',
    bg: 'bg-red-50',
    icon: <AlertCircle className="h-5 w-5 text-red-600" />,
    badge: 'bg-red-100 text-red-700',
    label: 'Critico',
  },
  warning: {
    border: 'border-amber-300',
    bg: 'bg-amber-50',
    icon: <AlertTriangle className="h-5 w-5 text-amber-600" />,
    badge: 'bg-amber-100 text-amber-700',
    label: 'Attenzione',
  },
  info: {
    border: 'border-blue-300',
    bg: 'bg-blue-50',
    icon: <Info className="h-5 w-5 text-blue-600" />,
    badge: 'bg-blue-100 text-blue-700',
    label: 'Info',
  },
}

const actionIconMap: Record<string, React.ReactNode> = {
  sollecito: <Send className="h-3.5 w-3.5" />,
  verifica: <Search className="h-3.5 w-3.5" />,
}

export default function AlertsPage() {
  const { data, isLoading } = useAlertsScan()

  if (isLoading) return <LoadingSpinner className="mt-20" size="lg" />

  const alerts = (data as { alerts?: AlertItem[] })?.alerts ?? (data as AlertItem[]) ?? []

  // Sort: critical first, then warning, then info
  const sortedAlerts = [...alerts].sort((a, b) => {
    const order = { critical: 0, warning: 1, info: 2 }
    return (order[a.severity] ?? 3) - (order[b.severity] ?? 3)
  })

  const criticalCount = alerts.filter((a) => a.severity === 'critical').length
  const warningCount = alerts.filter((a) => a.severity === 'warning').length

  return (
    <div className="mx-auto max-w-3xl">
      <PageHeader
        title="Notifiche e avvisi"
        subtitle={
          alerts.length > 0
            ? `${alerts.length} avvis${alerts.length === 1 ? 'o' : 'i'} attiv${alerts.length === 1 ? 'o' : 'i'}${
                criticalCount > 0 ? ` - ${criticalCount} critic${criticalCount === 1 ? 'o' : 'i'}` : ''
              }${warningCount > 0 ? ` - ${warningCount} da verificare` : ''}`
            : 'Tutto sotto controllo'
        }
      />

      {sortedAlerts.length === 0 ? (
        <EmptyState
          icon={<Bell className="h-12 w-12" />}
          title="Nessun avviso"
          description="Ottimo! Non ci sono problemi da segnalare al momento."
        />
      ) : (
        <div className="space-y-3">
          {sortedAlerts.map((alert) => {
            const config = severityConfig[alert.severity] ?? severityConfig.info
            return (
              <Card key={alert.id} className={`!border ${config.border} ${config.bg}`}>
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 shrink-0">{config.icon}</div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium text-gray-900">{alert.title}</h3>
                      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${config.badge}`}>
                        {config.label}
                      </span>
                    </div>
                    <p className="mt-1 text-sm text-gray-700">{alert.description}</p>
                    {alert.action_label && (
                      <button
                        onClick={() => {
                          if (alert.action_route) {
                            window.location.href = alert.action_route
                          }
                        }}
                        className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-sm font-medium text-gray-700 shadow-sm ring-1 ring-gray-200 hover:bg-gray-50"
                      >
                        {actionIconMap[alert.action_type ?? ''] ?? null}
                        {alert.action_label}
                      </button>
                    )}
                  </div>
                  <span className="shrink-0 text-xs text-gray-400">
                    {new Date(alert.created_at).toLocaleDateString('it-IT', {
                      day: 'numeric',
                      month: 'short',
                    })}
                  </span>
                </div>
              </Card>
            )
          })}
        </div>
      )}
    </div>
  )
}
